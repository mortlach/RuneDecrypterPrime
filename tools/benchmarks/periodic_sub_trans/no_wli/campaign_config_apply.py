from __future__ import annotations

from typing import Any, Callable, Mapping, MutableMapping


def apply_scorer_impl_override(
    *,
    state: MutableMapping[str, Any],
    impl: str | None,
    scorer_stage3_impl_avg_fulltext: str | None,
    effective_stage3_impl_fn: Callable[[dict[str, Any]], str],
) -> None:
    resolved = "" if impl is None else str(impl).strip()
    if resolved:
        state["SCORER_IMPL"] = resolved
    resolved_stage3 = (
        ""
        if scorer_stage3_impl_avg_fulltext is None
        else str(scorer_stage3_impl_avg_fulltext).strip()
    )
    if resolved_stage3:
        state["SCORER_STAGE3_IMPL_AVG_FULLTEXT"] = resolved_stage3
    for cfg_name in ("SCORER_STAGE1", "SCORER_STAGE2"):
        cfg = state.get(cfg_name)
        if isinstance(cfg, dict):
            cfg["impl"] = str(state["SCORER_IMPL"])
    scorer_full = state.get("SCORER_FULL")
    if isinstance(scorer_full, dict):
        scorer_full["impl"] = effective_stage3_impl_fn(scorer_full)


def apply_campaign_run_config(
    *,
    state: MutableMapping[str, Any],
    cfg: Any,
    get_profile_fn: Callable[[str], Any],
    apply_profile_defaults_fn: Callable[[], None],
    apply_schedule_fn: Callable[..., Any],
    apply_scorer_impl_override_fn: Callable[..., None],
) -> None:
    state["AUTOSKIP_PROVEN"] = bool(cfg.autoskip_proven)
    state["FORCE_RERUN_PROVEN"] = bool(cfg.force_rerun_proven)
    state["PIPELINE_RUN_MODE"] = str(cfg.run_mode)
    state["PROFILE"] = str(cfg.profile_name)
    state["HEARTBEAT_SECONDS"] = int(cfg.heartbeat_seconds)
    state["TEXT_OFFSETS"][:] = [int(x) for x in cfg.text_offsets]
    state["KEY_SEEDS"][:] = [int(cfg.run_seed)]
    state["TIERS"][:] = [cfg.tier()]

    profile_id = str(cfg.profile_name or "").strip()
    if profile_id:
        try:
            _ = get_profile_fn(profile_id)
        except Exception:
            pass
        else:
            state["NO_WLI_PIPELINE_PROFILE_ID"] = profile_id
            apply_profile_defaults_fn()
            state["TIERS"][:] = [cfg.tier()]
            state["TEXT_OFFSETS"][:] = [int(x) for x in cfg.text_offsets]
            state["KEY_SEEDS"][:] = [int(cfg.run_seed)]
            state["PIPELINE_RUN_MODE"] = str(cfg.run_mode)
            state["HEARTBEAT_SECONDS"] = int(cfg.heartbeat_seconds)

    labels = apply_schedule_fn(
        scorer_schedule=cfg.scorer_schedule,
        stage1_cfg=state["SCORER_STAGE1"],
        stage2_cfg=state["SCORER_STAGE2"],
        stage3_cfg=state["SCORER_FULL"],
    )
    if labels.stage1_label is not None:
        state["SCORER_STAGE1_LABEL"] = str(labels.stage1_label)
    if labels.stage2_label is not None:
        state["SCORER_STAGE2_LABEL"] = str(labels.stage2_label)
    if labels.stage3_label is not None:
        state["SCORER_STAGE3_LABEL"] = str(labels.stage3_label)
    apply_scorer_impl_override_fn(
        cfg.scorer_impl,
        scorer_stage3_impl_avg_fulltext=cfg.scorer_stage3_impl_avg_fulltext,
    )
