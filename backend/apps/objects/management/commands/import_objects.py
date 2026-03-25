"""
Импорт объектов из xlsx-файла (формат «Проекты.xlsx»).

Колонки Excel → поля БД:
  C (Город) + D (Адрес)    → name
  D (Адрес)                → address
  F (Клиент)               → customer
  H (Дэдлайн)              → deadline
  I (Статус стройки)        → current_stage
  L (Ответственный за стройку) → project_manager (FK User)
  V (Примечание)            → notes
"""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO

from django.db import transaction
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError

from apps.core.xlsx_utils import XlsxReader, clean_text, parse_date_flexible
from apps.objects.models import ProjectObject, Stage
from apps.users.models import User

# Индексы колонок (0-based после вычитания, т.к. XlsxReader отдаёт list[str] с 0-index)
COL_CITY = 2         # C
COL_ADDRESS = 3      # D
COL_DESCRIPTION = 4  # E
COL_CUSTOMER = 5     # F
COL_DEADLINE = 7     # H
COL_STAGE = 8        # I
COL_PM = 11          # L — Ответственный за стройку
COL_NOTES = 21       # V


def build_name(city: str, address: str, description: str) -> str:
    parts = [p for p in (city, address) if p]
    name = ", ".join(parts) if parts else description
    return name[:255] if name else ""


def _build_user_map() -> dict[str, User]:
    """
    Строит карту «текст из Excel → User» для сопоставления ответственных.
    Ключи: lowercase варианты — username, фамилия, «Имя Ф.», полное имя.
    """
    mapping: dict[str, User] = {}
    for u in User.objects.filter(is_active=True):
        mapping[u.username.lower()] = u
        if u.last_name:
            mapping[u.last_name.lower()] = u
        if u.first_name and u.last_name:
            # «Михаил Г.» — частый формат в Excel
            short = f"{u.first_name} {u.last_name[0]}.".lower()
            mapping[short] = u
            full = f"{u.first_name} {u.last_name}".lower()
            mapping[full] = u
            full_rev = f"{u.last_name} {u.first_name}".lower()
            mapping[full_rev] = u
    return mapping


def import_objects_from_reader(reader: XlsxReader, sheet: str | None = None) -> dict:
    """Импортирует объекты, возвращает статистику."""
    stage_map: dict[str, Stage] = {
        s.name.lower().strip(): s for s in Stage.objects.all()
    }
    user_map = _build_user_map()

    rows = list(reader.read_sheet_rows(sheet_name=sheet, max_columns=22))
    if not rows:
        raise CommandError("Файл пуст или не содержит строк.")

    created = 0
    skipped = 0
    errors: list[str] = []

    for row_idx, row in enumerate(rows[1:], start=2):
        city = clean_text(row[COL_CITY])
        address = clean_text(row[COL_ADDRESS])
        description = clean_text(row[COL_DESCRIPTION])
        customer = clean_text(row[COL_CUSTOMER])
        deadline_raw = clean_text(row[COL_DEADLINE])
        stage_raw = clean_text(row[COL_STAGE])
        pm_raw = clean_text(row[COL_PM])
        notes = clean_text(row[COL_NOTES])

        name = build_name(city, address, description)
        if not name:
            skipped += 1
            continue

        deadline = None
        dt = parse_date_flexible(deadline_raw)
        if dt:
            deadline = dt.date()

        current_stage = stage_map.get(stage_raw.lower().strip()) if stage_raw else None
        project_manager = user_map.get(pm_raw.lower().strip()) if pm_raw else None

        with transaction.atomic():
            obj, was_created = ProjectObject.objects.get_or_create(
                name=name,
                defaults={
                    "address": address,
                    "customer": customer,
                    "deadline": deadline,
                    "current_stage": current_stage,
                    "project_manager": project_manager,
                    "notes": notes,
                },
            )

        if was_created:
            created += 1
        else:
            skipped += 1

    return {"created": created, "skipped": skipped, "errors": errors}


def import_objects_from_file(file_obj: IO[bytes], sheet: str | None = None) -> dict:
    """Принимает file-like object (из REST upload), сохраняет во временный файл и импортирует."""
    with NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
        for chunk in iter(lambda: file_obj.read(8192), b""):
            tmp.write(chunk)
        tmp.flush()
        reader = XlsxReader(tmp.name)
        return import_objects_from_reader(reader, sheet=sheet)


class Command(BaseCommand):
    help = "Импорт объектов из xlsx-файла (формат «Проекты.xlsx»)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Путь к xlsx-файлу.")
        parser.add_argument("--sheet", default=None, help="Имя листа (по умолчанию первый).")

    def handle(self, *args, **options):
        filepath = Path(options["file"]).expanduser().resolve()
        if not filepath.exists():
            raise CommandError(f"Файл не найден: {filepath}")

        reader = XlsxReader(filepath)
        result = import_objects_from_reader(reader, sheet=options["sheet"])

        self.stdout.write(self.style.SUCCESS(
            f"Импорт завершён: создано {result['created']}, пропущено {result['skipped']}."
        ))
        for err in result["errors"]:
            self.stdout.write(self.style.WARNING(f"  {err}"))
