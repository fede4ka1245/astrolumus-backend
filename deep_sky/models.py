from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models
from django.utils.html import strip_tags
from django_minio_backend import MinioBackend
from utils.multilinguality import get_default_language_value_admin


class Constellation(models.Model):
    title = models.JSONField(verbose_name="Название")
    description = models.JSONField(verbose_name="Описание", null=True, blank=True)

    def __str__(self):
        return strip_tags(get_default_language_value_admin(self.title) or "").strip()

    class Meta:
        db_table = "constellations"
        verbose_name = "Созвездие"
        verbose_name_plural = "Созвездия"


class StellarObjectType(models.Model):
    name = models.JSONField()
    comment = models.JSONField(verbose_name="Комментарий", null=True, blank=True)
    custom_id = models.PositiveIntegerField(default=0)

    def __str__(self):
        return strip_tags(get_default_language_value_admin(self.name) or "").strip()

    class Meta:
        db_table = "stellar_object_types"
        verbose_name = "Тип звездного объекта"
        verbose_name_plural = "Типы звездных объектов"


def upload_to(instance, filename):
    return 'images/deep_sky/{filename}'.format(filename=filename)


class Star(models.Model):
    custom_id = models.CharField(max_length=255, null=True, blank=True)
    title = models.JSONField(verbose_name="Название")
    area = models.JSONField(
        verbose_name="Область", null=True, blank=True
    )
    constellation = models.ForeignKey(
        Constellation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="constellation_stars",
    )
    comment = models.JSONField(verbose_name="Комментарий", null=True, blank=True)
    img = models.ImageField("Изображение", storage=MinioBackend(bucket_name='alpha'), upload_to=upload_to)
    stellar_object_type = models.ForeignKey(
        StellarObjectType,
        related_name="stellar_object_type_stars",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return strip_tags(get_default_language_value_admin(self.title) or "").strip()

    class Meta:
        db_table = "stars"
        verbose_name = "Объект"
        verbose_name_plural = "Объекты"


class Year(models.Model):
    class Signs(models.TextChoices):
        VIRGO = "virgo", "Дева"
        SCALES = "scales", "Весы"
        SCORPIO = "scorpion", "Скорпион"
        SAGITTARIUS = "Sagittarius", "Стрелец"
        CAPRICORN = "Capricorn", "Козерог"
        AQUARIUS = "Aquarius", "Водолей"
        FISH = "Fish", "Рыбы"
        ARIES = "Aries", "Овен"
        TAURUS = "Taurus", "Телец"
        TWINS = "Twins", "Близнецы"
        CRAYFISH = "Crayfish", "Рак"
        LION = "lion", "Лев"

    class Periods(models.TextChoices):
        TROPICAL = "Tropical", "Тропический"
        SIDEREAL = "Sidereal", "Сидерический"

    tropical_sign = models.CharField(
        max_length=255,
        verbose_name="Тропический знак",
        choices=Signs.choices,
        null=True,
        blank=True,
    )
    tropical_signdegree = models.PositiveIntegerField(default=0)
    tropical_minutes = models.PositiveIntegerField(default=0)
    sidereal_sign = models.CharField(
        max_length=255,
        verbose_name="Сидерический знак",
        choices=Signs.choices,
        null=True,
        blank=True,
    )
    sidereal_signdegree = models.PositiveIntegerField(default=0)
    sidereal_minutes = models.PositiveIntegerField(default=0)
    star = models.ForeignKey(
        Star, on_delete=models.SET_NULL, null=True, blank=True, related_name="years"
    )
    value = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "deep_sky_years"
        verbose_name = "Год"
        verbose_name_plural = "Года"


class Information(models.Model):
    title = models.JSONField(verbose_name="Название")
    description = models.JSONField(verbose_name="Описание")
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True, editable=True)
    published_at = models.DateTimeField("Опубликован", editable=True,
                                        help_text="Используется последняя опубликованная редакция")

    def __str__(self):
        return strip_tags(get_default_language_value_admin(self.title) or "").strip()

    class Meta:
        ordering = ["-published_at", "-updated_at"]
        verbose_name = "Информация"
        verbose_name_plural = "Информация"
