from django.apps import apps
from django.db.utils import ProgrammingError
from django.conf import settings

from utils.multilinguality import get_default_language_code


def get_default_app_language():
    """
    Lazily fetches the default app language object.
    This is deferred to avoid database queries at import time,
    which would break Django migrations.
    """
    try:
        return apps.get_model(settings.APP_LANGUAGE_MODEL).objects.get(
            code=get_default_language_code()
        )
    except ProgrammingError:
        # Database table doesn't exist yet (e.g., during migrations)
        return None
    except Exception:
        # AppLanguage doesn't exist, return None
        return None


# Legacy support - kept for backwards compatibility
# This is evaluated lazily now via callable_default
DEFAULT_APP_LANGUAGE_OBJECT = None
