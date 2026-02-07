from colorfield.fields import ColorField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.db import models
from django.utils import timezone
from django_minio_backend import MinioBackend

from ckeditor_uploader.fields import RichTextUploadingField
from model_utils import Choices


def upload_to(instance, filename):
    return 'images/alpha/{filename}'.format(filename=filename)


class Banner(models.Model):
    title = models.CharField("Название", max_length=255)
    image = models.ImageField("Фото", storage=MinioBackend(bucket_name='alpha'), null=True, blank=True,
                              upload_to=upload_to)
    image_link = models.URLField("Ссылка на ресурс", null=True, blank=True)
    video_link = models.URLField("Ссылка на видео", null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"


class NotificationPage(models.Model):
    title = models.CharField("Заголовок", max_length=255)
    primary_info = RichTextUploadingField("Главная информация", blank=True, null=True)
    secondary_info = models.TextField("Второстепенная информация", blank=True, null=True)
    language_code = models.ForeignKey(
        settings.APP_LANGUAGE_MODEL,
        verbose_name="Язык",
        related_name='notification_pages',
        on_delete=models.RESTRICT
    )
    banner = models.ForeignKey(Banner, on_delete=models.SET_NULL, blank=True, null=True,
                               related_name="banner", verbose_name="Баннер")
    primary_banner = models.ForeignKey(Banner, on_delete=models.SET_NULL, blank=True, null=True,
                                       related_name="primary_banner", verbose_name="Главный баннер")
    secondary_banner = models.ForeignKey(Banner, on_delete=models.SET_NULL, blank=True, null=True,
                                         related_name="secondary_banner", verbose_name="Второстепенный баннер")
    interesting_tag = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название интересного тега")
    interesting_text = models.TextField("Интересный текст", blank=True, null=True)
    first_button_text = models.CharField(max_length=255, blank=True, null=True, verbose_name="Текст первой кнопки")
    first_button_link = models.URLField(blank=True, null=True, verbose_name="Ссылка первой кнопки")
    second_button_text = models.CharField(max_length=255, blank=True, null=True, verbose_name="Текст второй кнопки")
    second_button_link = models.URLField(blank=True, null=True, verbose_name="Ссылка второй кнопки")

    def __str__(self):
        return f'{self.title} ({self.language_code})'

    class Meta:
        verbose_name = "Страница уведомления"
        verbose_name_plural = "Страницы уведомлений"


class NotificationPageType(models.Model):
    title = models.CharField(verbose_name="Название", max_length=255)
    alias = models.CharField(verbose_name="Псевдоним", max_length=255)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Раздел страниц уведомлений"
        verbose_name_plural = "Разделы страниц уведомлений"


class Tag(models.Model):
    alias = models.CharField(verbose_name="Псевдоним", max_length=255)
    color = ColorField(default="#FFFFFF")
    title = models.JSONField(verbose_name="Название")

    def __str__(self):
        return self.alias

    class Meta:
        verbose_name = "Тег для страниц уведомлений"
        verbose_name_plural = "Теги для страниц уведомлений"


class NotificationPageGroup(models.Model):
    title = models.CharField(verbose_name="Название", max_length=255)
    page_types = models.ManyToManyField(NotificationPageType, blank=False, related_name="groups")
    pages = models.ManyToManyField(NotificationPage, blank=True, related_name="groups")
    tags = models.ManyToManyField(Tag, blank=True, related_name="groups")
    accessible_at = models.DateTimeField(verbose_name="Доступна с", default=timezone.now)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Группа страниц уведомлений"
        verbose_name_plural = "Группы страниц уведомлений"


class NotificationTask(models.Model):
    LEVELS = Choices('success', 'info', 'warning', 'error')
    level = models.CharField(choices=LEVELS, default=LEVELS.info, max_length=20)

    unread = models.BooleanField(default=True, blank=False)

    verb = models.JSONField()
    description = models.JSONField(blank=True, null=True)

    target_content_type = models.ForeignKey(
        ContentType,
        related_name='notification_tasks_target',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    target_object_id = models.CharField(max_length=255, blank=True, null=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')

    action_object_content_type = models.ForeignKey(ContentType, blank=True, null=True, on_delete=models.SET_NULL,
                                                   related_name='notification_tasks_action_object')
    action_object_object_id = models.CharField(max_length=255, blank=True, null=True)
    action_object = GenericForeignKey('action_object_content_type', 'action_object_object_id')

    timestamp = models.DateTimeField(default=timezone.now)

    public = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    emailed = models.BooleanField(default=False)
    sent = models.BooleanField(default=False, verbose_name="Отправлено")

    pages_group = models.ForeignKey(NotificationPageGroup, on_delete=models.RESTRICT, related_name="notification_tasks",
                                    verbose_name="Группа страниц уведомлений")

    data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ('-timestamp',)
        verbose_name = "Задача на отправку уведомления"
        verbose_name_plural = "Задачи на отправку уведомлений"
