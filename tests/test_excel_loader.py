from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from src.extractors.pdf_extractor import PDFExtractor
from src.extractors.word_extractor import WordExtractor
from src.loaders.excel_loader import ExcelLoader
from src.models.workbook_reader import WorkbookReader
from src.transformers.transformation_layer import TransformationLayer
from src.validators.validation_layer import ValidationLayer


def test_loader_writes_only_validated_cells_and_preserves_schedule(tmp_path: Path):
    raw = Path("data/raw")
    source = next(raw.glob("*.xlsx"))
    pdf = next(raw.glob("*.pdf"))
    docx = next(raw.glob("*.docx"))
    output = tmp_path / "Programa_actualizado.xlsx"
    source_workbook = load_workbook(source, data_only=False)
    source_schedule = source_workbook["DIARIO"]["F7"].value

    pdf_result = PDFExtractor().extract(str(pdf))
    word_result = WordExtractor().extract(str(docx))
    transformed = TransformationLayer().transform(
        pdf_result.commercial_services, pdf_result.reserve, word_result.operations
    )
    validated = ValidationLayer().validate(transformed, WorkbookReader().read(str(source)))

    load_result = ExcelLoader().load(
        validated,
        source,
        output,
        program_date=date(2026, 7, 10),
        test_train="P019/P018",
        test_registration="N001",
    )
    workbook = load_workbook(output, data_only=False)
    worksheet = workbook["DIARIO"]

    assert load_result.commercial_updates_written == 22
    assert load_result.ticket_updates_written == 32
    assert load_result.reserve_updates_written == 14
    assert load_result.test_train_written is True
    assert worksheet["D7"].value == "L003"  # service 101 from the PDF
    assert worksheet["B3"].value == "10 Julio. 2026"
    assert worksheet["B68"].value == "P019/P018"
    assert worksheet["D68"].value == "N001"
    assert worksheet["B68"].fill.fgColor.rgb == "00FFFFFF"
    assert worksheet["D68"].fill.fgColor.rgb == "00FFFFFF"
    assert worksheet["E7"].value == 134  # first 101 route segment from Word
    assert worksheet["F7"].value == source_schedule  # protected schedule value
    assert worksheet["D70"].value == "L007"  # first Cancún reserve
    assert worksheet["E70"].value == "RESERVA EN ESTACION"
    assert worksheet["E72"].value is None  # plain RESERVA is intentionally blank
