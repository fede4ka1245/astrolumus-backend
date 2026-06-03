from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0014_stabilize_recurring_subscription_index_names"),
        ("tariffs", "0011_tariff_assistant_and_payments"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ExternalPaymentEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        choices=[("boosty", "Boosty"), ("patreon", "Patreon")],
                        max_length=16,
                        verbose_name="Провайдер",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        blank=True, default="", max_length=64,
                        verbose_name="Тип события",
                    ),
                ),
                (
                    "external_user_id",
                    models.CharField(
                        blank=True, default="", max_length=128,
                        verbose_name="ID пользователя у провайдера",
                    ),
                ),
                (
                    "external_email",
                    models.EmailField(
                        blank=True, default="", max_length=254, verbose_name="Email",
                    ),
                ),
                (
                    "tier_id",
                    models.CharField(
                        blank=True, default="", max_length=128,
                        verbose_name="Tier / level id",
                    ),
                ),
                ("payload", models.JSONField(default=dict, verbose_name="Payload")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Получен"),
                            ("processed", "Активация создана"),
                            ("unmatched", "Не сопоставлено"),
                            ("invalid", "Неверный payload"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                (
                    "note",
                    models.TextField(blank=True, default="", verbose_name="Комментарий"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Получен"),
                ),
                (
                    "activation",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="external_events",
                        to="tariffs.activationtariff",
                        verbose_name="Созданная активация",
                    ),
                ),
                (
                    "matched_tariff",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="external_events",
                        to="tariffs.tariff",
                        verbose_name="Найденный тариф",
                    ),
                ),
                (
                    "matched_user",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="external_payment_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Найденный пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Внешний платёж (webhook)",
                "verbose_name_plural": "Внешние платежи (webhook'и)",
                "ordering": ("-created_at",),
            },
        ),
    ]
