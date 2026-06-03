from datetime import date as _date

from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone


User = get_user_model()


class TarotCard(models.Model):
    """A single Rider–Waite–Smith card."""

    ARCANA_MAJOR = "major"
    ARCANA_MINOR = "minor"
    ARCANA_CHOICES = (
        (ARCANA_MAJOR, "Старший Аркан"),
        (ARCANA_MINOR, "Младший Аркан"),
    )

    SUIT_WANDS = "wands"
    SUIT_CUPS = "cups"
    SUIT_SWORDS = "swords"
    SUIT_PENTACLES = "pentacles"
    SUIT_CHOICES = (
        (SUIT_WANDS, "Жезлы"),
        (SUIT_CUPS, "Кубки"),
        (SUIT_SWORDS, "Мечи"),
        (SUIT_PENTACLES, "Пентакли"),
    )

    code = models.SlugField("Код", max_length=64, unique=True)
    name = models.CharField("Название", max_length=128)
    arcana = models.CharField("Аркан", max_length=8, choices=ARCANA_CHOICES)
    suit = models.CharField(
        "Масть", max_length=16, choices=SUIT_CHOICES, blank=True, null=True,
    )
    number = models.IntegerField(
        "Номер", null=True, blank=True,
        help_text="0–21 для Старших Арканов, 1–14 для Младших",
    )
    image_url = models.URLField("URL изображения", max_length=500, blank=True, null=True)
    upright_meaning = models.TextField("Значение прямой")
    reversed_meaning = models.TextField("Значение перевёрнутой")
    keywords = models.JSONField("Ключевые слова", default=list, blank=True)

    class Meta:
        verbose_name = "Карта Таро"
        verbose_name_plural = "Карты Таро"
        ordering = ("arcana", "suit", "number", "name")

    def __str__(self):
        return self.name


class TarotSpread(models.Model):
    """A pre-defined spread (1-card, 3-card, etc)."""

    code = models.SlugField("Код", max_length=64, unique=True)
    name = models.CharField("Название", max_length=128)
    description = models.TextField("Описание", blank=True)
    card_count = models.PositiveIntegerField("Количество карт")
    positions = models.JSONField(
        "Позиции",
        default=list,
        help_text='Список названий позиций, напр. ["Прошлое", "Настоящее", "Будущее"]',
    )
    is_active = models.BooleanField("Активен", default=True)
    sort_order = models.IntegerField("Порядок сортировки", default=0)

    class Meta:
        verbose_name = "Расклад Таро"
        verbose_name_plural = "Расклады Таро"
        ordering = ("sort_order", "card_count", "name")

    def __str__(self):
        return self.name


