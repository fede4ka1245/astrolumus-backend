from django.db import models


class ExpenseCategory(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    description = models.TextField("Описание", blank=True)

    class Meta:
        db_table = "expense_categories"
        verbose_name = "Категория расходов"
        verbose_name_plural = "Категории расходов"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Expense(models.Model):
    class Currencies(models.TextChoices):
        USD = "USD", "USD"
        EUR = "EUR", "EUR"
        RUB = "RUB", "RUB"
        BYN = "BYN", "BYN"

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="expenses",
        verbose_name="Категория",
    )
    description = models.CharField("Описание", max_length=255)
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=2)
    currency = models.CharField(
        "Валюта",
        max_length=3,
        choices=Currencies.choices,
        default=Currencies.USD,
    )
    period = models.DateField(
        "Период (месяц)",
        help_text="Первый день месяца, к которому относится расход",
    )
    is_recurring = models.BooleanField(
        "Ежемесячный",
        default=False,
        help_text="Повторяется ли этот расход каждый месяц",
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        db_table = "expenses"
        verbose_name = "Расход"
        verbose_name_plural = "Расходы"
        ordering = ["-period", "category"]

    def __str__(self):
        return f"{self.category} — {self.amount} {self.currency} ({self.period:%Y-%m})"


class CurrencyRate(models.Model):
    """Курсы валют к USD для конвертации в P&L."""

    currency = models.CharField("Валюта", max_length=3, unique=True)
    rate_to_usd = models.DecimalField(
        "Курс к USD",
        max_digits=12,
        decimal_places=6,
        help_text="1 единица этой валюты = X USD",
    )
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        db_table = "currency_rates"
        verbose_name = "Курс валюты"
        verbose_name_plural = "Курсы валют"

    def __str__(self):
        return f"{self.currency} → {self.rate_to_usd} USD"


# ------------------------------------------------------------------
# Read-only models backed by the analytics (cold) database.
# managed = False — Django will NOT create/alter these tables;
# the sync task (tasks.py) creates them from the main DB schema.
# ------------------------------------------------------------------

class AnalyticsUser(models.Model):
    """Read-only mirror of users_user in analytics DB."""
    email = models.EmailField()
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    date_joined = models.DateTimeField(null=True)
    last_seen = models.DateTimeField(null=True)
    language = models.CharField(max_length=10, blank=True)
    consent_marketing = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "users_user"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email


class AnalyticsPayment(models.Model):
    """Read-only mirror of payment_records in analytics DB."""
    user_id = models.IntegerField(null=True)
    user_email = models.EmailField(blank=True, null=True)
    tariff_name = models.CharField(max_length=255, blank=True, null=True)
    payment_system = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20)
    is_recurring = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(null=True)

    class Meta:
        managed = False
        db_table = "payment_records"
        verbose_name = "Платёж"
        verbose_name_plural = "Платящие пользователи"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_email} — {self.amount} {self.currency}"


class MetabaseDashboard(models.Model):
    name = models.CharField("Название", max_length=100)
    metabase_id = models.PositiveIntegerField(
        "ID дашборда в Metabase",
        help_text="Номер дашборда из URL в Metabase (например, 1)",
    )
    description = models.TextField("Описание", blank=True)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        db_table = "metabase_dashboards"
        verbose_name = "Metabase дашборд"
        verbose_name_plural = "Metabase дашборды"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name
