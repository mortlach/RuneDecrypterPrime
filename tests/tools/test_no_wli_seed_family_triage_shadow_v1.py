from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.seed_family_triage_shadow_v1 import (
    extract_seed_family_triage_shadow_v1 as mod,
)


def _stop_run_row(
    *,
    key_seed: int,
    run_type: str,
    panel_name: str,
    panel_role: str,
    would_dump: int,
    rule_id: str = "",
) -> dict[str, object]:
    return {
        "artifact_path": f"output/test/{key_seed}.json",
        "key_seed": key_seed,
        "run_type": run_type,
        "target_panel_name": panel_name,
        "target_panel_role": panel_role,
        "would_dump": would_dump,
        "would_stop": 0,
        "shadow_rule_id": rule_id,
    }


def _case_row(
    *,
    key_seed: int,
    case_shape_label: str,
    decision_axis_label: str,
    primary_explanation: str,
) -> dict[str, object]:
    return {
        "key_seed": key_seed,
        "case_shape_label": case_shape_label,
        "decision_axis_label": decision_axis_label,
        "primary_explanation": primary_explanation,
    }


def _v1_digest_row(
    *,
    key_seed: int,
    study_role: str,
    target_panel_name: str,
    target_panel_role: str,
    family_quality_read_label: str,
    truth_family: str,
    trust_family: str,
    archive_family: str,
    full_family: str,
    persistence_family: str,
) -> dict[str, object]:
    return {
        "key_seed": key_seed,
        "study_role": study_role,
        "target_panel_name": target_panel_name,
        "target_panel_role": target_panel_role,
        "family_quality_read_label": family_quality_read_label,
        "truth_winner_family_id": truth_family,
        "trust_winner_family_id": trust_family,
        "archive_uplift_winner_family_id": archive_family,
        "full_uplift_winner_family_id": full_family,
        "persistence_winner_family_id": persistence_family,
    }


def _v2_agreement_row(
    *,
    key_seed: int,
    winner_pattern_key: str,
    unique_winner_family_count: int,
    truth_agreement_count: int,
) -> dict[str, object]:
    return {
        "key_seed": key_seed,
        "winner_pattern_key": winner_pattern_key,
        "pattern_bucket_label": "test_bucket",
        "unique_winner_family_count": unique_winner_family_count,
        "truth_agreement_count": truth_agreement_count,
    }


def _v3_pattern_row(
    *,
    key_seed: int,
    winner_pattern_key: str,
    split_pattern_label: str,
    pattern_strength_read_label: str,
    truth_winner_strength_label: str,
) -> dict[str, object]:
    return {
        "key_seed": key_seed,
        "winner_pattern_key": winner_pattern_key,
        "split_pattern_label": split_pattern_label,
        "pattern_strength_read_label": pattern_strength_read_label,
        "truth_winner_strength_label": truth_winner_strength_label,
    }


def _family_row(
    *,
    key_seed: int,
    study_role: str,
    family_id: str,
    family_role_label: str,
    best_truth: float,
    best_trust: float,
    best_archive_uplift: float,
    best_full_uplift: float,
    boundary_count: int,
    boundaries_seen: str,
    persistence_count: int,
    reaches_archive: int,
    truth_trend_label: str = "improves",
    trust_trend_label: str = "improves",
    archive_uplift_trend_label: str = "improves",
    full_uplift_trend_label: str = "improves",
) -> dict[str, object]:
    return {
        "key_seed": key_seed,
        "study_role": study_role,
        "family_id": family_id,
        "family_role_label": family_role_label,
        "best_truth": best_truth,
        "best_trust": best_trust,
        "best_archive_uplift": best_archive_uplift,
        "best_full_uplift": best_full_uplift,
        "boundary_count": boundary_count,
        "boundaries_seen": boundaries_seen,
        "family_persistence_count": persistence_count,
        "family_reaches_archive": reaches_archive,
        "truth_trend_label": truth_trend_label,
        "trust_trend_label": trust_trend_label,
        "archive_uplift_trend_label": archive_uplift_trend_label,
        "full_uplift_trend_label": full_uplift_trend_label,
    }


