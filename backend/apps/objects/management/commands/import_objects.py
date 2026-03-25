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
from apps.users.models import RoleCode, User

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
        project_manager = _get_or_create_pm(pm_raw, user_map)

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
