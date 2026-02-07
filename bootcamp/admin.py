import nested_admin
from django.contrib import admin

from .models import (
    AdditionalField,
    Bonus,
    Course,
    Curriculum,
    ForWhomCourse,
    Lesson,
    Module,
    PaymentOption,
    PaymentOptionType,
    VideoPresentation,
    WhatYouBuy,
    WithinCourse,
    AdvCourseCard,
    Tag,
    Feature
)


class BonusInline(nested_admin.NestedStackedInline):
    model = Bonus


class PaymentOptionInline(nested_admin.NestedStackedInline):
    model = PaymentOption
    inlines = (BonusInline,)


class WhatYouBuyInline(nested_admin.NestedStackedInline):
    model = WhatYouBuy


class WithinCourseInline(nested_admin.NestedStackedInline):
    model = WithinCourse


class AdditionalFieldInline(nested_admin.NestedStackedInline):
    model = AdditionalField


class VideoPresentationInline(nested_admin.NestedStackedInline):
    model = VideoPresentation


class ForWhomCourseInline(nested_admin.NestedStackedInline):
    model = ForWhomCourse


class LessonInline(nested_admin.NestedStackedInline):
    list_display = ("title",)
    model = Lesson


class ModuleInline(nested_admin.NestedStackedInline):
    list_display = ("title",)
    model = Module
    inlines = (LessonInline,)


@admin.register(Course)
class CourseAdmin(nested_admin.NestedModelAdmin):
    list_display = ("title",)
    inlines = (
        ModuleInline,
        LessonInline,
        AdditionalFieldInline,
        VideoPresentationInline,
        ForWhomCourseInline,
        WithinCourseInline,
        WhatYouBuyInline,
        PaymentOptionInline,
    )


@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "created")
    list_filter = ("user", "course")


@admin.register(PaymentOptionType)
class PaymentOptionTypeAdmin(admin.ModelAdmin):
    list_display = ("title", "alias")


@admin.register(AdvCourseCard)
class AdvCourseCardAdmin(admin.ModelAdmin):
    list_display = ("title", "publish_start", "link")


admin.site.register(Tag)
admin.site.register(Feature)
