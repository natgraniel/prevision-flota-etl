"""Command-line entry point for the full Fleet Forecast ETL pipeline."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from src.extractors.pdf_extractor import PDFExtractor
from src.extractors.word_extractor import WordExtractor
from src.loaders.excel_loader import ExcelLoader
from src.models.workbook_reader import WorkbookReader
from src.transformers.transformation_layer import TransformationLayer
from src.validators.validation_layer import ValidationLayer


def parse_program_date(value: str):
    """Parse the user-facing ``dd/mm/yyyy`` Programa date."""

    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use the date format dd/mm/yyyy.") from error


def run(
    pdf_path: Path,
    word_path: Path,
    workbook_path: Path,
    output_path: Path,
    program_date=None,
    test_train: str | None = None,
    test_registration: str | None = None,
):
    pdf_result = PDFExtractor().extract(str(pdf_path))
    word_result = WordExtractor().extract(str(word_path))
    transformed = TransformationLayer().transform(
        pdf_result.commercial_services, pdf_result.reserve, word_result.operations
    )
    validated = ValidationLayer().validate(transformed, WorkbookReader().read(str(workbook_path)))

    if validated.issues:
        for issue in validated.issues:
            print(f"{issue.rule_id} | {issue.record_id} | {issue.description}")
        raise RuntimeError("No output was generated because validation reported issues.")

    return ExcelLoader().load(
        validated,
        workbook_path,
        output_path,
        program_date,
        test_train,
        test_registration,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the daily Programa workbook.")
    parser.add_argument("--pdf", type=Path, required=True, help="Fleet forecast PDF")
    parser.add_argument("--word", type=Path, required=True, help="Operations report DOCX")
    parser.add_argument("--programa", type=Path, required=True, help="Programa template XLSX")
    parser.add_argument("--output", type=Path, required=True, help="Destination XLSX")
    parser.add_argument("--date", type=parse_program_date, help="Program date: dd/mm/yyyy")
    parser.add_argument("--test-train", help="Test train number, for example P019/P018")
    parser.add_argument("--test-mr", help="Test train MR registration, for example N001")
    args = parser.parse_args()

    program_date = args.date
    if program_date is None:
        captured_date = input("Fecha del Programa (dd/mm/aaaa, Enter para conservar B3): ").strip()
        if captured_date:
            program_date = parse_program_date(captured_date)

    test_train = args.test_train
    test_registration = args.test_mr
    if (test_train is None) != (test_registration is None):
        parser.error("--test-train and --test-mr must be provided together.")
    if test_train is None:
        has_test = input("¿Hay tren de pruebas? (s/n): ").strip().casefold()
        if has_test in {"s", "si", "sí"}:
            test_train = input("Tren de pruebas: ").strip()
            test_registration = input("MR/Matrícula: ").strip()
        elif has_test not in {"n", "no", ""}:
            parser.error("Respond with s or n for the test train question.")

    result = run(
        args.pdf,
        args.word,
        args.programa,
        args.output,
        program_date,
        test_train,
        test_registration,
    )
    print(f"Programa generated: {result.output_path}")


if __name__ == "__main__":
    main()
