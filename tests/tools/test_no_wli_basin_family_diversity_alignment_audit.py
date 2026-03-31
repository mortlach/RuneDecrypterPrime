from __future__ import annotations

import math
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import (
    audit_basin_family_diversity_alignment as audit_mod,
)


pytestmark = pytest.mark.tier_a


def _row(
    row_id: str,
    key_idx: list[int],
    *,
    truth_match: float = float("nan"),
    score_judge: float = float("nan"),
    score: float = float("nan"),
) -> dict[str, object]:
    return {
        "row_id": row_id,
        "key_idx": key_idx,
        "truth_match": truth_match,
        "score_judge": score_judge,
        "score": score,
        "candidate_hash": "",
    }


def test_cluster_family_ids_groups_near_tail_by_hamming() -> None:
    rows = [
        _row("a", [1, 2, 3, 4]),
        _row("b", [5, 6, 3, 5]),
        _row("c", [7, 8, 9, 9]),
    ]
    assignments, unassigned = audit_mod.cluster_family_ids(
        rows,
        family_view={"id": "near_tail_h1", "kind": "near_tail", "tail_hamming_max": 1},
        columns=2,
    )
    assert unassigned == 0
    assert assignments["a"] == assignments["b"]
    assert assignments["a"] != assignments["c"]


def test_summarize_family_block_reports_selected_vs_available() -> None:
    rows = [
        _row("a", [1, 2, 3, 4], score_judge=0.9),
        _row("b", [5, 6, 3, 4], score_judge=0.8),
        _row("c", [7, 8, 9, 9], score_judge=0.7),
        _row("d", [0, 1, 9, 9], score_judge=0.6),
    ]
    out = audit_mod.summarize_family_block(
        rows,
        family_view={"id": "exact_tail", "kind": "exact_tail"},
        columns=2,
        selected_row_ids=["a", "b"],
    )
    assert out["family_count"] == 2
    assert out["selected_top_band_family_count"] == 1
    assert math.isclose(float(out["top_band_family_mass_share"]), 0.5)


def test_summarize_pool_alignment_separates_within_and_between_family_regret() -> None:
    rows = [
        _row("top_bad", [1, 1, 1, 1], truth_match=0.40, score_judge=0.90),
        _row("top_bad_2", [1, 1, 1, 2], truth_match=0.45, score_judge=0.80),
        _row("good", [9, 9, 9, 9], truth_match=0.70, score_judge=0.70),
    ]
    out = audit_mod.summarize_pool_alignment(
        rows,
        pool_name="stage3_topk",
        family_view={"id": "near_tail_h1", "kind": "near_tail", "tail_hamming_max": 1},
        columns=2,
    )
    assert math.isclose(float(out["selected_row_truth"]), 0.40)
    assert math.isclose(float(out["selected_family_truth"]), 0.45)
    assert math.isclose(float(out["best_family_truth"]), 0.70)
    assert math.isclose(float(out["within_family_regret"]), 0.05)
    assert math.isclose(float(out["between_family_regret"]), 0.25)


def test_extract_pool_rows_handles_missing_optional_artifacts(tmp_path: Path) -> None:
    artifact = {
        "columns": 2,
        "target_plaintext_idx": [0, 1, 2, 3],
        "stage2_topk": [
            {
                "key_idx": [1, 2, 3, 4],
                "match_ratio": 0.1,
                "score_stage2": 0.2,
                "score_judge": 0.3,
            }
        ],
        "stage3_topk": [
            {
                "key_idx": [1, 2, 3, 4],
                "match_ratio": 0.6,
                "score_judge": 0.7,
                "score_raw": -10.0,
            }
        ],
    }
    run_dir = tmp_path / "run"
    artifact_path = run_dir / "final_instances" / "artifact.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("{}", encoding="utf-8")

    out = audit_mod._extract_pool_rows(artifact, artifact_path=artifact_path, bundle_dir=None)
    assert "stage2_topk" in out
    assert "stage3_topk" in out
    assert "phasec_start" not in out


def test_classify_run_summary_detects_absent_vs_undervalued() -> None:
    absent = audit_mod.classify_run_summary(
        final_best_match=0.57,
        latest_alignment={
            "between_family_regret": 0.0,
            "within_family_regret": 0.0,
        },
        best_seen_truth=0.58,
        earliest_best_truth=0.58,
        latest_best_truth=0.58,
        reference_best_match=0.637,
        is_reference_success=False,
    )
    undervalued = audit_mod.classify_run_summary(
        final_best_match=0.041,
        latest_alignment={
            "between_family_regret": 0.379,
            "within_family_regret": 0.0,
        },
        best_seen_truth=0.418,
        earliest_best_truth=0.418,
        latest_best_truth=0.418,
        reference_best_match=0.596,
        is_reference_success=False,
    )
    assert absent["primary_failure_mode"] == "good_family_absent"
    assert undervalued["primary_failure_mode"] == "good_family_undervalued"
    assert float(undervalued["classification_confidence"]) > float(
        absent["classification_confidence"]
    )
