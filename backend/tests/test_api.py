"""Endpoint example tests for the SOE/BPI API (task 9.1).

Synthetic data only, seeded numpy generators, no hypothesis.
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.tests.conftest import (
    BPI_FILE,
    N_ITER,
    RELEASES_FILE,
    ROUTES_FILE,
    make_bpi,
    make_client,
    make_releases,
    make_routes,
    write_precomputed,
    write_synthetic_dir,
)

ALL_ENDPOINTS = [
    "/health",
    "/api/health",
    "/api/filters",
    "/api/soe/heatmap",
    "/api/soe/players",
    "/api/soe/plays",
    "/api/bpi/summary",
]


# --------------------------------------------------------------------- health


def test_health_and_api_health_identical_with_data(synthetic_dir):
    with make_client(synthetic_dir) as client:
        a = client.get("/health")
        b = client.get("/api/health")
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json() == {"status": "ok", "data_loaded": True}


def test_health_data_loaded_false_for_missing_dir(missing_dir):
    with make_client(missing_dir) as client:
        a = client.get("/health")
        b = client.get("/api/health")
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json() == {"status": "ok", "data_loaded": False}


def test_health_data_loaded_false_for_empty_files(empty_files_dir):
    with make_client(empty_files_dir) as client:
        a = client.get("/health")
        b = client.get("/api/health")
    assert a.json() == b.json() == {"status": "ok", "data_loaded": False}


# -------------------------------------------------------------------- filters


def test_filters_sorted_distinct(synthetic_data):
    directory, routes, _, bpi = synthetic_data
    with make_client(directory) as client:
        body = client.get("/api/filters").json()
    assert body["pff_passCoverage"] == sorted(routes["pff_passCoverage"].unique())
    assert body["pff_passCoverageType"] == sorted(routes["pff_passCoverageType"].unique())
    assert body["pff_positionLinedUp"] == sorted(routes["pff_positionLinedUp"].unique())
    assert body["distance_bucket"] == sorted(bpi["distance_bucket"].dropna().unique())
    assert body["down"] == sorted(int(d) for d in bpi["down"].unique())


# -------------------------------------------------------------------- heatmap


def test_heatmap_matches_pandas_aggregation(synthetic_data):
    directory, routes, _, _ = synthetic_data
    with make_client(directory) as client:
        resp = client.get("/api/soe/heatmap")
    assert resp.status_code == 200
    cells = resp.json()["cells"]
    expected = routes.groupby(["pff_passCoverage", "pff_positionLinedUp"])["soe"].agg(["mean", "size"])
    assert len(cells) == len(expected)
    for cell in cells:
        mean, size = expected.loc[(cell["pff_passCoverage"], cell["pff_positionLinedUp"])]
        assert cell["n"] == size
        assert cell["mean_soe"] == pytest.approx(mean)


def test_heatmap_filters_apply(synthetic_data):
    directory, routes, _, _ = synthetic_data
    with make_client(directory) as client:
        cov = routes["pff_passCoverage"].iloc[0]
        cells = client.get("/api/soe/heatmap", params={"coverage": cov}).json()["cells"]
        targets = client.get("/api/soe/heatmap", params={"only_targets": "true"}).json()["cells"]
        none = client.get("/api/soe/heatmap", params={"coverage": "NoSuch"}).json()["cells"]
    assert cells and all(c["pff_passCoverage"] == cov for c in cells)
    assert sum(c["n"] for c in targets) == int(routes["is_likely_target"].sum())
    assert none == []


# -------------------------------------------------------------------- players


def test_players_sorted_bounded_and_min_n(synthetic_data):
    directory, routes, _, _ = synthetic_data
    with make_client(directory) as client:
        full = client.get("/api/soe/players", params={"limit": 500}).json()["players"]
        limited = client.get("/api/soe/players", params={"limit": 3}).json()["players"]
        min_n = client.get("/api/soe/players", params={"min_n": 4, "limit": 500}).json()["players"]
    assert len(full) == routes["nflId"].nunique()
    keys = [(-p["mean_soe"], p["nflId"]) for p in full]
    assert keys == sorted(keys)
    assert limited == full[:3]
    assert all(p["n"] >= 4 for p in min_n)
    counts = routes.groupby("nflId").size()
    assert len(min_n) == int((counts >= 4).sum())


# ---------------------------------------------------------------------- plays


def test_plays_aggregate_and_pagination(synthetic_data):
    directory, routes, _, _ = synthetic_data
    n_plays = len(routes[["gameId", "playId"]].drop_duplicates())
    with make_client(directory) as client:
        body = client.get("/api/soe/plays", params={"limit": 500}).json()
        page = client.get("/api/soe/plays", params={"limit": 5, "offset": 2}).json()
        beyond = client.get("/api/soe/plays", params={"offset": 10_000}).json()
    assert body["total"] == n_plays == len(body["plays"])
    keys = [(p["gameId"], p["playId"]) for p in body["plays"]]
    assert keys == sorted(keys)
    assert page["total"] == n_plays
    assert page["plays"] == body["plays"][2:7]
    assert beyond["total"] == n_plays and beyond["plays"] == []
    grouped = routes.groupby(["gameId", "playId"]).agg(n=("soe", "size"), mean=("soe", "mean"))
    for p in body["plays"]:
        n, mean = grouped.loc[(p["gameId"], p["playId"])]
        assert p["n_routes"] == n
        assert p["mean_soe"] == pytest.approx(mean)


def test_plays_all_have_release_frame(tmp_path):
    rng = np.random.default_rng(7)
    routes = make_routes(rng, n_plays=15)
    releases = make_releases(rng, routes)
    keep = releases.iloc[::2]  # half of the plays have no frame
    directory = write_precomputed(tmp_path / "pre", routes, keep, make_bpi(rng))
    have = set(map(tuple, keep[["gameId", "playId"]].to_numpy().tolist()))
    with make_client(directory) as client:
        body = client.get("/api/soe/plays", params={"limit": 500}).json()
        assert body["total"] == len(have) == len(body["plays"])
        for p in body["plays"]:
            assert (p["gameId"], p["playId"]) in have
            detail = client.get(f"/api/soe/play/{p['gameId']}/{p['playId']}")
            assert detail.status_code == 200
            assert detail.json()["frameId"] is not None


# ---------------------------------------------------------------- play detail


def test_play_detail_known_play(synthetic_data):
    directory, routes, releases, _ = synthetic_data
    row = routes.iloc[0]
    game_id, play_id = int(row["gameId"]), int(row["playId"])
    with make_client(directory) as client:
        resp = client.get(f"/api/soe/play/{game_id}/{play_id}")
    assert resp.status_code == 200
    body = resp.json()
    expected = routes[(routes["gameId"] == game_id) & (routes["playId"] == play_id)]
    assert body["gameId"] == game_id and body["playId"] == play_id
    assert [r["nflId"] for r in body["routes"]] == sorted(expected["nflId"].tolist())
    frame = releases[(releases["gameId"] == game_id) & (releases["playId"] == play_id)]["frameId"]
    assert body["frameId"] == int(frame.iloc[0])


def test_play_detail_unknown_is_404(synthetic_dir):
    with make_client(synthetic_dir) as client:
        resp = client.get("/api/soe/play/1/2")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Play not found"


# ------------------------------------------------------------------------ bpi


def test_bpi_summary_totals_and_filters(synthetic_data):
    directory, _, _, bpi = synthetic_data
    with make_client(directory) as client:
        body = client.get("/api/bpi/summary").json()
        down = int(bpi["down"].iloc[0])
        filtered = client.get("/api/bpi/summary", params={"down": down}).json()
        empty = client.get("/api/bpi/summary", params={"down": 9}).json()
    assert body["total_plays"] == len(bpi)
    assert body["pressure_rate"] == pytest.approx(bpi["is_pressure"].mean())
    assert sum(g["n_plays"] for g in body["groups"]) == len(bpi)
    assert sum(g["n_pressure"] for g in body["groups"]) == int(bpi["is_pressure"].sum())
    assert all(0.0 <= g["pressure_rate"] <= 1.0 for g in body["groups"])
    assert filtered["total_plays"] == int((bpi["down"] == down).sum())
    assert empty["total_plays"] == 0 and empty["pressure_rate"] is None and empty["groups"] == []


# ------------------------------------------------------- empty / missing data


def _assert_empty_result(path, resp):
    assert resp.status_code == 200, f"{path}: {resp.status_code}"
    body = resp.json()
    if path in ("/health", "/api/health"):
        assert body["data_loaded"] is False
    elif path == "/api/filters":
        assert all(v == [] for v in body.values())
    elif path == "/api/soe/heatmap":
        assert body == {"cells": []}
    elif path == "/api/soe/players":
        assert body == {"players": []}
    elif path == "/api/soe/plays":
        assert body == {"total": 0, "plays": []}
    elif path == "/api/bpi/summary":
        assert body["total_plays"] == 0
        assert body["pressure_rate"] is None
        assert body["groups"] == []


@pytest.mark.parametrize("path", ALL_ENDPOINTS)
def test_missing_directory_gives_empty_result(missing_dir, path):
    with make_client(missing_dir) as client:
        _assert_empty_result(path, client.get(path))


@pytest.mark.parametrize("path", ALL_ENDPOINTS)
def test_empty_files_give_empty_result(empty_files_dir, path):
    with make_client(empty_files_dir) as client:
        _assert_empty_result(path, client.get(path))


def test_play_detail_missing_data_is_404_not_500(missing_dir):
    with make_client(missing_dir) as client:
        assert client.get("/api/soe/play/1/2").status_code == 404


# Feature: soe-bpi-backend, Property 15: Missing data yields Empty_Result everywhere
def test_property_missing_files_never_500(tmp_path):
    rng = np.random.default_rng(15)
    routes = make_routes(rng, n_plays=8)
    releases = make_releases(rng, routes)
    bpi = make_bpi(rng, n_plays=10)
    for i in range(N_ITER):
        present = rng.random(3) < 0.5
        directory = write_precomputed(
            tmp_path / f"it{i}",
            routes if present[0] else None,
            releases if present[1] else None,
            bpi if present[2] else None,
        )
        with make_client(directory) as client:
            for path in ALL_ENDPOINTS:
                resp = client.get(path)
                assert resp.status_code == 200, f"seed=15 iter={i} present={present} {path}"
            health = client.get("/health").json()
            assert health["data_loaded"] is bool(present.all()), f"seed=15 iter={i}"
            detail = client.get("/api/soe/play/1/2")
            assert detail.status_code == 404, f"seed=15 iter={i}"
            if not present[0]:
                assert client.get("/api/soe/heatmap").json() == {"cells": []}
            if not present[2]:
                assert client.get("/api/bpi/summary").json()["total_plays"] == 0


# ------------------------------------------------------------------ 422 cases


@pytest.mark.parametrize(
    "path,params",
    [
        ("/api/soe/players", {"limit": 0}),
        ("/api/soe/players", {"limit": 501}),
        ("/api/soe/players", {"limit": "abc"}),
        ("/api/soe/players", {"min_n": 0}),
        ("/api/soe/plays", {"limit": 0}),
        ("/api/soe/plays", {"limit": 501}),
        ("/api/soe/plays", {"offset": -1}),
        ("/api/soe/play/abc/1", None),
        ("/api/soe/play/1/xyz", None),
        ("/api/bpi/summary", {"down": "x"}),
        ("/api/bpi/summary", {"num_rushers": "x"}),
    ],
)
def test_bad_params_give_422(synthetic_dir, path, params):
    with make_client(synthetic_dir) as client:
        assert client.get(path, params=params).status_code == 422


# Feature: soe-bpi-backend, Property 16: Invalid query parameters are rejected
def test_property_invalid_params_rejected(synthetic_dir):
    rng = np.random.default_rng(16)
    with make_client(synthetic_dir) as client:
        for i in range(N_ITER):
            limit = int(rng.integers(-50, 700))
            offset = int(rng.integers(-20, 30))
            min_n = int(rng.integers(-5, 10))
            for path in ("/api/soe/plays", "/api/soe/players"):
                resp = client.get(path, params={"limit": limit})
                ok = 1 <= limit <= 500
                assert resp.status_code == (200 if ok else 422), f"seed=16 iter={i} {path} limit={limit}"
            resp = client.get("/api/soe/plays", params={"offset": offset})
            assert resp.status_code == (200 if offset >= 0 else 422), f"seed=16 iter={i} offset={offset}"
            resp = client.get("/api/soe/players", params={"min_n": min_n})
            assert resp.status_code == (200 if min_n >= 1 else 422), f"seed=16 iter={i} min_n={min_n}"


# ----------------------------------------------------------------------- CORS


def test_cors_default_origins(monkeypatch, synthetic_dir):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    with make_client(synthetic_dir) as client:
        for origin in ("http://localhost:5173", "http://localhost:3000"):
            resp = client.get("/health", headers={"Origin": origin})
            assert resp.headers.get("access-control-allow-origin") == origin
        resp = client.get("/health", headers={"Origin": "http://evil.example"})
        assert "access-control-allow-origin" not in resp.headers


def test_cors_override_from_env(monkeypatch, synthetic_dir):
    monkeypatch.setenv("CORS_ORIGINS", "http://frontend.example")
    with make_client(synthetic_dir) as client:
        ok = client.get("/health", headers={"Origin": "http://frontend.example"})
        assert ok.headers.get("access-control-allow-origin") == "http://frontend.example"
        default = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert "access-control-allow-origin" not in default.headers


def test_cors_preflight_allows_get_only(monkeypatch, synthetic_dir):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
    with make_client(synthetic_dir) as client:
        resp = client.options("/api/filters", headers=headers)
        assert resp.status_code == 200
        allowed = resp.headers.get("access-control-allow-methods", "")
        assert "GET" in allowed and "POST" not in allowed
