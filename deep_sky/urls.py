from django.urls import path
from rest_framework import routers

from .views import (
    ConstellationViewSet,
    StarViewSet,
    StellarObjectTypeViewSet,
    YearViewSet, get_info,
)

router = routers.SimpleRouter()
router.register("years", YearViewSet)
router.register("constellations", ConstellationViewSet)
router.register("stars", StarViewSet)
router.register("Stellar-object-types", StellarObjectTypeViewSet)

urlpatterns = [
    path("info/", get_info, name="info"),
]

urlpatterns += router.urls
