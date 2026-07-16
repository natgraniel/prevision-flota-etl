"""Identify the Programa date represented by source-document filenames."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re
import unicodedata


SPANISH_MONTHS = {
    "ENE": 1, "ENERO": 1,
    "FEB": 2, "FEBRERO": 2,
    "MAR": 3, "MARZO": 3,
    "ABR": 4, "ABRIL": 4,
    "MAY": 5, "MAYO": 5,
    "JUN": 6, "JUNIO": 6,
    "JUL": 7, "JULIO": 7,
    "AGO": 8, "AGOSTO": 8,
    "SEP": 9, "SEPT": 9, "SEPTIEMBRE": 9,
    "OCT": 10, "OCTUBRE": 10,
    "NOV": 11, "NOVIEMBRE": 11,
    "DIC": 12, "DICIEMBRE": 12,
}


def _normalize_filename(path: str | Path) -> str:
    """Return an accent-free uppercase filename for predictable matching."""

    name = Path(path).stem.upper()
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(
        character for character in decomposed
        if not unicodedata.combining(character)
    )


def _make_date(day: str, month_name: str, year: str) -> date | None:
    month = SPANISH_MONTHS.get(month_name)
    if month is None:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def extract_fleet_forecast_date(path: str | Path) -> date | None:
    """Extract dates such as ``13-Julio-2026`` from a fleet PDF name."""

    filename = _normalize_filename(path)
    match = re.search(r"\b(\d{1,2})[\s_-]+([A-Z]+)[\s_-]+(20\d{2})\b", filename)
    if match is None:
        return None
    return _make_date(*match.groups())


def extract_operations_report_date(path: str | Path) -> date | None:
    """Extract the target date before ``HECHO EL`` from an operations Word name."""

    filename = _normalize_filename(path)
    match = re.search(
        r"\bDEL\s+(\d{1,2})\s+([A-Z]+)(?:\s+(20\d{2}))?\s+HECHO\b",
        filename,
    )
    if match is None:
        return None

    day, month_name, year = match.groups()
    if year is None:
        years = re.findall(r"\b20\d{2}\b", filename)
        if not years:
            return None
        year = years[-1]
    return _make_date(day, month_name, year)
