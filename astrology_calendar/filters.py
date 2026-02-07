import django_filters.rest_framework as filters
from django_filters.widgets import RangeWidget

from .models import Event


class EventFilter(filters.FilterSet):
    event_date = filters.DateFromToRangeFilter(
        widget=RangeWidget(attrs={"type": "date"})
    )

    class Meta:
        model = Event
        fields = ("user_src", "access_type", "event_date")
