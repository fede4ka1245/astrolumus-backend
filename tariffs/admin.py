from django.contrib import admin

from rangefilter.filters import DateTimeRangeFilter

from .models import Tariff, ActivationTariff

from utils.multilinguality import LocalizedModelAdmin


@admin.register(Tariff)
class TariffAdmin(LocalizedModelAdmin):
    tolgee_namespace = "tariffs"
    localized_fields = ("title", "description", "public_description")
    list_display = ("id", "default_localized_title", "code", "tariff_group", "created_at", "start_datetime",
                    "end_datetime", "validity_days", "priority_for_default", "tariff_renew_wait")


@admin.register(ActivationTariff)
class ActivationTariffAdmin(admin.ModelAdmin):
    autocomplete_fields = ['user']
    list_filter = ["tariff", ('created_at', DateTimeRangeFilter),]

    def user__email(self, obj):
        return obj.user.email

    def validity_days(self, obj):
        if obj.tariff is None:
            return '-'
        return obj.tariff.validity_days

    list_display = ("id", "user", "user__email", "tariff", "created_at", "validity_days")
    search_fields = ("user__email", )
    readonly_fields = ["user__email", ]
