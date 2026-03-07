from __future__ import annotations

from typing import Any, Callable, Mapping, MutableMapping, Sequence


def apply_profile_defaults(
    *,
    state: MutableMapping[str, Any],
    get_profile_fn: Callable[[str], Any],
    apply_profile_defaults_from_profile_fn: Callable[..., None],
    apply_kaeding_progress_settings_fn: Callable[[], None],
) -> None:
    profile = get_profile_fn(str(state["NO_WLI_PIPELINE_PROFILE_ID"]))
    apply_profile_defaults_from_profile_fn(
        state=state,
        profile=profile,
        effective_stage3_impl_fn=state["_effective_stage3_impl"],
    )
    apply_kaeding_progress_settings_fn()


def apply_scorer_impl_override(
    *,
    state: MutableMapping[str, Any],
    impl: str | None,
    scorer_stage3_impl_avg_fulltext: str | None,
    apply_scorer_impl_override_fn: Callable[..., None],
) -> None:
    apply_scorer_impl_override_fn(
        state=state,
        impl=impl,
        scorer_stage3_impl_avg_fulltext=scorer_stage3_impl_avg_fulltext,
        effective_stage3_impl_fn=state["_effective_stage3_impl"],
    )


def configure_campaign_run(
    *,
    state: MutableMapping[str, Any],
    run_seed: int,
    period: int,
    columns: int,
    length: int,
    tier_name: str,
    run_mode: str,
    profile_name: str,
    heartbeat_seconds: int,
    autoskip_proven: bool,
    force_rerun_proven: bool,
    avoid_repeat_fail: bool,
    text_offsets: Sequence[int],
    tiers_regex_override: str | None,
    scorer_impl: str | None,
    scorer_stage3_impl_avg_fulltext: str | None,
    scorer_schedule: Mapping[str, Any] | None,
    build_campaign_run_config_fn: Callable[..., Any],
    apply_campaign_run_config_fn: Callable[..., None],
    get_profile_fn: Callable[[str], Any],
    apply_profile_defaults_fn: Callable[[], None],
    apply_schedule_fn: Callable[..., None],
    apply_scorer_impl_override_wrapper_fn: Callable[..., None],
) -> None:
    cfg = build_campaign_run_config_fn(
        run_seed=run_seed,
        period=period,
        columns=columns,
        length=length,
        tier_name=tier_name,
        run_mode=run_mode,
        profile_name=profile_name,
        heartbeat_seconds=heartbeat_seconds,
        autoskip_proven=autoskip_proven,
        force_rerun_proven=force_rerun_proven,
        avoid_repeat_fail=avoid_repeat_fail,
        text_offsets=text_offsets,
        tiers_regex_override=tiers_regex_override,
        scorer_impl=scorer_impl,
        scorer_stage3_impl_avg_fulltext=scorer_stage3_impl_avg_fulltext,
        scorer_schedule=scorer_schedule,
    )
    apply_campaign_run_config_fn(
        state=state,
        cfg=cfg,
        get_profile_fn=get_profile_fn,
        apply_profile_defaults_fn=apply_profile_defaults_fn,
        apply_schedule_fn=apply_schedule_fn,
        apply_scorer_impl_override_fn=apply_scorer_impl_override_wrapper_fn,
    )
