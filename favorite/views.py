from rest_framework.mixins import CreateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Favorite
from .serializers import FavoriteSerializer


class FavoriteViewSet(CreateModelMixin, DestroyModelMixin, ReadOnlyModelViewSet):
    queryset = Favorite.objects.order_by("-created_at").prefetch_related("author__delivery_address"). \
        prefetch_related('content_object')
    lookup_url_kwarg = "id"
    serializer_class = FavoriteSerializer
    permission_classes = (
        IsAuthenticatedOrReadOnly
    )

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_anonymous:
            qs = qs.none()
        elif not user.is_staff and not user.is_superuser:
            qs = qs.filter(author=user)
        return qs
