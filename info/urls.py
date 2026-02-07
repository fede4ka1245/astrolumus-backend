from django.urls import path, re_path

from .views import get_info, get_document, get_mobile_app_version, get_app_part_info

urlpatterns = [
    path("info/", get_info, name="info"),
    re_path("documents/(?P<code>\w{0,255})/", get_document, name="documents"),
    re_path("app-part-info/(?P<code>\w{0,255})/", get_app_part_info, name="app_part_info"),
    re_path("mobile-app-verion/(?P<app_type>android|ios)/", get_mobile_app_version, name="mobile_app_version"),
]