class TarotReading(models.Model):
    """A single user-completed reading. Drawn cards are persisted as JSON
    (rather than M2M) so the ordering, position, and reversed-state are
    immutable to history even if a TarotCard row is later edited."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tarot_readings",
        verbose_name="Пользователь",
    )
    spread = models.ForeignKey(
        TarotSpread,
        on_delete=models.PROTECT,
        related_name="readings",
        verbose_name="Расклад",
    )
    question = models.TextField("Вопрос", blank=True)
    drawn = models.JSONField(
        "Выпавшие карты",
        default=list,
        help_text="Список объектов {position, card: {...}, reversed: bool}",
    )
    interpretation = models.TextField("Интерпретация", blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Расклад пользователя"
        verbose_name_plural = "Расклады пользователей"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} · {self.spread.code} · {self.created_at:%Y-%m-%d}"


class TarotUsage(models.Model):
    """Per-user Tarot reading counter (mirrors AssistantUsage)."""

    PERIOD_DAILY = "daily"
    PERIOD_MONTHLY = "monthly"
    PERIOD_CHOICES = (
        (PERIOD_DAILY, "День"),
        (PERIOD_MONTHLY, "Месяц"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tarot_usage",
        verbose_name="Пользователь",
    )
    period_type = models.CharField(
        "Тип периода", max_length=10, choices=PERIOD_CHOICES,
    )
    period_start = models.DateField("Начало периода")
    count = models.PositiveIntegerField("Использовано раскладов", default=0)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Использование Таро"
        verbose_name_plural = "Использование Таро"
        unique_together = (("user", "period_type", "period_start"),)
        indexes = [
            models.Index(fields=["user", "period_type", "period_start"]),
        ]

    def __str__(self):
        return f"{self.user_id} / {self.period_type} {self.period_start}: {self.count}"


def period_start_for(period_type: str) -> _date:
    today = timezone.now().date()
    if period_type == TarotUsage.PERIOD_MONTHLY:
        return today.replace(day=1)
    return today


def get_user_quota(user):
    """Compute the highest applicable Tarot quota across the user's currently
    active tariffs. Returns dict with keys: enabled, monthly, daily.
    `monthly`/`daily` of 0 means unlimited (when enabled).
    """
    from tariffs.models import Tariff

    if not user or not user.is_authenticated:
        return {"enabled": False, "monthly": 0, "daily": 0}

    tariffs = list(Tariff.objects.get_user_tariffs(user))
    enabled = [t for t in tariffs if getattr(t, "tarot_enabled", False)]
    if not enabled:
        return {"enabled": False, "monthly": 0, "daily": 0}

    monthly_values = [t.tarot_requests_per_month for t in enabled]
    daily_values = [t.tarot_requests_per_day for t in enabled]
    monthly = 0 if 0 in monthly_values else max(monthly_values, default=0)
    daily = 0 if 0 in daily_values else max(daily_values, default=0)
    return {"enabled": True, "monthly": monthly, "daily": daily}


def get_usage_snapshot(user):
    quota = get_user_quota(user)
    monthly_usage = 0
    daily_usage = 0
    if user and user.is_authenticated:
        m_row = TarotUsage.objects.filter(
            user=user,
            period_type=TarotUsage.PERIOD_MONTHLY,
            period_start=period_start_for(TarotUsage.PERIOD_MONTHLY),
        ).first()
        d_row = TarotUsage.objects.filter(
            user=user,
            period_type=TarotUsage.PERIOD_DAILY,
            period_start=period_start_for(TarotUsage.PERIOD_DAILY),
        ).first()
        monthly_usage = m_row.count if m_row else 0
        daily_usage = d_row.count if d_row else 0

    monthly_limit = quota["monthly"]
    daily_limit = quota["daily"]
    monthly_remaining = (
        None if monthly_limit == 0 else max(monthly_limit - monthly_usage, 0)
    )
    daily_remaining = (
        None if daily_limit == 0 else max(daily_limit - daily_usage, 0)
    )

    return {
        "enabled": quota["enabled"],
        "monthly": {
            "used": monthly_usage,
            "limit": monthly_limit,
            "remaining": monthly_remaining,
        },
        "daily": {
            "used": daily_usage,
            "limit": daily_limit,
            "remaining": daily_remaining,
        },
    }


@transaction.atomic
def try_consume(user) -> dict:
    """Atomically check the Tarot quota and increment counters if there's
    room. Returns:
        {"ok": True, "snapshot": {...}}  on success
        {"ok": False, "reason": "...", "snapshot": {...}}  if blocked
    """
    snapshot = get_usage_snapshot(user)
    if not snapshot["enabled"]:
        return {"ok": False, "reason": "no_access", "snapshot": snapshot}

    monthly_remaining = snapshot["monthly"]["remaining"]
    daily_remaining = snapshot["daily"]["remaining"]
    if monthly_remaining is not None and monthly_remaining <= 0:
        return {"ok": False, "reason": "monthly_exhausted", "snapshot": snapshot}
    if daily_remaining is not None and daily_remaining <= 0:
        return {"ok": False, "reason": "daily_exhausted", "snapshot": snapshot}

    for period_type in (TarotUsage.PERIOD_DAILY, TarotUsage.PERIOD_MONTHLY):
        usage, _ = (
            TarotUsage.objects
            .select_for_update()
            .get_or_create(
                user=user,
                period_type=period_type,
                period_start=period_start_for(period_type),
                defaults={"count": 0},
            )
        )
        usage.count = (usage.count or 0) + 1
        usage.save(update_fields=["count", "updated_at"])

    return {"ok": True, "snapshot": get_usage_snapshot(user)}
