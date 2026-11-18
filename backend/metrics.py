"""Pure metric functions for SOE and BPI, shared by the preprocessor and the tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

FALLBACK_MIN_SAMPLES = 15

PRIMARY_EVENT = "pass_forward"
FALLBACK_EVENT = "autoevent_passforward"


def select_release_frames(tracking: pd.DataFrame) -> pd.DataFrame:
    """Return one row per play (gameId, playId, frameId) with its release frame.

    ``pass_forward`` wins over ``autoevent_passforward``. Plays with neither event
    are absent. When the chosen event repeats, the minimum ``frameId`` is used.
    """
    columns = ["gameId", "playId", "frameId"]
    if tracking.empty:
        return pd.DataFrame({c: pd.Series(dtype="int64") for c in columns})

    keys = ["gameId", "playId"]
    primary = (
        tracking.loc[tracking["event"] == PRIMARY_EVENT, columns]
        .groupby(keys, as_index=False)["frameId"]
        .min()
    )
    fallback = (
        tracking.loc[tracking["event"] == FALLBACK_EVENT, columns]
        .groupby(keys, as_index=False)["frameId"]
        .min()
    )
    if not primary.empty and not fallback.empty:
        primary_keys = pd.MultiIndex.from_frame(primary[keys])
        fallback_keys = pd.MultiIndex.from_frame(fallback[keys])
        fallback = fallback.loc[~fallback_keys.isin(primary_keys)]

    result = pd.concat([primary, fallback], ignore_index=True)
    result = result.sort_values(keys, kind="stable").reset_index(drop=True)
    return result[columns].astype("int64")


def compute_separation(route_xy: np.ndarray, cover_xy: np.ndarray) -> np.ndarray:
    """Minimum Euclidean distance from each route point to any coverage point.

    ``route_xy`` has shape (R, 2) and ``cover_xy`` has shape (C, 2). Returns shape (R,).
    When there are no coverage rows, returns an empty array of shape (0,).
    """
    route = np.asarray(route_xy, dtype=float).reshape(-1, 2)
    cover = np.asarray(cover_xy, dtype=float).reshape(-1, 2)
    if cover.shape[0] == 0:
        return np.empty(0, dtype=float)
    diff = route[:, None, :] - cover[None, :, :]
    distances = np.sqrt((diff ** 2).sum(axis=-1))
    return distances.min(axis=1)


def assign_expected_separation(routes: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``routes`` with ``expected_separation`` and ``soe`` added.

    Primary key is ``(pff_passCoverage, pff_positionLinedUp)``. Rows whose primary
    group has fewer than ``FALLBACK_MIN_SAMPLES`` samples take the mean of their
    ``(pff_passCoverageType, pff_positionLinedUp)`` group instead.
    Missing key values are kept as their own group (``dropna=False``).
    """
    result = routes.copy()
    if result.empty:
        result["expected_separation"] = pd.Series(dtype="float64")
        result["soe"] = pd.Series(dtype="float64")
        return result

    primary_keys = ["pff_passCoverage", "pff_positionLinedUp"]
    fallback_keys = ["pff_passCoverageType", "pff_positionLinedUp"]

    primary_group = result.groupby(primary_keys, dropna=False)["separation"]
    primary_mean = primary_group.transform("mean")
    primary_count = primary_group.transform("size")
    fallback_mean = result.groupby(fallback_keys, dropna=False)["separation"].transform("mean")

    result["expected_separation"] = np.where(
        primary_count >= FALLBACK_MIN_SAMPLES, primary_mean, fallback_mean
    ).astype(float)
    result["soe"] = result["separation"] - result["expected_separation"]
    return result


def is_likely_target(display_name: str | None, play_description: str | None) -> bool:
    """True when the surname (last whitespace token of ``display_name``) appears in
    ``play_description``, ignoring case. Empty or missing values give False."""
    if not isinstance(display_name, str) or not isinstance(play_description, str):
        return False
    tokens = display_name.split()
    if not tokens or not play_description:
        return False
    return tokens[-1].lower() in play_description.lower()


def distance_bucket(yards_to_go) -> str | None:
    """Corto for 1..3, Medio for 4..7, Largo for 8 or more, None for missing, NaN or < 1."""
    if yards_to_go is None:
        return None
    try:
        value = float(yards_to_go)
    except (TypeError, ValueError):
        return None
    if np.isnan(value) or value < 1:
        return None
    if value <= 3:
        return "Corto"
    if value <= 7:
        return "Medio"
    return "Largo"


def build_bpi_plays(pff: pd.DataFrame, plays: pd.DataFrame) -> pd.DataFrame:
    """One row per play with at least one ``Pass Rush`` player.

    Columns: gameId, playId, num_rushers, is_pressure, down, yardsToGo, distance_bucket.
    Missing ``pff_hit``, ``pff_hurry`` and ``pff_sack`` count as not equal to 1.
    """
    columns = [
        "gameId", "playId", "num_rushers", "is_pressure",
        "down", "yardsToGo", "distance_bucket",
    ]
    keys = ["gameId", "playId"]
    rushers = pff.loc[pff["pff_role"] == "Pass Rush"].copy()
    if rushers.empty:
        return pd.DataFrame({c: pd.Series(dtype="object") for c in columns}).astype(
            {"gameId": "int64", "playId": "int64", "num_rushers": "int64", "is_pressure": "bool"}
        )

    hit = pd.Series(False, index=rushers.index)
    for col in ("pff_hit", "pff_hurry", "pff_sack"):
        if col in rushers.columns:
            hit = hit | (pd.to_numeric(rushers[col], errors="coerce") == 1)
    rushers["_pressure"] = hit

    grouped = rushers.groupby(keys, as_index=False).agg(
        num_rushers=("pff_role", "size"), is_pressure=("_pressure", "any")
    )
    situation = plays[keys + ["down", "yardsToGo"]].drop_duplicates(keys)
    result = grouped.merge(situation, on=keys, how="left")
    result["distance_bucket"] = result["yardsToGo"].map(distance_bucket)
    result = result.sort_values(keys, kind="stable").reset_index(drop=True)
    result["num_rushers"] = result["num_rushers"].astype("int64")
    result["is_pressure"] = result["is_pressure"].astype(bool)
    return result[columns]
