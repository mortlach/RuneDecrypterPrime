from __future__ import annotations

from typing import Any, Callable, MutableMapping


def initialize_runner_state(
    *,
    state: MutableMapping[str, Any],
    root: Any,
    base_module: Any,
    append_csv_row_common_fn: Callable[..., Any],
    write_csv_rows_common_fn: Callable[..., Any],
    scoring_config_cls: type,
    build_scorer_fn: Callable[..., Any],
    install_runner_bindings_fn: Callable[..., Any],
    canonical_run_mode_fn: Callable[..., Any],
    mode_intent_fn: Callable[..., Any],
    mode_stage3_can_skip_fn: Callable[..., Any],
    is_adaptive_focus_mode_fn: Callable[..., Any],
    build_run_mode_info_fn: Callable[..., Any],
    load_proven_solved_index_fn: Callable[..., Any],
    normalize_oracle_mode_fn: Callable[..., str],
    apply_profile_defaults_fn: Callable[[], None],
) -> None:
    state["_canonical_run_mode"] = canonical_run_mode_fn
    state["_mode_intent"] = mode_intent_fn
    state["_mode_stage3_can_skip"] = mode_stage3_can_skip_fn
    state["_is_adaptive_focus_mode"] = is_adaptive_focus_mode_fn
    state["_build_run_mode_info"] = build_run_mode_info_fn

    install_runner_bindings_fn(
        state=state,
        root=root,
        base_module=base_module,
        append_csv_row_common_fn=append_csv_row_common_fn,
        write_csv_rows_common_fn=write_csv_rows_common_fn,
        scoring_config_cls=scoring_config_cls,
        build_scorer_fn=build_scorer_fn,
    )
    state["_load_proven_solved_index"] = load_proven_solved_index_fn
    state["_oracle_mode_normalized"] = lambda: str(
        normalize_oracle_mode_fn(state["ORACLE_MODE"])
    )
    apply_profile_defaults_fn()
    state["_RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE"] = False
