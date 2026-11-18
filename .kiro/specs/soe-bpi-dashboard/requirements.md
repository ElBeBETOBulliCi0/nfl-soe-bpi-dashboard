# Requirements Document

## Introduction

This feature adds a Spanish-language, dark, high-contrast analytics dashboard to the existing React 18 frontend in `hackathon-unam\dashboard`. The dashboard presents two metrics computed from the NFL Big Data Bowl regional tracking data (7,541 pass plays, 122 games): SOE (Separation Over Expected, the distance between a receiver and the nearest defender at the release frame, minus the expected distance for the same coverage and alignment) and BPI (Blocking and Pressure Index, a composite value that combines the pressure rate and the mean yards allowed of plays grouped by the number of pass rushers, down and distance).

The dashboard reads data only from the FastAPI backend defined in the `soe-bpi-backend` spec. The backend receives a small set of additive extensions (new response fields and query parameters) so the dashboard can show team rankings, yards allowed, play descriptions and per-receiver play lists. Existing fields and behaviors of the backend stay unchanged.

Constraints that apply to all requirements: the dashboard adds no new npm dependencies (React 18, recharts and Tailwind 3 are already present), every API call uses a relative URL without a leading slash, the Vite base stays `./`, and the implementation work uses file creation and editing only, with no terminal commands run by the implementing agent.

## Glossary

- **Dashboard**: The React 18 single-page application in `hackathon-unam\dashboard`.
- **Backend**: The FastAPI application in `hackathon-unam\backend` that serves `/api/...` endpoints.
- **API_Client**: The Dashboard module that issues `fetch` calls to the Backend.
- **Vite_Proxy**: The Vite dev server proxy configuration that forwards `/api` requests to `http://localhost:8000`.
- **SOE**: Separation Over Expected, in yards. Positive values mean the receiver had more separation than expected.
- **BPI**: Blocking and Pressure Index, the composite value `bpi = round((pressure_rate * 100) - (mean_yards_allowed * 5), 2)`, computed per group, rusher row, down-distance cell and defense row. A positive BPI means the pressure compensates the yards given up. A negative BPI means the blitz was costly. BPI is null when `mean_yards_allowed` is null or the group has no plays.
- **Pressure_Rate**: The number of plays with a hit, hurry or sack divided by the number of plays in the group, a value in the range 0 to 1. The `pressure_rate` field keeps this meaning and is not changed by BPI.
- **Release_Frame**: The tracking frame at which the pass is thrown.
- **Heatmap**: The grid of mean SOE values with pass coverage on one axis and receiver alignment position on the other axis.
- **Heatmap_Cell**: One Heatmap entry with `mean_soe`, `n` and the new field `mean_separation`.
- **Receiver_Ranking**: The ordered list of receivers by mean SOE, backed by `/api/soe/players`.
- **Play_List**: The list of plays backed by `/api/soe/plays`.
- **Field_View**: The 2D SVG drawing of a football field, 120 yards by 53.3 yards, that shows one play at the Release_Frame.
- **Nearest_Defender_Line**: The dotted line in the Field_View from a receiver to the defender closest to that receiver.
- **Rusher_Group**: A client-side grouping of `num_rushers` into the buckets 3, 4, 5 and 6+.
- **Distance_Bucket**: The backend value `Corto`, `Medio` or `Largo`. The Dashboard displays these as Short, Medium and Long.
- **DxD_Matrix**: The Down by Distance_Bucket matrix of Pressure_Rate.
- **Team_Ranking**: The ordered list of defensive teams by Pressure_Rate, with mean yards allowed and BPI shown per team.
- **BPI_Explanation**: The one-line text "BPI positivo = la presión compensa las yardas permitidas; BPI negativo = el blitz salió caro".
- **Diverging_Scale**: A color scale with two distinct hues for negative and positive values, centered on 0, where intensity increases with the absolute value.
- **Filter_Bar**: The Dashboard controls populated from `/api/filters`.
- **Methodology_Panel**: The collapsible section titled "¿Cómo se calcula?".
- **Mean_Yards_Allowed**: The mean of `playResult` over the plays in a BPI group, exposed by the Backend as `mean_yards_allowed`.
- **Loading_State**: The visual state shown while a request is pending.
- **Empty_State**: The visual state shown when a request succeeds with no data.
- **Error_State**: The visual state shown when a request fails, with a retry control.

