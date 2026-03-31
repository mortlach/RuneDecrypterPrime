from __future__ import annotations

import copy
import re
from pathlib import Path
import inspect

import pytest

from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
from tools.benchmarks.periodic_sub_trans.col_then_sub import runner as col_runner
from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli_runner
from tools.benchmarks.periodic_sub_trans.no_wli import runtime_config as no_wli_runtime_config
from tools.benchmarks.periodic_sub_trans.no_wli import stage2_promotion as no_wli_stage2_promotion
from tools.benchmarks.periodic_sub_trans.no_wli import stage3_band_policy as no_wli_stage3_band_policy
from tools.benchmarks.periodic_sub_trans.sub_then_col import runner as sub_runner
from tools.benchmarks.periodic_sub_trans.common.scorer_schedule import (
    SCHEDULE_EARLY_A_CHAR34,
    SCHEDULE_EARLY_CHAR34_ONLY,
    SCHEDULE_LATE_B_CHAR34,
    SCHEDULE_LATE_CHAR34_ONLY,
    SCHEDULE_MIDDLE_M_CHAR34,
    SCHEDULE_MIDDLE_CHAR34_ONLY,
)
from rune_decrypter_prime.solvers import solver_base as solver_base_mod


pytestmark = pytest.mark.tier_a


def test_col_then_sub_scorer_impl_is_pinned():
    assert col_runner.SCORER_STAGE1.get("impl") == col_runner.SCORER_IMPL
    assert col_runner.SCORER_STAGE1_HARD_RERANK.get("impl") == col_runner.SCORER_IMPL
    assert col_runner.SCORER_FULL.get("impl") == col_runner.SCORER_IMPL


def test_no_wli_scorer_impl_is_pinned_after_profile_load():
    no_wli_runner._apply_profile_defaults()
    assert no_wli_runner.SCORER_STAGE1.get("impl") == no_wli_runner.SCORER_IMPL
    assert no_wli_runner.SCORER_STAGE2.get("impl") == no_wli_runner.SCORER_IMPL
    if no_wli_runner._is_avg_fulltext_scorer(no_wli_runner.SCORER_FULL):
        assert no_wli_runner.SCORER_FULL.get("impl") == no_wli_runner.SCORER_STAGE3_IMPL_AVG_FULLTEXT
    else:
        assert no_wli_runner.SCORER_FULL.get("impl") == no_wli_runner.SCORER_IMPL
    assert str(no_wli_runner.SCORER_FULL.get("objective", "")).startswith("avg.logp")
    assert str(no_wli_runner.SCORER_FULL.get("avg_window_policy", "")) == "full_text"
    assert dict(no_wli_runner.SCORER_STAGE2.get("char_weights", {})) == {4: 1.0}
    assert dict(no_wli_runner.SCORER_FULL.get("char_weights", {})) == {4: 1.0}


def test_no_wli_full_text_objective_summary_is_explicit():
    txt = no_wli_runner._scorer_objective_summary(
        {"objective": "avg.logp.win20", "avg_window_policy": "full_text"}
    )
    assert "span=full_text" in txt
    assert "win_effective=FULL_TEXT" in txt
    assert "win_configured=20" in txt


def test_no_wli_stage3_impl_guard_for_avg_fulltext():
    impl = no_wli_runner._effective_stage3_impl(
        {"objective": "avg.logp.win20", "avg_window_policy": "full_text"}
    )
    assert impl == no_wli_runner.SCORER_STAGE3_IMPL_AVG_FULLTEXT
    assert no_wli_runner.SCORER_STAGE3_IMPL_AVG_FULLTEXT == no_wli_runner.SCORER_IMPL


def test_no_wli_stage3_avg_profile_widens_archive_and_promote():
    profile = get_no_wli_pipeline_profile("no_wli_a1_m12_b34_stage3avg_fulltext_v1")
    assert profile.stage12_archive_keep >= 192
    assert profile.stage12_promote_top >= 96
    assert profile.stage3_initial_keys >= 64
    assert bool(profile.solver_stage3.get("use_raw_score")) is True
    assert float(profile.solver_stage3.get("raw_accept_min_delta", 0.0)) <= 1e-7
    assert float(profile.solver_stage3.get("plateau_min_delta", 1.0)) <= 1e-4
    assert str(profile.scorer_schedule.stage1_a.objective) == "avg.logp.win20"
    assert str(profile.scorer_schedule.stage2_m.objective) == "avg.logp.win20"
    assert str(profile.scorer_schedule.stage3_b.objective) == "avg.logp.win20"
    assert str(profile.scorer_schedule.stage1_a.avg_window_policy) == "full_text"
    assert str(profile.scorer_schedule.stage2_m.avg_window_policy) == "full_text"
    assert str(profile.scorer_schedule.stage3_b.avg_window_policy) == "full_text"
    assert dict(profile.scorer_schedule.stage3_b.char_weights) == {4: 1.0}


def test_no_wli_longrun3x_profile_is_default_and_has_expected_budget():
    assert (
        no_wli_runner.NO_WLI_PIPELINE_PROFILE_ID
        == "no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1"
    )
    profile = get_no_wli_pipeline_profile("no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1")
    assert str(profile.scorer_schedule.stage1_label) == "A_char2_avg_fulltext"
    assert dict(profile.scorer_schedule.stage1_a.char_weights) == {2: 1.0}
    assert dict(profile.scorer_schedule.stage2_m.char_weights) == {4: 1.0}
    assert dict(profile.scorer_schedule.stage3_b.char_weights) == {4: 1.0}
    assert profile.stage3_initial_keys >= 192
    assert profile.stage1_seed_restarts >= 288
    assert profile.stage1_seed_total >= 768
    assert profile.stage1_scout_no_improve_patience >= 3
    assert profile.stage1_scout_min_new_archive <= 1
    base_far = [b for b in profile.stage3_dynamic_bands if str(b.get("name", "")) == "far"]
    assert base_far, "expected far band in long-run profile"
    assert int(base_far[0]["steps"]) >= 9600


def test_no_wli_longrun3x_enables_safe_two_phase_stage3_defaults():
    no_wli_runner._apply_profile_defaults()
    assert no_wli_runner.STAGE3_TWO_PHASE_ENABLED is True
    assert int(no_wli_runner.STAGE3_PHASEA_CFG.get("col_every", -1)) == 0
    assert int(no_wli_runner.STAGE3_PHASEA_CFG.get("col_batch", -1)) == 0
    assert int(no_wli_runner.STAGE3_PHASEA_CFG.get("slip_every", -1)) == 0
    assert int(no_wli_runner.STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS) == int(no_wli_runner.STAGE12_SCOUT_RUNS)
    assert bool(no_wli_runner.STAGE3_C1_FOCUS_ENABLED) is True
    assert int(no_wli_runner.STAGE3_C1_INIT_KEYS) >= 96
    assert int(no_wli_runner.STAGE3_C1_PHASEA_STEPS) >= 1200
    assert int(no_wli_runner.STAGE3_C1_PHASEB_STEPS) >= 6000
    assert int(no_wli_runner.STAGE3_C1_PHASEB_TOP_N) >= 24


