from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models
from django.utils.html import strip_tags

from utils.multilinguality import get_default_language_value_admin


class AstroprocessorType(models.Model):
    name = models.JSONField("Имя")

    def __str__(self):
        return strip_tags(get_default_language_value_admin(self.name) or "").strip()

    class Meta:
        verbose_name = "Тип данных астропроцессора"
        verbose_name_plural = "Тип данных астропроцессора"


class AstroprocessorData(models.Model):
    internal_id = models.IntegerField("Внутренний id")
    type = models.ForeignKey(AstroprocessorType, verbose_name="Тип", on_delete=models.CASCADE)
    is_public = models.BooleanField("Публичная запись", default=False)
    name = models.JSONField("Имя")
    description = models.JSONField("Описание", blank=True, null=True)

    def __str__(self):
        type_name = strip_tags(get_default_language_value_admin(self.type.name) or "").strip()
        name = strip_tags(get_default_language_value_admin(self.name) or "").strip()
        return f"{type_name} / {name}"

    class Meta:
        unique_together = ["internal_id", "type"]
        verbose_name = "Данные астропроцессора"
        verbose_name_plural = "Данные астропроцессора"


class SignPlanetConnection(models.Model):
    name = models.JSONField(verbose_name="Имя")
    planet = models.IntegerField("Планета")
    sign = models.IntegerField("Знак")
    description = models.JSONField(verbose_name="Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Планета в знаке"
        verbose_name_plural = "Планеты в знаке"


class PlanetHouseConnection(models.Model):
    name = models.JSONField("Имя")
    planet = models.IntegerField("Планета")
    house = models.IntegerField("Дом")
    description = models.JSONField("Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Планета в доме"
        verbose_name_plural = "Планеты в доме"


class MasterHouseConnection(models.Model):
    name = models.JSONField("Имя")
    master_house = models.IntegerField("Управитель дома")
    at_house = models.IntegerField("В доме")
    description = models.JSONField("Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Управитель"
        verbose_name_plural = "Управитель"


# --- Proxy models for separate admin sections ---

class ZodiacSignData(AstroprocessorData):
    class Meta:
        proxy = True
        verbose_name = "Знак Зодиака"
        verbose_name_plural = "Знаки Зодиака"


class NakshatraData(AstroprocessorData):
    class Meta:
        proxy = True
        verbose_name = "Накшатра"
        verbose_name_plural = "Накшатры"


class PlanetData(AstroprocessorData):
    class Meta:
        proxy = True
        verbose_name = "Планета / лагна / упаграха"
        verbose_name_plural = "Планеты, дополнительные лагны, упаграхи"


class KarakaData(AstroprocessorData):
    class Meta:
        proxy = True
        verbose_name = "Карака"
        verbose_name_plural = "Караки"


class ArudhaData(AstroprocessorData):
    class Meta:
        proxy = True
        verbose_name = "Арудха"
        verbose_name_plural = "Арудхи"


class HouseData(AstroprocessorData):
    class Meta:
        proxy = True
        verbose_name = "Дом"
        verbose_name_plural = "Дома"


class PlanetInSignData(AstroprocessorData):
    class Meta:
        proxy = True
        verbose_name = "Планета в знаке (данные)"
        verbose_name_plural = "Планета в знаке"


class HouseTypeData(AstroprocessorData):
    class Meta:
        proxy = True
        verbose_name = "Дом (тип)"
        verbose_name_plural = "Дом"
