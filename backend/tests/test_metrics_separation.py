"""Property tests for release frame selection and separation (Properties 1 and 2)."""

import math

import numpy as np
import pandas as pd

from backend.metrics import compute_separation, select_release_frames

ITERATIONS = 150
OTHER_EVENTS = [None, "ball_snap", "pass_arrived", "line_set"]


def _random_tracking(rng):
    rows = []
    n_plays = int(rng.integers(0, 8))
    for p in range(n_plays):
        game_id = int(rng.integers(1, 4))
        play_id = int(p + 1)
        n_frames = int(rng.integers(1, 30))
        kind = int(rng.integers(0, 5))  # 0 none, 1 primary, 2 fallback, 3 both, 4 repeated
        primary = set()
        fallback = set()
        if kind in (1, 3):
            primary.add(int(rng.integers(1, n_frames + 1)))
        if kind in (2, 3):
            fallback.add(int(rng.integers(1, n_frames + 1)))
        if kind == 4:
            primary.update(int(x) for x in rng.integers(1, n_frames + 1, size=3))
        for f in range(1, n_frames + 1):
            for nfl_id in range(int(rng.integers(1, 4))):
                if f in primary:
                    ev = "pass_forward"
                elif f in fallback:
                    ev = "autoevent_passforward"
                else:
                    ev = OTHER_EVENTS[int(rng.integers(0, len(OTHER_EVENTS)))]
                rows.append((game_id * 1000, play_id, f, nfl_id, ev))
    return pd.DataFrame(rows, columns=["gameId", "playId", "frameId", "nflId", "event"])


def test_release_frame_selection_property():
    rng = np.random.default_rng(12345)
    for _ in range(ITERATIONS):
        tracking = _random_tracking(rng)
        result = select_release_frames(tracking)

        assert list(result.columns) == ["gameId", "playId", "frameId"]
        assert not result.duplicated(["gameId", "playId"]).any()

        expected = {}
        for (g, p), grp in tracking.groupby(["gameId", "playId"]):
            prim = grp.loc[grp["event"] == "pass_forward", "frameId"]
            fall = grp.loc[grp["event"] == "autoevent_passforward", "frameId"]
            if len(prim):
                expected[(g, p)] = int(prim.min())
            elif len(fall):
                expected[(g, p)] = int(fall.min())

        actual = {(int(r.gameId), int(r.playId)): int(r.frameId) for r in result.itertuples()}
        assert actual == {(int(g), int(p)): f for (g, p), f in expected.items()}


def test_release_frame_empty_tracking():
    empty = pd.DataFrame(columns=["gameId", "playId", "frameId", "nflId", "event"])
    assert select_release_frames(empty).empty


def _brute_force(route, cover):
    out = []
    for rx, ry in route:
        best = math.inf
        for cx, cy in cover:
            best = min(best, math.sqrt((rx - cx) ** 2 + (ry - cy) ** 2))
        out.append(best)
    return np.array(out)


def test_separation_matches_brute_force_property():
    rng = np.random.default_rng(54321)
    for _ in range(ITERATIONS):
        route = rng.uniform(-60, 60, size=(int(rng.integers(0, 8)), 2))
        cover = rng.uniform(-60, 60, size=(int(rng.integers(1, 12)), 2))
        sep = compute_separation(route, cover)
        assert sep.shape == (route.shape[0],)
        assert np.all(sep >= 0)
        np.testing.assert_allclose(sep, _brute_force(route, cover), rtol=1e-9, atol=1e-9)


def test_separation_symmetry_single_points():
    rng = np.random.default_rng(777)
    for _ in range(ITERATIONS):
        a = rng.uniform(-60, 60, size=(1, 2))
        b = rng.uniform(-60, 60, size=(1, 2))
        np.testing.assert_allclose(
            compute_separation(a, b), compute_separation(b, a), rtol=1e-12, atol=1e-12
        )


def test_separation_empty_coverage_yields_no_values():
    rng = np.random.default_rng(99)
    for _ in range(ITERATIONS):
        route = rng.uniform(-60, 60, size=(int(rng.integers(0, 6)), 2))
        assert compute_separation(route, np.empty((0, 2))).shape == (0,)