def test_no_wli_focus_mode_starts_with_period5_tiers():
    old_mode = str(no_wli_runner.PIPELINE_RUN_MODE)
    try:
        no_wli_runner.PIPELINE_RUN_MODE = "focus_500_nowli"
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()
        assert no_wli_runner.TIERS
        assert int(no_wli_runner.TIERS[0].period) == 5
        assert int(no_wli_runner.TIERS[0].columns) == 1
    finally:
        no_wli_runner.PIPELINE_RUN_MODE = old_mode
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()


def test_no_wli_focus_p5_c1_only_mode_single_tier():
    old_mode = str(no_wli_runner.PIPELINE_RUN_MODE)
    try:
        no_wli_runner.PIPELINE_RUN_MODE = "focus_p5_c1_only"
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()
        assert len(no_wli_runner.TIERS) == 1
        assert str(no_wli_runner.TIERS[0].name) == "focus_p5_c1_l1000"
        assert int(no_wli_runner.TIERS[0].period) == 5
        assert int(no_wli_runner.TIERS[0].columns) == 1
        assert int(no_wli_runner.TIERS[0].length) == 1000
        assert no_wli_runner.STAGE2_PROMOTE_BY_STAGE3_JUDGE is False
        assert no_wli_runner.STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE is False
    finally:
        no_wli_runner.PIPELINE_RUN_MODE = old_mode
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()


def test_no_wli_scan_p5_p7_c1357_mode_matrix_and_scaling():
    old_mode = str(no_wli_runner.PIPELINE_RUN_MODE)
    try:
        no_wli_runner.PIPELINE_RUN_MODE = "scan_p5_p7_c1357"
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()
        assert len(no_wli_runner.TIERS) == 8
        assert str(no_wli_runner.TIERS[0].name) == "scan_p5_c1_l1000"
        assert str(no_wli_runner.TIERS[-1].name) == "scan_p7_c7_l1000"
        periods = sorted({int(t.period) for t in no_wli_runner.TIERS})
        assert periods == [5, 7]
        cols_by_period = {
            p: sorted({int(t.columns) for t in no_wli_runner.TIERS if int(t.period) == p}) for p in periods
        }
        assert cols_by_period == {5: [1, 3, 5, 7], 7: [1, 3, 5, 7]}
        assert str(no_wli_runner.SCORING_EXPERIMENT_PROFILE) == "c_min_late"
        assert no_wli_runner.STAGE2_PROMOTE_BY_STAGE3_JUDGE is False
        assert no_wli_runner.STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE is False
        assert no_wli_runner.ORACLE_ASSIST_SELECTION is False
        assert no_wli_runner.STAGE3_CONTINUE_AFTER_SOLVE is False
        assert float(no_wli_runner.SCAN_TIER_TIME_CAP_SECONDS) == pytest.approx(600.0)
        assert bool(no_wli_runner.SCAN_STAGE2_CONTINUE_TO_GATE) is True
        assert float(no_wli_runner.SCAN_STAGE2_CONTINUE_CAP_SECONDS) == pytest.approx(900.0)
        assert float(no_wli_runner.SCAN_STAGE3_MIN_STAGE2_MATCH) == pytest.approx(0.15)
        assert float(no_wli_runner.SCAN_STAGE3_GATE_LOW_MATCH) == pytest.approx(0.15)
        assert float(no_wli_runner.SCAN_STAGE3_GATE_HIGH_MATCH) == pytest.approx(0.22)
        assert int(no_wli_runner.STAGE12_ARCHIVE_KEEP) == 192
        assert int(no_wli_runner.STAGE12_PROMOTE_TOP) == 96
        assert no_wli_runner.STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS == {3: 24, 5: 24, 7: 24}
        assert no_wli_runner.STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS == {3: 6, 5: 240, 7: 1536}
        assert no_wli_runner.STAGE3_INITIAL_KEYS_BY_COLUMNS == {1: 48, 3: 72, 5: 128, 7: 160, 10: 128, 13: 128}
        assert int(no_wli_runner.STAGE3_C1_INIT_KEYS) == 128
        assert int(no_wli_runner.STAGE3_C1_PHASEA_STEPS) == 1800
        assert int(no_wli_runner.STAGE3_C1_PHASEB_STEPS) == 6000
        assert int(no_wli_runner.STAGE3_C1_PHASEB_TOP_N) == 32
        assert int(no_wli_runner.STAGE3_PHASEB_TOP_N) == 24
        assert float(no_wli_runner.STAGE3_PHASEB_GATE_DELTA_FLOOR) == pytest.approx(0.006)
        assert float(no_wli_runner.STAGE3_PHASEB_GATE_END_GAIN_FLOOR) == pytest.approx(0.003)
        assert int(no_wli_runner.STAGE3_PHASEB_CFG.get("slip_swaps", 0)) == 16
        assert no_wli_runner.STAGE3_PERIOD_INIT_MULT_BY_PERIOD == {7: 1.55}
        assert no_wli_runner.STAGE3_PERIOD_STEP_MULT_BY_PERIOD == {7: 1.85}
        assert no_wli_runner.STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD == {7: 2}
        assert int(no_wli_runner.STAGE3_INIT_KEYS_CAP) == 224
    finally:
        no_wli_runner.PIPELINE_RUN_MODE = old_mode
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()


def test_no_wli_mode_alias_and_intent_contract():
    assert no_wli_runner._canonical_run_mode("scan_p5_p7_c1357") == "adaptive_scan_v1"
    assert no_wli_runner._canonical_run_mode("adaptive_scan_v1") == "adaptive_scan_v1"
    assert no_wli_runner._mode_intent("scan_fast_v1") == "scan"
    assert no_wli_runner._mode_intent("adaptive_scan_v1") == "scan"
    assert no_wli_runner._mode_intent("adaptive_focus_v1") == "focus"
    assert no_wli_runner._mode_intent("adaptive_fixture_v1") == "focus"
    assert bool(no_wli_runner._mode_stage3_can_skip("scan_fast_v1")) is True
    assert bool(no_wli_runner._mode_stage3_can_skip("adaptive_scan_v1")) is True
    assert bool(no_wli_runner._mode_stage3_can_skip("adaptive_focus_v1")) is False
    assert bool(no_wli_runner._mode_stage3_can_skip("adaptive_fixture_v1")) is False
    assert bool(no_wli_runner._is_adaptive_focus_mode("adaptive_fixture_v1")) is True


def test_no_wli_runtime_config_module_matches_runner_wrappers():
    info = no_wli_runtime_config.build_run_mode_info("scan_p5_p7_c1357")
    assert info.mode_raw == "scan_p5_p7_c1357"
    assert info.mode_canonical == "adaptive_scan_v1"
    assert info.intent == "scan"
    assert info.stage3_can_skip is True
    assert info.adaptive_focus is False
    assert no_wli_runner._canonical_run_mode(info.mode_raw) == info.mode_canonical
    assert no_wli_runner._mode_intent(info.mode_raw) == info.intent
    assert no_wli_runner._mode_stage3_can_skip(info.mode_raw) is info.stage3_can_skip


def test_no_wli_runtime_config_oracle_mode_normalization():
    assert no_wli_runtime_config.normalize_oracle_mode("benchmark_only") == "benchmark_only"
    assert no_wli_runtime_config.normalize_oracle_mode("off") == "off"
    assert no_wli_runtime_config.normalize_oracle_mode("unexpected") == "off"


