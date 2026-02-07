from django.urls import path
from rest_framework import routers

from .views import (
    SettingsView,
    HoroscopeCacheViewSet,
    MyHoroscopeViewSet
)

router = routers.SimpleRouter()
router.register("horoscopes", HoroscopeCacheViewSet)
router.register("my-horoscopes", MyHoroscopeViewSet)

urlpatterns = [
    path("settings/", SettingsView.as_view()),
] + router.urls
