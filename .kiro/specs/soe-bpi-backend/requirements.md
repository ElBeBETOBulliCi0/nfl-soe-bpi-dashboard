# Requirements Document

## Introduction

This feature delivers the backend for two NFL Big Data Bowl metrics: Separation Over Expected (SOE) for pass routes and Blocking Pressure Index (BPI) for pass rush. The backend has three parts: an offline preprocessor script, a FastAPI service that serves precomputed data, and a pytest suite. The scope excludes any frontend.

The preprocessor reads the raw CSV files in `data/` and writes precomputed CSV files into `backend/precomputed/`. The API reads only the precomputed files. The stack is Python 3.12, FastAPI 0.115.14, Pydantic 2.11.7, pandas 2.2.3, numpy 2.1.3, pytest 8.3.5 and httpx 0.28.1. Property-based tests use pytest with seeded numpy randomized inputs, because the hypothesis library is not available.

## Glossary

- **Preprocessor**: The script `scripts/build_precomputed.py` that reads `data/` and writes `backend/precomputed/`.
- **API**: The FastAPI application in `backend/` that serves precomputed data over HTTP.
- **Precomputed_Dir**: The directory `backend/precomputed/`.
- **Data_Dir**: The directory `data/` holding `games.csv`, `players.csv`, `plays.csv`, `pffScoutingData.csv` and `tracking/tracking_*.csv`.
- **SOE**: Separation Over Expected. For a route player on a play, the observed separation minus the expected separation.
- **BPI**: Blocking Pressure Index, the pass-rush pressure summary computed per play.
- **Release_Frame**: The tracking frame whose event is `pass_forward`, or `autoevent_passforward` when no `pass_forward` frame exists for the play.
- **Route_Player**: A player whose `pff_role` is `Pass Route`.
- **Coverage_Player**: A player whose `pff_role` is `Coverage`.
- **Separation**: The minimum Euclidean distance, in yards, from one Route_Player to any Coverage_Player at the Release_Frame.
- **Expected_Separation**: The mean Separation across all samples sharing a `(pff_passCoverage, pff_positionLinedUp)` key.
- **Fallback_Key**: The `pff_passCoverageType` value used in place of `pff_passCoverage` when a key has fewer than 15 samples.
- **Likely_Target**: A Route_Player whose surname appears in the `playDescription` of the play.
- **Rusher**: A player whose `pff_role` is `Pass Rush`.
- **Pressure**: A play on which at least one Rusher has `pff_hit`, `pff_hurry` or `pff_sack` equal to 1.
- **Distance_Bucket**: The label `Corto` for yards to go 1 to 3, `Medio` for 4 to 7, and `Largo` for 8 or more.
- **Route_File**: `backend/precomputed/soe_routes.csv`.
- **Release_File**: `backend/precomputed/play_release_frames.csv`.
- **BPI_File**: `backend/precomputed/bpi_plays.csv`.
- **Empty_Result**: A response with HTTP status 200 and empty collections or null values in the declared schema.

## Requirements

### Requirement 1: Precomputed data build

**User Story:** As a data analyst, I want a preprocessor that builds the precomputed CSV files from raw data, so that the API serves results without recomputing tracking data.

#### Acceptance Criteria

1. WHEN the Preprocessor is run, THE Preprocessor SHALL read the CSV files from Data_Dir and write Route_File, Release_File and BPI_File into Precomputed_Dir.
2. WHERE Precomputed_Dir does not exist, THE Preprocessor SHALL create Precomputed_Dir before writing.
3. IF a required input file is missing from Data_Dir, THEN THE Preprocessor SHALL print the missing file path and exit with a non-zero status code.
4. WHEN a tracking file is processed, THE Preprocessor SHALL read the file in a single pass and release the file data before the next tracking file is read.
5. THE Preprocessor SHALL write each output file with a header row and one row per record.

### Requirement 2: Release frame detection

