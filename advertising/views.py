from rest_framework import mixins, viewsets
from django_filters.rest_framework import DjangoFilterBackend

from .models import Banner
from .serializers import BannerSerializer
from .filters import BannerFilterV2

from utils.multilinguality import MultilingualityViewMixin


class BannerViewSet(
    MultilingualityViewMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = ()
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("banner_type",)


class BannerViewSetV2(
    MultilingualityViewMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = ()
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = BannerFilterV2