## Requirements

### Requirement 1: Project conventions

**User Story:** As a developer, I want the Dashboard to follow the project's build and API conventions, so that it runs in development and behind the hosted deployment path without changes.

#### Acceptance Criteria

1. THE Dashboard SHALL use only the dependencies already declared in `dashboard/package.json`.
2. THE API_Client SHALL issue every request with a relative URL that begins with `api/` and has no leading slash.
3. THE Vite configuration SHALL keep the `base` option set to `./`.
4. THE Vite_Proxy SHALL forward requests whose path begins with `/api` to `http://localhost:8000`.
5. THE Vite_Proxy SHALL NOT alter the `base` option.
6. THE Dashboard SHALL define one function per Backend endpoint in a single API_Client module.
7. WHEN the Backend responds with a non-2xx status, THE API_Client SHALL reject with an error that contains the HTTP status code.

### Requirement 2: Theme, language and header

**User Story:** As an analyst, I want a clear Spanish dark interface with a descriptive header, so that I can read the dashboard in low light and know what data it covers.

#### Acceptance Criteria

1. THE Dashboard SHALL render all visible text in Spanish, except the Distance_Bucket labels Short, Medium and Long.
2. THE Dashboard SHALL render on a dark background with a text-to-background contrast ratio of at least 7:1 for body text.
3. THE Dashboard SHALL display a header containing the project title and the subtitle "7,541 jugadas de pase · 122 juegos".
4. THE Dashboard SHALL style the interface with Tailwind 3 utility classes.
5. WHILE the viewport width is 1024 pixels or more, THE Dashboard SHALL arrange the KPI cards in a single row of four.
6. WHILE the viewport width is below 1024 pixels, THE Dashboard SHALL stack the KPI cards in one or two columns without horizontal page scrolling.

### Requirement 3: SOE and BPI tabs

**User Story:** As an analyst, I want two tabs for SOE and BPI, so that I can switch between the two analyses.

#### Acceptance Criteria

1. THE Dashboard SHALL display exactly two tabs labeled "SOE" and "BPI".
2. WHEN the Dashboard loads, THE Dashboard SHALL select the SOE tab.
3. WHEN the user selects a tab, THE Dashboard SHALL show the content of that tab and hide the content of the other tab.
4. WHEN the user selects a tab, THE Dashboard SHALL mark the selected tab with `aria-selected="true"`.
5. WHEN the user switches tabs, THE Dashboard SHALL keep the filter selections of the other tab unchanged.

### Requirement 4: Methodology panel

**User Story:** As a new user, I want a collapsible explanation of the metrics, so that I understand how SOE and BPI are calculated.

#### Acceptance Criteria

1. THE Dashboard SHALL display the Methodology_Panel titled "¿Cómo se calcula?" below the header.
2. WHEN the Dashboard loads, THE Methodology_Panel SHALL be collapsed.
3. WHEN the user activates the Methodology_Panel title, THE Methodology_Panel SHALL toggle between collapsed and expanded.
4. THE Methodology_Panel SHALL expose its state through the `aria-expanded` attribute on its toggle control.
5. WHILE the Methodology_Panel is expanded, THE Methodology_Panel SHALL display the SOE definition, the Release_Frame definition, the expected-separation grouping, the BPI definition including the formula `bpi = round((pressure_rate * 100) - (mean_yards_allowed * 5), 2)`, the BPI_Explanation, and the Distance_Bucket ranges (Short 1 to 3 yards, Medium 4 to 7 yards, Long 8 yards or more).
6. WHILE the BPI tab is selected, THE Dashboard SHALL display the BPI_Explanation in one line outside the Methodology_Panel.

### Requirement 5: Filters

**User Story:** As an analyst, I want filters populated from the Backend, so that I can narrow the analysis to a coverage, position, down or distance.

#### Acceptance Criteria

1. WHEN the Dashboard loads, THE API_Client SHALL request `api/filters` once.
2. WHEN `api/filters` succeeds, THE Filter_Bar SHALL populate one option list per returned field, with an "Todos" option first in each list.
3. WHILE the SOE tab is selected, THE Filter_Bar SHALL offer the controls pass coverage, coverage type, receiver position and a "Solo objetivos probables" toggle.
4. WHILE the BPI tab is selected, THE Filter_Bar SHALL offer the controls down, distance bucket and number of rushers.
5. WHEN the user changes a filter, THE Dashboard SHALL request the affected endpoints with the selected values as query parameters and omit parameters whose value is "Todos".
6. WHEN the user activates the "Limpiar filtros" control, THE Dashboard SHALL reset all filters of the selected tab to "Todos" and clear any selected receiver.
7. IF `api/filters` fails, THEN THE Filter_Bar SHALL display the Error_State with a retry control.

