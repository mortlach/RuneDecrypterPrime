from __future__ import annotations

from typing import Any, Callable, MutableMapping


def apply_run_mode(
    *,
    state: MutableMapping[str, Any],
    build_run_mode_overrides_fn: Callable[..., dict[str, Any]],
    apply_run_mode_overrides_fn: Callable[..., None],
    build_tier_fn: Callable[[str, int, int, int], Any],
) -> None:
    overrides = build_run_mode_overrides_fn(
        mode=state["PIPELINE_RUN_MODE"],
        pipeline_profile_id=str(state["NO_WLI_PIPELINE_PROFILE_ID"]),
        oracle_assist_selection_default=bool(state["_ORACLE_ASSIST_SELECTION_DEFAULT"]),
        stage3_continue_after_solve_default=bool(
            state["_STAGE3_CONTINUE_AFTER_SOLVE_DEFAULT"]
        ),
        stage12_scout_runs=int(state["STAGE12_SCOUT_RUNS"]),
        stage3_phaseb_cfg=dict(state["STAGE3_PHASEB_CFG"]),
    )
    if not overrides:
        return
    apply_run_mode_overrides_fn(
        state=state,
        overrides=overrides,
        build_tier_fn=build_tier_fn,
    )
