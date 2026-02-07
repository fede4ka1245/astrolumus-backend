import time
from types import SimpleNamespace

import pytest
from django.urls import reverse

from payments.models import Order, PaymentRecord, RecurringSubscription
from tariffs.models import Tariff


@pytest.mark.django_db
def test_stripe_invoice_paid_webhook_is_idempotent(client, django_user_model, monkeypatch, settings):
    settings.STRIPE_WEBHOOK_SECRET = "whsec_test"

    user = django_user_model.objects.get(first_name="user")
    tariff = Tariff.objects.create(title={"ru": "Тестовый тариф"}, code="test_tariff")
    order = Order.objects.create(
        user=user,
        status=Order.PaymentStatuses.PENDING,
        amount=10,
        currency="USD",
        pay_system=Order.PaymentSystems.STRIPE,
    )
    RecurringSubscription.objects.create(
        user=user,
        tariff=tariff,
        order=order,
        payment_system=RecurringSubscription.PaymentSystems.STRIPE,
        subscription_id="sub_1",
        customer_id="cus_1",
        status=RecurringSubscription.SubscriptionStatuses.ACTIVE,
        amount=10,
        currency="USD",
    )

    now = int(time.time())
    event = {
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_1",
                "subscription": "sub_1",
                "customer": "cus_1",
                "amount_paid": 1000,  # cents
                "currency": "usd",
            }
        },
    }

    import payments.views as payment_views

    monkeypatch.setattr(
        payment_views.stripe.Webhook,
        "construct_event",
        lambda payload, sig_header, endpoint_secret: event,
    )
    monkeypatch.setattr(
        payment_views.stripe.Customer,
        "retrieve",
        lambda customer_id: SimpleNamespace(email="payer@example.com"),
    )
    monkeypatch.setattr(
        payment_views.stripe.Subscription,
        "retrieve",
        lambda subscription_id: SimpleNamespace(
            current_period_start=now,
            current_period_end=now + 3600,
        ),
    )

    activate_calls = {"n": 0}

    def fake_delay(*args, **kwargs):
        activate_calls["n"] += 1

    monkeypatch.setattr(payment_views.activate_user_tariff, "delay", fake_delay)

    url = reverse("payments:stripe-callback")
    client.post(url, data="{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="t")
    client.post(url, data="{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="t")

    assert (
        PaymentRecord.objects.filter(
            payment_system=PaymentRecord.PaymentSystems.STRIPE,
            payment_id="in_1",
        ).count()
        == 1
    )
    assert activate_calls["n"] == 1