def test_no_wli_runtime_config_tier_presets_cover_expected_modes():
    assert no_wli_runtime_config.SMOKE_TIERS[0][0] == "smoke_p7_c5_l452"
    assert no_wli_runtime_config.FOCUS_P5_C1_ONLY_TIERS[0][0] == "focus_p5_c1_l1000"
    assert len(no_wli_runtime_config.SCAN_P5_P7_C1357_TIERS) == 8
    assert no_wli_runtime_config.ADAPTIVE_FOCUS_P7C3_ONLY_TIERS[0][0] == "focus_p7_c3_l1000"


def test_no_wli_runtime_config_build_mode_overrides_scan_fast():
    out = no_wli_runtime_config.build_run_mode_overrides(
        mode="scan_fast_v1",
        pipeline_profile_id="pid",
        oracle_assist_selection_default=True,
        stage3_continue_after_solve_default=True,
        stage12_scout_runs=6,
        stage3_phaseb_cfg={"slip_swaps": 28, "steps": 1400},
    )
    assert str(out.get("PROFILE", "")) == "pid__scan_fast_v1"
    assert int(out.get("STAGE12_ARCHIVE_KEEP", 0)) == 160
    assert int(out.get("STAGE12_PROMOTE_TOP", 0)) == 80
    assert int(out.get("STAGE3_PHASEB_CFG", {}).get("slip_swaps", 0)) == 12
    assert len(list(out.get("TIERS", []))) == 8


def test_no_wli_runtime_config_build_mode_overrides_full_is_empty():
    out = no_wli_runtime_config.build_run_mode_overrides(
        mode="full",
        pipeline_profile_id="pid",
        oracle_assist_selection_default=True,
        stage3_continue_after_solve_default=True,
        stage12_scout_runs=6,
        stage3_phaseb_cfg={"slip_swaps": 28, "steps": 1400},
    )
    assert out == {}


def test_no_wli_stage3_band_policy_default_and_oracle_paths():
    bands = [
        {"name": "very_close", "max_gap": 0.01},
        {"name": "mid", "max_gap": 0.08},
        {"name": "far", "max_gap": 1e9},
    ]
    gap_off, band_off, used_off = no_wli_stage3_band_policy.resolve_stage3_gap_and_band(
        dynamic_bands=bands,
        stage2_gate_score=0.5,
        oracle_stage3_score=0.9,
        oracle_decision_paths_enabled=False,
    )
    assert used_off is False
    assert str(band_off.get("name")) == "mid"
    assert gap_off != gap_off  # nan
    gap_on, band_on, used_on = no_wli_stage3_band_policy.resolve_stage3_gap_and_band(
        dynamic_bands=bands,
        stage2_gate_score=0.5,
        oracle_stage3_score=0.9,
        oracle_decision_paths_enabled=True,
    )
    assert used_on is True
    assert gap_on == pytest.approx(0.4)
    assert str(band_on.get("name")) == "far"


def test_no_wli_stage2_promotion_module_contract():
    assert no_wli_stage2_promotion.is_better_score_first(
        cand_score=-1.0,
        cand_match=0.2,
        best_score=-2.0,
        best_match=0.9,
    )
    out = no_wli_stage2_promotion.build_stage3_promoted_keys(
        promoted_entries=[{"key": [1, 2, 3]}, {"key": [1, 2, 3]}, {"key": [4, 5, 6]}],
        best_key=[9, 9, 9],
        key_len=3,
    )
    assert out[0] == [9, 9, 9]
    assert out.count([1, 2, 3]) == 1


def test_no_wli_adaptive_fixture_mode_preserves_external_grid():
    old_state = dict(
        mode=str(no_wli_runner.PIPELINE_RUN_MODE),
        profile=str(no_wli_runner.PROFILE),
        heartbeat=int(no_wli_runner.HEARTBEAT_SECONDS),
        tiers=list(no_wli_runner.TIERS),
        text_offsets=list(no_wli_runner.TEXT_OFFSETS),
        key_seeds=list(no_wli_runner.KEY_SEEDS),
        scoring_experiment=str(no_wli_runner.SCORING_EXPERIMENT_PROFILE),
        promote=bool(no_wli_runner.STAGE2_PROMOTE_BY_STAGE3_JUDGE),
        entry_band=bool(no_wli_runner.STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE),
    )
    try:
        no_wli_runner.PIPELINE_RUN_MODE = "adaptive_fixture_v1"
        no_wli_runner.TIERS[:] = [no_wli_runner.Tier("fixture_p11_c3_l1234", 11, 3, 1234)]
        no_wli_runner.TEXT_OFFSETS[:] = [5]
        no_wli_runner.KEY_SEEDS[:] = [777]
        no_wli_runner.HEARTBEAT_SECONDS = 444
        no_wli_runner.SCORING_EXPERIMENT_PROFILE = "off"
        no_wli_runner._apply_run_mode()
        assert len(no_wli_runner.TIERS) == 1
        assert str(no_wli_runner.TIERS[0].name) == "fixture_p11_c3_l1234"
        assert int(no_wli_runner.TIERS[0].period) == 11
        assert int(no_wli_runner.TIERS[0].columns) == 3
        assert int(no_wli_runner.TIERS[0].length) == 1234
        assert no_wli_runner.TEXT_OFFSETS == [5]
        assert no_wli_runner.KEY_SEEDS == [777]
        assert int(no_wli_runner.HEARTBEAT_SECONDS) == 444
        assert str(no_wli_runner.SCORING_EXPERIMENT_PROFILE) == "off"
        assert no_wli_runner.STAGE2_PROMOTE_BY_STAGE3_JUDGE is True
        assert no_wli_runner.STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE is True
        assert bool(no_wli_runner._mode_stage3_can_skip(no_wli_runner.PIPELINE_RUN_MODE)) is False
    finally:
        no_wli_runner.PIPELINE_RUN_MODE = old_state["mode"]
        no_wli_runner.PROFILE = old_state["profile"]
        no_wli_runner.HEARTBEAT_SECONDS = int(old_state["heartbeat"])
        no_wli_runner.TIERS[:] = list(old_state["tiers"])
        no_wli_runner.TEXT_OFFSETS[:] = list(old_state["text_offsets"])
        no_wli_runner.KEY_SEEDS[:] = list(old_state["key_seeds"])
        no_wli_runner.SCORING_EXPERIMENT_PROFILE = old_state["scoring_experiment"]
        no_wli_runner.STAGE2_PROMOTE_BY_STAGE3_JUDGE = bool(old_state["promote"])
        no_wli_runner.STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE = bool(old_state["entry_band"])


def test_no_wli_scan_fast_v1_mode_contract():
    old_mode = str(no_wli_runner.PIPELINE_RUN_MODE)
    try:
        no_wli_runner.PIPELINE_RUN_MODE = "scan_fast_v1"
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()
        assert str(no_wli_runner.SCORING_EXPERIMENT_PROFILE) == "c_min_late"
        assert bool(no_wli_runner.SCAN_STAGE2_CONTINUE_TO_GATE) is False
        assert float(no_wli_runner.SCAN_STAGE2_CONTINUE_CAP_SECONDS) == pytest.approx(0.0)
        assert float(no_wli_runner.SCAN_STAGE3_MIN_STAGE2_MATCH) == pytest.approx(0.18)
        assert float(no_wli_runner.SCAN_STAGE3_GATE_LOW_MATCH) == pytest.approx(0.18)
        assert float(no_wli_runner.SCAN_STAGE3_GATE_HIGH_MATCH) == pytest.approx(0.24)
        assert float(no_wli_runner.SCAN_TIER_TIME_CAP_SECONDS) == pytest.approx(600.0)
        assert len(no_wli_runner.TIERS) == 8
    finally:
        no_wli_runner.PIPELINE_RUN_MODE = old_mode
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()


