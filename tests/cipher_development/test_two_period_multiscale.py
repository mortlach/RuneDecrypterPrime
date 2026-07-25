from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from cipher_development.two_period_overlay.config import (
    CRIB_RUNES,
    EXACT_EXTRA_CRIB_BENCHMARKS,
    SCORING_CONTRACT,
    TARGET_BENCHMARK,
    benchmark_for,
)
from cipher_development.two_period_overlay.keyspace import crib_space, deterministic_key, expand
from cipher_development.two_period_overlay.replay import make_replay_context
from cipher_development.two_period_overlay.multiscale import (
    _aggregate_signal_terminal,
    _score_only_candidate_signals,
)
from cipher_development.two_period_overlay.scorer_profiles import (
    J1,
    RECORDED_J0,
    SCORER_PANEL,
    effective_family_weights,
    portable_contract,
    profile_for,
    weighting_contract_note,
)


def _ciphertext_for_declared_cribs(benchmark):
    key = deterministic_key(benchmark)
    ciphertext = np.zeros(benchmark.text_length, dtype=np.uint8)
    for crib in benchmark.crib_specs:
        for offset, plain in enumerate(crib.runes):
            pos = crib.start + offset
            ciphertext[pos] = (
                int(plain)
                + int(key[pos % benchmark.period_a])
                + int(key[benchmark.period_a + pos % benchmark.period_b])
            ) % benchmark.alphabet_size
    return key, ciphertext


def test_multiscale_panel_is_small_predeclared_and_deterministic() -> None:
    assert [profile.profile_id for profile in SCORER_PANEL] == [
        "j0_recorded_char34_wli34",
        "s1_char12",
        "s2_wli12",
        "s3_char12_wli12",
        "b1_char23_wli23",
        "j1_char34_wli34",
        "f1_char1234_wli1234",
    ]
    assert profile_for(J1.profile_id) is J1
    first = [profile.to_json_dict() for profile in SCORER_PANEL]
    second = [profile.to_json_dict() for profile in SCORER_PANEL]
    assert first == second
    assert len({profile.profile_id for profile in SCORER_PANEL}) == len(SCORER_PANEL)


def test_recorded_baseline_is_preserved_and_weight_mismatch_is_explicit() -> None:
    assert portable_contract(RECORDED_J0.scoring_contract()) == portable_contract(SCORING_CONTRACT)
    assert effective_family_weights(RECORDED_J0.scoring_contract()) == {
        "character": 0.5,
        "wli": 0.5,
    }
    assert effective_family_weights(J1.scoring_contract()) == {
        "character": 0.25,
        "wli": 0.75,
    }
    note = weighting_contract_note()
    assert note["affected_item"].startswith("WP6 C.5")
    assert "do not alter core scorer runtime" in note["replacement_action"]


def test_combined_profiles_encode_family_weights_in_per_order_maps() -> None:
    contract = J1.scoring_contract()
    assert contract["weights"] == [0.25, 0.75]
    assert contract["char_weights"] == {3: 0.125, 4: 0.125}
    assert contract["wli_weights"] == {3: 0.375, 4: 0.375}


def test_exact_extra_crib_benchmarks_are_registered_but_not_added_to_ladder() -> None:
    assert [benchmark.expected_free_dimension for benchmark in EXACT_EXTRA_CRIB_BENCHMARKS] == [8, 8]
    assert [benchmark.additional_cribs[0].start for benchmark in EXACT_EXTRA_CRIB_BENCHMARKS] == [206, 81]
    assert all(benchmark.additional_cribs[0].word == "dormouse" for benchmark in EXACT_EXTRA_CRIB_BENCHMARKS)
    for benchmark in EXACT_EXTRA_CRIB_BENCHMARKS:
        assert benchmark_for(benchmark.benchmark_id) is benchmark
        assert benchmark.to_json_dict()["additional_cribs"][0]["rune_length"] == 8


def test_offsets_206_and_81_each_reduce_d16_to_d8_and_reconstruct_key() -> None:
    for benchmark in EXACT_EXTRA_CRIB_BENCHMARKS:
        key, ciphertext = _ciphertext_for_declared_cribs(benchmark)
        particular, basis, free = crib_space(
            ciphertext,
            np.asarray(CRIB_RUNES, dtype=np.uint8),
            benchmark,
        )
        variables = np.asarray([key[index] for index in free], dtype=np.uint8)
        assert len(free) == benchmark.expected_free_dimension == 8
        assert TARGET_BENCHMARK.expected_free_dimension - len(free) == 8
        assert basis.shape == (benchmark.key_length, 8)
        assert np.array_equal(expand(variables, particular, basis, benchmark), key)


