from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone

from utils.multilinguality import get_default_language_value_admin

try:  # Prefer calendar-accurate month math when available.
    from dateutil.relativedelta import relativedelta
except ImportError:  # pragma: no cover - fallback
    relativedelta = None

from datetime import timedelta

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
    discount_percent = models.PositiveSmallIntegerField("Скидка (%)", null=True, blank=True)
    is_popular = models.BooleanField("Популярный", default=False)
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
    """Legacy per-user request counter for the AI assistant.

    No longer the source of truth for assistant quota (replaced by
    RequestBalance). Kept so historical rows and admin views survive; new code
    must not depend on it.
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


class RequestBalance(models.Model):
    """Pure credit balance of AI-assistant requests for a single user.

    Created lazily on first access; the very first creation grants 2 free
    requests (the "2 free after registration" bonus). The balance never
    resets — it only goes up via pack purchases and down via consumption.
    """

    FREE_GRANT = 2

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="request_balance",
        verbose_name="Пользователь",
    )
    balance = models.PositiveIntegerField("Баланс запросов", default=0)
    free_grant_done = models.BooleanField("Бонус начислен", default=False)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Баланс запросов"
        verbose_name_plural = "Балансы запросов"

    def __str__(self):
        return f"{self.user_id}: {self.balance}"

    @classmethod
    def get_or_create_for(cls, user):
        """Return the user's balance row, creating it (with the 2 free
        requests granted) on first access. Atomic and race-safe."""
        with transaction.atomic():
            obj, created = cls.objects.select_for_update().get_or_create(
                user=user,
                defaults={"balance": cls.FREE_GRANT, "free_grant_done": True},
            )
        return obj


class RequestPackPurchase(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Ожидает оплаты"),
        (STATUS_SUCCEEDED, "Оплачен"),
        (STATUS_CANCELED, "Отменён"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="request_pack_purchases",
        verbose_name="Пользователь",
    )
    pack = models.ForeignKey(
        RequestPack,
        on_delete=models.PROTECT,
        related_name="purchases",
        verbose_name="Пак",
    )
    requests_count = models.PositiveIntegerField("Количество запросов")
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    currency = models.CharField("Валюта", max_length=8, default="RUB")
    status = models.CharField(
        "Статус", max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING,
    )
    provider = models.CharField("Провайдер", max_length=32, default="yookassa")
    provider_payment_id = models.CharField(
        "ID платежа провайдера", max_length=128, blank=True, db_index=True,
    )
    confirmation_url = models.TextField("URL подтверждения", blank=True)
    credited = models.BooleanField("Зачислено", default=False)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Покупка пака запросов"
        verbose_name_plural = "Покупки паков запросов"
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"#{self.id} {self.user_id} {self.pack_id} {self.status}"

    def mark_succeeded_and_credit(self):
        """Idempotently mark the purchase paid and credit the user's balance.

        Safe to call multiple times (the webhook may fire more than once):
        the credit only happens on the first call thanks to the `credited`
        flag, checked under a row lock.
        """
        with transaction.atomic():
            purchase = (
                RequestPackPurchase.objects.select_for_update().get(pk=self.pk)
            )
            if purchase.credited:
                return purchase

            balance = RequestBalance.get_or_create_for(purchase.user)
            balance = (
                RequestBalance.objects.select_for_update().get(pk=balance.pk)
            )
            balance.balance = (balance.balance or 0) + purchase.requests_count
            balance.save(update_fields=["balance", "updated_at"])

            purchase.status = RequestPackPurchase.STATUS_SUCCEEDED
            purchase.credited = True
            purchase.save(update_fields=["status", "credited", "updated_at"])

            # Reflect changes onto the instance the caller holds.
            self.status = purchase.status
            self.credited = purchase.credited
            return purchase


def _is_unlimited(user) -> bool:
    unlimited_emails = getattr(settings, "ASSISTANT_UNLIMITED_EMAILS", set())
    user_email = (getattr(user, "email", "") or "").strip().lower()
    return bool(user_email) and user_email in unlimited_emails


def get_usage_snapshot(user) -> dict:
    """Balance-based status of the assistant quota for the given user.

    Returns {"enabled": bool, "unlimited": bool, "balance": int}.
    """
    if not user or not user.is_authenticated:
        return {"enabled": False, "unlimited": False, "balance": 0}

    if _is_unlimited(user):
        return {"enabled": True, "unlimited": True, "balance": 0}

    balance = RequestBalance.get_or_create_for(user)
    return {"enabled": True, "unlimited": False, "balance": balance.balance}


def try_consume(user) -> dict:
    """Atomically debit one request from the user's balance.

    Returns:
        {"ok": True, "snapshot": {...}}              on success
        {"ok": False, "reason": "...", "snapshot"?}  if blocked
    """
    if not user or not user.is_authenticated:
        return {"ok": False, "reason": "no_auth"}

    if _is_unlimited(user):
        return {"ok": True, "snapshot": {"enabled": True, "unlimited": True, "balance": 0}}

    with transaction.atomic():
        balance = RequestBalance.get_or_create_for(user)
        balance = RequestBalance.objects.select_for_update().get(pk=balance.pk)
        if balance.balance <= 0:
            return {
                "ok": False,
                "reason": "no_balance",
                "snapshot": {"enabled": True, "unlimited": False, "balance": 0},
            }
        balance.balance -= 1
        balance.save(update_fields=["balance", "updated_at"])
        return {
            "ok": True,
            "snapshot": {"enabled": True, "unlimited": False, "balance": balance.balance},
        }


def _add_months(start, months):
    """Add `months` calendar months to a datetime, preferring dateutil."""
    if relativedelta is not None:
        return start + relativedelta(months=months)
    return start + timedelta(days=30 * months)


# Astroprocessor sections unlocked by an active subscription.
UNLOCKED_SECTIONS = ["ashtakavarga", "varshapkhala", "rectification"]


class SubscriptionPlan(models.Model):
    """A purchasable recurring subscription tier (e.g. 3/6/12 months).

    Unlocks the astroprocessor sections in UNLOCKED_SECTIONS; unrelated to the
    AI-assistant request quota.
    """

    code = models.SlugField("Код", unique=True)
    months = models.PositiveSmallIntegerField("Длительность (мес.)")
    title = models.JSONField("Название")
    description = models.JSONField("Описание", blank=True, default=dict)
    price_rub = models.DecimalField("Цена (RUB)", max_digits=10, decimal_places=2, null=True, blank=True)
    price_byn = models.DecimalField("Цена (BYN)", max_digits=10, decimal_places=2, null=True, blank=True)
    price_usd = models.DecimalField("Цена (USD)", max_digits=10, decimal_places=2, null=True, blank=True)
    price_eur = models.DecimalField("Цена (EUR)", max_digits=10, decimal_places=2, null=True, blank=True)
    is_popular = models.BooleanField("Популярный", default=False)
    is_active = models.BooleanField("Активен", default=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    def __str__(self):
        return get_default_language_value_admin(self.title) or self.code

    class Meta:
        verbose_name = "Тариф подписки"
        verbose_name_plural = "Тарифы подписки"
        ordering = ("sort_order", "id")


class Subscription(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_PAST_DUE = "past_due"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Ожидает оплаты"),
        (STATUS_ACTIVE, "Активна"),
        (STATUS_CANCELED, "Отменена"),
        (STATUS_EXPIRED, "Истекла"),
        (STATUS_PAST_DUE, "Просрочена"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Пользователь",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        verbose_name="Тариф",
    )
    status = models.CharField(
        "Статус", max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING,
    )
    current_period_start = models.DateTimeField("Начало периода", null=True, blank=True)
    current_period_end = models.DateTimeField(
        "Конец периода", null=True, blank=True, db_index=True,
    )
    auto_renew = models.BooleanField("Автопродление", default=True)
    provider = models.CharField("Провайдер", max_length=32, default="yookassa")
    provider_payment_method_id = models.CharField(
        "ID сохранённого метода оплаты", max_length=128, blank=True,
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"#{self.id} {self.user_id} {self.plan_id} {self.status}"

    def is_active(self) -> bool:
        return bool(
            self.status == self.STATUS_ACTIVE
            and self.current_period_end
            and self.current_period_end > timezone.now()
        )


class SubscriptionPayment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Ожидает оплаты"),
        (STATUS_SUCCEEDED, "Оплачен"),
        (STATUS_CANCELED, "Отменён"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="subscription_payments",
        verbose_name="Пользователь",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
        blank=True,
        verbose_name="Подписка",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Тариф",
    )
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    currency = models.CharField("Валюта", max_length=8, default="RUB")
    status = models.CharField(
        "Статус", max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING,
    )
    provider = models.CharField("Провайдер", max_length=32, default="yookassa")
    provider_payment_id = models.CharField(
        "ID платежа провайдера", max_length=128, blank=True, db_index=True,
    )
    provider_payment_method_id = models.CharField(
        "ID сохранённого метода оплаты", max_length=128, blank=True,
    )
    confirmation_url = models.TextField("URL подтверждения", blank=True)
    is_renewal = models.BooleanField("Автопродление", default=False)
    applied = models.BooleanField("Применён", default=False)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Платёж подписки"
        verbose_name_plural = "Платежи подписок"
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"#{self.id} {self.user_id} {self.plan_id} {self.status}"

    def mark_succeeded_and_activate(self):
        """Idempotently mark the payment paid and activate/extend the
        subscription.

        Safe to call multiple times (the webhook may fire more than once): the
        activation only happens on the first call thanks to the `applied`
        flag, checked under a row lock.
        """
        with transaction.atomic():
            payment = (
                SubscriptionPayment.objects.select_for_update().get(pk=self.pk)
            )
            if payment.applied:
                return payment

            now = timezone.now()
            sub = None
            if payment.subscription_id:
                sub = (
                    Subscription.objects.select_for_update()
                    .filter(pk=payment.subscription_id)
                    .first()
                )
            if sub is None:
                sub = Subscription.objects.create(
                    user=payment.user,
                    plan=payment.plan,
                    status=Subscription.STATUS_PENDING,
                    provider=payment.provider,
                )
                payment.subscription = sub

            # Extend from the later of "now" and any remaining active period.
            base = sub.current_period_end if sub.current_period_end and sub.current_period_end > now else now
            if not sub.current_period_start:
                sub.current_period_start = now
            sub.current_period_end = _add_months(base, payment.plan.months)
            sub.status = Subscription.STATUS_ACTIVE
            # An early manual renewal may extend an existing subscription with
            # a different tier; keep the subscription's plan in sync with the
            # latest paid plan so status reporting reflects what was bought.
            sub.plan = payment.plan
            if payment.provider_payment_method_id:
                sub.provider_payment_method_id = payment.provider_payment_method_id
            sub.save(update_fields=[
                "current_period_start", "current_period_end", "status",
                "plan", "provider_payment_method_id", "updated_at",
            ])

            payment.status = SubscriptionPayment.STATUS_SUCCEEDED
            payment.applied = True
            payment.save(update_fields=[
                "status", "applied", "subscription", "updated_at",
            ])

            # Reflect changes onto the instance the caller holds.
            self.status = payment.status
            self.applied = payment.applied
            self.subscription = sub
            return payment


def has_subscription_access(user) -> bool:
    """True if the user may use the subscription-gated astroprocessor sections.

    Unlimited emails always have access; otherwise any of the user's
    subscriptions must be currently active. Defensive against anon/None.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if _is_unlimited(user):
        return True
    now = timezone.now()
    return Subscription.objects.filter(
        user=user,
        status=Subscription.STATUS_ACTIVE,
        current_period_end__gt=now,
    ).exists()