def test_no_wli_adaptive_focus_v1_mode_contract():
    old_mode = str(no_wli_runner.PIPELINE_RUN_MODE)
    try:
        no_wli_runner.PIPELINE_RUN_MODE = "adaptive_focus_v1"
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()
        assert str(no_wli_runner.SCORING_EXPERIMENT_PROFILE) == "c_min_late"
        assert no_wli_runner.STAGE2_PROMOTE_BY_STAGE3_JUDGE is True
        assert no_wli_runner.STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE is True
        assert bool(no_wli_runner._mode_stage3_can_skip(no_wli_runner.PIPELINE_RUN_MODE)) is False
        assert len(no_wli_runner.TIERS) == 2
    finally:
        no_wli_runner.PIPELINE_RUN_MODE = old_mode
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()


def test_no_wli_adaptive_focus_p7c3_only_mode_contract():
    old_mode = str(no_wli_runner.PIPELINE_RUN_MODE)
    try:
        no_wli_runner.PIPELINE_RUN_MODE = "adaptive_focus_v1_p7c3_only"
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()
        assert str(no_wli_runner.SCORING_EXPERIMENT_PROFILE) == "c_min_late"
        assert no_wli_runner.STAGE2_PROMOTE_BY_STAGE3_JUDGE is True
        assert no_wli_runner.STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE is True
        assert bool(no_wli_runner._mode_stage3_can_skip(no_wli_runner.PIPELINE_RUN_MODE)) is False
        assert bool(no_wli_runner._is_adaptive_focus_mode(no_wli_runner.PIPELINE_RUN_MODE)) is True
        assert str(no_wli_runner.STAGE2_JUDGE_POLICY) == "search_only"
        assert len(no_wli_runner.TIERS) == 1
        assert str(no_wli_runner.TIERS[0].name) == "focus_p7_c3_l1000"
    finally:
        no_wli_runner.PIPELINE_RUN_MODE = old_mode
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()


def test_no_wli_outcome_code_mapping_contract():
    assert no_wli_runner._derive_outcome_code(status="skipped_proven", stop_reason="autoskip_proven") == "skipped_proven"
    assert no_wli_runner._derive_outcome_code(status="solved", stop_reason="solved_stage3") == "solved"
    assert no_wli_runner._derive_outcome_code(
        status="unsolved",
        stop_reason="scan_skip_stage3_stage2_cap_weak_stage2:best2_match=0.101:threshold=0.150",
    ) == "stage2_cap"
    assert no_wli_runner._derive_outcome_code(
        status="unsolved",
        stop_reason="scan_skip_stage3_weak_stage2:best2_match=0.101:threshold=0.150",
    ) == "weak_stage2"
    assert no_wli_runner._derive_outcome_code(
        status="unsolved",
        stop_reason="time_cap_before_stage3:elapsed=601.0:cap=600.0",
    ) == "time_cap"
    assert no_wli_runner._derive_outcome_code(status="stalled", stop_reason="stalled_no_improve") == "stalled_stage3"
    assert no_wli_runner._derive_outcome_code(status="error", stop_reason="boom") == "crash"


def test_no_wli_build_stage3_experiment_cfg_contract(tmp_path: Path):
    assets = tmp_path / "span_assets"
    ecdf_root = assets / "ecdf" / "span_x"
    ecdf_root.mkdir(parents=True, exist_ok=True)
    (assets / "combined_calibration.json").write_text("{}", encoding="utf-8")

    cfg_a = no_wli_runner._build_stage3_experiment_cfg(
        profile_name="a_baseline",
        direction=no_wli_runner.Direction.LTR,
        span_assets_dir=assets,
    )
    assert str(cfg_a.get("span_hamming_mode", "")) == "off"
    assert bool(cfg_a.get("span_hamming_enabled", True)) is False

    cfg_c = no_wli_runner._build_stage3_experiment_cfg(
        profile_name="c_min_late",
        direction=no_wli_runner.Direction.LTR,
        span_assets_dir=assets,
        char_pct_min_override=0.37,
    )
    assert str(cfg_c.get("span_hamming_mode", "")) == "calibrated"
    assert str(cfg_c.get("span_hamming_gate_fail_policy", "")) == "char_only"
    assert float(cfg_c.get("span_hamming_char_pct_min", 0.0)) == pytest.approx(0.37)


def test_no_wli_adaptive_focus_source_has_phase_experiment_switch():
    runner_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(encoding="utf-8")
    policy_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/stage3_policy.py").read_text(encoding="utf-8")
    runtime_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/iteration_runtime.py").read_text(
        encoding="utf-8"
    )
    pre_stage3_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/iteration_pre_stage3.py").read_text(
        encoding="utf-8"
    )
    matrix_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py").read_text(
        encoding="utf-8"
    )
    text = (
        runner_text
        + "\n"
        + policy_text
        + "\n"
        + runtime_text
        + "\n"
        + pre_stage3_text
        + "\n"
        + matrix_text
    )
    assert "stage3_phaseA_experiment" in text
    assert "stage3_phaseB_experiment" in text
    assert "phaseA_experiment" in text
    assert "phaseB_experiment" in text
    assert "policy=phaseA_only" in text
    assert "scan_stage3_gate_low_match" in text
    assert "scan_stage3_gate_high_match" in text


def test_no_wli_two_phase_gate_and_phaseb_selection_use_pct_space():
    runner_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(
        encoding="utf-8"
    )
    two_phase_text = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py"
    ).read_text(encoding="utf-8")
    span_summary_text = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/stage3_span_summary.py"
    ).read_text(encoding="utf-8")
    text = runner_text + "\n" + two_phase_text + "\n" + span_summary_text
    assert "end_score_pct" in text
    assert "best_delta_pct" in text
    assert "phaseA_basins_judged_by_span=" in text
    assert "span_basin_judge_k_cfg" in text
    assert "span_active_rate_source" in text


