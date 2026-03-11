from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.pricing.models import PriceList, PriceListItem


NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


@dataclass
class ParsedRow:
    item_number: str
    name: str
    composition: str
    unit: str
    note: str
    base_rate: Decimal
    smr_rate: Decimal | None
    materials_rate: Decimal | None
    pir_rate: Decimal | None


class XlsxReader:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.shared_strings: list[str] = []

    def read_sheet_rows(self, sheet_name: str | None = None, max_columns: int = 9) -> Iterable[list[str]]:
        with zipfile.ZipFile(self.filepath) as archive:
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}

            if "xl/sharedStrings.xml" in archive.namelist():
                shared_strings_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                self.shared_strings = [
                    "".join((node.text or "") for node in item.findall(".//a:t", NS))
                    for item in shared_strings_root.findall("a:si", NS)
                ]

            sheets = workbook.find("a:sheets", NS)
            if sheets is None:
                raise CommandError("В файле не найдено листов Excel.")

            selected_sheet = None
            for sheet in sheets:
                current_name = sheet.attrib.get("name")
                rel_id = sheet.attrib.get(f"{{{NS['r']}}}id")
                if not rel_id:
                    continue
                if sheet_name is None or current_name == sheet_name:
                    selected_sheet = rel_map[rel_id]
                    break

            if selected_sheet is None:
                raise CommandError(f"Лист '{sheet_name}' не найден в файле.")

            sheet_path = "xl/" + selected_sheet.lstrip("/").replace("\\", "/")
            worksheet = ET.fromstring(archive.read(sheet_path))
            sheet_data = worksheet.find("a:sheetData", NS)
            if sheet_data is None:
                return

            for row in sheet_data.findall("a:row", NS):
                values_by_col: dict[int, str] = {}
                for cell in row.findall("a:c", NS):
                    ref = cell.attrib.get("r", "")
                    match = re.match(r"([A-Z]+)", ref)
                    if not match:
                        continue
                    col_idx = self._column_to_number(match.group(1))
                    if col_idx > max_columns:
                        continue
                    values_by_col[col_idx] = self._extract_cell_value(cell)

                if not values_by_col:
                    continue
                yield [values_by_col.get(idx, "") for idx in range(1, max_columns + 1)]

    def _extract_cell_value(self, cell: ET.Element) -> str:
        cell_type = cell.attrib.get("t")
        value_node = cell.find("a:v", NS)
        inline_node = cell.find("a:is", NS)

        if cell_type == "s" and value_node is not None and value_node.text is not None:
            try:
                return self.shared_strings[int(value_node.text)]
            except (IndexError, ValueError):
                return ""
        if cell_type == "inlineStr" and inline_node is not None:
            return "".join((node.text or "") for node in inline_node.findall(".//a:t", NS))
        if value_node is not None and value_node.text is not None:
            return value_node.text
        return ""

    @staticmethod
    def _column_to_number(column: str) -> int:
        value = 0
        for char in column:
            value = value * 26 + ord(char) - ord("A") + 1
        return value


class Command(BaseCommand):
    help = "Импортирует позиции расценок из xlsx-файла в PriceList."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Путь к xlsx-файлу с расценками.")
        parser.add_argument("--title", required=True, help="Название базы расценок.")
        parser.add_argument(
            "--pricelist-version",
            dest="pricelist_version",
            default="1.0",
            help="Версия базы расценок.",
        )
        parser.add_argument("--sheet", default=None, help="Имя листа Excel. По умолчанию первый лист.")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Перезаписать позиции в существующей базе (title+version).",
        )

    def handle(self, *args, **options):
        filepath = Path(options["file"]).expanduser().resolve()
        if not filepath.exists():
            raise CommandError(f"Файл не найден: {filepath}")
        if filepath.suffix.lower() != ".xlsx":
            raise CommandError("Поддерживаются только файлы .xlsx")

        title = options["title"].strip()
        version = options["pricelist_version"].strip()
        replace = options["replace"]
        sheet_name = options["sheet"]

        if not title:
            raise CommandError("Параметр --title не может быть пустым.")
        if not version:
            raise CommandError("Параметр --pricelist-version не может быть пустым.")

        reader = XlsxReader(filepath)
        parsed_rows = self._parse_rows(reader.read_sheet_rows(sheet_name=sheet_name))

        if not parsed_rows:
            raise CommandError("Не найдено строк с расценками для импорта.")

        with transaction.atomic():
            price_list, created = PriceList._default_manager.get_or_create(
                title=title,
                version=version,
                defaults={"is_active": True},
            )

            if not created and not replace and price_list.items.exists():
                raise CommandError(
                    "База расценок уже содержит позиции. Используйте --replace для перезаписи."
                )
            if not created and replace:
                price_list.items.all().delete()

            PriceListItem._default_manager.bulk_create(
                [
                    PriceListItem(
                        price_list=price_list,
                        item_number=row.item_number,
                        name=row.name,
                        composition=row.composition,
                        unit=row.unit,
                        note=row.note,
                        base_rate=row.base_rate,
                        smr_rate=row.smr_rate,
                        materials_rate=row.materials_rate,
                        pir_rate=row.pir_rate,
                    )
                    for row in parsed_rows
                ],
                batch_size=500,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Импорт завершен: {len(parsed_rows)} позиций в '{price_list.title} v{price_list.version}'."
            )
        )

    def _parse_rows(self, rows: Iterable[list[str]]) -> list[ParsedRow]:
        result: list[ParsedRow] = []

        for row in rows:
            item_number = self._clean_text(row[0])
            name = self._clean_text(row[1])
            composition = self._clean_text(row[2])
            unit = self._clean_text(row[3])
            note = self._clean_text(row[4])

            if not item_number:
                continue
            if item_number.lower() == "№ п/п":
                continue
            if item_number.startswith("Раздел"):
                continue

            base_rate = self._to_decimal(row[5])
            if base_rate is None:
                # Пропускаем заголовочные/служебные строки без стоимости.
                continue
            if not name:
                continue

            result.append(
                ParsedRow(
                    item_number=item_number,
                    name=name,
                    composition=composition,
                    unit=unit,
                    note=note,
                    base_rate=base_rate,
                    smr_rate=self._to_decimal(row[6]),
                    materials_rate=self._to_decimal(row[7]),
                    pir_rate=self._to_decimal(row[8]),
                )
            )

        return result

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join((value or "").replace("\xa0", " ").split()).strip()

    @staticmethod
    def _to_decimal(value: str) -> Decimal | None:
        if value is None:
            return None
        raw = str(value).strip().replace(" ", "").replace(",", ".")
        if not raw:
            return None
        try:
            return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            return None