**User Story:** As a data analyst, I want the release frame identified for each play, so that separation is measured at the moment of the throw.

#### Acceptance Criteria

1. WHEN a play has a tracking frame with event `pass_forward`, THE Preprocessor SHALL use that frame as the Release_Frame.
2. IF a play has no `pass_forward` frame and has an `autoevent_passforward` frame, THEN THE Preprocessor SHALL use the `autoevent_passforward` frame as the Release_Frame.
3. IF a play has neither a `pass_forward` frame nor an `autoevent_passforward` frame, THEN THE Preprocessor SHALL omit the play from Release_File and Route_File.
4. THE Preprocessor SHALL write one row per play to Release_File with the columns `gameId`, `playId` and `frameId`, where `frameId` is the Release_Frame.

### Requirement 3: Route separation

**User Story:** As a data analyst, I want per-route separation computed at the release frame, so that route quality can be compared across plays.

#### Acceptance Criteria

1. WHEN a play has a Release_Frame, THE Preprocessor SHALL compute Separation for each Route_Player on the play.
2. THE Preprocessor SHALL compute Separation as the minimum Euclidean distance from the Route_Player position (`x`, `y`) to the position of each Coverage_Player at the Release_Frame.
3. IF a play has no Coverage_Player with a tracked position at the Release_Frame, THEN THE Preprocessor SHALL omit the Route_Players of that play from Route_File.
4. THE Preprocessor SHALL write one row per Route_Player per play to Route_File with the columns `gameId`, `playId`, `nflId`, `displayName`, `pff_positionLinedUp`, `pff_passCoverage`, `pff_passCoverageType`, `separation`, `expected_separation`, `soe` and `is_likely_target`.

### Requirement 4: Expected separation and SOE

**User Story:** As a data analyst, I want expected separation computed by coverage and alignment, so that SOE reflects difficulty of the situation.

#### Acceptance Criteria

1. THE Preprocessor SHALL compute Expected_Separation as the mean Separation of all Route_File samples that share the same `(pff_passCoverage, pff_positionLinedUp)` key.
2. IF a `(pff_passCoverage, pff_positionLinedUp)` key has fewer than 15 samples, THEN THE Preprocessor SHALL compute Expected_Separation as the mean Separation of all samples that share the same `(pff_passCoverageType, pff_positionLinedUp)` key.
3. THE Preprocessor SHALL compute `soe` as `separation` minus `expected_separation` for each Route_File row.
4. FOR ALL Route_File rows sharing one key group that has 15 or more samples, THE mean of `soe` SHALL equal 0 within a tolerance of 1e-9.

### Requirement 5: Likely target flag

**User Story:** As a data analyst, I want likely targets flagged, so that SOE can be filtered to the intended receiver.

#### Acceptance Criteria

1. WHEN the surname of a Route_Player appears in the `playDescription` of the play, THE Preprocessor SHALL set `is_likely_target` to true for that Route_Player.
2. WHEN the surname of a Route_Player does not appear in the `playDescription` of the play, THE Preprocessor SHALL set `is_likely_target` to false for that Route_Player.
3. THE Preprocessor SHALL derive the surname as the last whitespace-separated token of `displayName` and compare the surname to `playDescription` without regard to letter case.
4. IF `playDescription` is empty or missing, THEN THE Preprocessor SHALL set `is_likely_target` to false for every Route_Player of the play.

### Requirement 6: BPI pressure summary

**User Story:** As a data analyst, I want a per-play pass-rush pressure summary, so that BPI can be explored by situation.

#### Acceptance Criteria

