from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    interpret_phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1 as interp,
)


def _require_source_artifacts() -> None:
    source_manifest = Path(interp.REPO_ROOT) / interp.SOURCE_OUTPUT_REL / "pilot_manifest.json"
    if not source_manifest.exists():
        pytest.skip(f"requires generated source artifact: {source_manifest.relative_to(interp.REPO_ROOT).as_posix()}")


def test_sample_index_matrix_interpretation_preserves_claim_bounds() -> None:
    _require_source_artifacts()
    payload = interp.build_interpretation()
    manifest = payload["manifest"]

    assert manifest["status"] == "review_ready"
    assert manifest["dataset_status"] == "sample_index_confirmed"
    assert manifest["sample_index_based"] is True
    assert manifest["full_raw_ngram_rebuild_confirmed"] is False
    assert manifest["production_scorer_changes"] is False
    assert manifest["controlled_damage_ladder_claim"] is False


def test_sample_index_matrix_interpretation_evaluates_all_pairs() -> None:
    _require_source_artifacts()
    payload = interp.build_interpretation()
    manifest = payload["manifest"]

    assert manifest["summary"]["candidate_count"] == 604
    assert manifest["summary"]["pair_count"] == 2594
    assert len(payload["pairwise_score_rows"]) == 2594


def test_sample_index_matrix_interpretation_reports_score_modes() -> None:
    _require_source_artifacts()
    payload = interp.build_interpretation()
    manifest = payload["manifest"]

    assert manifest["score_modes"] == [
        "current_score_only",
        "p2_raw_weighted_hits_only",
        "current_score_plus_log1p_p2",
        "gated_current_plus_log1p_p2",
    ]
    assert manifest["summary"]["p2_pair_known_better_rate"] >= 0.0
    assert manifest["summary"]["gated_combo_pair_known_better_rate"] >= 0.0


def test_sample_index_matrix_interpretation_keeps_rescue_claim_blocked() -> None:
    _require_source_artifacts()
    payload = interp.build_interpretation()
    manifest = payload["manifest"]

    assert manifest["summary"]["panel_rescue_candidate_count"] == 20
    assert manifest["summary"]["panel_rescue_p2_hit_candidate_count"] == 0


def test_sample_index_matrix_interpretation_outputs_are_serialisable() -> None:
    _require_source_artifacts()
    payload = interp.build_interpretation()

    assert payload["candidate_score_rows"]
    assert payload["pairwise_mode_summary_rows"]
    assert payload["contrast_rows"]
    json.dumps(payload, sort_keys=True)
