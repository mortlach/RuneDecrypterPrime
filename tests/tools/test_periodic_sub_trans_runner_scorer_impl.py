from __future__ import annotations

import re
from pathlib import Path
import inspect

import pytest

from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
from tools.benchmarks.periodic_sub_trans.col_then_sub import runner as col_runner
from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli_runner
from tools.benchmarks.periodic_sub_trans.sub_then_col import runner as sub_runner
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
    no_wli_runner._apply_profile_defaults()
    no_wli_runner._apply_run_mode()
    assert no_wli_runner.TIERS
    assert int(no_wli_runner.TIERS[0].period) == 5
    assert int(no_wli_runner.TIERS[0].columns) == 1


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
        assert no_wli_runner.STAGE2_PROMOTE_BY_STAGE3_JUDGE is False
        assert no_wli_runner.STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE is False
        assert no_wli_runner.ORACLE_ASSIST_SELECTION is False
        assert no_wli_runner.STAGE3_CONTINUE_AFTER_SOLVE is False
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
    text = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(encoding="utf-8")
    assert "AUTOSKIP_PROVEN = True" in text
    assert "FORCE_RERUN_PROVEN = False" in text
    assert "_load_proven_solved_index(" in text
    assert "status=\"skipped_proven\"" in text
    assert "[pipeline_no_wli] setup: autoskip_proven=" in text


def test_sub_then_col_scorer_impl_is_pinned():
    assert sub_runner.SCORER_SUB.get("impl") == sub_runner.SCORER_IMPL
    assert sub_runner.SCORER_FULL.get("impl") == sub_runner.SCORER_IMPL
    for profile_cfg in sub_runner.STAGEAB_SCORER_PROFILES.values():
        assert profile_cfg.get("impl") == sub_runner.SCORER_IMPL


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
    path = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py")
    text = path.read_text(encoding="utf-8")
    assert "entry_score_source=" in text
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
    assert "_append_csv_row(hist, hist_row)" in text
    assert "history_rows_written" in text


def test_no_wli_score_first_comparator_behaviour():
    assert no_wli_runner._is_better_score_first(-10.0, 0.20, -11.0, 0.90) is True
    assert no_wli_runner._is_better_score_first(-11.5, 0.95, -11.0, 0.10) is False
    # Tie on score falls back to higher match (telemetry-only tie-break).
    assert no_wli_runner._is_better_score_first(-11.0, 0.30, -11.0, 0.20) is True


def test_no_wli_run_config_includes_resolved_tiers():
    text = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(encoding="utf-8")
    assert "tiers=[" in text
    assert "for t in TIERS" in text


def test_stage2_promotion_uses_kept_pool_in_no_wli_and_colsub():
    no_wli_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(encoding="utf-8")
    colsub_text = Path("tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py").read_text(encoding="utf-8")
    assert "stage2_kept_by_score = list(stage2_ranked)" in no_wli_text
    assert "stage2_kept_by_match = sorted(" in no_wli_text
    assert "if r < len(stage2_kept_by_score):" in no_wli_text
    assert "stage2_kept_by_score = list(stage2_ranked)" in colsub_text
    assert "stage2_kept_by_match = sorted(" in colsub_text
    assert "if r < len(stage2_kept_by_score):" in colsub_text


def test_stall_stage_limit_is_applied_in_stage3_stop_no_wli_and_colsub():
    no_wli_text = Path("tools/benchmarks/periodic_sub_trans/no_wli/runner.py").read_text(encoding="utf-8")
    colsub_text = Path("tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py").read_text(encoding="utf-8")
    assert 'stop_reason = "stalled_no_improve" if int(STALL_STAGE_LIMIT) <= 1 else "unsolved"' in no_wli_text
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
