// Response types mirroring backend/schemas.py (including additive dashboard fields).

export interface HealthResponse {
  status: string;
  data_loaded: boolean;
}

export interface FiltersResponse {
  pff_passCoverage: string[];
  pff_passCoverageType: string[];
  pff_positionLinedUp: string[];
  distance_bucket: string[];
  down: number[];
  week: number[];
  team: string[];
}

export interface HeatmapCell {
  pff_passCoverage: string | null;
  pff_positionLinedUp: string | null;
  mean_soe: number | null;
  mean_separation: number | null;
  n: number;
}

export interface HeatmapResponse {
  cells: HeatmapCell[];
}

export interface PlayerSoe {
  nflId: number;
  displayName: string | null;
  team: string | null;
  mean_soe: number | null;
  mean_separation: number | null;
  n: number;
}

export interface PlayersResponse {
  players: PlayerSoe[];
}

export interface PlaySoe {
  gameId: number;
  playId: number;
  n_routes: number;
  mean_soe: number | null;
  max_soe: number | null;
  target_soe: number | null;
  playDescription: string | null;
  result: string | null;
  play_result: number | null;
}

export interface PlaysResponse {
  total: number;
  plays: PlaySoe[];
}

export interface RouteRow {
  gameId: number;
  playId: number;
  nflId: number;
  displayName: string | null;
  pff_positionLinedUp: string | null;
  pff_passCoverage: string | null;
  pff_passCoverageType: string | null;
  separation: number | null;
  expected_separation: number | null;
  soe: number | null;
  is_likely_target: boolean;
}

export interface FramePoint {
  nflId: number | null;
  displayName: string | null;
  club: string | null;
  x: number | null;
  y: number | null;
  is_ball: boolean;
  pff_role: string | null;
  pff_positionLinedUp: string | null;
  distance: number | null;
}

export interface PlayDetailResponse {
  gameId: number;
  playId: number;
  frameId: number | null;
  routes: RouteRow[];
  players: FramePoint[];
  ball: FramePoint | null;
  receptor: FramePoint | null;
  nearest_defender: FramePoint | null;
}

export interface BpiGroup {
  num_rushers: number;
  distance_bucket: string | null;
  n_plays: number;
  n_pressure: number;
  pressure_rate: number | null;
  mean_yards_allowed: number | null;
  bpi: number | null;
}

export interface BpiRushersRow {
  num_rushers: number;
  n_plays: number;
  n_pressure: number;
  pressure_rate: number | null;
  mean_yards_allowed: number | null;
  bpi: number | null;
}

export interface BpiDownDistanceCell {
  down: number | null;
  distance_bucket: string | null;
  n_plays: number;
  n_pressure: number;
  pressure_rate: number | null;
  mean_yards_allowed: number | null;
  bpi: number | null;
}

// bpi = round(pressure_rate * 100 - mean_yards_allowed * 5, 2)
export interface BpiDefenseRow {
  defensiveTeam: string | null;
  n_plays: number;
  n_pressure: number;
  pressure_rate: number | null;
  mean_rushers: number | null;
  mean_yards_allowed: number | null;
  bpi: number | null;
}

export interface BpiSummaryResponse {
  total_plays: number;
  pressure_rate: number | null;
  mean_yards_allowed: number | null;
  groups: BpiGroup[];
  by_rushers: BpiRushersRow[];
  down_distance: BpiDownDistanceCell[];
  defense_ranking: BpiDefenseRow[];
}
