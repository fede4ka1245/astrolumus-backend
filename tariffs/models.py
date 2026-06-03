from datetime import timedelta

from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q, F, Subquery, UniqueConstraint
from django.utils import timezone
from django.utils.timezone import now
from django.conf import settings
from django.utils.html import strip_tags

from utils.multilinguality import get_default_language_value_admin

User = get_user_model()


class TariffManager(models.Manager):
    # DEPRECATED FIXME
    def get_user_tariff(self, user):
        import logging
        logger = logging.getLogger(__name__)

        last_activation = ActivationTariff.objects.filter(user=user).order_by("-created_at").first()
        # if not exist or validity days ends
        if not last_activation or (
                last_activation.tariff.validity_days > 0 and timezone.now() > last_activation.created_at + timedelta(
            days=last_activation.tariff.validity_days)):

            all_prevs_activations_count = ActivationTariff.objects.filter(user=user).count()
            has_guest_tariff = getattr(settings, 'HAS_GUEST_TARIFF', 'False') == 'True'
            # USER just registered
            if all_prevs_activations_count == 0 and not has_guest_tariff:
                # find first workings tariff
                default_tariff = self.filter(Q(start_datetime__isnull=True) | Q(start_datetime__lte=timezone.now()),
                                             Q(end_datetime__isnull=True) | Q(
                                                 end_datetime__gte=timezone.now())).order_by("-priority_for_default").first()
            else:
                try:
                    default_tariff = self.get(tariff_renew_wait=True)
                except Tariff.DoesNotExist:
                    logger.error("No tariff_renew_wait tariff configured — user %s has no active tariff", user.pk)
                    return None

            if not default_tariff:
                logger.error("No default tariff found — user %s has no active tariff", user.pk)
                return None

            last_activation = ActivationTariff.objects.create(tariff=default_tariff, user=user)

        return last_activation.tariff

    def get_user_tariffs(self, user):
        # get last + all previous with can_work_with_another
        last_activations = ActivationTariff.objects.filter(user=user).filter(
            Q(Q(tariff__validity_days__gt=0)
              & Q(created_at__gt=timezone.now() - timedelta(days=1) *
                                 F("tariff__validity_days"))) |
            Q(tariff__validity_days=0)
        ).order_by("-created_at")

        # if not find
        if last_activations.count() == 0:
            import logging
            logger = logging.getLogger(__name__)

            all_prevs_activations_count = ActivationTariff.objects.filter(user=user).count()
            has_guest_tariff = getattr(settings, 'HAS_GUEST_TARIFF', 'False') == 'True'
            # USER just registered
            if all_prevs_activations_count == 0 and not has_guest_tariff:
                # find first workings tariff (excluding 'guest' tariff)
                default_tariff = self.filter(Q(start_datetime__isnull=True) | Q(start_datetime__lte=timezone.now()),
                                             Q(end_datetime__isnull=True) | Q(
                                                 end_datetime__gte=timezone.now())).exclude(
                    code='guest').order_by("-priority_for_default").first()
            else:
                try:
                    default_tariff = self.get(tariff_renew_wait=True)
                except Tariff.DoesNotExist:
                    logger.error("No tariff_renew_wait tariff configured — user %s has no active tariff", user.pk)
                    return self.none()

            if not default_tariff:
                logger.error("No default tariff found — user %s has no active tariff", user.pk)
                return self.none()

            x = ActivationTariff.objects.create(tariff=default_tariff, user=user)
            tariffs_ids = [x.tariff_id, ]
            return self.filter(pk__in=tariffs_ids)
            # tariffs_ids = last_activations.values("tariff_id")
        else:
            # exclude not first and non can_work_with_another
            first_activation = last_activations.first()
            # Get first activation + all with can_work_with_another, but exclude duplicates
            if first_activation.tariff.can_work_with_another:
                # If first already has can_work_with_another, just get all with this flag
                last_activations = last_activations.filter(Q(tariff__can_work_with_another=True))
            else:
                # Otherwise, get first + all with can_work_with_another
                last_activations = last_activations.filter(
                    Q(id=first_activation.id) | Q(tariff__can_work_with_another=True))
            # Use distinct to avoid duplicate tariff_ids
            tariffs_ids = last_activations.values_list("tariff_id", flat=True).distinct()
            return self.filter(pk__in=tariffs_ids)


class TariffGroup(models.Model):
    title = models.CharField(verbose_name="Название", max_length=255)

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = "Семейство тарифов"
        verbose_name_plural = "Семейства тарифов"


