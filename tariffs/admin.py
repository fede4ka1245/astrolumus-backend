from django.contrib import admin

from rangefilter.filters import DateTimeRangeFilter

from .models import Tariff, ActivationTariff

from utils.multilinguality import LocalizedModelAdmin


@admin.register(Tariff)
class TariffAdmin(LocalizedModelAdmin):
    tolgee_namespace = "tariffs"
    localized_fields = ("title", "description", "public_description")
    list_display = ("id", "default_localized_title", "code", "tariff_group", "created_at", "start_datetime",
                    "end_datetime", "validity_days", "priority_for_default", "tariff_renew_wait",
                    "assistant_enabled", "assistant_requests_per_month", "assistant_requests_per_day")
    list_filter = ("public", "assistant_enabled", "tarot_enabled", "tariff_group")
    search_fields = ("code", "boosty_subscription_level_id", "patreon_tier_id")
    fieldsets = (
        (None, {
            "fields": ("title", "description", "public_description", "code", "public",
                       "tariff_group", "tariff_renew_wait", "can_work_with_another"),
        }),
        ("Действие", {
            "fields": ("start_datetime", "end_datetime", "validity_days", "priority_for_default"),
        }),
        ("Ограничения", {
            "fields": ("restriction_forum", "restriction_astroprocessor",
                       "restriction_number_of_topic", "restriction_number_of_horoscopes",
                       "restriction_astroprocessor_validity_days"),
        }),
        ("Цены", {
            "fields": ("price_rub", "price_byn", "price_usd", "price_eur", "tariff_link"),
        }),
        ("Ассистент", {
            "fields": ("assistant_enabled", "assistant_requests_per_month",
                       "assistant_requests_per_day"),
            "description": "Лимиты для AI-ассистента. 0 = без ограничений.",
        }),
        ("Таро", {
            "fields": ("tarot_enabled", "tarot_requests_per_month",
                       "tarot_requests_per_day"),
            "description": "Лимиты раскладов Таро. 0 = без ограничений.",
        }),
        ("Boosty / Patreon", {
            "fields": ("boosty_url", "boosty_subscription_level_id",
                       "patreon_url", "patreon_tier_id"),
            "description": "URL'ы попадают на кнопки оплаты на сайте; *_id используются "
                           "webhook'ами для сопоставления внешней подписки с тарифом.",
        }),
    )


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