def test_base_replay_context_shape_remains_compatible() -> None:
    particular = np.zeros(TARGET_BENCHMARK.key_length, dtype=np.uint8)
    basis = np.zeros(
        (TARGET_BENCHMARK.key_length, TARGET_BENCHMARK.expected_free_dimension),
        dtype=np.uint8,
    )
    search_case = SimpleNamespace(
        benchmark=TARGET_BENCHMARK,
        ciphertext=np.zeros(TARGET_BENCHMARK.text_length, dtype=np.uint8),
        wli=tuple((0, 1) for _ in range(TARGET_BENCHMARK.text_length)),
        crib=np.asarray(CRIB_RUNES, dtype=np.uint8),
        particular=particular,
        basis=basis,
        free_columns=tuple(range(TARGET_BENCHMARK.expected_free_dimension)),
        scoring_contract=J1.scoring_contract(),
    )
    context = make_replay_context(
        search_case,
        run_id="test_run",
        configuration_hash="0" * 40,
        evaluator_provenance={"schema": "test"},
        decision_score=J1.score_name,
        evaluator_id="test_multiscale",
    )
    assert context.payload["decision_score"] == J1.score_name
    assert context.payload["benchmark"] == TARGET_BENCHMARK.to_json_dict()
    assert context.payload["scoring"]["char_weights"] == {"3": 0.125, "4": 0.125}


def test_score_only_candidate_signals_are_frozen_without_terminal_metrics() -> None:
    candidate_ids = [f"candidate_{index:02d}" for index in range(20)]
    rankings = {profile.profile_id: list(candidate_ids) for profile in SCORER_PANEL}
    rankings["s1_char12"] = [candidate_ids[18], *candidate_ids[:18], candidate_ids[19]]
    rankings["s2_wli12"] = [candidate_ids[19], *candidate_ids[:18], candidate_ids[18]]
    rankings["s3_char12_wli12"] = [candidate_ids[18], candidate_ids[19], *candidate_ids[:18]]
    rankings["b1_char23_wli23"] = [candidate_ids[17], *candidate_ids[:17], candidate_ids[18], candidate_ids[19]]
    rankings["j1_char34_wli34"] = [*candidate_ids[:17], candidate_ids[18], candidate_ids[19], candidate_ids[17]]

    signals = _score_only_candidate_signals(rankings)

    assert candidate_ids[18] in signals["low_order_rescued_from_recorded_j0"]
    assert candidate_ids[19] in signals["low_order_rescued_from_recorded_j0"]
    assert candidate_ids[17] in signals["bridge_top8_dropped_by_j1"]
    assert candidate_ids[19] in signals["wli12_favoured_over_char12"]
    assert candidate_ids[18] in signals["char12_favoured_over_wli12"]


def test_signal_terminal_diagnostics_are_aggregate_only() -> None:
    candidate_ids = ("a", "b", "c")
    metrics = (
        {"rune_matches": 10, "complete_word_matches": 1, "affine_variable_matches": 0, "exact_plaintext": False},
        {"rune_matches": 20, "complete_word_matches": 2, "affine_variable_matches": 1, "exact_plaintext": False},
        {"rune_matches": 30, "complete_word_matches": 3, "affine_variable_matches": 2, "exact_plaintext": True},
    )
    result = _aggregate_signal_terminal(
        candidate_ids, metrics, {"rescued": ("b", "c"), "empty": ()}
    )

    assert result["rescued"]["candidate_count"] == 2
    assert result["rescued"]["rune_match_summary"]["maximum"] == 30.0
    assert result["rescued"]["exact_plaintext_count"] == 1
    assert result["empty"] == {"candidate_count": 0}
    assert "candidate_ids" not in result["rescued"]


def test_review_pack_contracts_cover_all_pack01_experiments(tmp_path) -> None:
    import json
    import cipher_development.two_period_overlay.review_pack as review_pack

    expected = {
        "multiscale_scorer_contract_canary_v1": "artifacts/scorer_contract_canary.json",
        "multiscale_static_panel_v1": "artifacts/static_panel_summary.json",
        "exact_extra_crib_contract_canary_v1": "artifacts/exact_extra_crib_contracts.json",
    }
    for experiment_id, artifact in expected.items():
        assert artifact in review_pack._required_artifacts(experiment_id)

    run = tmp_path / "run"
    payload = {
        "asset_provenance": {
            "asset_manifest_complete": True,
            "language_model_assets": [
                {"logical_path": "contract_0/example", "sha256": "a" * 64, "size_bytes": 1}
            ],
        }
    }
    path = run / "artifacts/scorer_contract_canary.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert review_pack._asset_provenance(run) == payload["asset_provenance"]
