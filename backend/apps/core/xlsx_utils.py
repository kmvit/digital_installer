"""Shared xlsx reader — works without openpyxl (zip + XML parsing)."""

from __future__ import annotations

import re
import zipfile
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

EXCEL_EPOCH = datetime(1899, 12, 30)


class XlsxReader:
    """Reads an .xlsx file using only the standard library."""

    def __init__(self, filepath: Path | str):
        self.filepath = Path(filepath)
        self.shared_strings: list[str] = []

    def read_sheet_rows(
        self,
        sheet_name: str | None = None,
        max_columns: int = 22,
    ) -> Iterable[list[str]]:
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
                raise ValueError("В файле не найдено листов Excel.")

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
                raise ValueError(f"Лист '{sheet_name}' не найден в файле.")

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
                    col_idx = column_to_number(match.group(1))
                    if col_idx > max_columns:
                        continue
                    values_by_col[col_idx] = self._extract_cell_value(cell)

                if not values_by_col:
                    continue
                yield [values_by_col.get(idx, "") for idx in range(1, max_columns + 1)]

    def sheet_names(self) -> list[str]:
        with zipfile.ZipFile(self.filepath) as archive:
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            sheets = workbook.find("a:sheets", NS)
            if sheets is None:
                return []
            return [s.attrib.get("name", "") for s in sheets]

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def column_to_number(column: str) -> int:
    value = 0
    for char in column:
        value = value * 26 + ord(char) - ord("A") + 1
    return value


def clean_text(value: str | None) -> str:
    return " ".join((value or "").replace("\xa0", " ").split()).strip()


def to_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip().replace(" ", "").replace(",", ".")
    if not raw or raw in ("+", "-"):
        return None
    try:
        return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None


def excel_serial_to_date(value: str | None) -> datetime | None:
    """Convert Excel serial date number to a Python datetime."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        serial = int(float(raw))
        if serial < 1:
            return None
        return EXCEL_EPOCH + timedelta(days=serial)
    except (ValueError, OverflowError):
        return None


def parse_date_flexible(value: str | None) -> datetime | None:
    """Try to parse a date from Excel serial, dd.mm.yyyy, or yyyy-mm-dd."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw or raw in ("+", "-"):
        return None

    # dd.mm.yyyy
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    return excel_serial_to_date(raw)
