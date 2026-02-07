from django.conf import settings
from django.contrib import admin
from django.db import models

from utils.admin_multilang_json_widget import MultilangJSONCKEditorWidget


def get_default_language_code():
    return settings.DEFAULT_LANGUAGE_CODE


def _common_get_default_language_value(obj, placeholder: str = ""):
    if not isinstance(obj, dict):
        return
    return obj.get(get_default_language_code(), placeholder)


def get_default_language_value_admin(obj):
    return _common_get_default_language_value(obj, "Default language not set")


def get_default_language_value(obj):
    return _common_get_default_language_value(obj)


def get_language_value(obj, language_code: str):
    if not isinstance(obj, dict):
        return
    if not language_code:
        return get_default_language_value(obj)
    return obj.get(
        language_code.lower(),
        get_default_language_value(obj)
    )


class MultilingualityViewMixin:
    def get_serializer_context(self):
        context = super().get_serializer_context()

        context['language_code'] = self.request.query_params.get(
            'language_code',
            get_default_language_code()
        )

        return context


class LocalizedFieldsSerializerMixin:
    localized_fields = []

    def get_localized_value(self, obj, field_name):
        return get_language_value(
            getattr(obj, field_name, None),
            self.context.get("language_code")
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in self.localized_fields:
            representation[field] = self.get_localized_value(instance, field)
        return representation


class LocalizedModelAdmin(admin.ModelAdmin):
    localized_fields = []

    @staticmethod
    def get_localized_value(obj, field_name):
        return get_default_language_value_admin(
            getattr(obj, field_name, {})
        )

    def add_localized_display_methods(self):
        for field in self.localized_fields:
            method_name = f"default_localized_{field}"
            if hasattr(self, method_name):
                continue
            setattr(
                self,
                method_name,
                self.create_localized_display_method(field),
            )

            admin.display(description=f"Localized {field}")(
                getattr(self, method_name)
            )

    def create_localized_display_method(self, field_name):
        def localized_field_display(obj):
            return self.get_localized_value(obj, field_name)

        return localized_field_display

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_localized_display_methods()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if (
            isinstance(db_field, models.JSONField)
            and db_field.name in getattr(self, "localized_fields", [])
            and formfield is not None
        ):
            formfield.widget = MultilangJSONCKEditorWidget()
        return formfield
