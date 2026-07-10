# ETL Pipeline Diagram

```mermaid
flowchart TD
    A1[PDF: Prevision Flota] --> E1[PDF Extraction Layer<br/>pdfplumber + Camelot fallback]
    A2[Word: Parte de Operaciones] --> E2[Extract DOCX<br/>python-docx]

    E1 --> N1[Normalize Table 1<br/>service + registration]
    E1 --> N2[Normalize Table 2<br/>reserve units]
    E2 --> N3[Normalize segments<br/>forward-fill train number]

    N1 --> S1[Build operational structure model:<br/>service set, combined pairs,<br/>reserve count]
    N2 --> S1

    S1 --> R1{Structural check:<br/>does today's shape match<br/>the Excel template's blocks?}
    R1 -- No --> RPT1[Structural discrepancy report]
    R1 -- Yes --> M[Join datasets<br/>by train number]
    N3 --> M

    M --> V1{Data check:<br/>train exists in both sources?}
    V1 -- No --> RPT2[Data quality report]
    V1 -- Yes --> V2{Data check:<br/>PDF route vs Word route match?}
    V2 -- No --> RPT2
    V2 -- Yes --> L1[Load: update Matrícula<br/>and Tickets in Programa.xlsx]

    N2 --> L2[Load: Reserve section<br/>in Programa.xlsx]

    L1 --> OUT[Updated Programa_DD_MM_YYYY.xlsx]
    L2 --> OUT
    RPT1 --> OUT2[quality_report.csv]
    RPT2 --> OUT2
```

## Design notes

- The pipeline is designed as independent, idempotent steps (Extract →
  Normalize → Derive structure → Validate → Merge → Load), so that a
  later phase can orchestrate it with Airflow/Prefect without
  redesigning the logic.
- **Structural reconciliation happens first**, before any row-level
  data validation. The PDF is the source of truth for the day's
  *shape* — how many service blocks exist, which are combined
  (`301-302`), and how many reserve units there are — because this can
  legitimately change day to day. Skipping this check and jumping
  straight to data validation could silently misalign registrations
  and ticket counts against the wrong block if the day's structure
  shifted.
- Validation is not an optional final step: both the structural check
  and the data check run *before* writing to Excel, so inconsistent
  data never reaches the official document.
- Discrepancies don't halt the whole pipeline (fail-soft): they are
  documented in `quality_report.csv`, and every service without
  detected issues is still loaded.