1. THE Preprocessor SHALL compute `num_rushers` for each play as the count of Rushers on the play.
2. THE Preprocessor SHALL set `is_pressure` to true for a play when at least one Rusher on the play has `pff_hit`, `pff_hurry` or `pff_sack` equal to 1, and to false otherwise.
3. THE Preprocessor SHALL assign Distance_Bucket from `yardsToGo` using `Corto` for 1 to 3, `Medio` for 4 to 7 and `Largo` for 8 or more.
4. IF `yardsToGo` is missing or less than 1, THEN THE Preprocessor SHALL leave the Distance_Bucket empty for that play.
5. THE Preprocessor SHALL write one row per play with at least one Rusher to BPI_File with the columns `gameId`, `playId`, `num_rushers`, `is_pressure`, `down`, `yardsToGo` and `distance_bucket`.

### Requirement 7: Repository hygiene

**User Story:** As a developer, I want repository hygiene for large and secret files, so that raw tracking data and credentials are not committed.

#### Acceptance Criteria

1. THE repository `.gitignore` SHALL list `data/tracking/` and `.env`.
2. THE repository SHALL keep `.env.example` tracked in version control.

### Requirement 8: Health endpoints

**User Story:** As a frontend developer, I want a health endpoint, so that I can check that the API is running.

#### Acceptance Criteria

1. WHEN a GET request is received at `/health`, THE API SHALL respond with status 200 and a JSON body containing `status` equal to `ok`.
2. WHEN a GET request is received at `/api/health`, THE API SHALL respond with status 200 and the same JSON body as `/health`.
3. WHEN a health request is received and any precomputed file is missing, THE API SHALL respond with status 200 and a boolean `data_loaded` equal to false.

### Requirement 9: Filters endpoint

**User Story:** As a frontend developer, I want filter options from the API, so that I can populate selectors.

#### Acceptance Criteria

1. WHEN a GET request is received at `/api/filters`, THE API SHALL respond with the sorted distinct values of `pff_passCoverage`, `pff_passCoverageType`, `pff_positionLinedUp`, `distance_bucket` and `down` found in the precomputed files.
2. IF the precomputed files are missing or empty, THEN THE API SHALL return an Empty_Result with empty lists for every filter field.

### Requirement 10: SOE heatmap endpoint

**User Story:** As an analyst, I want an SOE heatmap, so that I can compare average SOE across coverages and alignments.

#### Acceptance Criteria

1. WHEN a GET request is received at `/api/soe/heatmap`, THE API SHALL return one cell per `(pff_passCoverage, pff_positionLinedUp)` pair containing `pff_passCoverage`, `pff_positionLinedUp`, `mean_soe` and `n`.
2. WHERE the query parameter `only_targets` equals true, THE API SHALL include only rows whose `is_likely_target` is true.
3. WHERE the query parameters `coverage`, `coverage_type` or `position` are supplied, THE API SHALL include only rows matching every supplied value.
4. IF no rows match the filters, THEN THE API SHALL return an Empty_Result with an empty `cells` list.

### Requirement 11: SOE players endpoint

**User Story:** As an analyst, I want a player SOE ranking, so that I can identify the receivers who separate best.

#### Acceptance Criteria

1. WHEN a GET request is received at `/api/soe/players`, THE API SHALL return one entry per `nflId` containing `nflId`, `displayName`, `mean_soe`, `mean_separation` and `n`, sorted by `mean_soe` descending.
2. WHERE the query parameter `min_n` is supplied, THE API SHALL exclude players with fewer than `min_n` routes.
3. WHERE the query parameter `limit` is supplied, THE API SHALL return at most `limit` entries, with `limit` between 1 and 500 and a default of 50.
4. IF `limit` or `min_n` is outside its valid range, THEN THE API SHALL respond with status 422.
5. WHERE the query parameters `only_targets`, `coverage`, `coverage_type` or `position` are supplied, THE API SHALL apply them as defined in Requirement 10.
6. IF no rows match the filters, THEN THE API SHALL return an Empty_Result with an empty `players` list.

### Requirement 12: SOE plays endpoint

**User Story:** As an analyst, I want a paginated list of plays with SOE, so that I can browse individual plays.

#### Acceptance Criteria

