from ckeditor_uploader.fields import RichTextUploadingField
from colorfield.fields import ColorField
from django_minio_backend import MinioBackend
from django.db import models
from django.utils.html import strip_tags

from utils.multilinguality import get_default_language_value_admin


def upload_to(instance, filename):
    return 'images/alpha/{filename}'.format(filename=filename)


class BannerType(models.Model):
    title = models.CharField(verbose_name="Название", max_length=255)
    alias = models.CharField(verbose_name="Псевдоним", max_length=255)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "banner_types"
        verbose_name = "Раздел баннера"
        verbose_name_plural = "Разделы баннеров"


class Tag(models.Model):
    title = models.JSONField(verbose_name="Название")
    alias = models.CharField(verbose_name="Псевдоним", max_length=255)

    def __str__(self):
        return self.alias

    class Meta:
        db_table = "banner_tags"
        verbose_name = "Тег для баннеров"
        verbose_name_plural = "Теги для баннеров"


class BannerImage(models.Model):
    name = models.CharField(max_length=255)
    language_code = models.CharField(max_length=15)
    image = models.ImageField("Фото", storage=MinioBackend(bucket_name='alpha'), null=True, blank=True, upload_to=upload_to)
    image_link = models.URLField(null=True, blank=True)

    def __str__(self):
        return f'{self.name} ({self.language_code})'

    class Meta:
        db_table = "banner_images"
        verbose_name = "Изображение для баннеров"
        verbose_name_plural = "Изображения для баннеров"


class Banner(models.Model):
    title = models.JSONField(verbose_name="Название")
    color = ColorField(default="#FF0000")
    description = models.JSONField(verbose_name="Описание")
    date = models.DateField(auto_created=True)
    date_from = models.DateTimeField(null=True, blank=True)
    date_to = models.DateTimeField(null=True, blank=True)
    images = models.ManyToManyField(BannerImage, related_name="banner_images")
    video_link = models.JSONField(null=True, blank=True)
    banner_type = models.ManyToManyField(
        BannerType,
        related_name="banners",
        blank=True
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="banners",
        blank=True
    )

    def __str__(self):
        return strip_tags(get_default_language_value_admin(self.title) or "").strip()

    class Meta:
        db_table = "banners"
        verbose_name = "Баннер (устаревший)"
        verbose_name_plural = "Баннеры (устаревшие)"


