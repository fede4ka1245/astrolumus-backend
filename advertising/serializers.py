from pytube import extract
from pytube.exceptions import RegexMatchError
from rest_framework import serializers

from .models import Banner, BannerType, BannerImage, Tag

from utils.multilinguality import get_language_value, get_default_language_code, LocalizedFieldsSerializerMixin


class BannerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BannerType
        fields = "__all__"


class BannerImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BannerImage
        fields = "__all__"


class TagSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = None
    localized_fields = ("title", )

    class Meta:
        model = Tag
        fields = "__all__"


class BannerSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = None
    localized_fields = ("title", "description", "video_link")
    banner_type = BannerTypeSerializer(many=True)
    previews = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    image_link = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    def get_tags(self, obj):
        return TagSerializer(
            obj.tags.all(),
            many=True,
            context=self.context
        ).data

    def get_previews(self, obj):
        try:
            video_id = extract.video_id(
                get_language_value(
                    obj.video_link,
                    self.context.get("language_code")
                )
            )
            return {
                0: f"https://img.youtube.com/vi/{video_id}/0.jpg",
                1: f"https://img.youtube.com/vi/{video_id}/1.jpg",
            }
        except (TypeError, RegexMatchError):
            return {}

    def get_image(self, obj):
        language_image = obj.images.filter(
            language_code=self.context.get("language_code")
        ).first()
        if language_image and language_image.image:
            return language_image.image.url

        default_language_image = obj.images.filter(
            language_code=get_default_language_code()
        ).first()
        if default_language_image and default_language_image.image:
            return default_language_image.image.url

    def get_image_link(self, obj):
        language_image = obj.images.filter(
            language_code=self.context.get("language_code")
        ).first()
        if language_image and language_image.image_link:
            return language_image.image_link

        default_language_image = obj.images.filter(
            language_code=get_default_language_code()
        ).first()
        if default_language_image and default_language_image.image_link:
            return default_language_image.image_link

    class Meta:
        model = Banner
        exclude = ("images", )
