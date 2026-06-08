from django.contrib import admin
from django.utils.html import mark_safe

from astroprocessor.models import (AstroprocessorData, AstroprocessorType,
                                   SignPlanetConnection, PlanetHouseConnection, MasterHouseConnection)

from utils.multilinguality import get_default_language_value_admin, LocalizedModelAdmin


@admin.register(AstroprocessorData)
class AstroprocessorDataAdmin(LocalizedModelAdmin):
    @staticmethod
    def description_html(obj):
        return mark_safe(get_default_language_value_admin(obj.description))

    search_fields = ("internal_id", "name")
    localized_fields = ("name", "description")
    list_display = ("id", "is_public", "internal_id", "type", "default_localized_name", "description_html")
    list_filter = ("type__name", )


@admin.register(AstroprocessorType)
class AstroprocessorTypeAdmin(LocalizedModelAdmin):
    search_fields = ("id", "name")
    localized_fields = ("name", )
    list_display = ("default_localized_name", )


@admin.register(SignPlanetConnection)
class SignPlanetConnectionAdmin(LocalizedModelAdmin):

    @staticmethod
    def description_html(obj):
        return mark_safe(get_default_language_value_admin(obj.description))

    search_fields = ["planet", "sign"]
    localized_fields = ("name", "description")
    list_display = ["id", "default_localized_name", "planet", "sign", "description_html"]


@admin.register(PlanetHouseConnection)
class PlanetHouseConnectionAdmin(LocalizedModelAdmin):

    @staticmethod
    def description_html(obj):
        return mark_safe(get_default_language_value_admin(obj.description))

    search_fields = ["planet", "house"]
    localized_fields = ("name", "description")
    list_display = ["id", "default_localized_name", "planet", "house", "description_html"]


@admin.register(MasterHouseConnection)
class MasterHouseConnectionAdmin(LocalizedModelAdmin):

    @staticmethod
    def description_html(obj):
        return mark_safe(get_default_language_value_admin(obj.description))

    search_fields = ["master_house", "at_house"]
    localized_fields = ("name", "description")
    list_display = ["id", "default_localized_name", "master_house", "at_house", "description_html"]
    list_filter = ["master_house", "at_house"]
