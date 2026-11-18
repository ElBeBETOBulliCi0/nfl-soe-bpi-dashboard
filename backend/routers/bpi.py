"""BPI endpoints: pressure summary by rusher count, down x distance and defense."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Query, Request

from backend.schemas import (
    BpiDefenseRow,
    BpiDownDistanceCell,
    BpiGroup,
    BpiRushersRow,
    BpiSummaryResponse,
)
from backend.store import DataStore

router = APIRouter()

BUCKET_ORDER = {"Corto": 0, "Medio": 1, "Largo": 2}


def _rate(n_pressure: int, n_plays: int) -> float | None:
    """Fraction in [0, 1], or None when there are no plays."""
    if n_plays <= 0:
        return None
    return min(1.0, max(0.0, n_pressure / n_plays))


def _none_if_na(value):
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def _bucket_key(bucket) -> tuple[int, int]:
    return (bucket is None, BUCKET_ORDER.get(bucket, 99) if bucket is not None else 0)


def _mean_yards(value) -> float | None:
    """Mean of non-null playResult as a float, or None when no value exists."""
    value = _none_if_na(value)
    return float(value) if value is not None else None


def _bpi(pressure_rate: float | None, mean_yards: float | None) -> float | None:
    """BPI = pressure_rate * 100 - mean_yards * 5, rounded to 2 decimals."""
    if pressure_rate is None or mean_yards is None:
        return None
    return round(pressure_rate * 100 - mean_yards * 5, 2)


def _agg(work: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    return (
        work.groupby(keys, dropna=False)
        .agg(n_plays=("is_pressure", "size"), n_pressure=("is_pressure", "sum"),
             mean_yards=("playResult", "mean"))
        .reset_index()
    )


@router.get("/api/bpi/summary", response_model=BpiSummaryResponse)
def bpi_summary(
    request: Request,
    down: int | None = Query(None),
    distance_bucket: str | None = Query(None),
    num_rushers: int | None = Query(None),
    coverage: str | None = Query(None),
    team: str | None = Query(None),
) -> BpiSummaryResponse:
    store = getattr(request.app.state, "store", None) or DataStore()
    df = store.filter_bpi(
        down=down, distance_bucket=distance_bucket, num_rushers=num_rushers,
        coverage=coverage, team=team,
    )

    total = int(len(df))
    if total == 0:
        return BpiSummaryResponse(
            total_plays=0, pressure_rate=None, mean_yards_allowed=None, groups=[])

    pressure = df["is_pressure"].astype(bool)
    total_pressure = int(pressure.sum())

    work = pd.DataFrame(
        {
            "num_rushers": df["num_rushers"].to_numpy(),
            "distance_bucket": df["distance_bucket"].astype(object).to_numpy(),
            "down": df["down"].to_numpy(),
            "defensiveTeam": df["defensiveTeam"].astype(object).to_numpy(),
            "playResult": pd.to_numeric(df["playResult"], errors="coerce").to_numpy(dtype="float64"),
            "is_pressure": pressure.to_numpy(),
        }
    )
    total_yards = _mean_yards(work["playResult"].mean())

    # (num_rushers, distance_bucket) groups (Req 14.1).
    groups: list[BpiGroup] = []
    for row in _agg(work, ["num_rushers", "distance_bucket"]).itertuples(index=False):
        n_plays, n_pressure = int(row.n_plays), int(row.n_pressure)
        rate, yards = _rate(n_pressure, n_plays), _mean_yards(row.mean_yards)
        groups.append(BpiGroup(
            num_rushers=int(row.num_rushers),
            distance_bucket=_none_if_na(row.distance_bucket),
            n_plays=n_plays, n_pressure=n_pressure,
            pressure_rate=rate, mean_yards_allowed=yards, bpi=_bpi(rate, yards),
        ))
    groups.sort(key=lambda g: (g.num_rushers, *_bucket_key(g.distance_bucket)))

    # Table by number of rushers.
    by_rushers: list[BpiRushersRow] = []
    for row in _agg(work, ["num_rushers"]).itertuples(index=False):
        n_plays, n_pressure = int(row.n_plays), int(row.n_pressure)
        rate, yards = _rate(n_pressure, n_plays), _mean_yards(row.mean_yards)
        by_rushers.append(BpiRushersRow(
            num_rushers=int(row.num_rushers), n_plays=n_plays, n_pressure=n_pressure,
            pressure_rate=rate, mean_yards_allowed=yards, bpi=_bpi(rate, yards),
        ))
    by_rushers.sort(key=lambda r: r.num_rushers)

    # Down x distance matrix.
    down_distance: list[BpiDownDistanceCell] = []
    for row in _agg(work, ["down", "distance_bucket"]).itertuples(index=False):
        n_plays, n_pressure = int(row.n_plays), int(row.n_pressure)
        d = _none_if_na(row.down)
        rate, yards = _rate(n_pressure, n_plays), _mean_yards(row.mean_yards)
        down_distance.append(BpiDownDistanceCell(
            down=int(d) if d is not None else None,
            distance_bucket=_none_if_na(row.distance_bucket),
            n_plays=n_plays, n_pressure=n_pressure,
            pressure_rate=rate, mean_yards_allowed=yards, bpi=_bpi(rate, yards),
        ))
    down_distance.sort(key=lambda c: (c.down is None, c.down or 0, *_bucket_key(c.distance_bucket)))

    # Defense ranking: pressure rate descending, then team name.
    defense = (
        work.groupby("defensiveTeam", dropna=False)
        .agg(n_plays=("is_pressure", "size"), n_pressure=("is_pressure", "sum"),
             mean_rushers=("num_rushers", "mean"), mean_yards=("playResult", "mean"))
        .reset_index()
    )
    defense_ranking: list[BpiDefenseRow] = []
    for row in defense.itertuples(index=False):
        n_plays, n_pressure = int(row.n_plays), int(row.n_pressure)
        mean_rushers = _none_if_na(row.mean_rushers)
        rate, yards = _rate(n_pressure, n_plays), _mean_yards(row.mean_yards)
        defense_ranking.append(BpiDefenseRow(
            defensiveTeam=_none_if_na(row.defensiveTeam),
            n_plays=n_plays, n_pressure=n_pressure,
            pressure_rate=rate,
            mean_rushers=float(mean_rushers) if mean_rushers is not None else None,
            mean_yards_allowed=yards, bpi=_bpi(rate, yards),
        ))
    defense_ranking.sort(key=lambda r: (-(r.pressure_rate or 0.0), r.defensiveTeam is None,
                                        r.defensiveTeam or ""))

    return BpiSummaryResponse(
        total_plays=total,
        pressure_rate=_rate(total_pressure, total),
        mean_yards_allowed=total_yards,
        groups=groups,
        by_rushers=by_rushers,
        down_distance=down_distance,
        defense_ranking=defense_ranking,
    )
