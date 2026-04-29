"""
Импорт объектов из xlsx-файла (формат «Проекты.xlsx»).

Колонки Excel → поля БД:
  C (Город)                → city (FK на City)
  D (Адрес)                → address
  E (Описание проекта)     → name
  F (Клиент)               → customer
  G (Статус/Решение)       → decision_status
  H (Дэдлайн)              → deadline
  I (Статус стройки)       → construction_status + current_stage
  J (Статус материалы)     → materials_status
  K (Статус ПИР)           → pir_status
  L (Ответственный за стройку) → project_manager (FK User)
  Q (Статус ИД)            → as_built_status
  V (Примечание)            → notes
"""

from __future__ import annotations

import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO

from django.db import transaction
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError

from apps.core.xlsx_utils import XlsxReader, clean_text, parse_date_flexible
from apps.objects.models import City, ProjectObject, Stage
from apps.users.models import RoleCode, User

# Индексы колонок (0-based после вычитания, т.к. XlsxReader отдаёт list[str] с 0-index)
COL_CITY = 2         # C
COL_ADDRESS = 3      # D
COL_DESCRIPTION = 4  # E
COL_CUSTOMER = 5     # F
COL_DECISION_STATUS = 6  # G
COL_DEADLINE = 7     # H
COL_CONSTRUCTION_STATUS = 8  # I
COL_MATERIALS_STATUS = 9  # J
COL_PIR_STATUS = 10  # K
COL_PM = 11          # L — Ответственный за стройку
COL_AS_BUILT_STATUS = 16  # Q
COL_NOTES = 21       # V

DECISION_STATUS_MAP = {
    "Анализ": "analysis",
    "Строим": "in_progress",
    "Отказ": "rejected",
    "Передан СП": "transferred_to_sp",
    "Архив анализ": "archive_analysis",
}
CONSTRUCTION_STATUS_MAP = {
    "Обследовать": "survey",
    "Выбрать ПО": "select_software",
    "Строить": "build",
    "Завершен": "completed",
    "Завершен (доделать)": "completed_todo",
    "Завершен оплачен": "completed_paid",
}
MATERIALS_STATUS_MAP = {
    "Заказать": "order",
    "Заказаны": "ordered",
    "Пришли": "arrived",
    "СП": "sp",
}
PIR_STATUS_MAP = {
    "Разработать": "develop",
    "Согл. с РТК": "agreed_rtk",
    "Согл. со службами": "agreed_services",
    "Сдать ПИР": "submit_pir",
    "Завершен": "completed",
    "Не брали": "not_taken",
    "СП": "sp",
}
AS_BUILT_STATUS_MAP = {
    "Назначить": "assign",
    "Разработка": "in_development",
    "Сдан МП": "submitted_mp",
    "Проверка РТК": "check_rtk",
    "Доработка ПП": "rework_pp",
    "Сдан ПП": "submitted_pp",
    "Не требуется": "not_required",
}


CITY_PREFIX_RE = re.compile(r"^(?:Город|город|г\.|г\s)\s*", re.UNICODE)


def normalize_city(raw: str) -> str:
    value = clean_text(raw)
    if not value:
        return ""
    return CITY_PREFIX_RE.sub("", value).strip()


def build_name(address: str, description: str) -> str:
    name = description or address
    return name[:255] if name else ""


def _get_or_create_city(raw_name: str, cache: dict[str, City]) -> City | None:
    name = normalize_city(raw_name)
    if not name:
        return None
    key = name.casefold()
    if key in cache:
        return cache[key]
    city, _ = City.objects.get_or_create(name=name)
    cache[key] = city
    return city


def _register_user(mapping: dict[str, User], user: User) -> None:
    """Добавляет все варианты написания имени пользователя в карту."""
    mapping[user.username.lower()] = user
    if user.last_name:
        mapping[user.last_name.lower()] = user
    if user.first_name and user.last_name:
        short = f"{user.first_name} {user.last_name[0]}.".lower()
        mapping[short] = user
        full = f"{user.first_name} {user.last_name}".lower()
        mapping[full] = user
        full_rev = f"{user.last_name} {user.first_name}".lower()
        mapping[full_rev] = user
    if user.first_name and not user.last_name:
        mapping[user.first_name.lower()] = user


def _build_user_map() -> dict[str, User]:
    mapping: dict[str, User] = {}
    for u in User.objects.filter(is_active=True):
        _register_user(mapping, u)
    return mapping


