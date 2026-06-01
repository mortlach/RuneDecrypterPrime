from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    design_phaseB_ngram_hamming_nonproduction_scorer_v1 as design,
)


def _require_source_artifacts() -> None:
    source_manifest = Path(design.REPO_ROOT) / design.SOURCE_OUTPUT_REL / "pilot_manifest.json"
    if not source_manifest.exists():
        pytest.skip(f"requires generated source artifact: {source_manifest.relative_to(design.REPO_ROOT).as_posix()}")


def test_nonproduction_scorer_design_preserves_claim_bounds() -> None:
    _require_source_artifacts()
    payload = design.build_design()
    manifest = payload["manifest"]

    assert manifest["status"] == "review_ready"
    assert manifest["claim_mode"] == "hard_pair_candidate_comparability"
    assert manifest["scorer_design_only"] is True
    assert manifest["production_scorer_changes"] is False
    assert manifest["controlled_damage_ladder_claim"] is False
    assert manifest["full_hard_pair_report"] is False


def test_nonproduction_scorer_design_uses_p2_as_primary_and_p0_as_audit() -> None:
    _require_source_artifacts()
    payload = design.build_design()
    manifest = payload["manifest"]
    rows = payload["candidate_design_rows"]

    assert manifest["primary_design"]["primary_profile_id"] == "P2_conservative_len8_hd2"
    assert manifest["primary_design"]["control_profile_id"] == "P0_exact_short"
    assert manifest["primary_design"]["p0_usage"] == "audit/control only"
    assert len(rows) == 118
    assert any(row["primary_score_raw_weighted_hits"] > 0.0 for row in rows)
    assert manifest["summary"]["p0_audit_flag_count"] == 1


def test_nonproduction_scorer_design_captures_known_better_separation() -> None:
    _require_source_artifacts()
    payload = design.build_design()
    role_rows = {
        row["known_better_or_worse_role"]: row
        for row in payload["role_design_rows"]
    }

    assert role_rows["known_better"]["mean_primary_score"] > role_rows["known_worse"]["mean_primary_score"]
    assert role_rows["known_better"]["candidate_hit_rate"] > role_rows["known_worse"]["candidate_hit_rate"]


def test_nonproduction_scorer_design_keeps_rescue_claim_blocked() -> None:
    _require_source_artifacts()
    payload = design.build_design()
    manifest = payload["manifest"]
    rescue_rows = payload["panel_rescue_inspection_rows"]

    assert len(rescue_rows) == 20
    assert manifest["summary"]["panel_rescue_candidates_with_primary_hits"] == 0
    assert all(row["primary_hit_count"] == 0 for row in rescue_rows)


def test_nonproduction_scorer_design_outputs_are_serialisable() -> None:
    _require_source_artifacts()
    payload = design.build_design()

    assert payload["stratum_design_rows"]
    assert payload["role_design_rows"]
    assert payload["candidate_design_rows"]
    json.dumps(payload, sort_keys=True)
