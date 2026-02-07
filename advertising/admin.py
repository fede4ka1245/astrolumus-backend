from django.contrib import admin

from .models import BannerType, Banner, BannerImage, Tag

from utils.multilinguality import LocalizedModelAdmin


@admin.register(BannerType)
class BannerTypeAdmin(admin.ModelAdmin):
    list_display = ("title", "alias",)
    search_fields = ("title", "alias")


@admin.register(Banner)
class BannerAdmin(LocalizedModelAdmin):

    @staticmethod
    def get_banner_type(obj):
        return "\n".join([p.title for p in obj.banner_type.all()])

    localized_fields = ("title", "description", "video_link")
    list_display = ("default_localized_title", "get_banner_type",)
    list_filter = ("banner_type",)


@admin.register(Tag)
class TagAdmin(LocalizedModelAdmin):
    localized_fields = ("title",)
    list_display = ("default_localized_title", "alias")
    search_fields = ("alias",)


admin.site.register(BannerImage)
