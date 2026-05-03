from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    enrich_current_scorer_failure_sidecars_v1 as sidecar_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.enrich_current_scorer_failure_sidecars_v1 import (
    build_readout,
    summarize_sidecar_rows,
    token_diversity_metrics,
    write_sidecar_outputs,
)


pytestmark = pytest.mark.tier_a


def _sidecar_row(**overrides):
    row = {
        "fixture_seed": 1111,
        "search_seed": 7005,
        "run_id": "demo",
        "bundle_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/demo",
        "artifact_path": "output/tools/benchmarks/periodic_sub_trans/no_wli/demo/cases/case.json",
        "winner_candidate_hash": "winner",
        "challenger_candidate_hash": "challenger",
        "winner_truth_match": 0.4,
        "challenger_truth_match": 0.5,
        "truth_gap_challenger_minus_winner": 0.1,
        "winner_current_score": 0.25,
        "challenger_current_score": 0.2,
        "score_gap_challenger_minus_winner": -0.05,
        "winner_source": "stage3_best_phaseB",
        "winner_source_rank": 0,
        "challenger_source": "phaseA_selected",
        "challenger_source_rank": 3,
        "winner_material_available": 1,
        "challenger_material_available": 1,
        "pair_material_available": 1,
        "scorer_sidecar_available": 0,
        "scorer_sidecar_missing_reason": "demo missing scorer",
        "component_that_prefers_truth_better": "",
        "failure_subtype_after_sidecars": "unknown_after_sidecars",
        "winner_text_length": 8,
        "challenger_text_length": 8,
        "winner_char_lm_score": "",
        "challenger_char_lm_score": "",
        "winner_window_mean": "",
        "challenger_window_mean": "",
        "winner_window_worst": "",
        "challenger_window_worst": "",
        "winner_window_lower_quartile": "",
        "challenger_window_lower_quartile": "",
        "winner_window_variance": "",
        "challenger_window_variance": "",
        "winner_span_hamming_score": "",
        "challenger_span_hamming_score": "",
        "winner_word_ngram_judge_score": "",
        "challenger_word_ngram_judge_score": "",
        "winner_repeated_ngram_rate": 0.8,
        "challenger_repeated_ngram_rate": 0.0,
        "winner_unique_token_rate": 0.25,
        "challenger_unique_token_rate": 1.0,
        "winner_entropy_norm": 0.5,
        "challenger_entropy_norm": 1.0,
        "winner_low_diversity_penalty": 0.5,
        "challenger_low_diversity_penalty": 0.0,
        "winner_low_diversity_penalty_preferred": 0,
        "challenger_low_diversity_penalty_preferred": 1,
        "repeated_ngram_rate_prefers_truth_better": 1,
        "low_diversity_penalty_prefers_truth_better": 1,
    }
    row.update(overrides)
    return row


def test_token_diversity_metrics_report_repeated_motif_and_entropy() -> None:
    metrics = token_diversity_metrics([1, 2, 1, 2, 1, 2], ngram_n=2)

    assert int(metrics["text_length"]) == 6
    assert float(metrics["repeated_ngram_rate"]) > 0.0
    assert float(metrics["unique_token_rate"]) == pytest.approx(2 / 6)
    assert 0.0 <= float(metrics["entropy_norm"]) <= 1.0
    assert float(metrics["low_diversity_penalty"]) == pytest.approx(1.0 - float(metrics["entropy_norm"]))


def test_summary_counts_match_sidecar_rows() -> None:
    rows = [
        _sidecar_row(),
        _sidecar_row(
            scorer_sidecar_available=1,
            scorer_sidecar_missing_reason="",
            component_that_prefers_truth_better="repeated_ngram_rate",
            failure_subtype_after_sidecars="local_ngram_overfit",
        ),
    ]

    summary = summarize_sidecar_rows(rows)

    assert int(summary["pair_count"]) == 2
    assert int(summary["pair_material_available_count"]) == 2
    assert int(summary["scorer_sidecar_available_count"]) == 1
    assert int(summary["scorer_sidecar_missing_count"]) == 1
    assert summary["failure_subtype_after_sidecars_counts"]["unknown_after_sidecars"] == 1
    assert summary["failure_subtype_after_sidecars_counts"]["local_ngram_overfit"] == 1


