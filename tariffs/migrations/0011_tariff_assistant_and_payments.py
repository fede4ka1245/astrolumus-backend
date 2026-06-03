from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tariffs", "0010_tariff_pricing"),
    ]

    operations = [
        migrations.AddField(
            model_name="tariff",
            name="assistant_enabled",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Если выключено — пользователь, у которого активен только этот тариф, "
                    "не может писать ассистенту"
                ),
                verbose_name="Доступ к ассистенту",
            ),
        ),
        migrations.AddField(
            model_name="tariff",
            name="assistant_requests_per_month",
            field=models.PositiveIntegerField(
                default=0,
                help_text="0 — без месячного лимита",
                verbose_name="Запросов к ассистенту в месяц",
            ),
        ),
        migrations.AddField(
            model_name="tariff",
            name="assistant_requests_per_day",
            field=models.PositiveIntegerField(
                default=0,
                help_text="0 — без дневного лимита",
                verbose_name="Запросов к ассистенту в день",
            ),
        ),
        migrations.AddField(
            model_name="tariff",
            name="boosty_url",
            field=models.URLField(
                blank=True,
                null=True,
                max_length=500,
                help_text=(
                    "Куда уходит пользователь по кнопке «Оплатить через Boosty». "
                    "Пустое поле прячет кнопку."
                ),
                verbose_name="Boosty checkout URL",
            ),
        ),
        migrations.AddField(
            model_name="tariff",
            name="boosty_subscription_level_id",
            field=models.CharField(
                blank=True,
                null=True,
                max_length=128,
                help_text=(
                    "Webhook сопоставляет это значение с уровнем подписки в Boosty "
                    "(поле subscription_level.id)."
                ),
                verbose_name="Boosty subscription level id",
            ),
        ),
        migrations.AddField(
            model_name="tariff",
            name="patreon_url",
            field=models.URLField(
                blank=True,
                null=True,
                max_length=500,
                help_text=(
                    "Куда уходит пользователь по кнопке «Оплатить через Patreon». "
                    "Пустое поле прячет кнопку."
                ),
                verbose_name="Patreon checkout URL",
            ),
        ),
        migrations.AddField(
            model_name="tariff",
            name="patreon_tier_id",
            field=models.CharField(
                blank=True,
                null=True,
                max_length=128,
                help_text=(
                    "Webhook сопоставляет это значение с tier id в Patreon "
                    "(data.relationships.currently_entitled_tiers.data[].id)."
                ),
                verbose_name="Patreon tier id",
            ),
        ),
    ]
