from __future__ import annotations

from typing import Any, Callable, Mapping

from tools.benchmarks.periodic_sub_trans.no_wli.runtime_mode_presets import (
    ADAPTIVE_FOCUS_P7C3_ONLY_TIERS,
    ADAPTIVE_FOCUS_V1_TIERS,
    ADAPTIVE_SCAN_V1_STAGE2_EXACT_PASS1_TOP_BY_COLUMNS,
    ADAPTIVE_SCAN_V1_STAGE2_EXACT_SUB_BY_COLUMNS,
    ADAPTIVE_SCAN_V1_STAGE3_DYNAMIC_BANDS,
    ADAPTIVE_SCAN_V1_STAGE3_INITIAL_KEYS_BY_COLUMNS,
    ADAPTIVE_SCAN_V1_STAGE3_PERIOD_INIT_MULT,
    ADAPTIVE_SCAN_V1_STAGE3_PERIOD_RESTART_BONUS,
    ADAPTIVE_SCAN_V1_STAGE3_PERIOD_STEP_MULT,
    FOCUS_500_NOWLI_TIERS,
    FOCUS_P5_C1_ONLY_TIERS,
    SCAN_FAST_V1_STAGE2_EXACT_PASS1_TOP_BY_COLUMNS,
    SCAN_FAST_V1_STAGE2_EXACT_SUB_BY_COLUMNS,
    SCAN_FAST_V1_STAGE3_DYNAMIC_BANDS,
    SCAN_FAST_V1_STAGE3_INITIAL_KEYS_BY_COLUMNS,
    SCAN_FAST_V1_STAGE3_PERIOD_INIT_MULT,
    SCAN_FAST_V1_STAGE3_PERIOD_RESTART_BONUS,
    SCAN_FAST_V1_STAGE3_PERIOD_STEP_MULT,
    SCAN_P5_P7_C1357_TIERS,
    SMOKE_TIERS,
)


