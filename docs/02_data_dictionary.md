# Data Dictionary

## 1. Source: Fleet Forecast (PDF)

The PDF has 3 relevant blocks (plus 2 out-of-scope blocks: maintenance
and "non-productive received trains").

### Table 1 — Commercial services

| Source column | Field | Type | Format / regex | Example | Notes |
|---|---|---|---|---|---|
| Taller / Estación | `origin_station` | text | free text | `Palenque` | not transcribed to Programa, used only to cross-check table 2 |
| Tren | `ts_code` | text | `TS\d{2}` | `TS30` | internal identifier, **not transcribed** |
| Tren | `registration` | text | `[A-Z]\d{3}` | `L010` | **target: Matrícula column** |
| Servicio | `service` | text | `\d{3}` or `\d{3}-\d{3}` | `101` / `301-302` | **join key** with train number in the Word file |
| Ruta | `route_pdf` | text | `Station-Station` (one or more segments) | `Palenque-Cancún` | used for route cross-validation |
| Observaciones | `notes` | text | free text, may be empty | `Tren de 7 coches` | informational only, not transcribed |

**"Tren" cell parsing rule**: the cell contains two stacked values —
the first is the TS code (irrelevant), the second is the actual
registration number, formatted as one letter + 3 digits. Extract only
the second value.

### Table 2 — Reserve

| Source column | Field | Type | Format | Example | Notes |
|---|---|---|---|---|---|
| Taller/Estación | `station` | text | free text | `Cancún` | **target: Reserve section of Programa** |
| Tren (registration) | `registration` | text | `[A-Z]\d{3}` | `D008` | **target: Matrícula** |
| Observaciones | `reserve_status` | text | contains `RESERVA` or `RESERVA EN ESTACIÓN` | — | filter: only rows where this field contains "RESERVA" |

### Excluded blocks (out of scope)
- "Maintenance" (rows with an estimated maintenance departure date and
  notes such as "Pruebas de señalización", "Retrofit de ruedas", etc.)
- "Non-productive received trains" (e.g. "Tren accidentado")

---

## 2. Source: Operations Report (Word)

A single table with one row per **route segment** (not per full
service).

| Source column | Field | Type | Format | Example | Notes |
|---|---|---|---|---|---|
| Ruta | `segment` | text | `Station – Station` | `Palenque – S.F. Campeche.` | a train with several segments spans several rows; the train number only appears on the first row of the group |
| Número de tren | `train_number` | text | `\d{3}` | `101` | **join key** — blank in subsequent rows of the same train, requires forward-fill |
| Cantidad de boletos vendidos | `tickets_sold` | integer | `\d+` | `85` | **target: Cantidad de boletos vendidos**, per segment |
| % de Ocupación | `occupancy_pct` | decimal | `\d+(\.\d+)?%` | `14.9%` | not transcribed to Programa, but useful for range validation (e.g. tickets_sold=0 with occupancy≠0 would be inconsistent) |

**Key parsing note (corrected after inspecting the real file)**: an
earlier version of this document assumed the train number would be
blank on non-first rows of a segment group, requiring a forward-fill.
That assumption did not hold. In the actual `.docx`, the Train Number
cells for all segments of the same train are **vertically merged** at
the document level — `python-docx` returns the same value for every
row spanned by the merge (verified: identical underlying XML cell
object across those rows). No forward-fill is required; each row's
`train_number` value can be read directly.

---

## 3. Destination: Programa (Excel, sheet `DIARIO`)

| Column (actual header) | Cell | Modified? | Source | Mapping rule |
|---|---|---|---|---|
| Circulación | B | No | — | already exists in the template, used as the lookup key |
| Ruta | C | No | — | already exists, used to **validate** against the Word/PDF route |
| Matrícula | D | **Yes** | PDF table 1 (or table 2 if reserve) | one registration per service block (merged cell); if the service is combined (`301-302`), the same registration applies to both service numbers |
| Cantidad de boletos vendidos | E | **Yes** | Word | one value per segment, in the same order the segments appear for that service |
| Salida prog. | F | No | — | untouched |
| Llegada prog. | G | No | — | untouched |
| Tiempo de recorrido | H | No | — | untouched |
| Tiempo total | I | No | — | untouched (only on the first row of the block, merged cell) |

**Structural particularity**: the `Circulación`, `Matrícula`, and
sometimes `Tiempo total` columns are in **vertically merged cells**
spanning the entire block of segments for a service. When writing with
`openpyxl`, values must be written to the anchor cell of the merged
range (top-left cell), not to the merged child cells.

**Reserve section** (separate block on the same sheet): `station` and
`registration` columns only, no route or ticket data.

## 5. Section markers in the workbook

Sections within sheet `DIARIO` are marked by a single row where columns
`B:I` are merged into one cell containing the section title. Verified
against the real workbook:

| Row | Merged title | Contents |
|---|---|---|
| 5 | `Circulaciones comerciales` | commercial service blocks follow (rows 7–66) |
| 67 | `Pruebas` | rows belonging to signaling/validation test units — **out of scope** |
| 69 | `Reserva` | reserve unit rows follow (rows 70–84) |

This is the reliable way to detect where the Reserve section starts
and ends programmatically — not by row number (which will shift as the
day's structure changes, per requirements rule 7), but by locating the
`B:I`-merged row whose text is `"Reserva"`, and reading rows until the
next `B:I`-merged section title or the end of the sheet.

## 6. Rows with no corresponding source record

Not every row under `Circulaciones comerciales` is guaranteed to match
a record from the PDF or Word datasets. For example, a row under the
`Pruebas` section (e.g. registration `N001` for signaling test unit
`P019/P018`) legitimately has no corresponding entry in either source
document — it isn't a commercial service or a reserve unit.

**Rule**: if a workbook row has no matching record in any of the three
Update Datasets, the Loader must leave that row **completely
untouched** and the Validation Layer should record it as **out of
scope** (a distinct category from a validation failure — it's not
wrong, it simply isn't something this pipeline is responsible for).

---

## 4. Structural metadata (derived, not a source column)

Beyond individual field values, the pipeline also derives **structural
facts** from the PDF that determine the day's row layout in the
Programa, since these can change day to day (see Requirements, rule 7):

| Derived fact | Source | Example | Why it matters |
|---|---|---|---|
| Set of service numbers for the day | PDF table 1, `Servicio` column | `{101, 102, 201, 202, 301, 302, ...}` | defines how many service blocks the Programa should have |
| Combined-service pairs | PDF table 1, `Servicio` column | `{301: 302, 304: 303, ...}` | defines which blocks share a single registration |
| Count of reserve units | PDF table 2, rows with `RESERVA` | e.g. 15 rows today, 18 tomorrow | defines how many rows the Reserve section should have |

These facts are computed once per run and compared against the current
Excel template's block structure as part of the Transform/Validate
stage, before any Load step executes.
