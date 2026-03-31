from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.run_summary import build_summary


pytestmark = pytest.mark.tier_a


def test_build_summary_uses_required_instance_fields() -> None:
    summary = build_summary(
        tiers=[SimpleNamespace(name="fixture_fixture_001_p9_c3_l1000")],
        instances=[
            {
                "tier": "fixture_fixture_001_p9_c3_l1000",
                "best_match_ratio": 0.25,
                "outcome_code": "unsolved",
            },
            {
                "tier": "fixture_fixture_001_p9_c3_l1000",
                "best_match_ratio": 0.75,
                "outcome_code": "solved",
            },
        ],
        solve_match_threshold=0.5,
        derive_outcome_code_fn=lambda **kwargs: "unused",
    )

    tier_summary = summary["tiers"]["fixture_fixture_001_p9_c3_l1000"]
    assert tier_summary["n"] == 2
    assert tier_summary["solved_rate"] == pytest.approx(0.5)
    assert tier_summary["outcome_counts"] == {"solved": 1, "unsolved": 1}


def test_build_summary_rejects_missing_best_match_ratio() -> None:
    with pytest.raises(KeyError, match="best_match_ratio"):
        build_summary(
            tiers=[SimpleNamespace(name="fixture_fixture_001_p9_c3_l1000")],
            instances=[
                {
                    "tier": "fixture_fixture_001_p9_c3_l1000",
                    "outcome_code": "unsolved",
                }
            ],
            solve_match_threshold=0.5,
            derive_outcome_code_fn=lambda **kwargs: "unused",
        )
