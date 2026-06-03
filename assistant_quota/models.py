from datetime import date as _date

from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone

from utils.multilinguality import get_default_language_value_admin

User = get_user_model()


class RequestPack(models.Model):
    code = models.SlugField("Код", unique=True)
    title = models.JSONField("Название")
    description = models.JSONField("Описание", blank=True, default=dict)
    requests_count = models.PositiveIntegerField("Количество запросов")
    price_rub = models.DecimalField("Цена (RUB)", max_digits=10, decimal_places=2, null=True, blank=True)
    price_byn = models.DecimalField("Цена (BYN)", max_digits=10, decimal_places=2, null=True, blank=True)
    price_usd = models.DecimalField("Цена (USD)", max_digits=10, decimal_places=2, null=True, blank=True)
    price_eur = models.DecimalField("Цена (EUR)", max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField("Активен", default=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    def __str__(self):
        return get_default_language_value_admin(self.title) or self.code

    class Meta:
        verbose_name = "Пак запросов"
        verbose_name_plural = "Паки запросов"
        ordering = ("sort_order", "id")


class AssistantUsage(models.Model):
    """Per-user request counter for the AI assistant.

    A user gets one row per (period_type, period_start). Daily and monthly
    counters are tracked independently; consume() increments BOTH so callers
    can compare against either limit.
    """

    PERIOD_DAILY = "daily"
    PERIOD_MONTHLY = "monthly"

    PERIOD_CHOICES = (
        (PERIOD_DAILY, "День"),
        (PERIOD_MONTHLY, "Месяц"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assistant_usage",
        verbose_name="Пользователь",
    )
    period_type = models.CharField(
        "Тип периода", max_length=10, choices=PERIOD_CHOICES,
    )
    period_start = models.DateField("Начало периода")
    count = models.PositiveIntegerField("Использовано запросов", default=0)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Использование ассистента"
        verbose_name_plural = "Использование ассистента"
        unique_together = (("user", "period_type", "period_start"),)
        indexes = [
            models.Index(fields=["user", "period_type", "period_start"]),
        ]

    def __str__(self):
        return f"{self.user_id} / {self.period_type} {self.period_start}: {self.count}"


def period_start_for(period_type: str) -> _date:
    today = timezone.now().date()
    if period_type == AssistantUsage.PERIOD_MONTHLY:
        return today.replace(day=1)
    return today


def get_user_quota(user):
    """Compute the highest applicable assistant quota across the user's
    currently active tariffs. Returns dict with keys:
        enabled (bool), monthly (int), daily (int).
    `monthly`/`daily` of 0 means unlimited (when enabled).
    """
    # Lazy import to avoid circular tariffs<->assistant_quota at import time.
    from tariffs.models import Tariff

    if not user or not user.is_authenticated:
        return {"enabled": False, "monthly": 0, "daily": 0}

    tariffs = list(Tariff.objects.get_user_tariffs(user))
    enabled_tariffs = [t for t in tariffs if t.assistant_enabled]
    if not enabled_tariffs:
        return {"enabled": False, "monthly": 0, "daily": 0}

    # If any enabled tariff has 0 (= unlimited), 0 wins → no cap.
    monthly_values = [t.assistant_requests_per_month for t in enabled_tariffs]
    daily_values = [t.assistant_requests_per_day for t in enabled_tariffs]
    monthly = 0 if 0 in monthly_values else max(monthly_values, default=0)
    daily = 0 if 0 in daily_values else max(daily_values, default=0)
    return {"enabled": True, "monthly": monthly, "daily": daily}


def get_usage_snapshot(user):
    """Returns full status for the assistant quota of the current user."""
    quota = get_user_quota(user)
    monthly_usage = 0
    daily_usage = 0
    if user and user.is_authenticated:
        m_row = AssistantUsage.objects.filter(
            user=user,
            period_type=AssistantUsage.PERIOD_MONTHLY,
            period_start=period_start_for(AssistantUsage.PERIOD_MONTHLY),
        ).first()
        d_row = AssistantUsage.objects.filter(
            user=user,
            period_type=AssistantUsage.PERIOD_DAILY,
            period_start=period_start_for(AssistantUsage.PERIOD_DAILY),
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
    """Atomically check the quota and increment counters if there's room.

    Returns:
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

    # Increment both counters under the same transaction.
    for period_type in (AssistantUsage.PERIOD_DAILY, AssistantUsage.PERIOD_MONTHLY):
        usage, _ = (
            AssistantUsage.objects
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
