import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from . import yookassa_gateway
from .models import RequestPackPurchase, Subscription, SubscriptionPayment

logger = logging.getLogger(__name__)

# A pending renewal payment that never got a provider payment id cannot be
# resolved via the gateway (the idempotence key is random and not persisted).
# Before this age we skip the subscription entirely to avoid any chance of a
# double charge (the charge may have reached the provider right before a
# crash); after it we write the row off as canceled so the subscription can
# be charged again on the next run.
STALE_UNLINKED_RENEWAL_AGE = timedelta(hours=24)


def resolve_pending_renewals(sub, now=None):
    """Resolve in-flight (pending) renewal payments of `sub` via the gateway.

    Re-checks each pending renewal SubscriptionPayment against the provider's
    canonical status before the caller decides whether to charge anew. Network
    errors and still-pending charges are treated as in-flight so the
    subscription is NEVER moved to past_due (and never double-charged) on an
    unverified outcome.

    Returns one of:
        "none"      - no pending renewal payments remain; safe to charge anew
        "renewed"   - a pending charge turned out succeeded; the subscription
                      has been extended (mark_succeeded_and_activate)
        "in_flight" - a charge is still pending or unresolvable right now;
                      keep the subscription ACTIVE and do NOT charge again
        "canceled"  - every resolvable pending charge is verifiably canceled
    """
    now = now or timezone.now()
    pendings = list(
        SubscriptionPayment.objects.filter(
            subscription=sub,
            is_renewal=True,
            status=SubscriptionPayment.STATUS_PENDING,
        ).order_by("-created_at")
    )
    if not pendings:
        return "none"

    outcomes = set()
    for payment in pendings:
        if not payment.provider_payment_id:
            if payment.created_at <= now - STALE_UNLINKED_RENEWAL_AGE:
                payment.status = SubscriptionPayment.STATUS_CANCELED
                payment.save(update_fields=["status", "updated_at"])
                logger.warning(
                    "renew_due_subscriptions: wrote off stale unlinked renewal "
                    "payment %s (subscription %s)",
                    payment.id, sub.id,
                )
                # Written off -> does not block a fresh charge.
            else:
                logger.warning(
                    "renew_due_subscriptions: renewal payment %s (subscription %s) "
                    "has no provider id yet, skipping this run",
                    payment.id, sub.id,
                )
                outcomes.add("in_flight")
            continue

        try:
            remote_status = yookassa_gateway.fetch_payment(payment.provider_payment_id)
        except Exception as exc:  # pragma: no cover - network/provider errors
            logger.warning(
                "renew_due_subscriptions: could not verify renewal payment %s "
                "(subscription %s): %s",
                payment.id, sub.id, exc,
            )
            outcomes.add("in_flight")
            continue

        if remote_status == "succeeded":
            payment.mark_succeeded_and_activate()
            outcomes.add("renewed")
        elif remote_status == "canceled":
            payment.status = SubscriptionPayment.STATUS_CANCELED
            payment.save(update_fields=["status", "updated_at"])
            outcomes.add("canceled")
        else:
            # "pending", "waiting_for_capture", None, ... -> still in flight.
            outcomes.add("in_flight")

    if "renewed" in outcomes:
        return "renewed"
    if "in_flight" in outcomes:
        return "in_flight"
    if "canceled" in outcomes:
        return "canceled"
    return "none"


