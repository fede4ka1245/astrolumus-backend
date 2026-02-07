from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated

from .filters import EventFilter
from .models import Event
from .serializers import EventSerializer


class EventViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = EventFilter

    def get_queryset(self):
        qs = super().get_queryset()

        if (
            hasattr(self.request.user, "profile") is False
            or self.request.user.profile.user_role
            == self.request.user.profile.UserRole.COMMON_USER
        ):
            qs = qs.filter(user_src=self.request.user)
        return qs
