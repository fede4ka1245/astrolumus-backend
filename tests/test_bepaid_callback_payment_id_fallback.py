import json

import pytest
from django.urls import reverse

from payments.models import Order, PaymentRecord


@pytest.mark.django_db
def test_bepaid_callback_creates_record_even_without_uid(client, django_user_model):
    user = django_user_model.objects.get(first_name="user")
    order = Order.objects.create(
        user=user,
        status=Order.PaymentStatuses.PENDING,
        amount=10,
        currency="RUB",
        pay_system=Order.PaymentSystems.BEPAID,
    )

    url = reverse("payments:bepaid-callback", kwargs={"pk": order.pk})
    payload = {
        "status": "successful",
        "last_transaction": {
            "status": "successful",
            "amount": 1000,
            "currency": "RUB",
        },
        "customer": None,
        # Intentionally no uid/token here
    }
    client.post(url, data=json.dumps(payload), content_type="application/json")

    assert PaymentRecord.objects.filter(
        payment_system=PaymentRecord.PaymentSystems.BEPAID,
        order=order,
        status=PaymentRecord.PaymentStatuses.SUCCESS,
    ).count() == 1
