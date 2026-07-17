"""Create a machine-readable data-quality report for every pipeline run."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from src.validators.validation_layer import ValidationResult


def build_quality_report(
    validation: ValidationResult,
    pdf_path: Path,
    word_path: Path,
    workbook_path: Path,
    program_date: date | None,
) -> dict:
    """Return an auditable summary without exposing the source file contents."""

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "program_date": program_date.isoformat() if program_date else None,
        "source_files": {
            "fleet_forecast_pdf": pdf_path.name,
            "operations_report_docx": word_path.name,
            "program_template_xlsx": workbook_path.name,
        },
        "summary": {
            "commercial_updates_approved": len(validation.commercial_updates),
            "ticket_updates_approved": len(validation.ticket_updates),
            "reserve_updates_approved": len(validation.reserve_updates),
            "validation_issues": len(validation.issues),
            "execution_issues": 0,
            "status": "passed" if not validation.issues else "failed",
        },
        "issues": [asdict(issue) for issue in validation.issues],
    }


def add_execution_issue(
    report: dict,
    rule_id: str,
    source: str,
    record_id: str,
    description: str,
) -> None:
    """Add a post-validation execution error, such as an invalid UI input."""

    report["issues"].append(
        {
            "rule_id": rule_id,
            "source": source,
            "record_id": record_id,
            "description": description,
        }
    )
    report["summary"]["execution_issues"] += 1
    report["summary"]["status"] = "failed"


def write_quality_report(report: dict, path: Path) -> Path:
    """Persist the report as UTF-8 JSON for review, audit and automation."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
