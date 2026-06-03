from django.contrib import admin

from .models import TarotCard, TarotSpread, TarotReading, TarotUsage


@admin.register(TarotCard)
class TarotCardAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "arcana", "suit", "number")
    list_filter = ("arcana", "suit")
    search_fields = ("code", "name")
    ordering = ("arcana", "suit", "number", "name")


@admin.register(TarotSpread)
class TarotSpreadAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "card_count", "is_active", "sort_order")
    list_filter = ("is_active",)
    list_editable = ("is_active", "sort_order")
    search_fields = ("code", "name")
    ordering = ("sort_order", "card_count", "name")


@admin.register(TarotReading)
class TarotReadingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "spread", "created_at")
    list_filter = ("spread", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "question")
    autocomplete_fields = ("user", "spread")
    readonly_fields = ("drawn", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(TarotUsage)
class TarotUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "period_type", "period_start", "count", "updated_at")
    list_filter = ("period_type", "period_start")
    search_fields = ("user__email",)
    autocomplete_fields = ("user",)
    readonly_fields = ("updated_at",)
    ordering = ("-period_start",)
