from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from rangefilter.filters import DateTimeRangeFilter

from complaints.admin import ComplaintInline
from utils.admin import ExportCsvMixin
from .forms import UserChangeForm, UserCreationForm
from .models import (
    BaseGroup,
    # BlockedUser,
    GeneratedPassword,
    Group,
    # RequestSubscription,
    Subscription,
    User,
    UserFile,
    UserProfile,
    AppLanguage
)


class UserFileTabularInlineAdmin(admin.TabularInline):
    def image_preview(self, obj):
        image_html = ''
        image_html += '<a href="{0}" target="blank"><img src="{1}" style="width: 100px; height:100px;" /></a><br />'.format(
            obj.image_original.url, obj.image.url)
        return format_html(image_html)

    fields = ("image_preview", "image", "image_original", "file_type")
    readonly_fields = ("image_preview",)

    model = UserFile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    max_num = 1
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin, ExportCsvMixin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(complaint_count=Count("complaint", filter=Q(complaint__status=1)))
        return queryset

    def complaint(self, obj):
        return obj.complaint_count == 0

    complaint.boolean = True

    @admin.display(ordering='profile__about', description='About')
    def get_about(self, obj):
        return obj.profile.about

    inlines = [UserProfileInline, UserFileTabularInlineAdmin,
               ComplaintInline]  # this should be limited, so no need pagination
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "patronymic", "last_name")}),
        (_("Translation"), {"fields": ("language", "app_language")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "restriction_forum",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "last_seen", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    list_filter = (("date_joined", DateTimeRangeFilter), ('complaint', admin.EmptyFieldListFilter),
                   ("last_login", DateTimeRangeFilter), ("last_seen", DateTimeRangeFilter),
                   ("profile__about", admin.EmptyFieldListFilter), "is_staff", "is_superuser")
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = (
        "email",
        "first_name",
        # "patronymic",
        "last_name",
        "complaint",
        "date_joined",
        "last_login",
        "last_seen",
        "get_about",
        "is_staff",
        "is_superuser",
        "restriction_forum"
    )
    search_fields = (
        "email",
        "first_name",
        "patronymic",
        "last_name",
    )
    actions = ["export_as_csv"]
    ordering = ("-id",)


admin.site.unregister(BaseGroup)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    pass


@admin.register(GeneratedPassword)
class GeneratedPasswordAdmin(admin.ModelAdmin):
    readonly_fields = ('date', 'password')


@admin.register(UserFile)
class UserFileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "file_type", "img_preview")

    def img_preview(self, obj):
        image_html = '<a href="{0}" target="blank"><img src="{1}" style="width: 50px; height:50px;" /></a><br />'.format(
            obj.image_original.url, obj.image.url)
        return format_html(image_html)

    img_preview.short_description = 'Image'


# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     autocomplete_fields = ["user", ]
#
#     list_display = (
#         "id",
#         "user",
#         "about",
#         # "email",
#         "full_show",
#         "user_notifications",
#         "calendar",
#         "astro_processor",
#         "forum",
#     )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user_dst", "user_src", "created_at", "updated_at", "status")
    readonly_fields = ("created_at", "updated_at")

# @admin.register(RequestSubscription)
# class RequestSubscriptionAdmin(admin.ModelAdmin):
#     list_display = ("user_dst", "user_src", "status")


# @admin.register(BlockedUser)
# class BlockedUserAdmin(admin.ModelAdmin):
#     list_display = ("user_dst", "user_src")


@admin.register(AppLanguage)
class AppLanguageAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