1. WHEN a GET request is received at `/api/soe/plays`, THE API SHALL return one entry per play containing `gameId`, `playId`, `n_routes`, `mean_soe`, `max_soe` and `target_soe`, where `target_soe` is null when no Likely_Target exists on the play.
2. WHERE the query parameters `limit` and `offset` are supplied, THE API SHALL return the requested page, with `limit` between 1 and 500 with a default of 50 and `offset` of 0 or greater.
3. THE API SHALL include the total play count `total` in the response.
4. IF `limit` or `offset` is outside its valid range, THEN THE API SHALL respond with status 422.
5. IF no plays match the filters, THEN THE API SHALL return an Empty_Result with `total` equal to 0 and an empty `plays` list.

### Requirement 13: SOE play detail endpoint

**User Story:** As an analyst, I want the detail of a single play, so that I can inspect each route's separation.

#### Acceptance Criteria

1. WHEN a GET request is received at `/api/soe/play/{game_id}/{play_id}` for an existing play, THE API SHALL return the Release_File `frameId` and one entry per Route_Player with the Route_File columns.
2. IF the play does not exist in Route_File, THEN THE API SHALL respond with status 404 and a JSON error body containing `detail`.
3. IF `game_id` or `play_id` is not an integer, THEN THE API SHALL respond with status 422.

### Requirement 14: BPI summary endpoint

**User Story:** As an analyst, I want a BPI summary, so that I can see pressure rates by rusher count and distance.

#### Acceptance Criteria

1. WHEN a GET request is received at `/api/bpi/summary`, THE API SHALL return `total_plays`, `pressure_rate` and a list of groups keyed by `num_rushers` and `distance_bucket`, each with `n_plays`, `n_pressure` and `pressure_rate`.
2. THE API SHALL compute each `pressure_rate` as `n_pressure` divided by `n_plays`, expressed as a fraction between 0 and 1.
3. WHERE the query parameters `down`, `distance_bucket` or `num_rushers` are supplied, THE API SHALL include only plays matching every supplied value.
4. IF no plays match the filters, THEN THE API SHALL return an Empty_Result with `total_plays` equal to 0, `pressure_rate` equal to null and an empty `groups` list.

### Requirement 15: API contract and resilience

**User Story:** As a frontend developer, I want typed, stable API responses, so that the frontend can rely on the contract.

#### Acceptance Criteria

1. THE API SHALL declare a Pydantic response model for every endpoint listed in Requirements 8 to 14.
2. WHEN a precomputed file is missing or empty, THE API SHALL respond with status 200 and an Empty_Result instead of status 500.
3. THE API SHALL load the precomputed files once at startup and serve requests from memory.
4. THE API SHALL add CORS headers that allow cross-origin GET requests from the origins listed in a configurable environment variable, with a default that allows the local development origins `http://localhost:5173` and `http://localhost:3000`.
5. IF a numeric value in a precomputed file is NaN, THEN THE API SHALL serialize the value as null.

### Requirement 16: Automated tests

**User Story:** As a developer, I want automated tests, so that metric logic and endpoints stay correct.

#### Acceptance Criteria

1. THE test suite SHALL run with pytest 8.3.5 and use httpx 0.28.1 through the FastAPI test client for endpoint tests.
2. THE test suite SHALL implement property-based tests using numpy random generators with fixed seeds, and run each property for at least 100 generated inputs.
3. THE test suite SHALL verify that Separation equals the brute-force minimum distance for randomly generated route and coverage positions.
4. THE test suite SHALL verify that the mean `soe` is 0 within each key group of 15 or more samples.
5. THE test suite SHALL verify the Distance_Bucket boundaries at 1, 3, 4, 7 and 8 yards to go.
6. THE test suite SHALL verify that every endpoint responds with status 200 and an Empty_Result when the precomputed files are missing.
7. THE test suite SHALL verify that `/health` and `/api/health` return identical bodies.
8. THE test suite SHALL use small synthetic fixture data and not read `data/tracking/`.