def test_no_wli_stage3_search_contract_and_span_judge_path():
    cfg = no_wli_runner._stage3_char4_avg_fulltext_search_cfg(direction=no_wli_runner.Direction.LTR)
    assert str(cfg.get("objective", "")).startswith("avg.")
    assert str(cfg.get("avg_window_policy", "")) == "full_text"
    assert bool(cfg.get("span_hamming_enabled", True)) is False

    runner_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(encoding="utf-8")
    runtime_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/iteration_runtime.py").read_text(encoding="utf-8")
    oracle_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/oracle_precheck.py").read_text(encoding="utf-8")
    bridge_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py").read_text(
        encoding="utf-8"
    )
    span_summary_text = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/stage3_span_summary.py"
    ).read_text(encoding="utf-8")
    text = (
        runner_text
        + "\n"
        + bridge_text
        + "\n"
        + runtime_text
        + "\n"
        + oracle_text
        + "\n"
        + span_summary_text
    )
    assert "_stage3_char4_avg_fulltext_search_cfg" in text
    assert "stage3_search_cfg_fn=state[\"_stage3_char4_avg_fulltext_search_cfg\"]" in bridge_text
    assert "scorer_stage3_search = stage3_search_cfg_fn(direction=direction)" in runtime_text
    assert "disable_char_pct_gate=bool(stage3_phase_switch_enabled)" in runtime_text
    assert "phaseA_basins_judged_by_span=" in text
    assert "span_judge_time_s=" in text
    assert "STAGE2_JUDGE_POLICY = \"search_only\"" in text
    assert "stage2-judge-policy" in text


def test_no_wli_stage2_judge_pool_limit_for_avg_fulltext():
    old_mode = str(no_wli_runner.PIPELINE_RUN_MODE)
    try:
        no_wli_runner.PIPELINE_RUN_MODE = "focus_500_nowli"
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()
        assert no_wli_runner.STAGE2_PROMOTE_BY_STAGE3_JUDGE is True
        assert no_wli_runner.STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE is True
        limit_avg = no_wli_runner._stage2_judge_pool_limit(
            ranked_count=500,
            archive_keep=192,
            stage3_scorer_cfg={"objective": "avg.logp.win20", "avg_window_policy": "full_text"},
        )
        assert limit_avg == 192
        limit_pct = no_wli_runner._stage2_judge_pool_limit(
            ranked_count=500,
            archive_keep=192,
            stage3_scorer_cfg={"objective": "pct.logp.win10"},
        )
        assert limit_pct == no_wli_runner.SAVE_STAGE2_TOPK
    finally:
        no_wli_runner.PIPELINE_RUN_MODE = old_mode
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()


def test_no_wli_proven_autoskip_is_wired():
    runner_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(
        encoding="utf-8"
    )
    run_environment_text = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/run_environment.py"
    ).read_text(encoding="utf-8")
    setup_logging_text = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/setup_logging.py"
    ).read_text(encoding="utf-8")
    autoskip_text = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/autoskip_proven.py"
    ).read_text(encoding="utf-8")
    text = (
        runner_text
        + "\n"
        + run_environment_text
        + "\n"
        + setup_logging_text
        + "\n"
        + autoskip_text
    )
    assert "AUTOSKIP_PROVEN = True" in text
    assert "FORCE_RERUN_PROVEN = True" in text
    assert ("_load_proven_solved_index(" in text) or ("load_proven_index_fn(" in text)
    assert "status=\"skipped_proven\"" in text
    assert "setup: autoskip_proven=" in text


def test_sub_then_col_scorer_impl_is_pinned():
    assert sub_runner.SCORER_SUB.get("impl") == sub_runner.SCORER_IMPL
    assert sub_runner.SCORER_FULL.get("impl") == sub_runner.SCORER_IMPL
    for profile_cfg in sub_runner.STAGEAB_SCORER_PROFILES.values():
        assert profile_cfg.get("impl") == sub_runner.SCORER_IMPL


def test_sub_then_col_repo_root_matches_repo_root():
    repo_root = Path(__file__).resolve().parents[2]
    assert sub_runner._repo_root() == repo_root


def test_col_then_sub_campaign_config_disables_tier_sweep_filters():
    old_state = dict(
        tiers_period_sweep=str(col_runner.TIERS_PERIOD_SWEEP),
        tiers_min_columns=col_runner.TIERS_MIN_COLUMNS,
        tiers_regex_override=col_runner.TIERS_REGEX_OVERRIDE,
        tiers=list(col_runner.TIERS),
        run_mode=str(col_runner.PIPELINE_RUN_MODE),
        profile=str(col_runner.PROFILE),
        heartbeat=int(col_runner.HEARTBEAT_SECONDS),
        key_seeds=list(col_runner.KEY_SEEDS),
        key_seeds_override=None if col_runner.KEY_SEEDS_OVERRIDE is None else list(col_runner.KEY_SEEDS_OVERRIDE),
        text_offsets=list(col_runner.TEXT_OFFSETS),
    )
    try:
        col_runner.TIERS_PERIOD_SWEEP = "p10_only"
        col_runner.TIERS_MIN_COLUMNS = 7
        col_runner.configure_campaign_run(
            run_seed=777,
            period=11,
            columns=3,
            length=1234,
            tier_name="community_col_then_sub_p11_c3_l1234",
            run_mode="full",
            profile_name="community_baseline_resume_v1_1",
            heartbeat_seconds=3600,
            autoskip_proven=False,
            force_rerun_proven=True,
            avoid_repeat_fail=False,
            text_offsets=[0],
            tiers_regex_override=None,
            scorer_impl="numpy",
        )
        assert col_runner.TIERS_PERIOD_SWEEP == "none"
        assert col_runner.TIERS_MIN_COLUMNS is None
        col_runner._apply_run_mode()
        col_runner._apply_runtime_overrides()
        assert len(col_runner.TIERS) == 1
        assert int(col_runner.TIERS[0].period) == 11
        assert int(col_runner.TIERS[0].columns) == 3
    finally:
        col_runner.TIERS_PERIOD_SWEEP = old_state["tiers_period_sweep"]
        col_runner.TIERS_MIN_COLUMNS = old_state["tiers_min_columns"]
        col_runner.TIERS_REGEX_OVERRIDE = old_state["tiers_regex_override"]
        col_runner.TIERS = list(old_state["tiers"])
        col_runner.PIPELINE_RUN_MODE = old_state["run_mode"]
        col_runner.PROFILE = old_state["profile"]
        col_runner.HEARTBEAT_SECONDS = int(old_state["heartbeat"])
        col_runner.KEY_SEEDS = list(old_state["key_seeds"])
        col_runner.KEY_SEEDS_OVERRIDE = (
            None
            if old_state["key_seeds_override"] is None
            else list(old_state["key_seeds_override"])
        )
        col_runner.TEXT_OFFSETS = list(old_state["text_offsets"])


