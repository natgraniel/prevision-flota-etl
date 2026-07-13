"""Write validated ETL updates to a copy of Programa.xlsx.

The loader deliberately accepts only ``ValidationResult``.  It never decides
whether a source record is correct; it writes the exact anchor rows selected by
the Validation Layer and preserves every other workbook value and format.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import PatternFill

from src.validators.validation_layer import ValidationResult

SHEET_NAME = "DIARIO"
COL_STATION = 2  # B
COL_REGISTRATION = 4  # D
COL_TICKETS = 5  # E
COL_RESERVE_STATUS = 5  # E
CELL_PROGRAM_DATE = "B3"
TEST_ROW = 68
TEST_TRAIN_CELL = "B68"
TEST_REGISTRATION_CELL = "D68"
VALID_REGISTRATION_RE = re.compile(r"^[A-Z]\d{3}$")
WHITE_FILL = PatternFill(fill_type="solid", fgColor="FFFFFF")
MONTH_NAMES_ES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


@dataclass(frozen=True)
class LoadResult:
    output_path: Path
    commercial_updates_written: int
    ticket_updates_written: int
    reserve_updates_written: int
    test_train_written: bool


class ExcelLoader:
    """Persist validated updates without changing Programa's layout."""

    def load(
        self,
        validated_updates: ValidationResult,
        input_path: str | Path,
        output_path: str | Path,
        program_date: date | None = None,
        test_train: str | None = None,
        test_registration: str | None = None,
    ) -> LoadResult:
        source = Path(input_path).resolve()
        destination = Path(output_path).resolve()
        if source == destination:
            raise ValueError("Output path must differ from input path; the template is never overwritten.")

        workbook = load_workbook(source, data_only=False)
        worksheet = workbook[SHEET_NAME]

        if program_date is not None:
            self._write(worksheet, 3, 2, format_program_date(program_date))

        self._write_test_train(worksheet, test_train, test_registration)

        for update in validated_updates.commercial_updates:
            self._write(worksheet, update.target_row, COL_REGISTRATION, update.registration)

        for update in validated_updates.ticket_updates:
            self._write(worksheet, update.target_row, COL_TICKETS, update.tickets_sold)

        for update in validated_updates.reserve_updates:
            self._write(worksheet, update.target_row, COL_STATION, update.workshop_station)
            self._write(worksheet, update.target_row, COL_REGISTRATION, update.registration)
            # "RESERVA" is the default condition in this section and must not
            # be displayed.  Only the more specific station reservation stays
            # visible in the final Programa.
            status_to_write = "" if update.status.strip().upper() == "RESERVA" else update.status
            self._write(worksheet, update.target_row, COL_RESERVE_STATUS, status_to_write)

        destination.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(destination)

        return LoadResult(
            output_path=destination,
            commercial_updates_written=len(validated_updates.commercial_updates),
            ticket_updates_written=len(validated_updates.ticket_updates),
            reserve_updates_written=len(validated_updates.reserve_updates),
            test_train_written=test_train is not None,
        )

    @staticmethod
    def _write_test_train(worksheet, train: str | None, registration: str | None) -> None:
        """Optionally write one user-entered test train in the existing test row."""

        if train is None and registration is None:
            return
        if not train or not registration:
            raise ValueError("Test train and MR registration must be entered together.")

        normalized_registration = registration.strip().upper()
        if not VALID_REGISTRATION_RE.fullmatch(normalized_registration):
            raise ValueError("Test MR registration must follow the pattern A000, for example N001.")

        ExcelLoader._write(worksheet, TEST_ROW, 2, train.strip())
        ExcelLoader._write(worksheet, TEST_ROW, 4, normalized_registration)
        # B68:C68 is a merged field. Styling its top-left anchor preserves its
        # merge, border and alignment while applying the requested white fill.
        worksheet[TEST_TRAIN_CELL].fill = WHITE_FILL
        worksheet[TEST_REGISTRATION_CELL].fill = WHITE_FILL

    @staticmethod
    def _write(worksheet, row: int, column: int, value: str | int) -> None:
        """Write to a validated cell, resolving merge children to their anchor."""

        cell = worksheet.cell(row=row, column=column)
        if isinstance(cell, MergedCell):
            for merged_range in worksheet.merged_cells.ranges:
                if cell.coordinate in merged_range:
                    cell = worksheet.cell(merged_range.min_row, merged_range.min_col)
                    break
            else:
                raise ValueError(f"Merged cell {cell.coordinate} has no merge anchor.")
        cell.value = value


def format_program_date(value: date) -> str:
    """Format a user-entered date exactly as the Programa title expects."""

    return f"{value.day:02d} {MONTH_NAMES_ES[value.month - 1]}. {value.year}"
