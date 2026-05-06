from rest_framework import serializers

from info.models import AppPartInfo, Documents, Info, MobileAppsVersion

from utils.multilinguality import LocalizedFieldsSerializerMixin, get_language_value


class AppPartInfoSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = "app_info"
    tolgee_key_prefix = "appinfo"
    localized_fields = ("title", "sub_title", "description", "main_description", "link")

    class Meta:
        model = AppPartInfo
        fields = [
            "id", "code", "title", "sub_title", "description", "main_description",
            "link", "created_at", "updated_at", "is_active"
        ]


class DocumentsSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = "documents"
    tolgee_key_prefix = "doc"
    localized_fields = ("title", "description")

    class Meta:
        model = Documents
        fields = ("code", "title", "description", "created_at", "updated_at", "published_at")


class InfoSerializer(serializers.ModelSerializer):
    whatsapp = serializers.SerializerMethodField()
    telegram_direct = serializers.SerializerMethodField()
    telegram = serializers.SerializerMethodField()
    viber = serializers.SerializerMethodField()
    youtube_alpha = serializers.SerializerMethodField()
    youtube_deep_sky = serializers.SerializerMethodField()

    def _lang(self):
        return self.context.get("language_code") or "ru"

    def get_whatsapp(self, obj):
        return get_language_value(obj.whatsapp, self._lang())

    def get_telegram_direct(self, obj):
        return get_language_value(obj.telegram_direct, self._lang())

    def get_telegram(self, obj):
        return get_language_value(obj.telegram, self._lang())

    def get_viber(self, obj):
        return get_language_value(obj.viber, self._lang())

    def get_youtube_alpha(self, obj):
        return get_language_value(obj.youtube_alpha, self._lang())

    def get_youtube_deep_sky(self, obj):
        return get_language_value(obj.youtube_deep_sky, self._lang())

    class Meta:
        model = Info
        fields = ("id", "whatsapp", "telegram_direct", "telegram", "viber",
                  "youtube_alpha", "youtube_deep_sky", "email")


class MobileAppsVersionSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    def _lang(self):
        return self.context.get("language_code") or "ru"

    def get_link(self, obj):
        return get_language_value(obj.link, self._lang())

    def get_description(self, obj):
        return get_language_value(obj.description, self._lang())

    class Meta:
        model = MobileAppsVersion
        fields = ("id", "app_type", "version", "link", "description")
