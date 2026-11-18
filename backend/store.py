"""In-memory store for the precomputed SOE and BPI CSV files.

The files are read once at startup. A missing, empty or unreadable file is
replaced by an empty frame with the expected columns, so no request path
raises because of absent data.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROUTES_FILE = "soe_routes.csv"
RELEASES_FILE = "play_release_frames.csv"
BPI_FILE = "bpi_plays.csv"

ROUTES_COLUMNS = [
    "gameId", "playId", "nflId", "displayName", "pff_positionLinedUp",
    "pff_passCoverage", "pff_passCoverageType", "separation",
    "expected_separation", "soe", "is_likely_target",
]
# Optional context columns appended by the preprocessor. Missing ones become NA.
ROUTES_EXTRA_COLUMNS = ["week", "possessionTeam", "defensiveTeam"]
RELEASES_COLUMNS = ["gameId", "playId", "frameId"]
# play_release_frames.csv holds many rows per play (all players and the ball at the
# release frame). Only the first three columns are required in practice.
FRAMES_COLUMNS = [
    "gameId", "playId", "frameId", "nflId", "displayName", "club", "team",
    "x", "y", "is_ball", "pff_role", "pff_positionLinedUp",
]
BPI_COLUMNS = [
    "gameId", "playId", "num_rushers", "is_pressure", "down", "yardsToGo",
    "distance_bucket",
]
BPI_EXTRA_COLUMNS = [
    "defensiveTeam", "pff_passCoverage", "pff_passCoverageType",
    "playResult", "passResult", "playDescription",
]

_READ_ERRORS = (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with Python-native objects where NaN/NaT/NA become None."""
    out = df.astype(object)
    return out.where(df.notna(), None)


def clean_records(df: pd.DataFrame) -> list[dict]:
    """Rows as dicts with NaN converted to None, ready for Pydantic models."""
    return clean(df).to_dict(orient="records")


def _to_bool(series: pd.Series) -> pd.Series:
    """Normalize 'True'/'False' strings (or real booleans) to bool; anything else is False."""
    text = series.astype(str).str.strip().str.lower()
    return text.eq("true")


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in columns})


def _read(path: Path, columns: list[str]) -> tuple[pd.DataFrame, bool]:
    """Read one CSV; return (frame, ok). On any read failure return an empty frame."""
    try:
        df = pd.read_csv(path)
    except _READ_ERRORS:
        return _empty(columns), False
    except (OSError, UnicodeDecodeError, ValueError):
        return _empty(columns), False
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns].copy(), True


def _int_ids(df: pd.DataFrame, id_cols: list[str]) -> pd.DataFrame:
    """Coerce id columns to int64, dropping rows whose ids are missing or invalid."""
    for col in id_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=id_cols).copy()
    for col in id_cols:
        df[col] = df[col].astype("int64")
    return df.reset_index(drop=True)


def _numeric(df: pd.DataFrame, cols: list[str]) -> None:
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")


def _text(df: pd.DataFrame, cols: list[str]) -> None:
    for col in cols:
        df[col] = df[col].astype(object).where(df[col].notna(), None)


def _prepare_routes(df: pd.DataFrame) -> pd.DataFrame:
    df = _int_ids(df, ["gameId", "playId", "nflId"])
    _numeric(df, ["separation", "expected_separation", "soe", "week"])
    _text(df, ["displayName", "pff_positionLinedUp", "pff_passCoverage", "pff_passCoverageType",
               "possessionTeam", "defensiveTeam"])
    df["is_likely_target"] = _to_bool(df["is_likely_target"]).astype(bool)
    return df


def _prepare_frames(df: pd.DataFrame) -> pd.DataFrame:
    """Full release-frame table: many rows per play, ids as int64, nflId nullable (ball)."""
    df = _int_ids(df, ["gameId", "playId", "frameId"])
    df["nflId"] = pd.to_numeric(df["nflId"], errors="coerce").astype("Int64")
    _numeric(df, ["x", "y"])
    _text(df, ["displayName", "club", "team", "pff_role", "pff_positionLinedUp"])
    df["is_ball"] = _to_bool(df["is_ball"]).astype(bool)
    return df