class Tariff(models.Model):
    title = models.JSONField(verbose_name="Название")
    public = models.BooleanField("Публичный тариф", default=False,
                                 help_text="Отображается в списке карточек для перехода/и на сайте")
    description = models.JSONField(verbose_name="Описание", null=True, blank=True,
                                   help_text="Для отображения пользователю как активированного тарифа")
    public_description = models.JSONField(verbose_name="Публичное описание", null=True, blank=True,
                                          help_text="Для использования в карточках")
    tariff_group = models.ForeignKey(TariffGroup, verbose_name="Семейство тарифов", related_name="tariffs",
                                     on_delete=models.CASCADE, null=True, blank=True,
                                     help_text="При оплате тарифа из одного семейства срок активации, отсчитывается от "
                                               "последней не просроченной активации любого тарифа из семейства")
    code = models.CharField(verbose_name="Код", max_length=255)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)
    start_datetime = models.DateTimeField("Действует с", null=True, blank=True)
    end_datetime = models.DateTimeField("Действует по", null=True, blank=True)
    validity_days = models.IntegerField(verbose_name="Срок действия после активации, дней", default=0,
                                        help_text="Если 0 - действует бессрочно")
    priority_for_default = models.IntegerField(verbose_name="Приоритет для тарифа по умолчанию",
                                               default=0,
                                               help_text="Тариф по умолчанию, выбирается как действующий на "
                                                         "текущую дату и имеющий наивысший приоритете среди прочих. "
                                                         "Применяется для новых пользователей")
    can_work_with_another = models.BooleanField("Может работать параллельно с другими тарифами", default=False)
    restriction_forum = models.BooleanField("Форум отключен", default=False,
                                            help_text="Параметр не обрабатывается, оставлен на будущее")
    restriction_astroprocessor = models.BooleanField("Астропроцессор отключен", default=False)
    restriction_number_of_topic = models.IntegerField("Ограничить количество тем", default=0,
                                                      help_text="Параметр не обрабатывается, оставлен на будущее")
    restriction_number_of_horoscopes = models.IntegerField("Ограничить количество гороскопов", default=0)
    restriction_astroprocessor_validity_days = models.IntegerField(
        "Срок действия астропроцессора после активации, дней", default=0)
    tariff_renew_wait = models.BooleanField("Тариф для перехода после окончания всех других тарифов",
                                            default=False)
    tariff_link = models.URLField("Ссылка на тариф", max_length=255, null=True, blank=True)
    
    price_rub = models.DecimalField("Цена (RUB)", max_digits=10, decimal_places=2, default=0,
                                   help_text="Цена в российских рублях")
    price_byn = models.DecimalField("Цена (BYN)", max_digits=10, decimal_places=2, default=0,
                                   help_text="Цена в белорусских рублях")
    price_usd = models.DecimalField("Цена (USD)", max_digits=10, decimal_places=2, default=0,
                                   help_text="Цена в американских долларах")
    price_eur = models.DecimalField("Цена (EUR)", max_digits=10, decimal_places=2, default=0,
                                   help_text="Цена в евро")

    # ----- Astrolumus AI assistant quota -----
    assistant_enabled = models.BooleanField(
        "Доступ к ассистенту", default=False,
        help_text="Если выключено — пользователь, у которого активен только этот тариф, не может писать ассистенту")
    assistant_requests_per_month = models.PositiveIntegerField(
        "Запросов к ассистенту в месяц", default=0,
        help_text="0 — без месячного лимита")
    assistant_requests_per_day = models.PositiveIntegerField(
        "Запросов к ассистенту в день", default=0,
        help_text="0 — без дневного лимита")

    # ----- Tarot quota -----
    tarot_enabled = models.BooleanField(
        "Доступ к раскладам Таро", default=False,
        help_text="Если выключено — пользователь, у которого активен только этот тариф, не может делать расклады")
    tarot_requests_per_month = models.PositiveIntegerField(
        "Раскладов Таро в месяц", default=0,
        help_text="0 — без месячного лимита")
    tarot_requests_per_day = models.PositiveIntegerField(
        "Раскладов Таро в день", default=0,
        help_text="0 — без дневного лимита")

    # ----- Boosty -----
    boosty_url = models.URLField(
        "Boosty checkout URL", max_length=500, null=True, blank=True,
        help_text="Куда уходит пользователь по кнопке «Оплатить через Boosty». Пустое поле прячет кнопку.")
    boosty_subscription_level_id = models.CharField(
        "Boosty subscription level id", max_length=128, null=True, blank=True,
        help_text="Webhook сопоставляет это значение с уровнем подписки в Boosty (поле subscription_level.id).")

    # ----- Patreon -----
    patreon_url = models.URLField(
        "Patreon checkout URL", max_length=500, null=True, blank=True,
        help_text="Куда уходит пользователь по кнопке «Оплатить через Patreon». Пустое поле прячет кнопку.")
    patreon_tier_id = models.CharField(
        "Patreon tier id", max_length=128, null=True, blank=True,
        help_text="Webhook сопоставляет это значение с tier id в Patreon (data.relationships.currently_entitled_tiers.data[].id).")

    objects = TariffManager()

    def __str__(self):
        return strip_tags(get_default_language_value_admin(self.title) or "").strip()

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"

        constraints = [
            UniqueConstraint(fields=['tariff_renew_wait'], condition=Q(tariff_renew_wait=True),
                             name='unique_tariff_renew_wait')
        ]


class ActivationTariff(models.Model):
    # created_at = models.DateTimeField("Создан", auto_now_add=True)
    created_at = models.DateTimeField("Создан", default=now)
    tariff = models.ForeignKey(Tariff, related_name="activations", on_delete=models.CASCADE, null=True,
                               blank=True)
    user = models.ForeignKey(User, related_name="tariffs_activations", on_delete=models.CASCADE, null=True,
                             blank=True)

    class Meta:
        verbose_name = "Активация тарифа"
        verbose_name_plural = "Активации тарифов"


class SitePayments(models.Model):
    class Currency(models.TextChoices):
        RUB = "RUB", "рубль"
        BYN = "BYN", "белорусский рубль"

    created_at = models.DateTimeField("Создан", auto_now_add=True)
    email = models.EmailField("Email", max_length=255)
    datetime = models.DateTimeField("Date")
    tariff_code = models.CharField("Tariff code", max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма платежа')
    currency = models.CharField(
        choices=Currency.choices, verbose_name="Валюта", max_length=10
    )

    class Meta:
        verbose_name = "Платеж с сайта"
        verbose_name_plural = "Платежи с сайта"

    def __str__(self):
        return str(self.email)
