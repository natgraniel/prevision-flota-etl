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

**Key parsing note**: in the Word table, the train number is **not
repeated on every segment row** — it only appears on the row where that
service starts. A forward-fill of the train number is required
(propagate downward until the next non-empty value) in order to group
segments correctly.

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
