from django.contrib import admin
from django.utils.html import strip_tags

from rangefilter.filters import DateRangeFilter

from utils.multilinguality import LocalizedModelAdmin, get_default_language_value_admin
from .models import AssistantUsage, RequestPack


@admin.register(AssistantUsage)
class AssistantUsageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_email", "period_type", "period_start", "count", "updated_at")
    list_filter = ("period_type", ("period_start", DateRangeFilter))
    search_fields = ("user__email",)
    autocomplete_fields = ("user",)
    readonly_fields = ("updated_at",)

    @admin.display(description="Email", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email if obj.user else "-"


@admin.register(RequestPack)
class RequestPackAdmin(LocalizedModelAdmin):
    localized_fields = ("title", "description")
    list_display = ("code", "localized_title", "requests_count", "price_rub", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    search_fields = ("code",)

    @admin.display(description="Название")
    def localized_title(self, obj):
        value = get_default_language_value_admin(obj.title)
        return strip_tags(value) if value else "-"
