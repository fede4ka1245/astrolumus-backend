from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from notifications.models import Notification
from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from notifications_ext.models import NotificationPage
from notifications_ext.serializers import NotificationSerializer, NotificationPageSerializer
from notifications_ext.filters import NotificationPageFilter

User = get_user_model()


class NotificationsPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificationsViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationsPagination
    queryset = Notification.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("unread", )

    def perform_destroy(self, instance):
        instance.deleted = True
        instance.save()

    def destroy(self, request, *args, **kwargs):
        try:
            instance = request.user.notifications.filter(deleted=False).get(pk=self.get_object().pk)
        except Notification.DoesNotExist:
            raise NotFound()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, format=None):
        notifications = request.user.notifications.filter(deleted=False)
        language_code = self.request.query_params.get("language_code")
        queryset = self.filter_queryset(notifications)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(notifications, many=True, context={'request': request})
        response = Response(serializer.data, status=status.HTTP_200_OK)
        return response

    @action(methods=['post'], detail=True, url_path="mark-as-read", permission_classes=[IsAuthenticated, ])
    def mark_as_read(self, request, *args, **kwargs):
        notification = get_object_or_404(
            Notification, recipient=request.user, id=self.get_object().pk, deleted=False)
        notification.mark_as_read()

        serializer = self.get_serializer(notification, many=False, context={'request': request})
        response = Response(serializer.data, status=status.HTTP_200_OK)
        return response

    @action(methods=['post'], detail=True, url_path="mark-as-unread", permission_classes=[IsAuthenticated, ])
    def mark_as_unread(self, request, *args, **kwargs):
        notification = get_object_or_404(
            Notification, recipient=request.user, id=self.get_object().pk, deleted=False)
        notification.mark_as_unread()

        serializer = self.get_serializer(notification, many=False, context={'request': request})
        response = Response(serializer.data, status=status.HTTP_200_OK)
        return response

    @action(methods=['post'], detail=False, url_path="mark-all-as-read", permission_classes=[IsAuthenticated, ])
    def mark_all_as_read(self, request, *args, **kwargs):
        notifications = request.user.notifications.all()
        notifications.mark_all_as_read()

        return self.list(request, *args, **kwargs)


class NotificationPageViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    permission_classes = (IsAuthenticated,)
    queryset = NotificationPage.objects.all()
    serializer_class = NotificationPageSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = NotificationPageFilter

    def get_queryset(self):
        return self.queryset.filter(
            groups__isnull=False,
            groups__accessible_at__lte=timezone.now()
        ).select_related('banner', 'primary_banner', 'secondary_banner').order_by('-groups__accessible_at')
