from django.conf import settings
from django.contrib import admin
from django.db import models
from django.utils.html import strip_tags

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
    def _get_language_code(self):
        # 1. Explicit query parameter
        lang = self.request.query_params.get('language_code') or self.request.query_params.get('lang')
        if lang:
            return lang.split('-')[0].lower()

        # 2. Accept-Language header
        accept_lang = self.request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        if accept_lang:
            primary = accept_lang.split(',')[0].split(';')[0].strip()
            if primary:
                return primary.split('-')[0].lower()

        # 3. Authenticated user's language preference
        user = self.request.user
        if user and user.is_authenticated and getattr(user, 'language', None):
            return user.language.split('-')[0].lower()

        # 4. Default
        return get_default_language_code()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['language_code'] = self._get_language_code()
        return context


class LocalizedFieldsSerializerMixin:
    """
    Миксин для сериализаторов с локализованными полями.

    Поддерживает два режима:
    1. Из БД (legacy): поле модели содержит JSON dict {"ru": "...", "en": "..."}
    2. Из S3 (Tolgee): читает переводы из S3 по ключу model_name.pk.field_name

    Переключение: если установлен tolgee_namespace, читаем из S3.
    """
    localized_fields = []
    tolgee_namespace = None  # Установить для чтения из S3 (например "tariffs", "content")
    tolgee_key_prefix = None  # Опциональный префикс ключа; если None — используется _meta.model_name

    def get_localized_value(self, obj, field_name):
        lang = self.context.get("language_code")

        # Если задан tolgee_namespace — читаем из S3
        if self.tolgee_namespace:
            from utils.translation_loader import get_localized_value_from_s3

            prefix = self.tolgee_key_prefix if self.tolgee_key_prefix is not None else obj._meta.model_name
            key_prefix = f"{prefix}.{obj.pk}"
            value = get_localized_value_from_s3(
                self.tolgee_namespace, key_prefix, field_name, lang
            )
            if value is not None:
                return value
            # Fallback на default language
            default_lang = get_default_language_code()
            if lang != default_lang:
                value = get_localized_value_from_s3(
                    self.tolgee_namespace, key_prefix, field_name, default_lang
                )
                if value is not None:
                    return value

        # Fallback: читаем из JSON поля в БД
        return get_language_value(
            getattr(obj, field_name, None),
            lang
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in self.localized_fields:
            representation[field] = self.get_localized_value(instance, field)
        return representation


class LocalizedModelAdmin(admin.ModelAdmin):
    """
    Admin для моделей с локализованными JSON-полями.

    При сохранении данные пишутся и в поле БД, и в Tolgee.
    Языковые табы берутся из Tolgee (через _languages_for_tabs).
    """
    localized_fields = []
    tolgee_namespace = "content"  # override в подклассах (например "tariffs")
    tolgee_key_prefix = None  # override в подклассах; если None — используется model_name

    def get_localized_value(self, obj, field_name):
        """Читает значение из S3 (Tolgee), fallback на БД."""
        if self.tolgee_namespace and obj.pk:
            from utils.translation_loader import get_localized_value_from_s3
            key_prefix = self._tolgee_key_prefix(obj)
            lang = get_default_language_code()
            value = get_localized_value_from_s3(
                self.tolgee_namespace, key_prefix, field_name, lang
            )
            if value is not None:
                return value
        return get_default_language_value_admin(
            getattr(obj, field_name, {})
        )

    def _tolgee_key_prefix(self, obj):
        """Возвращает prefix для ключей Tolgee: {tolgee_key_prefix или model_name}.pk"""
        prefix = self.tolgee_key_prefix if self.tolgee_key_prefix is not None else obj._meta.model_name
        return f"{prefix}.{obj.pk}"

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
            value = self.get_localized_value(obj, field_name)
            if value:
                return strip_tags(value)
            return value

        return localized_field_display

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_localized_display_methods()

    def get_object(self, request, object_id, from_field=None):
        """Подставляет значения из S3 (Tolgee) в localized поля формы."""
        obj = super().get_object(request, object_id, from_field)
        if obj is None or not self.tolgee_namespace:
            return obj

        from utils.translation_loader import get_localized_value_from_s3
        from utils.admin_multilang_json_widget import _languages_for_tabs

        key_prefix = self._tolgee_key_prefix(obj)
        languages = _languages_for_tabs()

        for field_name in self.localized_fields:
            s3_values = {}
            for lang_code, _ in languages:
                value = get_localized_value_from_s3(
                    self.tolgee_namespace, key_prefix, field_name, lang_code
                )
                if value is not None:
                    s3_values[lang_code] = value
            if s3_values:
                # Merge: S3 values take priority, keep DB values for missing langs
                db_values = getattr(obj, field_name, {}) or {}
                merged = {**db_values, **s3_values}
                setattr(obj, field_name, merged)
        return obj

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if (
            isinstance(db_field, models.JSONField)
            and db_field.name in getattr(self, "localized_fields", [])
            and formfield is not None
        ):
            formfield.widget = MultilangJSONCKEditorWidget()
        return formfield

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Синхронизируем локализованные поля в Tolgee
        synced = False
        try:
            from utils.tolgee_client import upsert_key

            for field_name in self.localized_fields:
                value = getattr(obj, field_name, None)
                if not isinstance(value, dict):
                    continue
                translations = {
                    lang: text for lang, text in value.items()
                    if isinstance(text, str) and text.strip()
                }
                if translations:
                    tolgee_key = f"{self._tolgee_key_prefix(obj)}.{field_name}"
                    upsert_key(self.tolgee_namespace, tolgee_key, translations)
                    synced = True
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Failed to sync to Tolgee for %s pk=%s", obj._meta.model_name, obj.pk
            )

        if synced:
            try:
                from utils.tasks import sync_tolgee_to_s3
                from utils.translation_loader import invalidate_cache
                sync_tolgee_to_s3.delay()
                invalidate_cache()
            except Exception:
                import logging
                logging.getLogger(__name__).exception(
                    "Failed to trigger S3 sync after Tolgee update for %s pk=%s",
                    obj._meta.model_name, obj.pk
                )

    def delete_model(self, request, obj):
        # Удаляем ключи из Tolgee
        try:
            from utils.tolgee_client import delete_keys_by_prefix

            prefix = self._tolgee_key_prefix(obj)
            delete_keys_by_prefix(self.tolgee_namespace, f"{prefix}.")
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Failed to delete Tolgee keys for %s pk=%s", obj._meta.model_name, obj.pk
            )
        super().delete_model(request, obj)
