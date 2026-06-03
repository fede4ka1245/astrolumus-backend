from django.urls import path

from . import views


urlpatterns = [
    path("spreads/", views.spread_list, name="tarot_spread_list"),
    path("cards/", views.card_list, name="tarot_card_list"),
    path("readings/", views.reading_create, name="tarot_reading_create"),
    path("readings/list/", views.reading_list, name="tarot_reading_list"),
    path("usage/", views.tarot_usage, name="tarot_usage"),
]
