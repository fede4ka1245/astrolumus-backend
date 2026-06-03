import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q

from bootcamp.models import Course, Curriculum
from tariffs.models import Tariff

User = get_user_model()


class PaymentSettings(models.Model):
    """Model to manage payment enablement per platform"""
    
    class Platforms(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"
        WEB = "web", "Web"
    
    platform = models.CharField(
        max_length=50,
        verbose_name="Платформа",
        choices=Platforms.choices,
        unique=True,
        help_text="Платформа для которой настраиваются платежи"
    )
    enabled = models.BooleanField(
        default=True,
        verbose_name="Платежи включены",
        help_text="Включить или выключить платежи для данной платформы"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    def __str__(self):
        status = "включены" if self.enabled else "выключены"
        return f"{self.get_platform_display()}: платежи {status}"
    
    class Meta:
        db_table = "payment_settings"
        verbose_name = "Настройка платежей"
        verbose_name_plural = "Настройки платежей"


# this is not uses now
class Order(models.Model):
    class PaymentSystems(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        BEPAID = "bepaid", "BePaid"

    class PaymentStatuses(models.TextChoices):
        PENDING = "pending", "pending"
        SUCCEEDED = "succeeded", "succeeded"
        CANCELED = "canceled", "canceled"
        FAILED = "failed", "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="user_orders",
    )
    status = models.CharField(
        max_length=255,
        verbose_name="Статус",
        choices=PaymentStatuses.choices,
        default=PaymentStatuses.PENDING,
    )
    amount = models.DecimalField(
        verbose_name="сумма", max_digits=10, decimal_places=2, default=0
    )
    currency = models.CharField(
        max_length=3,
        verbose_name="Валюта",
        default="USD",
        help_text="Currency code (USD, RUB, BYN, EUR)"
    )
    payload = models.JSONField(default=dict, editable=False)
    pay_system = models.CharField(
        max_length=255,
        verbose_name="Платежные системы",
        choices=PaymentSystems.choices,
        default=PaymentSystems.STRIPE,
    )
    created_at = models.DateTimeField(blank=True, null=True)
    course = models.ForeignKey(
        Course, related_name="orders", blank=True, null=True, on_delete=models.SET_NULL
    )
    tariff = models.ForeignKey(
        Tariff, related_name="orders", blank=True, null=True, on_delete=models.SET_NULL
    )
    payment_id = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return "{} {}".format(self.id, self.user, self.status)

    class Meta:
        db_table = "orders"
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"


class PaymentRecord(models.Model):
    """Модель для хранения записей об оплатах с информацией для поиска в админке"""
    
    class PaymentSystems(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        BEPAID = "bepaid", "BePaid"
    
    class PaymentStatuses(models.TextChoices):
        SUCCESS = "success", "Успешно"
        FAILED = "failed", "Неуспешно"
        PENDING = "pending", "Ожидание"
    
    # Связь с пользователем и заказом
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="payment_records",
        verbose_name="Пользователь"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="payment_records",
        verbose_name="Заказ"
    )
    
    # Данные пользователя в приложении
    user_first_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Имя в приложении"
    )
    user_last_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Фамилия в приложении"
    )
    user_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email в приложении"
    )
    
    # Данные при оплате (merchant)
    merchant_first_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Имя при оплате"
    )
    merchant_last_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Фамилия при оплате"
    )
    merchant_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email при оплате"
    )
    
    # Информация о тарифе
    tariff_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Название тарифа"
    )
    
    # Информация о платеже
    payment_system = models.CharField(
        max_length=20,
        choices=PaymentSystems.choices,
        verbose_name="Платежная система"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Сумма оплаты"
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        verbose_name="Валюта"
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatuses.choices,
        default=PaymentStatuses.SUCCESS,
        verbose_name="Статус"
    )
    is_recurring = models.BooleanField(
        default=False,
        verbose_name="Рекурентный платеж",
        help_text="Является ли этот платеж частью рекурентной подписки"
    )
    
    # Служебные поля
    payment_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ID платежа"
    )
    raw_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Сырые данные платежа"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    
    def __str__(self):
        return f"{self.payment_system} - {self.amount} {self.currency} - {self.user_email or self.merchant_email}"
    
    class Meta:
        db_table = "payment_records"
        verbose_name = "Запись об оплате"
        verbose_name_plural = "Записи об оплатах"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["payment_system", "payment_id"],
                condition=Q(payment_id__isnull=False) & ~Q(payment_id=""),
                name="uniq_payment_records_system_payment_id",
            )
        ]