### Requirement 6: KPI cards

**User Story:** As an analyst, I want four KPI cards per tab, so that I can read the headline numbers for the current filters.

#### Acceptance Criteria

1. WHILE the SOE tab is selected, THE Dashboard SHALL display four KPI cards: number of routes analyzed, mean SOE, mean separation and number of receivers ranked.
2. WHILE the BPI tab is selected, THE Dashboard SHALL display four KPI cards: number of plays, overall Pressure_Rate, mean yards allowed and number of plays with pressure.
3. THE Dashboard SHALL compute the SOE KPI values from the Heatmap_Cell `n`, `mean_soe` and `mean_separation` values, weighting each cell by `n`, and from the length of the Receiver_Ranking response.
4. THE Dashboard SHALL compute the BPI KPI values from `/api/bpi/summary` for the current filters.
5. THE Dashboard SHALL format SOE and separation values in yards with two decimals and Pressure_Rate as a percentage with one decimal.
6. IF a KPI value is null, THEN THE Dashboard SHALL display "—" in that card.
7. WHILE a KPI source request is pending, THE Dashboard SHALL display the Loading_State inside the affected card.

### Requirement 7: SOE heatmap

**User Story:** As an analyst, I want a coverage by position heatmap, so that I can see where receivers get more or less separation than expected.

#### Acceptance Criteria

1. WHEN the SOE tab is selected or an SOE filter changes, THE API_Client SHALL request `api/soe/heatmap` with the active SOE filters.
2. THE Dashboard SHALL render the Heatmap with one row per pass coverage and one column per receiver position present in the response, using only HTML, SVG and Tailwind elements.
3. THE Dashboard SHALL color each Heatmap_Cell on a diverging scale where negative `mean_soe` and positive `mean_soe` use two distinct hues and the color intensity increases with the absolute value.
4. WHEN the user hovers or focuses a Heatmap_Cell, THE Dashboard SHALL display a tooltip with the coverage, the position, `mean_soe`, `mean_separation` and `n`.
5. THE Dashboard SHALL display a color legend for the Heatmap that states the SOE range in yards.
6. IF a coverage and position pair has no Heatmap_Cell, THEN THE Dashboard SHALL render that grid position as an empty neutral cell without a tooltip.

### Requirement 8: Receiver ranking

**User Story:** As an analyst, I want a receiver ranking, so that I can find the receivers who create the most separation and inspect their plays.

#### Acceptance Criteria

1. WHEN the SOE tab is selected or an SOE filter changes, THE API_Client SHALL request `api/soe/players` with the active SOE filters and `limit=20`.
2. THE Dashboard SHALL display the Receiver_Ranking with rank, receiver name, team, number of routes, mean separation and mean SOE.
3. THE Dashboard SHALL order the Receiver_Ranking by `mean_soe` descending, as returned by the Backend.
4. WHEN the user clicks a receiver row, THE Dashboard SHALL mark that row as selected and request `api/soe/plays` with the `nflId` of that receiver as the player filter.
5. WHEN the user clicks the selected receiver row again, THE Dashboard SHALL clear the selection and request `api/soe/plays` without the player filter.
6. WHERE the receiver `team` field is null, THE Dashboard SHALL display "—" in the team column.

### Requirement 9: Play list

**User Story:** As an analyst, I want a list of plays with their descriptions and results, so that I can pick a play to inspect on the field.

#### Acceptance Criteria

1. WHEN the SOE tab is selected or an SOE filter or receiver selection changes, THE API_Client SHALL request `api/soe/plays` with the active SOE filters, the selected receiver if any, and `limit=25`.
2. THE Dashboard SHALL display each play with game id, play id, play description, play result, number of routes and target SOE.
3. WHEN the response `total` exceeds the number of plays shown, THE Dashboard SHALL display pagination controls that request the next or previous page with `offset` changes of 25.
4. WHEN the user selects a play, THE API_Client SHALL request `api/soe/play/{game_id}/{play_id}` and THE Dashboard SHALL render that play in the Field_View.
5. THE Dashboard SHALL mark the selected play row with `aria-selected="true"`.
6. IF the play detail request returns 404, THEN THE Dashboard SHALL display the Empty_State in the Field_View with the text "Jugada no encontrada".

