from django.contrib import admin
from django.utils.html import format_html

from .models import Constellation, Star, StellarObjectType, Year, Information

from utils.multilinguality import LocalizedModelAdmin


@admin.register(Constellation)
class ConstellationAdmin(LocalizedModelAdmin):
    localized_fields = ("title", "description")
    list_display = ("default_localized_title", )


@admin.register(Star)
class StarAdmin(LocalizedModelAdmin):
    localized_fields = ("title", "area", "comment")
    list_display = ("default_localized_title", "stellar_object_type", "img_preview", "custom_id")
    list_filter = ("custom_id",)

    def img_preview(self, obj):
        image_html = ''
        if obj.img.url.find("{") != -1 or obj.img.url.find("}") != -1:
            image_html += "Нет изображения"
        else:
            image_html += '<a href="{0}" target="blank"><img src="{1}" style="width: 50px; height:50px;" /></a><br />'.format(
                obj.img.url, obj.img.url)
        return format_html(image_html)

    img_preview.short_description = 'Image'

    # form = StarForm
    search_fields = ("years__value", "custom_id")


@admin.register(Year)
class YearAdmin(admin.ModelAdmin):
    list_display = (
        "star", "value", "tropical_sign", "tropical_signdegree", "tropical_minutes", "sidereal_sign",
        "sidereal_signdegree",
        "sidereal_minutes")
    search_fields = (
        "star__title", "value", "tropical_signdegree", "tropical_minutes", "sidereal_signdegree", "sidereal_minutes")


@admin.register(StellarObjectType)
class StellarObjectTypeAdmin(LocalizedModelAdmin):
    localized_fields = ("name", "comment")
    list_display = ("default_localized_name", "custom_id")


@admin.register(Information)
class InformationAdmin(LocalizedModelAdmin):
    localized_fields = ("title", "description")
    list_display = ("default_localized_title", "published_at")
