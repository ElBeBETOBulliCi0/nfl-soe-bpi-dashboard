# Implementation Plan: soe-bpi-backend

## Overview

Python 3.12 backend in three parts: pure metric functions in `backend/metrics.py`, an offline preprocessor `scripts/build_precomputed.py`, and a FastAPI app that serves the precomputed CSVs from memory. Tests live in `backend/tests/` (so `python -m pytest backend/tests -q` finds them) and use seeded numpy generators with at least 100 iterations. No hypothesis and no new dependencies.

The terminal is blocked for the coding agent. Every task only creates or edits files. Nothing may be executed, including the build script and the tests. Task 12 lists the commands the user runs in an external CMD.

## Tasks

- [x] 1. Repository hygiene and package skeleton
  - [x] 1.1 Update `.gitignore` and verify `.env.example`
    - Add the lines `data/tracking/` and `.env` to `.gitignore` if absent, and keep `.env.example` tracked (not ignored)
    - Add `CORS_ORIGINS=http://localhost:5173,http://localhost:3000` to `.env.example` if absent
    - _Requirements: 7.1, 7.2, 15.4_
  - [x] 1.2 Create package skeleton
    - Create `backend/__init__.py`, `backend/routers/__init__.py`, `backend/config.py` (paths `DATA_DIR`, `PRECOMPUTED_DIR`, and CORS origins parsed from `CORS_ORIGINS` with the default of the two local origins), `backend/precomputed/.gitkeep`
    - Read existing `backend/main.py` first and keep its `cargar_env()` block and `GET /health` behavior
    - _Requirements: 1.2, 15.4_

- [x] 2. Pure metric functions
  - [x] 2.1 Implement `select_release_frames` and `compute_separation` in `backend/metrics.py`
    - `pass_forward` wins over `autoevent_passforward`, plays with neither are absent, one row per play, minimum `frameId` when repeated
    - `compute_separation` uses numpy broadcasting and returns an empty array when there are no coverage rows
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3_
  - [x] 2.2 Implement `assign_expected_separation` in `backend/metrics.py`
    - Primary key `(pff_passCoverage, pff_positionLinedUp)`, fallback to `(pff_passCoverageType, pff_positionLinedUp)` when the primary count is below `FALLBACK_MIN_SAMPLES = 15`
    - Use `groupby(..., dropna=False)`, then `soe = separation - expected_separation`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 2.3 Implement `is_likely_target`, `distance_bucket` and `build_bpi_plays` in `backend/metrics.py`
    - Surname is the last whitespace token of `display_name`, case-insensitive substring match, empty or missing description gives False
    - `distance_bucket`: `Corto` for 1..3, `Medio` for 4..7, `Largo` for 8 or more, `None` for missing, NaN or below 1 (use `<= 3` and `<= 7` after the `< 1` check)
    - `build_bpi_plays`: one row per play with at least one `Pass Rush` player, columns `gameId, playId, num_rushers, is_pressure, down, yardsToGo, distance_bucket`, missing `pff_hit/hurry/sack` count as not 1
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5_
  - [x]* 2.4 Write property tests for release frames and separation
    - Create `backend/tests/test_metrics_properties.py` with `N_ITER = 100`, `numpy.random.default_rng(seed)`, and assertion messages that include the seed and iteration
    - **Property 1: Release frame selection**
    - **Property 2: Separation equals brute-force minimum distance** (explicit loop reference, empty coverage case)
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 16.2, 16.3**
  - [x]* 2.5 Write property tests for expected separation and SOE
    - Append to `backend/tests/test_metrics_properties.py`
    - **Property 3: Expected separation is the group mean and SOE is zero-mean** (groups of 15 or more, tolerance 1e-9)
    - **Property 4: Small groups fall back to coverage type**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 16.4**
  - [x]* 2.6 Write property tests for target flag, BPI rows and distance bucket
    - Append to `backend/tests/test_metrics_properties.py`
    - **Property 5: Likely target matches surname case-insensitively** (include empty and None descriptions)
    - **Property 6: BPI play rows match rusher data**
    - **Property 7: Distance bucket boundaries** (always include 1, 3, 4, 7, 8, plus 0, negative and NaN)
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 16.5**

- [x] 3. Checkpoint - Review metrics code and tests
  - Re-read `backend/metrics.py` and `backend/tests/test_metrics_properties.py` for consistency. Tests are not run by the agent, ask the user if questions arise.

