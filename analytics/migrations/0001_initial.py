from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ExpenseCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="Название")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
            ],
            options={
                "verbose_name": "Категория расходов",
                "verbose_name_plural": "Категории расходов",
                "db_table": "expense_categories",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="CurrencyRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("currency", models.CharField(max_length=3, unique=True, verbose_name="Валюта")),
                ("rate_to_usd", models.DecimalField(decimal_places=6, help_text="1 единица этой валюты = X USD", max_digits=12, verbose_name="Курс к USD")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлён")),
            ],
            options={
                "verbose_name": "Курс валюты",
                "verbose_name_plural": "Курсы валют",
                "db_table": "currency_rates",
            },
        ),
        migrations.CreateModel(
            name="MetabaseDashboard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="Название")),
                ("metabase_id", models.PositiveIntegerField(help_text="Номер дашборда из URL в Metabase (например, 1)", verbose_name="ID дашборда в Metabase")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
            ],
            options={
                "verbose_name": "Metabase дашборд",
                "verbose_name_plural": "Metabase дашборды",
                "db_table": "metabase_dashboards",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=255, verbose_name="Описание")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Сумма")),
                ("currency", models.CharField(choices=[("USD", "USD"), ("EUR", "EUR"), ("RUB", "RUB"), ("BYN", "BYN")], default="USD", max_length=3, verbose_name="Валюта")),
                ("period", models.DateField(help_text="Первый день месяца, к которому относится расход", verbose_name="Период (месяц)")),
                ("is_recurring", models.BooleanField(default=False, help_text="Повторяется ли этот расход каждый месяц", verbose_name="Ежемесячный")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлён")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expenses", to="analytics.expensecategory", verbose_name="Категория")),
            ],
            options={
                "verbose_name": "Расход",
                "verbose_name_plural": "Расходы",
                "db_table": "expenses",
                "ordering": ["-period", "category"],
            },
        ),
    ]
