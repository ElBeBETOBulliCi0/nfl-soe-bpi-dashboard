# Implementation Plan: SOE/BPI Dashboard

## Overview

The plan first adds the additive backend extensions (Python, FastAPI, pandas), then builds the React 18 + TypeScript dashboard in `hackathon-unam/dashboard` bottom-up: types and API client, pure `lib/` helpers, the request hook, UI components, and finally the `App.tsx` wiring. The last task updates `backend/RUN_COMMANDS.md`.

Rules for the implementing agent:
- Create and edit files only. Do NOT run any terminal command (no `npm`, `tsc`, `pytest`, `python`, `uvicorn`). Regenerating the precomputed CSVs, pytest, restarting uvicorn and starting the React frontend are run by the user in an external CMD and are listed in task 9.1.
- Add no new npm or Python dependencies. Use only what is in `dashboard/package.json` (React 18, recharts, Tailwind 3).
- All API URLs are relative and start with `api/` (no leading slash). Keep Vite `base: './'`.
- All visible text is Spanish, except the labels Short, Medium and Long.

## Tasks

- [x] 1. Backend additive extensions
  - [x] 1.1 Extend Pydantic schemas in `backend/schemas.py`
    - Add `mean_separation` to `HeatmapCell`, `team` to `PlayerSoe`
    - Add `playDescription`, `result`, `play_result` to `PlaySoe`
    - Add `mean_yards_allowed` and `bpi` to `BpiGroup`, `BpiRushersRow`, `BpiDownDistanceCell` and `BpiDefenseRow`, `mean_yards_allowed` to `BpiSummaryResponse`
    - All new fields default to `None`; no existing field changes
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.8, 15.9_

  - [x] 1.2 Add `playDescription` to the precomputed pipeline and store
    - In `scripts/build_precomputed.py` add `"playDescription"` to `BPI_EXTRA_COLUMNS`
    - In `backend/store.py` add `"playDescription"` to `BPI_EXTRA_COLUMNS` and `_text(...)` in `_prepare_bpi`
    - Add `DataStore.play_context(keys)` returning `playDescription`, `passResult`, `playResult` per `gameId`/`playId` (`None` when missing; works when the column is absent)
    - _Requirements: 15.5, 15.8, 15.9_

  - [x] 1.3 Extend `backend/routers/soe.py`
    - Heatmap: add `mean_separation=("separation", "mean")` to the aggregation
    - Players: add `team=("possessionTeam", "first")`, NaN to `None`
    - Plays: add optional `player: int | None = None`; when set, keep all routes of plays that have a filtered route row for that `nflId`; when absent skip the code path
    - Plays: apply `store.play_context` to the page slice and fill `playDescription`, `result` (passResult), `play_result`
    - _Requirements: 15.1, 15.2, 15.5, 15.6, 15.7, 15.8, 15.9, 15.10_

  - [x] 1.4 Extend `backend/routers/bpi.py`
    - Add `playResult` to the working frame; extend `_agg` and the defense groupby with `mean_yards=("playResult", "mean")` (NaN to `None` through `_none_if_na`)
    - Add helper `_bpi(pressure_rate, mean_yards)`: `None` if either argument is `None`, else `round(pressure_rate * 100 - mean_yards * 5, 2)`
    - Set `mean_yards_allowed` on groups, rusher rows, down-distance cells, defense rows and the summary total (also `None` in the zero-plays early return)
    - Set `bpi=_bpi(pressure_rate, mean_yards_allowed)` on groups, rusher rows, down-distance cells and defense rows, using the unrounded values; `pressure_rate` stays a fraction in [0, 1]
    - Keep `defense_ranking` ordered by `pressure_rate` descending
    - _Requirements: 13.1, 13.3, 15.3, 15.4, 15.8, 15.9, 15.12, 15.13_

  - [ ]* 1.5 Write property test for heatmap `mean_separation`
    - Create `backend/tests/test_dashboard_extensions.py`; seeded `numpy.random.default_rng`, at least 100 iterations, no hypothesis
    - Tag comment `# Feature: soe-bpi-dashboard, Property 13: Heatmap mean_separation`
    - **Property 13: Heatmap mean_separation**
    - **Validates: Requirements 15.1**

  - [ ]* 1.6 Write property test for BPI formula and `mean_yards_allowed`
    - Tag comment `# Feature: soe-bpi-dashboard, Property 14: BPI formula and mean_yards_allowed`
    - On the summary total, groups, rusher rows, down-distance cells and defense rows: `mean_yards_allowed` equals the mean of non-null `playResult` (null when none); `pressure_rate` is in [0, 1] or null; `bpi == round(pressure_rate*100 - mean_yards_allowed*5, 2)` when both are non-null, else null
    - **Property 14: BPI formula and mean_yards_allowed**
    - **Validates: Requirements 15.3, 15.4, 15.9, 15.12, 15.13**

  - [ ]* 1.7 Write property test for team ranking order
    - Tag comment `# Feature: soe-bpi-dashboard, Property 15: Team ranking order`
    - Verified in `backend/routers/bpi.py`: the defense groupby uses `dropna=False`, so plays with a null `defensiveTeam` are kept as a row with `defensiveTeam` null (last among equal rates). Assert `defense_ranking` is ordered by `pressure_rate` descending and that the sum of `n_plays` equals `total_plays` (no plays dropped), including a case with null `defensiveTeam`
    - The design text says null-team plays are dropped; the code does not drop them, so this test follows the code
    - **Property 15: Team ranking order**
    - **Validates: Requirements 13.2, 13.3**

  - [ ]* 1.8 Write property test for the `player` filter on plays
    - Tag comment `# Feature: soe-bpi-dashboard, Property 16: Player filter on plays`
    - **Property 16: Player filter on plays**
    - **Validates: Requirements 15.6, 15.7, 15.8**

  - [ ]* 1.9 Write property test for additive compatibility
    - Tag comment `# Feature: soe-bpi-dashboard, Property 17: Additive compatibility`
    - **Property 17: Additive compatibility**
    - **Validates: Requirements 15.8, 15.9**

  - [ ]* 1.10 Write example unit tests for backend extensions
    - `team` on players; `playDescription`/`result`/`play_result` with and without the `playDescription` column; `player=abc` returns 422; zero-plays summary returns `mean_yards_allowed` null
    - _Requirements: 15.2, 15.5, 15.9, 15.10_

