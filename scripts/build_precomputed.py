"""Preprocessor: reads data/ and writes backend/precomputed/*.csv.

Usage (from the project root):
    .venv\\Scripts\\python scripts\\build_precomputed.py

Outputs:
    soe_routes.csv           one row per Route_Player per play (SOE metrics)
    play_release_frames.csv  all players and the ball at the release frame of each
                             usable play (>= 3 Pass Route and >= 4 Coverage) and of
                             every play present in soe_routes.csv
    bpi_plays.csv            one row per play with at least one Pass Rush player
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from backend.config import DATA_DIR, PRECOMPUTED_DIR  # noqa: E402
from backend.metrics import (  # noqa: E402
    assign_expected_separation,
    build_bpi_plays,
    compute_separation,
    is_likely_target,
    select_release_frames,
)

REQUIRED_FILES = ["games.csv", "players.csv", "plays.csv", "pffScoutingData.csv"]
TRACKING_USECOLS = [
    "gameId", "playId", "nflId", "frameId", "team", "playDirection", "x", "y", "event",
]

MIN_ROUTES = 3
MIN_COVERAGE = 4
FIELD_LENGTH = 120.0
FIELD_WIDTH = 53.3

# Req 3.4 columns first, then optional context columns used by the API filters
# (week, offense team, defense team). The API tolerates their absence.
ROUTE_COLUMNS = [
    "gameId", "playId", "nflId", "displayName", "pff_positionLinedUp",
    "pff_passCoverage", "pff_passCoverageType", "separation",
    "expected_separation", "soe", "is_likely_target",
    "week", "possessionTeam", "defensiveTeam",
]
PLAY_CONTEXT_COLUMNS = [
    "playDescription", "pff_passCoverage", "pff_passCoverageType",
    "week", "possessionTeam", "defensiveTeam",
]
# One row per player (and the ball) at the release frame. `club` is the tracking
# `team` abbreviation ("football" for the ball); `team` is kept for compatibility.
RELEASE_COLUMNS = [
    "gameId", "playId", "frameId", "nflId", "displayName", "club", "team",
    "x", "y", "is_ball", "pff_role", "pff_positionLinedUp",
]
BPI_EXTRA_COLUMNS = [
    "defensiveTeam", "pff_passCoverage", "pff_passCoverageType",
    "playResult", "passResult", "playDescription",
]
KEYS = ["gameId", "playId"]


def check_inputs(data_dir: Path) -> list[Path]:
    """Return the required input paths that are missing."""
    missing = [data_dir / name for name in REQUIRED_FILES if not (data_dir / name).is_file()]
    tracking_dir = data_dir / "tracking"
    if not tracking_dir.is_dir() or not any(tracking_dir.glob("tracking_*.csv")):
        missing.append(tracking_dir / "tracking_*.csv")
    return missing


def _empty_routes() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in ROUTE_COLUMNS})


def _empty_releases() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in RELEASE_COLUMNS})


def process_tracking_file(
    path: Path, pff: pd.DataFrame, plays: pd.DataFrame, players: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (release_rows, route_rows_without_expected) for one tracking file.

    The file is read once. Only the release-frame rows are kept.
    """
    tracking = pd.read_csv(path, usecols=TRACKING_USECOLS)
    release = select_release_frames(tracking)
    if release.empty:
        return _empty_releases(), _empty_routes()

    frames = tracking.merge(release, on=["gameId", "playId", "frameId"], how="inner")
    del tracking

    # Normalize so the offense always moves to the right.
    left = frames["playDirection"].eq("left")
    frames["x"] = np.where(left, FIELD_LENGTH - frames["x"], frames["x"])
    frames["y"] = np.where(left, FIELD_WIDTH - frames["y"], frames["y"])
    frames["is_ball"] = frames["nflId"].isna()

    roles = pff[KEYS + ["nflId", "pff_role", "pff_positionLinedUp"]].drop_duplicates(
        KEYS + ["nflId"]
    )
    frames = frames.merge(roles, on=KEYS + ["nflId"], how="left")
    names = players[["nflId", "displayName"]].drop_duplicates("nflId")
    frames = frames.merge(names, on="nflId", how="left")
    frames["displayName"] = frames["displayName"].where(~frames["is_ball"], "football")
    frames["club"] = frames["team"]

    is_route = frames["pff_role"].eq("Pass Route") & ~frames["is_ball"]
    is_cover = frames["pff_role"].eq("Coverage") & ~frames["is_ball"]
    counts = (
        pd.DataFrame({"gameId": frames["gameId"], "playId": frames["playId"],
                      "n_route": is_route, "n_cover": is_cover})
        .groupby(KEYS, as_index=False).sum()
    )
    usable = counts.loc[
        (counts["n_route"] >= MIN_ROUTES) & (counts["n_cover"] >= MIN_COVERAGE), KEYS
    ]

    # Routes (Req 3): any play with at least one route player and one tracked coverage player.
    play_info = plays.reindex(columns=KEYS + PLAY_CONTEXT_COLUMNS).drop_duplicates(KEYS)
    route_parts: list[pd.DataFrame] = []
    route_play_keys: list[tuple[int, int]] = []
    for (game_id, play_id), grp in frames.loc[~frames["is_ball"]].groupby(KEYS):
        r = grp.loc[grp["pff_role"] == "Pass Route"]
        c = grp.loc[grp["pff_role"] == "Coverage", ["x", "y"]].dropna()
        r = r.dropna(subset=["x", "y"])
        if r.empty or c.empty:
            continue
        sep = compute_separation(r[["x", "y"]].to_numpy(), c.to_numpy())
        part = r[["gameId", "playId", "nflId", "pff_positionLinedUp"]].copy()
        part["separation"] = sep
        route_parts.append(part)
        route_play_keys.append((game_id, play_id))

    if route_parts:
        routes = pd.concat(route_parts, ignore_index=True)
        routes = routes.merge(names, on="nflId", how="left")
        routes = routes.merge(play_info, on=KEYS, how="left")
        routes["is_likely_target"] = [
            is_likely_target(n, d) for n, d in zip(routes["displayName"], routes["playDescription"])
        ]
        routes["nflId"] = routes["nflId"].astype("int64")
        routes = routes[
            [c for c in ROUTE_COLUMNS if c not in ("expected_separation", "soe")]
        ]
    else:
        routes = _empty_routes().drop(columns=["expected_separation", "soe"])

    # Release frames (Req 2.4): usable plays plus every play that has route rows.
    keep = pd.concat(
        [usable, pd.DataFrame(route_play_keys, columns=KEYS).astype("int64")],
        ignore_index=True,
    ).drop_duplicates()
    out = frames.merge(keep, on=KEYS, how="inner")[RELEASE_COLUMNS].copy()
    out["nflId"] = out["nflId"].astype("Int64")
    out = out.sort_values(KEYS + ["is_ball", "nflId"], kind="stable").reset_index(drop=True)
    return out, routes


