"""
transformation_layer.py

TransformationLayer — implements docs/07_transformation_design.md.

Takes the three raw extractor outputs and produces the three "Update
Datasets" the Validation Layer expects:

    CommercialServicesDataset  ─┐
    ReserveDataset              ├─► TransformationLayer ─► CommercialUpdateDataset
    OperationsDataset          ─┘                          TicketUpdateDataset
                                                            ReserveUpdateDataset

Key business rule applied here (see docs/01_requirements.md, rule 2):
combined services in the PDF (e.g. service="301-302") are split into
one CommercialUpdateRecord per individual service number, all sharing
the same registration. This is necessary because the Word dataset
already reports segments against individual service numbers ("301",
"302" as separate train_number values, never "301-302"), and the
Excel template has one block per individual service number — so the
combined PDF string has no direct counterpart to match against
downstream; splitting it here is what makes BR-001/BR-002 matching
possible at all.

This layer does not validate business rules, compare datasets against
each other, or touch `Programa.xlsx` — all explicitly out of scope
per the design doc.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.extractors.pdf_extractor import CommercialRecord, ReserveRecord
from src.extractors.word_extractor import OperationsRecord


@dataclass
class CommercialUpdateRecord:
    """Used to update the Registration column. Matching field: service."""

    service: str  # always a single service number after splitting, e.g. "301" (never "301-302")
    registration: str
    # Original services from one PDF row. This preserves the information that
    # they may share one vertically-merged Matrícula cell in Programa.
    source_services: tuple[str, ...] = ()


@dataclass
class TicketUpdateRecord:
    """Used to update TicketsSold. Validation fields: service, route_segment."""

    service: str
    route_segment: str
    tickets_sold: int


@dataclass
class ReserveUpdateRecord:
    """Used to populate the Reserve section of Programa.xlsx."""

    workshop_station: str
    registration: str
    status: str


@dataclass
class TransformationResult:
    commercial_updates: list[CommercialUpdateRecord] = field(default_factory=list)
    ticket_updates: list[TicketUpdateRecord] = field(default_factory=list)
    reserve_updates: list[ReserveUpdateRecord] = field(default_factory=list)


class TransformationLayer:
    """
    Implements docs/07_transformation_design.md.

    Standardizes and reshapes extractor output into the three Update
    Datasets consumed by the Validation Layer. No validation, no
    cross-dataset comparison, no Excel writes.
    """

    def transform_commercial(
        self, records: list[CommercialRecord]
    ) -> list[CommercialUpdateRecord]:
        """
        Splits combined services ("301-302") into one record per
        individual service number, all sharing the same registration.
        See module docstring for why this split is required.
        """
        updates: list[CommercialUpdateRecord] = []
        for rec in records:
            source_services = tuple(rec.service.split("-"))
            for single_service in source_services:
                updates.append(
                    CommercialUpdateRecord(
                        service=single_service,
                        registration=rec.registration,
                        source_services=source_services,
                    )
                )
        return updates

    def transform_tickets(self, records: list[OperationsRecord]) -> list[TicketUpdateRecord]:
        """
        One-to-one reshape: OperationsRecord already has one row per
        segment with an individual (non-combined) train number, so no
        splitting is needed here — see docs/06_word_extractor_design.md.
        """
        return [
            TicketUpdateRecord(
                service=rec.train_number,
                route_segment=rec.route_segment,
                tickets_sold=rec.tickets_sold,
            )
            for rec in records
        ]

    def transform_reserve(self, records: list[ReserveRecord]) -> list[ReserveUpdateRecord]:
        """One-to-one reshape — reserve records need no splitting or merging."""
        return [
            ReserveUpdateRecord(
                workshop_station=rec.workshop_station,
                registration=rec.registration,
                status=rec.status,
            )
            for rec in records
        ]

    def transform(
        self,
        commercial_services: list[CommercialRecord],
        reserve: list[ReserveRecord],
        operations: list[OperationsRecord],
    ) -> TransformationResult:
        return TransformationResult(
            commercial_updates=self.transform_commercial(commercial_services),
            ticket_updates=self.transform_tickets(operations),
            reserve_updates=self.transform_reserve(reserve),
        )


if __name__ == "__main__":
    import sys

    from src.extractors.pdf_extractor import PDFExtractor
    from src.extractors.word_extractor import WordExtractor

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/prevision_flota_sample.pdf"
    docx_path = sys.argv[2] if len(sys.argv) > 2 else "data/raw/parte_operaciones_sample.docx"

    pdf_result = PDFExtractor().extract(pdf_path)
    word_result = WordExtractor().extract(docx_path)

    layer = TransformationLayer()
    result = layer.transform(
        commercial_services=pdf_result.commercial_services,
        reserve=pdf_result.reserve,
        operations=word_result.operations,
    )

    print(f"CommercialUpdateDataset: {len(result.commercial_updates)} records")
    for rec in result.commercial_updates:
        print(f"  service={rec.service:8s} registration={rec.registration}")

    print(f"\nTicketUpdateDataset: {len(result.ticket_updates)} records")
    for rec in result.ticket_updates:
        print(f"  service={rec.service:5s} tickets={rec.tickets_sold:4d}  route={rec.route_segment}")

    print(f"\nReserveUpdateDataset: {len(result.reserve_updates)} records")
    for rec in result.reserve_updates:
        print(f"  {rec.workshop_station:12s} {rec.registration}  {rec.status}")
