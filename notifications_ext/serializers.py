from django.contrib.auth import get_user_model
from django.template.defaultfilters import truncatechars_html
from notifications.models import Notification
from rest_framework import serializers

from astrology_forum.models import Topic, Comment
from users.serializers import PublicUserSerializer

from .models import NotificationPage, Banner, Tag

from utils.multilinguality import LocalizedFieldsSerializerMixin

User = get_user_model()


class TopicSimpleSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()

    def get_description(self, obj):
        return truncatechars_html(obj.description, 150)

    class Meta:
        model = Topic
        fields = (
            "id",
            "title",
            "status",
            "description",
            "published_at",
            "access_level",
            "access_level"
        )


class CommentSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = (
            "id",
            "text",
            "topic",
            "comment",
            "created_at",
            "status"
        )


class GenericNotificationRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        match value:
            case Topic():
                return TopicSimpleSerializer(value).data
            case User():
                return PublicUserSerializer(value).data
            case Comment():
                return CommentSimpleSerializer(value).data
            case _:
                return {"error": "template for object is not found"}


class NotificationPageBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    recipient = PublicUserSerializer(User, read_only=True)
    unread = serializers.BooleanField(read_only=True)
    target = GenericNotificationRelatedField(read_only=True)
    actor = GenericNotificationRelatedField(read_only=True)
    action_object = GenericNotificationRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "recipient", "unread", "actor", "verb", "action_object", "target", "data", "timestamp", "level",
                  "description"]


class TagSerializer(
    LocalizedFieldsSerializerMixin,
    serializers.ModelSerializer
):
    localized_fields = ("title", )

    class Meta:
        model = Tag
        fields = "__all__"


class NotificationPageSerializer(serializers.ModelSerializer):
    banner = NotificationPageBannerSerializer()
    primary_banner = NotificationPageBannerSerializer()
    secondary_banner = NotificationPageBannerSerializer()
    tags = serializers.SerializerMethodField()

    def get_tags(self, obj):
        group = obj.groups.first()
        if group:
            return TagSerializer(
                group.tags.all(),
                many=True,
                context=self.context | {"language_code": obj.language_code.code}
            ).data
        return []

    class Meta:
        model = NotificationPage
        fields = '__all__'
