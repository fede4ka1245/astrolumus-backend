"""Boosty + Patreon webhook receivers.

Both vendors only ship "subscription created/charge succeeded" payloads with an
external user identifier (email for Boosty; Patreon user id + email for Patreon)
and a tier/level id. We map that tier id back to a local Tariff (via
`Tariff.boosty_subscription_level_id` / `patreon_tier_id`) and create an
`ActivationTariff` for the matched user. Unmatched events are still recorded so
admins can see what came in and bind it manually.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import logging
from datetime import timedelta
from typing import Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from tariffs.models import ActivationTariff, Tariff
from .models import ExternalPaymentEvent


logger = logging.getLogger(__name__)
User = get_user_model()


def _resolve_user(email: Optional[str]) -> Optional["User"]:
    if not email:
        return None
    return User.objects.filter(email__iexact=email).first()


def _activate(user, tariff) -> ActivationTariff:
    """Create an ActivationTariff stacked on the latest active activation in
    the same tariff group, mirroring tariffs.views.payment_from_site."""
    last_activations = (
        ActivationTariff.objects
        .filter(user=user)
        .filter(
            Q(Q(tariff__validity_days__gt=0)
              & Q(created_at__gt=timezone.now() - timedelta(days=1) * F("tariff__validity_days")))
            | Q(tariff__validity_days=0)
        )
        .order_by("-created_at")
    )
    group_anchor = last_activations.filter(
        Q(tariff=tariff) | Q(tariff__tariff_group_id=tariff.tariff_group_id)
    ).first() if tariff.tariff_group_id else None

    activation = ActivationTariff.objects.create(tariff=tariff, user=user)
    if group_anchor and group_anchor.tariff and group_anchor.tariff.validity_days:
        activation.created_at = group_anchor.created_at + timedelta(
            days=group_anchor.tariff.validity_days
        )
        activation.save(update_fields=["created_at"])
    return activation


@transaction.atomic
def _process_event(*, provider: str, event_type: str, email: str,
                   external_user_id: str, tier_id: str, payload: dict) -> ExternalPaymentEvent:
    event = ExternalPaymentEvent.objects.create(
        provider=provider,
        event_type=event_type or "",
        external_user_id=external_user_id or "",
        external_email=email or "",
        tier_id=tier_id or "",
        payload=payload or {},
    )

    tariff = None
    if tier_id:
        if provider == ExternalPaymentEvent.PROVIDER_BOOSTY:
            tariff = Tariff.objects.filter(boosty_subscription_level_id=str(tier_id)).first()
        elif provider == ExternalPaymentEvent.PROVIDER_PATREON:
            tariff = Tariff.objects.filter(patreon_tier_id=str(tier_id)).first()

    user = _resolve_user(email)

    if not tariff:
        event.status = ExternalPaymentEvent.STATUS_UNMATCHED
        event.note = "Tariff for this tier id is not configured."
        event.save(update_fields=["status", "note"])
        return event

    event.matched_tariff = tariff

    if not user:
        event.status = ExternalPaymentEvent.STATUS_UNMATCHED
        event.note = "User with this email is not registered yet."
        event.save(update_fields=["matched_tariff", "status", "note"])
        return event

    activation = _activate(user, tariff)
    event.matched_user = user
    event.activation = activation
    event.status = ExternalPaymentEvent.STATUS_PROCESSED
    event.save(update_fields=["matched_tariff", "matched_user", "activation", "status"])
    logger.info(
        "external payment processed: provider=%s user=%s tariff=%s",
        provider, user.pk, tariff.code,
    )
    return event


@method_decorator(csrf_exempt, name="dispatch")
class BoostyWebhookView(View):
    """Boosty webhook receiver.

    Boosty's webhook layout (see docs.boosty.to): JSON with `event` discriminator
    and `data` payload. We accept both subscription_created/recurring_payment_succeeded
    and treat them as activation events.

    Configure in admin → Boosty: send to /payments/boosty/webhook/?token=<settings.BOOSTY_WEBHOOK_TOKEN>.
    """

    def post(self, request, *args, **kwargs):
        from django.conf import settings as dj_settings
        token = request.GET.get("token") or request.headers.get("X-Webhook-Token")
        expected = getattr(dj_settings, "BOOSTY_WEBHOOK_TOKEN", "")
        if expected and token != expected:
            return HttpResponse("forbidden", status=403)

        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError) as exc:
            logger.warning("boosty webhook: bad body: %s", exc)
            return HttpResponse("invalid", status=400)

        event_type = body.get("event") or body.get("type") or ""
        data = body.get("data") or {}
        # Boosty payload: data.user.email / data.user.id / data.subscription_level.id
        user_node = data.get("user") or {}
        email = user_node.get("email") or data.get("email") or ""
        external_user_id = str(user_node.get("id") or data.get("user_id") or "")
        level_node = data.get("subscription_level") or data.get("level") or {}
        tier_id = str(level_node.get("id") or data.get("subscription_level_id") or "")

        event = _process_event(
            provider=ExternalPaymentEvent.PROVIDER_BOOSTY,
            event_type=event_type,
            email=email,
            external_user_id=external_user_id,
            tier_id=tier_id,
            payload=body,
        )
        return JsonResponse({"ok": True, "event_id": event.id, "status": event.status})


@method_decorator(csrf_exempt, name="dispatch")
class PatreonWebhookView(View):
    """Patreon webhook receiver.

    Patreon sends an HMAC-MD5 signature in the X-Patreon-Signature header
    using the secret configured in the creator's webhook settings. The event
    type is in X-Patreon-Event (`members:create`, `members:update`, etc.).
    The payload JSON-API includes `data.relationships.currently_entitled_tiers.data[].id`
    (the tier we map) and `included[]` user attributes (email).
    """

    def post(self, request, *args, **kwargs):
        from django.conf import settings as dj_settings
        secret = getattr(dj_settings, "PATREON_WEBHOOK_SECRET", "")
        signature = request.headers.get("X-Patreon-Signature", "")
        body_bytes = request.body
        if secret:
            digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.md5).hexdigest()
            if not hmac.compare_digest(digest, signature):
                return HttpResponse("forbidden", status=403)

        try:
            body = json.loads(body_bytes.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError) as exc:
            logger.warning("patreon webhook: bad body: %s", exc)
            return HttpResponse("invalid", status=400)

        event_type = request.headers.get("X-Patreon-Event", "")
        data = body.get("data") or {}

        relationships = data.get("relationships") or {}
        tiers = (relationships.get("currently_entitled_tiers") or {}).get("data") or []
        tier_id = str(tiers[0]["id"]) if tiers else ""

        # Patreon uses JSON:API; user attributes live in `included[]` next to the
        # member resource. We try a few likely shapes to dig out the email.
        included = body.get("included") or []
        email = ""
        external_user_id = ""
        for inc in included:
            if inc.get("type") == "user":
                attrs = inc.get("attributes") or {}
                email = attrs.get("email") or ""
                external_user_id = str(inc.get("id") or "")
                break
        if not email:
            attrs = data.get("attributes") or {}
            email = attrs.get("email") or ""

        event = _process_event(
            provider=ExternalPaymentEvent.PROVIDER_PATREON,
            event_type=event_type,
            email=email,
            external_user_id=external_user_id,
            tier_id=tier_id,
            payload=body,
        )
        return JsonResponse({"ok": True, "event_id": event.id, "status": event.status})
