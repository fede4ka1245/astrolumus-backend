from django.contrib import admin
from django.db import models

from info.models import Info, Documents, MobileAppsVersion, AppPartInfo
from utils.admin_multilang_json_widget import MultilangJSONCKEditorWidget, MultilangJSONTextInputWidget
from utils.multilinguality import LocalizedModelAdmin

_JSON_LINK_FIELDS = {"whatsapp", "telegram_direct", "telegram", "viber", "youtube_alpha", "youtube_deep_sky"}


@admin.register(Info)
class InfoAdmin(admin.ModelAdmin):
    list_display = ["id", "email"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if isinstance(db_field, models.JSONField) and db_field.name in _JSON_LINK_FIELDS and formfield is not None:
            formfield.widget = MultilangJSONTextInputWidget()
        return formfield


@admin.register(Documents)
class DocumentsAdmin(LocalizedModelAdmin):
    tolgee_namespace = "documents"
    tolgee_key_prefix = "doc"
    localized_fields = ("title", "description")
    list_display = ("id", "code", "default_localized_title", "published_at", "updated_at")

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if isinstance(db_field, models.JSONField) and db_field.name in self.localized_fields and formfield is not None:
            if db_field.name == "description":
                formfield.widget = MultilangJSONCKEditorWidget()
            else:
                formfield.widget = MultilangJSONTextInputWidget()
        return formfield


@admin.register(MobileAppsVersion)
class MobileAppsVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "app_type", "version")

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if isinstance(db_field, models.JSONField) and formfield is not None:
            if db_field.name == "description":
                formfield.widget = MultilangJSONCKEditorWidget()
            elif db_field.name == "link":
                formfield.widget = MultilangJSONTextInputWidget()
        return formfield


@admin.register(AppPartInfo)
class AppPartInfoAdmin(LocalizedModelAdmin):
    tolgee_namespace = "app_info"
    tolgee_key_prefix = "appinfo"
    localized_fields = ("title", "sub_title", "description", "main_description")
    list_display = ("id", "code", "default_localized_title", "is_active", "updated_at")

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if isinstance(db_field, models.JSONField) and db_field.name == "link" and formfield is not None:
            formfield.widget = MultilangJSONTextInputWidget()
        return formfield
