import django_filters
from django.db.models.functions import Lower
from django_filters import OrderingFilter
from django_filters.constants import EMPTY_VALUES

from horoscope.models import MyHoroscope


class CaseInsensitiveOrderingFilter(OrderingFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        def get_lower_order(param):
            if 'name' in param:
                if param.startswith("-"):
                    return Lower(self.get_ordering_value(param[1:])).desc()
                else:
                    return Lower(self.get_ordering_value(param))

            return self.get_ordering_value(param)

        ordering = [get_lower_order(param) for param in value]
        return qs.order_by(*ordering)


class MyHoroscopeFilter(django_filters.FilterSet):
    ordering = CaseInsensitiveOrderingFilter(
        # tuple-mapping retains order
        fields=(
            ('name', 'name'),
            ('id', 'id'),
        ),
    )

    class Meta:
        model = MyHoroscope
        fields = {
            'name': ['exact', 'icontains'],
            'city': ['exact', 'icontains'],
        }
