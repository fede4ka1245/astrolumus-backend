import json

import pytest
from django.urls import reverse

from payments.models import Order


@pytest.mark.django_db
def test_bepaid_callback_expired_sets_order_failed(client, django_user_model):
    user = django_user_model.objects.get(first_name="user")
    order = Order.objects.create(
        user=user,
        status=Order.PaymentStatuses.PENDING,
        amount=10,
        currency="BYN",
        pay_system=Order.PaymentSystems.BEPAID,
    )

    url = reverse("payments:bepaid-callback", kwargs={"pk": order.pk})
    payload = {"status": "expired", "message": "Token is expired.", "customer": None}
    client.post(url, data=json.dumps(payload), content_type="application/json")

    order.refresh_from_db()
    assert order.status == Order.PaymentStatuses.FAILED

