from __future__ import annotations

from typing import Any, Mapping

from tools.benchmarks.periodic_sub_trans.no_wli.runtime_mode_presets import (
    ADAPTIVE_FOCUS_MODES as _ADAPTIVE_FOCUS_MODES,
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
    SCAN_MODES as _SCAN_MODES,
    SCAN_P5_P7_C1357_TIERS,
    SMOKE_TIERS,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runtime_mode_overrides import (
    build_run_mode_overrides as _build_run_mode_overrides_impl,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runtime_mode_info import (
    RunModeInfo,
    build_run_mode_info as _build_run_mode_info_impl,
    canonical_run_mode as _canonical_run_mode_impl,
    is_adaptive_focus_mode as _is_adaptive_focus_mode_impl,
    mode_intent as _mode_intent_impl,
    mode_stage3_can_skip as _mode_stage3_can_skip_impl,
)


def canonical_run_mode(mode: str | None) -> str:
    return _canonical_run_mode_impl(mode)


def mode_intent(mode: str | None) -> str:
    return _mode_intent_impl(mode, scan_modes=_SCAN_MODES)


def mode_stage3_can_skip(mode: str | None) -> bool:
    return _mode_stage3_can_skip_impl(mode, scan_modes=_SCAN_MODES)


def is_adaptive_focus_mode(mode: str | None) -> bool:
    return _is_adaptive_focus_mode_impl(mode, adaptive_focus_modes=_ADAPTIVE_FOCUS_MODES)


def build_run_mode_info(mode: str | None) -> RunModeInfo:
    return _build_run_mode_info_impl(
        mode,
        scan_modes=_SCAN_MODES,
        adaptive_focus_modes=_ADAPTIVE_FOCUS_MODES,
    )


def normalize_oracle_mode(mode: str | None) -> str:
    m = str(mode or "").strip().lower()
    if m == "benchmark_only":
        return "benchmark_only"
    return "off"


def build_run_mode_overrides(
    *,
    mode: str | None,
    pipeline_profile_id: str,
    oracle_assist_selection_default: bool,
    stage3_continue_after_solve_default: bool,
    stage12_scout_runs: int,
    stage3_phaseb_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    return _build_run_mode_overrides_impl(
        mode=mode,
        canonical_run_mode_fn=canonical_run_mode,
        pipeline_profile_id=pipeline_profile_id,
        oracle_assist_selection_default=oracle_assist_selection_default,
        stage3_continue_after_solve_default=stage3_continue_after_solve_default,
        stage12_scout_runs=stage12_scout_runs,
        stage3_phaseb_cfg=stage3_phaseb_cfg,
    )
