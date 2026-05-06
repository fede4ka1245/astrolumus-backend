from rest_framework import serializers

from .models import Constellation, Star, StellarObjectType, Year

from utils.multilinguality import LocalizedFieldsSerializerMixin


class StellarObjectTypeSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = "stellar_types"
    tolgee_key_prefix = "stype"
    localized_fields = ("name", "comment")

    class Meta:
        model = StellarObjectType
        fields = "__all__"


class YearSerializer(serializers.ModelSerializer):
    class Meta:
        model = Year
        fields = "__all__"


class ConstellationSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = "constellations"
    tolgee_key_prefix = "const"
    localized_fields = ("title", "description")

    class Meta:
        model = Constellation
        fields = "__all__"


class StarSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = "stars"
    localized_fields = ("title", "comment")
    upload_image = serializers.ImageField(required=True)

    class Meta:
        model = Star
        fields = (
            "custom_id",
            "title",
            "constellation",
            "comment",
            "upload_image",
            "stellar_object_type",
        )
        extra_kwargs = {
            "stellar_object_type": {"required": True},
            "upload_image": {"required": True},
        }


class StarListSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    tolgee_namespace = "stars"
    localized_fields = ("title", "comment", "area")
    years = YearSerializer(many=True, allow_null=True, required=False)

    class Meta:
        model = Star
        fields = "__all__"
