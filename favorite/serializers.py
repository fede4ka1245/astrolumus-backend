from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import ProgrammingError
from django.db.utils import OperationalError
from drf_yasg import openapi
from rest_framework import serializers

from astrology_forum.models import Topic
from astrology_forum.serializers import TopicSerializer
from users.serializers import UserSerializer

from .models import Favorite

MODELS_FOR_REVIEW = ("astrology_forum.topic",)


def get_choices_for_review():
    result = []
    for model_qualifier in MODELS_FOR_REVIEW:
        app_label, model_name = model_qualifier.split(".")
        model = apps.get_model(app_label, model_name)
        result.append((model_qualifier, model._meta.verbose_name))
    return result


def get_queryset_for_review():
    models = []
    for model_qualifier in MODELS_FOR_REVIEW:
        app_label, model_name = model_qualifier.split(".")
        models.append(apps.get_model(app_label, model_name))
    try:
        return ContentType.objects.filter(
            pk__in=[x.pk for x in ContentType.objects.get_for_models(*models).values()]
        )
    except (ProgrammingError, OperationalError):
        # Fix for migrate/startup when DB isn't ready/reachable yet
        return ContentType.objects.none()


class ContentTypeField(serializers.PrimaryKeyRelatedField):
    """Represents `ContentType.pk` with a nice model qualifier."""

    class Meta:
        swagger_schema_fields = {
            "type": openapi.TYPE_STRING,
            "enum": MODELS_FOR_REVIEW,
            "title": "Тип контента",
        }

    def __init__(self, **kwargs):
        # Don't query DB at import time (serializer fields are instantiated on module import).
        kwargs.setdefault("queryset", ContentType.objects.none())
        super().__init__(**kwargs)

    def get_queryset(self):
        return get_queryset_for_review()

    def to_internal_value(self, data):
        data = ContentType.objects.get_for_model(apps.get_model(*data.split("."))).pk
        return super().to_internal_value(data)

    def to_representation(self, value):
        value = ContentType.objects.get(pk=value.pk)
        return ".".join([value.app_label, value.model])


class ObjectRelatedField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if isinstance(value, Topic):
            serializer = TopicSerializer(value, context={'request': self.context["request"]})
            data = serializer.data
        else:
            data = "Данные не доступны"

        return data


class FavoriteSerializer(serializers.ModelSerializer):
    content_type = ContentTypeField()
    content_object = ObjectRelatedField(read_only=True,)
    author_on_read = UserSerializer(source="author", read_only=True, label="автор")
    author = serializers.PrimaryKeyRelatedField(
        label="автор",
        queryset=get_user_model().objects.all(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Favorite
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["author"] = data.pop("author_on_read")
        return data

    def to_internal_value(self, data):
        user = self.context.get("request").user
        data["author"] = user.pk
        return super().to_internal_value(data)
