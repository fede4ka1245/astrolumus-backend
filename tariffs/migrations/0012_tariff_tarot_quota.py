from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tariffs", "0011_tariff_assistant_and_payments"),
    ]

    operations = [
        migrations.AddField(
            model_name="tariff",
            name="tarot_enabled",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Если выключено — пользователь, у которого активен только этот тариф, "
                    "не может делать расклады"
                ),
                verbose_name="Доступ к раскладам Таро",
            ),
        ),
        migrations.AddField(
            model_name="tariff",
            name="tarot_requests_per_month",
            field=models.PositiveIntegerField(
                default=0,
                help_text="0 — без месячного лимита",
                verbose_name="Раскладов Таро в месяц",
            ),
        ),
        migrations.AddField(
            model_name="tariff",
            name="tarot_requests_per_day",
            field=models.PositiveIntegerField(
                default=0,
                help_text="0 — без дневного лимита",
                verbose_name="Раскладов Таро в день",
            ),
        ),
    ]
