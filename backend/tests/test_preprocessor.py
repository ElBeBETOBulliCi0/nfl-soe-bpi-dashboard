"""Unit tests for scripts/build_precomputed.py using tiny synthetic CSVs.

Nothing reads data/ or backend/precomputed/. All randomness is seeded numpy.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.store import DataStore

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_precomputed.py"
GAME_ID = 2021090900
RELEASE_FRAME = 2
N_ITER = 100


@pytest.fixture(scope="module")
def bp():
    spec = importlib.util.spec_from_file_location("build_precomputed_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Play layouts: playId -> (direction, n_route, n_cover, event)
PLAYS = {
    1: ("right", 3, 4, "pass_forward"),                # usable, routes
    2: ("left", 3, 4, "autoevent_passforward"),        # usable via fallback event, mirrored
    3: ("right", 3, 4, None),                          # no release event: absent everywhere
    4: ("right", 1, 1, "pass_forward"),                # routes, not usable, still in releases
    5: ("right", 3, 0, "pass_forward"),                # no coverage: no routes, not usable
}
CAP = {1: (5, "Cover-3", "Zone"), 2: (10, "Cover-1", "Man"), 3: (2, "Cover-3", "Zone"),
       4: (3, "Cover-3", "Zone"), 5: (1, "Cover-3", "Zone")}


def make_input_dir(data_dir: Path, seed: int = 7) -> dict:
    """Write a tiny dataset. Returns raw (pre-normalization) positions at the release frame."""
    rng = np.random.default_rng(seed)
    (data_dir / "tracking").mkdir(parents=True)

    pd.DataFrame({"gameId": [GAME_ID], "week": [1]}).to_csv(data_dir / "games.csv", index=False)

    ids = list(range(1, 4)) + list(range(11, 15)) + [21, 31]
    pd.DataFrame({"nflId": ids, "displayName": [f"First{i} Last{i}" for i in ids]}).to_csv(
        data_dir / "players.csv", index=False)

    plays, pff, tracking = [], [], []
    raw: dict = {}
    for pid, (direction, n_route, n_cover, event) in PLAYS.items():
        ytg, cov, cov_type = CAP[pid]
        plays.append({
            "gameId": GAME_ID, "playId": pid,
            "playDescription": "pass short to Last1 complete" if pid == 1 else "pass incomplete",
            "down": 2, "yardsToGo": ytg, "possessionTeam": "KC", "defensiveTeam": "BUF",
            "passResult": "C", "playResult": 6,
            "pff_passCoverage": cov, "pff_passCoverageType": cov_type,
        })
        players = (
            [(i, "KC", "Pass Route", "WR") for i in range(1, 1 + n_route)]
            + [(i, "BUF", "Coverage", "CB") for i in range(11, 11 + n_cover)]
            + [(21, "KC", "Pass", "QB")]
        )
        for nfl_id, _team, role, pos in players:
            pff.append({"gameId": GAME_ID, "playId": pid, "nflId": nfl_id, "pff_role": role,
                        "pff_positionLinedUp": pos, "pff_hit": np.nan, "pff_hurry": np.nan,
                        "pff_sack": np.nan})
        if pid == 1:
            pff.append({"gameId": GAME_ID, "playId": pid, "nflId": 31, "pff_role": "Pass Rush",
                        "pff_positionLinedUp": "DE", "pff_hit": np.nan, "pff_hurry": 1.0,
                        "pff_sack": np.nan})
        for frame in (1, 2, 3):
            ev = event if frame == RELEASE_FRAME else None
            for nfl_id, team, _role, _pos in players:
                x, y = rng.uniform(10, 110), rng.uniform(5, 48)
                tracking.append({"gameId": GAME_ID, "playId": pid, "nflId": nfl_id,
                                 "frameId": frame, "team": team, "playDirection": direction,
                                 "x": x, "y": y, "event": ev})
                if frame == RELEASE_FRAME:
                    raw[(pid, nfl_id)] = (x, y)
            tracking.append({"gameId": GAME_ID, "playId": pid, "nflId": np.nan,
                             "frameId": frame, "team": "football", "playDirection": direction,
                             "x": 60.0, "y": 26.0, "event": ev})

    pd.DataFrame(plays).to_csv(data_dir / "plays.csv", index=False)
    pd.DataFrame(pff).to_csv(data_dir / "pffScoutingData.csv", index=False)
    pd.DataFrame(tracking).to_csv(data_dir / "tracking" / "tracking_2021090900.csv", index=False)
    return raw


@pytest.fixture
def run(tmp_path, bp):
    data_dir, out_dir = tmp_path / "data", tmp_path / "out" / "precomputed"
    raw = make_input_dir(data_dir)
    code = bp.main(data_dir, out_dir)
    return code, out_dir, raw


def test_missing_input_returns_1_and_writes_nothing(tmp_path, bp, capsys):
    out_dir = tmp_path / "out"
    code = bp.main(tmp_path / "no_data", out_dir)
    assert code == 1
    assert not out_dir.exists()
    assert "Missing input" in capsys.readouterr().out


def test_missing_tracking_only_returns_1(tmp_path, bp):
    data_dir = tmp_path / "data"
    make_input_dir(data_dir)
    (data_dir / "tracking" / "tracking_2021090900.csv").unlink()
    out_dir = tmp_path / "out"
    assert bp.check_inputs(data_dir) == [data_dir / "tracking" / "tracking_*.csv"]
    assert bp.main(data_dir, out_dir) == 1
    assert not out_dir.exists()


def test_end_to_end_creates_output_dir_and_three_files(run):
    code, out_dir, _ = run
    assert code == 0
    for name in ("soe_routes.csv", "play_release_frames.csv", "bpi_plays.csv"):
        assert (out_dir / name).is_file()


def test_route_file_columns_match_requirement_3_4(run, bp):
    _, out_dir, _ = run
    header = list(pd.read_csv(out_dir / "soe_routes.csv", nrows=0).columns)
    assert header == bp.ROUTE_COLUMNS
    assert header[:11] == [
        "gameId", "playId", "nflId", "displayName", "pff_positionLinedUp",
        "pff_passCoverage", "pff_passCoverageType", "separation",
        "expected_separation", "soe", "is_likely_target",
    ]


def test_routes_content(run):
    _, out_dir, raw = run
    routes = pd.read_csv(out_dir / "soe_routes.csv")
    assert set(routes["playId"]) == {1, 2, 4}
    assert len(routes) == 3 + 3 + 1
    assert routes["soe"].notna().all()
    np.testing.assert_allclose(
        routes["soe"], routes["separation"] - routes["expected_separation"], atol=1e-9)
    # Separation equals the brute-force minimum distance to a coverage player.
    for row in routes.itertuples():
        n_cover = PLAYS[row.playId][2]
        rx, ry = raw[(row.playId, row.nflId)]
        expected = min(
            np.hypot(rx - raw[(row.playId, c)][0], ry - raw[(row.playId, c)][1])
            for c in range(11, 11 + n_cover)
        )
        assert row.separation == pytest.approx(expected, rel=1e-9)
    # Likely target: only Last1 in play 1.
    targets = routes[routes["is_likely_target"]]
    assert list(zip(targets["playId"], targets["nflId"])) == [(1, 1)]
    assert set(routes["week"]) == {1}
    assert set(routes["defensiveTeam"]) == {"BUF"}


def test_release_frames_content(run):
    _, out_dir, raw = run
    frames = pd.read_csv(out_dir / "play_release_frames.csv")
    assert set(frames["playId"]) == {1, 2, 4}  # 3 has no event, 5 has no coverage
    assert (frames["frameId"] == RELEASE_FRAME).all()
    assert frames.groupby("playId").size().to_dict() == {1: 9, 2: 9, 4: 4}
    ball = frames[frames["is_ball"]]
    assert len(ball) == 3 and ball["nflId"].isna().all()
    assert (ball["displayName"] == "football").all()
    # Direction normalization: left play mirrored, right play untouched.
    p2 = frames[(frames["playId"] == 2) & (frames["nflId"] == 1)].iloc[0]
    assert p2["x"] == pytest.approx(120.0 - raw[(2, 1)][0])
    assert p2["y"] == pytest.approx(53.3 - raw[(2, 1)][1])
    p1 = frames[(frames["playId"] == 1) & (frames["nflId"] == 1)].iloc[0]
    assert p1["x"] == pytest.approx(raw[(1, 1)][0])
    assert p1["pff_role"] == "Pass Route"


def test_every_route_play_has_release_frames(run):
    _, out_dir, _ = run
    routes = pd.read_csv(out_dir / "soe_routes.csv")
    frames = pd.read_csv(out_dir / "play_release_frames.csv")
    route_keys = set(map(tuple, routes[["gameId", "playId"]].drop_duplicates().to_numpy()))
    frame_keys = set(map(tuple, frames[["gameId", "playId"]].drop_duplicates().to_numpy()))
    assert route_keys <= frame_keys
    store = DataStore.load(out_dir)
    assert len(store.with_release(store.routes)) == len(store.routes)
    for game_id, play_id in route_keys:
        assert store.release_frame(int(game_id), int(play_id)) == RELEASE_FRAME
        assert not store.play_frames(int(game_id), int(play_id)).empty


def test_bpi_content(run, bp):
    _, out_dir, _ = run
    bpi = pd.read_csv(out_dir / "bpi_plays.csv")
    assert len(bpi) == 1
    row = bpi.iloc[0]
    assert (row["playId"], row["num_rushers"], bool(row["is_pressure"])) == (1, 1, True)
    assert row["distance_bucket"] == "Medio"
    assert list(bpi.columns)[-len(bp.BPI_EXTRA_COLUMNS):] == bp.BPI_EXTRA_COLUMNS
    assert row["defensiveTeam"] == "BUF"


def test_no_tracked_release_events_gives_empty_outputs(tmp_path, bp):
    data_dir, out_dir = tmp_path / "data", tmp_path / "out"
    make_input_dir(data_dir)
    path = data_dir / "tracking" / "tracking_2021090900.csv"
    df = pd.read_csv(path)
    df["event"] = np.nan
    df.to_csv(path, index=False)
    assert bp.main(data_dir, out_dir) == 0
    assert list(pd.read_csv(out_dir / "soe_routes.csv").columns) == bp.ROUTE_COLUMNS
    assert pd.read_csv(out_dir / "soe_routes.csv").empty


# ---------------------------------------------------------------- Property 8


def _text(rng, choices, n, none_rate=0.2):
    return [None if rng.random() < none_rate else str(rng.choice(choices)) for _ in range(n)]


def _nan_floats(rng, low, high, n, nan_rate=0.2):
    vals = rng.uniform(low, high, size=n)
    vals[rng.random(n) < nan_rate] = np.nan
    return vals


def _rand_routes(rng, n):
    return pd.DataFrame({
        "gameId": rng.integers(2021090900, 2021091000, size=n),
        "playId": rng.integers(1, 5000, size=n),
        "nflId": rng.integers(30000, 60000, size=n),
        "displayName": [f"First{i} Last{i}" for i in range(n)],
        "pff_positionLinedUp": _text(rng, ["WR", "TE", "HB"], n),
        "pff_passCoverage": _text(rng, ["Cover-1", "Cover-3"], n),
        "pff_passCoverageType": _text(rng, ["Man", "Zone"], n),
        "separation": _nan_floats(rng, 0, 10, n),
        "expected_separation": _nan_floats(rng, 0, 10, n),
        "soe": _nan_floats(rng, -5, 5, n),
        "is_likely_target": rng.random(n) < 0.3,
        "week": rng.integers(1, 19, size=n).astype(float),
        "possessionTeam": _text(rng, ["KC", "BUF"], n),
        "defensiveTeam": _text(rng, ["KC", "BUF"], n),
    })


def _rand_frames(rng, n):
    is_ball = rng.random(n) < 0.15
    nfl = pd.array(np.where(is_ball, -1, rng.integers(30000, 60000, size=n)), dtype="Int64")
    nfl[is_ball] = pd.NA
    return pd.DataFrame({
        "gameId": rng.integers(2021090900, 2021091000, size=n),
        "playId": rng.integers(1, 5000, size=n),
        "frameId": rng.integers(1, 120, size=n),
        "nflId": nfl,
        "displayName": _text(rng, ["A B", "C D"], n),
        "club": _text(rng, ["KC", "BUF", "football"], n),
        "team": _text(rng, ["KC", "BUF", "football"], n),
        "x": _nan_floats(rng, 0, 120, n),
        "y": _nan_floats(rng, 0, 53.3, n),
        "is_ball": is_ball,
        "pff_role": _text(rng, ["Pass Route", "Coverage"], n),
        "pff_positionLinedUp": _text(rng, ["WR", "CB"], n),
    })


def _rand_bpi(rng, n):
    return pd.DataFrame({
        "gameId": rng.integers(2021090900, 2021091000, size=n),
        "playId": rng.integers(1, 5000, size=n),
        "num_rushers": rng.integers(1, 9, size=n),
        "is_pressure": rng.random(n) < 0.4,
        "down": _nan_floats(rng, 1, 4, n).round(),
        "yardsToGo": _nan_floats(rng, 1, 20, n).round(),
        "distance_bucket": _text(rng, ["Corto", "Medio", "Largo"], n),
        "defensiveTeam": _text(rng, ["KC", "BUF"], n),
        "pff_passCoverage": _text(rng, ["Cover-1", "Cover-3"], n),
        "pff_passCoverageType": _text(rng, ["Man", "Zone"], n),
        "playResult": _nan_floats(rng, -5, 40, n).round(),
        "passResult": _text(rng, ["C", "I", "IN"], n),
    })


def _assert_same(written: pd.DataFrame, loaded: pd.DataFrame, columns: list[str]):
    assert len(loaded) == len(written)
    for col in columns:
        a, b = written[col], loaded[col]
        if col in ("is_likely_target", "is_ball", "is_pressure"):
            assert a.astype(bool).tolist() == b.astype(bool).tolist(), col
        elif pd.api.types.is_numeric_dtype(a) or pd.api.types.is_numeric_dtype(b):
            np.testing.assert_allclose(
                a.astype("float64").to_numpy(), b.astype("float64").to_numpy(),
                rtol=1e-12, atol=0, equal_nan=True, err_msg=col)
        else:
            assert [None if pd.isna(v) else v for v in a] == [
                None if pd.isna(v) else v for v in b], col


def test_property_8_output_csv_round_trip(tmp_path, bp):
    # Feature: soe-bpi-backend, Property 8: Output CSV round trip
    # **Validates: Requirements 1.2, 1.3, 3.4, 15.5**
    rng = np.random.default_rng(8)
    for i in range(N_ITER):
        out_dir = tmp_path / f"iter{i}"
        n = int(rng.integers(1, 25))
        routes, frames, bpi = _rand_routes(rng, n), _rand_frames(rng, n), _rand_bpi(rng, n)
        bp.write_outputs(out_dir, routes, frames, bpi)

        assert list(pd.read_csv(out_dir / "soe_routes.csv", nrows=0).columns) == list(routes.columns)
        assert list(pd.read_csv(out_dir / "play_release_frames.csv", nrows=0).columns) == list(frames.columns)
        assert list(pd.read_csv(out_dir / "bpi_plays.csv", nrows=0).columns) == list(bpi.columns)

        store = DataStore.load(out_dir)
        assert store.data_loaded
        _assert_same(routes, store.routes, list(routes.columns))
        _assert_same(frames, store.frames, list(frames.columns))
        _assert_same(bpi, store.bpi, list(bpi.columns))
