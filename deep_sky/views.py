from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Constellation, Star, StellarObjectType, Year, Information
from .serializers import (
    ConstellationSerializer,
    StarListSerializer,
    StarSerializer,
    StellarObjectTypeSerializer,
    YearSerializer,
)

from utils.multilinguality import get_language_value, get_default_language_code, MultilingualityViewMixin


class YearViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = ()
    queryset = Year.objects.all()
    serializer_class = YearSerializer


class ConstellationViewSet(
    MultilingualityViewMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = ()
    queryset = Constellation.objects.all()
    serializer_class = ConstellationSerializer


class StarViewSet(
    MultilingualityViewMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = ()
    queryset = Star.objects.all().prefetch_related("years")
    serializer_class = StarSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("years__value",)

    def list(self, request, *args, **kwargs):
        self.serializer_class = StarListSerializer
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        self.serializer_class = StarSerializer
        return Response(serializer.data)


class StellarObjectTypeViewSet(
    MultilingualityViewMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = ()
    queryset = StellarObjectType.objects.all()
    serializer_class = StellarObjectTypeSerializer


@api_view(['GET'])
def get_info(request):
    info = Information.objects.filter(published_at__isnull=False).last()
    if info:
        language_code = request.GET.get("language_code", get_default_language_code())
        return Response(
            {
                "title": get_language_value(info.title, language_code),
                "description": get_language_value(info.description, language_code)
            }
        )
    else:
        return Response(status=status.HTTP_204_NO_CONTENT)
