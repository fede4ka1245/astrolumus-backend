from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


app_name = 'rest_framework_simplejwt'

urlpatterns = [
    # path('token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    # path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token-verify'),
]
