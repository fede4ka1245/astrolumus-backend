from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AssistantUsage",
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
                    "period_type",
                    models.CharField(
                        choices=[("daily", "День"), ("monthly", "Месяц")],
                        max_length=10,
                        verbose_name="Тип периода",
                    ),
                ),
                ("period_start", models.DateField(verbose_name="Начало периода")),
                (
                    "count",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Использовано запросов"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Обновлено"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="assistant_usage",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Использование ассистента",
                "verbose_name_plural": "Использование ассистента",
                "indexes": [
                    models.Index(
                        fields=["user", "period_type", "period_start"],
                        name="assistant_q_user_id_3a4d3b_idx",
                    )
                ],
                "unique_together": {("user", "period_type", "period_start")},
            },
        ),
    ]
