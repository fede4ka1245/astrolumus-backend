from django.urls import path, re_path
from rest_framework import routers

from .views import AstroprocessorViewSet, SignPlanetConnectionView, PlanetHouseConnectionView, MasterHouseConnectionView

router = routers.SimpleRouter()
router.register("astroproccesor", AstroprocessorViewSet)
router.register("astroprocessor", AstroprocessorViewSet)
router.register("sign-planet-connection", SignPlanetConnectionView)
router.register("planet-house-connection", PlanetHouseConnectionView)
router.register("master-house-connection", MasterHouseConnectionView)

urlpatterns = router.urls