def test_col_then_sub_campaign_schedule_override_changes_effective_scorers():
    old_state = dict(
        run_mode=str(col_runner.PIPELINE_RUN_MODE),
        profile=str(col_runner.PROFILE),
        heartbeat=int(col_runner.HEARTBEAT_SECONDS),
        key_seeds=list(col_runner.KEY_SEEDS),
        key_seeds_override=None if col_runner.KEY_SEEDS_OVERRIDE is None else list(col_runner.KEY_SEEDS_OVERRIDE),
        text_offsets=list(col_runner.TEXT_OFFSETS),
        tiers=list(col_runner.TIERS),
        tiers_regex_override=col_runner.TIERS_REGEX_OVERRIDE,
        tiers_period_sweep=str(col_runner.TIERS_PERIOD_SWEEP),
        tiers_min_columns=col_runner.TIERS_MIN_COLUMNS,
        scorer_stage1=copy.deepcopy(col_runner.SCORER_STAGE1),
        scorer_stage1_hard=copy.deepcopy(col_runner.SCORER_STAGE1_HARD_RERANK),
        scorer_full=copy.deepcopy(col_runner.SCORER_FULL),
        scorer_impl=str(col_runner.SCORER_IMPL),
    )
    try:
        col_runner.configure_campaign_run(
            run_seed=333,
            period=10,
            columns=7,
            length=1234,
            tier_name="community_col_then_sub_p10_c7_l1234",
            run_mode="full",
            profile_name="community_schedule_char34_only",
            heartbeat_seconds=3600,
            autoskip_proven=False,
            force_rerun_proven=True,
            avoid_repeat_fail=False,
            text_offsets=[0],
            tiers_regex_override=None,
            scorer_impl="numpy",
            scorer_schedule={
                "early": SCHEDULE_EARLY_CHAR34_ONLY,
                "middle": SCHEDULE_MIDDLE_CHAR34_ONLY,
                "late": SCHEDULE_LATE_CHAR34_ONLY,
            },
        )
        assert dict(col_runner.SCORER_STAGE1.get("char_weights", {})) == {3: 0.2, 4: 0.8}
        assert bool(col_runner.SCORER_STAGE1.get("use_word_breaks", True)) is False
        assert dict(col_runner.SCORER_FULL.get("char_weights", {})) == {3: 0.2, 4: 0.8}
        assert bool(col_runner.SCORER_FULL.get("use_word_breaks", True)) is False
        assert dict(col_runner.SCORER_FULL.get("wli_weights", {})) == {}
        assert str(col_runner.SCORER_FULL.get("objective", "")) == "pct.logp.win10"
    finally:
        col_runner.PIPELINE_RUN_MODE = old_state["run_mode"]
        col_runner.PROFILE = old_state["profile"]
        col_runner.HEARTBEAT_SECONDS = int(old_state["heartbeat"])
        col_runner.KEY_SEEDS = list(old_state["key_seeds"])
        col_runner.KEY_SEEDS_OVERRIDE = (
            None
            if old_state["key_seeds_override"] is None
            else list(old_state["key_seeds_override"])
        )
        col_runner.TEXT_OFFSETS = list(old_state["text_offsets"])
        col_runner.TIERS = list(old_state["tiers"])
        col_runner.TIERS_REGEX_OVERRIDE = old_state["tiers_regex_override"]
        col_runner.TIERS_PERIOD_SWEEP = old_state["tiers_period_sweep"]
        col_runner.TIERS_MIN_COLUMNS = old_state["tiers_min_columns"]
        col_runner.SCORER_STAGE1 = copy.deepcopy(old_state["scorer_stage1"])
        col_runner.SCORER_STAGE1_HARD_RERANK = copy.deepcopy(old_state["scorer_stage1_hard"])
        col_runner.SCORER_FULL = copy.deepcopy(old_state["scorer_full"])
        col_runner.SCORER_IMPL = old_state["scorer_impl"]


def test_sub_then_col_campaign_schedule_override_changes_effective_scorers():
    old_state = dict(
        run_mode=str(sub_runner.PIPELINE_RUN_MODE),
        profile=str(sub_runner.PROFILE),
        heartbeat=int(sub_runner.HEARTBEAT_SECONDS),
        key_seeds=list(sub_runner.KEY_SEEDS),
        key_seeds_override=None if sub_runner.KEY_SEEDS_OVERRIDE is None else list(sub_runner.KEY_SEEDS_OVERRIDE),
        text_offsets=list(sub_runner.TEXT_OFFSETS),
        tiers=list(sub_runner.TIERS),
        tiers_regex_override=sub_runner.TIERS_REGEX_OVERRIDE,
        scorer_sub=copy.deepcopy(sub_runner.SCORER_SUB),
        scorer_full=copy.deepcopy(sub_runner.SCORER_FULL),
        scorer_profile=str(sub_runner.STAGEAB_SCORER_PROFILE),
        scorer_profiles=copy.deepcopy(sub_runner.STAGEAB_SCORER_PROFILES),
        scorer_impl=str(sub_runner.SCORER_IMPL),
    )
    try:
        sub_runner.configure_campaign_run(
            run_seed=444,
            period=10,
            columns=7,
            length=1234,
            tier_name="community_sub_then_col_p10_c7_l1234",
            run_mode="focus_sub_then_col",
            profile_name="community_schedule_char34_only",
            heartbeat_seconds=3600,
            autoskip_proven=False,
            force_rerun_proven=True,
            avoid_repeat_fail=False,
            text_offsets=[0],
            tiers_regex_override=None,
            scorer_impl="numpy",
            scorer_schedule={
                "early": SCHEDULE_EARLY_CHAR34_ONLY,
                "middle": SCHEDULE_MIDDLE_CHAR34_ONLY,
                "late": SCHEDULE_LATE_CHAR34_ONLY,
            },
        )
        assert str(sub_runner.STAGEAB_SCORER_PROFILE) == sub_runner.StageABScorerProfile.A_CHAR34.value
        assert dict(sub_runner.SCORER_SUB.get("wli_weights", {})) == {}
        assert bool(sub_runner.SCORER_SUB.get("use_word_breaks", True)) is False
        assert dict(sub_runner.SCORER_FULL.get("wli_weights", {})) == {}
        assert bool(sub_runner.SCORER_FULL.get("use_word_breaks", True)) is False
        assert str(sub_runner.SCORER_FULL.get("objective", "")) == "pct.logp.win10"
    finally:
        sub_runner.PIPELINE_RUN_MODE = old_state["run_mode"]
        sub_runner.PROFILE = old_state["profile"]
        sub_runner.HEARTBEAT_SECONDS = int(old_state["heartbeat"])
        sub_runner.KEY_SEEDS = list(old_state["key_seeds"])
        sub_runner.KEY_SEEDS_OVERRIDE = (
            None
            if old_state["key_seeds_override"] is None
            else list(old_state["key_seeds_override"])
        )
        sub_runner.TEXT_OFFSETS = list(old_state["text_offsets"])
        sub_runner.TIERS = list(old_state["tiers"])
        sub_runner.TIERS_REGEX_OVERRIDE = old_state["tiers_regex_override"]
        sub_runner.SCORER_SUB = copy.deepcopy(old_state["scorer_sub"])
        sub_runner.SCORER_FULL = copy.deepcopy(old_state["scorer_full"])
        sub_runner.STAGEAB_SCORER_PROFILE = old_state["scorer_profile"]
        sub_runner.STAGEAB_SCORER_PROFILES = copy.deepcopy(old_state["scorer_profiles"])
        sub_runner.SCORER_IMPL = old_state["scorer_impl"]


