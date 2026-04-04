from __future__ import annotations

import math

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.audit_selector_ladder import (
    analyze_stage3_topk_rows,
    summarize_case,
    summarize_tier,
)


def test_analyze_stage3_topk_rows_detects_truth_regret() -> None:
    out = analyze_stage3_topk_rows(
        [
            {"rank": 1, "match_ratio": 0.638, "score_raw": -11.2021},
            {"rank": 2, "match_ratio": 0.638, "score_raw": -11.2084},
            {"rank": 3, "match_ratio": 0.640, "score_raw": -11.2087},
            {"rank": 4, "match_ratio": 0.640, "score_raw": -11.2107},
        ]
    )
    assert out["topk_len"] == 4
    assert math.isclose(out["top_match"], 0.638)
    assert math.isclose(out["best_truth_match"], 0.640)
    assert math.isclose(out["truth_regret"], 0.002)
    assert out["best_truth_rank"] == 3
    assert out["top_is_truth_best"] == 0


def test_summarize_case_reports_best_score_run_and_regret() -> None:
    rows = [
        {
            "tier": "hard",
            "case_id": "fixture_fixture_001_p9_c3_l1000",
            "artifact_relpath": "run_a/final.json",
            "best_match_ratio": 0.773,
            "best_score": 0.3387,
            "stage3_topk_len": 5,
            "stage3_topk_top_is_truth_best": 1,
            "stage3_topk_truth_regret": 0.0,
            "stage3_topk_score_match_spearman": 1.0,
            "stage35_requested_cfg": 0,
            "phasec_enabled_cfg": 0,
        },
        {
            "tier": "hard",
            "case_id": "fixture_fixture_001_p9_c3_l1000",
            "artifact_relpath": "run_b/final.json",
            "best_match_ratio": 0.668,
            "best_score": 0.2864,
            "stage3_topk_len": 5,
            "stage3_topk_top_is_truth_best": 0,
            "stage3_topk_truth_regret": 0.002,
            "stage3_topk_score_match_spearman": 0.7,
            "stage35_requested_cfg": 1,
            "phasec_enabled_cfg": 1,
        },
    ]
    out = summarize_case(rows)
    assert out["artifact_count"] == 2
    assert math.isclose(out["best_match_ratio"], 0.773)
    assert math.isclose(out["best_score"], 0.3387)
    assert math.isclose(out["best_score_run_match_ratio"], 0.773)
    assert math.isclose(out["mean_topk_truth_regret"], 0.001)
    assert math.isclose(out["max_topk_truth_regret"], 0.002)
    assert out["stage35_requested_artifact_count"] == 1
    assert out["phasec_artifact_count"] == 1


def test_summarize_tier_aggregates_selector_regret() -> None:
    rows = [
        {
            "tier": "easy",
            "case_id": "fixture_fixture_001_p5_c1_l1000",
            "best_match_ratio": 1.0,
            "best_score": 0.50,
            "stage3_topk_len": 1,
            "stage3_topk_top_is_truth_best": 1,
            "stage3_topk_truth_regret": 0.0,
            "stage3_topk_score_match_spearman": float("nan"),
            "stage35_requested_cfg": 0,
            "phasec_enabled_cfg": 0,
        },
        {
            "tier": "easy",
            "case_id": "fixture_fixture_001_p5_c3_l1000",
            "best_match_ratio": 1.0,
            "best_score": 0.49,
            "stage3_topk_len": 1,
            "stage3_topk_top_is_truth_best": 1,
            "stage3_topk_truth_regret": 0.0,
            "stage3_topk_score_match_spearman": float("nan"),
            "stage35_requested_cfg": 0,
            "phasec_enabled_cfg": 0,
        },
    ]
    out = summarize_tier(rows)
    assert out["artifact_count"] == 2
    assert out["case_count"] == 2
    assert math.isclose(out["best_match_ratio"], 1.0)
    assert math.isclose(out["topk_truth_best_rate"], 1.0)
    assert math.isclose(out["mean_topk_truth_regret"], 0.0)
