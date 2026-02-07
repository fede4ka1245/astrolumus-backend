from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import SimpleRouter

from .views import (
    BepaidCallBackView,
    OrderViewset,
    PaymentSettingsViewSet,
    StripeCallbackView,
)

router = SimpleRouter()
router.register("orders", OrderViewset)
router.register("settings", PaymentSettingsViewSet, basename="payment-settings")

urlpatterns = [
    path(
        "stripe-callback/",
        csrf_exempt(StripeCallbackView.as_view()),
        name="stripe-callback",
    ),
    path(
        "bepaid-callback/<uuid:pk>",
        csrf_exempt(BepaidCallBackView.as_view()),
        name="bepaid-callback",
    ),
]
urlpatterns += router.urls
