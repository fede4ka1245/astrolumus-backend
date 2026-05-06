"""
Импорт динамического контента (JSONField переводов) в Tolgee.

Namespace 'tariffs' — для тарифов.
Namespace 'content' — для всех остальных моделей.
"""

from django.apps import apps
from django.core.management.base import BaseCommand

from utils.tolgee_client import upsert_keys_batch

# Registry: (app_label, model_name) → (tolgee_namespace, key_prefix, [fields])
DYNAMIC_MODELS = {
    ("tariffs", "Tariff"): ("tariffs", "tariff", ["title", "description", "public_description"]),
    ("info", "Documents"): ("documents", "doc", ["title", "description"]),
    ("info", "AppPartInfo"): ("app_info", "appinfo", ["title", "sub_title", "description", "main_description"]),
    ("astroprocessor", "AstroprocessorType"): ("astroprocessor_types", "type", ["name"]),
    ("astroprocessor", "AstroprocessorData"): ("astroprocessor_data", "data", ["name", "description"]),
    ("astroprocessor", "SignPlanetConnection"): ("sign_planet", "sp", ["name", "description"]),
    ("astroprocessor", "PlanetHouseConnection"): ("planet_house", "ph", ["name", "description"]),
    ("astroprocessor", "MasterHouseConnection"): ("master_house", "mh", ["name", "description"]),
    ("deep_sky", "Constellation"): ("constellations", "const", ["title", "description"]),
    ("deep_sky", "StellarObjectType"): ("stellar_types", "stype", ["name", "comment"]),
    ("deep_sky", "Star"): ("stars", "star", ["title", "area", "comment"]),
    ("deep_sky", "Information"): ("sky_info", "info", ["title", "description"]),
}


class Command(BaseCommand):
    help = "Импорт динамического контента (JSON-поля переводов) в Tolgee namespaces 'tariffs' и 'content'"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Только показать ключи, не загружать",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Collect keys per namespace
        namespace_keys = {}  # namespace → {key: {lang: text}}

        for (app_label, model_name), (namespace, prefix, fields) in DYNAMIC_MODELS.items():
            try:
                Model = apps.get_model(app_label, model_name)
            except LookupError:
                self.stderr.write(f"Модель {app_label}.{model_name} не найдена, пропускаем")
                continue

            qs = Model.objects.all()
            count = 0

            for instance in qs.iterator():
                pk = instance.pk
                for field_name in fields:
                    value = getattr(instance, field_name, None)
                    if not isinstance(value, dict) or not value:
                        continue

                    tolgee_key = f"{prefix}.{pk}.{field_name}"

                    if namespace not in namespace_keys:
                        namespace_keys[namespace] = {}

                    # value is {"ru": "text", "en": "text"}
                    translations = {
                        lang: text
                        for lang, text in value.items()
                        if isinstance(text, str) and text.strip()
                    }
                    if translations:
                        namespace_keys[namespace][tolgee_key] = translations
                        count += 1

            self.stdout.write(
                f"  {app_label}.{model_name}: {count} ключей"
            )

        # Summary
        for ns, keys in namespace_keys.items():
            self.stdout.write(f"\nNamespace '{ns}': {len(keys)} ключей")

        if dry_run:
            for ns, keys in namespace_keys.items():
                self.stdout.write(f"\n--- {ns} ---")
                for key, trans in list(keys.items())[:5]:
                    self.stdout.write(f"  {key}: {trans}")
                if len(keys) > 5:
                    self.stdout.write(f"  ... и ещё {len(keys) - 5}")
            return

        # Upload
        for ns, keys in namespace_keys.items():
            if not keys:
                continue
            self.stdout.write(f"Загрузка в Tolgee namespace '{ns}'...")
            result = upsert_keys_batch(ns, keys)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Готово: {result['total_keys']} ключей в {result['chunks']} batch(es)"
                )
            )