def test_no_wli_campaign_schedule_override_changes_effective_scorers():
    old_mode = str(no_wli_runner.PIPELINE_RUN_MODE)
    old_profile_id = str(no_wli_runner.NO_WLI_PIPELINE_PROFILE_ID)
    old_impl = str(no_wli_runner.SCORER_IMPL)
    old_stage3_impl = str(no_wli_runner.SCORER_STAGE3_IMPL_AVG_FULLTEXT)
    try:
        no_wli_runner.NO_WLI_PIPELINE_PROFILE_ID = old_profile_id
        no_wli_runner.SCORER_IMPL = old_impl
        no_wli_runner.SCORER_STAGE3_IMPL_AVG_FULLTEXT = old_stage3_impl
        no_wli_runner._apply_profile_defaults()
        no_wli_runner.configure_campaign_run(
            run_seed=555,
            period=7,
            columns=3,
            length=1000,
            tier_name="community_no_wli_p7_c3_l1000",
            run_mode="adaptive_focus_v1_p7c3_only",
            profile_name=old_profile_id,
            heartbeat_seconds=3600,
            autoskip_proven=False,
            force_rerun_proven=True,
            avoid_repeat_fail=False,
            text_offsets=[0],
            tiers_regex_override=None,
            scorer_impl="numpy",
            scorer_stage3_impl_avg_fulltext="numpy",
            scorer_schedule={
                "early": SCHEDULE_EARLY_A_CHAR34,
                "middle": SCHEDULE_MIDDLE_M_CHAR34,
                "late": SCHEDULE_LATE_B_CHAR34,
            },
        )
        assert str(no_wli_runner.SCORER_STAGE1_LABEL) == "A_char34"
        assert str(no_wli_runner.SCORER_STAGE2_LABEL) == "M_char34"
        assert str(no_wli_runner.SCORER_STAGE3_LABEL) == "B_char34"
        assert dict(no_wli_runner.SCORER_STAGE1.get("char_weights", {})) == {3: 0.2, 4: 0.8}
        assert dict(no_wli_runner.SCORER_STAGE2.get("char_weights", {})) == {3: 0.2, 4: 0.8}
        assert dict(no_wli_runner.SCORER_FULL.get("char_weights", {})) == {3: 0.2, 4: 0.8}
        assert bool(no_wli_runner.SCORER_FULL.get("use_word_breaks", True)) is False
        assert dict(no_wli_runner.SCORER_FULL.get("wli_weights", {})) == {}
        assert str(no_wli_runner.SCORER_FULL.get("objective", "")) == "pct.logp.win10"
    finally:
        no_wli_runner.NO_WLI_PIPELINE_PROFILE_ID = old_profile_id
        no_wli_runner.PIPELINE_RUN_MODE = old_mode
        no_wli_runner.SCORER_IMPL = old_impl
        no_wli_runner.SCORER_STAGE3_IMPL_AVG_FULLTEXT = old_stage3_impl
        no_wli_runner._apply_profile_defaults()
        no_wli_runner._apply_run_mode()


def test_runners_expose_campaign_config_entrypoint():
    assert callable(getattr(col_runner, "configure_campaign_run", None))
    assert callable(getattr(sub_runner, "configure_campaign_run", None))
    assert callable(getattr(no_wli_runner, "configure_campaign_run", None))


def test_periodic_sub_trans_runners_avoid_direct_scalar_scorer_calls():
    repo_root = Path(__file__).resolve().parents[2]
    runner_paths = [
        repo_root / "tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py",
        repo_root / "tools/benchmarks/periodic_sub_trans/no_wli/runner.py",
        repo_root / "tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py",
    ]
    pat = re.compile(r"scorer_[A-Za-z0-9_]+(?:_runtime)?\.score\(")
    for path in runner_paths:
        text = path.read_text(encoding="utf-8")
        assert pat.search(text) is None, f"direct scalar scorer call found in {path}"


def test_no_wli_stage3_stop_log_has_entry_diagnostics():
    runner_path = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py")
    run_config_builder_path = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py"
    )
    setup_logging_path = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/setup_logging.py"
    )
    stage3_flow_path = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py"
    )
    stage1_path = Path("tools/benchmarks/periodic_sub_trans/no_wli/stage1_substitution.py")
    stage2_path = Path("tools/benchmarks/periodic_sub_trans/no_wli/stage2_search.py")
    commit_path = Path("tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_commit.py")
    bridges_path = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py")
    text = (
        runner_path.read_text(encoding="utf-8")
        + "\n"
        + run_config_builder_path.read_text(encoding="utf-8")
        + "\n"
        + setup_logging_path.read_text(encoding="utf-8")
        + "\n"
        + stage1_path.read_text(encoding="utf-8")
        + "\n"
        + stage2_path.read_text(encoding="utf-8")
        + "\n"
        + stage3_flow_path.read_text(encoding="utf-8")
        + "\n"
        + commit_path.read_text(encoding="utf-8")
        + "\n"
        + bridges_path.read_text(encoding="utf-8")
    )
    assert "entry_score_source=" in text
    assert "entry_policy=" in text
    assert "entry_target_before_cap=" in text
    assert "entry_mutation_calls_per_promoted=" in text
    assert "period_scale=(init=" in text
    assert "promoted_best_match=" in text
    assert "best2_in_promoted=" in text
    assert "best2_in_stage2_topk=" in text
    assert "spearman_score_match=" in text
    assert "setup: ecdf_guard=" in text
    assert "oracle_assist_selection=" in text
    assert "stage1-diversity" in text
    assert "oracle_scores=dict(" in text
    assert "score_minus_oracle=dict(" in text
    assert "stage2_diagnostics" in text
    assert "stage3_diagnostics" in text
    assert "period_scaling=dict(" in text
    assert "Per-instance checkpoint (crash-safe)" in text
    assert ("_append_csv_row_common(" in text) or ("append_csv_row_common_fn=" in text)
    assert "history_rows_written" in text


def test_no_wli_score_first_comparator_behaviour():
    assert no_wli_runner._is_better_score_first(-10.0, 0.20, -11.0, 0.90) is True
    assert no_wli_runner._is_better_score_first(-11.5, 0.95, -11.0, 0.10) is False
    # Tie on score falls back to higher match (telemetry-only tie-break).
    assert no_wli_runner._is_better_score_first(-11.0, 0.30, -11.0, 0.20) is True


def test_no_wli_stage3_candidate_compare_preserves_solved_incumbent():
    # Unsolved candidate cannot replace solved incumbent, even if score is higher.
    assert (
        no_wli_runner._is_better_stage3_candidate_preserving_solve(
            cand_score=-9.5,
            cand_match=0.25,
            best_score=-10.1,
            best_match=0.95,
            score_first=True,
        )
        is False
    )
    # Solved candidate always upgrades an unsolved incumbent.
    assert (
        no_wli_runner._is_better_stage3_candidate_preserving_solve(
            cand_score=-11.0,
            cand_match=0.92,
            best_score=-10.0,
            best_match=0.40,
            score_first=True,
        )
        is True
    )


def test_no_wli_run_config_includes_resolved_tiers():
    text = (
        Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(
            encoding="utf-8"
        )
        + "\n"
        + Path("tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py").read_text(
            encoding="utf-8"
        )
    )
    assert "tiers=[" in text
    assert ("for t in TIERS" in text) or ('for t in state["TIERS"]' in text)


def test_no_wli_run_outputs_use_repo_relative_span_asset_paths():
    root = no_wli_runner._repo_root()
    abs_assets = root / "assets" / "scoring" / "span_hamming_nose_assets_v1"
    rel_assets = no_wli_runner._to_repo_rel_path(abs_assets, root=root)
    assert not Path(rel_assets).is_absolute()
    assert rel_assets.startswith("assets/")

    text = (
        Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(
            encoding="utf-8"
        )
        + "\n"
        + Path("tools/benchmarks/periodic_sub_trans/no_wli/run_startup.py").read_text(
            encoding="utf-8"
        )
        + "\n"
        + Path(
            "tools/benchmarks/periodic_sub_trans/no_wli/run_manifest_setup.py"
        ).read_text(encoding="utf-8")
    )
    assert (
        "_to_repo_rel_path(span_assets_dir, root=root)" in text
        or "to_repo_rel_path_fn(span_assets_dir, root)" in text
    )
    assert "_scoring_meta_for_output(" in text or "scoring_meta_for_output_fn(" in text


