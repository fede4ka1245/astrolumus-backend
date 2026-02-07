from ckeditor.fields import RichTextField
from django.db import models

from utils.multilinguality import get_default_language_value_admin


class Info(models.Model):
    whatsapp = models.URLField("whatsapp", max_length=255, blank=True, null=True)
    telegram_direct = models.URLField("telegram_direct", max_length=255, blank=True, null=True)
    telegram = models.URLField("telegram", max_length=255, blank=True, null=True)
    viber = models.CharField("viber", max_length=255, blank=True, null=True)
    youtube_alpha = models.URLField("youtube_alpha", max_length=255, blank=True, null=True)
    youtube_deep_sky = models.URLField("youtube_deep_sky", max_length=255, blank=True, null=True)
    email = models.EmailField("email", max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Информация"
        verbose_name_plural = "Информация"

    def __str__(self):
        return str(self.id)


class Documents(models.Model):
    code = models.CharField(verbose_name="Код документа", max_length=255,
                            help_text="Код для отличия документа (например, privacy)")
    title = models.JSONField(verbose_name="Название")
    description = models.JSONField(verbose_name="Содержимое")
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True, editable=True)
    published_at = models.DateTimeField("Опубликован", editable=True,
                                        help_text="Используется последняя опубликованная редакция")

    def __str__(self):
        return get_default_language_value_admin(self.title)

    class Meta:
        ordering = ["-published_at", "-updated_at"]
        verbose_name = "Документ"
        verbose_name_plural = "Документы"


class MobileAppsVersion(models.Model):
    class AppType(models.TextChoices):
        ANDROID = "android", "android"
        IOS = "ios", "ios"

    app_type = models.CharField(
        choices=AppType.choices, verbose_name="Статус", max_length=25,
        default=AppType.ANDROID
    )
    version = models.CharField(verbose_name="версия", max_length=155)
    link = models.URLField("Ссылка", max_length=255)
    description = RichTextField(blank=True, null=True)

    def __str__(self):
        return f"{self.app_type} {self.version}"

    class Meta:
        ordering = ["id"]
        verbose_name = "Мобильная версия"
        verbose_name_plural = "Мобильные версии"


class AppPartInfo(models.Model):
    code = models.CharField(verbose_name="Код раздела приложения", max_length=255,
                            help_text="Код для раздела приложения (например, scholar)")
    title = models.JSONField(verbose_name="Название")
    sub_title = models.JSONField(verbose_name="Подзаголовок")
    description = models.JSONField(verbose_name="Описание")
    main_description = models.JSONField(verbose_name="Главное описание")
    link = models.URLField("Ссылка")
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True, editable=True)
    is_active = models.BooleanField("Активный раздел", default=True)

    def __str__(self):
        return get_default_language_value_admin(self.title)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Информация о разделе приложения"
        verbose_name_plural = "Информация о разделе приложения"
