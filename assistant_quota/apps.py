from django.apps import AppConfig


class AssistantQuotaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assistant_quota"
    verbose_name = "Ассистент: лимиты запросов"
