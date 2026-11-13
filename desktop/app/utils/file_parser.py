"""Parser for CSV and XLSX epidemiological datasets without heavy external dependencies.

Supports:
- CSV files with comma or semicolon delimiters and UTF-8 / Latin-1 encoding
- Modern Excel (.xlsx) files via OpenXML standard library extraction
- Cleaning of empty cells to None (avoiding invalid JSON NaN)
- Field normalization adhering to API_ESCRITORIO.md POST /cargas/
"""
from __future__ import annotations

import csv
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _normalize_key(key: str) -> str:
    k = key.strip().lower()
    mapping = {
        "año": "anio",
        "ano": "anio",
        "anio": "anio",
        "year": "anio",
        "mes": "mes",
        "month": "mes",
        "casos": "casos_dengue",
        "casos_dengue": "casos_dengue",
        "dengue": "casos_dengue",
        "temperatura": "temperatura_c",
        "temperatura_c": "temperatura_c",
        "temp": "temperatura_c",
        "humedad": "humedad_pct",
        "humedad_pct": "humedad_pct",
        "hum": "humedad_pct",
        "precipitacion": "precipitacion_mm",
        "precipitacion_mm": "precipitacion_mm",
        "lluvia": "precipitacion_mm",
    }
    return mapping.get(k, k)


def _clean_val(val: Any, target_type: str) -> Any:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "null", "none", "", "--", "-"):
        return None

    try:
        if target_type == "int":
            return int(float(s))
        elif target_type == "float":
            return float(s)
    except (ValueError, TypeError):
        return s
    return s


def parse_csv(path: Path | str) -> list[dict[str, Any]]:
    p = Path(path)
    # Detect encoding
    raw = p.read_bytes()
    encoding = "utf-8"
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        encoding = "latin-1"

    text = raw.decode(encoding)
    # Detect delimiter
    first_line = text.splitlines()[0] if text.splitlines() else ""
    delimiter = ";" if ";" in first_line and "," not in first_line else ","

    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    records: list[dict[str, Any]] = []

    for row in reader:
        norm_row: dict[str, Any] = {}
        for k, v in row.items():
            if k:
                norm_row[_normalize_key(k)] = v

        anio = _clean_val(norm_row.get("anio"), "int")
        mes = _clean_val(norm_row.get("mes"), "int")
        casos = _clean_val(norm_row.get("casos_dengue"), "int")
        temp = _clean_val(norm_row.get("temperatura_c"), "float")
        hum = _clean_val(norm_row.get("humedad_pct"), "float")
        prec = _clean_val(norm_row.get("precipitacion_mm"), "float")

        # Skip completely empty rows
        if anio is None and mes is None and casos is None:
            continue

        records.append({
            "anio": anio,
            "mes": mes,
            "casos_dengue": casos,
            "temperatura_c": temp,
            "humedad_pct": hum,
            "precipitacion_mm": prec,
        })
    return records


def parse_xlsx(path: Path | str) -> list[dict[str, Any]]:
    p = Path(path)
    records: list[dict[str, Any]] = []

    with zipfile.ZipFile(p, "r") as z:
        # 1. Read shared strings if present
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in tree.findall(".//{*}si"):
                t = si.find(".//{*}t")
                shared_strings.append(t.text if t is not None and t.text else "")

        # 2. Read first sheet
        sheet_file = "xl/worksheets/sheet1.xml"
        if sheet_file not in z.namelist():
            sheets = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
            sheet_file = sheets[0] if sheets else ""

        if not sheet_file:
            raise ValueError("No se encontró ninguna hoja de cálculo en el archivo Excel.")

        sheet_tree = ET.fromstring(z.read(sheet_file))
        rows_data: list[list[str]] = []

        for row in sheet_tree.findall(".//{*}row"):
            row_cells: list[str] = []
            for c in row.findall(".//{*}c"):
                t = c.get("t")
                v = c.find(".//{*}v")
                val_text = ""
                if v is not None and v.text is not None:
                    if t == "s":
                        idx = int(v.text)
                        val_text = shared_strings[idx] if 0 <= idx < len(shared_strings) else ""
                    else:
                        val_text = v.text
                row_cells.append(val_text)
            if any(cell.strip() for cell in row_cells):
                rows_data.append(row_cells)

    if not rows_data:
        return []

    # First row is header
    raw_headers = rows_data[0]
    headers = [_normalize_key(h) for h in raw_headers]

    for row_vals in rows_data[1:]:
        row_dict: dict[str, Any] = {}
        for h, val in zip(headers, row_vals):
            if h:
                row_dict[h] = val

        anio = _clean_val(row_dict.get("anio"), "int")
        mes = _clean_val(row_dict.get("mes"), "int")
        casos = _clean_val(row_dict.get("casos_dengue"), "int")
        temp = _clean_val(row_dict.get("temperatura_c"), "float")
        hum = _clean_val(row_dict.get("humedad_pct"), "float")
        prec = _clean_val(row_dict.get("precipitacion_mm"), "float")

        if anio is None and mes is None and casos is None:
            continue

        records.append({
            "anio": anio,
            "mes": mes,
            "casos_dengue": casos,
            "temperatura_c": temp,
            "humedad_pct": hum,
            "precipitacion_mm": prec,
        })

    return records


def parse_data_file(path: Path | str) -> list[dict[str, Any]]:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return parse_csv(p)
    elif suffix in (".xlsx", ".xlsm"):
        return parse_xlsx(p)
    else:
        raise ValueError(f"Formato no soportado: '{suffix}'. Solo se admiten archivos .csv y .xlsx.")
