"""Property tests for metrics (seeded numpy, plain pytest loops, no hypothesis)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.metrics import build_bpi_plays, distance_bucket, is_likely_target

N_ITER = 100

_FIRST = ["Tyreek", "Davante", "Cooper", "Justin", "Amon-Ra", "CeeDee", "A.J."]
_LAST = ["Hill", "Adams", "Kupp", "Jefferson", "St. Brown", "Lamb", "Brown", "O'Neal"]


def _random_case(rng: np.random.Generator, text: str) -> str:
    return "".join(c.upper() if rng.random() < 0.5 else c.lower() for c in text)


# Feature: soe-bpi-backend, Property 5: Likely target matches surname case-insensitively
def test_property_5_likely_target_matches_surname_case_insensitive():
    """**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 16.5**"""
    seed = 5005
    rng = np.random.default_rng(seed)
    for it in range(N_ITER):
        first = _FIRST[rng.integers(len(_FIRST))]
        last = _LAST[rng.integers(len(_LAST))]
        name = f"{first} {last}"
        surname = name.split()[-1]
        msg = f"seed={seed} iter={it} name={name!r}"

        # Description containing the surname in random case -> True.
        desc = f"(12:00) Q.B. pass short right to {_random_case(rng, surname)} for 8 yards."
        assert is_likely_target(name, desc) is True, msg

        # Description built without the surname -> False.
        other = "ZZZ Qqq"
        assert is_likely_target(name, f"pass incomplete intended for {other}.") is False, msg

        # Empty and missing descriptions -> False.
        assert is_likely_target(name, "") is False, msg
        assert is_likely_target(name, None) is False, msg

        # Empty and missing names -> False.
        assert is_likely_target("", desc) is False, msg
        assert is_likely_target(None, desc) is False, msg
        assert is_likely_target("   ", desc) is False, msg

    # Single-token name uses that token as surname.
    assert is_likely_target("Madonna", "pass to madonna") is True


def _random_bpi_inputs(rng: np.random.Generator):
    n_plays = int(rng.integers(1, 12))
    pff_rows = []
    plays_rows = []
    for p in range(n_plays):
        game_id = int(rng.integers(1, 4))
        play_id = p + 1  # unique per (game, play) because play ids are unique
        plays_rows.append(
            {
                "gameId": game_id,
                "playId": play_id,
                "down": int(rng.integers(1, 5)),
                "yardsToGo": int(rng.integers(1, 21)),
            }
        )
        n_players = int(rng.integers(3, 12))
        for k in range(n_players):
            role = rng.choice(["Pass Rush", "Pass Block", "Coverage", "Pass"])
            row = {"gameId": game_id, "playId": play_id, "nflId": 1000 * play_id + k, "pff_role": role}
            for col in ("pff_hit", "pff_hurry", "pff_sack"):
                r = rng.random()
                row[col] = np.nan if r < 0.3 else (1.0 if r < 0.45 else 0.0)
            pff_rows.append(row)
    return pd.DataFrame(pff_rows), pd.DataFrame(plays_rows)


# Feature: soe-bpi-backend, Property 6: BPI play rows match rusher data
def test_property_6_bpi_play_rows_match_rusher_data():
    """**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**"""
    seed = 6006
    rng = np.random.default_rng(seed)
    for it in range(N_ITER):
        pff, plays = _random_bpi_inputs(rng)
        msg = f"seed={seed} iter={it}"
        result = build_bpi_plays(pff, plays)

        assert list(result.columns) == [
            "gameId", "playId", "num_rushers", "is_pressure",
            "down", "yardsToGo", "distance_bucket",
        ], msg

        # Reference computed with explicit loops.
        expected = {}
        for _, r in pff.iterrows():
            if r["pff_role"] != "Pass Rush":
                continue
            key = (int(r["gameId"]), int(r["playId"]))
            count, pressure = expected.get(key, (0, False))
            hit = any(
                (not pd.isna(r[c])) and r[c] == 1 for c in ("pff_hit", "pff_hurry", "pff_sack")
            )
            expected[key] = (count + 1, pressure or hit)

        got_keys = list(zip(result["gameId"].astype(int), result["playId"].astype(int)))
        assert len(got_keys) == len(set(got_keys)), msg
        assert set(got_keys) == set(expected), msg
        assert got_keys == sorted(got_keys), msg

        plays_idx = plays.set_index(["gameId", "playId"])
        for _, row in result.iterrows():
            key = (int(row["gameId"]), int(row["playId"]))
            n, pressure = expected[key]
            assert int(row["num_rushers"]) == n, msg
            assert bool(row["is_pressure"]) == pressure, msg
            assert int(row["down"]) == int(plays_idx.loc[key, "down"]), msg
            ytg = plays_idx.loc[key, "yardsToGo"]
            assert row["yardsToGo"] == ytg, msg
            assert row["distance_bucket"] == distance_bucket(ytg), msg

        # Pressure rate per bucket stays within [0, 1].
        if not result.empty:
            rates = result.groupby("distance_bucket", dropna=False)["is_pressure"].mean()
            assert ((rates >= 0) & (rates <= 1)).all(), msg
            overall = float(result["is_pressure"].mean())
            assert 0.0 <= overall <= 1.0, msg


def test_property_6_no_rushers_gives_empty_frame():
    """**Validates: Requirements 6.1**"""
    pff = pd.DataFrame(
        {"gameId": [1], "playId": [1], "nflId": [1], "pff_role": ["Coverage"],
         "pff_hit": [1.0], "pff_hurry": [1.0], "pff_sack": [1.0]}
    )
    plays = pd.DataFrame({"gameId": [1], "playId": [1], "down": [1], "yardsToGo": [10]})
    assert build_bpi_plays(pff, plays).empty


# Feature: soe-bpi-backend, Property 7: Distance bucket boundaries
def test_property_7_distance_bucket_boundaries():
    """**Validates: Requirements 6.5**"""
    fixed = {
        1: "Corto", 3: "Corto", 4: "Medio", 7: "Medio", 8: "Largo",
        0: None, -1: None, -10: None, float("nan"): None, None: None,
    }
    for value, expected in fixed.items():
        assert distance_bucket(value) == expected, f"value={value!r}"
    assert distance_bucket(3.5) == "Medio"
    assert distance_bucket(0.5) is None

    seed = 7007
    rng = np.random.default_rng(seed)
    for it in range(N_ITER):
        msg = f"seed={seed} iter={it}"
        v = int(rng.integers(-5, 60))
        got = distance_bucket(v)
        if v < 1:
            assert got is None, msg
        elif v <= 3:
            assert got == "Corto", msg
        elif v <= 7:
            assert got == "Medio", msg
        else:
            assert got == "Largo", msg
        f = float(rng.uniform(-5, 60))
        got_f = distance_bucket(f)
        if f < 1:
            assert got_f is None, msg
        elif f <= 3:
            assert got_f == "Corto", msg
        elif f <= 7:
            assert got_f == "Medio", msg
        else:
            assert got_f == "Largo", msg
