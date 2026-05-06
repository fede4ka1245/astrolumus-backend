"""
Context processors для Django templates.
"""

import logging

logger = logging.getLogger(__name__)


def tolgee_languages(request):
    """
    Добавляет список языков из Tolgee и текущий язык пользователя
    в контекст шаблонов.
    """
    languages = []
    current_language = getattr(request.user, "language", "ru") if hasattr(request, "user") and request.user.is_authenticated else "ru"

    # Нормализуем код языка (en-us → en)
    current_language = current_language.split("-")[0].lower()

    try:
        from django.apps import apps
        from django.conf import settings

        model_path = getattr(settings, "APP_LANGUAGE_MODEL", None)
        if model_path:
            AppLanguage = apps.get_model(model_path)
            languages = [
                {"code": lang.code, "name": lang.name}
                for lang in AppLanguage.objects.filter(enabled=True)
            ]
    except Exception as e:
        logger.warning("Failed to fetch languages from AppLanguage model: %s", e)

    if not languages:
        languages = [
            {"code": "ru", "name": "Русский"},
            {"code": "en", "name": "English"},
        ]

    return {
        "tolgee_languages": languages,
        "current_language": current_language,
    }
