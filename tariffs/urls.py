from django.urls import path

from .views import payment_from_site, current_user_tariff, current_user_tariffs, public_tariffs, check_user_exist

urlpatterns = [
    path("payment-from-site/", payment_from_site, name="payment_from_site"),
    path("check-user-exist/", check_user_exist, name="payment_from_site"),
    path("current-user-tariff/", current_user_tariff, name="current_user_tariff"),
    path("current-user-tariffs/", current_user_tariffs, name="current_user_tariffs"),
    path("public/", public_tariffs, name="public_tariffs"),
]
