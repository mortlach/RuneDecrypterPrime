from __future__ import annotations

from typing import Any, Callable, MutableMapping


def maybe_run_stage3_span_basin_k_sweep(
    *,
    state: MutableMapping[str, Any],
    canonical_run_mode_fn: Callable[[str | None], str],
    apply_profile_defaults_fn: Callable[[], None],
    main_fn: Callable[[], None],
) -> bool:
    if (not bool(state["RUN_STAGE3_SPAN_BASIN_K_SWEEP"])) or bool(
        state["_RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE"]
    ):
        return False

    sweep_vals: list[int] = []
    for raw_k in list(state["STAGE3_SPAN_BASIN_K_SWEEP_VALUES"]):
        try:
            k_i = int(raw_k)
        except Exception:
            continue
        if k_i <= 0:
            continue
        if k_i not in sweep_vals:
            sweep_vals.append(int(k_i))
    if not sweep_vals:
        raise ValueError(
            "RUN_STAGE3_SPAN_BASIN_K_SWEEP enabled but "
            "STAGE3_SPAN_BASIN_K_SWEEP_VALUES is empty/invalid."
        )
    print(
        f"[pipeline_no_wli] stage3-span-basin-k-sweep enabled=1 values={sweep_vals} "
        f"mode={canonical_run_mode_fn(state['PIPELINE_RUN_MODE'])}",
        flush=True,
    )
    state["_RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE"] = True
    try:
        for sweep_idx, k_i in enumerate(sweep_vals, start=1):
            apply_profile_defaults_fn()
            state["STAGE3_SPAN_BASIN_JUDGE_K"] = int(k_i)
            print(
                f"[pipeline_no_wli] stage3-span-basin-k-sweep "
                f"run={int(sweep_idx)}/{int(len(sweep_vals))} "
                f"k={int(state['STAGE3_SPAN_BASIN_JUDGE_K'])}",
                flush=True,
            )
            main_fn()
    finally:
        state["_RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE"] = False
    return True