- [x] 4. Preprocessor script
  - [x] 4.1 Implement `scripts/build_precomputed.py`
    - Add the project root to `sys.path` and import from `backend.metrics`
    - `check_inputs` returns missing paths for `games.csv`, `players.csv`, `plays.csv`, `pffScoutingData.csv` and for a `tracking/` directory with no `tracking_*.csv`. `main` prints each one and returns 1 without writing
    - `process_tracking_file` reads each tracking file once with `usecols=[gameId, playId, nflId, frameId, x, y, event]`, drops rows with null `nflId`, builds release rows and route rows, and the caller deletes the raw frame before the next file
    - `build_outputs` concatenates, calls `assign_expected_separation` over all plays, builds `bpi_plays` with `build_bpi_plays`
    - `write_outputs` creates the output directory and writes `soe_routes.csv`, `play_release_frames.csv`, `bpi_plays.csv` with header and `index=False`
    - End with `sys.exit(main())` under `if __name__ == "__main__"`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.3, 2.4, 3.3, 3.4_
  - [x]* 4.2 Write unit tests for the preprocessor
    - Create `backend/tests/test_preprocessor.py` using tiny synthetic CSVs in `tmp_path`, loading the script with `importlib` from `scripts/build_precomputed.py`
    - Missing input returns non-zero and writes nothing, output directory is created, Route_File column list matches Requirement 3.4, one small end-to-end run produces the three files
    - **Property 8: Output CSV round trip** (generate frames with numpy, write with `write_outputs`, read back with `DataStore.load`, compare header, row count and values with NaN equal to NaN). Add this test after task 5.1 exists.
    - **Validates: Requirements 1.2, 1.3, 1.5, 3.4, 15.5**

- [x] 5. Data store and schemas
  - [x] 5.1 Implement `backend/store.py`
    - `DataStore.load(directory)` reads the three CSVs once, catches `FileNotFoundError`, `EmptyDataError` and `ParserError`, substitutes empty frames with the expected columns, sets `data_loaded`, normalizes boolean columns from `True`/`False` strings and reads ids as `int64`
    - `filter_routes(only_targets, coverage, coverage_type, position)`, `filter_bpi(down, distance_bucket, num_rushers)` (AND of equality masks), `filter_values()` with sorted distinct non-null values
    - Add a `clean(df)` helper that converts NaN to `None`
    - _Requirements: 9.1, 9.2, 10.2, 10.3, 14.3, 15.2, 15.3, 15.5_
  - [x] 5.2 Implement `backend/schemas.py`
    - Pydantic models exactly as in the design: `HealthResponse`, `FiltersResponse`, `HeatmapCell`, `HeatmapResponse`, `PlayerSoe`, `PlayersResponse`, `PlaySoe`, `PlaysResponse`, `RouteRow`, `PlayDetailResponse`, `BpiGroup`, `BpiSummaryResponse`, with `float | None` for numeric fields
    - _Requirements: 15.1, 15.5_

- [x] 6. API routers and app wiring
  - [x] 6.1 Implement `backend/routers/health.py` and `backend/routers/filters.py`
    - One shared handler for `/health` and `/api/health` returning `status="ok"` and `data_loaded`
    - `GET /api/filters` returns `FiltersResponse` from `store.filter_values()`
    - Routers read the store from `request.app.state.store`
    - _Requirements: 8.1, 8.2, 8.3, 9.1, 9.2, 15.1_
  - [x] 6.2 Implement `backend/routers/soe.py`
    - `GET /api/soe/heatmap`, `/api/soe/players` (`min_n` ge 1 default 1, `limit` 1..500 default 50, sort `mean_soe` descending then `nflId` ascending), `/api/soe/plays` (`limit`, `offset` ge 0, sort by `gameId`, `playId`, `total` before slicing, `target_soe` null when no likely target), `/api/soe/play/{game_id}/{play_id}` (int path params, 404 with `detail="Play not found"`, `frameId` from releases or null)
    - Use `Query(..., ge=, le=)` so out-of-range values return 422
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 12.1, 12.2, 12.3, 12.4, 12.5, 13.1, 13.2, 13.3, 15.1_
  - [x] 6.3 Implement `backend/routers/bpi.py`
    - `GET /api/bpi/summary` with `down`, `distance_bucket`, `num_rushers` filters, groups by `(num_rushers, distance_bucket)` with `dropna=False`, `pressure_rate` null when there are no plays
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 15.1_
  - [x] 6.4 Update `backend/main.py`
    - Keep the `cargar_env()` block and the exposed `app`. Add `lifespan` that sets `app.state.store = DataStore.load(PRECOMPUTED_DIR)` once, `create_app(precomputed_dir=None)`, `CORSMiddleware` with `allow_methods=["GET"]` and origins from `config.py`, register all routers, keep `GET /health` at the root
    - `app = create_app()`
    - _Requirements: 8.1, 8.2, 15.3, 15.4_

- [x] 7. Checkpoint - Review API code
  - Re-read `backend/main.py`, `backend/store.py`, `backend/routers/*.py` for import and route consistency. Tests are not run by the agent, ask the user if questions arise.

