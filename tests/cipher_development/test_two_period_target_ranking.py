from __future__ import annotations

import json
from pathlib import Path

import pytest

from cipher_development.two_period_overlay import review_pack
from cipher_development.two_period_overlay.target_ranking import (
    _ciphertext_matches,
    aggregate_terminal_ranking,
    average_ranks,
    latest_completed_target_supply,
    spearman_rank_correlation,
)


def test_ciphertext_comparison_accepts_frozen_json_sequence() -> None:
    assert _ciphertext_matches((1, 2, 3), [1, 2, 3]) is True
    assert _ciphertext_matches((1, 2, 3), [1, 2, 4]) is False


def _terminal(
    rune_matches: int,
    complete_word_matches: int,
    affine_variable_matches: int,
    *,
    exact: bool = False,
) -> dict[str, object]:
    return {
        "rune_matches": rune_matches,
        "complete_word_matches": complete_word_matches,
        "affine_variable_matches": affine_variable_matches,
        "exact_plaintext": exact,
        "canonical_key_equal": exact,
        "combined_shift_equal": exact,
    }


def test_average_ranks_use_average_ties_and_best_rank_one() -> None:
    assert average_ranks([4.0, 2.0, 2.0, 1.0]) == (1.0, 2.5, 2.5, 4.0)
    assert average_ranks([1.0, 2.0, 2.0, 4.0], higher_is_better=False) == (
        1.0,
        2.5,
        2.5,
        4.0,
    )


def test_spearman_rank_correlation_is_tie_aware() -> None:
    assert spearman_rank_correlation([4, 3, 2, 1], [40, 30, 20, 10]) == pytest.approx(1.0)
    assert spearman_rank_correlation([4, 3, 2, 1], [10, 20, 30, 40]) == pytest.approx(-1.0)
    assert spearman_rank_correlation([4, 3, 2, 1], [1, 1, 1, 1]) is None


def test_terminal_ranking_is_aggregate_only() -> None:
    ids = tuple(f"{index:040x}" for index in range(4))
    summary = aggregate_terminal_ranking(
        ids,
        [0.4, 0.3, 0.2, 0.1],
        [
            _terminal(8, 2, 4),
            _terminal(6, 1, 3),
            _terminal(4, 1, 2),
            _terminal(2, 0, 1),
        ],
        top_k_values=(2, 4),
    )

    encoded = json.dumps(summary, sort_keys=True)
    assert summary["candidate_count"] == 4
    assert summary["candidate_specific_truth_emitted"] is False
    assert summary["score_vs_rune_spearman"] == pytest.approx(1.0)
    assert summary["best_rune_candidate_wli_rank"] == 1
    assert summary["top_k"]["2"]["rune_top_k_overlap_count"] == 2
    assert all(candidate_id not in encoded for candidate_id in ids)


def test_terminal_ranking_records_exact_counts_without_identity_leakage() -> None:
    ids = tuple(f"{index + 10:040x}" for index in range(3))
    summary = aggregate_terminal_ranking(
        ids,
        [0.1, 0.3, 0.2],
        [
            _terminal(3, 0, 1),
            _terminal(9, 2, 4, exact=True),
            _terminal(7, 1, 3),
        ],
        top_k_values=(1, 2, 3),
    )

    assert summary["exact_plaintext_count"] == 1
    assert summary["canonical_key_count"] == 1
    assert summary["combined_shift_count"] == 1
    assert summary["top_wli_candidate_terminal"]["exact_plaintext"] is True
    assert summary["best_rune_matches"] == 9
    assert summary["best_rune_candidate_wli_rank"] == 1


def test_latest_target_supply_requires_completed_passed_gate(tmp_path: Path) -> None:
    root = tmp_path / "output/cipher_development/two_period_overlay"
    valid = root / "20260723_100000__two_period_overlay__target_coordinate_supply_v1__abc"
    invalid = root / "20260723_110000__two_period_overlay__target_coordinate_supply_v1__def"
    for run in (valid, invalid):
        (run / "artifacts").mkdir(parents=True)
        (run / "artifacts/experiment_manifest.json").write_text(
            json.dumps({"experiment": {"experiment_id": "target_coordinate_supply_v1"}}),
            encoding="utf-8",
        )
    (valid / "artifacts/experiment_result.json").write_text(
        json.dumps({
            "status": "completed",
            "run_id": valid.name,
            "result_summary": {"target_supply_gate_passed": True},
        }),
        encoding="utf-8",
    )
    (invalid / "artifacts/experiment_result.json").write_text(
        json.dumps({
            "status": "completed",
            "run_id": invalid.name,
            "result_summary": {"target_supply_gate_passed": False},
        }),
        encoding="utf-8",
    )

    assert latest_completed_target_supply(tmp_path) == valid.name


def test_review_pack_requires_complete_target_ranking_surface() -> None:
    required = review_pack._required_artifacts("target_ranking_diagnostic_v1")

    assert "artifacts/source_combined_pool_archive.json" in required
    assert "artifacts/source_combined_diagnostics.json" in required
    assert "artifacts/all_candidates_batch.json" in required
    assert "artifacts/all_candidates_binding.json" in required
    assert "artifacts/all_candidates_replay.json" in required
