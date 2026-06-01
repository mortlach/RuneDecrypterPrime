from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    simulate_phaseB_ngram_hamming_nonproduction_scorer_combination_v1 as sim,
)


def _require_source_artifacts() -> None:
    source_manifest = Path(sim.REPO_ROOT) / sim.SOURCE_OUTPUT_REL / "design_manifest.json"
    if not source_manifest.exists():
        pytest.skip(f"requires generated source artifact: {source_manifest.relative_to(sim.REPO_ROOT).as_posix()}")


def test_nonproduction_combination_preserves_claim_bounds() -> None:
    _require_source_artifacts()
    payload = sim.build_simulation()
    manifest = payload["manifest"]

    assert manifest["status"] == "review_ready"
    assert manifest["claim_mode"] == "hard_pair_candidate_comparability"
    assert manifest["scorer_design_only"] is True
    assert manifest["production_scorer_changes"] is False
    assert manifest["controlled_damage_ladder_claim"] is False
    assert manifest["full_hard_pair_report"] is False


def test_nonproduction_combination_has_required_score_modes() -> None:
    _require_source_artifacts()
    payload = sim.build_simulation()
    manifest = payload["manifest"]
    rows = payload["candidate_score_rows"]

    assert manifest["score_modes"] == [
        "current_score_only",
        "p2_raw_weighted_hits_only",
        "current_score_plus_log1p_p2",
    ]
    assert len(rows) == 118
    assert all("current_score_plus_log1p_p2_rank" in row for row in rows)


def test_nonproduction_combination_reports_required_separations() -> None:
    _require_source_artifacts()
    payload = sim.build_simulation()
    manifest = payload["manifest"]

    assert manifest["summary"]["p2_known_better_vs_known_worse_mean_margin"] > 0.0
    assert manifest["summary"]["combo_known_better_vs_known_worse_mean_margin"] > 0.0
    assert manifest["summary"]["p2_high_truth_vs_bad_control_mean_margin"] > 0.0
    assert manifest["summary"]["combo_high_truth_vs_bad_control_mean_margin"] > 0.0


def test_nonproduction_combination_keeps_panel_rescue_blocked() -> None:
    _require_source_artifacts()
    payload = sim.build_simulation()
    manifest = payload["manifest"]

    assert manifest["summary"]["panel_rescue_candidate_count"] == 20
    assert manifest["summary"]["panel_rescue_candidates_with_p2_hits"] == 0
    assert all(row["primary_hit_count"] == 0 for row in payload["panel_rescue_rows"])


def test_nonproduction_combination_reports_inversions() -> None:
    _require_source_artifacts()
    payload = sim.build_simulation()
    pair_rows = payload["pair_inversion_rows"]
    contrast_rows = payload["contrast_rows"]

    assert pair_rows
    assert any(row["score_mode"] == "current_score_plus_log1p_p2" for row in pair_rows)
    assert any(row["undesired_pairwise_inversions"] >= 0 for row in contrast_rows)
    json.dumps(payload, sort_keys=True)
