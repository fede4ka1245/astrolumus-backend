from django.urls import include, path
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from rest_framework.routers import SimpleRouter

router = SimpleRouter()

router.register('devices', FCMDeviceAuthorizedViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