- [x] 8. Test fixtures
  - [x] 8.1 Create `backend/tests/__init__.py` and `backend/tests/conftest.py`
    - Synthetic builders for routes, releases and BPI DataFrames (seeded numpy), a helper that writes them to `tmp_path`, and a `make_client(directory)` factory that returns `TestClient(create_app(directory))` used as a context manager so the lifespan runs
    - A fixture for a missing directory and for a directory with only empty files
    - Never read `data/tracking/`
    - _Requirements: 16.1, 16.8_

- [x] 9. API tests
  - [x]* 9.1 Write endpoint example tests in `backend/tests/test_api.py`
    - `/health` and `/api/health` identical bodies, `data_loaded` false for a missing or empty directory
    - Empty_Result with status 200 for every endpoint when files are missing
    - 422 for bad `limit`, `offset`, `min_n` and non-integer ids, 404 for an unknown play
    - CORS default origins and `CORS_ORIGINS` override through `monkeypatch.setenv`
    - **Property 15: Missing data yields Empty_Result everywhere** (loop over seeded subsets of missing files, at least 100 iterations)
    - **Property 16: Invalid query parameters are rejected** (seeded values inside and outside the ranges)
    - **Validates: Requirements 8.1, 8.2, 8.3, 9.2, 10.4, 11.4, 11.6, 12.4, 12.5, 13.2, 13.3, 14.4, 15.2, 15.4, 16.6, 16.7**
  - [x]* 9.2 Write store and aggregation property tests in `backend/tests/test_store_properties.py`
    - Each test uses seeded numpy frames written to `tmp_path`, with pandas as the reference aggregation
    - **Property 9: Filter values are sorted and distinct**
    - **Property 10: Heatmap cells match filtered aggregation**
    - **Property 11: Player ranking is sorted, filtered and bounded**
    - **Property 12: Play list aggregates and pagination**
    - **Property 13: BPI summary rates and filters**
    - **Property 14: NaN serializes as null** (inject NaN at random positions, check the response text is valid JSON with null)
    - **Validates: Requirements 9.1, 10.1, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 11.5, 11.6, 12.1, 12.2, 12.3, 12.5, 14.1, 14.2, 14.3, 14.4, 15.5**
  - [x]* 9.3 Write repository hygiene tests in `backend/tests/test_repo_hygiene.py`
    - `.gitignore` contains `data/tracking/` and `.env`, `.env.example` exists and is not ignored
    - _Requirements: 7.1, 7.2_

- [x] 10. Checkpoint - Review test suite
  - Re-read the test files against the design properties list. Tests are not run by the agent, ask the user if questions arise.

- [x] 11. Final wiring check
  - [x] 11.1 Review imports and file layout
    - Confirm every module imported by `main.py`, the routers, the script and the tests exists, that no new dependency was added to `requirements.txt`, and that `hypothesis` is not imported anywhere
    - _Requirements: 15.1, 16.1, 16.2_

- [x] 12. Commands for the user's external CMD
  - [x] 12.1 Create `backend/RUN_COMMANDS.md` listing the exact commands
    - The agent only writes this file. The user runs the commands from the project root (`hackathon-unam`) in a separate CMD, in this order:
      1. `.venv\Scripts\python scripts\build_precomputed.py` (builds `backend/precomputed/*.csv`, needs `data/` in place)
      2. `.venv\Scripts\python -m pytest backend/tests -q`
      3. `.venv\Scripts\python -m uvicorn backend.main:app --port 8000`
    - Note that the build exits with code 1 and prints missing paths when raw inputs are absent, and that the API still starts without precomputed files and reports `data_loaded: false`
    - _Requirements: 1.1, 1.3, 15.2, 16.1_

## Notes

- Tasks marked with `*` are optional test tasks. The agent must not run any command, including pytest and the build script.
- Tests are placed in `backend/tests/` to match the requested pytest command. The design lists `tests/`, and this plan overrides it.
- Property tests are plain pytest loops with `numpy.random.default_rng(seed)`, at least 100 iterations, with a tag comment `# Feature: soe-bpi-backend, Property N: <title>`.
- Task 4.2 includes Property 8, which depends on `DataStore` from task 5.1, so it is scheduled in a later wave.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "5.2"] },
    { "id": 2, "tasks": ["2.2", "5.1"] },
    { "id": 3, "tasks": ["2.3", "8.1"] },
    { "id": 4, "tasks": ["2.4", "4.1", "6.1", "6.2", "6.3"] },
    { "id": 5, "tasks": ["2.5", "6.4", "9.3"] },
    { "id": 6, "tasks": ["2.6", "4.2", "9.1"] },
    { "id": 7, "tasks": ["9.2"] },
    { "id": 8, "tasks": ["11.1"] },
    { "id": 9, "tasks": ["12.1"] }
  ]
}
```
