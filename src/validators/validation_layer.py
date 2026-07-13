"""Validate transformed update datasets against the Programa workbook structure.

This layer is deliberately read-only.  It turns a :class:`TransformationResult`
and a :class:`WorkbookStructure` into records that a future Excel loader can
write safely, plus a traceable list of rejected records.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from src.models.workbook_reader import CommercialBlockRow, WorkbookStructure
from src.transformers.transformation_layer import (
    CommercialUpdateRecord,
    ReserveUpdateRecord,
    TicketUpdateRecord,
    TransformationResult,
)

REGISTRATION_RE = re.compile(r"^[A-Z]\d{3}$")
VALID_RESERVE_STATUSES = {"reserva", "reserva en estacion"}
# Verified naming difference between the real Word source and Programa
# template. Keep this mapping small and explicit: it is a business glossary,
# not fuzzy matching.
STATION_ALIASES = {"estacioncancun": "cancunaeropuerto"}


@dataclass(frozen=True)
class ValidationIssue:
    """A rejected source record and the business rule that rejected it."""

    rule_id: str
    source: str
    record_id: str
    description: str


@dataclass(frozen=True)
class ValidatedCommercialUpdate:
    service: str
    registration: str
    target_row: int


@dataclass(frozen=True)
class ValidatedTicketUpdate:
    service: str
    route_segment: str
    tickets_sold: int
    target_row: int


@dataclass(frozen=True)
class ValidatedReserveUpdate:
    workshop_station: str
    registration: str
    status: str
    target_row: int


@dataclass
class ValidationResult:
    commercial_updates: list[ValidatedCommercialUpdate] = field(default_factory=list)
    ticket_updates: list[ValidatedTicketUpdate] = field(default_factory=list)
    reserve_updates: list[ValidatedReserveUpdate] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)


def normalize_route(value: str) -> str:
    """Normalize route text for BR-002's deliberately flexible comparison.

    Case, accents, whitespace, punctuation and dash variants are ignored.  For
    example, ``"Palenque – S.F. Campeche."`` and ``"palenque-sf campeche"``
    both normalize to ``"palenquesfcampeche"``.
    """

    decomposed = unicodedata.normalize("NFKD", value.lower())
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    normalized = "".join(ch for ch in without_accents if ch.isalnum())
    for source_name, canonical_name in STATION_ALIASES.items():
        normalized = normalized.replace(source_name, canonical_name)
    return normalized


def _service_blocks(rows: list[CommercialBlockRow]) -> dict[str, list[CommercialBlockRow]]:
    """Group physical Excel rows under their vertically-merged service anchor."""

    blocks: dict[str, list[CommercialBlockRow]] = {}
    active_service: str | None = None
    for row in rows:
        if row.is_anchor_row:
            active_service = row.service
            blocks[active_service] = []
        if active_service is not None:
            blocks[active_service].append(row)
    return blocks


def _route_targets(rows: list[CommercialBlockRow]) -> list[tuple[str, int]]:
    """Rebuild each logical route segment from one or two physical Excel rows."""

    targets: list[tuple[str, int]] = []
    index = 0
    while index < len(rows):
        current = rows[index]
        route = (current.route or "").strip()
        if not route:
            index += 1
            continue

        # The template often splits a segment at the dash, e.g. C7/C8:
        # "Palenque – " + "SF Campeche.".  The ticket cell is vertically
        # merged over those same rows, with its writable anchor in the first.
        if route.rstrip().endswith(("-", "–", "—")) and index + 1 < len(rows):
            next_route = (rows[index + 1].route or "").strip()
            if next_route:
                targets.append((f"{route} {next_route}", current.row))
                index += 2
                continue

        targets.append((route, current.row))
        index += 1
    return targets


class ValidationLayer:
    """Apply BR-001 through BR-004 before the workbook is changed."""

    def validate(
        self, updates: TransformationResult, workbook: WorkbookStructure
    ) -> ValidationResult:
        result = ValidationResult()
        service_blocks = _service_blocks(workbook.commercial_rows)

        self._validate_commercial(updates.commercial_updates, service_blocks, result)
        self._validate_tickets(updates.ticket_updates, service_blocks, result)
        self._validate_reserves(updates.reserve_updates, workbook, result)
        return result

    @staticmethod
    def _validate_commercial(
        updates: list[CommercialUpdateRecord],
        service_blocks: dict[str, list[CommercialBlockRow]],
        result: ValidationResult,
    ) -> None:
        for update in updates:
            if not REGISTRATION_RE.fullmatch(update.registration):
                result.issues.append(
                    ValidationIssue(
                        "BR-003",
                        "PrevisionFlota.pdf",
                        update.service,
                        f"Invalid registration: {update.registration!r}.",
                    )
                )
                continue

            block = service_blocks.get(update.service)
            if not block:
                result.issues.append(
                    ValidationIssue(
                        "BR-001",
                        "PrevisionFlota.pdf",
                        update.service,
                        "Service does not exist in Programa's commercial section.",
                    )
                )
                continue

            result.commercial_updates.append(
                ValidatedCommercialUpdate(update.service, update.registration, block[0].row)
            )

    @staticmethod
    def _validate_tickets(
        updates: list[TicketUpdateRecord],
        service_blocks: dict[str, list[CommercialBlockRow]],
        result: ValidationResult,
    ) -> None:
        used_rows: set[int] = set()
        for update in updates:
            block = service_blocks.get(update.service)
            if not block:
                result.issues.append(
                    ValidationIssue(
                        "BR-002",
                        "Parte de Operaciones.docx",
                        update.service,
                        "Service does not exist in Programa's commercial section.",
                    )
                )
                continue

            expected_route = normalize_route(update.route_segment)
            match = next(
                (
                    (route, row)
                    for route, row in _route_targets(block)
                    if row not in used_rows and normalize_route(route) == expected_route
                ),
                None,
            )
            if match is None:
                result.issues.append(
                    ValidationIssue(
                        "BR-002",
                        "Parte de Operaciones.docx",
                        f"{update.service}: {update.route_segment}",
                        "Route segment does not match any available Programa route for this service.",
                    )
                )
                continue

            _, target_row = match
            used_rows.add(target_row)
            result.ticket_updates.append(
                ValidatedTicketUpdate(
                    update.service, update.route_segment, update.tickets_sold, target_row
                )
            )

    @staticmethod
    def _validate_reserves(
        updates: list[ReserveUpdateRecord],
        workbook: WorkbookStructure,
        result: ValidationResult,
    ) -> None:
        slots_by_station: dict[str, list[int]] = {}
        active_station = ""
        for row in workbook.reserve_rows:
            if row.is_anchor_row and row.station:
                active_station = row.station
            if active_station:
                slots_by_station.setdefault(normalize_route(active_station), []).append(row.row)

        next_slot_by_station: dict[str, int] = {}
        for update in updates:
            normalized_status = " ".join(update.status.lower().split())
            station_key = normalize_route(update.workshop_station)
            if (
                not update.workshop_station.strip()
                or not REGISTRATION_RE.fullmatch(update.registration)
                or normalized_status not in VALID_RESERVE_STATUSES
            ):
                result.issues.append(
                    ValidationIssue(
                        "BR-004",
                        "PrevisionFlota.pdf",
                        update.registration or "<empty registration>",
                        "Reserve record requires station, valid registration and an allowed status.",
                    )
                )
                continue

            slot_index = next_slot_by_station.get(station_key, 0)
            station_slots = slots_by_station.get(station_key, [])
            if slot_index >= len(station_slots):
                result.issues.append(
                    ValidationIssue(
                        "BR-004",
                        "PrevisionFlota.pdf",
                        update.registration,
                        f"No available Reserva row for station {update.workshop_station!r}.",
                    )
                )
                continue

            result.reserve_updates.append(
                ValidatedReserveUpdate(
                    update.workshop_station,
                    update.registration,
                    update.status,
                    station_slots[slot_index],
                )
            )
            next_slot_by_station[station_key] = slot_index + 1