def _get_or_create_pm(raw_name: str, user_map: dict[str, User]) -> User | None:
    """Ищет пользователя по имени из Excel; если нет — создаёт с ролью project_manager."""
    if not raw_name:
        return None

    key = raw_name.lower().strip()
    if key in user_map:
        return user_map[key]

    # парсим «Имя Ф.» или «Фамилия» или просто имя
    parts = raw_name.strip().split()
    first_name = parts[0] if parts else raw_name.strip()
    last_name = parts[1].rstrip(".") if len(parts) > 1 else ""

    # username: транслит-подобная очистка — берём латиницу или оставляем как есть
    base = raw_name.strip().lower().replace(" ", "_").replace(".", "")
    # убираем недопустимые символы для username
    username = "".join(c for c in base if c.isalnum() or c == "_")
    if not username:
        username = f"pm_{id(raw_name)}"

    # если username уже занят — добавляем суффикс
    original = username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{original}_{counter}"
        counter += 1

    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        role=RoleCode.PROJECT_MANAGER,
        password=None,  # unusable password
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])

    _register_user(user_map, user)
    return user


def _map_status(raw_value: str, mapping: dict[str, str], row_idx: int, field_title: str) -> tuple[str, str | None]:
    if not raw_value:
        return "", None
    lookup = {key.casefold(): value for key, value in mapping.items()}
    mapped = lookup.get(raw_value.casefold())
    if mapped:
        return mapped, None
    valid = ", ".join(mapping.keys())
    return "", f"Строка {row_idx}: недопустимое значение '{raw_value}' для поля '{field_title}'. Допустимо: {valid}."


def import_objects_from_reader(reader: XlsxReader, sheet: str | None = None) -> dict:
    """Импортирует объекты, возвращает статистику."""
    stage_map: dict[str, Stage] = {
        s.name.lower().strip(): s for s in Stage.objects.all()
    }
    user_map = _build_user_map()
    city_cache: dict[str, City] = {c.name.casefold(): c for c in City.objects.all()}

    rows = list(reader.read_sheet_rows(sheet_name=sheet, max_columns=22))
    if not rows:
        raise CommandError("Файл пуст или не содержит строк.")

    created = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    for row_idx, row in enumerate(rows[1:], start=2):
        city_raw = clean_text(row[COL_CITY])
        address = clean_text(row[COL_ADDRESS])
        description = clean_text(row[COL_DESCRIPTION])
        customer = clean_text(row[COL_CUSTOMER])
        decision_raw = clean_text(row[COL_DECISION_STATUS])
        deadline_raw = clean_text(row[COL_DEADLINE])
        construction_raw = clean_text(row[COL_CONSTRUCTION_STATUS])
        materials_raw = clean_text(row[COL_MATERIALS_STATUS])
        pir_raw = clean_text(row[COL_PIR_STATUS])
        pm_raw = clean_text(row[COL_PM])
        as_built_raw = clean_text(row[COL_AS_BUILT_STATUS])
        notes = clean_text(row[COL_NOTES])

        name = build_name(address, description)
        if not name:
            skipped += 1
            continue

        city = _get_or_create_city(city_raw, city_cache)

        deadline = None
        dt = parse_date_flexible(deadline_raw)
        if dt:
            deadline = dt.date()

        decision_status, decision_error = _map_status(decision_raw, DECISION_STATUS_MAP, row_idx, "Решение")
        construction_status, construction_error = _map_status(construction_raw, CONSTRUCTION_STATUS_MAP, row_idx, "Статус стройки")
        materials_status, materials_error = _map_status(materials_raw, MATERIALS_STATUS_MAP, row_idx, "Статус материалы")
        pir_status, pir_error = _map_status(pir_raw, PIR_STATUS_MAP, row_idx, "Статус ПИР")
        as_built_status, as_built_error = _map_status(as_built_raw, AS_BUILT_STATUS_MAP, row_idx, "Статус ИД")

        row_errors = [e for e in (decision_error, construction_error, materials_error, pir_error, as_built_error) if e]
        if row_errors:
            errors.extend(row_errors)
            skipped += 1
            continue

        current_stage = stage_map.get(construction_raw.lower().strip()) if construction_raw else None
        project_manager = _get_or_create_pm(pm_raw, user_map)

        defaults = {
            "city": city,
            "address": address,
            "customer": customer,
            "decision_status": decision_status,
            "construction_status": construction_status,
            "materials_status": materials_status,
            "pir_status": pir_status,
            "as_built_status": as_built_status,
            "deadline": deadline,
            "current_stage": current_stage,
            "project_manager": project_manager,
            "notes": notes,
        }

        with transaction.atomic():
            qs = ProjectObject.objects.filter(name=name, city=city, address=address)
            obj = qs.first()
            if obj is None:
                obj = ProjectObject.objects.create(name=name, **defaults)
                was_created = True
            else:
                for field, value in defaults.items():
                    setattr(obj, field, value)
                obj.save()
                was_created = False

        if was_created:
            created += 1
        else:
            updated += 1

    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors}


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
            f"Импорт завершён: создано {result['created']}, обновлено {result['updated']}, пропущено {result['skipped']}."
        ))
        for err in result["errors"]:
            self.stdout.write(self.style.WARNING(f"  {err}"))
