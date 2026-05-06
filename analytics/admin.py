import csv

from django.contrib import admin
from django.http import HttpResponse
from rangefilter.filters import DateRangeFilter

from .models import (
    AnalyticsPayment,
    AnalyticsUser,
    CurrencyRate,
    Expense,
    ExpenseCategory,
)


def export_csv(modeladmin, request, queryset):
    """Generic CSV export action."""
    meta = modeladmin.model._meta
    field_names = [f.name for f in meta.fields]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={meta.db_table}.csv"
    response.write("\ufeff")  # BOM for Excel UTF-8

    writer = csv.writer(response)
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in field_names])
    return response


export_csv.short_description = "Экспорт в CSV"


class ReadOnlyAdmin(admin.ModelAdmin):
    """Base for read-only analytics tables."""

    actions = [export_csv]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnalyticsUser)
class AnalyticsUserAdmin(ReadOnlyAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "date_joined",
        "last_seen",
        "language",
        "consent_marketing",
    )
    search_fields = ("email", "first_name", "last_name")
    list_filter = (
        "language",
        "consent_marketing",
        ("date_joined", DateRangeFilter),
        ("last_seen", DateRangeFilter),
    )
    date_hierarchy = "date_joined"


@admin.register(AnalyticsPayment)
class AnalyticsPaymentAdmin(ReadOnlyAdmin):
    list_display = (
        "user_email",
        "tariff_name",
        "amount",
        "currency",
        "payment_system",
        "status",
        "is_recurring",
        "created_at",
    )
    search_fields = ("user_email", "tariff_name", "payment_id")
    list_filter = (
        "payment_system",
        "currency",
        "status",
        "is_recurring",
        ("created_at", DateRangeFilter),
    )
    date_hierarchy = "created_at"


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "description",
        "amount",
        "currency",
        "period",
        "is_recurring",
    )
    list_filter = (
        "category",
        "currency",
        "is_recurring",
        ("period", DateRangeFilter),
    )
    search_fields = ("description", "category__name")
    date_hierarchy = "period"
    list_editable = ("amount", "currency", "is_recurring")


@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ("currency", "rate_to_usd", "updated_at")
    list_editable = ("rate_to_usd",)