class RecurringSubscription(models.Model):
    """Модель для хранения информации о рекурентных подписках"""
    
    class PaymentSystems(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        BEPAID = "bepaid", "BePaid"
    
    class SubscriptionStatuses(models.TextChoices):
        ACTIVE = "active", "Активна"
        CANCELED = "canceled", "Отменена"
        PAST_DUE = "past_due", "Просрочена"
        UNPAID = "unpaid", "Не оплачена"
        TRIALING = "trialing", "Пробный период"
        INCOMPLETE = "incomplete", "Не завершена"
        INCOMPLETE_EXPIRED = "incomplete_expired", "Не завершена (истекла)"
    
    # Связь с пользователем и тарифом
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recurring_subscriptions",
        verbose_name="Пользователь"
    )
    tariff = models.ForeignKey(
        Tariff,
        on_delete=models.CASCADE,
        related_name="recurring_subscriptions",
        verbose_name="Тариф"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="recurring_subscriptions",
        verbose_name="Заказ"
    )
    
    # Платежная система
    payment_system = models.CharField(
        max_length=20,
        choices=PaymentSystems.choices,
        verbose_name="Платежная система"
    )
    
    # ID подписки в платежной системе
    subscription_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="ID подписки"
    )
    
    # ID клиента в платежной системе (для Stripe)
    customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ID клиента"
    )
    
    # Статус подписки
    status = models.CharField(
        max_length=30,
        choices=SubscriptionStatuses.choices,
        default=SubscriptionStatuses.INCOMPLETE,
        verbose_name="Статус подписки"
    )
    
    # Сумма и валюта
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Сумма подписки"
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        verbose_name="Валюта"
    )
    
    # Даты
    current_period_start = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Начало текущего периода"
    )
    current_period_end = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Конец текущего периода"
    )
    cancel_at_period_end = models.BooleanField(
        default=False,
        verbose_name="Отменить в конце периода"
    )
    canceled_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата отмены"
    )
    
    # Дополнительные данные
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Метаданные"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    
    def __str__(self):
        return f"{self.payment_system} - {self.user.email} - {self.tariff.code} - {self.status}"
    
    class Meta:
        db_table = "recurring_subscriptions"
        verbose_name = "Рекурентная подписка"
        verbose_name_plural = "Рекурентные подписки"
        ordering = ["-created_at"]
        indexes = [
            # Explicit names to keep migrations stable across environments.
            models.Index(fields=["user", "status"], name="recurring_s_user_id_status_idx"),
            models.Index(fields=["subscription_id"], name="recurring_s_subscri_idx"),
            models.Index(fields=["customer_id"], name="recurring_s_custome_idx"),
        ]


class ExternalPaymentEvent(models.Model):
    """Audit log for inbound Boosty/Patreon webhook payloads.

    Each row records the raw payload + the result of mapping it to a local
    Tariff / User. Unmatched events stay around so admins can rebind them
    manually (e.g. user paid before registering).
    """

    PROVIDER_BOOSTY = 'boosty'
    PROVIDER_PATREON = 'patreon'
    PROVIDER_CHOICES = (
        (PROVIDER_BOOSTY, 'Boosty'),
        (PROVIDER_PATREON, 'Patreon'),
    )

    STATUS_PENDING = 'pending'
    STATUS_PROCESSED = 'processed'
    STATUS_UNMATCHED = 'unmatched'
    STATUS_INVALID = 'invalid'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Получен'),
        (STATUS_PROCESSED, 'Активация создана'),
        (STATUS_UNMATCHED, 'Не сопоставлено'),
        (STATUS_INVALID, 'Неверный payload'),
    )

    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES, verbose_name='Провайдер')
    event_type = models.CharField(max_length=64, blank=True, default='', verbose_name='Тип события')
    external_user_id = models.CharField(max_length=128, blank=True, default='', verbose_name='ID пользователя у провайдера')
    external_email = models.EmailField(blank=True, default='', verbose_name='Email')
    tier_id = models.CharField(max_length=128, blank=True, default='', verbose_name='Tier / level id')
    payload = models.JSONField(default=dict, verbose_name='Payload')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    note = models.TextField(blank=True, default='', verbose_name='Комментарий')
    matched_tariff = models.ForeignKey(
        Tariff, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='external_events', verbose_name='Найденный тариф',
    )
    matched_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='external_payment_events', verbose_name='Найденный пользователь',
    )
    activation = models.ForeignKey(
        'tariffs.ActivationTariff', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='external_events', verbose_name='Созданная активация',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Получен')

    class Meta:
        verbose_name = 'Внешний платёж (webhook)'
        verbose_name_plural = 'Внешние платежи (webhook\'и)'
        ordering = ('-created_at',)

    def __str__(self):
        return f'[{self.provider}] {self.event_type or "?"} – {self.external_email or self.external_user_id or self.id}'

