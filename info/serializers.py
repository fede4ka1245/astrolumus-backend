from rest_framework import serializers

from info.models import AppPartInfo, Documents

from utils.multilinguality import LocalizedFieldsSerializerMixin


class AppPartInfoSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    localized_fields = ("title", "sub_title", "description", "main_description")

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
    localized_fields = ("title", "description")
    
    class Meta:
        model = Documents
        fields = ("code", "title", "description", "created_at", "updated_at", "published_at")
