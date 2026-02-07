from django.urls import path
from rest_framework import routers

from users.views import (
    BlockedUserViewSet,
    FriendsView,
    GenerateLoginCodeAPIView,
    RegistrationAPIViewSet,
    SubscriptionViewSet,
    UserFileViewSet,
    UserProfileOpenInfoViewSet,
    UserProfileView,
    UserView,
    ValidateLoginCodeAPIView, UserRightsAPIView, AppLanguagesView
)

router = routers.SimpleRouter()
router.register("users", UserView)
router.register("user-files", UserFileViewSet)
router.register("user-profile", UserProfileView)
router.register(
    "user-profile-open-info", UserProfileOpenInfoViewSet, basename="user-profile-open-info"
)
router.register("subscriptions", SubscriptionViewSet)
router.register("blocked-users", BlockedUserViewSet)
router.register("friends", FriendsView)
router.register("app-languages", AppLanguagesView)

urlpatterns = [
    path("registration/", RegistrationAPIViewSet.as_view({"post": "create"}), name="registration"),
    path(
        "generate-login-code/",
        GenerateLoginCodeAPIView.as_view(),
        name="generate_reg_code",
    ),
    path(
        "validate-login-code/",
        ValidateLoginCodeAPIView.as_view(),
        name="validate_reg_code",
    ),
    path(
        "current-user-rights/",
        UserRightsAPIView.as_view(),
        name="user_rights",
    ),
]
urlpatterns += router.urls
