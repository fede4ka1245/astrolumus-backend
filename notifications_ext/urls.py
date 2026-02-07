from django.urls import path, re_path
from rest_framework import routers

from .views import NotificationsViewSet, NotificationPageViewSet
from notifications.views import live_unread_notification_count, live_all_notification_count

router = routers.SimpleRouter()
router.register("notifications", NotificationsViewSet)
router.register("notification-page", NotificationPageViewSet)

urlpatterns = [
    re_path(r'^unread_count/$', live_unread_notification_count,
            name='live_unread_notification_count'),
    re_path(r'^all_count/$', live_all_notification_count, name='live_all_notification_count'),
]

urlpatterns += router.urls
