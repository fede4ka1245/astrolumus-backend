from django.urls import path

from .views import assistant_usage, assistant_consume, request_packs_list


urlpatterns = [
    path("usage/", assistant_usage, name="assistant_usage"),
    path("consume/", assistant_consume, name="assistant_consume"),
    path("packs/", request_packs_list, name="request_packs_list"),
]