def test_summary_reports_unique_candidate_pairs_and_dominant_pair() -> None:
    rows = [
        _sidecar_row(scorer_sidecar_available=1, scorer_sidecar_missing_reason=""),
        _sidecar_row(scorer_sidecar_available=1, scorer_sidecar_missing_reason=""),
        _sidecar_row(
            winner_candidate_hash="winner-2",
            challenger_candidate_hash="challenger-2",
            scorer_sidecar_available=1,
            scorer_sidecar_missing_reason="",
        ),
    ]

    summary = summarize_sidecar_rows(rows)

    assert int(summary["row_occurrence_count"]) == 3
    assert int(summary["unique_candidate_pair_count"]) == 2
    assert int(summary["unique_enriched_candidate_pair_count"]) == 2
    assert int(summary["dominant_pair_count"]) == 2
    assert int(summary["dominant_enriched_pair_count"]) == 2
    assert float(summary["dominant_enriched_pair_fraction"]) == pytest.approx(2 / 3)


def test_repeated_ngram_and_low_diversity_are_reported_separately() -> None:
    rows = [
        _sidecar_row(
            scorer_sidecar_available=1,
            scorer_sidecar_missing_reason="",
            winner_repeated_ngram_rate=0.8,
            challenger_repeated_ngram_rate=0.1,
            winner_low_diversity_penalty=0.1,
            challenger_low_diversity_penalty=0.2,
            repeated_ngram_rate_prefers_truth_better=1,
            low_diversity_penalty_prefers_truth_better=0,
        )
    ]

    summary = summarize_sidecar_rows(rows)

    assert int(summary["repeated_ngram_rate_truth_better_row_count"]) == 1
    assert int(summary["repeated_ngram_rate_truth_better_unique_pair_count"]) == 1
    assert int(summary["low_diversity_penalty_truth_better_row_count"]) == 0
    assert int(summary["low_diversity_penalty_truth_better_unique_pair_count"]) == 0
    assert summary["repeated_ngram_rate_preference_counts"]["truth_better"] == 1
    assert summary["low_diversity_penalty_preference_counts"]["truth_worse"] == 1


def test_missing_final_plaintext_idx_reason_is_counted() -> None:
    rows = [
        _sidecar_row(
            winner_material_available=0,
            challenger_material_available=0,
            pair_material_available=0,
            scorer_sidecar_available=0,
            scorer_sidecar_missing_reason="missing winner or challenger final_plaintext_idx",
        )
    ]

    summary = summarize_sidecar_rows(rows)

    assert summary["sidecar_missing_reason_counts"]["missing winner or challenger final_plaintext_idx"] == 1
    assert int(summary["missing_candidate_material_count"]) == 1
    assert int(summary["missing_both_material_count"]) == 1


def test_readout_marks_stage_2b_as_selected_truth_gap_slice() -> None:
    rows = [_sidecar_row()]
    summary = summarize_sidecar_rows(rows)

    readout = build_readout(rows, summary)

    assert "Stage 2b enrichment for the selected truth-gap slice" in readout
    assert "not a runtime scorer change" in readout


def test_write_sidecar_outputs_uses_expected_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sidecar_mod, "REPO_ROOT", tmp_path)
    out_dir = tmp_path / "current_scorer_failure_sidecars_v1"

    summary = write_sidecar_outputs(rows=[_sidecar_row()], output_dir=out_dir)

    assert int(summary["pair_count"]) == 1
    assert (out_dir / "current_scorer_failure_sidecar_rows.csv").exists()
    assert (out_dir / "current_scorer_failure_sidecar_rows.jsonl").exists()
    assert (out_dir / "current_scorer_failure_sidecar_summary.json").exists()
    assert (out_dir / "current_scorer_failure_sidecar_readout.md").exists()
