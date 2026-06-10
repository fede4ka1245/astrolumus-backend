from django.urls import path

from .views import (
    assistant_consume,
    assistant_usage,
    pack_purchase_status,
    purchase_pack,
    purchase_subscription,
    request_packs_list,
    subscription_payment_status,
    subscription_plans_list,
    subscription_status_view,
    yookassa_webhook,
)


urlpatterns = [
    path("usage/", assistant_usage, name="assistant_usage"),
    path("consume/", assistant_consume, name="assistant_consume"),
    path("packs/", request_packs_list, name="request_packs_list"),
    path("packs/<slug:code>/purchase/", purchase_pack, name="request_pack_purchase"),
    path("packs/purchases/<int:purchase_id>/status/", pack_purchase_status, name="request_pack_purchase_status"),
    path("subscriptions/plans/", subscription_plans_list, name="subscription_plans_list"),
    path("subscriptions/status/", subscription_status_view, name="subscription_status"),
    path("subscriptions/<slug:code>/purchase/", purchase_subscription, name="subscription_purchase"),
    path("subscriptions/payments/<int:payment_id>/status/", subscription_payment_status, name="subscription_payment_status"),
    path("yookassa/webhook/", yookassa_webhook, name="yookassa_webhook"),
]
