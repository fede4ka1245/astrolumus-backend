from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds the AI-assistant quota fields to Tariff.

    These columns already exist in the deployed database (they were created by
    the horo-me/staging schema this environment was migrated from), so the
    field additions are applied to Django's migration *state* only — no SQL is
    emitted against the database. This keeps the model in sync with the
    pre-existing columns without attempting to re-create them.
    """

    dependencies = [
        ("tariffs", "0010_tariff_pricing"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="tariff",
                    name="assistant_enabled",
                    field=models.BooleanField(
                        default=False,
                        help_text=(
                            "Если выключено — пользователь, у которого активен "
                            "только этот тариф, не может писать ассистенту"
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
            ],
        ),
    ]