def build_outputs(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (routes, releases, bpi) for the whole dataset."""
    players = pd.read_csv(data_dir / "players.csv", usecols=["nflId", "displayName"])
    plays = pd.read_csv(
        data_dir / "plays.csv",
        usecols=["gameId", "playId", "playDescription", "down", "yardsToGo",
                 "possessionTeam", "defensiveTeam", "passResult", "playResult",
                 "pff_passCoverage", "pff_passCoverageType"],
    )
    games = pd.read_csv(data_dir / "games.csv", usecols=["gameId", "week"])
    plays = plays.merge(games.drop_duplicates("gameId"), on="gameId", how="left")
    pff = pd.read_csv(data_dir / "pffScoutingData.csv")

    route_parts: list[pd.DataFrame] = []
    release_parts: list[pd.DataFrame] = []
    for path in sorted((data_dir / "tracking").glob("tracking_*.csv")):
        release_rows, route_rows = process_tracking_file(path, pff, plays, players)
        release_parts.append(release_rows)
        route_parts.append(route_rows)
        print(f"processed {path.name}: {len(route_rows)} routes", flush=True)

    routes = pd.concat(route_parts, ignore_index=True) if route_parts else _empty_routes()
    routes = assign_expected_separation(routes)
    routes = routes[ROUTE_COLUMNS]
    releases = pd.concat(release_parts, ignore_index=True) if release_parts else _empty_releases()
    bpi = build_bpi_plays(pff, plays)
    bpi = add_bpi_context(bpi, plays)
    return routes, releases, bpi


def add_bpi_context(bpi: pd.DataFrame, plays: pd.DataFrame) -> pd.DataFrame:
    """Append defensiveTeam, coverage and result columns to the BPI rows (kept after the
    Req 6.5 columns)."""
    context = plays.reindex(columns=KEYS + BPI_EXTRA_COLUMNS).drop_duplicates(KEYS)
    out = bpi.merge(context, on=KEYS, how="left")
    return out[list(bpi.columns) + BPI_EXTRA_COLUMNS]


def write_outputs(out_dir: Path, routes: pd.DataFrame, releases: pd.DataFrame,
                  bpi: pd.DataFrame) -> None:
    """Create ``out_dir`` and write the three CSV files with header and no index."""
    out_dir.mkdir(parents=True, exist_ok=True)
    routes.to_csv(out_dir / "soe_routes.csv", index=False)
    releases.to_csv(out_dir / "play_release_frames.csv", index=False)
    bpi.to_csv(out_dir / "bpi_plays.csv", index=False)


def main(data_dir: Path = DATA_DIR, out_dir: Path = PRECOMPUTED_DIR) -> int:
    missing = check_inputs(Path(data_dir))
    if missing:
        for p in missing:
            print(f"Missing input: {p}")
        return 1
    routes, releases, bpi = build_outputs(Path(data_dir))
    write_outputs(Path(out_dir), routes, releases, bpi)
    print(f"Wrote {len(routes)} routes, {len(releases)} release-frame rows, "
          f"{len(bpi)} BPI plays to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
