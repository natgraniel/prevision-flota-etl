import json
from datetime import date
from pathlib import Path

import pytest

from src.reporting.quality_report import build_quality_report, write_quality_report
from src.loaders.excel_loader import TestTrainInput, TestTrainValidationError
from src.pipeline import run
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


def test_pipeline_reports_invalid_test_train_input(tmp_path):
    raw = Path("data/raw")
    report_path = tmp_path / "quality_report.json"

    with pytest.raises(TestTrainValidationError):
        run(
            pdf_path=next(raw.glob("*.pdf")),
            word_path=next(raw.glob("*.docx")),
            workbook_path=next(raw.glob("*.xlsx")),
            output_path=tmp_path / "Programa.xlsx",
            program_date=date(2026, 7, 10),
            test_trains=[
                TestTrainInput("P009", "855+000 - 893+000", "ROO7", "17:00", "03:00")
            ],
            report_path=report_path,
            log_dir=tmp_path / "logs",
            lock_dir=tmp_path,
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["status"] == "failed"
    assert report["summary"]["validation_issues"] == 0
    assert report["summary"]["execution_issues"] == 1
    assert report["issues"][-1]["rule_id"] == "UI-001"
    assert "ROO7" in report["issues"][-1]["description"]


def test_execution_lock_rejects_parallel_run(tmp_path):
    with exclusive_run_lock(tmp_path):
        with pytest.raises(RunAlreadyInProgressError):
            with exclusive_run_lock(tmp_path):
                pass
