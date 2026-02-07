import django_filters

from django.contrib.auth import get_user_model
from django.db.models import Q

from users.models import Subscription

User = get_user_model()


class UserFilter(django_filters.FilterSet):
    ordering = django_filters.OrderingFilter(
        fields=(
            ('id', 'id'),
        ),
    )

    query = django_filters.CharFilter(method='q_filter', label="Search")

    membership__topic__not_joint = django_filters.NumberFilter(label="user not in topic",
                                                               field_name='membership__topic',
                                                               exclude=True)

    subscribers_for = django_filters.NumberFilter(
        field_name='subscribers_for', method='get_subscribers_for', label="Get subscribers for")

    def get_subscribers_for(self, queryset, field_name, value):
        # subscribers = Subscription.objects.filter(date_of_collection__month=2)
        return queryset.filter(user_src_subscriptions__user_dst=value,
                               user_src_subscriptions__status=Subscription.Statuses.ACCEPTED.value)

    def q_filter(self, queryset, name, value):

        q_objects = Q(Q(first_name__icontains=value) |
                      Q(patronymic__icontains=value) |
                      Q(last_name__icontains=value))
        try:
            user_id = int(value)
            q_objects |= Q(id=user_id)
        except (TypeError, ValueError):
            pass

        if self.request.user.is_authenticated and (
                self.request.user.is_staff or self.request.user.is_superuser):
            q_objects |= Q(email__icontains=value)

        if self.request.user.is_authenticated:
            # exclude myself
            queryset = queryset.exclude(pk=self.request.user.pk)

        return queryset.filter(
            q_objects
        )

    class Meta:
        model = User
        fields = ['query', 'subscribers_for', 'membership__topic__not_joint',
                  'membership__status',
                  'membership__user_status', 'membership__topic']


class SubscriptionFilter(django_filters.FilterSet):
    # ordering = django_filters.OrderingFilter(
    #     fields=(
    #         ('id', 'id'),
    #     ),
    # )

    query = django_filters.CharFilter(method='q_filter', label="Search")

    def q_filter(self, queryset, name, value):

        q_objects = Q(Q(user_dst__first_name__icontains=value) |
                      Q(user_dst__patronymic__icontains=value) |
                      Q(user_dst__last_name__icontains=value) |
                      Q(user_src__first_name__icontains=value) |
                      Q(user_src__patronymic__icontains=value) |
                      Q(user_src__last_name__icontains=value)
                      )
        try:
            user_id = int(value)
            q_objects |= Q(user_dst_id=user_id)
            q_objects |= Q(user_src_id=user_id)
        except (TypeError, ValueError):
            pass

        if self.request.user.is_authenticated and (
                self.request.user.is_staff or self.request.user.is_superuser):
            q_objects |= Q(user_dst__email__icontains=value)
            q_objects |= Q(user_src__email__icontains=value)

        # if self.request.user.is_authenticated:
        #     # exclude myself
        #     queryset = queryset.exclude(pk=self.request.user.pk)

        return queryset.filter(
            q_objects
        )

    class Meta:
        model = Subscription
        fields = ['query', "status", "user_dst", "user_src"]
