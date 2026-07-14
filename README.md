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

## A note on Python version

This project was developed against **Python 3.14**, since that was
already installed on the development machine. In hindsight, pinning to
a more established LTS-style version (3.11 or 3.12) would have been
the better call for a new project: the scientific Python ecosystem
(pandas, pydantic, and others) typically takes weeks to months to
publish pre-compiled wheels for a brand-new Python release, and 3.14
was released only shortly before this project started.

That gap surfaced directly during setup: several pinned dependency
versions in `requirements.txt` had no pre-built wheel for 3.14 yet and
pip fell back to compiling from source, which failed without a C/Rust
toolchain installed. The fix was straightforward — bump each affected
package to the earliest version that shipped 3.14 wheels — but it's a
good illustration of why **pinning to a widely-adopted, stable Python
version is generally preferred for new projects**, rather than
defaulting to whatever is locally installed. A future iteration of
this project would target 3.12 for that reason.

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
- [x] Phase 1 — Environment & version control
- [x] Phase 2 — Extraction (PDF/Word)
- [x] Phase 3 — Transformation & business rules
- [x] Phase 4 — Data quality validation
- [x] Phase 5 — Load to Excel
- [ ] Phase 6 — Tests
- [ ] Phase 7 — Logging
- [ ] Phase 8 — CI/CD (GitHub Actions)

## Operational desktop application

The operator-facing application is `src/gui/app.py`. It uses Tkinter,
which is included with the standard Windows Python installation and has
no licence cost. The application requests the three source files, the
Programa date, and (optionally) the test-train number and MR.

Choose a shared root folder in the application. It automatically
creates this structure:

```
ProgramaETL/
|-- input/       # optional location for documents received each day
|-- output/      # generated Programa and quality report
|-- archive/     # timestamped copy of every successful run
`-- logs/        # rotating technical log
```

Only one generation can run at a time for the shared folder. If a
second user tries to run it while another run is active, the app shows
an informative warning and does not modify any file. Before loading,
the application also asks before replacing an existing Programa for the
same date.

### Build the Windows executable

From the project root, run:

```powershell
.\scripts\build_exe.ps1
```

The script installs PyInstaller in the virtual environment and creates
`dist\ProgramaETL\ProgramaETL.exe`. It normally runs with the user's
own permissions; administrator rights are not required. IT should grant
the team read/write permission to the shared folder and may need to
approve the unsigned executable in endpoint-security software.
