"""
Импорт frontend (alfa-frontend) переводов в Tolgee namespace 'frontend'.

Читает ru.json и en.json, конвертирует nested JSON в flat dot-separated ключи,
загружает в Tolgee.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from utils.tolgee_client import upsert_keys_batch


def _flatten_json(data: dict, prefix: str = "") -> dict:
    """Flatten nested dict: {"a": {"b": "c"}} → {"a.b": "c"}"""
    result = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_json(value, full_key))
        else:
            result[full_key] = value
    return result


class Command(BaseCommand):
    help = "Импорт frontend переводов (alfa-frontend) в Tolgee namespace 'frontend'"

    def add_arguments(self, parser):
        parser.add_argument(
            "--locales-dir",
            default=str(settings.BASE_DIR / "alfa-frontend" / "src" / "locales"),
            help="Путь к директории с JSON файлами переводов",
        )
        parser.add_argument(
            "--namespace",
            default="frontend",
            help="Tolgee namespace",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать что будет импортировано, не загружать",
        )

    def handle(self, *args, **options):
        locales_dir = Path(options["locales_dir"])
        namespace = options["namespace"]
        dry_run = options["dry_run"]

        # Collect all locale files
        locale_files = sorted(locales_dir.glob("*.json"))
        if not locale_files:
            self.stderr.write(f"Не найдены JSON файлы в {locales_dir}")
            return

        self.stdout.write(f"Найдены файлы: {[f.name for f in locale_files]}")

        # Load and flatten all languages
        languages_data = {}
        for locale_file in locale_files:
            lang_tag = locale_file.stem  # "ru" from "ru.json"
            with open(locale_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            flat = _flatten_json(raw)
            languages_data[lang_tag] = flat
            self.stdout.write(f"  {lang_tag}: {len(flat)} ключей")

        # Merge into key→{lang: text} structure
        all_keys = set()
        for lang_data in languages_data.values():
            all_keys.update(lang_data.keys())

        keys_translations = {}
        for key in sorted(all_keys):
            translations = {}
            for lang_tag, lang_data in languages_data.items():
                if key in lang_data:
                    translations[lang_tag] = str(lang_data[key])
            keys_translations[key] = translations

        self.stdout.write(
            f"\nВсего уникальных ключей: {len(keys_translations)}"
        )

        if dry_run:
            for key, trans in list(keys_translations.items())[:10]:
                self.stdout.write(f"  {key}: {trans}")
            self.stdout.write("  ... (dry-run, не загружаем)")
            return

        # Upload to Tolgee
        self.stdout.write(f"Загрузка в Tolgee namespace '{namespace}'...")
        result = upsert_keys_batch(namespace, keys_translations)
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: {result['total_keys']} ключей в {result['chunks']} batch(es)"
            )
        )