def test_stage2_promotion_uses_kept_pool_in_no_wli_and_colsub():
    no_wli_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/stage2_search.py").read_text(encoding="utf-8")
    colsub_text = Path("tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py").read_text(encoding="utf-8")
    assert "stage2_kept_by_score = list(stage2_ranked)" in no_wli_text
    assert "stage2_kept_by_match = sorted(" in no_wli_text
    assert "if r < len(stage2_kept_by_score):" in no_wli_text
    assert "stage2_kept_by_score = list(stage2_ranked)" in colsub_text
    assert "stage2_kept_by_match = sorted(" in colsub_text
    assert "if r < len(stage2_kept_by_score):" in colsub_text


def test_stall_stage_limit_is_applied_in_stage3_stop_no_wli_and_colsub():
    no_wli_text = (
        Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(encoding="utf-8")
        + "\n"
        + Path("tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py").read_text(encoding="utf-8")
    )
    colsub_text = Path("tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py").read_text(encoding="utf-8")
    assert 'stop_reason = "stalled_no_improve" if int(stall_stage_limit) <= 1 else "unsolved"' in no_wli_text
    assert 'stop_reason = "stalled_no_improve" if int(STALL_STAGE_LIMIT) <= 1 else "unsolved"' in colsub_text


def test_no_wli_elitism_injects_best_entry_into_ranked_pool():
    ranked = [
        {"key": [1, 2, 3], "score": -4.0, "match": 0.10},
        {"key": [2, 1, 3], "score": -4.2, "match": 0.09},
    ]
    best = {"key": [9, 9, 9], "score": -5.0, "match": 0.15}
    out = no_wli_runner._ensure_best_entry_in_ranked(ranked_entries=ranked, best_entry=best)
    assert out[0]["key"] == [9, 9, 9]
    assert sum(1 for e in out if e.get("key") == [9, 9, 9]) == 1


def test_no_wli_elitism_forces_best_entry_into_promoted_pool_with_cap():
    promoted = [
        {"key": [1, 2, 3], "score": -4.0, "match": 0.10},
        {"key": [2, 1, 3], "score": -4.2, "match": 0.09},
    ]
    best = {"key": [9, 9, 9], "score": -5.0, "match": 0.15}
    out, has_best = no_wli_runner._ensure_best_entry_in_promoted(
        promoted_entries=promoted,
        best_entry=best,
        promote_top=2,
    )
    assert has_best is True
    assert len(out) == 2
    assert any(e.get("key") == [9, 9, 9] for e in out)


def test_no_wli_stage3_seed_builder_starts_from_stage2_best_and_dedupes():
    promoted = [
        {"key": [1, 2, 3]},
        {"key": [4, 5, 6]},
        {"key": [1, 2, 3]},
    ]
    out = no_wli_runner._build_stage3_promoted_keys(
        promoted_entries=promoted,
        best_key=[9, 9, 9],
        key_len=3,
    )
    assert out[0] == [9, 9, 9]
    assert out.count([1, 2, 3]) == 1
    assert out.count([4, 5, 6]) == 1


def test_no_wli_ecdf_guard_wraps_avg_fulltext_runtime():
    class Dummy:
        def __init__(self):
            self._ecdf = None

        def _ensure_ecdf(self):
            return 123

    d = Dummy()
    no_wli_runner._guard_no_ecdf_usage(
        scorer_runtime=d,
        scorer_cfg={"objective": "avg.logp.win20", "avg_window_policy": "full_text"},
        stage_label="stageX",
    )
    with pytest.raises(RuntimeError, match="ECDF guard failed"):
        d._ensure_ecdf()


def test_no_wli_ecdf_guard_rejects_preinitialized_ecdf():
    class Dummy:
        def __init__(self):
            self._ecdf = object()

    with pytest.raises(RuntimeError, match="unexpectedly has initialized ECDF"):
        no_wli_runner._guard_no_ecdf_usage(
            scorer_runtime=Dummy(),
            scorer_cfg={"objective": "avg.logp.win20", "avg_window_policy": "full_text"},
            stage_label="stageY",
        )


def test_solver_progress_model_label_handles_avg_full_text():
    src = inspect.getsource(solver_base_mod.SolverBase._progress_model_label)
    assert "avg_window_policy" in src
    assert "full_text" in src


def test_runner_oracle_mode_defaults_off():
    assert str(col_runner.ORACLE_MODE) == "off"
    assert str(sub_runner.ORACLE_MODE) == "off"
    assert str(no_wli_runner.ORACLE_MODE) == "off"


def test_no_wli_oracle_decision_paths_are_mode_gated_and_reported():
    runner_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(
        encoding="utf-8"
    )
    stage3_flow_text = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py"
    ).read_text(encoding="utf-8")
    seeding_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/stage3_seeding.py").read_text(
        encoding="utf-8"
    )
    two_phase_text = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py"
    ).read_text(encoding="utf-8")
    pipeline_exec_text = Path(
        "tools/benchmarks/periodic_sub_trans/no_wli/run_pipeline_execution.py"
    ).read_text(encoding="utf-8")
    text = (
        runner_text
        + "\n"
        + stage3_flow_text
        + "\n"
        + seeding_text
        + "\n"
        + two_phase_text
        + "\n"
        + pipeline_exec_text
    )
    assert 'ORACLE_MODE = "off"' in text
    assert "oracle_mode=str(oracle_mode)" in text
    assert "oracle_consulted_in_decisions" in text
    assert "_resolve_stage3_gap_and_band_external" in text
    assert "stage2_gap_to_oracle, band, oracle_used_for_stage3_band =" in text
    assert 'oracle_used_for_stage3_band", False' in text
    assert "score_first=(not bool(oracle_assist_selection_effective))" in text


def test_col_then_sub_oracle_decision_paths_are_mode_gated_and_reported():
    text = Path("tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py").read_text(
        encoding="utf-8"
    )
    assert 'ORACLE_MODE = "off"' in text
    assert "oracle_mode=str(oracle_mode)" in text
    assert "oracle_consulted_in_decisions" in text
    assert "stage1_oracle_guard = bool(" in text
    assert "oracle_decision_paths_enabled" in text
    assert (
        "if bool(oracle_decision_paths_enabled) and np.isfinite(stage2_gate_score) and "
        "np.isfinite(oracle_s23):" in text
    )
    assert "if bool(oracle_decision_paths_enabled) and bool(STAGE3_USE_ORACLE_GUIDE_STOP):" in text


def test_sub_then_col_oracle_decision_paths_are_mode_gated_and_reported():
    text = Path("tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py").read_text(
        encoding="utf-8"
    )
    assert 'ORACLE_MODE = "off"' in text
    assert "oracle_mode=str(oracle_mode)" in text
    assert "oracle_consulted_in_decisions" in text
    assert "if bool(oracle_decision_paths_enabled) and bool(STAGE3_USE_ORACLE_GUIDE_STOP):" in text