def subscription_status(user) -> dict:
    """Status of the user's subscription entitlement."""
    if not user or not getattr(user, "is_authenticated", False):
        return {
            "active": False,
            "plan": None,
            "current_period_end": None,
            "auto_renew": False,
            "sections": [],
        }

    if _is_unlimited(user):
        return {
            "active": True,
            "plan": None,
            "current_period_end": None,
            "auto_renew": False,
            "sections": list(UNLOCKED_SECTIONS),
        }

    now = timezone.now()
    sub = (
        Subscription.objects.filter(
            user=user,
            status=Subscription.STATUS_ACTIVE,
            current_period_end__gt=now,
        )
        .select_related("plan")
        .order_by("-current_period_end")
        .first()
    )
    if sub is None:
        return {
            "active": False,
            "plan": None,
            "current_period_end": None,
            "auto_renew": False,
            "sections": [],
        }

    return {
        "active": True,
        "plan": sub.plan.code,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "auto_renew": sub.auto_renew,
        "sections": list(UNLOCKED_SECTIONS),
    }


class AssistantChat(models.Model):
    """Per-horoscope assistant chat persisted for an authenticated user.

    Keyed by the client-computed ``chart_id`` so each horoscope keeps its own
    conversation. The ``messages`` array is stored verbatim as supplied by the
    client.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assistant_chats",
        verbose_name="Пользователь",
    )
    chart_id = models.SlugField("Идентификатор гороскопа", max_length=64)
    subject = models.TextField("Гороскоп", blank=True, default="")
    key = models.CharField("Ключ анализа", max_length=64, blank=True, default="")
    question = models.TextField("Вопрос", blank=True, default="")
    context = models.TextField("Контекст", blank=True, default="")
    messages = models.JSONField("Сообщения", default=list)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    def __str__(self):
        return f"{self.user_id}:{self.chart_id}"

    class Meta:
        verbose_name = "Чат ассистента"
        verbose_name_plural = "Чаты ассистента"
        unique_together = (("user", "chart_id"),)
        ordering = ("-updated_at",)
