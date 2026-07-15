# Requirements Document

## 1. Business context

The Dirección de Circulación Ferroviaria (Railway Operations
Directorate) must publish, every day, a document called **Programa**,
consolidating which rolling stock (registration number) will cover each
commercial service the following day, and how many tickets have already
been sold for each route segment of that service. Today this information
is transcribed by hand from two documents that arrive in different,
non-tabular formats.

## 2. Users / stakeholders

- **Direct user**: staff member of the Dirección de Circulación
  Ferroviaria responsible for preparing the Programa.
- **End users**: operational and management personnel who use the
  Programa for daily circulation and fleet-management decisions.

## 3. Scope

### In scope
- Extract from the **Fleet Forecast (PDF)**: service number(s) and
  assigned registration (table 1), and registration + reserve station
  (table 2, rows flagged `RESERVA`).
- Extract from the **Operations Report (Word)**: route segment, train
  number, and tickets sold.
- Cross-reference both sources by **train number (service)**.
- Update only the `Matrícula` (registration) and `Cantidad de boletos
  vendidos` (tickets sold) columns of the Programa Excel file,
  preserving the rest of the template (scheduled times, travel
  duration, formatting).
- Generate a **data quality report** listing any inconsistency found.
- **Reconcile the day's structure** (see rule 7 below) before writing
  any data.

### Out of scope (for now)
- The "preventive maintenance" and "non-productive received trains"
  blocks in the PDF are **not** transcribed to the Programa — only
  commercial services and reserve units are.
- Creating the Programa template itself is not automated (it is
  assumed to already exist with its formatting).
- Scheduled times are never edited, only registration and tickets.

## 4. Business rules (critical)

1. **Match by train number**: the service number from the PDF
   (`Servicio` column) must also exist as `Número de tren` in the Word
   file. If there's no match → it is reported as a discrepancy, never
   silently dropped.
2. **Combined services** (e.g. `301-302`, `304-303`): when the PDF
   lists two service numbers separated by a hyphen in a single cell,
   **both service numbers receive the same registration** in the
   Programa.
3. **Multiple segments per service**: a single service can have
   several route segments (e.g. train 101: Palenque→SF Campeche→
   Mérida Teya→Cancún), each with its own ticket count. The
   registration is unique per service, but tickets are assigned per
   segment, in the same order the segments appear in the Word file.
4. **Reserve units**: rows in PDF table 2 flagged `RESERVA` or
   `RESERVA EN ESTACIÓN` are transcribed in full (station +
   registration) into the "Reserve" section of the Programa — they
   carry no route or ticket data.
5. **Cross-validation of route**: the sequence of stations in the Word
   file must be consistent with the route declared in the PDF for that
   service number (e.g. service 101 = "Palenque-Cancún" in the PDF
   should correspond to the Palenque→...→Cancún segments in the Word
   file).
6. **No blind overwrite**: the Programa Excel file already exists with
   formatting and time formulas; the pipeline must update specific
   cells, not regenerate the whole file.
7. **Structural reconciliation (day-to-day variability)**: the number
   of reserve units and whether a service is single or combined **can
   change from one day to the next**, and this is dictated entirely by
   the PDF — never assumed from a previous day's layout. Before
   merging data, the pipeline must compare the "shape" implied by that
   day's PDF (which service numbers exist, which are combined, how
   many reserve rows there are) against the current Excel template's
   block structure. If they differ — e.g. a new combined service that
   didn't exist the day before, or a change in the count of reserve
   units — this is reported as a **structural discrepancy**, a
   distinct category from a simple data-matching issue, since it may
   require adjusting the template's row/merge structure rather than
   just writing values into existing cells.

## 5. Success criteria

- 100% of the day's commercial services end up with the correct
  registration and ticket counts, verified against a manually-built
  reference Programa (used as ground truth for testing).
- Any discrepancy (unmatched train, inconsistent route, structural
  change) is documented in a report, never hidden.
- The process is repeatable day after day by swapping only the 3 input
  files.

## 6. Non-functional requirements

- **Idempotency**: running the pipeline twice with the same input
  files must produce the same result.
- **Traceability**: logging at every step (what was extracted, what
  was discarded, what failed to match).
- **Reproducibility**: virtual environment + `requirements.txt` with
  pinned versions.
