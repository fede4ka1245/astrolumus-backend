from django.contrib import admin

from info.models import Info, Documents, MobileAppsVersion, AppPartInfo
from utils.multilinguality import LocalizedModelAdmin


@admin.register(Info)
class InfoAdmin(admin.ModelAdmin):
    list_display = ["id", "whatsapp", "telegram_direct", "telegram", "viber", "youtube_alpha", "youtube_deep_sky",
                    "email"]

@admin.register(Documents)
class DocumentsAdmin(LocalizedModelAdmin):
    localized_fields = ("title", "description")
    list_display = ("id", "code", "default_localized_title", "published_at", "updated_at")


admin.site.register(MobileAppsVersion)


@admin.register(AppPartInfo)
class AppPartInfoAdmin(LocalizedModelAdmin):
    localized_fields = ("title", "sub_title", "description", "main_description")
    list_display = ("id", "code", "default_localized_title", "is_active", "updated_at")
