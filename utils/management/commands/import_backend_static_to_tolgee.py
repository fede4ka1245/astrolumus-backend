"""
Импорт Django статических текстов в Tolgee namespace 'backend'.

Сканирует все модели: verbose_name, verbose_name_plural, field verbose_name/help_text,
Choice labels. Также admin fieldset labels и @display descriptions.
"""

from django.apps import apps
from django.core.management.base import BaseCommand

from utils.tolgee_client import upsert_keys_batch

# Admin fieldset labels (manually collected since they're not introspectable)
ADMIN_FIELDSETS = {
    "payments.paymentrecord.fieldset.basic_info": "Основная информация",
    "payments.paymentrecord.fieldset.app_user": "Пользователь в приложении",
    "payments.paymentrecord.fieldset.merchant_data": "Данные при оплате (merchant)",
    "payments.paymentrecord.fieldset.related_objects": "Связанные объекты",
    "payments.paymentrecord.fieldset.raw_data": "Сырые данные",
    "payments.recurringsubscription.fieldset.basic_info": "Основная информация",
    "payments.recurringsubscription.fieldset.financial_info": "Финансовая информация",
    "payments.recurringsubscription.fieldset.subscription_periods": "Периоды подписки",
    "payments.recurringsubscription.fieldset.metadata": "Метаданные",
    "payments.recurringsubscription.fieldset.dates": "Даты",
    "users.user.fieldset.personal_info": "Personal info",
    "users.user.fieldset.translation": "Translation",
    "users.user.fieldset.permissions": "Permissions",
    "users.user.fieldset.important_dates": "Important dates",
}

# Admin @display / short_description strings
ADMIN_DISPLAY = {
    "astroprocessor.admin.signplanet.planet": "Планета",
    "astroprocessor.admin.signplanet.sign": "Знак",
    "astroprocessor.admin.planethouse.planet": "Планета",
    "astroprocessor.admin.planethouse.house": "Дом",
    "astroprocessor.admin.masterhouse.master_house": "Управитель дома",
    "astroprocessor.admin.masterhouse.at_house": "В доме",
    "deep_sky.admin.star.no_image": "Нет изображения",
    "payments.admin.paymentrecord.user_full_name": "Имя в приложении",
    "payments.admin.paymentrecord.merchant_full_name": "Имя при оплате",
    "alpha.admin.send_mail_form.title_label": "Заголовок",
    "alpha.admin.send_mail_form.user_email_label": "отправить на один email, если указано",
}


class Command(BaseCommand):
    help = "Импорт Django статических текстов (verbose_name, help_text, choices) в Tolgee namespace 'backend'"

    def add_arguments(self, parser):
        parser.add_argument(
            "--namespace", default="backend",
            help="Tolgee namespace",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Только показать ключи, не загружать",
        )

    def handle(self, *args, **options):
        namespace = options["namespace"]
        dry_run = options["dry_run"]

        keys = {}  # key → {"ru": text}

        for model in apps.get_models():
            meta = model._meta
            app_label = meta.app_label
            model_name = meta.model_name

            # verbose_name / verbose_name_plural
            vn = str(meta.verbose_name) if meta.verbose_name else None
            vnp = str(meta.verbose_name_plural) if meta.verbose_name_plural else None

            if vn:
                keys[f"{app_label}.{model_name}.verbose_name"] = {"ru": vn}
            if vnp:
                keys[f"{app_label}.{model_name}.verbose_name_plural"] = {"ru": vnp}

            # Fields
            for field in meta.get_fields():
                if not hasattr(field, "verbose_name"):
                    continue

                field_vn = str(field.verbose_name) if field.verbose_name else None
                if field_vn:
                    keys[f"{app_label}.{model_name}.field.{field.name}"] = {"ru": field_vn}

                field_ht = str(field.help_text) if getattr(field, "help_text", None) else None
                if field_ht:
                    keys[f"{app_label}.{model_name}.field.{field.name}.help_text"] = {"ru": field_ht}

                # Choices
                choices = getattr(field, "choices", None)
                if choices:
                    for choice_value, choice_label in choices:
                        choice_key_suffix = str(choice_value).lower().replace(" ", "_")
                        key = f"{app_label}.{model_name}.choice.{field.name}.{choice_key_suffix}"
                        keys[key] = {"ru": str(choice_label)}

        # Admin fieldsets
        for key, text in ADMIN_FIELDSETS.items():
            keys[key] = {"ru": text}

        # Admin display strings
        for key, text in ADMIN_DISPLAY.items():
            keys[key] = {"ru": text}

        self.stdout.write(f"Всего ключей: {len(keys)}")

        if dry_run:
            for key, trans in sorted(keys.items()):
                self.stdout.write(f"  {key} = {trans['ru']}")
            return

        self.stdout.write(f"Загрузка в Tolgee namespace '{namespace}'...")
        result = upsert_keys_batch(namespace, keys)
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: {result['total_keys']} ключей в {result['chunks']} batch(es)"
            )
        )