- [x] 2. Checkpoint - Backend complete
  - Confirm tasks 1.1 to 1.4 are implemented and ask the user if questions arise. The user's verification commands are listed in task 9.1.

- [x] 3. Dashboard foundation (config, types, client, pure helpers, hook)
  - [x] 3.1 Configure the Vite proxy
    - In `dashboard/vite.config.ts` add `server.proxy = { '/api': 'http://localhost:8000' }`; keep `base: './'`
    - _Requirements: 1.3, 1.4, 1.5_

  - [x] 3.2 Create `dashboard/src/api/types.ts`
    - Interfaces mirroring `backend/schemas.py` including the new fields (`HeatmapCell`, `PlayerSoe`, `PlaySoe`, `FramePoint`, `PlayDetailResponse`, `RouteRow`, `Bpi*`, `FiltersResponse`, `PlaysResponse`, `PlayersResponse`, `HeatmapResponse`)
    - _Requirements: 1.6, 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x] 3.3 Create `dashboard/src/api/client.ts`
    - `ApiError` with `status` and message containing the code; `buildUrl` omitting undefined values; `request` using `fetch` on `api/...` paths
    - One function per endpoint: `getFilters`, `getHeatmap`, `getPlayers` (`limit=20`), `getPlays` (`player`, `limit=25`, `offset`), `getPlay`, `getBpiSummary`
    - `soeQuery` and `bpiQuery` map filter state to backend names and omit "Todos"; `only_targets` only when on
    - _Requirements: 1.2, 1.6, 1.7, 5.5, 7.1, 8.1, 9.1, 9.4, 11.1, 13.1_

  - [x] 3.4 Create `lib/format.ts`, `lib/filters.ts`, `lib/paging.ts`
    - `fmtYards` (two decimals, "—" for null), `fmtPct` (one decimal with `%`), `fmtBpi` ("—" for null, `+` prefix when positive, two decimals)
    - Filter state types, `toQuery`, `resetFilters` (all "Todos", no selected receiver), `toggle(prev, id)`
    - Paging: next offset `offset + 25` enabled when `offset + 25 < total`, previous `max(0, offset - 25)`
    - _Requirements: 5.5, 5.6, 6.5, 6.6, 8.4, 8.5, 9.3_

  - [x] 3.5 Create `lib/kpi.ts`, `lib/bpi.ts`, `lib/field.ts`
    - `kpi.ts`: `soeKpis` n-weighted (weights only from cells with non-null values, null when weight is 0), `bpiKpis` from the summary
    - `bpi.ts`: `groupRushers` (keys 3, 4, 5, 6+; exclude `num_rushers < 3`; group BPI recomputed as `round(rate*100 - meanYards*5, 2)` with `meanYards` the `n_plays`-weighted mean over members with non-null `mean_yards_allowed`, null when none; never average `bpi` values), `buildDxd` (downs 1 to 4, Corto/Medio/Largo shown as Short/Medium/Long, each cell carries `bpi`, `pressure_rate`, `mean_yards_allowed`, `n_plays`; cells with zero plays or null `bpi` are null and excluded from the scale)
    - `bpi.ts`: `bpiColor(bpi, maxAbs)` returning `{ hue: 'positive' | 'negative' | 'neutral', intensity }` (null for null `bpi`; neutral for 0 or `maxAbs <= 0`; positive blue, negative red; intensity `min(1, |bpi| / maxAbs)`), with `maxAbs` the max `|bpi|` over non-null cells
    - `field.ts`: `pairReceivers` using Coverage players and routes as in the design; use the backend `nearest_defender` for the likely target when present
    - _Requirements: 6.3, 6.4, 7.3, 10.3, 10.4, 11.2, 11.5, 12.1, 12.2, 12.3, 12.5_

  - [x] 3.6 Create `dashboard/src/hooks/useApi.ts`
    - Returns `{ status: 'loading' | 'empty' | 'error' | 'ready', data, error, retry }`
    - Request id stored in a ref; apply only the latest response; `retry` re-runs only that hook; per-section `isEmpty` predicate
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

