from django.contrib.admin.apps import AdminConfig


class AlphaAdminConfig(AdminConfig):
    default_site = 'alpha.admin.AlphaAdminSite'