### Requirement 10: Field view

**User Story:** As an analyst, I want a 2D field drawing of the selected play, so that I can see receivers, defenders and separation at the release frame.

#### Acceptance Criteria

1. THE Field_View SHALL render as one SVG element with a coordinate system of 120 units by 53.3 units, covering the field and both end zones.
2. THE Field_View SHALL draw yard lines every 5 yards, the two end zones and the hash marks.
3. THE Field_View SHALL draw each receiver of the selected play as a marker positioned at its release-frame coordinates, labeled with the receiver name.
4. WHERE the Backend returns the coordinates of a nearest defender for a receiver, THE Field_View SHALL draw a Nearest_Defender_Line as a dotted line from the receiver to that defender and label the line with the separation in yards.
5. THE Field_View SHALL draw the likely target receiver with a marker style distinct from the other receivers.
6. THE Field_View SHALL display a legend that identifies the receiver marker, the likely target marker, the defender marker and the Nearest_Defender_Line.
7. THE Field_View SHALL display for the selected play the play description, the play result, and for each receiver the separation, expected separation and SOE.
8. WHILE no play is selected, THE Field_View SHALL display the Empty_State with the text "Selecciona una jugada".

### Requirement 11: BPI by rushers

**User Story:** As an analyst, I want pressure rate by number of rushers, so that I can see how blitzing affects pressure.

#### Acceptance Criteria

1. WHEN the BPI tab is selected or a BPI filter changes, THE API_Client SHALL request `api/bpi/summary` with the active BPI filters.
2. THE Dashboard SHALL aggregate the `groups` of the response by Rusher_Group, where `num_rushers` of 3 maps to "3", 4 to "4", 5 to "5", and 6 or more to "6+", summing `n_plays` and `n_pressure` before computing each Pressure_Rate.
3. THE Dashboard SHALL render the Pressure_Rate per Rusher_Group as a recharts bar chart with the y-axis in percent.
4. WHEN the user hovers a bar, THE Dashboard SHALL display a tooltip with the Rusher_Group, Pressure_Rate, BPI, number of plays and number of plays with pressure.
5. IF a group has `num_rushers` below 3, THEN THE Dashboard SHALL exclude that group from the chart and keep it in the KPI totals.
6. IF no Rusher_Group has plays, THEN THE Dashboard SHALL display the Empty_State in place of the chart.

### Requirement 12: Down by distance matrix

**User Story:** As an analyst, I want a down by distance matrix, so that I can see in which situations pressure happens most.

#### Acceptance Criteria

1. THE Dashboard SHALL render the DxD_Matrix with rows for downs 1 to 4 and columns for Short, Medium and Long.
2. THE Dashboard SHALL fill each DxD_Matrix cell with the BPI, the Pressure_Rate and the number of plays for that down and Distance_Bucket, computed from `/api/bpi/summary`.
3. THE Dashboard SHALL color each DxD_Matrix cell with a Diverging_Scale centered on 0 using the BPI of that cell.
4. WHEN the user hovers or focuses a DxD_Matrix cell, THE Dashboard SHALL display a tooltip with the down, the distance label, BPI, Pressure_Rate, Mean_Yards_Allowed and number of plays.
5. IF a DxD_Matrix cell has zero plays or a null BPI, THEN THE Dashboard SHALL display "—" in that cell, render the cell with a neutral color and exclude the cell from the Diverging_Scale range.
6. THE Dashboard SHALL display a color legend for the DxD_Matrix that states the BPI range and marks 0 as the center.
7. THE Dashboard SHALL request the data for the DxD_Matrix without the down and distance filters, so that the matrix always shows every down and distance combination, and SHALL apply the number of rushers filter.

### Requirement 13: Team defense ranking

**User Story:** As an analyst, I want a team defense ranking, so that I can compare defenses by pressure and yards allowed.

#### Acceptance Criteria