def _pair_row(
    *,
    key_seed: int,
    pair_name: str,
    truth_family_id: str,
    alt_family_id: str,
    pair_read_label: str,
) -> dict[str, object]:
    return {
        "key_seed": key_seed,
        "pair_name": pair_name,
        "truth_family_id": truth_family_id,
        "alt_family_id": alt_family_id,
        "pair_read_label": pair_read_label,
    }


def _build_test_inputs(
    *,
    promote_explore_only_seed: int | None = None,
) -> tuple[
    list[dict[str, object]],
    dict[int, dict[str, object]],
    dict[int, dict[str, object]],
    dict[int, dict[str, object]],
    dict[int, dict[str, object]],
    dict[int, dict[str, dict[str, object]]],
    dict[int, dict[str, dict[str, object]]],
]:
    stop_rows = [
        _stop_run_row(key_seed=511, run_type="solved_control", panel_name="core", panel_role="benchmark", would_dump=1, rule_id="trust"),
        _stop_run_row(key_seed=411, run_type="stage35_live_win", panel_name="core", panel_role="benchmark", would_dump=1, rule_id="archive"),
        _stop_run_row(key_seed=611, run_type="stage35_live_win", panel_name="core", panel_role="benchmark", would_dump=1, rule_id="trust"),
        _stop_run_row(key_seed=711, run_type="stage35_live_win", panel_name="core", panel_role="benchmark", would_dump=1, rule_id="trust"),
        _stop_run_row(key_seed=811, run_type="unknown", panel_name="core", panel_role="benchmark", would_dump=0),
        _stop_run_row(key_seed=911, run_type="unknown", panel_name="core", panel_role="benchmark", would_dump=0),
        _stop_run_row(key_seed=1011, run_type="stage35_live_win", panel_name="core", panel_role="benchmark", would_dump=1, rule_id="trust"),
        _stop_run_row(key_seed=1111, run_type="stage35_live_win", panel_name="core", panel_role="benchmark", would_dump=0),
        _stop_run_row(key_seed=1211, run_type="unknown", panel_name="core", panel_role="benchmark", would_dump=0),
        _stop_run_row(key_seed=1311, run_type="unknown", panel_name="pressure", panel_role="falsification", would_dump=1, rule_id="trust"),
        _stop_run_row(key_seed=1411, run_type="unknown", panel_name="pressure", panel_role="falsification", would_dump=1, rule_id="archive"),
        _stop_run_row(key_seed=1511, run_type="unknown", panel_name="pressure", panel_role="falsification", would_dump=0),
    ]
    case_rows = {
        1111: _case_row(key_seed=1111, case_shape_label="accepted_miss_outside_current_model", decision_axis_label="mixed", primary_explanation="truth_row_not_trust_led"),
        1311: _case_row(key_seed=1311, case_shape_label="trust_false_fire", decision_axis_label="trust", primary_explanation="trust_rule_admits_weak_family"),
        1411: _case_row(key_seed=1411, case_shape_label="archive_false_fire", decision_axis_label="archive_uplift", primary_explanation="archive_rule_prefers_low_truth_uplift"),
    }
    v1_digest = {
        1111: _v1_digest_row(key_seed=1111, study_role="discriminator", target_panel_name="core", target_panel_role="benchmark", family_quality_read_label="accepted_miss_family_looks_real", truth_family="f0", trust_family="f0", archive_family="f1", full_family="f0", persistence_family="f0"),
        1311: _v1_digest_row(key_seed=1311, study_role="discriminator", target_panel_name="pressure", target_panel_role="falsification", family_quality_read_label="trust_false_fire_family_looks_weak", truth_family="f0", trust_family="f1", archive_family="f1", full_family="f0", persistence_family="f0"),
        1411: _v1_digest_row(key_seed=1411, study_role="discriminator", target_panel_name="pressure", target_panel_role="falsification", family_quality_read_label="archive_false_fire_family_looks_weak", truth_family="f1", trust_family="f0", archive_family="f1", full_family="f0", persistence_family="f0"),
        411: _v1_digest_row(key_seed=411, study_role="reference", target_panel_name="core", target_panel_role="benchmark", family_quality_read_label="truth_trust_split", truth_family="f0", trust_family="f1", archive_family="f0", full_family="f0", persistence_family="f0"),
        611: _v1_digest_row(key_seed=611, study_role="reference", target_panel_name="core", target_panel_role="benchmark", family_quality_read_label="truth_uplift_split", truth_family="f0", trust_family="f0", archive_family="f1", full_family="f0", persistence_family="f0"),
        1011: _v1_digest_row(key_seed=1011, study_role="reference", target_panel_name="core", target_panel_role="benchmark", family_quality_read_label="truth_trust_split", truth_family="f1", trust_family="f0", archive_family="f0", full_family="f0", persistence_family="f0"),
    }
    v2_agreement = {
        1111: _v2_agreement_row(key_seed=1111, winner_pattern_key="A-A-B-A-A", unique_winner_family_count=2, truth_agreement_count=4),
        1311: _v2_agreement_row(key_seed=1311, winner_pattern_key="A-B-B-A-A", unique_winner_family_count=2, truth_agreement_count=3),
        1411: _v2_agreement_row(key_seed=1411, winner_pattern_key="A-B-A-B-B", unique_winner_family_count=2, truth_agreement_count=2),
        411: _v2_agreement_row(key_seed=411, winner_pattern_key="A-B-A-A-A", unique_winner_family_count=2, truth_agreement_count=4),
        611: _v2_agreement_row(key_seed=611, winner_pattern_key="A-A-B-A-A", unique_winner_family_count=2, truth_agreement_count=4),
        1011: _v2_agreement_row(key_seed=1011, winner_pattern_key="A-B-B-B-B", unique_winner_family_count=2, truth_agreement_count=1),
    }
    v3_pattern = {
        1111: _v3_pattern_row(key_seed=1111, winner_pattern_key="A-A-B-A-A", split_pattern_label="multi_split", pattern_strength_read_label="accepted_miss_reference_like", truth_winner_strength_label="strong"),
        1311: _v3_pattern_row(key_seed=1311, winner_pattern_key="A-B-B-A-A", split_pattern_label="multi_split", pattern_strength_read_label="inconclusive", truth_winner_strength_label="strong"),
        1411: _v3_pattern_row(key_seed=1411, winner_pattern_key="A-B-A-B-B", split_pattern_label="multi_split", pattern_strength_read_label="inconclusive", truth_winner_strength_label="partial"),
        411: _v3_pattern_row(key_seed=411, winner_pattern_key="A-B-A-A-A", split_pattern_label="truth_trust_split", pattern_strength_read_label="reference_like_strong", truth_winner_strength_label="strong"),
        611: _v3_pattern_row(key_seed=611, winner_pattern_key="A-A-B-A-A", split_pattern_label="truth_archive_split", pattern_strength_read_label="reference_like_strong", truth_winner_strength_label="strong"),
        1011: _v3_pattern_row(key_seed=1011, winner_pattern_key="A-B-B-B-B", split_pattern_label="multi_split", pattern_strength_read_label="pattern_only_reference_like_but_strength_weak", truth_winner_strength_label="weak"),
    }

    family_rows_by_seed = {
        1111: {
            "f0": _family_row(key_seed=1111, study_role="discriminator", family_id="f0", family_role_label="mixed", best_truth=0.528, best_trust=0.167, best_archive_uplift=0.0, best_full_uplift=0.013, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1),
            "f1": _family_row(key_seed=1111, study_role="discriminator", family_id="f1", family_role_label="challenger_like", best_truth=0.489, best_trust=0.0, best_archive_uplift=0.225, best_full_uplift=0.0, boundary_count=2, boundaries_seen="phaseC_start|stage35_seed", persistence_count=2, reaches_archive=0),
        },
        1311: {
            "f0": _family_row(key_seed=1311, study_role="discriminator", family_id="f0", family_role_label="mixed", best_truth=0.578, best_trust=0.353, best_archive_uplift=0.0, best_full_uplift=0.015, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1),
            "f1": _family_row(key_seed=1311, study_role="discriminator", family_id="f1", family_role_label="challenger_like", best_truth=0.558, best_trust=0.375, best_archive_uplift=0.222, best_full_uplift=0.0, boundary_count=2, boundaries_seen="phaseC_start|stage35_seed", persistence_count=2, reaches_archive=0, truth_trend_label="degrades"),
        },
        1411: {
            "f0": _family_row(key_seed=1411, study_role="discriminator", family_id="f0", family_role_label="mixed", best_truth=0.276, best_trust=0.0, best_archive_uplift=0.182, best_full_uplift=0.003, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1, truth_trend_label="mixed", trust_trend_label="flat"),
            "f1": _family_row(key_seed=1411, study_role="discriminator", family_id="f1", family_role_label="challenger_like", best_truth=0.302, best_trust=0.0, best_archive_uplift=0.499, best_full_uplift=0.0, boundary_count=2, boundaries_seen="phaseC_start|stage35_seed", persistence_count=2, reaches_archive=0, trust_trend_label="flat"),
        },
        411: {
            "f0": _family_row(key_seed=411, study_role="reference", family_id="f0", family_role_label="anchor_like", best_truth=0.488, best_trust=0.067, best_archive_uplift=0.242, best_full_uplift=0.0, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1, trust_trend_label="mixed", archive_uplift_trend_label="mixed"),
            "f1": _family_row(key_seed=411, study_role="reference", family_id="f1", family_role_label="mixed", best_truth=0.418, best_trust=0.083, best_archive_uplift=0.0, best_full_uplift=0.0, boundary_count=2, boundaries_seen="phaseC_start|stage35_seed", persistence_count=2, reaches_archive=0, truth_trend_label="flat", trust_trend_label="flat", archive_uplift_trend_label="flat", full_uplift_trend_label="flat"),
        },
        611: {
            "f0": _family_row(key_seed=611, study_role="reference", family_id="f0", family_role_label="mixed", best_truth=0.635, best_trust=0.444, best_archive_uplift=0.0, best_full_uplift=0.01, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1),
            "f1": _family_row(key_seed=611, study_role="reference", family_id="f1", family_role_label="challenger_like", best_truth=0.620, best_trust=0.300, best_archive_uplift=0.150, best_full_uplift=0.0, boundary_count=2, boundaries_seen="phaseC_start|stage35_seed", persistence_count=2, reaches_archive=0),
        },
        1011: {
            "f0": _family_row(key_seed=1011, study_role="reference", family_id="f0", family_role_label="mixed", best_truth=0.730, best_trust=0.321, best_archive_uplift=0.140, best_full_uplift=0.01, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1),
            "f1": _family_row(key_seed=1011, study_role="reference", family_id="f1", family_role_label="challenger_like", best_truth=0.737, best_trust=0.210, best_archive_uplift=0.0, best_full_uplift=0.0, boundary_count=1, boundaries_seen="phaseC_start", persistence_count=1, reaches_archive=0),
        },
    }
    if promote_explore_only_seed == 411:
        v1_digest[411] = _v1_digest_row(key_seed=411, study_role="reference", target_panel_name="core", target_panel_role="benchmark", family_quality_read_label="truth_trust_split", truth_family="f0", trust_family="f0", archive_family="f0", full_family="f0", persistence_family="f0")
        family_rows_by_seed[411]["f1"] = _family_row(key_seed=411, study_role="reference", family_id="f1", family_role_label="mixed", best_truth=0.300, best_trust=0.020, best_archive_uplift=0.0, best_full_uplift=0.0, boundary_count=1, boundaries_seen="phaseC_start", persistence_count=1, reaches_archive=0, truth_trend_label="flat", trust_trend_label="flat", archive_uplift_trend_label="flat", full_uplift_trend_label="flat")

    pair_rows_by_seed = {
        1111: {
            "truth_vs_trust": _pair_row(key_seed=1111, pair_name="truth_vs_trust", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
            "truth_vs_archive": _pair_row(key_seed=1111, pair_name="truth_vs_archive", truth_family_id="f0", alt_family_id="f1", pair_read_label="alt_not_clearly_weaker"),
            "truth_vs_full_uplift": _pair_row(key_seed=1111, pair_name="truth_vs_full_uplift", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
            "truth_vs_persistence": _pair_row(key_seed=1111, pair_name="truth_vs_persistence", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
        },
        1311: {
            "truth_vs_trust": _pair_row(key_seed=1311, pair_name="truth_vs_trust", truth_family_id="f0", alt_family_id="f1", pair_read_label="alt_not_clearly_weaker"),
            "truth_vs_archive": _pair_row(key_seed=1311, pair_name="truth_vs_archive", truth_family_id="f0", alt_family_id="f1", pair_read_label="alt_not_clearly_weaker"),
            "truth_vs_full_uplift": _pair_row(key_seed=1311, pair_name="truth_vs_full_uplift", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
            "truth_vs_persistence": _pair_row(key_seed=1311, pair_name="truth_vs_persistence", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
        },
        1411: {
            "truth_vs_trust": _pair_row(key_seed=1411, pair_name="truth_vs_trust", truth_family_id="f1", alt_family_id="f0", pair_read_label="alt_not_clearly_weaker"),
            "truth_vs_archive": _pair_row(key_seed=1411, pair_name="truth_vs_archive", truth_family_id="f1", alt_family_id="f1", pair_read_label="same_family"),
            "truth_vs_full_uplift": _pair_row(key_seed=1411, pair_name="truth_vs_full_uplift", truth_family_id="f1", alt_family_id="f0", pair_read_label="alt_not_clearly_weaker"),
            "truth_vs_persistence": _pair_row(key_seed=1411, pair_name="truth_vs_persistence", truth_family_id="f1", alt_family_id="f0", pair_read_label="alt_not_clearly_weaker"),
        },
        411: {
            "truth_vs_trust": _pair_row(key_seed=411, pair_name="truth_vs_trust", truth_family_id="f0", alt_family_id="f1", pair_read_label="alt_not_clearly_weaker"),
            "truth_vs_archive": _pair_row(key_seed=411, pair_name="truth_vs_archive", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
            "truth_vs_full_uplift": _pair_row(key_seed=411, pair_name="truth_vs_full_uplift", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
            "truth_vs_persistence": _pair_row(key_seed=411, pair_name="truth_vs_persistence", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
        },
        611: {
            "truth_vs_trust": _pair_row(key_seed=611, pair_name="truth_vs_trust", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
            "truth_vs_archive": _pair_row(key_seed=611, pair_name="truth_vs_archive", truth_family_id="f0", alt_family_id="f1", pair_read_label="alt_not_clearly_weaker"),
            "truth_vs_full_uplift": _pair_row(key_seed=611, pair_name="truth_vs_full_uplift", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
            "truth_vs_persistence": _pair_row(key_seed=611, pair_name="truth_vs_persistence", truth_family_id="f0", alt_family_id="f0", pair_read_label="same_family"),
        },
        1011: {
            "truth_vs_trust": _pair_row(key_seed=1011, pair_name="truth_vs_trust", truth_family_id="f1", alt_family_id="f0", pair_read_label="alt_not_clearly_weaker"),
            "truth_vs_archive": _pair_row(key_seed=1011, pair_name="truth_vs_archive", truth_family_id="f1", alt_family_id="f0", pair_read_label="alt_not_clearly_weaker"),
            "truth_vs_full_uplift": _pair_row(key_seed=1011, pair_name="truth_vs_full_uplift", truth_family_id="f1", alt_family_id="f0", pair_read_label="alt_not_clearly_weaker"),
            "truth_vs_persistence": _pair_row(key_seed=1011, pair_name="truth_vs_persistence", truth_family_id="f1", alt_family_id="f0", pair_read_label="alt_not_clearly_weaker"),
        },
    }
    return stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, family_rows_by_seed, pair_rows_by_seed


def test_triage_shadow_v1_review_seed_contract_is_fixed() -> None:
    assert mod.TRIAGE_REVIEW_SEEDS == (511, 411, 611, 711, 811, 911, 1011, 1111, 1211, 1311, 1411, 1511)


def test_triage_shadow_v1_family_enriched_seed_contract_is_fixed() -> None:
    assert mod.TRIAGE_FAMILY_ENRICHED_SEEDS == (1111, 1311, 1411, 411, 611, 1011)


def test_triage_shadow_v1_requires_explicit_input_bundle_files(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        mod._require_bundle_files(bundle_dir, mod.REQUIRED_STOP_INPUT_FILES, label="stop")


def test_seed_priority_high_for_reference_like_strong_case() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    by_seed = {row["key_seed"]: row for row in rows}
    assert by_seed[411]["seed_priority_band"] == "high"


def test_seed_priority_high_for_accepted_miss_reference_like_case() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    by_seed = {row["key_seed"]: row for row in rows}
    assert by_seed[1111]["seed_priority_band"] == "high"


def test_seed_priority_medium_for_pattern_only_but_weak_case() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    by_seed = {row["key_seed"]: row for row in rows}
    assert by_seed[1011]["seed_priority_band"] == "medium"


def test_seed_priority_low_for_quiet_reject_case() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    by_seed = {row["key_seed"]: row for row in rows}
    assert by_seed[811]["seed_priority_band"] == "low"


def test_seed_priority_unclear_for_inconclusive_family_case() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    by_seed = {row["key_seed"]: row for row in rows}
    assert by_seed[1311]["seed_priority_band"] == "unclear"
    assert by_seed[1411]["seed_priority_band"] == "unclear"


def test_budget_policy_focus_with_exploration_for_high_case() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    by_seed = {row["key_seed"]: row for row in rows}
    assert by_seed[1111]["seed_budget_policy_label"] == "focus_with_exploration"


def test_budget_policy_balanced_portfolio_for_medium_case() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    by_seed = {row["key_seed"]: row for row in rows}
    assert by_seed[1011]["seed_budget_policy_label"] == "balanced_portfolio"


def test_budget_policy_exploration_heavy_for_unclear_case() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    by_seed = {row["key_seed"]: row for row in rows}
    assert by_seed[1311]["seed_budget_policy_label"] == "exploration_heavy"


def test_budget_policy_observe_only_for_low_case() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    by_seed = {row["key_seed"]: row for row in rows}
    assert by_seed[811]["seed_budget_policy_label"] == "observe_only"


def test_seed_level_budget_shares_sum_to_one() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    for row in rows:
        total = (
            float(row["recommended_primary_budget_share"])
            + float(row["recommended_secondary_budget_share"])
            + float(row["recommended_exploration_budget_share"])
        )
        assert total == pytest.approx(1.0)


def test_family_priority_high_for_truth_winner_with_strong_or_partial_strength() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, family_rows_by_seed, pair_rows_by_seed = _build_test_inputs()
    seed_rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    family_rows, _ = mod.build_family_priority_rows(seed_rows, family_rows_by_seed, v1_digest, pair_rows_by_seed)
    target = next(row for row in family_rows if row["key_seed"] == 1111 and row["family_id"] == "f0")
    assert target["family_priority_band"] == "high"


def test_family_priority_medium_for_non_truth_alt_winner() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, family_rows_by_seed, pair_rows_by_seed = _build_test_inputs()
    seed_rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    family_rows, _ = mod.build_family_priority_rows(seed_rows, family_rows_by_seed, v1_digest, pair_rows_by_seed)
    target = next(row for row in family_rows if row["key_seed"] == 611 and row["family_id"] == "f1")
    assert target["family_priority_band"] == "medium"


def test_family_priority_explore_only_keeps_non_truth_family_alive() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, family_rows_by_seed, pair_rows_by_seed = _build_test_inputs(promote_explore_only_seed=411)
    seed_rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    family_rows, _ = mod.build_family_priority_rows(seed_rows, family_rows_by_seed, v1_digest, pair_rows_by_seed)
    target = next(row for row in family_rows if row["key_seed"] == 411 and row["family_id"] == "f1")
    assert target["family_priority_band"] == "explore_only"


def test_family_budget_shares_sum_to_one_per_enriched_seed() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, family_rows_by_seed, pair_rows_by_seed = _build_test_inputs()
    seed_rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    family_rows, _ = mod.build_family_priority_rows(seed_rows, family_rows_by_seed, v1_digest, pair_rows_by_seed)
    totals: dict[int, float] = {}
    for row in family_rows:
        totals.setdefault(int(row["key_seed"]), 0.0)
        totals[int(row["key_seed"])] += float(row["recommended_family_budget_share"])
    for key_seed in mod.TRIAGE_FAMILY_ENRICHED_SEEDS:
        assert totals[key_seed] == pytest.approx(1.0)


def test_stop_only_seed_gets_seed_triage_row_without_family_outputs() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    target = next(row for row in rows if row["key_seed"] == 711)
    assert target["triage_evidence_tier"] == "stop_only"
    assert target["family_quality_read_label"] == ""


def test_family_enriched_seed_requires_family_inputs() -> None:
    _, _, v1_digest, v2_agreement, v3_pattern, family_rows_by_seed, pair_rows_by_seed = _build_test_inputs()
    broken_v3 = dict(v3_pattern)
    broken_v3.pop(1111)
    with pytest.raises(ValueError):
        mod._require_enriched_seed_inputs(
            family_rows_by_seed=family_rows_by_seed,
            v1_digest_by_seed=v1_digest,
            v2_agreement_by_seed=v2_agreement,
            v3_pattern_by_seed=broken_v3,
            v3_pair_by_seed=pair_rows_by_seed,
        )


def test_seed_triage_rows_are_deterministic_under_input_reordering() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, _, _ = _build_test_inputs()
    rows_a = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    rows_b = mod.build_seed_triage_rows(list(reversed(stop_rows)), case_rows, dict(reversed(list(v1_digest.items()))), dict(reversed(list(v2_agreement.items()))), dict(reversed(list(v3_pattern.items()))))
    assert rows_a == rows_b


def test_family_priority_rows_are_deterministic_under_input_reordering() -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, family_rows_by_seed, pair_rows_by_seed = _build_test_inputs()
    seed_rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    rows_a, _ = mod.build_family_priority_rows(seed_rows, family_rows_by_seed, v1_digest, pair_rows_by_seed)
    reversed_family_rows = {
        seed: dict(reversed(list(rows.items())))
        for seed, rows in reversed(list(family_rows_by_seed.items()))
    }
    reversed_pairs = {
        seed: dict(reversed(list(rows.items())))
        for seed, rows in reversed(list(pair_rows_by_seed.items()))
    }
    rows_b, _ = mod.build_family_priority_rows(seed_rows, reversed_family_rows, dict(reversed(list(v1_digest.items()))), reversed_pairs)
    assert rows_a == rows_b


def test_triage_cases_markdown_includes_all_review_seeds(tmp_path: Path) -> None:
    stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern, family_rows_by_seed, pair_rows_by_seed = _build_test_inputs()
    seed_rows = mod.build_seed_triage_rows(stop_rows, case_rows, v1_digest, v2_agreement, v3_pattern)
    family_rows, budget_rows = mod.build_family_priority_rows(seed_rows, family_rows_by_seed, v1_digest, pair_rows_by_seed)
    mod.write_triage_cases_markdown(tmp_path, seed_triage_rows=seed_rows, family_priority_rows=family_rows, budget_rows=budget_rows)
    text = (tmp_path / "triage_cases.md").read_text(encoding="utf-8")
    for seed in mod.TRIAGE_REVIEW_SEEDS:
        assert f"Seed {seed}" in text
