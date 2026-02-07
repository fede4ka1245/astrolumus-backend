from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from django.core.management.base import BaseCommand
from django.db import transaction

from advertising.models import Banner
from info.models import AppPartInfo, Documents, MobileAppsVersion


_RE_ESCAPED_NEWLINES = re.compile(r"(\\\\r\\\\n|\\\\n|\\\\r)")
_RE_REAL_NEWLINES = re.compile(r"\r\n|\r|\n")
_RE_MULTISPACE = re.compile(r"[ \t]{2,}")


def _clean_string(value: str, *, keep_newlines: bool) -> str:
    value = _RE_ESCAPED_NEWLINES.sub("\n", value)
    value = _RE_REAL_NEWLINES.sub("\n", value)
    if not keep_newlines:
        value = value.replace("\n", " ")
        value = _RE_MULTISPACE.sub(" ", value)
        value = value.strip()
    return value


def _clean_value(value: Any, *, keep_newlines: bool) -> tuple[Any, bool]:
    if isinstance(value, str):
        cleaned = _clean_string(value, keep_newlines=keep_newlines)
        return cleaned, cleaned != value

    if isinstance(value, list):
        changed = False
        cleaned_list: list[Any] = []
        for item in value:
            cleaned_item, item_changed = _clean_value(item, keep_newlines=keep_newlines)
            cleaned_list.append(cleaned_item)
            changed = changed or item_changed
        return cleaned_list, changed

    if isinstance(value, dict):
        changed = False
        cleaned_dict: dict[Any, Any] = {}
        for key, item in value.items():
            cleaned_item, item_changed = _clean_value(item, keep_newlines=keep_newlines)
            cleaned_dict[key] = cleaned_item
            changed = changed or item_changed
        return cleaned_dict, changed

    return value, False


@dataclass(frozen=True)
class _FieldSpec:
    model: type
    field_names: tuple[str, ...]


class Command(BaseCommand):
    help = (
        "Cleans stray newline sequences (\\r\\n, \\r, \\n and their escaped forms) "
        "from `info` and `banners` records."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write changes to DB (default: dry-run).",
        )
        parser.add_argument(
            "--keep-newlines",
            action="store_true",
            help="Normalize to '\\n' but keep line breaks (default: replace with spaces).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max rows per model to process (0 = no limit).",
        )

    def handle(self, *args, **options):
        apply_changes: bool = options["apply"]
        keep_newlines: bool = options["keep_newlines"]
        limit: int = options["limit"]

        field_specs: Iterable[_FieldSpec] = (
            _FieldSpec(Banner, ("title", "description", "video_link")),
            _FieldSpec(Documents, ("title", "description")),
            _FieldSpec(AppPartInfo, ("title", "sub_title", "description", "main_description")),
            _FieldSpec(MobileAppsVersion, ("description",)),
        )

        total_rows_changed = 0
        total_fields_changed = 0

        with transaction.atomic():
            for spec in field_specs:
                qs = spec.model.objects.all().order_by("pk")
                if limit and limit > 0:
                    qs = qs[:limit]

                rows_changed = 0
                fields_changed = 0

                for obj in qs.iterator():
                    update_fields: list[str] = []
                    for field_name in spec.field_names:
                        raw_value = getattr(obj, field_name)
                        cleaned_value, changed = _clean_value(raw_value, keep_newlines=keep_newlines)
                        if not changed:
                            continue
                        setattr(obj, field_name, cleaned_value)
                        update_fields.append(field_name)
                        fields_changed += 1

                    if not update_fields:
                        continue

                    rows_changed += 1
                    if apply_changes:
                        obj.save(update_fields=update_fields)

                total_rows_changed += rows_changed
                total_fields_changed += fields_changed
                self.stdout.write(
                    f"{spec.model._meta.label}: rows_changed={rows_changed}, fields_changed={fields_changed}"
                )

            if not apply_changes:
                self.stdout.write("Dry-run: no changes written (use --apply).")
                transaction.set_rollback(True)

        self.stdout.write(
            f"TOTAL: rows_changed={total_rows_changed}, fields_changed={total_fields_changed}"
        )
