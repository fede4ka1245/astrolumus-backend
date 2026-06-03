from django.urls import path, re_path
from rest_framework import routers

from .views import AstroprocessorViewSet, SignPlanetConnectionView, PlanetHouseConnectionView, MasterHouseConnectionView
from .definitions_views import DefinitionGroupListView, DefinitionGroupDetailView, DefinitionItemDetailView

router = routers.SimpleRouter()
router.register("astroproccesor", AstroprocessorViewSet)
router.register("astroprocessor", AstroprocessorViewSet)
router.register("sign-planet-connection", SignPlanetConnectionView)
router.register("planet-house-connection", PlanetHouseConnectionView)
router.register("master-house-connection", MasterHouseConnectionView)

urlpatterns = router.urls + [
    path("definitions/groups/", DefinitionGroupListView.as_view(), name="definitions-groups"),
    path("definitions/groups/<slug:slug>/", DefinitionGroupDetailView.as_view(), name="definitions-group-detail"),
    path("definitions/groups/<slug:slug>/<slug:item_slug>/", DefinitionItemDetailView.as_view(), name="definitions-item-detail"),
]