- [x] 4. Shell and shared components
  - [x] 4.1 Create `StateViews`, `Header`, `Tabs`, `MethodologyPanel` in `dashboard/src/components/`
    - `StateViews`: Loading (`aria-busy="true"`), Empty ("Sin datos para los filtros seleccionados"), Error ("No se pudieron cargar los datos" + "Reintentar")
    - `Header`: project title and subtitle "7,541 jugadas de pase · 122 juegos"
    - `Tabs`: exactly "SOE" and "BPI", `role="tab"` with `aria-selected`
    - `MethodologyPanel`: "¿Cómo se calcula?", collapsed by default, `aria-expanded`, shows SOE, Release_Frame, expected-separation grouping, the BPI formula `BPI = (tasa de presión × 100) − (yardas permitidas promedio × 5)`, the one-line explanation "Positivo: la presión compensa las yardas cedidas; negativo: el blitz salió caro." and distance ranges (Short 1 to 3, Medium 4 to 7, Long 8 or more yards)
    - Show the same explanation as static one-line text on the BPI tab, outside the panel
    - Dark theme and Tailwind 3 utility classes, text contrast at least 7:1
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 14.1, 14.2, 14.3_

  - [x] 4.2 Create `FilterBar` and `KpiCards`
    - `FilterBar`: request `api/filters` once; "Todos" first in each list; SOE controls (coverage, coverage type, position, "Solo objetivos probables"); BPI controls (down, distance bucket, number of rushers); "Limpiar filtros"; Error_State with retry
    - `KpiCards`: four cards per tab, grid of four at 1024 px or more and one or two columns below, per-card Loading_State, "—" for null
    - _Requirements: 2.5, 2.6, 5.1, 5.2, 5.3, 5.4, 5.6, 5.7, 6.1, 6.2, 6.5, 6.6, 6.7_

- [x] 5. SOE tab components
  - [x] 5.1 Create `Heatmap` component
    - Rows are coverages, columns are positions present in the response; HTML, SVG and Tailwind only
    - Diverging colors, tooltip on hover and focus (coverage, position, `mean_soe`, `mean_separation`, `n`), legend with the SOE range in yards, neutral empty cells without tooltip
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 5.2 Create `ReceiverRanking` and `PlayList` components
    - `ReceiverRanking`: rank, name, team ("—" when null), routes, mean separation, mean SOE; click toggles selection (`aria-selected`) and resets `offset` to 0
    - `PlayList`: game id, play id, description, result label (C Completo, I Incompleto, IN Intercepción, S Sack, R Corrida, raw code otherwise) with `play_result` yards, routes, target SOE; selected row `aria-selected="true"`; pagination controls with steps of 25
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 5.3 Create `FieldView` component
    - One SVG with `viewBox="0 0 120 53.3"`, end zones, yard lines every 5 yards, hash marks
    - Receiver markers with names, distinct likely-target marker, dotted Nearest_Defender_Line labeled with separation (two decimals), legend, per-receiver separation, expected separation and SOE, play description and result
    - Empty_State "Selecciona una jugada" when no play is selected; "Jugada no encontrada" on 404
    - _Requirements: 9.6, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_

