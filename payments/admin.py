from django.contrib import admin

from .models import Order, PaymentSettings, PaymentRecord, RecurringSubscription


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ("platform", "enabled", "updated_at")
    list_filter = ("enabled", "platform")
    list_editable = ("enabled",)
    search_fields = ("platform",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "amount", "pay_system", "payload")


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    """Админка для записей об оплатах с поиском по всем полям"""
    
    list_display = (
        "id",
        "created_at",
        "tariff_name",
        "payment_system",
        "amount",
        "currency",
        "status",
        "is_recurring",
        "user_full_name",
        "user_email",
        "merchant_full_name",
        "merchant_email",
    )
    
    list_filter = (
        "payment_system",
        "status",
        "currency",
        "is_recurring",
        "created_at",
    )
    
    search_fields = (
        # Поиск по Имени и Фамилии в приложении
        "user_first_name",
        "user_last_name",
        # Поиск по почте в приложении
        "user_email",
        # Поиск по Имени и Фамилии при оплате (merchant)
        "merchant_first_name",
        "merchant_last_name",
        # Поиск по почте при оплате (merchant)
        "merchant_email",
        # Поиск по названию тарифа
        "tariff_name",
        # Дополнительные поля для поиска
        "payment_id",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    
    readonly_fields = (
        "created_at",
        "payment_id",
        "raw_data",
    )
    
    date_hierarchy = "created_at"
    
    ordering = ("-created_at",)
    
    fieldsets = (
        ("Основная информация", {
            "fields": ("tariff_name", "payment_system", "amount", "currency", "status", "is_recurring", "payment_id", "created_at")
        }),
        ("Пользователь в приложении", {
            "fields": ("user", "user_first_name", "user_last_name", "user_email")
        }),
        ("Данные при оплате (merchant)", {
            "fields": ("merchant_first_name", "merchant_last_name", "merchant_email")
        }),
        ("Связанные объекты", {
            "fields": ("order",),
            "classes": ("collapse",)
        }),
        ("Сырые данные", {
            "fields": ("raw_data",),
            "classes": ("collapse",)
        }),
    )
    
    def user_full_name(self, obj):
        """Полное имя пользователя в приложении"""
        if obj.user_first_name or obj.user_last_name:
            return f"{obj.user_first_name or ''} {obj.user_last_name or ''}".strip()
        return "-"
    user_full_name.short_description = "Имя в приложении"
    user_full_name.admin_order_field = "user_first_name"
    
    def merchant_full_name(self, obj):
        """Полное имя при оплате"""
        if obj.merchant_first_name or obj.merchant_last_name:
            return f"{obj.merchant_first_name or ''} {obj.merchant_last_name or ''}".strip()
        return "-"
    merchant_full_name.short_description = "Имя при оплате"
    merchant_full_name.admin_order_field = "merchant_first_name"


@admin.register(RecurringSubscription)
class RecurringSubscriptionAdmin(admin.ModelAdmin):
    """Админка для рекурентных подписок"""
    
    list_display = (
        "id",
        "user",
        "tariff",
        "payment_system",
        "status",
        "amount",
        "currency",
        "current_period_start",
        "current_period_end",
        "cancel_at_period_end",
        "created_at",
    )
    
    list_filter = (
        "payment_system",
        "status",
        "currency",
        "cancel_at_period_end",
        "created_at",
    )
    
    search_fields = (
        "subscription_id",
        "customer_id",
        "user__email",
        "user__first_name",
        "user__last_name",
        "tariff__code",
        "tariff__title",
    )
    
    readonly_fields = (
        "created_at",
        "updated_at",
        "subscription_id",
        "customer_id",
        "metadata",
    )
    
    date_hierarchy = "created_at"
    
    ordering = ("-created_at",)
    
    fieldsets = (
        ("Основная информация", {
            "fields": (
                "user",
                "tariff",
                "order",
                "payment_system",
                "status",
                "subscription_id",
                "customer_id",
            )
        }),
        ("Финансовая информация", {
            "fields": ("amount", "currency")
        }),
        ("Периоды подписки", {
            "fields": (
                "current_period_start",
                "current_period_end",
                "cancel_at_period_end",
                "canceled_at",
            )
        }),
        ("Метаданные", {
            "fields": ("metadata",),
            "classes": ("collapse",)
        }),
        ("Даты", {
            "fields": ("created_at", "updated_at")
        }),
    )
