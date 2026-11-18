"""Property tests for the data store and aggregation endpoints (Properties 9-14).

Plain pytest loops over seeded ``numpy.random.default_rng`` generators. Frames are
written to ``tmp_path`` and pandas is the reference aggregation.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from backend.store import DataStore
from backend.tests.conftest import (
    COVERAGE_TYPES,
    COVERAGES,
    N_ITER,
    POSITIONS,
    make_bpi,
    make_client,
    make_releases,
    make_routes,
    write_precomputed,
)


def _msg(seed: int, it: int, extra: str = "") -> str:
    return f"seed={seed} iteration={it} {extra}".strip()


def _build(tmp_path, seed: int, it: int, nan_rate: float = 0.0, n_plays: int | None = None):
    rng = np.random.default_rng(seed + it)
    routes = make_routes(
        rng, n_plays=int(rng.integers(1, 30)) if n_plays is None else n_plays,
        max_routes=int(rng.integers(1, 7)), nan_rate=nan_rate,
    )
    releases = make_releases(rng, routes, extra_plays=int(rng.integers(0, 3)))
    bpi = make_bpi(rng, n_plays=int(rng.integers(1, 60)))
    directory = write_precomputed(tmp_path / f"d{seed}_{it}", routes, releases, bpi)
    return rng, directory, routes, releases, bpi


def _opt(rng: np.random.Generator, values: list):
    """Pick one of values or None (filter absent) with equal-ish probability."""
    if not values or rng.random() < 0.4:
        return None
    return values[int(rng.integers(0, len(values)))]


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is None and (b is None or (isinstance(b, float) and math.isnan(b)))
    return a == pytest.approx(b, abs=1e-9)


# Feature: soe-bpi-backend, Property 9: Filter values are sorted and distinct
def test_property_9_filter_values_sorted_and_distinct(tmp_path):
    """**Validates: Requirements 9.1, 9.2**"""
    seed = 9000
    for it in range(N_ITER):
        _, directory, routes, _, bpi = _build(tmp_path, seed, it)
        values = DataStore.load(directory).filter_values()
        expected = {
            "pff_passCoverage": sorted(routes["pff_passCoverage"].dropna().unique().tolist()),
            "pff_passCoverageType": sorted(routes["pff_passCoverageType"].dropna().unique().tolist()),
            "pff_positionLinedUp": sorted(routes["pff_positionLinedUp"].dropna().unique().tolist()),
            "distance_bucket": sorted(bpi["distance_bucket"].dropna().unique().tolist()),
            "down": sorted(int(v) for v in bpi["down"].dropna().unique()),
        }
        for key, ref in expected.items():
            got = values[key]
            assert got == ref, _msg(seed, it, key)
            assert got == sorted(got), _msg(seed, it, key)
            assert len(got) == len(set(got)), _msg(seed, it, key)
            assert all(v is not None for v in got), _msg(seed, it, key)

    # Through the endpoint too, one example.
    _, directory, routes, _, _ = _build(tmp_path, seed, 0)
    with make_client(directory) as client:
        body = client.get("/api/filters").json()
    assert body["pff_passCoverage"] == sorted(routes["pff_passCoverage"].unique().tolist())


# Feature: soe-bpi-backend, Property 10: Heatmap cells match filtered aggregation
def test_property_10_heatmap_matches_filtered_aggregation(tmp_path):
    """**Validates: Requirements 10.1, 10.2, 10.3, 10.4**"""
    seed = 1000
    for it in range(N_ITER):
        rng, directory, routes, _, _ = _build(tmp_path, seed, it)
        only_targets = bool(rng.random() < 0.4)
        coverage = _opt(rng, COVERAGES)
        coverage_type = _opt(rng, sorted(set(COVERAGE_TYPES.values())))
        position = _opt(rng, POSITIONS)

        ref = routes
        if only_targets:
            ref = ref[ref["is_likely_target"]]
        if coverage is not None:
            ref = ref[ref["pff_passCoverage"] == coverage]
        if coverage_type is not None:
            ref = ref[ref["pff_passCoverageType"] == coverage_type]
        if position is not None:
            ref = ref[ref["pff_positionLinedUp"] == position]
        expected = {
            (k[0], k[1]): (float(g["soe"].mean()), int(len(g)))
            for k, g in ref.groupby(["pff_passCoverage", "pff_positionLinedUp"])
        }

        params: dict = {}
        if only_targets:
            params["only_targets"] = "true"
        if coverage is not None:
            params["coverage"] = coverage
        if coverage_type is not None:
            params["coverage_type"] = coverage_type
        if position is not None:
            params["position"] = position
        with make_client(directory) as client:
            resp = client.get("/api/soe/heatmap", params=params)
        assert resp.status_code == 200, _msg(seed, it)
        cells = resp.json()["cells"]
        got = {(c["pff_passCoverage"], c["pff_positionLinedUp"]): (c["mean_soe"], c["n"]) for c in cells}
        assert len(cells) == len(got), _msg(seed, it, "duplicate cells")
        assert set(got) == set(expected), _msg(seed, it, str(params))
        for key, (mean, n) in expected.items():
            assert got[key][1] == n, _msg(seed, it, str(key))
            assert got[key][0] == pytest.approx(mean, abs=1e-9), _msg(seed, it, str(key))


# Feature: soe-bpi-backend, Property 11: Player ranking is sorted, filtered and bounded
def test_property_11_player_ranking_sorted_filtered_bounded(tmp_path):
    """**Validates: Requirements 11.1, 11.2, 11.3, 11.5, 11.6**"""
    seed = 1100
    for it in range(N_ITER):
        rng, directory, routes, _, _ = _build(tmp_path, seed, it)
        only_targets = bool(rng.random() < 0.3)
        coverage = _opt(rng, COVERAGES)
        position = _opt(rng, POSITIONS)
        min_n = int(rng.integers(1, 5))
        limit = int(rng.integers(1, 12))

        ref = routes
        if only_targets:
            ref = ref[ref["is_likely_target"]]
        if coverage is not None:
            ref = ref[ref["pff_passCoverage"] == coverage]
        if position is not None:
            ref = ref[ref["pff_positionLinedUp"] == position]
        agg = ref.groupby("nflId").agg(
            mean_soe=("soe", "mean"), mean_separation=("separation", "mean"), n=("soe", "size"),
        ).reset_index()
        agg = agg[agg["n"] >= min_n].sort_values(
            ["mean_soe", "nflId"], ascending=[False, True]
        ).head(limit)

        params: dict = {"min_n": min_n, "limit": limit}
        if only_targets:
            params["only_targets"] = "true"
        if coverage is not None:
            params["coverage"] = coverage
        if position is not None:
            params["position"] = position
        with make_client(directory) as client:
            resp = client.get("/api/soe/players", params=params)
        assert resp.status_code == 200, _msg(seed, it)
        got = resp.json()["players"]

        assert len(got) <= limit, _msg(seed, it)
        assert all(p["n"] >= min_n for p in got), _msg(seed, it)
        keys = [(-p["mean_soe"], p["nflId"]) for p in got]
        assert keys == sorted(keys), _msg(seed, it, "order")
        assert [p["nflId"] for p in got] == agg["nflId"].tolist(), _msg(seed, it, str(params))
        for p, (_, r) in zip(got, agg.iterrows()):
            assert p["n"] == int(r["n"]), _msg(seed, it)
            assert p["mean_soe"] == pytest.approx(float(r["mean_soe"]), abs=1e-9), _msg(seed, it)
            assert p["mean_separation"] == pytest.approx(float(r["mean_separation"]), abs=1e-9), _msg(seed, it)


# Feature: soe-bpi-backend, Property 12: Play list aggregates and pagination
def test_property_12_play_list_aggregates_and_pagination(tmp_path):
    """**Validates: Requirements 12.1, 12.2, 12.3, 12.5**"""
    seed = 1200
    for it in range(N_ITER):
        rng, directory, routes, _, _ = _build(tmp_path, seed, it)
        coverage = _opt(rng, COVERAGES)
        position = _opt(rng, POSITIONS)
        limit = int(rng.integers(1, 10))
        offset = int(rng.integers(0, 12))

        ref = routes
        if coverage is not None:
            ref = ref[ref["pff_passCoverage"] == coverage]
        if position is not None:
            ref = ref[ref["pff_positionLinedUp"] == position]
        expected = []
        for (g, p), grp in sorted(ref.groupby(["gameId", "playId"]), key=lambda kv: kv[0]):
            tgt = grp[grp["is_likely_target"]]
            expected.append({
                "gameId": int(g), "playId": int(p), "n_routes": int(len(grp)),
                "mean_soe": float(grp["soe"].mean()), "max_soe": float(grp["soe"].max()),
                "target_soe": float(tgt["soe"].mean()) if len(tgt) else None,
            })

        params: dict = {"limit": limit, "offset": offset}
        if coverage is not None:
            params["coverage"] = coverage
        if position is not None:
            params["position"] = position
        with make_client(directory) as client:
            resp = client.get("/api/soe/plays", params=params)
        assert resp.status_code == 200, _msg(seed, it)
        body = resp.json()

        assert body["total"] == len(expected), _msg(seed, it, str(params))
        page = expected[offset: offset + limit]
        assert len(body["plays"]) == len(page), _msg(seed, it, str(params))
        for got, exp in zip(body["plays"], page):
            assert (got["gameId"], got["playId"]) == (exp["gameId"], exp["playId"]), _msg(seed, it)
            assert got["n_routes"] == exp["n_routes"], _msg(seed, it)
            assert _same(got["mean_soe"], exp["mean_soe"]), _msg(seed, it)
            assert _same(got["max_soe"], exp["max_soe"]), _msg(seed, it)
            assert _same(got["target_soe"], exp["target_soe"]), _msg(seed, it, "target_soe")


# Feature: soe-bpi-backend, Property 13: BPI summary rates and filters
def test_property_13_bpi_summary_rates_and_filters(tmp_path):
    """**Validates: Requirements 14.1, 14.2, 14.3, 14.4**"""
    seed = 1300
    for it in range(N_ITER):
        rng, directory, _, _, bpi = _build(tmp_path, seed, it)
        down = _opt(rng, [1, 2, 3, 4])
        bucket = _opt(rng, ["Corto", "Medio", "Largo"])
        rushers = _opt(rng, list(range(1, 8)))

        ref = bpi
        params: dict = {}
        if down is not None:
            ref = ref[ref["down"] == down]
            params["down"] = down
        if bucket is not None:
            ref = ref[ref["distance_bucket"] == bucket]
            params["distance_bucket"] = bucket
        if rushers is not None:
            ref = ref[ref["num_rushers"] == rushers]
            params["num_rushers"] = rushers

        with make_client(directory) as client:
            resp = client.get("/api/bpi/summary", params=params)
        assert resp.status_code == 200, _msg(seed, it)
        body = resp.json()

        assert body["total_plays"] == len(ref), _msg(seed, it, str(params))
        if len(ref) == 0:
            assert body["groups"] == [], _msg(seed, it)
            assert body["pressure_rate"] is None, _msg(seed, it)
            continue
        assert body["pressure_rate"] == pytest.approx(float(ref["is_pressure"].mean()), abs=1e-12)
        assert 0.0 <= body["pressure_rate"] <= 1.0, _msg(seed, it)

        expected = {
            (int(k[0]), k[1]): (int(len(g)), int(g["is_pressure"].sum()))
            for k, g in ref.groupby(["num_rushers", "distance_bucket"])
        }
        got = {(g["num_rushers"], g["distance_bucket"]): g for g in body["groups"]}
        assert len(got) == len(body["groups"]), _msg(seed, it, "duplicate groups")
        assert set(got) == set(expected), _msg(seed, it, str(params))
        assert sum(g["n_plays"] for g in body["groups"]) == len(ref), _msg(seed, it)
        for key, (n_plays, n_pressure) in expected.items():
            g = got[key]
            assert g["n_plays"] == n_plays, _msg(seed, it, str(key))
            assert g["n_pressure"] == n_pressure, _msg(seed, it, str(key))
            assert 0.0 <= g["pressure_rate"] <= 1.0, _msg(seed, it, str(key))
            assert g["pressure_rate"] == pytest.approx(n_pressure / n_plays, abs=1e-12)


# Feature: soe-bpi-backend, Property 14: NaN serializes as null
def test_property_14_nan_serializes_as_null(tmp_path):
    """**Validates: Requirements 15.5**"""

    def strict_loads(text: str):
        def reject(token):
            raise AssertionError(f"non-JSON constant {token} in response")
        return json.loads(text, parse_constant=reject)

    seed = 1400
    saw_null = False
    for it in range(N_ITER):
        rng, directory, routes, _, _ = _build(tmp_path, seed, it, nan_rate=0.5)
        with make_client(directory) as client:
            heat = client.get("/api/soe/heatmap")
            players = client.get("/api/soe/players", params={"limit": 500})
            plays = client.get("/api/soe/plays", params={"limit": 500})
        for resp in (heat, players, plays):
            assert resp.status_code == 200, _msg(seed, it)
            assert "NaN" not in resp.text and "Infinity" not in resp.text, _msg(seed, it)
            strict_loads(resp.text)  # valid JSON, no bare NaN

        # Groups whose values are all NaN must come back as null.
        ref_players = routes.groupby("nflId")["soe"].mean()
        got_players = {p["nflId"]: p["mean_soe"] for p in players.json()["players"]}
        for nfl_id, mean in ref_players.items():
            assert nfl_id in got_players, _msg(seed, it)
            if pd.isna(mean):
                assert got_players[nfl_id] is None, _msg(seed, it, f"nflId={nfl_id}")
                saw_null = True
            else:
                assert got_players[nfl_id] == pytest.approx(float(mean), abs=1e-9), _msg(seed, it)

        ref_cells = routes.groupby(["pff_passCoverage", "pff_positionLinedUp"])["soe"].mean()
        got_cells = {
            (c["pff_passCoverage"], c["pff_positionLinedUp"]): c["mean_soe"]
            for c in heat.json()["cells"]
        }
        for key, mean in ref_cells.items():
            if pd.isna(mean):
                assert got_cells[key] is None, _msg(seed, it, str(key))
                saw_null = True
    assert saw_null, "generator never produced an all-NaN group"
