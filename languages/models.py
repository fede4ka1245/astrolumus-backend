from users.models import AppLanguage


class AppLanguageProxy(AppLanguage):
    class Meta:
        proxy = True
        app_label = "languages"
        verbose_name = "Язык"
        verbose_name_plural = "Языки приложения"