1. WHEN the BPI tab is selected or a BPI filter changes, THE API_Client SHALL request the team-level data exposed by the Backend for the Team_Ranking with the active BPI filters.
2. THE Dashboard SHALL display the Team_Ranking with rank, team, number of plays, Pressure_Rate, Mean_Yards_Allowed and BPI.
3. THE Dashboard SHALL order the Team_Ranking by Pressure_Rate descending.
4. IF Mean_Yards_Allowed or BPI is null for a team, THEN THE Dashboard SHALL display "—" in the corresponding column.
5. IF the team-level data is empty, THEN THE Dashboard SHALL display the Empty_State in the Team_Ranking.

### Requirement 14: Loading, empty and error states

**User Story:** As an analyst, I want consistent loading, empty and error states, so that I always know whether data is pending, absent or failed.

#### Acceptance Criteria

1. WHILE a request for a Dashboard section is pending, THE Dashboard SHALL display the Loading_State in that section with `aria-busy="true"`.
2. WHEN a request succeeds with no rows, THE Dashboard SHALL display the Empty_State with the text "Sin datos para los filtros seleccionados" in that section.
3. IF a request fails, THEN THE Dashboard SHALL display the Error_State in that section with the text "No se pudieron cargar los datos" and a "Reintentar" control.
4. WHEN the user activates the "Reintentar" control, THE Dashboard SHALL repeat the failed request for that section only.
5. WHEN a request fails in one section, THE Dashboard SHALL keep the other sections interactive.
6. WHEN the filters change while a request is pending, THE Dashboard SHALL discard the response of the superseded request.

### Requirement 15: Additive backend extensions

**User Story:** As a frontend developer, I want additive Backend extensions, so that the Dashboard receives the fields it needs without breaking existing consumers.

#### Acceptance Criteria

1. THE Backend SHALL add `mean_separation` to each Heatmap_Cell as the mean of `separation` over the rows in that cell.
2. THE Backend SHALL add `team` to each `PlayerSoe` entry as the team abbreviation of the receiver, or null when unavailable.
3. THE Backend SHALL add `mean_yards_allowed` to each BPI group and to the BPI summary total as the mean of `playResult` over the matching plays, or null when no matching play has a `playResult`.
4. THE Backend SHALL add a `bpi` field to each BPI group, each rusher row, each down-distance cell and each defense row of the Team_Ranking, computed as `round((pressure_rate * 100) - (mean_yards_allowed * 5), 2)`, with the exact row and endpoint shape specified in the design document.
5. THE Backend SHALL add `playDescription` and `result` to each `PlaySoe` entry of `/api/soe/plays`.
6. WHEN `/api/soe/plays` receives the optional query parameter `player`, THE Backend SHALL return only plays that include a route row for that `nflId`.
7. WHEN the optional `player` parameter is absent, THE Backend SHALL return the same plays as before the extension.
8. THE Backend SHALL keep every field, parameter and status code that existed before these extensions unchanged.
9. THE Backend SHALL return `null` for each new numeric field that has no source rows.
10. IF the `player` parameter is not an integer, THEN THE Backend SHALL respond with status 422.
11. THE Backend design document extension SHALL specify the endpoint path, query parameters, response models and precomputed columns for the Team_Ranking data.
12. IF `mean_yards_allowed` is null or the group has no plays, THEN THE Backend SHALL return `bpi` as null.
13. THE Backend SHALL keep `pressure_rate` in the range 0 to 1 and keep `mean_yards_allowed` as a separate field, so that existing tests are unaffected.
14. THE `scripts/build_precomputed.py` script SHALL add the `playDescription` column to the precomputed play data, and the user SHALL rerun the script to regenerate the precomputed files.

### Requirement 16: Run documentation and delivery

**User Story:** As a developer, I want run instructions kept current, so that I can start the backend and the Dashboard after the changes.

#### Acceptance Criteria

1. THE implementation SHALL update `backend/RUN_COMMANDS.md` with the commands to run the Preprocessor, the Backend, the Dashboard dev server and the tests.
2. THE implementation SHALL create and edit files only, SHALL NOT run terminal commands and SHALL add no new Python or npm dependencies.
3. WHEN the implementation is complete, THE implementing agent SHALL list the external CMD commands, one per step, for the user to run.
4. THE external CMD commands SHALL be listed in this order: regenerate the precomputed files, run pytest, restart uvicorn on port 8000, start the React frontend.
5. THE implementation SHALL update `backend/RUN_COMMANDS.md` with the same commands in the same order.
