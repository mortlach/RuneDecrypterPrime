from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_benchmark import (
    PairwiseLateStageRerankerConfig,
    WeightedLateStageRerankerConfig,
    build_frontier_selector_evaluation,
    build_frontier_trial_material_rows,
    build_late_stage_candidate_feature_table,
    build_truth_gap_benchmark_summary,
    build_truth_gap_pattern_rows,
    load_late_stage_frontier_fixture,
    score_pairwise_challenger_margin,
    select_legacy_frontier_winner,
    select_pairwise_frontier_candidate,
    select_weighted_frontier_candidate,
    write_late_stage_selector_stagea_report,
)


pytestmark = pytest.mark.tier_a


FIXTURE_PATH = Path("tests/fixtures/no_wli/v45_seed411_late_frontier_fixture.json")


def _load_fixture() -> dict:
    return load_late_stage_frontier_fixture(FIXTURE_PATH)


def test_v45_fixture_reproduces_legacy_wrong_choice() -> None:
    fixture = _load_fixture()
    feature_rows = build_late_stage_candidate_feature_table(fixture)

    legacy = select_legacy_frontier_winner(
        feature_rows,
        winner_hash=str(fixture["score_selected_winner_hash"]),
    )
    oracle = next(
        row
        for row in feature_rows
        if str(row["candidate_hash"]) == str(fixture["oracle_best_explored_hash"])
    )

    assert str(legacy["candidate_hash"]) == str(fixture["score_selected_winner_hash"])
    assert str(oracle["candidate_hash"]) != str(legacy["candidate_hash"])
    assert float(oracle["final_match"]) > float(legacy["final_match"]) + 0.2
    assert float(oracle["final_score"]) < float(legacy["final_score"])


def test_v45_fixture_revised_selector_prefers_stronger_explored_challenger() -> None:
    fixture = _load_fixture()
    feature_rows = build_late_stage_candidate_feature_table(fixture)

    legacy = select_legacy_frontier_winner(
        feature_rows,
        winner_hash=str(fixture["score_selected_winner_hash"]),
    )
    selected = select_weighted_frontier_candidate(
        feature_rows,
        config=WeightedLateStageRerankerConfig(),
    )

    assert str(selected["candidate_hash"]) != str(legacy["candidate_hash"])
    assert str(selected["lane"]) == "challenger"
    assert float(selected["final_match"]) > float(legacy["final_match"]) + 0.2


def test_v45_fixture_and_benchmark_summary_keep_disagreement_visible() -> None:
    fixture = _load_fixture()
    disagreement = dict(fixture["oracle_truth_disagreement"])

    assert int(disagreement["winner_and_best_truth_differ"]) == 1
    assert str(disagreement["winner_candidate_hash"]) == str(
        fixture["score_selected_winner_hash"]
    )
    assert str(disagreement["best_truth_challenger_candidate_hash"]) == str(
        fixture["oracle_best_explored_hash"]
    )
    assert float(disagreement["truth_gap_best_truth_challenger_vs_winner"]) == pytest.approx(
        0.379
    )
    assert float(disagreement["score_gap_best_truth_challenger_vs_winner"]) < 0.0

    dataset_rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )
    summary = build_truth_gap_benchmark_summary(dataset_rows)

    assert int(summary["row_count"]) >= 1
    assert int(summary["disagreement_row_count"]) >= 1
    assert float(summary["max_truth_gap"]) >= 0.379
    assert "phaseA_selected" in dict(summary["challenger_source_counts"])


def test_frontier_selector_evaluation_reports_rescue_over_legacy() -> None:
    fixture = _load_fixture()

    out = build_frontier_selector_evaluation(
        fixture,
        config=WeightedLateStageRerankerConfig(),
    )

    assert int(out["rescued_from_legacy"]) == 1
    assert str(out["legacy_candidate_hash"]) == str(fixture["score_selected_winner_hash"])
    assert str(out["revised_candidate_hash"]) != str(out["legacy_candidate_hash"])
    assert str(out["pairwise_candidate_hash"]) != str(out["legacy_candidate_hash"])
    assert float(out["revised_truth_match"]) > float(out["legacy_truth_match"])
    assert float(out["pairwise_truth_match"]) > float(out["legacy_truth_match"])
    assert float(out["pairwise_truth_accuracy"]) >= 0.5


def test_frontier_trial_material_rows_keep_replay_shape_visible() -> None:
    fixture = _load_fixture()

    rows = build_frontier_trial_material_rows(fixture)

    assert len(rows) == int(fixture["candidate_count"])
    assert str(rows[0]["candidate_hash"]) == str(fixture["score_selected_winner_hash"])
    assert int(sum(int(row["replay_material_complete"]) for row in rows)) == 0
    assert all(isinstance(row["final_key_idx"], list) for row in rows)
    assert all(isinstance(row["final_plaintext_idx"], list) for row in rows)


def test_pairwise_selector_prefers_better_v45_challenger() -> None:
    fixture = _load_fixture()
    feature_rows = build_late_stage_candidate_feature_table(fixture)
    legacy = select_legacy_frontier_winner(
        feature_rows,
        winner_hash=str(fixture["score_selected_winner_hash"]),
    )
    selected = select_pairwise_frontier_candidate(
        feature_rows,
        winner_hash=str(fixture["score_selected_winner_hash"]),
        config=PairwiseLateStageRerankerConfig(),
    )

    assert str(selected["candidate_hash"]) != str(legacy["candidate_hash"])
    assert float(selected["final_match"]) > float(legacy["final_match"]) + 0.2
    assert float(selected["pairwise_margin_vs_legacy"]) > 0.0


def test_pairwise_margin_prefers_oracle_candidate_over_legacy_winner() -> None:
    fixture = _load_fixture()
    feature_rows = build_late_stage_candidate_feature_table(fixture)
    legacy = select_legacy_frontier_winner(
        feature_rows,
        winner_hash=str(fixture["score_selected_winner_hash"]),
    )
    oracle = next(
        row
        for row in feature_rows
        if str(row["candidate_hash"]) == str(fixture["oracle_best_explored_hash"])
    )

    margin = score_pairwise_challenger_margin(
        oracle,
        legacy,
        config=PairwiseLateStageRerankerConfig(),
    )

    assert float(margin) > 0.0


def test_truth_gap_pattern_rows_collapse_repeated_disagreements() -> None:
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    patterns = build_truth_gap_pattern_rows(rows)

    assert len(patterns) >= 1
    assert int(patterns[0]["count"]) >= 2
    assert str(patterns[0]["winner_candidate_hash"]) == "73eee2bf84b7c07f"
    assert str(patterns[0]["challenger_candidate_hash"]) == "9002ee09917e5a0d"


def test_write_stagea_report_keeps_selector_results_and_trial_rows(tmp_path: Path) -> None:
    fixture = _load_fixture()
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    summary = write_late_stage_selector_stagea_report(
        fixture=fixture,
        truth_gap_rows=rows,
        output_dir=tmp_path,
    )

    assert str(summary["fixture_id"]) == "v45_seed411_late_frontier"
    assert int(summary["dataset_summary"]["disagreement_row_count"]) >= 1
    assert int(summary["selector_evaluation"]["rescued_from_legacy"]) == 1
    assert int(summary["selector_evaluation"]["pairwise_rescued_from_legacy"]) == 1
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "v45_feature_rows.json").exists()
    assert (tmp_path / "v45_trial_material_rows.json").exists()