@shared_task
def renew_due_subscriptions():
    """Auto-charge saved payment methods for subscriptions due for renewal.

    Picks active, auto-renew subscriptions with a stored payment method whose
    current period has ended. Before charging, any existing pending renewal
    payment is resolved against the gateway (idempotency: a sub with an
    in-flight charge is never charged again). State machine per subscription:

        charge succeeded            -> extend, stay ACTIVE
        charge pending / unknown    -> stay ACTIVE, re-resolve on the next run
        charge verifiably canceled  -> past_due

    past_due is only ever set on a VERIFIED canceled charge; transient errors
    and pending charges leave the subscription ACTIVE so the daily task keeps
    retrying/resolving it. Each subscription is wrapped in its own try/except
    so one failure does not stop the batch.
    """
    now = timezone.now()
    due = (
        Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            auto_renew=True,
            current_period_end__lte=now,
        )
        .exclude(provider_payment_method_id="")
        .select_related("plan", "user")
    )

    renewed = 0
    failed = 0
    in_flight = 0
    for sub in due:
        try:
            outcome = resolve_pending_renewals(sub, now)
            if outcome == "renewed":
                renewed += 1
                continue
            if outcome == "in_flight":
                in_flight += 1
                logger.info(
                    "renew_due_subscriptions: subscription %s has an in-flight "
                    "renewal charge, will re-check next run",
                    sub.id,
                )
                continue
            if outcome == "canceled":
                sub.status = Subscription.STATUS_PAST_DUE
                sub.save(update_fields=["status", "updated_at"])
                failed += 1
                logger.warning(
                    "renew_due_subscriptions: subscription %s renewal charge "
                    "verified canceled -> past_due",
                    sub.id,
                )
                continue

            plan = sub.plan
            if plan.price_rub is None:
                logger.warning(
                    "renew_due_subscriptions: subscription %s plan %s has no RUB price, skipping",
                    sub.id, plan.code,
                )
                continue

            payment = SubscriptionPayment.objects.create(
                user=sub.user,
                subscription=sub,
                plan=plan,
                amount=plan.price_rub,
                currency="RUB",
                status=SubscriptionPayment.STATUS_PENDING,
                provider="yookassa",
                provider_payment_method_id=sub.provider_payment_method_id,
                is_renewal=True,
            )

            payment_id, charge_status = yookassa_gateway.charge_saved(
                amount=plan.price_rub,
                currency="RUB",
                payment_method_id=sub.provider_payment_method_id,
                description=f"Подписка {plan.months} мес. (автопродление)",
                metadata={
                    "user_id": sub.user_id,
                    "plan_code": plan.code,
                    "subscription_payment_id": payment.id,
                    "kind": "subscription",
                },
                customer_email=sub.user.email,
            )
            payment.provider_payment_id = payment_id or ""
            payment.save(update_fields=["provider_payment_id", "updated_at"])

            if charge_status == "succeeded":
                payment.mark_succeeded_and_activate()
                renewed += 1
            elif charge_status == "canceled":
                payment.status = SubscriptionPayment.STATUS_CANCELED
                payment.save(update_fields=["status", "updated_at"])
                sub.status = Subscription.STATUS_PAST_DUE
                sub.save(update_fields=["status", "updated_at"])
                failed += 1
                logger.warning(
                    "renew_due_subscriptions: subscription %s charge canceled -> past_due",
                    sub.id,
                )
            else:
                # "pending" (or any unverified status): the charge is in
                # flight. Keep the subscription ACTIVE; the payment row stays
                # pending and is resolved via the gateway on the next run.
                in_flight += 1
                logger.info(
                    "renew_due_subscriptions: subscription %s charge status=%s, "
                    "treating as in-flight",
                    sub.id, charge_status,
                )
        except Exception as exc:  # pragma: no cover - network/provider errors
            failed += 1
            logger.exception(
                "renew_due_subscriptions: failed to renew subscription %s: %s",
                sub.id, exc,
            )

    logger.info(
        "renew_due_subscriptions: renewed=%s failed=%s in_flight=%s",
        renewed, failed, in_flight,
    )
    return {"renewed": renewed, "failed": failed, "in_flight": in_flight}


# Server-side fallback for the YooKassa callback (HTTP-уведомления). The
# client-side poll on the return page finalizes most payments, but a user who
# closes the tab before it completes leaves a paid-but-pending row behind —
# forever, if the dashboard webhook is not configured. This task re-checks
# recent pending one-off payments against the provider and finalizes them
# with the same idempotent methods the webhook/poll endpoints use.
#
# Renewal charges (is_renewal=True) are deliberately excluded: they are
# resolved by renew_due_subscriptions/resolve_pending_renewals, which has
# stricter double-charge protection.
RESOLVE_MIN_AGE = timedelta(minutes=2)   # don't race a checkout in progress
RESOLVE_MAX_AGE = timedelta(days=2)      # bound provider API calls per run


@shared_task
def resolve_stuck_payments():
    now = timezone.now()
    window = (now - RESOLVE_MAX_AGE, now - RESOLVE_MIN_AGE)
    credited = canceled = checked = 0

    packs = RequestPackPurchase.objects.filter(
        status=RequestPackPurchase.STATUS_PENDING,
        created_at__range=window,
    ).exclude(provider_payment_id="")
    for purchase in packs:
        checked += 1
        try:
            remote_status = yookassa_gateway.fetch_payment(purchase.provider_payment_id)
        except Exception as exc:  # pragma: no cover - network/provider errors
            logger.warning(
                "resolve_stuck_payments: pack purchase %s check failed: %s",
                purchase.id, exc,
            )
            continue
        if remote_status == "succeeded":
            purchase.mark_succeeded_and_credit()
            credited += 1
            logger.info("resolve_stuck_payments: credited pack purchase %s", purchase.id)
        elif remote_status == "canceled":
            purchase.status = RequestPackPurchase.STATUS_CANCELED
            purchase.save(update_fields=["status", "updated_at"])
            canceled += 1

    payments = SubscriptionPayment.objects.filter(
        status=SubscriptionPayment.STATUS_PENDING,
        is_renewal=False,
        created_at__range=window,
    ).exclude(provider_payment_id="")
    for payment in payments:
        checked += 1
        try:
            remote_status, method_id = yookassa_gateway.fetch_payment_info(
                payment.provider_payment_id
            )
        except Exception as exc:  # pragma: no cover - network/provider errors
            logger.warning(
                "resolve_stuck_payments: subscription payment %s check failed: %s",
                payment.id, exc,
            )
            continue
        if remote_status == "succeeded":
            if method_id and not payment.provider_payment_method_id:
                payment.provider_payment_method_id = method_id
                payment.save(update_fields=["provider_payment_method_id", "updated_at"])
            payment.mark_succeeded_and_activate()
            credited += 1
            logger.info(
                "resolve_stuck_payments: activated subscription payment %s", payment.id
            )
        elif remote_status == "canceled":
            payment.status = SubscriptionPayment.STATUS_CANCELED
            payment.save(update_fields=["status", "updated_at"])
            canceled += 1

    if checked:
        logger.info(
            "resolve_stuck_payments: checked=%s credited=%s canceled=%s",
            checked, credited, canceled,
        )
    return {"checked": checked, "credited": credited, "canceled": canceled}
