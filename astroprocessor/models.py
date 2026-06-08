from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models

from utils.multilinguality import get_default_language_value_admin


class AstroprocessorType(models.Model):
    name = models.JSONField("Имя")

    def __str__(self):
        return get_default_language_value_admin(self.name)

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
        return f"{get_default_language_value_admin(self.type.name)} / {get_default_language_value_admin(self.name)}"

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
