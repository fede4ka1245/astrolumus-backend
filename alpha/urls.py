import debug_toolbar

from django.contrib import admin
from django.urls import include, path, re_path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from alpha.views import ping, j108_proxy

API_PREFIX = "api/v<int:version>"


schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)


urlpatterns = [
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    # non-API paths
    path("ping/", ping, name="ping"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("admin/", admin.site.urls),
    # path("rosetta/", include("rosetta.urls")),  # Replaced by Tolgee i18n Studio
    # API paths. Please prepend with API versioning prefix
    path("jwt/", include("alpha.jwt_urls", namespace="jwt")),
    path("users/", include(("users.urls", "users"), namespace="users")),
    path("payments/", include(("payments.urls", "users"), namespace="payments")),
    path("horoscope/", include(("horoscope.urls", "horoscope"), namespace="horoscope")),
    path("link/", include(("link.urls", "link"), namespace="link")),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("bootcamp/", include(("bootcamp.urls", "bootcamp"), namespace="bootcamp")),
    path(
        "astrology_calendar/",
        include(
            ("astrology_calendar.urls", "astrology_calendar"),
            namespace="astrology_calendar",
        ),
    ),
    path("favorite/", include(("favorite.urls", "favorite"), namespace="favorite")),
    path("forum/", include(("astrology_forum.urls", "forum"), namespace="forum")),
    path("deep_sky/", include(("deep_sky.urls", "deep_sky"), namespace="deep_sky")),
    path(
        "notifications/",
        include(("notifications_ext.urls", "notifications"), namespace="notifications"),
    ),
    path(
        "advertising/",
        include(("advertising.urls", "advertising"), namespace="advertising"),
    ),
    path("info/", include(("info.urls", "info"), namespace="info")),
    path("tariffs/", include(("tariffs.urls", "tariffs"), namespace="tariffs")),
    path(
        "astroprocessor/",
        include(("astroprocessor.urls", "astroprocessor"), namespace="astroprocessor"),
    ),
    path("fcm/", include(("FCM.urls", "FCM"), namespace="FCM")),
    # Proxy to j108.net API (requires authentication)
    path("api/j108/", j108_proxy, name="j108_proxy_root"),
    path("api/j108/<path:path>", j108_proxy, name="j108_proxy"),
]


# if settings.DEBUG:
# https://github.com/jazzband/django-debug-toolbar/issues/1035 TODO

urlpatterns.extend([path("__debug__/", include(debug_toolbar.urls))])

# add static files for gunicorn and uvicorn in debug mode
urlpatterns += staticfiles_urlpatterns()

