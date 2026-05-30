from __future__ import annotations

import json

from rune_decrypter_prime.scoring.ngram_hamming.fast_backend import fast_ngram_hamming_available
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_exact_no_cap_pilot_v1 as pilot,
)


def test_exact_no_cap_pilot_requires_cpp_backend() -> None:
    assert fast_ngram_hamming_available()


def test_exact_no_cap_pilot_claim_mode_and_bounds() -> None:
    config = pilot.build_config()

    assert config["run_mode"] == "microbatch_sizing"
    assert config["claim_mode"] == "hard_pair_candidate_comparability"
    assert config["dictionary_cuts"] == ["normal"]
    assert config["orders"] == [2, 3]
    assert config["profiles"] == [
        "P0_exact_short",
        "P1_word_analogue_len7_hd2",
        "P2_conservative_len8_hd2",
    ]
    assert config["max_candidates"] == 1
    assert config["max_chunks_total"] == 1
    assert config["max_chunks_per_candidate"] == 1
    assert config["full_pilot_target_candidates"] == 10
    assert config["full_pilot_target_chunks_per_candidate"] == 2
    assert config["full_pilot_target_cell_count"] == 120
    assert config["backend_impl"] == "cpp_fast"
    assert config["python_fallback_allowed"] is False
    assert config["no_hit_cap"] is True


def test_exact_no_cap_pilot_preflight_verifies_hard_pair_stream_without_damage_ladder_claim() -> None:
    context = pilot.load_manifest_context()
    preflight = context["preflight"]
    selection = context["selection"]

    assert len(selection["selected_candidates"]) == pilot.MAX_CANDIDATES
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
    assert len(selected) == pilot.MAX_CANDIDATES
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
    assert projection["full_pilot_target_cell_count"] == 120
    assert projection["attempt_weighted_full_pilot_attempts"] == 12000
    assert projection["attempt_weighted_full_pilot_projected_seconds"] == 120


def test_exact_no_cap_pilot_phrase_manifest_is_json_serialisable() -> None:
    _, phrase_manifest = pilot.load_phrase_entries()

    assert phrase_manifest["dictionary_cut"] == "normal"
    assert phrase_manifest["orders"] == [2, 3]
    assert all(count > 0 for count in phrase_manifest["entry_counts_by_order"].values())
    json.dumps(phrase_manifest, sort_keys=True)
