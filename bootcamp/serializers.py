from django.contrib.auth import get_user_model
from rest_framework import serializers

from advertising.serializers import BannerTypeSerializer
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
    tags = TagSerializer(many=True)
    features = FeatureSerializer(many=True)
    target_languages = serializers.SerializerMethodField()

    @staticmethod
    def get_target_languages(obj):
        return [language.code for language in obj.target_languages.all()]

    class Meta:
        model = AdvCourseCard
        fields = "__all__"


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
