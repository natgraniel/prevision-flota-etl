from datetime import date

from src.utils.source_date import extract_fleet_forecast_date, extract_operations_report_date


def test_extract_fleet_forecast_date_accepts_full_spanish_month_and_copy_suffix():
    assert extract_fleet_forecast_date(
        "PREVISION FLOTA TREN MAYA PARA EL DÍA 10-Julio-2026 (1).pdf"
    ) == date(2026, 7, 10)


def test_extract_operations_report_date_uses_date_before_hecho_el():
    assert extract_operations_report_date(
        "PARTE OPERACIONES DEL 16 JUL HECHO EL 15 JUL 2026.docx"
    ) == date(2026, 7, 16)


def test_extract_operations_report_date_accepts_single_digit_days():
    assert extract_operations_report_date(
        "PARTE OPERACIONES DEL 4 JUN HECHO EL 3 JUN 2026.docx"
    ) == date(2026, 6, 4)


def test_unknown_filename_returns_none():
    assert extract_fleet_forecast_date("prevision.pdf") is None
    assert extract_operations_report_date("parte.docx") is None
