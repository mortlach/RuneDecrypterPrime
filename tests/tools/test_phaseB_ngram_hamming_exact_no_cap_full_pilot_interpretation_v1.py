from __future__ import annotations

import json

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    interpret_phaseB_ngram_hamming_exact_no_cap_full_pilot_v1 as interp,
)


def test_full_pilot_interpretation_preserves_claim_boundaries() -> None:
    payload = interp.build_manifest()
    manifest = payload["manifest"]

    assert manifest["status"] == "pass"
    assert manifest["claim_mode"] == "hard_pair_candidate_comparability"
    assert manifest["broad_pilot"] is False
    assert manifest["full_hard_pair_report"] is False
    assert manifest["production_scorer_changes"] is False
    assert manifest["controlled_damage_ladder_claim"] is False
    assert manifest["forbidden_claims_made"] == []


def test_full_pilot_interpretation_hit_totals_match_review_gate() -> None:
    payload = interp.build_manifest()
    manifest = payload["manifest"]

    assert manifest["hit_summary"]["total_hits"] == 14
    assert manifest["hit_summary"]["candidates_with_hits"] == 3
    assert manifest["hit_summary"]["candidates_with_zero_hits"] == 7
    assert manifest["hit_summary"]["productive_profile_orders"] == [
        "P1_word_analogue_len7_hd2|order2",
        "P2_conservative_len8_hd2|order2",
    ]


def test_full_pilot_interpretation_summary_rows_are_serialisable() -> None:
    payload = interp.build_manifest()

    assert payload["summary_by_candidate"]
    assert payload["summary_by_profile_order"]
    assert payload["summary_by_stratum"]
    assert payload["summary_by_chunk"]
    assert len(payload["enriched_hit_examples"]) == 14
    json.dumps(payload, sort_keys=True)
