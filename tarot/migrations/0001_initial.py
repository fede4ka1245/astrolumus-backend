from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TarotCard",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID",
                    ),
                ),
                ("code", models.SlugField(max_length=64, unique=True, verbose_name="Код")),
                ("name", models.CharField(max_length=128, verbose_name="Название")),
                (
                    "arcana",
                    models.CharField(
                        choices=[("major", "Старший Аркан"), ("minor", "Младший Аркан")],
                        max_length=8,
                        verbose_name="Аркан",
                    ),
                ),
                (
                    "suit",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("wands", "Жезлы"),
                            ("cups", "Кубки"),
                            ("swords", "Мечи"),
                            ("pentacles", "Пентакли"),
                        ],
                        max_length=16,
                        null=True,
                        verbose_name="Масть",
                    ),
                ),
                (
                    "number",
                    models.IntegerField(
                        blank=True,
                        help_text="0–21 для Старших Арканов, 1–14 для Младших",
                        null=True,
                        verbose_name="Номер",
                    ),
                ),
                (
                    "image_url",
                    models.URLField(blank=True, max_length=500, null=True, verbose_name="URL изображения"),
                ),
                ("upright_meaning", models.TextField(verbose_name="Значение прямой")),
                ("reversed_meaning", models.TextField(verbose_name="Значение перевёрнутой")),
                ("keywords", models.JSONField(blank=True, default=list, verbose_name="Ключевые слова")),
            ],
            options={
                "verbose_name": "Карта Таро",
                "verbose_name_plural": "Карты Таро",
                "ordering": ("arcana", "suit", "number", "name"),
            },
        ),
        migrations.CreateModel(
            name="TarotSpread",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID",
                    ),
                ),
                ("code", models.SlugField(max_length=64, unique=True, verbose_name="Код")),
                ("name", models.CharField(max_length=128, verbose_name="Название")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                ("card_count", models.PositiveIntegerField(verbose_name="Количество карт")),
                (
                    "positions",
                    models.JSONField(
                        default=list,
                        help_text='Список названий позиций, напр. ["Прошлое", "Настоящее", "Будущее"]',
                        verbose_name="Позиции",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
                ("sort_order", models.IntegerField(default=0, verbose_name="Порядок сортировки")),
            ],
            options={
                "verbose_name": "Расклад Таро",
                "verbose_name_plural": "Расклады Таро",
                "ordering": ("sort_order", "card_count", "name"),
            },
        ),
        migrations.CreateModel(
            name="TarotReading",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID",
                    ),
                ),
                ("question", models.TextField(blank=True, verbose_name="Вопрос")),
                (
                    "drawn",
                    models.JSONField(
                        default=list,
                        help_text="Список объектов {position, card: {...}, reversed: bool}",
                        verbose_name="Выпавшие карты",
                    ),
                ),
                ("interpretation", models.TextField(blank=True, verbose_name="Интерпретация")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                (
                    "spread",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="readings",
                        to="tarot.tarotspread",
                        verbose_name="Расклад",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="tarot_readings",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Расклад пользователя",
                "verbose_name_plural": "Расклады пользователей",
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(
                        fields=["user", "-created_at"], name="tarot_tarot_user_id_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="TarotUsage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID",
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
                    models.PositiveIntegerField(default=0, verbose_name="Использовано раскладов"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="tarot_usage",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Использование Таро",
                "verbose_name_plural": "Использование Таро",
                "indexes": [
                    models.Index(
                        fields=["user", "period_type", "period_start"],
                        name="tarot_taro_user_id_period_idx",
                    ),
                ],
                "unique_together": {("user", "period_type", "period_start")},
            },
        ),
    ]
