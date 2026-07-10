# ETL Pipeline: Fleet Forecast → Daily Train Program (Tren Maya)

An ETL (Extract, Transform, Load) pipeline that automates the creation
of the daily **"Programa"** document from two unstructured sources: a
fleet-forecast PDF and an operations-report Word document.

> Data Analyst / Data Engineer portfolio project.
> Source documents contain real operational data (station names, train
> numbers, rolling-stock registration numbers); documentation and code
> are in English, raw data samples are kept as-is.

## Business problem

Every day, operations must manually consolidate — into an Excel file
called **Programa** — which rolling stock (registration number) will
run each commercial service the following day, and how many tickets
have been sold per route segment. Today this is transcribed by hand
from two documents that arrive in different, non-tabular formats.

## Objective

Automate the extraction and cross-referencing of this data, with a
**data quality validation layer** that surfaces inconsistencies
(unmatched train numbers, mismatched routes, structural changes
between days) instead of failing silently or propagating bad data.

## Sources (Extract)

| # | File | Format | Relevant content |
|---|---|---|---|
| 1 | Fleet Forecast PDF | Semi-tabular PDF (2 tables) | Service number(s) per train, assigned registration, reserve units |
| 2 | Operations Report (Word) | Word (1 table) | Route segment, train number, tickets sold, occupancy % |

## Destination (Load)

`Programa_DD_MM_YYYY.xlsx`, sheet `DIARIO` — **only** the `Matrícula`
(registration) and `Cantidad de boletos vendidos` (tickets sold)
columns are updated; the rest of the template (scheduled times, travel
duration) is left untouched.

## Key design decision: the PDF is the structural source of truth

The number of reserve units and whether a service is single (`101`) or
combined (`301-302`) **can change from day to day**, and this is driven
entirely by the fleet-forecast PDF. The pipeline does not assume a
fixed row layout in the Excel template — it derives the day's structure
dynamically from the PDF and reconciles it against the template before
loading data. See `03_pipeline_diagram.md` for the reconciliation step.

## Repo structure

```
prevision-flota-etl/
├── README.md
├── docs/
│   ├── 01_requirements.md      ← scope, business rules, success criteria
│   ├── 02_data_dictionary.md   ← data dictionary for all 3 sources
│   └── 03_pipeline_diagram.md  ← ETL flow diagram (Mermaid)
├── src/                        ← (next phase) pipeline code
├── tests/                      ← (next phase) unit tests
└── data/
    ├── raw/                    ← sample input files
    └── output/                 ← generated Programa + quality report
```

## Project status

- [x] Phase 0 — Documentation & data dictionary
- [ ] Phase 1 — Environment & version control
- [ ] Phase 2 — Extraction (PDF/Word)
- [ ] Phase 3 — Transformation & business rules
- [ ] Phase 4 — Data quality validation
- [ ] Phase 5 — Load to Excel
- [ ] Phase 6 — Tests
- [ ] Phase 7 — Logging
- [ ] Phase 8 — CI/CD (GitHub Actions)
