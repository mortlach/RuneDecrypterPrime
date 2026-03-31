from __future__ import annotations

"""No-WLI staged periodic+columnar benchmark.

This benchmark keeps the same stage structure as the main pipeline benchmark and
removes all WLI dependencies so runic-like short-text tuning can be measured
with character-only models.

Default scorer schedule:
- Stage 1: A_char1 (explore)
- Stage 2: M_char12 (rerank/promote)
- Stage 3: B_char34 (deep refine)
"""

import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

_ROOT = Path(__file__).resolve().parents[4]
_SRC = _ROOT / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import Direction
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer

from tools.benchmarks.periodic_sub_trans.common import bench_solve_periodic_columnar_kaeding as base
from tools.benchmarks.periodic_sub_trans.common.campaign_run_config import (
    build_campaign_run_config,
)
from tools.benchmarks.periodic_sub_trans.common.io_reports import (
    append_csv_row as _append_csv_row_common,
    write_pipeline_snapshot_files,
    write_csv_rows as _write_csv_rows_common,
    write_json,
)
from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
from tools.benchmarks.periodic_sub_trans.common.paths import make_flavor_run_dir
from tools.benchmarks.periodic_sub_trans.common.runner_types import Tier
from tools.benchmarks.periodic_sub_trans.common.scorer_schedule_apply import (
    apply_no_wli_schedule,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runtime_config import (
    build_run_mode_overrides as _build_run_mode_overrides_external,
    build_run_mode_info as _build_run_mode_info_external,
    canonical_run_mode as _canonical_run_mode_external,
    is_adaptive_focus_mode as _is_adaptive_focus_mode_external,
    mode_intent as _mode_intent_external,
    mode_stage3_can_skip as _mode_stage3_can_skip_external,
    normalize_oracle_mode as _normalize_oracle_mode_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_mode_apply import (
    apply_run_mode_overrides as _apply_run_mode_overrides_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.profile_defaults import (
    apply_kaeding_progress_settings as _apply_kaeding_progress_settings_external,
    apply_profile_defaults_from_profile as _apply_profile_defaults_from_profile_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_config_builder import (
    build_run_config as _build_run_config_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_config_io import (
    persist_run_config_with_locks as _persist_run_config_with_locks_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_pipeline_execution import (
    execute_pipeline_from_startup as _execute_pipeline_from_startup_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.setup_logging_payload import (
    build_setup_logging_payload as _build_setup_logging_payload_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.campaign_config_apply import (
    apply_campaign_run_config as _apply_campaign_run_config_external,
    apply_scorer_impl_override as _apply_scorer_impl_override_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_environment import (
    prepare_run_environment as _prepare_run_environment_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_sweep import (
    maybe_run_stage3_span_basin_k_sweep as _maybe_run_stage3_span_basin_k_sweep_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_startup import (
    bootstrap_main_run as _bootstrap_main_run_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runtime_defaults import (
    DEFAULT_SCORER_FULL,
    DEFAULT_SCORER_STAGE1,
    DEFAULT_SCORER_STAGE2,
    DEFAULT_SOLVER_STAGE1,
    DEFAULT_SOLVER_STAGE2,
    DEFAULT_SOLVER_STAGE3,
    DEFAULT_STAGE3_ENTRY_ALLOCATION_POLICY,
    DEFAULT_STAGE3_ENTRY_MUTATIONS_PER_PROMOTED,
    DEFAULT_STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY,
    DEFAULT_STAGE3_PHASEB_FAMILY_RESERVED_SLOTS,
    DEFAULT_STAGE3_PHASEB_FAMILY_VIEW_ID,
    DEFAULT_STAGE3_PHASEC_START_POLICY,
    DEFAULT_STAGE3_DYNAMIC_BANDS,
    DEFAULT_STAGE3_PHASEA_CFG,
    DEFAULT_STAGE3_PHASEB_CFG,
    DEFAULT_TIERS,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_band_policy import (
    resolve_stage3_gap_and_band as _resolve_stage3_gap_and_band_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_summary import (
    load_proven_solved_index as _load_proven_solved_index_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.setup_logging import (
    emit_setup_logging as _emit_setup_logging_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_bindings import (
    install_runner_bindings,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_state_defaults import (
    initialize_runtime_state,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_entrypoints import (
    apply_profile_defaults as _apply_profile_defaults_entrypoint,
    apply_scorer_impl_override as _apply_scorer_impl_override_entrypoint,
    configure_campaign_run as _configure_campaign_run_entrypoint,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_main_orchestrator import (
    run_main as _run_main_orchestrator,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_mode_entrypoint import (
    apply_run_mode as _apply_run_mode_entrypoint,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_state_init import (
    initialize_runner_state,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_defaults import (
    apply_runner_defaults,
)
from tools.benchmarks.periodic_sub_trans.no_wli.order_dispatch import (
    build_no_wli_order_dispatch_payload as _build_no_wli_order_dispatch_payload,
    normalize_no_wli_order as _normalize_no_wli_order,
)


apply_runner_defaults(state=globals())
# Keep explicit literals in this module for source/guardrail tests.
STAGE2_JUDGE_POLICY = "search_only"
ORACLE_MODE = "off"
AUTOSKIP_PROVEN = True
FORCE_RERUN_PROVEN = True

initialize_runtime_state(
    state=globals(),
    default_scorer_stage1=DEFAULT_SCORER_STAGE1,
    default_scorer_stage2=DEFAULT_SCORER_STAGE2,
    default_scorer_full=DEFAULT_SCORER_FULL,
    default_solver_stage1=DEFAULT_SOLVER_STAGE1,
    default_solver_stage2=DEFAULT_SOLVER_STAGE2,
    default_solver_stage3=DEFAULT_SOLVER_STAGE3,
    default_stage3_entry_allocation_policy=DEFAULT_STAGE3_ENTRY_ALLOCATION_POLICY,
    default_stage3_entry_mutations_per_promoted=DEFAULT_STAGE3_ENTRY_MUTATIONS_PER_PROMOTED,
    default_stage3_phaseb_family_preservation_policy=(
        DEFAULT_STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY
    ),
    default_stage3_phaseb_family_view_id=DEFAULT_STAGE3_PHASEB_FAMILY_VIEW_ID,
    default_stage3_phaseb_family_reserved_slots=DEFAULT_STAGE3_PHASEB_FAMILY_RESERVED_SLOTS,
    default_stage3_phasec_start_policy=DEFAULT_STAGE3_PHASEC_START_POLICY,
    default_stage3_dynamic_bands=DEFAULT_STAGE3_DYNAMIC_BANDS,
    default_stage3_phasea_cfg=DEFAULT_STAGE3_PHASEA_CFG,
    default_stage3_phaseb_cfg=DEFAULT_STAGE3_PHASEB_CFG,
    default_tiers=DEFAULT_TIERS,
    tier_cls=Tier,
)


def _apply_profile_defaults() -> None:
    _apply_profile_defaults_entrypoint(
        state=globals(),
        get_profile_fn=get_no_wli_pipeline_profile,
        apply_profile_defaults_from_profile_fn=_apply_profile_defaults_from_profile_external,
        apply_kaeding_progress_settings_fn=_apply_kaeding_progress_settings,
    )


def _apply_kaeding_progress_settings() -> None:
    _apply_kaeding_progress_settings_external(state=globals())


def _apply_scorer_impl_override(
    impl: str | None,
    *,
    scorer_stage3_impl_avg_fulltext: str | None = None,
) -> None:
    _apply_scorer_impl_override_entrypoint(
        state=globals(),
        impl=str(impl) if impl is not None else None,
        scorer_stage3_impl_avg_fulltext=scorer_stage3_impl_avg_fulltext,
        apply_scorer_impl_override_fn=_apply_scorer_impl_override_external,
    )


def configure_campaign_run(
    *,
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
    scorer_impl: str | None = None,
    scorer_stage3_impl_avg_fulltext: str | None = None,
    scorer_schedule: Mapping[str, Any] | None = None,
) -> None:
    _configure_campaign_run_entrypoint(
        state=globals(),
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
        build_campaign_run_config_fn=build_campaign_run_config,
        apply_campaign_run_config_fn=_apply_campaign_run_config_external,
        get_profile_fn=get_no_wli_pipeline_profile,
        apply_profile_defaults_fn=_apply_profile_defaults,
        apply_schedule_fn=apply_no_wli_schedule,
        apply_scorer_impl_override_wrapper_fn=_apply_scorer_impl_override,
    )


def _repo_root() -> Path:
    return _ROOT


_canonical_run_mode = _canonical_run_mode_external
_mode_intent = _mode_intent_external
_mode_stage3_can_skip = _mode_stage3_can_skip_external
_is_adaptive_focus_mode = _is_adaptive_focus_mode_external
_build_run_mode_info = _build_run_mode_info_external


def _apply_run_mode() -> None:
    _apply_run_mode_entrypoint(
        state=globals(),
        build_run_mode_overrides_fn=_build_run_mode_overrides_external,
        apply_run_mode_overrides_fn=_apply_run_mode_overrides_external,
        build_tier_fn=lambda name, period, columns, length: Tier(
            str(name), int(period), int(columns), int(length)
        ),
    )

initialize_runner_state(
    state=globals(),
    root=_ROOT,
    base_module=base,
    append_csv_row_common_fn=_append_csv_row_common,
    write_csv_rows_common_fn=_write_csv_rows_common,
    scoring_config_cls=ScoringConfig,
    build_scorer_fn=build_scorer,
    install_runner_bindings_fn=install_runner_bindings,
    canonical_run_mode_fn=_canonical_run_mode_external,
    mode_intent_fn=_mode_intent_external,
    mode_stage3_can_skip_fn=_mode_stage3_can_skip_external,
    is_adaptive_focus_mode_fn=_is_adaptive_focus_mode_external,
    build_run_mode_info_fn=_build_run_mode_info_external,
    load_proven_solved_index_fn=_load_proven_solved_index_external,
    normalize_oracle_mode_fn=_normalize_oracle_mode_external,
    apply_profile_defaults_fn=_apply_profile_defaults,
)
_load_proven_solved_index = globals()["_load_proven_solved_index"]
_oracle_mode_normalized = globals()["_oracle_mode_normalized"]
_RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE = bool(
    globals()["_RUN_STAGE3_SPAN_BASIN_K_SWEEP_ACTIVE"]
)
ORDER = _normalize_no_wli_order(str(ORDER))


def main() -> None:
    _run_main_orchestrator(
        state=globals(),
        main_fn=main,
        maybe_run_stage3_span_basin_k_sweep_fn=_maybe_run_stage3_span_basin_k_sweep_external,
        bootstrap_main_run_fn=_bootstrap_main_run_external,
        execute_pipeline_from_startup_fn=_execute_pipeline_from_startup_external,
        direction_ltr=Direction.LTR,
        direction_rtl=Direction.RTL,
        require_assets_fn=base._require_assets,
        encode_long_plaintext_fn=base._encode_long_plaintext,
        repo_root_fn=_repo_root,
        make_flavor_run_dir_fn=make_flavor_run_dir,
        prepare_run_environment_fn=_prepare_run_environment_external,
        load_proven_index_fn=_load_proven_solved_index,
        build_run_mode_info_fn=_build_run_mode_info,
        oracle_mode_normalized_fn=_oracle_mode_normalized,
        apply_run_mode_fn=_apply_run_mode,
        apply_kaeding_progress_settings_fn=_apply_kaeding_progress_settings,
        apply_scoring_experiment_profile_fn=_apply_scoring_experiment_profile,
        build_run_config_fn=_build_run_config_external,
        build_no_wli_order_dispatch_payload_fn=_build_no_wli_order_dispatch_payload,
        normalize_no_wli_order_fn=_normalize_no_wli_order,
        persist_run_config_with_locks_fn=_persist_run_config_with_locks_external,
        resolve_repo_path_fn=_resolve_repo_path,
        stage3_search_cfg_fn=_stage3_char4_avg_fulltext_search_cfg,
        build_setup_logging_payload_fn=_build_setup_logging_payload_external,
        emit_setup_logging_fn=_emit_setup_logging_external,
        scorer_objective_summary_fn=_scorer_objective_summary,
        weights_text_fn=_weights_text,
        scorer_cfg_for_output_fn=_scorer_cfg_for_output,
        scoring_meta_for_output_fn=_scoring_meta_for_output,
        build_non_scoring_lock_payload_fn=_build_non_scoring_lock_payload,
        build_scoring_lock_payload_fn=_build_scoring_lock_payload,
        hash_payload_fn=_hash_payload,
        write_json_fn=write_json,
        git_short_fn=_git_short,
        git_commit_fn=_git_commit,
        git_dirty_fn=_git_dirty,
        sha256_file_fn=_sha256_file,
        to_repo_rel_path_fn=lambda p, root: _to_repo_rel_path(p, root=root),
        log_prefix="[pipeline_no_wli]",
    )


if __name__ == "__main__":
    main()


