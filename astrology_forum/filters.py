import django_filters
from django.core.exceptions import FieldError
from django.db.models import Q

from astrology_forum.models import Topic, Membership

TYPE_FILTER_CHOICES = (
    ('favorite', 'Favorite'),
)


class CustomTopicOrderingFilter(django_filters.OrderingFilter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra['choices'] += [
            ('popular', 'Popular'),
            ('-popular', 'Popular (descending)'),
        ]

    def filter(self, qs, value):
        # OrderingFilter is CSV-based, so `value` is a list
        if value and any(v in ['popular', '-popular'] for v in value):
            # number of comments division by date
            try:
                return qs.order_by(
                    f'{value[0]}_weight')
            except FieldError:
                # search have own "rank" FIXME fix this?
                return qs

        return super().filter(qs, value)


class TopicFilter(django_filters.FilterSet):
    type = django_filters.ChoiceFilter(
        label="type",
        choices=TYPE_FILTER_CHOICES,
        method="type__filter",
    )
    not_published = django_filters.BooleanFilter(field_name='published_at', lookup_expr='isnull')

    category = django_filters.NumberFilter(
        label="Category with child cats",
        method="category_filter",
    )

    def category_filter(self, queryset, name, value):
        if value:
            return queryset.filter(Q(category=value) | Q(category__parent=value))
        return queryset

    membership_user = django_filters.NumberFilter(
        label="Membership user",
        method="membership_user__filter",
    )

    def membership_user__filter(self, queryset, name, value):
        if value:
            return queryset.filter(membership__user_id__in=(int(value),), membership__status=Membership.Status.ACCEPTED,
                                   membership__user_status=Membership.UserStatus.ACCEPTED)
        return queryset

    ordering = CustomTopicOrderingFilter(
        fields=(
            ('user', 'user'),
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
            ('published_at', 'published_at'),
            ('category', 'category'),
        )
    )

    def type__filter(self, qs, name, value):
        if self.request.user.is_authenticated:
            if value == 'favorite':
                qs = qs.filter(favorites__author=self.request.user)
        return qs

    class Meta:
        model = Topic
        fields = ("user", "status")


class MembershipFilter(django_filters.FilterSet):
    user_query = django_filters.CharFilter(method='q_filter', label="Search")

    def q_filter(self, queryset, name, value):
        # similar users.filters.UserFilter
        q_objects = Q(Q(user__first_name__icontains=value) |
                      Q(user__patronymic__icontains=value) |
                      Q(user__last_name__icontains=value))
        try:
            user_id = int(value)
            q_objects |= Q(user_id=user_id)
        except (TypeError, ValueError):
            pass

        if self.request.user.is_authenticated and (
                self.request.user.is_staff or self.request.user.is_superuser):
            q_objects |= Q(user__email__icontains=value)

        if self.request.user.is_authenticated:
            # exclude myself
            queryset = queryset.exclude(pk=self.request.user.pk)

        return queryset.filter(
            q_objects
        )

    class Meta:
        model = Membership
        fields = {
            "topic": ["exact"],
            "user": ["exact"],
            "user_status": ["exact"],
            "status": ["exact"],
            # "user__first_name": ["exact", "icontains"],
            # "user__patronymic": ["exact", "icontains"],
            # "user__last_name": ["exact", "icontains"]
        }
