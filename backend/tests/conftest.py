"""Shared synthetic fixtures for the soe-bpi-backend tests.

Everything here is built from seeded numpy generators. Nothing reads
``data/tracking/``. ``create_app`` is imported lazily so this module loads even
when the app wiring changes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

N_ITER = 100

ROUTES_FILE = "soe_routes.csv"
RELEASES_FILE = "play_release_frames.csv"
BPI_FILE = "bpi_plays.csv"

ROUTES_COLUMNS = [
    "gameId", "playId", "nflId", "displayName", "pff_positionLinedUp",
    "pff_passCoverage", "pff_passCoverageType", "separation",
    "expected_separation", "soe", "is_likely_target",
]
RELEASES_COLUMNS = ["gameId", "playId", "frameId"]
BPI_COLUMNS = [
    "gameId", "playId", "num_rushers", "is_pressure", "down", "yardsToGo",
    "distance_bucket",
]

COVERAGES = ["Cover-1", "Cover-2", "Cover-3", "Quarters"]
COVERAGE_TYPES = {
    "Cover-1": "Man", "Cover-2": "Zone", "Cover-3": "Zone", "Quarters": "Zone",
}
POSITIONS = ["WR", "TE", "HB", "SLWR", "SRWR"]


def bucket_for(yards_to_go) -> str | None:
    """Local reference for the yardsToGo buckets: <=3 Corto, <=7 Medio, >7 Largo."""
    if yards_to_go is None or pd.isna(yards_to_go) or yards_to_go < 1:
        return None
    if yards_to_go <= 3:
        return "Corto"
    if yards_to_go <= 7:
        return "Medio"
    return "Largo"


def make_routes(rng: np.random.Generator, n_plays: int = 20, max_routes: int = 5,
                nan_rate: float = 0.0) -> pd.DataFrame:
    """Synthetic soe_routes table. ``nan_rate`` injects NaN into numeric columns."""
    rows = []
    for i in range(n_plays):
        game_id = 2021090900 + int(rng.integers(0, 4))
        play_id = 100 + i  # unique per play across games
        coverage = str(rng.choice(COVERAGES))
        n_routes = int(rng.integers(1, max_routes + 1))
        nfl_ids = rng.choice(np.arange(1000, 1015), size=n_routes, replace=False)
        target_idx = int(rng.integers(0, n_routes + 1))  # == n_routes -> no target
        for j, nfl_id in enumerate(nfl_ids):
            sep = float(rng.uniform(0.3, 8.0))
            exp = float(rng.uniform(1.0, 5.0))
            rows.append({
                "gameId": game_id,
                "playId": play_id,
                "nflId": int(nfl_id),
                "displayName": f"Player{int(nfl_id)} Surname{int(nfl_id)}",
                "pff_positionLinedUp": str(rng.choice(POSITIONS)),
                "pff_passCoverage": coverage,
                "pff_passCoverageType": COVERAGE_TYPES[coverage],
                "separation": sep,
                "expected_separation": exp,
                "soe": sep - exp,
                "is_likely_target": j == target_idx,
            })
    df = pd.DataFrame(rows, columns=ROUTES_COLUMNS)
    if nan_rate > 0:
        for col in ("separation", "expected_separation", "soe"):
            mask = rng.random(len(df)) < nan_rate
            df.loc[mask, col] = np.nan
    return df


def make_releases(rng: np.random.Generator, routes: pd.DataFrame,
                  extra_plays: int = 0) -> pd.DataFrame:
    """Release frames for EVERY (gameId, playId) in routes (Req 2.4 consistency
    with /api/soe/plays), plus optional extra plays that have no routes."""
    keys = routes[["gameId", "playId"]].drop_duplicates().reset_index(drop=True)
    frames = rng.integers(10, 60, size=len(keys))
    out = keys.assign(frameId=frames.astype("int64"))
    if extra_plays:
        extra = pd.DataFrame({
            "gameId": 2021099999,
            "playId": 9000 + np.arange(extra_plays),
            "frameId": rng.integers(10, 60, size=extra_plays).astype("int64"),
        })
        out = pd.concat([out, extra], ignore_index=True)
    return out[RELEASES_COLUMNS]


def make_bpi(rng: np.random.Generator, n_plays: int = 40) -> pd.DataFrame:
    """Synthetic bpi_plays table with distance_bucket consistent with yardsToGo."""
    ytg = rng.integers(1, 21, size=n_plays)
    df = pd.DataFrame({
        "gameId": 2021090900 + rng.integers(0, 4, size=n_plays),
        "playId": 500 + np.arange(n_plays),
        "num_rushers": rng.integers(1, 8, size=n_plays),
        "is_pressure": rng.random(n_plays) < 0.3,
        "down": rng.integers(1, 5, size=n_plays),
        "yardsToGo": ytg,
        "distance_bucket": [bucket_for(v) for v in ytg],
    })
    return df[BPI_COLUMNS]


def write_precomputed(directory: Path, routes: pd.DataFrame | None = None,
                      releases: pd.DataFrame | None = None,
                      bpi: pd.DataFrame | None = None) -> Path:
    """Write any supplied tables as the precomputed CSVs. None means the file is omitted."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if routes is not None:
        routes.to_csv(directory / ROUTES_FILE, index=False)
    if releases is not None:
        releases.to_csv(directory / RELEASES_FILE, index=False)
    if bpi is not None:
        bpi.to_csv(directory / BPI_FILE, index=False)
    return directory


def write_synthetic_dir(directory: Path, seed: int = 0, nan_rate: float = 0.0):
    """Write a full synthetic precomputed directory. Returns (routes, releases, bpi)."""
    rng = np.random.default_rng(seed)
    routes = make_routes(rng, nan_rate=nan_rate)
    releases = make_releases(rng, routes, extra_plays=2)
    bpi = make_bpi(rng)
    write_precomputed(directory, routes, releases, bpi)
    return routes, releases, bpi


def write_empty_files(directory: Path) -> Path:
    """Write the three files completely empty (zero bytes)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in (ROUTES_FILE, RELEASES_FILE, BPI_FILE):
        (directory / name).write_text("", encoding="utf-8")
    return directory


class _ClientContext:
    """Context manager wrapping TestClient so the lifespan runs on enter."""

    def __init__(self, directory: Path):
        self.directory = directory
        self._client = None

    def __enter__(self):
        from fastapi.testclient import TestClient

        from backend.main import create_app  # lazy: created by task 6.4

        self._client = TestClient(create_app(Path(self.directory)))
        return self._client.__enter__()

    def __exit__(self, *exc):
        return self._client.__exit__(*exc)


def make_client(directory: Path) -> _ClientContext:
    """Use as ``with make_client(dir) as client:`` so the lifespan loads the store."""
    return _ClientContext(directory)


@pytest.fixture
def synthetic_dir(tmp_path):
    """Directory with a full seeded synthetic dataset."""
    write_synthetic_dir(tmp_path / "pre", seed=123)
    return tmp_path / "pre"


@pytest.fixture
def synthetic_data(tmp_path):
    """(directory, routes, releases, bpi) for the seeded synthetic dataset."""
    directory = tmp_path / "pre"
    routes, releases, bpi = write_synthetic_dir(directory, seed=123)
    return directory, routes, releases, bpi


@pytest.fixture
def missing_dir(tmp_path):
    """A directory path that does not exist."""
    return tmp_path / "does_not_exist"


@pytest.fixture
def empty_files_dir(tmp_path):
    """A directory whose three precomputed files are empty."""
    return write_empty_files(tmp_path / "empty")


@pytest.fixture
def client_factory():
    """Fixture form of make_client."""
    return make_client
