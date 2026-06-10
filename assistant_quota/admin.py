from django.contrib import admin
from django.utils.html import strip_tags

from rangefilter.filters import DateRangeFilter

from utils.multilinguality import LocalizedModelAdmin, get_default_language_value_admin
from .models import (
    AssistantUsage,
    RequestBalance,
    RequestPack,
    RequestPackPurchase,
    Subscription,
    SubscriptionPayment,
    SubscriptionPlan,
)


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
    list_display = (
        "code", "localized_title", "requests_count", "price_rub",
        "discount_percent", "is_popular", "is_active", "sort_order",
    )
    list_editable = ("discount_percent", "is_popular", "is_active", "sort_order")
    search_fields = ("code",)

    @admin.display(description="Название")
    def localized_title(self, obj):
        value = get_default_language_value_admin(obj.title)
        return strip_tags(value) if value else "-"


@admin.register(RequestBalance)
class RequestBalanceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_email", "balance", "free_grant_done", "updated_at")
    search_fields = ("user__email",)
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Email", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email if obj.user else "-"


@admin.register(RequestPackPurchase)
class RequestPackPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "pack", "requests_count", "amount", "currency",
        "status", "credited", "created_at",
    )
    list_filter = ("status", "credited", "provider", ("created_at", DateRangeFilter))
    search_fields = ("user__email", "provider_payment_id", "pack__code")
    autocomplete_fields = ("user", "pack")
    readonly_fields = ("provider_payment_id", "confirmation_url", "created_at", "updated_at")


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(LocalizedModelAdmin):
    localized_fields = ("title", "description")
    list_display = (
        "code", "localized_title", "months", "price_rub",
        "is_popular", "is_active", "sort_order",
    )
    list_editable = ("price_rub", "is_popular", "is_active", "sort_order")
    search_fields = ("code",)

    @admin.display(description="Название")
    def localized_title(self, obj):
        value = get_default_language_value_admin(obj.title)
        return strip_tags(value) if value else "-"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "plan", "status", "current_period_end",
        "auto_renew", "created_at",
    )
    list_filter = ("status", "auto_renew", "provider", ("current_period_end", DateRangeFilter))
    search_fields = ("user__email", "plan__code", "provider_payment_method_id")
    autocomplete_fields = ("user", "plan")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "plan", "subscription", "amount", "currency",
        "status", "is_renewal", "applied", "created_at",
    )
    list_filter = ("status", "is_renewal", "applied", "provider", ("created_at", DateRangeFilter))
    search_fields = ("user__email", "provider_payment_id", "plan__code")
    autocomplete_fields = ("user", "plan", "subscription")
    readonly_fields = (
        "provider_payment_id", "provider_payment_method_id",
        "confirmation_url", "applied", "created_at", "updated_at",
    )
