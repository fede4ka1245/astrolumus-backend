import ipaddress
import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    RequestPack,
    RequestPackPurchase,
    Subscription,
    SubscriptionPayment,
    SubscriptionPlan,
    get_usage_snapshot,
    subscription_status,
    try_consume,
)
from .serializers import RequestPackSerializer, SubscriptionPlanSerializer
from . import yookassa_gateway

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assistant_usage(request):
    """Returns the current balance snapshot for the authenticated user."""
    return Response(get_usage_snapshot(request.user))


def _resolve_language_code(request):
    """Resolve the preferred language: query param, Accept-Language, then
    authenticated user's language. Returns a 2-letter code or None."""
    lang = request.query_params.get("language_code") or request.query_params.get("lang")
    if lang:
        return lang.split("-")[0].lower()
    accept_lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    if accept_lang:
        primary = accept_lang.split(",")[0].split(";")[0].strip()
        if primary:
            return primary.split("-")[0].lower()
    if request.user and request.user.is_authenticated:
        user_lang = getattr(request.user, "language", None)
        if user_lang:
            return user_lang.split("-")[0].lower()
    return None


@api_view(["GET"])
@permission_classes([AllowAny])
def request_packs_list(request):
    """Returns the list of active request packs ordered by sort_order."""
    language_code = _resolve_language_code(request)
    queryset = RequestPack.objects.filter(is_active=True).order_by("sort_order", "id")
    serializer = RequestPackSerializer(
        queryset, many=True, context={"language_code": language_code, "request": request}
    )
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def subscription_plans_list(request):
    """Returns the list of active subscription plans ordered by sort_order."""
    language_code = _resolve_language_code(request)
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by("sort_order", "id")
    serializer = SubscriptionPlanSerializer(
        queryset, many=True, context={"language_code": language_code, "request": request}
    )
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_status_view(request):
    """Returns the subscription entitlement status for the authenticated user."""
    return Response(subscription_status(request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def purchase_subscription(request, code):
    """Creates a YooKassa payment for the given subscription plan.

    200 -> {"confirmation_url": "...", "payment_id": <id>}
    400 -> plan not found / inactive / has no RUB price
    503 -> YooKassa not configured
    502 -> payment creation failed
    """
    plan = SubscriptionPlan.objects.filter(code=code, is_active=True).first()
    if plan is None:
        return Response({"detail": "Plan not found or inactive."}, status=status.HTTP_400_BAD_REQUEST)
    if plan.price_rub is None:
        return Response({"detail": "Plan has no RUB price."}, status=status.HTTP_400_BAD_REQUEST)

    # Manual renewal must extend the existing subscription, not run a second
    # one in parallel: attach the payment to the user's ACTIVE subscription
    # when there is one (mark_succeeded_and_activate extends from
    # max(now, current_period_end), so no paid time is lost). With no active
    # sub, reuse a previously abandoned PENDING row for the same plan so
    # repeated checkout attempts don't stack pending subscriptions. Only
    # create a brand-new Subscription when neither exists.
    created_subscription = False
    subscription = (
        Subscription.objects.filter(
            user=request.user, status=Subscription.STATUS_ACTIVE,
        )
        .order_by("-current_period_end")
        .first()
    )
    if subscription is None:
        subscription = (
            Subscription.objects.filter(
                user=request.user, plan=plan, status=Subscription.STATUS_PENDING,
            )
            .order_by("-created_at")
            .first()
        )
    if subscription is None:
        subscription = Subscription.objects.create(
            user=request.user,
            plan=plan,
            status=Subscription.STATUS_PENDING,
            provider="yookassa",
        )
        created_subscription = True

    payment = SubscriptionPayment.objects.create(
        user=request.user,
        subscription=subscription,
        plan=plan,
        amount=plan.price_rub,
        currency="RUB",
        status=SubscriptionPayment.STATUS_PENDING,
        provider="yookassa",
    )

    base_return = getattr(settings, "YOOKASSA_RETURN_URL", "") or ""
    sep = "&" if "?" in base_return else "?"
    return_url = f"{base_return}{sep}sub_paid={payment.id}"

    try:
        payment_id, confirmation_url = yookassa_gateway.create_subscription_payment(
            payment, return_url
        )
    except yookassa_gateway.NotConfigured:
        payment.delete()
        if created_subscription:
            subscription.delete()
        return Response(
            {"detail": "Payment provider is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as exc:  # pragma: no cover - network/provider errors
        logger.exception("yookassa: failed to create subscription payment: %s", exc)
        payment.delete()
        if created_subscription:
            subscription.delete()
        return Response(
            {"detail": "Failed to create payment."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    payment.provider_payment_id = payment_id or ""
    payment.confirmation_url = confirmation_url or ""
    payment.save(update_fields=["provider_payment_id", "confirmation_url", "updated_at"])

    return Response(
        {"confirmation_url": confirmation_url, "payment_id": payment.id},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assistant_consume(request):
    """Atomically debits one request from the user's balance.

    200 + snapshot on success, 429 + snapshot when the balance is exhausted.
    """
    result = try_consume(request.user)
    if result["ok"]:
        return Response(result["snapshot"], status=status.HTTP_200_OK)

    snapshot = result.get("snapshot") or {"enabled": True, "unlimited": False, "balance": 0}
    return Response(
        {
            "detail": "Request balance exhausted.",
            "reason": result.get("reason", "no_balance"),
            "balance": snapshot.get("balance", 0),
            "enabled": snapshot.get("enabled", True),
            "unlimited": snapshot.get("unlimited", False),
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def purchase_pack(request, code):
    """Creates a YooKassa payment for the given pack and a pending purchase.

    200 -> {"confirmation_url": "...", "purchase_id": <id>}
    400 -> pack not found / inactive / has no RUB price
    503 -> YooKassa not configured
    """
    pack = RequestPack.objects.filter(code=code, is_active=True).first()
    if pack is None:
        return Response({"detail": "Pack not found or inactive."}, status=status.HTTP_400_BAD_REQUEST)
    if pack.price_rub is None:
        return Response({"detail": "Pack has no RUB price."}, status=status.HTTP_400_BAD_REQUEST)

    purchase = RequestPackPurchase.objects.create(
        user=request.user,
        pack=pack,
        requests_count=pack.requests_count,
        amount=pack.price_rub,
        currency="RUB",
        status=RequestPackPurchase.STATUS_PENDING,
        provider="yookassa",
    )

    base_return = getattr(settings, "YOOKASSA_RETURN_URL", "") or ""
    sep = "&" if "?" in base_return else "?"
    return_url = f"{base_return}{sep}pack_paid={purchase.id}"

    try:
        payment_id, confirmation_url = yookassa_gateway.create_pack_payment(
            purchase, return_url
        )
    except yookassa_gateway.NotConfigured:
        purchase.delete()
        return Response(
            {"detail": "Payment provider is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as exc:  # pragma: no cover - network/provider errors
        logger.exception("yookassa: failed to create payment: %s", exc)
        purchase.delete()
        return Response(
            {"detail": "Failed to create payment."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    purchase.provider_payment_id = payment_id or ""
    purchase.confirmation_url = confirmation_url or ""
    purchase.save(update_fields=["provider_payment_id", "confirmation_url", "updated_at"])

    return Response(
        {"confirmation_url": confirmation_url, "purchase_id": purchase.id},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pack_purchase_status(request, purchase_id):
    """Client-side polling endpoint for a pack purchase.

    Looks up the purchase owned by the caller; while it is still pending,
    re-checks the canonical state with YooKassa and applies success
    idempotently (same `mark_succeeded_and_credit` path as the webhook). The
    response always includes a fresh usage snapshot so the client can update
    the balance in one round-trip.

    200 -> {"id": ..., "status": "pending|succeeded|canceled", "usage": {...}}
    404 -> purchase not found / not owned by the caller
    """
    purchase = RequestPackPurchase.objects.filter(
        pk=purchase_id, user=request.user
    ).first()
    if purchase is None:
        return Response({"detail": "Purchase not found."}, status=status.HTTP_404_NOT_FOUND)

    if purchase.status == RequestPackPurchase.STATUS_PENDING and purchase.provider_payment_id:
        try:
            remote_status = yookassa_gateway.fetch_payment(purchase.provider_payment_id)
        except yookassa_gateway.NotConfigured:
            remote_status = None
        except Exception as exc:  # pragma: no cover - network/provider errors
            logger.warning("yookassa: pack status poll failed for %s: %s", purchase.pk, exc)
            remote_status = None

        if remote_status == "succeeded":
            purchase.mark_succeeded_and_credit()
        elif remote_status == "canceled":
            purchase.status = RequestPackPurchase.STATUS_CANCELED
            purchase.save(update_fields=["status", "updated_at"])

    return Response(
        {
            "id": purchase.id,
            "status": purchase.status,
            "usage": get_usage_snapshot(request.user),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_payment_status(request, payment_id):
    """Client-side polling endpoint for a subscription payment.

    Looks up the payment owned by the caller; while it is still pending,
    re-checks the canonical state with YooKassa (also capturing the saved
    payment-method id for auto-renewal) and applies success idempotently via
    `mark_succeeded_and_activate`. The response always includes a fresh
    subscription snapshot.

    200 -> {"id": ..., "status": "...", "subscription": {...}}
    404 -> payment not found / not owned by the caller
    """
    payment = SubscriptionPayment.objects.filter(
        pk=payment_id, user=request.user
    ).first()
    if payment is None:
        return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

    if payment.status == SubscriptionPayment.STATUS_PENDING and payment.provider_payment_id:
        try:
            remote_status, method_id = yookassa_gateway.fetch_payment_info(
                payment.provider_payment_id
            )
        except yookassa_gateway.NotConfigured:
            remote_status, method_id = None, ""
        except Exception as exc:  # pragma: no cover - network/provider errors
            logger.warning(
                "yookassa: subscription status poll failed for %s: %s", payment.pk, exc
            )
            remote_status, method_id = None, ""

        if remote_status == "succeeded":
            if method_id and not payment.provider_payment_method_id:
                payment.provider_payment_method_id = method_id
                payment.save(update_fields=["provider_payment_method_id", "updated_at"])
            payment.mark_succeeded_and_activate()
        elif remote_status == "canceled":
            payment.status = SubscriptionPayment.STATUS_CANCELED
            payment.save(update_fields=["status", "updated_at"])

    return Response(
        {
            "id": payment.id,
            "status": payment.status,
            "subscription": subscription_status(request.user),
        }
    )


# YooKassa's documented notification source ranges
# (https://yookassa.ru/developers/using-api/webhooks#ip).
YOOKASSA_NOTIFICATION_NETWORKS = [
    ipaddress.ip_network(net)
    for net in (
        "185.71.76.0/27",
        "185.71.77.0/27",
        "77.75.153.0/25",
        "77.75.154.128/25",
        "77.75.156.11/32",
        "77.75.156.35/32",
        "2a02:5180::/32",
    )
]


def _webhook_client_ip(request):
    """Best-effort client IP: first X-Forwarded-For hop (set by the reverse
    proxy in front of the app) falling back to REMOTE_ADDR."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _ip_is_yookassa(ip_str):
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(addr in net for net in YOOKASSA_NOTIFICATION_NETWORKS)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def yookassa_webhook(request):
    """YooKassa notification receiver.

    On `payment.succeeded`, locate the purchase (preferring
    metadata.purchase_id), re-verify the payment status with YooKassa, then
    credit the balance idempotently. Always returns 200 for well-formed
    notifications so YooKassa stops retrying; 400 only on a malformed body.

    Hardening: the notification body is never trusted on its own — crediting
    only happens after re-fetching the payment from the YooKassa API and using
    that canonical state. Optionally (YOOKASSA_WEBHOOK_IP_CHECK, default ON in
    prod) the source IP must belong to YooKassa's documented ranges.
    """
    if getattr(settings, "YOOKASSA_WEBHOOK_IP_CHECK", False):
        client_ip = _webhook_client_ip(request)
        if not _ip_is_yookassa(client_ip):
            logger.warning("yookassa webhook: rejected non-YooKassa source ip=%s", client_ip)
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

    try:
        if isinstance(request.data, dict) and request.data:
            payload = request.data
        else:
            payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        logger.warning("yookassa webhook: bad body: %s", exc)
        return Response({"detail": "Malformed body."}, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(payload, dict):
        return Response({"detail": "Malformed body."}, status=status.HTTP_400_BAD_REQUEST)

    event = payload.get("event")
    obj = payload.get("object") or {}
    if not isinstance(obj, dict):
        obj = {}

    if event != "payment.succeeded":
        # Acknowledge anything else (cancellations, waiting_for_capture, etc.).
        return Response({"ok": True}, status=status.HTTP_200_OK)

    metadata = obj.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    payment_id = obj.get("id")

    # Subscription payments are routed by metadata.kind == "subscription" (or
    # the presence of subscription_payment_id). Keep the pack path below intact.
    kind = metadata.get("kind")
    sub_payment_id = metadata.get("subscription_payment_id")
    if kind == "subscription" or sub_payment_id:
        return _handle_subscription_webhook(sub_payment_id, payment_id)

    purchase_id = metadata.get("purchase_id")

    purchase = None
    if purchase_id:
        purchase = RequestPackPurchase.objects.filter(pk=purchase_id).first()
    if purchase is None and payment_id:
        purchase = RequestPackPurchase.objects.filter(provider_payment_id=payment_id).first()

    if purchase is None:
        logger.warning(
            "yookassa webhook: purchase not found (purchase_id=%s payment_id=%s)",
            purchase_id, payment_id,
        )
        return Response({"ok": True}, status=status.HTTP_200_OK)

    if purchase.credited:
        return Response({"ok": True}, status=status.HTTP_200_OK)

    # Re-fetch the payment from YooKassa to confirm it really succeeded. When
    # our DB recorded a provider payment id we verify THAT id; only when it is
    # missing do we fall back to the (untrusted) id from the notification body,
    # and in that case the canonical payment must additionally prove — via the
    # metadata written at creation time and the amount — that it belongs to
    # this exact purchase. Otherwise an attacker could replay their own cheap
    # succeeded payment id against someone else's pending purchase.
    trusted_link = bool(purchase.provider_payment_id)
    verify_id = purchase.provider_payment_id or payment_id
    try:
        details = yookassa_gateway.fetch_payment_details(verify_id) if verify_id else None
    except yookassa_gateway.NotConfigured:
        logger.error("yookassa webhook: gateway not configured")
        return Response({"ok": True}, status=status.HTTP_200_OK)
    except Exception as exc:  # pragma: no cover - network/provider errors
        logger.exception("yookassa webhook: verify failed: %s", exc)
        return Response({"ok": True}, status=status.HTTP_200_OK)

    remote_status = details["status"] if details else None
    if remote_status != "succeeded":
        logger.warning(
            "yookassa webhook: payment %s status is %s, not crediting",
            verify_id, remote_status,
        )
        return Response({"ok": True}, status=status.HTTP_200_OK)

    if not trusted_link:
        if not _canonical_payment_matches(
            details, "purchase_id", purchase.pk, purchase.amount, purchase.currency,
        ):
            logger.warning(
                "yookassa webhook: payment %s does not belong to purchase %s "
                "(metadata/amount mismatch), not crediting",
                verify_id, purchase.pk,
            )
            return Response({"ok": False}, status=status.HTTP_200_OK)
        # The body-supplied id is now verified to be ours: persist it.
        purchase.provider_payment_id = verify_id
        purchase.save(update_fields=["provider_payment_id", "updated_at"])

    purchase.mark_succeeded_and_credit()
    return Response({"ok": True}, status=status.HTTP_200_OK)


def _canonical_payment_matches(details, metadata_key, expected_pk, expected_amount, expected_currency):
    """True when a canonical (gateway-fetched) payment provably belongs to the
    local object: the metadata our create-payment code wrote references the
    object's pk AND the paid amount/currency equal the expected price."""
    metadata = details.get("metadata") or {}
    if str(metadata.get(metadata_key, "")) != str(expected_pk):
        return False
    try:
        paid = Decimal(str(details.get("amount_value")))
    except (InvalidOperation, TypeError, ValueError):
        return False
    if paid != expected_amount:
        return False
    paid_currency = (details.get("amount_currency") or "").upper()
    if paid_currency and paid_currency != (expected_currency or "RUB").upper():
        return False
    return True


def _handle_subscription_webhook(sub_payment_id, payment_id):
    """Activate/extend a subscription on a succeeded subscription payment.

    Mirrors the pack path: locate the SubscriptionPayment, re-verify with
    YooKassa (canonical fetch — nothing from the notification body is trusted),
    then idempotently activate. Always returns 200 for well-formed
    notifications.
    """
    payment = None
    if sub_payment_id:
        payment = SubscriptionPayment.objects.filter(pk=sub_payment_id).first()
    if payment is None and payment_id:
        payment = SubscriptionPayment.objects.filter(provider_payment_id=payment_id).first()

    if payment is None:
        logger.warning(
            "yookassa webhook: subscription payment not found "
            "(subscription_payment_id=%s payment_id=%s)",
            sub_payment_id, payment_id,
        )
        return Response({"ok": True}, status=status.HTTP_200_OK)

    if payment.applied:
        return Response({"ok": True}, status=status.HTTP_200_OK)

    # Same hardening as the pack path: verify our stored provider payment id
    # when present; a body-supplied id is only accepted if the canonical
    # payment's metadata + amount tie it to this exact SubscriptionPayment.
    trusted_link = bool(payment.provider_payment_id)
    verify_id = payment.provider_payment_id or payment_id
    try:
        details = yookassa_gateway.fetch_payment_details(verify_id) if verify_id else None
    except yookassa_gateway.NotConfigured:
        logger.error("yookassa webhook: gateway not configured")
        return Response({"ok": True}, status=status.HTTP_200_OK)
    except Exception as exc:  # pragma: no cover - network/provider errors
        logger.exception("yookassa webhook: subscription verify failed: %s", exc)
        return Response({"ok": True}, status=status.HTTP_200_OK)

    remote_status = details["status"] if details else None
    if remote_status != "succeeded":
        logger.warning(
            "yookassa webhook: subscription payment %s status is %s, not activating",
            verify_id, remote_status,
        )
        return Response({"ok": True}, status=status.HTTP_200_OK)

    if not trusted_link:
        if not _canonical_payment_matches(
            details, "subscription_payment_id", payment.pk, payment.amount, payment.currency,
        ):
            logger.warning(
                "yookassa webhook: payment %s does not belong to subscription "
                "payment %s (metadata/amount mismatch), not activating",
                verify_id, payment.pk,
            )
            return Response({"ok": False}, status=status.HTTP_200_OK)
        # The body-supplied id is now verified to be ours: persist it.
        payment.provider_payment_id = verify_id
        payment.save(update_fields=["provider_payment_id", "updated_at"])

    # Persist the saved payment method (for recurring) onto the payment so it
    # propagates to the subscription during activation. Taken from the
    # canonical gateway fetch, NOT from the notification body (same source the
    # polling path uses).
    method_id = details.get("payment_method_id") or ""
    if method_id and not payment.provider_payment_method_id:
        payment.provider_payment_method_id = method_id
        payment.save(update_fields=["provider_payment_method_id", "updated_at"])

    payment.mark_succeeded_and_activate()
    return Response({"ok": True}, status=status.HTTP_200_OK)