- [x] 6. BPI tab components
  - [x] 6.1 Create `RushersChart` component
    - recharts bar chart of Pressure_Rate per Rusher_Group with percent y-axis (bars stay on `pressure_rate`) and tooltip (group, rate, `BPI` via `fmtBpi`, `Yardas permitidas` via `fmtYards`, plays, plays with pressure); Empty_State when no group has plays
    - _Requirements: 11.2, 11.3, 11.4, 11.5, 11.6_

  - [x] 6.2 Create `DxdMatrix` component
    - Rows downs 1 to 4, columns Short, Medium, Long; each cell shows `fmtBpi(bpi)` colored with `bpiColor` (diverging, centered on 0); "—" and neutral color for zero plays or null `bpi`
    - Tooltip on hover and focus: down, distance label, BPI, Pressure_Rate, Mean_Yards_Allowed, plays
    - Legend with `-maxAbs`, 0 (marked as center) and `+maxAbs`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x] 6.3 Create `TeamRanking` component
    - Rank, team ("—" when null), plays, Pressure_Rate (percent), Mean_Yards_Allowed ("—" when null), new "BPI" column with `fmtBpi` ("—" when null; positive in the positive hue, negative in the negative hue), ordered as returned (rate descending); Empty_State when the array is empty
    - _Requirements: 13.2, 13.3, 13.4, 13.5_

- [x] 7. Integration and wiring
  - [x] 7.1 Wire everything in `dashboard/src/App.tsx`
    - Tab state with SOE selected on load; each tab keeps its own filters
    - SOE tab: `getHeatmap`, `getPlayers`, `getPlays` (with selected receiver and offset), `getPlay` for the selected play, each through its own `useApi`
    - BPI tab: one `getBpiSummary` with active filters (KPIs, rushers chart, team ranking) and one without `down` and `distance_bucket` but with `num_rushers` (DxD matrix)
    - Ensure the Tailwind entry CSS loads and no new dependency is added
    - _Requirements: 1.1, 3.2, 3.3, 3.5, 5.5, 6.3, 6.4, 8.4, 9.1, 11.1, 12.7, 13.1, 14.5_

- [x] 8. Checkpoint - Dashboard complete
  - Confirm tasks 3 to 7 are implemented and wired in `App.tsx` and ask the user if questions arise. The user's verification commands are listed in task 9.1.

- [x] 9. Final task: run documentation
  - [x] 9.1 Update `backend/RUN_COMMANDS.md` and list the external CMD commands
    - Keep the existing Spanish format: Windows CMD commands, run from `hackathon-unam`, one block per step
    - Add or update these steps, in this order:
      1. Regenerate the precomputed CSVs (adds `playDescription` to `bpi_plays.csv`): `.venv\Scripts\python scripts\build_precomputed.py`
      2. Run pytest: `.venv\Scripts\python -m pytest backend/tests -q`
      3. Restart uvicorn on port 8000: `.venv\Scripts\python -m uvicorn backend.main:app --port 8000`
      4. In a second CMD, start the React frontend: `cd dashboard` then `npm run dev`
    - Steps 1 to 3 run from `C:\Users\thega\OneDrive\Documents\NFLTRIPLET\plantilla-hackathon\hackathon-unam` (`cd /d` there first)
    - Note that without regenerating the CSVs the API still works but `playDescription` is `null`
    - In the final message, repeat the same commands in the same order and state that none were run by the agent
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- Frontend Properties 1 to 12 are implemented as pure functions in `lib/` and `api/` (no frontend test runner exists and no dependency may be added), so they have no test tasks. Backend Properties 13 to 17 have optional pytest tasks.
- UI rendering (theme, contrast, tabs, ARIA, SVG geometry, tooltips, Spanish text) is verified manually by the user.
- The implementing agent runs no terminal commands; every command is listed in task 9.1 for the user's external CMD.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "3.1", "3.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "3.3", "3.4", "3.5", "3.6"] },
    { "id": 2, "tasks": ["1.5", "4.1", "4.2", "5.1", "5.2", "5.3", "6.1", "6.2", "6.3"] },
    { "id": 3, "tasks": ["1.6", "7.1"] },
    { "id": 4, "tasks": ["1.7"] },
    { "id": 5, "tasks": ["1.8"] },
    { "id": 6, "tasks": ["1.9"] },
    { "id": 7, "tasks": ["1.10"] },
    { "id": 8, "tasks": ["9.1"] }
  ]
}
```