def _release_table(frames: pd.DataFrame) -> pd.DataFrame:
    """One (gameId, playId, frameId) row per play, deduplicated, lowest frameId kept."""
    base = frames[RELEASES_COLUMNS].sort_values(RELEASES_COLUMNS, kind="stable")
    return base.drop_duplicates(subset=["gameId", "playId"], keep="first").reset_index(drop=True)


def _prepare_bpi(df: pd.DataFrame) -> pd.DataFrame:
    df = _int_ids(df, ["gameId", "playId", "num_rushers"])
    _numeric(df, ["down", "yardsToGo"])
    _text(df, ["distance_bucket", "defensiveTeam", "pff_passCoverage", "pff_passCoverageType",
               "passResult", "playDescription"])
    _numeric(df, ["playResult"])
    df["is_pressure"] = _to_bool(df["is_pressure"]).astype(bool)
    return df


class DataStore:
    """Holds the three precomputed tables and the query helpers used by the routers."""

    def __init__(
        self,
        routes: pd.DataFrame | None = None,
        frames: pd.DataFrame | None = None,
        bpi: pd.DataFrame | None = None,
        data_loaded: bool = False,
    ) -> None:
        self.routes = routes if routes is not None else _prepare_routes(
            _empty(ROUTES_COLUMNS + ROUTES_EXTRA_COLUMNS))
        # Full table: all players and the ball at the release frame, many rows per play.
        self.frames = frames if frames is not None else _prepare_frames(_empty(FRAMES_COLUMNS))
        # One row per play (gameId, playId, frameId).
        self.releases = _release_table(self.frames)
        self.bpi = bpi if bpi is not None else _prepare_bpi(
            _empty(BPI_COLUMNS + BPI_EXTRA_COLUMNS))
        self.data_loaded = data_loaded

    @classmethod
    def load(cls, directory: Path | str) -> "DataStore":
        """Read the three CSVs once. Never raises for missing, empty or malformed files."""
        directory = Path(directory)
        routes, ok_routes = _read(directory / ROUTES_FILE, ROUTES_COLUMNS + ROUTES_EXTRA_COLUMNS)
        frames, ok_frames = _read(directory / RELEASES_FILE, FRAMES_COLUMNS)
        bpi, ok_bpi = _read(directory / BPI_FILE, BPI_COLUMNS + BPI_EXTRA_COLUMNS)
        return cls(
            routes=_prepare_routes(routes),
            frames=_prepare_frames(frames),
            bpi=_prepare_bpi(bpi),
            data_loaded=ok_routes and ok_frames and ok_bpi,
        )

    # ------------------------------------------------------------------ queries

    def filter_routes(
        self,
        only_targets: bool | None = None,
        coverage: str | None = None,
        coverage_type: str | None = None,
        position: str | None = None,
        require_release: bool = False,
        team: str | None = None,
        week: int | None = None,
        team_side: str = "defense",
        search: str | None = None,
    ) -> pd.DataFrame:
        """AND of equality masks over routes.

        ``team`` matches ``defensiveTeam`` (``team_side="defense"``, used by the
        heatmap) or ``possessionTeam`` (``team_side="offense"``, used by the player
        ranking). ``week`` matches the game week. ``search`` is a case-insensitive
        substring of ``displayName``.

        With ``require_release=True`` only routes of plays that have a row in
        ``releases`` are kept. /api/soe/plays uses this so every listed play has
        a matching frame in play_release_frames.
        """
        df = self.routes
        mask = pd.Series(True, index=df.index)
        if team is not None:
            col = "possessionTeam" if team_side == "offense" else "defensiveTeam"
            mask &= df[col] == team
        if week is not None:
            mask &= df["week"] == week
        if search:
            mask &= df["displayName"].fillna("").str.contains(search, case=False, regex=False)
        if only_targets:
            mask &= df["is_likely_target"]
        if coverage is not None:
            mask &= df["pff_passCoverage"] == coverage
        if coverage_type is not None:
            mask &= df["pff_passCoverageType"] == coverage_type
        if position is not None:
            mask &= df["pff_positionLinedUp"] == position
        out = df[mask]
        if require_release:
            out = self.with_release(out)
        return out

    def with_release(self, routes: pd.DataFrame) -> pd.DataFrame:
        """Keep only route rows whose (gameId, playId) has a release frame."""
        keys = self.releases[["gameId", "playId"]]
        return routes.merge(keys, on=["gameId", "playId"], how="inner")

    def release_frame(self, game_id: int, play_id: int) -> int | None:
        """frameId for a play from the release table, or None when absent."""
        rel = self.releases
        hit = rel[(rel["gameId"] == game_id) & (rel["playId"] == play_id)]
        if hit.empty:
            return None
        return int(hit["frameId"].iloc[0])

    def play_frames(self, game_id: int, play_id: int) -> pd.DataFrame:
        """All frame rows (every player and the ball) of one play at its release frame."""
        fr = self.frames
        rows = fr[(fr["gameId"] == game_id) & (fr["playId"] == play_id)]
        frame_id = self.release_frame(game_id, play_id)
        if frame_id is not None:
            rows = rows[rows["frameId"] == frame_id]
        return rows.reset_index(drop=True)

    def play_context(self, keys: pd.DataFrame) -> pd.DataFrame:
        """playDescription, passResult and playResult for each (gameId, playId) in ``keys``.

        Returns one row per input key, in the same order. Plays absent from the BPI
        table, or columns absent from it, yield None.
        """
        cols = ["playDescription", "passResult", "playResult"]
        base = keys[["gameId", "playId"]].reset_index(drop=True)
        ctx = self.bpi.reindex(columns=["gameId", "playId"] + cols)
        ctx = ctx.drop_duplicates(["gameId", "playId"])
        out = base.merge(ctx, on=["gameId", "playId"], how="left")
        for col in cols:
            if col not in out.columns:
                out[col] = None
        return out[["gameId", "playId"] + cols].astype(object).where(
            out[["gameId", "playId"] + cols].notna(), None)

    def filter_bpi(
        self,
        down: int | None = None,
        distance_bucket: str | None = None,
        num_rushers: int | None = None,
        coverage: str | None = None,
        team: str | None = None,
    ) -> pd.DataFrame:
        """AND of equality masks over BPI plays. ``coverage`` matches pff_passCoverage
        and ``team`` matches defensiveTeam."""
        df = self.bpi
        mask = pd.Series(True, index=df.index)
        if coverage is not None:
            mask &= df["pff_passCoverage"] == coverage
        if team is not None:
            mask &= df["defensiveTeam"] == team
        if down is not None:
            mask &= df["down"] == down
        if distance_bucket is not None:
            mask &= df["distance_bucket"] == distance_bucket
        if num_rushers is not None:
            mask &= df["num_rushers"] == num_rushers
        return df[mask]

    def filter_values(self) -> dict[str, list]:
        """Sorted distinct non-null values for each filter field."""

        def distinct(series: pd.Series) -> list:
            return sorted(series.dropna().unique().tolist())

        return {
            "pff_passCoverage": distinct(self.routes["pff_passCoverage"]),
            "pff_passCoverageType": distinct(self.routes["pff_passCoverageType"]),
            "pff_positionLinedUp": distinct(self.routes["pff_positionLinedUp"]),
            "distance_bucket": distinct(self.bpi["distance_bucket"]),
            "down": [int(v) for v in distinct(self.bpi["down"])],
            "week": [int(v) for v in distinct(self.routes["week"])],
            "team": sorted(
                set(distinct(self.routes["defensiveTeam"]))
                | set(distinct(self.routes["possessionTeam"]))
                | set(distinct(self.bpi["defensiveTeam"]))
            ),
        }
