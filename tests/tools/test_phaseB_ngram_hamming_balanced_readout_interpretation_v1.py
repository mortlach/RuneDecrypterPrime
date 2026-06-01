from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    interpret_phaseB_ngram_hamming_balanced_readout_v1 as interp,
)


def _require_source_artifacts() -> None:
    source_manifest = Path(interp.REPO_ROOT) / interp.SOURCE_OUTPUT_REL / "pilot_manifest.json"
    if not source_manifest.exists():
        pytest.skip(f"requires generated source artifact: {source_manifest.relative_to(interp.REPO_ROOT).as_posix()}")


def test_balanced_readout_interpretation_preserves_claim_bounds() -> None:
    _require_source_artifacts()
    payload = interp.build_interpretation()
    manifest = payload["manifest"]

    assert manifest["status"] == "pass"
    assert manifest["claim_mode"] == "hard_pair_candidate_comparability"
    assert manifest["broad_pilot"] is False
    assert manifest["full_hard_pair_report"] is False
    assert manifest["production_scorer_changes"] is False
    assert manifest["controlled_damage_ladder_claim"] is False


def test_balanced_readout_interpretation_captures_key_separation() -> None:
    _require_source_artifacts()
    payload = interp.build_interpretation()
    manifest = payload["manifest"]

    assert manifest["summary"]["source_candidates"] == 118
    assert manifest["summary"]["source_total_hits"] == 328
    assert manifest["summary"]["known_better_mean_hits"] > manifest["summary"]["known_worse_mean_hits"]
    assert manifest["summary"]["panel_rescue_known_better_hits"] == 0
    assert manifest["summary"]["p0_positive_chunk_count"] == 1


def test_balanced_readout_interpretation_outputs_are_serialisable() -> None:
    _require_source_artifacts()
    payload = interp.build_interpretation()

    assert payload["stratum_decision_rows"]
    assert payload["role_decision_rows"]
    assert payload["profile_redundancy_rows"]
    json.dumps(payload, sort_keys=True)
