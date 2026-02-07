from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from astroprocessor.models import AstroprocessorData, SignPlanetConnection, PlanetHouseConnection, MasterHouseConnection
from astroprocessor.serializers import (AstroprocessorDataSerializer, SignPlanetConnectionSerializer,
                                        PlanetHouseConnectionSerializer, MasterHouseConnectionSerializer)

from utils.multilinguality import MultilingualityViewMixin


class AstroprocessorViewSet(
    MultilingualityViewMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    serializer_class = AstroprocessorDataSerializer
    pagination_class = None
    queryset = AstroprocessorData.objects.filter(is_public=True).select_related("type")
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("type", )


class SignPlanetConnectionView(
    MultilingualityViewMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    queryset = SignPlanetConnection.objects.all()
    serializer_class = SignPlanetConnectionSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('sign', in_=openapi.IN_QUERY, type=openapi.TYPE_NUMBER),
            openapi.Parameter('planet', in_=openapi.IN_QUERY, type=openapi.TYPE_NUMBER),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        sign_param = self.request.query_params.get('sign', None)
        if sign_param:
            self.queryset = self.queryset.filter(sign=sign_param)

        planet_param = self.request.query_params.get('planet', None)
        if planet_param:
            self.queryset = self.queryset.filter(planet=planet_param)

        return self.queryset


class PlanetHouseConnectionView(
    MultilingualityViewMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    queryset = PlanetHouseConnection.objects.all()
    serializer_class = PlanetHouseConnectionSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('house', in_=openapi.IN_QUERY, type=openapi.TYPE_NUMBER),
            openapi.Parameter('planet', in_=openapi.IN_QUERY, type=openapi.TYPE_NUMBER),
        ],
    )
    def get_queryset(self):
        house_param = self.request.query_params.get('house', None)
        if house_param:
            self.queryset = self.queryset.filter(house=house_param)

        planet_param = self.request.query_params.get('planet', None)
        if planet_param:
            self.queryset = self.queryset.filter(planet=planet_param)

        return self.queryset


class MasterHouseConnectionView(
    MultilingualityViewMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    queryset = MasterHouseConnection.objects.all()
    serializer_class = MasterHouseConnectionSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('house', in_=openapi.IN_QUERY, type=openapi.TYPE_NUMBER),
            openapi.Parameter('planet', in_=openapi.IN_QUERY, type=openapi.TYPE_NUMBER),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        house_param = self.request.query_params.get('house', None)
        if house_param:
            self.queryset = self.queryset.filter(house=house_param)

        planet_param = self.request.query_params.get('planet', None)
        if planet_param:
            self.queryset = self.queryset.filter(planet=planet_param)

        return self.queryset
