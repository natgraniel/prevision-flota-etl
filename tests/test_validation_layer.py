from src.models.workbook_reader import CommercialBlockRow, ReserveBlockRow, WorkbookStructure
from src.transformers.transformation_layer import (
    CommercialUpdateRecord,
    ReserveUpdateRecord,
    TicketUpdateRecord,
    TransformationResult,
)
from src.validators.validation_layer import ValidationLayer, normalize_route


def test_normalize_route_ignores_accents_case_and_punctuation():
    assert normalize_route("Estacion Cancun") == normalize_route("Cancun Aeropuerto")
    assert normalize_route("Palenque – S.F. Campeche.") == normalize_route(
        "palenque-sf campeche"
    )


def test_validation_rebuilds_split_excel_route_and_keeps_reserves_dynamic():
    workbook = WorkbookStructure(
        commercial_rows=[
            CommercialBlockRow(7, "101", "Palenque – ", True),
            CommercialBlockRow(8, "", "SF Campeche.", False),
        ],
        reserve_rows=[
            ReserveBlockRow(70, "Cancún", True),
            ReserveBlockRow(71, None, False),
        ],
    )
    updates = TransformationResult(
        commercial_updates=[CommercialUpdateRecord("101", "L010")],
        ticket_updates=[TicketUpdateRecord("101", "Palenque – S.F. Campeche.", 85)],
        reserve_updates=[ReserveUpdateRecord("Cancun", "D008", "RESERVA EN ESTACION")],
    )

    result = ValidationLayer().validate(updates, workbook)

    assert result.issues == []
    assert result.commercial_updates[0].target_row == 7
    assert result.ticket_updates[0].target_row == 7
    assert result.reserve_updates[0].target_row == 0
