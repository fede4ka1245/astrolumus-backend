from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.db.models import Subquery, OuterRef, Count, Func, F, Q
from django.utils.html import format_html
from django.utils.timezone import now

from django_admin_inline_paginator.admin import TabularInlinePaginated

from ordered_model.admin import OrderedModelAdmin
from rangefilter.filters import DateTimeRangeFilter

from complaints.admin import ComplaintInline
from complaints.models import Complaint
from .models import Category, Comment, Topic, Image, LastTopicCommentRead, ForumRules, Membership


@admin.register(Category)
class CategoryAdmin(OrderedModelAdmin):
    list_select_related = (
        "parent",
    )
    list_display = ("id", "title", "parent", "order", "move_up_down_links")


class MembershipInline(TabularInlinePaginated):
    autocomplete_fields = ["user", "inviter"]
    readonly_fields = ["created_at", "updated_at"]
    per_page = 25
    model = Membership
    extra = 1
    can_delete = True


class CustomPublishedAtListFilter(admin.EmptyFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        # set filter by default
        if 'published_at__isempty' not in params:
            params["published_at__isempty"] = '0'
        super().__init__(field, request, params, model, model_admin, field_path)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(membership_count=Subquery(
            Membership.objects.filter(topic=OuterRef("pk"), status=Membership.Status.ACCEPTED)
                .order_by()
                .annotate(count=Func(F('id'), function='Count'))
                .values("count")
        ))
        return queryset

    def members_n(self, obj):
        return obj.membership_count

    def icon(self, obj):
        if obj.status == Topic.Status.BLOCKED:
            return False
        elif obj.status == Topic.Status.ACCEPTED:
            return True
        return None

    icon.boolean = True

    def user__email(self, obj):
        return obj.user.email

    def images_preview(self, obj):
        images_html = ''
        for image in obj.images.all():
            images_html += '<a href="{0}" target="blank"><img src="{1}" style="width: 100px; height:100px;" /></a><br />'.format(
                image.image_original.url, image.image.url)
        return format_html(images_html)

    def save_model(self, request, obj, form, change):
        # TODO check status changes?
        obj.moderated_by = request.user
        obj.moderated_at = now()
        if obj.status in ["blocked", "temporary_blocked", "archive"]:
            obj.published_at = None
        super().save_model(request, obj, form, change)

    autocomplete_fields = ["user", "images", "moderated_by"]
    list_select_related = (
        "category", "moderated_by", "user"
    )
    list_display = (
        "title", "icon", "status", "category", "members_n",
        "access_level", "user", "moderated_by",
        "moderated_at", "published_at",
        "moderator_comment", "created_at",
        "updated_at")
    readonly_fields = ["created_at", "updated_at", "user__email", "images_preview"]
    list_filter = ("status",  # ('user', admin.RelatedOnlyFieldListFilter),
                   ('published_at', CustomPublishedAtListFilter),
                   ('moderated_by', admin.RelatedOnlyFieldListFilter), ('moderated_at', DateTimeRangeFilter),
                   ('published_at', DateTimeRangeFilter), ("created_at", DateTimeRangeFilter),
                   ("updated_at", DateTimeRangeFilter), "access_level", "category")
    search_fields = ("title", "user__email",)
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    autocomplete_fields = ["topic", "user", "inviter"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(complaint_count=Count("complaint", filter=Q(complaint__status=1)))
        return queryset

    def user__email(self, obj):
        return obj.user.email

    def image_preview(self, obj):
        image_html = ''
        image_html += '<a href="{0}" target="blank"><img src="{1}" style="width: 100px; height:100px;" /></a><br />'.format(
            obj.image.image_original.url, obj.image.image.url)
        return format_html(image_html)

    def complaint(self, obj):
        return obj.complaint_count == 0

    complaint.boolean = True

    def has_image(self, obj):
        return bool(obj.image)

    has_image.boolean = True

    def save_model(self, request, obj, form, change):
        # TODO check status changes?
        obj.moderated_by = request.user
        obj.moderated_at = now()
        super().save_model(request, obj, form, change)

    autocomplete_fields = ["user", "image", "moderated_by", "comment", "topic"]
    list_select_related = (
        "comment", "moderated_by", "user", "topic", "image"
    )
    list_editable = ["status", ]  # "moderated_by", "moderated_at"]
    list_display = (
        "id", "text", "created_at", "updated_at", "complaint", "status", "moderated_by", "moderated_at",
        "user", "has_image")
    list_filter = ("status",  # ('user', admin.RelatedOnlyFieldListFilter),
                   ('complaint', admin.EmptyFieldListFilter),
                   ('moderated_by', admin.RelatedOnlyFieldListFilter), ('moderated_at', DateTimeRangeFilter),
                   ("created_at", DateTimeRangeFilter),
                   ("updated_at", DateTimeRangeFilter))
    readonly_fields = ["created_at", "updated_at", "user__email", "image_preview"]
    search_fields = ("text", "user__email",)
    inlines = [ComplaintInline]


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    search_fields = ["image"]


@admin.register(LastTopicCommentRead)
class LastTopicCommentReadAdmin(admin.ModelAdmin):
    pass


@admin.register(ForumRules)
class ForumRulesAdmin(admin.ModelAdmin):
    pass
