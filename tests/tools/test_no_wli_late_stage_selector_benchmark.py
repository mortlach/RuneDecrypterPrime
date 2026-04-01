from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_benchmark import (
    PairwiseLateStageRerankerConfig,
    WeightedLateStageRerankerConfig,
    build_frontier_challenger_vs_winner_case_summary,
    build_stagea_unrecovered_case_feature_audit,
    build_stagea_categorical_field_ablation_sweep,
    build_disagreement_frontier_pattern_audit,
    build_disagreement_frontier_row_audit,
    build_frontier_selector_evaluation,
    build_frontier_trial_material_rows,
    build_late_stage_candidate_feature_table,
    build_stagea_weighted_robustness_sweep,
    build_stagea_numeric_field_ablation_sweep,
    build_stagea_rescued_vs_unrecovered_contrast,
    build_stagea_weighted_ablation_sweep,
    build_stagea_data_realism_summary,
    build_stagea_feature_story,
    build_truth_gap_benchmark_summary,
    build_truth_gap_pattern_rows,
    build_weighted_ablation_configs,
    build_weighted_categorical_ablation_configs,
    build_weighted_numeric_ablation_configs,
    build_weighted_score_plus_lexical_config,
    build_weighted_score_plus_novelty_plus_init_score_config,
    build_weighted_score_plus_novelty_plus_init_search_score_config,
    build_weighted_score_plus_novelty_plus_phaseb_topk_penalty_config,
    build_weighted_score_plus_novelty_plus_source_penalties_config,
    build_weighted_score_plus_novelty_plus_stage3_best_phaseb_penalty_config,
    build_weighted_score_plus_novelty_plus_score_gap_to_anchor_config,
    build_weighted_score_plus_novelty_plus_score_gap_to_winner_config,
    build_weighted_score_plus_novelty_config,
    build_weighted_score_plus_novelty_plus_lexical_config,
    build_weighted_score_only_config,
    build_weighted_margin_explanation,
    build_pairwise_margin_explanation,
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


def test_weighted_score_only_keeps_v45_legacy_winner() -> None:
    fixture = _load_fixture()
    feature_rows = build_late_stage_candidate_feature_table(fixture)

    selected = select_weighted_frontier_candidate(
        feature_rows,
        config=build_weighted_score_only_config(),
    )

    assert str(selected["candidate_hash"]) == str(fixture["score_selected_winner_hash"])


def test_weighted_margin_explanation_shows_structural_group_drives_rescue() -> None:
    fixture = _load_fixture()
    feature_rows = build_late_stage_candidate_feature_table(fixture)
    legacy = select_legacy_frontier_winner(
        feature_rows,
        winner_hash=str(fixture["score_selected_winner_hash"]),
    )
    weighted = select_weighted_frontier_candidate(
        feature_rows,
        config=WeightedLateStageRerankerConfig(),
    )

    out = build_weighted_margin_explanation(
        weighted,
        legacy,
        config=WeightedLateStageRerankerConfig(),
    )

    assert str(out["dominant_positive_group"]) == "structural_features"
    assert float(out["group_totals"]["structural_features"]) > 0.0
    assert float(out["group_totals"]["score_features"]) < 0.0


def test_pairwise_margin_explanation_shows_structural_group_drives_rescue() -> None:
    fixture = _load_fixture()
    feature_rows = build_late_stage_candidate_feature_table(fixture)
    legacy = select_legacy_frontier_winner(
        feature_rows,
        winner_hash=str(fixture["score_selected_winner_hash"]),
    )
    pairwise = select_pairwise_frontier_candidate(
        feature_rows,
        winner_hash=str(fixture["score_selected_winner_hash"]),
        config=PairwiseLateStageRerankerConfig(),
    )

    out = build_pairwise_margin_explanation(
        pairwise,
        legacy,
        config=PairwiseLateStageRerankerConfig(),
    )

    assert str(out["dominant_positive_group"]) == "structural_features"
    assert float(out["group_totals"]["structural_features"]) > 0.0
    assert float(out["group_totals"]["score_features"]) < 0.0


def test_stagea_data_realism_summary_marks_current_dataset_thin() -> None:
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    dataset_summary = build_truth_gap_benchmark_summary(rows)
    realism = build_stagea_data_realism_summary(dataset_summary)

    assert int(realism["row_count"]) == 16
    assert int(realism["distinct_pattern_count"]) >= 1
    assert int(realism["dominant_pattern_count"]) >= 10
    assert str(realism["broader_lift_status"]) == "thin"


def test_stagea_feature_story_keeps_score_only_and_full_models_distinct() -> None:
    fixture = _load_fixture()

    out = build_stagea_feature_story(fixture)

    assert str(out["model_ladder"]["legacy_candidate_hash"]) == "73eee2bf84b7c07f"
    assert str(out["model_ladder"]["weighted_score_only_candidate_hash"]) == "73eee2bf84b7c07f"
    assert str(out["model_ladder"]["weighted_full_candidate_hash"]) == "9002ee09917e5a0d"
    assert str(out["model_ladder"]["pairwise_candidate_hash"]) == "9002ee09917e5a0d"
    assert str(out["weighted_margin_explanation"]["dominant_positive_group"]) == "structural_features"


def test_disagreement_frontier_row_audit_confirms_repeated_structural_rescue() -> None:
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    audit_rows = build_disagreement_frontier_row_audit(rows)

    assert len(audit_rows) == 16
    assert str(audit_rows[0]["winner_candidate_hash"]) == "73eee2bf84b7c07f"
    assert str(audit_rows[0]["challenger_candidate_hash"]) == "9002ee09917e5a0d"
    assert str(audit_rows[0]["weighted_candidate_hash"]) == "9002ee09917e5a0d"
    assert str(audit_rows[0]["pairwise_candidate_hash"]) == "9002ee09917e5a0d"
    assert str(audit_rows[0]["weighted_score_only_candidate_hash"]) == "73eee2bf84b7c07f"
    assert str(audit_rows[0]["weighted_dominant_group"]) == "structural_features"
    assert str(audit_rows[0]["pairwise_dominant_group"]) == "structural_features"
    assert int(audit_rows[0]["weighted_rescued_from_legacy"]) == 1
    assert int(audit_rows[0]["pairwise_rescued_from_legacy"]) == 1


def test_disagreement_frontier_pattern_audit_shows_dominant_pattern_rescue() -> None:
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    pattern_rows = build_disagreement_frontier_pattern_audit(rows)

    assert len(pattern_rows) == 5
    assert int(pattern_rows[0]["count"]) == 10
    assert str(pattern_rows[0]["winner_candidate_hash"]) == "73eee2bf84b7c07f"
    assert str(pattern_rows[0]["challenger_candidate_hash"]) == "9002ee09917e5a0d"
    assert int(pattern_rows[0]["phaseB_top_n_used"]) == 8
    assert str(pattern_rows[0]["phaseC_start_policy"]) == ""
    assert int(pattern_rows[0]["weighted_rescued_count"]) == 10
    assert int(pattern_rows[0]["pairwise_rescued_count"]) == 10
    assert dict(pattern_rows[0]["weighted_dominant_group_counts"]) == {
        "structural_features": 10
    }
    assert dict(pattern_rows[0]["pairwise_dominant_group_counts"]) == {
        "structural_features": 10
    }


def test_frontier_challenger_vs_winner_case_summary_explains_minority_unrecovered_case() -> None:
    artifact_path = Path(
        "output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T091806220616Z__bench_solve_pipeline_no_wli__55b7159/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
    )

    out = build_frontier_challenger_vs_winner_case_summary(
        artifact_path=artifact_path,
        winner_candidate_hash="73eee2bf84b7c07f",
        challenger_candidate_hash="e45c25ba171877fd",
    )

    assert str(out["challenger_candidate_hash"]) == "e45c25ba171877fd"
    assert int(out["challenger_eligible_novel"]) == 0
    assert int(out["challenger_source_rank"]) == 8
    assert float(out["weighted_margin_total"]) < 0.0
    assert float(out["pairwise_margin_total"]) < 0.0
    assert float(out["weighted_group_totals"]["score_features"]) < 0.0
    assert float(out["weighted_group_totals"]["structural_features"]) < 0.0


def test_stagea_rescued_vs_unrecovered_contrast_keeps_plain_language_difference_visible() -> None:
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    out = build_stagea_rescued_vs_unrecovered_contrast(rows)

    rescued = dict(out["rescued_case"])
    unrecovered = dict(out["unrecovered_case"])

    assert str(rescued["challenger_candidate_hash"]) == "9002ee09917e5a0d"
    assert int(rescued["challenger_eligible_novel"]) == 1
    assert int(rescued["challenger_source_rank"]) == 2
    assert float(rescued["weighted_margin_total"]) > 0.0
    assert float(rescued["weighted_group_totals"]["structural_features"]) > 0.0
    assert float(rescued["weighted_group_totals"]["score_features"]) < 0.0

    assert str(unrecovered["challenger_candidate_hash"]) == "e45c25ba171877fd"
    assert int(unrecovered["challenger_eligible_novel"]) == 0
    assert int(unrecovered["challenger_source_rank"]) == 8
    assert float(unrecovered["weighted_margin_total"]) < 0.0
    assert float(unrecovered["weighted_group_totals"]["score_features"]) < 0.0
    assert float(unrecovered["weighted_group_totals"]["structural_features"]) < 0.0


def test_weighted_ablation_configs_keep_small_interpretable_ladder() -> None:
    configs = build_weighted_ablation_configs()

    assert set(configs) == {
        "score_only",
        "score_plus_novelty",
        "score_plus_lexical",
        "score_plus_novelty_plus_lexical",
    }
    assert build_weighted_score_plus_novelty_config().word_ngram_weight == 0.0
    assert build_weighted_score_plus_lexical_config().word_ngram_weight > 0.0
    assert (
        build_weighted_score_plus_novelty_plus_lexical_config().novelty_distance_weight
        > 0.0
    )


def test_weighted_numeric_ablation_configs_keep_score_plus_novelty_baseline() -> None:
    configs = build_weighted_numeric_ablation_configs()

    assert set(configs) == {
        "score_plus_novelty",
        "score_plus_novelty_plus_score_gap_to_winner",
        "score_plus_novelty_plus_score_gap_to_anchor",
        "score_plus_novelty_plus_init_score",
        "score_plus_novelty_plus_init_search_score",
    }
    assert build_weighted_score_plus_novelty_plus_score_gap_to_winner_config().score_gap_to_winner_weight > 0.0
    assert build_weighted_score_plus_novelty_plus_score_gap_to_anchor_config().score_gap_to_anchor_weight > 0.0
    assert build_weighted_score_plus_novelty_plus_init_score_config().init_score_weight > 0.0
    assert build_weighted_score_plus_novelty_plus_init_search_score_config().init_search_score_weight > 0.0


def test_weighted_categorical_ablation_configs_keep_safe_source_only_scope() -> None:
    configs = build_weighted_categorical_ablation_configs()

    assert set(configs) == {
        "score_plus_novelty",
        "score_plus_novelty_plus_phaseb_topk_penalty",
        "score_plus_novelty_plus_stage3_best_phaseb_penalty",
        "score_plus_novelty_plus_source_penalties",
    }
    assert build_weighted_score_plus_novelty_plus_phaseb_topk_penalty_config().phaseb_topk_penalty_weight > 0.0
    assert (
        build_weighted_score_plus_novelty_plus_stage3_best_phaseb_penalty_config().stage3_best_phaseb_penalty_weight
        > 0.0
    )
    assert (
        build_weighted_score_plus_novelty_plus_source_penalties_config().phaseb_topk_penalty_weight
        > 0.0
    )


def test_stagea_unrecovered_case_feature_audit_separates_present_unused_and_absent() -> None:
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    out = build_stagea_unrecovered_case_feature_audit(rows)
    rescued = dict(out["rescued_case"])
    unrecovered = dict(out["unrecovered_case"])

    rescued_present_used = {row["field"] for row in rescued["present_and_used"]}
    rescued_present_unused = {row["field"] for row in rescued["present_but_unused"]}
    rescued_absent = {row["field"] for row in rescued["absent_today"]}
    unrecovered_present_used = {row["field"] for row in unrecovered["present_and_used"]}
    unrecovered_present_unused = {
        row["field"] for row in unrecovered["present_but_unused"]
    }
    unrecovered_absent = {row["field"] for row in unrecovered["absent_today"]}

    assert "final_score" in rescued_present_used
    assert "eligible_novel_challenger" in rescued_present_used
    assert "novelty_distance_to_anchor" in rescued_present_used
    assert "init_search_score" in rescued_present_unused
    assert "word_ngram_score" in rescued_absent

    assert "final_score" in unrecovered_present_used
    assert "eligible_novel_challenger" in unrecovered_present_used
    assert "novelty_distance_to_anchor" in unrecovered_absent
    assert "init_search_score" in unrecovered_present_unused
    assert "word_ngram_score" in unrecovered_absent


def test_stagea_weighted_ablation_sweep_shows_novelty_not_lexical_is_current_lever() -> None:
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    out = build_stagea_weighted_ablation_sweep(rows)
    models = dict(out["models"])

    assert int(models["score_only"]["rescued_row_count"]) == 0
    assert int(models["score_only"]["rescued_pattern_count"]) == 0
    assert int(models["score_plus_novelty"]["rescued_row_count"]) == 15
    assert int(models["score_plus_novelty"]["rescued_pattern_count"]) == 4
    assert int(models["score_plus_lexical"]["rescued_row_count"]) == 0
    assert int(models["score_plus_lexical"]["rescued_pattern_count"]) == 0
    assert int(models["score_plus_novelty_plus_lexical"]["rescued_row_count"]) == 15
    assert int(models["score_plus_novelty_plus_lexical"]["rescued_pattern_count"]) == 4


def test_stagea_numeric_field_ablation_sweep_reports_present_unused_numeric_variants() -> None:
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    out = build_stagea_numeric_field_ablation_sweep(rows)
    models = dict(out["models"])

    assert int(models["score_plus_novelty"]["rescued_row_count"]) == 15
    assert int(models["score_plus_novelty"]["rescued_pattern_count"]) == 4
    assert int(models["score_plus_novelty"]["rescued_unrecovered_class"]) == 0

    assert int(models["score_plus_novelty_plus_score_gap_to_winner"]["rescued_unrecovered_class"]) == 0
    assert int(models["score_plus_novelty_plus_score_gap_to_anchor"]["rescued_unrecovered_class"]) == 0
    assert int(models["score_plus_novelty_plus_init_score"]["rescued_unrecovered_class"]) == 0
    assert int(models["score_plus_novelty_plus_init_search_score"]["rescued_unrecovered_class"]) == 0


def test_stagea_categorical_field_ablation_sweep_keeps_safe_source_pass_honest() -> None:
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    out = build_stagea_categorical_field_ablation_sweep(rows)
    models = dict(out["models"])

    assert int(models["score_plus_novelty"]["rescued_row_count"]) == 15
    assert int(models["score_plus_novelty"]["rescued_pattern_count"]) == 4
    assert int(models["score_plus_novelty"]["rescued_unrecovered_class"]) == 0

    assert int(models["score_plus_novelty_plus_phaseb_topk_penalty"]["rescued_row_count"]) == 16
    assert int(models["score_plus_novelty_plus_phaseb_topk_penalty"]["rescued_pattern_count"]) == 5
    assert int(models["score_plus_novelty_plus_phaseb_topk_penalty"]["rescued_unrecovered_class"]) == 1
    assert "7391f8d462115a5b" in list(
        models["score_plus_novelty_plus_phaseb_topk_penalty"]["selected_candidate_hashes"]
    )

    assert int(models["score_plus_novelty_plus_stage3_best_phaseb_penalty"]["rescued_row_count"]) == 15
    assert int(models["score_plus_novelty_plus_stage3_best_phaseb_penalty"]["rescued_pattern_count"]) == 4
    assert int(models["score_plus_novelty_plus_stage3_best_phaseb_penalty"]["rescued_unrecovered_class"]) == 0

    assert int(models["score_plus_novelty_plus_source_penalties"]["rescued_row_count"]) == 16
    assert int(models["score_plus_novelty_plus_source_penalties"]["rescued_pattern_count"]) == 5
    assert int(models["score_plus_novelty_plus_source_penalties"]["rescued_unrecovered_class"]) == 1
    assert "7391f8d462115a5b" in list(
        models["score_plus_novelty_plus_source_penalties"]["selected_candidate_hashes"]
    )


def test_stagea_weighted_robustness_sweep_reports_pattern_stability() -> None:
    rows = json.loads(
        Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
        ).read_text(encoding="utf-8")
    )

    out = build_stagea_weighted_robustness_sweep(rows)

    assert int(out["total_configs"]) == 81
    assert int(out["dominant_pattern_all_configs_rescued"]) == 1
    assert int(out["unrecovered_class_any_config_rescued"]) == 0
    assert len(list(out["row_results"])) == 16


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
    assert str(summary["data_realism"]["broader_lift_status"]) == "thin"
    assert str(
        summary["feature_story"]["weighted_margin_explanation"]["dominant_positive_group"]
    ) == "structural_features"
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "decision_note.md").exists()
    assert (tmp_path / "v45_feature_rows.json").exists()
    assert (tmp_path / "v45_trial_material_rows.json").exists()
    assert (tmp_path / "disagreement_frontier_row_audit.json").exists()
    assert (tmp_path / "disagreement_frontier_pattern_audit.json").exists()
    assert (tmp_path / "rescued_vs_unrecovered_contrast.json").exists()
    assert (tmp_path / "unrecovered_case_feature_audit.json").exists()
    assert (tmp_path / "weighted_ablation_sweep.json").exists()
    assert (tmp_path / "numeric_field_ablation_sweep.json").exists()
    assert (tmp_path / "categorical_field_ablation_sweep.json").exists()
    assert (tmp_path / "weighted_robustness_sweep.json").exists()
    assert int(summary["disagreement_frontier_pattern_audit"][0]["count"]) == 10
    assert dict(
        summary["disagreement_frontier_pattern_audit"][0][
            "weighted_dominant_group_counts"
        ]
    ) == {"structural_features": 10}
    assert str(
        summary["rescued_vs_unrecovered_contrast"]["rescued_case"][
            "challenger_candidate_hash"
        ]
    ) == "9002ee09917e5a0d"
    assert str(
        summary["rescued_vs_unrecovered_contrast"]["unrecovered_case"][
            "challenger_candidate_hash"
        ]
    ) == "e45c25ba171877fd"
    assert (
        summary["unrecovered_case_feature_audit"]["unrecovered_case"]["absent_today"][0][
            "field"
        ]
        != ""
    )
    assert int(summary["weighted_ablation_sweep"]["models"]["score_only"]["rescued_row_count"]) == 0
    assert int(
        summary["numeric_field_ablation_sweep"]["models"]["score_plus_novelty"][
            "rescued_row_count"
        ]
    ) >= 0
    assert int(summary["weighted_robustness_sweep"]["total_configs"]) == 81
