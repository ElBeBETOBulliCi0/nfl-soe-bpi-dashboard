"""Property tests for expected separation and SOE (Properties 3 and 4).

Seeded numpy generators, 100+ iterations each, no hypothesis.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.metrics import FALLBACK_MIN_SAMPLES, assign_expected_separation  # noqa: E402

ITERATIONS = 120
COVERAGES = ["Cover-1", "Cover-2", "Cover-3", "Quarters"]
COVERAGE_TYPES = ["Zone", "Man", "Other"]
POSITIONS = ["WR", "TE", "RB"]


def _random_routes(rng: np.random.Generator, n_rows: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pff_passCoverage": rng.choice(COVERAGES, n_rows),
            "pff_passCoverageType": rng.choice(COVERAGE_TYPES, n_rows),
            "pff_positionLinedUp": rng.choice(POSITIONS, n_rows),
            "separation": rng.uniform(0.0, 15.0, n_rows),
        }
    )


def test_property_3_expected_separation_is_group_mean_and_soe_centered():
    """**Validates: Requirements 3.1, 3.2**

    With every primary group at or above the threshold, expected_separation equals
    the primary group mean and SOE averages to zero within each group.
    """
    rng = np.random.default_rng(20240301)
    for _ in range(ITERATIONS):
        n_groups = int(rng.integers(1, 5))
        frames = []
        for g in range(n_groups):
            size = int(rng.integers(FALLBACK_MIN_SAMPLES, FALLBACK_MIN_SAMPLES + 25))
            frames.append(
                pd.DataFrame(
                    {
                        "pff_passCoverage": COVERAGES[g],
                        "pff_passCoverageType": rng.choice(COVERAGE_TYPES, size),
                        "pff_positionLinedUp": POSITIONS[int(rng.integers(0, len(POSITIONS)))],
                        "separation": rng.uniform(0.0, 15.0, size),
                    }
                )
            )
        routes = pd.concat(frames, ignore_index=True)
        out = assign_expected_separation(routes)

        keys = ["pff_passCoverage", "pff_positionLinedUp"]
        for _, grp in out.groupby(keys):
            if len(grp) < FALLBACK_MIN_SAMPLES:
                continue
            np.testing.assert_allclose(grp["expected_separation"], grp["separation"].mean())
            assert abs(grp["soe"].mean()) < 1e-9
        np.testing.assert_allclose(
            out["soe"], out["separation"] - out["expected_separation"]
        )


def test_property_4_fallback_to_coverage_type_when_primary_group_small():
    """**Validates: Requirements 3.3**

    Rows whose primary group has fewer than FALLBACK_MIN_SAMPLES samples take the
    mean of their (pff_passCoverageType, pff_positionLinedUp) group.
    """
    rng = np.random.default_rng(20240302)
    for _ in range(ITERATIONS):
        n_rows = int(rng.integers(5, 120))
        routes = _random_routes(rng, n_rows)
        out = assign_expected_separation(routes)

        primary_keys = ["pff_passCoverage", "pff_positionLinedUp"]
        fallback_keys = ["pff_passCoverageType", "pff_positionLinedUp"]
        counts = routes.groupby(primary_keys)["separation"].transform("size")
        primary_mean = routes.groupby(primary_keys)["separation"].transform("mean")
        fallback_mean = routes.groupby(fallback_keys)["separation"].transform("mean")
        expected = np.where(counts >= FALLBACK_MIN_SAMPLES, primary_mean, fallback_mean)

        np.testing.assert_allclose(out["expected_separation"].to_numpy(), expected)
        small = (counts < FALLBACK_MIN_SAMPLES).to_numpy()
        np.testing.assert_allclose(
            out.loc[small, "expected_separation"].to_numpy(), fallback_mean[small].to_numpy()
        )


def test_property_4_threshold_boundary():
    """**Validates: Requirements 3.3**

    A primary group of exactly 15 uses its own mean; 14 falls back.
    """
    rng = np.random.default_rng(20240303)
    for _ in range(ITERATIONS):
        for size, use_primary in ((FALLBACK_MIN_SAMPLES, True), (FALLBACK_MIN_SAMPLES - 1, False)):
            target = pd.DataFrame(
                {
                    "pff_passCoverage": "Cover-3",
                    "pff_passCoverageType": "Zone",
                    "pff_positionLinedUp": "WR",
                    "separation": rng.uniform(0.0, 15.0, size),
                }
            )
            other = pd.DataFrame(
                {
                    "pff_passCoverage": "Cover-2",
                    "pff_passCoverageType": "Zone",
                    "pff_positionLinedUp": "WR",
                    "separation": rng.uniform(0.0, 15.0, 5),
                }
            )
            routes = pd.concat([target, other], ignore_index=True)
            out = assign_expected_separation(routes)
            got = out["expected_separation"].iloc[:size]
            want = target["separation"].mean() if use_primary else routes["separation"].mean()
            np.testing.assert_allclose(got, want)
