from django.contrib.auth import get_user_model
from rest_framework import serializers

from advertising.serializers import BannerTypeSerializer
from utils.multilinguality import get_language_value
from .models import (
    AdditionalField,
    Bonus,
    Course,
    ForWhomCourse,
    Lesson,
    Module,
    PaymentOption,
    VideoPresentation,
    WhatYouBuy,
    WithinCourse,
    AdvCourseCard,
    AdvCourseCardLocale,
    Tag,
    Feature
)

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = '__all__'


class AdvCourseCardSerializer(serializers.ModelSerializer):
    banner_type = BannerTypeSerializer(many=True)
    image = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()

    def _get_lang(self):
        lang = self.context.get('language_code')
        if lang:
            return lang
        request = self.context.get('request')
        if request:
            lang = request.GET.get('language_code') or request.GET.get('lang')
            if not lang:
                accept_lang = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
                if accept_lang:
                    lang = accept_lang.split(',')[0].split(';')[0].strip().split('-')[0].lower()
        return lang or 'ru'

    def get_title(self, obj):
        return get_language_value(obj.title, self._get_lang())

    def get_link(self, obj):
        return get_language_value(obj.link, self._get_lang())

    def get_image(self, obj):
        request = self.context.get('request')
        lang = self._get_lang()
        # 1. Per-language uploaded image from AdvCourseCardLocale
        locale = obj.locales.filter(language_code=lang).first()
        if locale is None and lang != 'ru':
            locale = obj.locales.filter(language_code='ru').first()
        if locale:
            if locale.image and request:
                return request.build_absolute_uri(locale.image.url)
            if locale.image_link and locale.image_link.strip():
                return locale.image_link
        # 2. Per-language URL from image_link JSONField
        if isinstance(obj.image_link, dict):
            url = (obj.image_link.get(lang) or obj.image_link.get('ru') or '').strip()
            if url:
                return url
        # 3. Fallback: default uploaded image
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    class Meta:
        model = AdvCourseCard
        fields = ("id", "title", "link", "image", "banner_type")


class BonusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bonus
        fields = ("text",)


class PaymentOptionSerializer(serializers.ModelSerializer):
    bonuses = BonusSerializer(many=True)

    class Meta:
        model = PaymentOption
        fields = "__all__"


class WhatYouBuySerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatYouBuy
        fields = "__all__"


class WithinCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithinCourse
        fields = "__all__"


class ForWhomCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForWhomCourse
        fields = "__all__"


class VideoPresentationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoPresentation
        fields = "__all__"


class AdditionalFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalField
        fields = "__all__"


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = "__all__"


class ModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(source="module_lessons.all", many=True)

    class Meta:
        model = Module
        fields = "__all__"


class TeacherSerializer(serializers.ModelSerializer):
    avatar = serializers.URLField(
        source="profile.avatar", allow_null=True, allow_blank=True
    )
    teacher_title = serializers.CharField(
        source="profile.teacher_title", allow_null=True, allow_blank=True
    )
    teacher_description = serializers.CharField(
        source="profile.teacher_description", allow_null=True, allow_blank=True
    )
    link = serializers.HyperlinkedRelatedField(
        source="profile",
        view_name="users:user-profile-open-info-detail",
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "avatar",
            "teacher_title",
            "teacher_description",
            "link",
        )


class CourseSerializer(serializers.ModelSerializer):
    lesson_count = serializers.IntegerField(source="lessons.count")
    lessons = LessonSerializer(source="lessons.all", many=True)
    module_count = serializers.IntegerField(source="course_modules.count")
    modules = ModuleSerializer(source="course_modules.all", many=True)
    additional_fields = AdditionalFieldSerializer(
        source="additional_fields.all", many=True
    )
    video_presentations = VideoPresentationSerializer(
        source="video_presentations.all", many=True
    )
    for_whom_courses = ForWhomCourseSerializer(source="for_whom_courses.all", many=True)
    teachers = TeacherSerializer(many=True)
    within_courses = WithinCourseSerializer(many=True)
    what_you_buys = WhatYouBuySerializer(many=True)
    payment_options = PaymentOptionSerializer(many=True)

    class Meta:
        model = Course
        fields = "__all__"