def build_run_mode_overrides(
    *,
    mode: str | None,
    canonical_run_mode_fn: Callable[[str | None], str],
    pipeline_profile_id: str,
    oracle_assist_selection_default: bool,
    stage3_continue_after_solve_default: bool,
    stage12_scout_runs: int,
    stage3_phaseb_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    m = canonical_run_mode_fn(mode)
    if m == "full":
        return {}
    if m == "smoke":
        return dict(
            PROFILE=f"{pipeline_profile_id}__smoke",
            HEARTBEAT_SECONDS=300,
            TEXT_OFFSETS=[0],
            KEY_SEEDS=[111],
            STAGE2_PROMOTE_BY_STAGE3_JUDGE=True,
            STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE=True,
            ORACLE_ASSIST_SELECTION=bool(oracle_assist_selection_default),
            STAGE3_CONTINUE_AFTER_SOLVE=bool(stage3_continue_after_solve_default),
            TIERS=list(SMOKE_TIERS),
        )
    if m == "focus_p5_c1_only":
        return dict(
            PROFILE=f"{pipeline_profile_id}__p5c1",
            HEARTBEAT_SECONDS=900,
            TEXT_OFFSETS=[0],
            KEY_SEEDS=[111],
            STAGE2_PROMOTE_BY_STAGE3_JUDGE=False,
            STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE=False,
            ORACLE_ASSIST_SELECTION=bool(oracle_assist_selection_default),
            STAGE3_CONTINUE_AFTER_SOLVE=bool(stage3_continue_after_solve_default),
            TIERS=list(FOCUS_P5_C1_ONLY_TIERS),
        )
    if m == "scan_fast_v1":
        cfg = dict(stage3_phaseb_cfg)
        cfg["slip_swaps"] = 12
        return dict(
            PROFILE=f"{pipeline_profile_id}__scan_fast_v1",
            HEARTBEAT_SECONDS=900,
            TEXT_OFFSETS=[0],
            KEY_SEEDS=[111],
            SCORING_EXPERIMENT_PROFILE="c_min_late",
            STAGE2_PROMOTE_BY_STAGE3_JUDGE=False,
            STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE=False,
            ORACLE_ASSIST_SELECTION=False,
            STAGE3_CONTINUE_AFTER_SOLVE=False,
            SCAN_TIER_TIME_CAP_SECONDS=600.0,
            SCAN_STAGE2_CONTINUE_TO_GATE=False,
            SCAN_STAGE2_CONTINUE_CAP_SECONDS=0.0,
            SCAN_STAGE3_GATE_LOW_MATCH=0.18,
            SCAN_STAGE3_GATE_HIGH_MATCH=0.24,
            SCAN_STAGE3_MIN_STAGE2_MATCH=0.18,
            STAGE1_SEED_RESTARTS=160,
            STAGE1_SEED_TOTAL=448,
            STAGE1_SCOUT_MIN_STEPS=1600,
            STAGE12_ARCHIVE_KEEP=160,
            STAGE12_PROMOTE_TOP=80,
            STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS=dict(
                SCAN_FAST_V1_STAGE2_EXACT_SUB_BY_COLUMNS
            ),
            STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS=dict(
                SCAN_FAST_V1_STAGE2_EXACT_PASS1_TOP_BY_COLUMNS
            ),
            STAGE3_INITIAL_KEYS=48,
            STAGE3_INITIAL_KEYS_BY_COLUMNS=dict(
                SCAN_FAST_V1_STAGE3_INITIAL_KEYS_BY_COLUMNS
            ),
            STAGE3_DYNAMIC_BANDS=[dict(b) for b in SCAN_FAST_V1_STAGE3_DYNAMIC_BANDS],
            STAGE3_C1_INIT_KEYS=96,
            STAGE3_C1_PHASEA_STEPS=1200,
            STAGE3_C1_PHASEB_STEPS=4200,
            STAGE3_C1_PHASEB_TOP_N=24,
            STAGE3_PHASEB_TOP_N=16,
            STAGE3_PHASEB_GATE_DELTA_FLOOR=0.008,
            STAGE3_PHASEB_GATE_END_GAIN_FLOOR=0.004,
            STAGE3_PHASEB_CFG=cfg,
            STAGE3_PERIOD_INIT_MULT_BY_PERIOD=dict(
                SCAN_FAST_V1_STAGE3_PERIOD_INIT_MULT
            ),
            STAGE3_PERIOD_STEP_MULT_BY_PERIOD=dict(
                SCAN_FAST_V1_STAGE3_PERIOD_STEP_MULT
            ),
            STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD=dict(
                SCAN_FAST_V1_STAGE3_PERIOD_RESTART_BONUS
            ),
            STAGE3_INIT_KEYS_CAP=192,
            TIERS=list(SCAN_P5_P7_C1357_TIERS),
        )
    if m == "adaptive_scan_v1":
        cfg = dict(stage3_phaseb_cfg)
        cfg["slip_swaps"] = 16
        return dict(
            PROFILE=f"{pipeline_profile_id}__scan_p5p7_c1357",
            HEARTBEAT_SECONDS=900,
            TEXT_OFFSETS=[0],
            KEY_SEEDS=[111],
            SCORING_EXPERIMENT_PROFILE="c_min_late",
            STAGE2_PROMOTE_BY_STAGE3_JUDGE=False,
            STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE=False,
            ORACLE_ASSIST_SELECTION=False,
            STAGE3_CONTINUE_AFTER_SOLVE=False,
            STAGE1_SEED_RESTARTS=192,
            STAGE1_SEED_TOTAL=512,
            STAGE1_SCOUT_MIN_STEPS=1800,
            STAGE12_ARCHIVE_KEEP=192,
            STAGE12_PROMOTE_TOP=96,
            STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS=dict(
                ADAPTIVE_SCAN_V1_STAGE2_EXACT_SUB_BY_COLUMNS
            ),
            STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS=dict(
                ADAPTIVE_SCAN_V1_STAGE2_EXACT_PASS1_TOP_BY_COLUMNS
            ),
            STAGE1_SCOUT_NO_IMPROVE_PATIENCE=3,
            STAGE1_SCOUT_MIN_NEW_ARCHIVE=1,
            STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS=max(1, int(stage12_scout_runs)),
            STAGE3_INITIAL_KEYS=64,
            STAGE3_INITIAL_KEYS_BY_COLUMNS=dict(
                ADAPTIVE_SCAN_V1_STAGE3_INITIAL_KEYS_BY_COLUMNS
            ),
            STAGE3_DYNAMIC_BANDS=[dict(b) for b in ADAPTIVE_SCAN_V1_STAGE3_DYNAMIC_BANDS],
            STAGE3_C1_INIT_KEYS=128,
            STAGE3_C1_PHASEA_STEPS=1800,
            STAGE3_C1_PHASEB_STEPS=6000,
            STAGE3_C1_PHASEB_TOP_N=32,
            STAGE3_PHASEB_TOP_N=24,
            STAGE3_PHASEB_GATE_DELTA_FLOOR=0.006,
            STAGE3_PHASEB_GATE_END_GAIN_FLOOR=0.003,
            STAGE3_PHASEB_CFG=cfg,
            STAGE3_PERIOD_INIT_MULT_BY_PERIOD=dict(
                ADAPTIVE_SCAN_V1_STAGE3_PERIOD_INIT_MULT
            ),
            STAGE3_PERIOD_STEP_MULT_BY_PERIOD=dict(
                ADAPTIVE_SCAN_V1_STAGE3_PERIOD_STEP_MULT
            ),
            STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD=dict(
                ADAPTIVE_SCAN_V1_STAGE3_PERIOD_RESTART_BONUS
            ),
            STAGE3_INIT_KEYS_CAP=224,
            SCAN_TIER_TIME_CAP_SECONDS=600.0,
            SCAN_STAGE2_CONTINUE_TO_GATE=True,
            SCAN_STAGE2_CONTINUE_CAP_SECONDS=900.0,
            SCAN_STAGE3_GATE_LOW_MATCH=0.15,
            SCAN_STAGE3_GATE_HIGH_MATCH=0.22,
            SCAN_STAGE3_MIN_STAGE2_MATCH=0.15,
            TIERS=list(SCAN_P5_P7_C1357_TIERS),
        )
    if m == "adaptive_fixture_v1":
        return dict(
            PROFILE=f"{pipeline_profile_id}__adaptive_fixture_v1",
            STAGE2_PROMOTE_BY_STAGE3_JUDGE=True,
            STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE=True,
            ORACLE_ASSIST_SELECTION=False,
            STAGE3_CONTINUE_AFTER_SOLVE=False,
            SCAN_TIER_TIME_CAP_SECONDS=0.0,
            SCAN_STAGE2_CONTINUE_TO_GATE=False,
            SCAN_STAGE2_CONTINUE_CAP_SECONDS=0.0,
            SCAN_STAGE3_GATE_LOW_MATCH=0.0,
            SCAN_STAGE3_GATE_HIGH_MATCH=0.0,
            SCAN_STAGE3_MIN_STAGE2_MATCH=0.0,
        )
    if m in {"adaptive_focus_v1", "adaptive_focus_v1_p7c3_only"}:
        return dict(
            PROFILE=(
                f"{pipeline_profile_id}__adaptive_focus_v1"
                if m == "adaptive_focus_v1"
                else f"{pipeline_profile_id}__adaptive_focus_v1_p7c3_only"
            ),
            HEARTBEAT_SECONDS=900,
            TEXT_OFFSETS=[0],
            KEY_SEEDS=[111],
            SCORING_EXPERIMENT_PROFILE="c_min_late",
            STAGE2_PROMOTE_BY_STAGE3_JUDGE=True,
            STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE=True,
            ORACLE_ASSIST_SELECTION=False,
            STAGE3_CONTINUE_AFTER_SOLVE=False,
            SCAN_TIER_TIME_CAP_SECONDS=0.0,
            SCAN_STAGE2_CONTINUE_TO_GATE=False,
            SCAN_STAGE2_CONTINUE_CAP_SECONDS=0.0,
            SCAN_STAGE3_GATE_LOW_MATCH=0.0,
            SCAN_STAGE3_GATE_HIGH_MATCH=0.0,
            SCAN_STAGE3_MIN_STAGE2_MATCH=0.0,
            TIERS=(
                list(ADAPTIVE_FOCUS_P7C3_ONLY_TIERS)
                if m == "adaptive_focus_v1_p7c3_only"
                else list(ADAPTIVE_FOCUS_V1_TIERS)
            ),
        )
    if m == "focus_500_nowli":
        return dict(
            PROFILE=f"{pipeline_profile_id}__focus500",
            HEARTBEAT_SECONDS=900,
            TEXT_OFFSETS=[0],
            KEY_SEEDS=[111],
            STAGE2_PROMOTE_BY_STAGE3_JUDGE=True,
            STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE=True,
            ORACLE_ASSIST_SELECTION=bool(oracle_assist_selection_default),
            STAGE3_CONTINUE_AFTER_SOLVE=bool(stage3_continue_after_solve_default),
            TIERS=list(FOCUS_500_NOWLI_TIERS),
        )
    raise ValueError(
        f"Unsupported PIPELINE_RUN_MODE={mode!r} "
        "(expected full|smoke|focus_p5_c1_only|focus_500_nowli|scan_fast_v1|adaptive_scan_v1|adaptive_fixture_v1|adaptive_focus_v1|adaptive_focus_v1_p7c3_only|scan_p5_p7_c1357[legacy_alias])"
    )
