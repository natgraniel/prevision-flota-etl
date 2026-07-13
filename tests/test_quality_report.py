from datetime import date

import pytest

from src.reporting.quality_report import build_quality_report, write_quality_report
from src.utils.execution_lock import RunAlreadyInProgressError, exclusive_run_lock
from src.validators.validation_layer import ValidationIssue, ValidationResult


def test_quality_report_records_failed_validation(tmp_path):
    result = ValidationResult(
        issues=[ValidationIssue("BR-001", "PDF", "101", "Missing service")]
    )
    report = build_quality_report(
        result,
        tmp_path / "forecast.pdf",
        tmp_path / "operations.docx",
        tmp_path / "programa.xlsx",
        date(2026, 7, 10),
    )
    output = write_quality_report(report, tmp_path / "quality_report.json")

    assert output.exists()
    assert report["summary"]["status"] == "failed"
    assert report["issues"][0]["rule_id"] == "BR-001"


def test_execution_lock_rejects_parallel_run(tmp_path):
    with exclusive_run_lock(tmp_path):
        with pytest.raises(RunAlreadyInProgressError):
            with exclusive_run_lock(tmp_path):
                pass
