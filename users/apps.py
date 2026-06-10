from django.utils.translation import gettext_lazy as _
from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'
    verbose_name = _("Authentication and Authorization")

    def ready(self):
        import users.signals  # noqa: F401
