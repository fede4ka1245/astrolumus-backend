import django_filters
from notifications_ext.models import NotificationPage


class NotificationPageFilter(django_filters.FilterSet):
    language_code = django_filters.CharFilter(field_name="language_code__code", lookup_expr="exact")
    page_type = django_filters.CharFilter(field_name="groups__page_types__alias", lookup_expr="exact")

    class Meta:
        model = NotificationPage
        fields = ('language_code',)
