"""Pydantic response models for the SOE and BPI API.

Numeric fields that can hold NaN in the precomputed files are declared as
``float | None`` so the API serializes NaN as null.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    data_loaded: bool


class FiltersResponse(BaseModel):
    pff_passCoverage: list[str] = Field(default_factory=list)
    pff_passCoverageType: list[str] = Field(default_factory=list)
    pff_positionLinedUp: list[str] = Field(default_factory=list)
    distance_bucket: list[str] = Field(default_factory=list)
    down: list[int] = Field(default_factory=list)
    week: list[int] = Field(default_factory=list)
    team: list[str] = Field(default_factory=list)


class HeatmapCell(BaseModel):
    pff_passCoverage: str | None = None
    pff_positionLinedUp: str | None = None
    mean_soe: float | None = None
    n: int
    mean_separation: float | None = None


class HeatmapResponse(BaseModel):
    cells: list[HeatmapCell] = Field(default_factory=list)


class PlayerSoe(BaseModel):
    nflId: int
    displayName: str | None = None
    mean_soe: float | None = None
    mean_separation: float | None = None
    n: int
    team: str | None = None  # receiver's possessionTeam


class PlayersResponse(BaseModel):
    players: list[PlayerSoe] = Field(default_factory=list)


class PlaySoe(BaseModel):
    gameId: int
    playId: int
    n_routes: int
    mean_soe: float | None = None
    max_soe: float | None = None
    target_soe: float | None = None
    playDescription: str | None = None
    result: str | None = None  # passResult code: C, I, IN, S, R, IR, or None
    play_result: float | None = None  # playResult in yards


class PlaysResponse(BaseModel):
    total: int = 0
    plays: list[PlaySoe] = Field(default_factory=list)


class RouteRow(BaseModel):
    gameId: int
    playId: int
    nflId: int
    displayName: str | None = None
    pff_positionLinedUp: str | None = None
    pff_passCoverage: str | None = None
    pff_passCoverageType: str | None = None
    separation: float | None = None
    expected_separation: float | None = None
    soe: float | None = None
    is_likely_target: bool


class FramePoint(BaseModel):
    """One player (or the ball) at the release frame."""

    nflId: int | None = None
    displayName: str | None = None
    club: str | None = None
    x: float | None = None
    y: float | None = None
    is_ball: bool = False
    pff_role: str | None = None
    pff_positionLinedUp: str | None = None
    distance: float | None = None  # only set on nearest_defender (yards to the receptor)


class PlayDetailResponse(BaseModel):
    gameId: int
    playId: int
    frameId: int | None = None
    routes: list[RouteRow] = Field(default_factory=list)
    players: list[FramePoint] = Field(default_factory=list)  # all non-ball (x, y)
    ball: FramePoint | None = None
    receptor: FramePoint | None = None
    nearest_defender: FramePoint | None = None


class BpiGroup(BaseModel):
    num_rushers: int
    distance_bucket: str | None = None
    n_plays: int
    n_pressure: int
    pressure_rate: float | None = None
    mean_yards_allowed: float | None = None
    bpi: float | None = None  # round(pressure_rate*100 - mean_yards_allowed*5, 2)


class BpiRushersRow(BaseModel):
    num_rushers: int
    n_plays: int
    n_pressure: int
    pressure_rate: float | None = None
    mean_yards_allowed: float | None = None
    bpi: float | None = None


class BpiDownDistanceCell(BaseModel):
    down: int | None = None
    distance_bucket: str | None = None
    n_plays: int
    n_pressure: int
    pressure_rate: float | None = None
    mean_yards_allowed: float | None = None
    bpi: float | None = None


class BpiDefenseRow(BaseModel):
    defensiveTeam: str | None = None
    n_plays: int
    n_pressure: int
    pressure_rate: float | None = None
    mean_rushers: float | None = None
    mean_yards_allowed: float | None = None
    bpi: float | None = None


class BpiSummaryResponse(BaseModel):
    total_plays: int = 0
    pressure_rate: float | None = None
    mean_yards_allowed: float | None = None
    groups: list[BpiGroup] = Field(default_factory=list)
    by_rushers: list[BpiRushersRow] = Field(default_factory=list)
    down_distance: list[BpiDownDistanceCell] = Field(default_factory=list)
    defense_ranking: list[BpiDefenseRow] = Field(default_factory=list)
