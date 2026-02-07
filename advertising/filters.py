import django_filters
from advertising.models import Banner


class BannerFilterV2(django_filters.FilterSet):
    banner_type = django_filters.CharFilter(field_name="banner_type__alias", lookup_expr="exact")

    class Meta:
        model = Banner
        fields = ("banner_type", )
