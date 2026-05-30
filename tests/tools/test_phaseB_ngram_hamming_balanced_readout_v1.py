from __future__ import annotations

import json

from rune_decrypter_prime.scoring.ngram_hamming.fast_backend import fast_ngram_hamming_available
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_balanced_readout_v1 as pilot,
)


def test_exact_no_cap_pilot_requires_cpp_backend() -> None:
    assert fast_ngram_hamming_available()


def test_exact_no_cap_pilot_claim_mode_and_bounds() -> None:
    config = pilot.build_config()

    assert config["run_mode"] == "balanced_readout"
    assert config["claim_mode"] == "hard_pair_candidate_comparability"
    assert config["dictionary_cuts"] == ["normal"]
    assert config["orders"] == [2]
    assert config["profiles"] == [
        "P0_exact_short",
        "P1_word_analogue_len7_hd2",
        "P2_conservative_len8_hd2",
    ]
    assert config["max_candidates"] == 120
    assert config["max_chunks_total"] == 240
    assert config["max_chunks_per_candidate"] == 2
    assert config["full_pilot_target_candidates"] == 120
    assert config["full_pilot_target_chunks_per_candidate"] == 2
    assert config["full_pilot_target_cell_count"] == 720
    assert config["max_wallclock_seconds"] == 600.0
    assert config["early_projection_check_cells"] == 30
    assert config["early_projection_stop_seconds"] == 600.0
    assert config["backend_impl"] == "cpp_fast"
    assert config["python_fallback_allowed"] is False
    assert config["no_hit_cap"] is True


def test_exact_no_cap_pilot_preflight_verifies_hard_pair_stream_without_damage_ladder_claim() -> None:
    context = pilot.load_manifest_context()
    preflight = context["preflight"]
    selection = context["selection"]

    assert len(selection["selected_candidates"]) <= pilot.MAX_CANDIDATES
    assert len(selection["selected_candidates"]) >= 110
    assert preflight["claim_mode"] == "hard_pair_candidate_comparability"
    assert preflight["hard_pair_candidate_stream_verified"] is True
    assert preflight["controlled_damage_stream_verified"] is False
    assert preflight["candidate_full_texts_used_as_primary_scan_source"] is False
    assert preflight["blocked"] is False
    assert preflight["blocked_reasons"] == []
    assert all(row["verified"] for row in preflight["candidate_checks"])
    assert all(row["candidate_full_texts_rehashed_match"] is True for row in preflight["candidate_checks"])


def test_exact_no_cap_pilot_selection_records_reasons() -> None:
    context = pilot.load_manifest_context()
    selected = context["selection"]["selected_candidates"]

    required = {
        "candidate_id",
        "selected_stratum",
        "source_pair_id",
        "known_better_or_worse_role",
        "current_score",
        "truth_match_ratio",
        "pair_occurrence_count",
        "chunk_count_available",
        "selection_status",
    }
    assert len(selected) <= pilot.MAX_CANDIDATES
    assert len(selected) >= 110
    assert all(required.issubset(row) for row in selected)
    assert all(row["selection_status"] == "selected" for row in selected)
    assert all(row["chunk_count_available"] >= pilot.MAX_CHUNKS_PER_CANDIDATE for row in selected)


def test_exact_no_cap_microbatch_projection_uses_attempts() -> None:
    projection = pilot.attempt_weighted_projection(
        [
            {
                "verification_attempts": 100,
                "elapsed_seconds": 1.0,
            },
            {"verification_attempts": 100, "elapsed_seconds": 1.0},
            {"verification_attempts": 100, "elapsed_seconds": 1.0},
            {"verification_attempts": 100, "elapsed_seconds": 1.0},
            {"verification_attempts": 100, "elapsed_seconds": 1.0},
            {"verification_attempts": 100, "elapsed_seconds": 1.0},
        ]
    )

    assert projection["measured_attempts"] == 600
    assert projection["measured_attempts_per_second"] == 100
    assert projection["full_pilot_target_cell_count"] == 720
    assert projection["attempt_weighted_full_pilot_attempts"] == 72000
    assert projection["attempt_weighted_full_pilot_projected_seconds"] == 720


def test_exact_no_cap_pilot_phrase_manifest_is_json_serialisable() -> None:
    _, phrase_manifest = pilot.load_phrase_entries()

    assert phrase_manifest["dictionary_cut"] == "normal"
    assert phrase_manifest["orders"] == [2]
    assert all(count > 0 for count in phrase_manifest["entry_counts_by_order"].values())
    json.dumps(phrase_manifest, sort_keys=True)


def test_balanced_readout_selection_has_target_strata() -> None:
    context = pilot.load_manifest_context()
    status_rows = context["selection"]["stratum_status_rows"]

    assert len(context["selection"]["selected_candidates"]) <= pilot.MAX_CANDIDATES
    assert len(context["selection"]["selected_candidates"]) >= 110
    assert {row["selected_stratum"] for row in status_rows} == {
        "known_better_pair_candidate",
        "known_worse_pair_candidate",
        "panel_rescue_known_better",
        "panel_break_known_worse",
        "bad_control_candidate",
        "high_truth_stable_fill",
    }
    shortfalls = [row for row in status_rows if row["selection_status"] != "selected"]
    assert len(shortfalls) <= 1
    assert all(row["selected_count"] >= 18 for row in status_rows)


def test_bounded_expansion_adds_p2_nonzero_parity_case() -> None:
    context = pilot.load_manifest_context()
    entries_by_order, _ = pilot.load_phrase_entries()
    tokens = pilot.load_selected_tokens(context["preflight"])

    parity_rows = pilot.run_required_pre_scan_parity(
        context["selection"]["selected_candidates"],
        context["chunk_rows_by_candidate"],
        tokens,
        entries_by_order,
    )

    p2_rows = [row for row in parity_rows if row["parity_case"] == "p2_order2_real_nonzero_hit_chunk"]
    assert len(p2_rows) == 1
    assert p2_rows[0]["profile_id"] == "P2_conservative_len8_hd2"
    assert p2_rows[0]["ngram_order"] == 2
    assert p2_rows[0]["fast_hit_count"] > 0
    assert p2_rows[0]["parity_match"] is True
