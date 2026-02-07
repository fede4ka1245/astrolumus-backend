from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from voting.models import Vote
from utils.multilinguality import get_default_language_code
from misc.runtime import get_default_app_language

from .models import (
    BlockedUser,
    Subscription,
    User,
    UserFile,
    UserProfile,
    Settings,
    AppLanguage
)


class RegistrationSerializer(serializers.ModelSerializer):
    app_language = serializers.SlugRelatedField(
        slug_field='code',
        queryset=AppLanguage.objects.all(),
        required=False,
        default=get_default_app_language
    )

    def create(self, validated_data):
        return get_user_model().objects.create_user(
            **validated_data,
            settings=Settings.objects.create()
        )

    def validate_email(self, value):
        norm_email = value.lower()
        if get_user_model().objects.filter(email=norm_email).exists():
            raise serializers.ValidationError(
                ["пользователь с таким адрес электронной почты уже существует."])
        return norm_email

    class Meta:
        model = get_user_model()
        fields = (
            "email",
            "first_name",
            "last_name",
            "patronymic",
            "language",
            "app_language",
        )


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(source="profile.avatar", read_only=True)
    birth_date = serializers.CharField(source="profile.birth_date", read_only=True)
    app_language = serializers.SlugRelatedField(
        slug_field='code',
        queryset=AppLanguage.objects.all(),
        required=False,
        default=get_default_app_language
    )

    likes_count = serializers.SerializerMethodField()

    def get_likes_count(self, obj):
        # TODO optimize this / one sql query per object
        return Vote.objects.get_score(obj)["score"]

    class Meta:
        model = get_user_model()
        fields = ("id", "avatar", "email", "nickname", "likes_count",
                  "patronymic", "language", "app_language", "first_name", "last_name", "birth_date")


class GenerateRegistrationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ValidateRegistrationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class UserFileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects, required=False, allow_null=True
    )

    class Meta:
        model = UserFile
        fields = "__all__"


class UserProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.CharField(source="user.email", required=False)
    patronymic = serializers.CharField(source="user.patronymic", required=False, allow_blank=True, allow_null=True)
    user = serializers.PrimaryKeyRelatedField(
        required=False, allow_null=True, read_only=True
    )
    likes_count = serializers.SerializerMethodField()

    def get_likes_count(self, obj):
        # TODO optimize this / one sql query per object
        return Vote.objects.get_score(obj.user)["score"]

    def save_user_fields(self, instance):
        user = instance.user

        data = {"email": user.email}
        if "first_name" in self.initial_data and self.initial_data.get("first_name"):
            data["first_name"] = self.initial_data.get("first_name")
        if "last_name" in self.initial_data and self.initial_data.get("last_name"):
            data["last_name"] = self.initial_data.get("last_name")

        user_serializer = UserSerializer(user, data=data, many=False)
        if user_serializer.is_valid(raise_exception=True):
            user_serializer.save()

    def create(self, validated_data):
        instance = super().create(validated_data)
        self.save_user_fields(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self.save_user_fields(instance)
        return instance

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "user",
            "first_name",
            "last_name",
            "birth_date",
            "patronymic",
            "avatar",
            "likes_count",
            "about",
            "email",
            "full_show",
            "user_notifications",
            "calendar",
            "astro_processor",
            "forum",
        )


class BlockedUserSerializer(serializers.ModelSerializer):
    def validate(self, data):
        if data["user_dst"] == self.context.get("request").user:
            raise serializers.ValidationError("You can not blocked to yourself")

        if BlockedUser.objects.filter(
                user_dst=data["user_dst"], user_src=self.context.get("request").user
        ).first():
            raise serializers.ValidationError("Duplication object")
        return data

    class Meta:
        model = BlockedUser
        fields = ("id", "user_dst", "user_src")
        read_only_fields = ("user_src",)


class UserProfileOpenInfoSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    patronymic = serializers.CharField(source="user.patronymic", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    likes_count = serializers.SerializerMethodField()
    subscribers_count = serializers.SerializerMethodField()

    current_user_liked = serializers.SerializerMethodField()
    current_user_subscribed = serializers.SerializerMethodField()

    def get_current_user_liked(self, obj):
        if "request" in self.context and self.context["request"].user.is_authenticated:
            # TODO optimize this / one sql query per object
            vote = Vote.objects.get_for_user(obj.user, self.context["request"].user)
            if vote:
                return True
        return False

    def get_current_user_subscribed(self, obj):
        if "request" in self.context and self.context["request"].user.is_authenticated:
            # TODO optimize this / one sql query per object
            vote = obj.user.user_dst_subscriptions.filter(user_src=self.context["request"].user)
            if vote:
                return True
        return False

    def get_likes_count(self, obj):
        # TODO optimize this / one sql query per object
        return Vote.objects.get_score(obj.user)["score"]

    def get_subscribers_count(self, obj):
        # TODO change this behavior if needed
        return 0

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "user_id",
            "avatar",
            "first_name",
            "patronymic",
            "birth_date",
            "last_name",
            "about",
            "likes_count",
            "subscribers_count",
            "current_user_liked",
            "current_user_subscribed",
            "teacher_title",
            "teacher_description",
        )


class PublicUserSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(source="profile.avatar", read_only=True)
    birth_date = serializers.CharField(source="profile.birth_date", read_only=True)
    app_language = serializers.SlugRelatedField(
        slug_field='code',
        queryset=AppLanguage.objects.all(),
        required=False,
        default=get_default_app_language
    )
    likes_count = serializers.SerializerMethodField()

    def get_likes_count(self, obj):
        # TODO optimize this / one sql query per object
        return Vote.objects.get_score(obj)["score"]

    class Meta:
        model = User
        fields = (
            "id",
            "avatar",
            "first_name",
            "nickname",
            "patronymic",
            "last_name",
            "likes_count",
            "birth_date",
            "app_language"
        )


class PublicUserSimpleSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(source="profile.avatar", read_only=True)
    birth_date = serializers.CharField(source="profile.birth_date", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "avatar",
            "first_name",
            "nickname",
            "patronymic",
            "last_name",
            "birth_date",
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    user_dst_id = serializers.IntegerField(write_only=True)
    user_src = PublicUserSerializer(many=False, read_only=True)
    user_dst = PublicUserSerializer(many=False, read_only=True)

    def validate(self, data):
        if "user_dst_id" not in data:
            raise ValidationError("{user_dst_id: id} required")

        if data["user_dst_id"] == self.context.get("request").user.id:
            raise serializers.ValidationError("You can not subscription to yourself")

        if not User.objects.filter(pk=data["user_dst_id"]).exists():
            raise serializers.ValidationError("user with this user_dst_id does not exist")

        subscription = Subscription.objects.filter(
            user_dst_id=data["user_dst_id"], user_src=self.context.get("request").user
        ).first()

        if subscription:
            raise serializers.ValidationError("Duplication object")
        return data

    class Meta:
        model = Subscription
        fields = ("id", "user_dst", "user_src", "status", "user_dst_id")
        read_only_fields = ("user_src",)


class AppLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppLanguage
        fields = "__all__"
