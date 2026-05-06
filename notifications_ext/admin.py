from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Banner, NotificationPage, NotificationTask, NotificationPageGroup, NotificationPageType, Tag
from utils.multilinguality import LocalizedModelAdmin

User = get_user_model()


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ["title", "image", "image_link", "video_link"]


@admin.register(NotificationPage)
class NotificationPageAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "banner", "primary_info", "secondary_info", "primary_banner", "secondary_banner",
                    "first_button_text", "first_button_link", "second_button_text", "second_button_link"]
    fields = ("title", "language_code", "banner", "primary_info", "secondary_info", "primary_banner",
              "interesting_tag", "interesting_text", "secondary_banner", "first_button_text",
              "first_button_link", "second_button_text", "second_button_link")


@admin.register(NotificationTask)
class NotificationTaskAdmin(LocalizedModelAdmin):
    tolgee_namespace = None
    localized_fields = ("verb", "description")
    list_display = ("id", "default_localized_verb", "default_localized_description", "timestamp")
    readonly_fields = ('sent', )


admin.site.register(NotificationPageType)
admin.site.register(NotificationPageGroup)
@admin.register(Tag)
class TagAdmin(LocalizedModelAdmin):
    tolgee_namespace = None
    localized_fields = ("title",)
    list_display = ("id", "default_localized_title", "alias", "color")
