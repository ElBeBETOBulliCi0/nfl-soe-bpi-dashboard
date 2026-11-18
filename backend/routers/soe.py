"""SOE endpoints: heatmap, player ranking, play list and play detail."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request

from backend.schemas import (
    FramePoint,
    HeatmapCell,
    HeatmapResponse,
    PlayDetailResponse,
    PlayerSoe,
    PlaysResponse,
    PlaySoe,
    PlayersResponse,
    RouteRow,
)
from backend.store import DataStore, clean_records

router = APIRouter(prefix="/api/soe", tags=["soe"])

ROUTE_COLUMNS = [
    "gameId", "playId", "nflId", "displayName", "pff_positionLinedUp",
    "pff_passCoverage", "pff_passCoverageType", "separation",
    "expected_separation", "soe", "is_likely_target",
]


def _store(request: Request) -> DataStore:
    store = getattr(request.app.state, "store", None)
    if store is None:
        store = DataStore()
        request.app.state.store = store
    return store


@router.get("/heatmap", response_model=HeatmapResponse)
def heatmap(
    request: Request,
    only_targets: bool | None = None,
    coverage: str | None = None,
    coverage_type: str | None = None,
    position: str | None = None,
    team: str | None = None,
    week: int | None = None,
) -> HeatmapResponse:
    # team = defensive team of the play
    df = _store(request).filter_routes(
        only_targets, coverage, coverage_type, position,
        team=team, week=week, team_side="defense",
    )
    if df.empty:
        return HeatmapResponse(cells=[])
    grouped = (
        df.groupby(["pff_passCoverage", "pff_positionLinedUp"], dropna=False)
        .agg(
            mean_soe=("soe", "mean"),
            n=("soe", "size"),
            mean_separation=("separation", "mean"),
        )
        .reset_index()
    )
    return HeatmapResponse(cells=[HeatmapCell(**r) for r in clean_records(grouped)])


@router.get("/players", response_model=PlayersResponse)
def players(
    request: Request,
    only_targets: bool | None = None,
    coverage: str | None = None,
    coverage_type: str | None = None,
    position: str | None = None,
    team: str | None = None,
    week: int | None = None,
    search: str | None = None,
    name: str | None = None,
    min_n: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
) -> PlayersResponse:
    # team = receiver's team (possessionTeam); search/name = substring of displayName
    df = _store(request).filter_routes(
        only_targets, coverage, coverage_type, position,
        team=team, week=week, team_side="offense", search=search or name,
    )
    if df.empty:
        return PlayersResponse(players=[])
    grouped = (
        df.groupby("nflId")
        .agg(
            displayName=("displayName", "first"),
            mean_soe=("soe", "mean"),
            mean_separation=("separation", "mean"),
            n=("soe", "size"),
            team=("possessionTeam", "first"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["n"] >= min_n]
    grouped = grouped.sort_values(
        ["mean_soe", "nflId"], ascending=[False, True], na_position="last"
    ).head(limit)
    return PlayersResponse(players=[PlayerSoe(**r) for r in clean_records(grouped)])


@router.get("/plays", response_model=PlaysResponse)
def plays(
    request: Request,
    only_targets: bool | None = None,
    coverage: str | None = None,
    coverage_type: str | None = None,
    position: str | None = None,
    team: str | None = None,
    week: int | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    player: int | None = None,
) -> PlaysResponse:
    # require_release: every listed play has a frame in play_release_frames.
    store = _store(request)
    df = store.filter_routes(
        only_targets, coverage, coverage_type, position, require_release=True,
        team=team, week=week, team_side="defense",
    )
    if player is not None:
        # Keep every route of the plays where the player has a filtered route row.
        play_keys = df.loc[df["nflId"] == player, ["gameId", "playId"]].drop_duplicates()
        df = df.merge(play_keys, on=["gameId", "playId"], how="inner")
    if df.empty:
        return PlaysResponse(total=0, plays=[])
    keys = ["gameId", "playId"]
    grouped = df.groupby(keys).agg(
        n_routes=("soe", "size"),
        mean_soe=("soe", "mean"),
        max_soe=("soe", "max"),
    )
    targets = df[df["is_likely_target"]]
    if targets.empty:
        grouped["target_soe"] = float("nan")
    else:
        grouped["target_soe"] = targets.groupby(keys)["soe"].mean()
    grouped = grouped.sort_index().reset_index()
    total = int(len(grouped))
    page = grouped.iloc[offset : offset + limit]
    ctx_rows = clean_records(store.play_context(page[keys]))
    rows = []
    for r, c in zip(clean_records(page), ctx_rows):
        rows.append(
            PlaySoe(
                **r,
                playDescription=c["playDescription"],
                result=c["passResult"],
                play_result=c["playResult"],
            )
        )
    return PlaysResponse(total=total, plays=rows)


@router.get("/play/{game_id}/{play_id}", response_model=PlayDetailResponse)
def play_detail(request: Request, game_id: int, play_id: int) -> PlayDetailResponse:
    store = _store(request)
    routes = store.routes
    rows = routes[(routes["gameId"] == game_id) & (routes["playId"] == play_id)]
    if rows.empty:
        raise HTTPException(status_code=404, detail="Play not found")
    rows = rows.sort_values("nflId")[ROUTE_COLUMNS]

    # Positions at the release frame: every player, the ball, the receptor
    # (likely target) and the nearest Coverage player to the receptor.
    frames = store.play_frames(game_id, play_id)
    ball_rows = frames[frames["is_ball"]]
    player_rows = frames[~frames["is_ball"] & frames["nflId"].notna()].sort_values(
        "nflId", kind="stable"
    )
    players = [FramePoint(**r) for r in clean_records(player_rows)]
    ball = FramePoint(**clean_records(ball_rows.head(1))[0]) if not ball_rows.empty else None

    receptor = None
    nearest = None
    targets = rows[rows["is_likely_target"]]
    if not targets.empty:
        target_id = int(targets["nflId"].iloc[0])
        rec = player_rows[player_rows["nflId"] == target_id].dropna(subset=["x", "y"])
        if not rec.empty:
            rec_row = rec.iloc[0]
            receptor = FramePoint(**clean_records(rec.head(1))[0])
            cover = player_rows[player_rows["pff_role"] == "Coverage"].dropna(subset=["x", "y"])
            if not cover.empty:
                dist = np.hypot(cover["x"] - rec_row["x"], cover["y"] - rec_row["y"])
                best = cover.loc[[dist.idxmin()]].copy()
                best["distance"] = float(dist.min())
                nearest = FramePoint(**clean_records(best)[0])

    return PlayDetailResponse(
        gameId=game_id,
        playId=play_id,
        frameId=store.release_frame(game_id, play_id),
        routes=[RouteRow(**r) for r in clean_records(rows)],
        players=players,
        ball=ball,
        receptor=receptor,
        nearest_defender=nearest,
    )
