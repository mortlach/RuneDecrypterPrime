from __future__ import annotations

import math
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    audit_partial_state_signal as audit_mod,
)


pytestmark = pytest.mark.tier_a


def _mock_artifact() -> dict[str, object]:
    return {
        "best_match_ratio": 0.8,
        "best_score": 0.35,
        "key_seed": 511,
        "target_plaintext_idx": [0, 1, 2, 3],
        "stage2_topk": [
            {
                "rank": 1,
                "match_ratio": 0.10,
                "score_stage2": 0.12,
                "score_judge": 0.15,
            }
        ],
        "stage3_topk": [
            {
                "rank": 1,
                "match_ratio": 0.76,
                "score_judge": 0.33,
                "score_pct": 0.29,
                "score_raw": -10.5,
                "plaintext_idx": [0, 1, 2, 3],
            }
        ],
        "stage35_seed_rows": [
            {
                "score": 0.34,
                "search_score": -10.4,
                "checkpoint_final_score": 0.33,
                "checkpoint_final_match": 0.77,
                "plaintext_idx": [0, 1, 2, 3],
            }
        ],
        "stage35_archive": [
            {
                "score": 0.36,
                "search_score": -10.3,
                "plaintext_idx": [0, 1, 2, 3],
            }
        ],
    }


def test_extract_partial_state_rows_includes_stage35_truth_from_plaintext(tmp_path: Path) -> None:
    artifact = _mock_artifact()
    path = tmp_path / "run" / "final_instances" / "artifact.json"
    path.parent.mkdir(parents=True)

    rows = audit_mod.extract_partial_state_rows(artifact, path=path, label="seed511_stage35_win")

    kinds = {str(row["state_kind"]) for row in rows}
    assert {"stage2_topk", "stage3_topk", "stage35_seed", "stage35_archive"} <= kinds
    archive_rows = [row for row in rows if str(row["state_kind"]) == "stage35_archive"]
    assert len(archive_rows) == 1
    assert math.isclose(float(archive_rows[0]["truth_match"]), 1.0)


def test_summarize_signal_detects_strong_vs_weak_separation() -> None:
    rows = [
        {
            "run_label": "strong_a",
            "state_kind": "stage3_topk",
            "row_id": "a1",
            "truth_match": 0.78,
            "score_judge": 0.34,
            "final_best_match": 0.79,
            "final_best_score": 0.35,
            "run_quality_bucket": "strong",
        },
        {
            "run_label": "strong_a",
            "state_kind": "stage3_topk",
            "row_id": "a2",
            "truth_match": 0.76,
            "score_judge": 0.33,
            "final_best_match": 0.79,
            "final_best_score": 0.35,
            "run_quality_bucket": "strong",
        },
        {
            "run_label": "weak_b",
            "state_kind": "stage3_topk",
            "row_id": "b1",
            "truth_match": 0.58,
            "score_judge": 0.21,
            "final_best_match": 0.57,
            "final_best_score": 0.24,
            "run_quality_bucket": "weak",
        },
        {
            "run_label": "weak_b",
            "state_kind": "stage3_topk",
            "row_id": "b2",
            "truth_match": 0.55,
            "score_judge": 0.20,
            "final_best_match": 0.57,
            "final_best_score": 0.24,
            "run_quality_bucket": "weak",
        },
    ]

    out = audit_mod.summarize_signal(rows, state_kind="stage3_topk", signal_field="score_judge")
    assert out["run_count"] == 2
    assert out["strong_run_count"] == 1
    assert out["weak_run_count"] == 1
    assert math.isclose(float(out["top_signal_is_best_truth_rate"]), 1.0)
    assert math.isclose(float(out["mean_truth_regret"]), 0.0)
    assert int(out["strong_above_weak_no_overlap"]) == 1
    assert float(out["strong_minus_weak_separation_gap"]) > 0.0
