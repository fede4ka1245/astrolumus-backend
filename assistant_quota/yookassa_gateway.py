"""Thin, isolated wrapper around the YooKassa payments API.

All YooKassa-specific knowledge lives here so the views stay testable. Two
entry points:
    create_pack_payment(purchase, return_url) -> (payment_id, confirmation_url)
    fetch_payment(payment_id)                 -> status string (e.g. "succeeded")

Configuration is read from settings: YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY.
If credentials are missing, NotConfigured is raised so the caller can return a
clear error instead of crashing.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from yookassa import Configuration, Payment
from yookassa.domain.exceptions.forbidden_error import ForbiddenError


class NotConfigured(Exception):
    """Raised when YooKassa credentials are not present in settings."""


def _configure():
    secret_key = getattr(settings, "YOOKASSA_SECRET_KEY", None)
    if not secret_key:
        raise NotConfigured("YOOKASSA_SECRET_KEY is not set")
    shop_id = getattr(settings, "YOOKASSA_SHOP_ID", None)
    # Disambiguate by SHOP ID presence, NOT by key prefix: ordinary shop secret
    # keys ALSO start with live_/test_, so treating that prefix as an OAuth token
    # (configure_auth_token) makes YooKassa reject a valid shop key with
    # "OAuth-token is invalid". When a shop id is configured, always use the
    # standard account_id + secret_key auth; OAuth tokens are the no-shop-id case.
    if shop_id:
        Configuration.account_id = str(shop_id)
        Configuration.secret_key = secret_key
    else:
        Configuration.configure_auth_token(secret_key)


def _receipt(email, description, amount_value, currency):
    """54-FZ fiscal receipt block, required on every payment because the live
    shop has fiscalization enabled (YooKassa otherwise rejects the request
    with "Receipt is missing or illegal"). vat_code 1 = no VAT; override via
    YOOKASSA_VAT_CODE if the tax regime changes."""
    return {
        "customer": {"email": email},
        "items": [
            {
                "description": description[:128],
                "quantity": "1.00",
                "amount": {"value": amount_value, "currency": currency},
                "vat_code": int(getattr(settings, "YOOKASSA_VAT_CODE", 1)),
                "payment_subject": "service",
                "payment_mode": "full_payment",
            }
        ],
    }


def create_pack_payment(purchase, return_url):
    """Create a YooKassa payment for the given RequestPackPurchase.

    Returns (payment_id, confirmation_url). Raises NotConfigured if the
    gateway credentials are missing.
    """
    _configure()

    idempotence_key = str(uuid.uuid4())
    description = f"Пакет {purchase.requests_count} запросов"
    currency = purchase.currency or "RUB"
    amount_value = f"{purchase.amount:.2f}"
    payment = Payment.create(
        {
            "amount": {
                "value": amount_value,
                "currency": currency,
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "capture": True,
            "description": description,
            "receipt": _receipt(purchase.user.email, description, amount_value, currency),
            "metadata": {
                "user_id": purchase.user_id,
                "pack_code": purchase.pack.code,
                "purchase_id": purchase.id,
            },
        },
        idempotence_key,
    )

    confirmation_url = ""
    confirmation = getattr(payment, "confirmation", None)
    if confirmation is not None:
        confirmation_url = getattr(confirmation, "confirmation_url", "") or ""
    return payment.id, confirmation_url


def create_subscription_payment(payment_obj, return_url):
    """Create a YooKassa payment for the given SubscriptionPayment.

    Requests a saved payment method (``save_payment_method=True``) so future
    periods can be auto-charged. If the shop has recurring payments disabled
    (YooKassa enables them per-shop on request), falls back to a one-off
    payment without saving the method — the subscription still activates, it
    just won't auto-renew until YooKassa enables recurring for the shop.
    Returns (payment_id, confirmation_url). Raises NotConfigured if the
    gateway credentials are missing.
    """
    _configure()

    plan = payment_obj.plan
    description = f"Подписка {plan.months} мес."
    currency = payment_obj.currency or "RUB"
    amount_value = f"{payment_obj.amount:.2f}"
    payload = {
        "amount": {
            "value": amount_value,
            "currency": currency,
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url,
        },
        "capture": True,
        "save_payment_method": True,
        "description": description,
        "receipt": _receipt(payment_obj.user.email, description, amount_value, currency),
        "metadata": {
            "user_id": payment_obj.user_id,
            "plan_code": plan.code,
            "subscription_payment_id": payment_obj.id,
            "kind": "subscription",
        },
    }
    try:
        payment = Payment.create(payload, str(uuid.uuid4()))
    except ForbiddenError as exc:
        content = getattr(exc, "content", None) or {}
        if "recurring" not in str(content.get("description", "")).lower():
            raise
        payload.pop("save_payment_method", None)
        payment = Payment.create(payload, str(uuid.uuid4()))

    confirmation_url = ""
    confirmation = getattr(payment, "confirmation", None)
    if confirmation is not None:
        confirmation_url = getattr(confirmation, "confirmation_url", "") or ""
    return payment.id, confirmation_url


def charge_saved(amount, currency, payment_method_id, description, metadata, customer_email):
    """Charge a previously saved payment method (recurring auto-renewal).

    Creates a captured payment with no confirmation step. Returns
    (payment_id, status). Raises NotConfigured if credentials are missing.
    """
    _configure()

    idempotence_key = str(uuid.uuid4())
    currency = currency or "RUB"
    amount_value = f"{amount:.2f}"
    payment = Payment.create(
        {
            "amount": {
                "value": amount_value,
                "currency": currency,
            },
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": description,
            "receipt": _receipt(customer_email, description, amount_value, currency),
            "metadata": metadata or {},
        },
        idempotence_key,
    )
    return payment.id, getattr(payment, "status", None)


def fetch_payment(payment_id):
    """Return the current status string of a YooKassa payment (e.g.
    "succeeded", "pending", "canceled"). Raises NotConfigured if credentials
    are missing."""
    _configure()
    payment = Payment.find_one(payment_id)
    return getattr(payment, "status", None)


def fetch_payment_info(payment_id):
    """Return (status, payment_method_id) for a YooKassa payment.

    payment_method_id is the saved-method id (empty string when absent) —
    needed by the subscription polling path so recurring charges keep working
    even when the webhook never arrives. Raises NotConfigured if credentials
    are missing."""
    _configure()
    payment = Payment.find_one(payment_id)
    method_id = ""
    pm = getattr(payment, "payment_method", None)
    if pm is not None:
        method_id = getattr(pm, "id", "") or ""
    return getattr(payment, "status", None), method_id


def fetch_payment_details(payment_id):
    """Return the canonical state of a YooKassa payment as a dict:

        {
            "status": "succeeded" | "pending" | "canceled" | ... | None,
            "payment_method_id": str,    # saved-method id, "" when absent
            "metadata": dict,            # metadata set at creation time
            "amount_value": str | None,  # e.g. "990.00"
            "amount_currency": str,      # e.g. "RUB"
        }

    Webhook handlers need metadata + amount so a notification's payment id can
    be proven to belong to the local purchase/payment (via the purchase_id /
    subscription_payment_id metadata written by the create_* functions above)
    before crediting/activating. Raises NotConfigured if credentials are
    missing."""
    _configure()
    payment = Payment.find_one(payment_id)
    method_id = ""
    pm = getattr(payment, "payment_method", None)
    if pm is not None:
        method_id = getattr(pm, "id", "") or ""
    metadata = getattr(payment, "metadata", None)
    if not isinstance(metadata, dict):
        metadata = dict(metadata) if metadata else {}
    amount = getattr(payment, "amount", None)
    amount_value = getattr(amount, "value", None) if amount is not None else None
    amount_currency = (getattr(amount, "currency", "") or "") if amount is not None else ""
    return {
        "status": getattr(payment, "status", None),
        "payment_method_id": method_id,
        "metadata": metadata,
        "amount_value": str(amount_value) if amount_value is not None else None,
        "amount_currency": amount_currency,
    }
