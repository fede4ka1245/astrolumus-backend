from django.contrib import admin
from django.db import models

from utils.admin_multilang_json_widget import MultilangJSONTextInputWidget

from .models import AdvCourseCard, AdvCourseCardLocale, Tag


class AdvCourseCardLocaleInline(admin.TabularInline):
    model = AdvCourseCardLocale
    extra = 0
    fields = ("language_code", "image", "image_link")
    verbose_name = "Картинка по языку"
    verbose_name_plural = "Картинки по языкам"


class AdvCourseCardAdmin(admin.ModelAdmin):
    list_display = ("get_title", "show_card")
    list_filter = ("banner_type", "show_card")
    filter_horizontal = ("banner_type",)
    fields = ("title", "banner_type", "link", "image_link", "show_card")
    inlines = (AdvCourseCardLocaleInline,)

    def get_title(self, obj):
        t = obj.title
        if isinstance(t, dict):
            return t.get("ru") or next(iter(t.values()), "")
        return t or ""
    get_title.short_description = "Название"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if isinstance(db_field, models.JSONField) and formfield is not None:
            formfield.widget = MultilangJSONTextInputWidget()
        return formfield


admin.site.register(AdvCourseCard, AdvCourseCardAdmin)
admin.site.register(Tag)
