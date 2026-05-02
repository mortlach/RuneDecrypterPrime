from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage3_entry_const_local_depth_fixed_canary_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.community._campaign_common import load_json, write_json
from tools.benchmarks.periodic_sub_trans.no_wli import fixture_matrix_api as fixture_api
from tools.benchmarks.periodic_sub_trans.no_wli import (
    fixture_matrix_config as fixture_cfg_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (
    refresh_catalog_safely,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_mainflow import (
    run_mainflow as _run_mainflow_impl,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_models import (
    FixtureMatrixMainflowConfig,
    MatrixControlFiles,
    Stage3TuningPreset,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_plan import (
    build_plan_payload as _build_plan_payload_impl,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_runtime import (
    run_jobs_with_checkpoints,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_io import (
    load_fixed_cipher_panel_spec,
    load_fixed_instance_spec_map,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runtime_preflight import (
    run_runtime_preflight,
)


RUN_LABEL = "stage3_entry_const_local_depth_fixed_canary_v1"
EXPERIMENT_RUN_ID = (
    "tune_v76_fixed_p9c3_1111_search7004_"
    "stage35_entry_const_local_depth_compare_2job"
)
CONTROL_FILES_BASE_DIR = Path("output/tools/benchmarks/periodic_sub_trans/no_wli")
MATRIX_CONTROL_FILES = MatrixControlFiles.for_experiment(
    experiment_run_id=EXPERIMENT_RUN_ID,
    base_dir=CONTROL_FILES_BASE_DIR,
)
FIXED_PANEL_PATH = Path(
    "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/"
    "p9_c3_solver_panel_1111_search7004_v1.json"
)
FIXED_INSTANCE_FIXTURE_DIR = Path(
    "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances"
)
CONTROL_PRESET_ID = "stage35_baseline_score_plus_novelty_live_bounded_p9"
CANDIDATE_PRESET_ID = (
    "stage35_baseline_score_plus_novelty_live_bounded_"
    "entry_const_local_depth_v1"
)
FIXED_TEXT_OFFSETS = (5,)
MAX_WALLCLOCK_SECONDS = 8.0 * 60.0 * 60.0
MECHANISM_LAYER = "allocation"
QUESTION = (
    "On fixed 1111/search7004, can constant-local-depth Stage-3 entry allocation "
    "beat the bounded Stage 3.5 control without breaking the ~8 hour session "
    "budget?"
)
SUSPICION = (
    "The bounded Stage 3.5 stack is already useful on 1111/search7004, but the "
    "legacy fixed-budget Stage-3 entry may still be too narrow before the late "
    "stack gets its chance."
)
MAIN_ALTERNATIVE = (
    "The bounded stack is already capturing what this cell can use, so wider "
    "constant-local-depth entry will stay flat or worse."
)
IF_SUSPICION_TRUE_EXPECT = (
    "The candidate should widen executed Stage-3 entry counts and beat control "
    "on run-level best match or late-route quality."
)
IF_ALTERNATIVE_TRUE_EXPECT = (
    "The candidate may widen entry counts but remain flat or worse than control, "
    "or fail to widen the executed handoff materially."
)
TOMORROWS_DECISION_RULE = (
    "Promote only if the candidate beats control with a meaningful run-level "
    "gain, the entry widening really executes, and the two-job compare stays "
    "inside the intended budget; otherwise refine only for a narrow ambiguous "
    "positive and close if the candidate stays flat or worse."
)
STOP_CONDITION = (
    "After the first completed job, compare actual elapsed time against the "
    "intended ~8 hour two-job session budget; stop and rescope if the projected "
    "two-job total already overruns budget materially."
)


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _control_preset_raw() -> dict[str, Any]:
    raw = dict(fixture_cfg_mod.STAGE3_TUNING_PRESETS.get(CONTROL_PRESET_ID, {}) or {})
    if not raw:
        raise KeyError(f"Missing control preset: {CONTROL_PRESET_ID}")
    return raw


def build_active_presets() -> dict[str, Stage3TuningPreset]:
    control_raw = _control_preset_raw()
    candidate_raw = dict(control_raw)
    candidate_raw["force_stage3_init_keys_cap"] = 288
    candidate_raw["force_stage3_entry_allocation_policy"] = "constant_local_depth"
    candidate_raw["force_stage3_entry_mutations_per_promoted"] = 1
    return {
        CONTROL_PRESET_ID: Stage3TuningPreset.from_mapping(
            preset_id=CONTROL_PRESET_ID,
            raw=control_raw,
        ),
        CANDIDATE_PRESET_ID: Stage3TuningPreset.from_mapping(
            preset_id=CANDIDATE_PRESET_ID,
            raw=candidate_raw,
        ),
    }


def active_preset_ids() -> tuple[str, ...]:
    return (CONTROL_PRESET_ID, CANDIDATE_PRESET_ID)


def install_active_presets() -> None:
    fixture_api.STAGE3_TUNING_PRESETS = {
        preset_id: preset.as_dict()
        for preset_id, preset in build_active_presets().items()
    }
    fixture_api.STAGE3_TUNING_PRESET_IDS = active_preset_ids()
    fixture_api.ENABLE_STAGE3_TUNING_PRESET_MATRIX = True


def build_matrix_mainflow_config() -> FixtureMatrixMainflowConfig:
    return FixtureMatrixMainflowConfig(
        campaign_config_path=Path(fixture_cfg_mod.CAMPAIGN_CONFIG_PATH),
        fixture_ids=None,
        fixture_length_override=int(fixture_cfg_mod.FIXTURE_LENGTH_OVERRIDE or 1000),
        instance_input_mode="fixed_ciphertext",
        fixed_instance_panel_path=FIXED_PANEL_PATH,
        fixed_instance_fixture_dir=FIXED_INSTANCE_FIXTURE_DIR,
        use_campaign_grid=False,
        periods_override=(9,),
        columns_override_by_period={9: (3,)},
        run_mode=str(fixture_cfg_mod.RUN_MODE),
        no_wli_profile_id=str(fixture_cfg_mod.NO_WLI_PROFILE_ID),
        run_seeds=tuple(int(x) for x in fixture_cfg_mod.RUN_SEEDS),
        text_offsets=FIXED_TEXT_OFFSETS,
        heartbeat_seconds=int(fixture_cfg_mod.HEARTBEAT_SECONDS),
        scorer_impl=str(fixture_cfg_mod.SCORER_IMPL),
        scorer_stage3_impl_avg_fulltext=str(
            fixture_cfg_mod.SCORER_STAGE3_IMPL_AVG_FULLTEXT
        ),
        enable_acceptance_harness_500x5=False,
        acceptance_harness_fixture_count=0,
        acceptance_harness_length=0,
        scoring_experiment_profiles=tuple(
            str(x) for x in fixture_cfg_mod.SCORING_EXPERIMENT_PROFILES
        ),
        enable_span_ab_pair=False,
        span_ab_decision_role=str(fixture_cfg_mod.SPAN_AB_DECISION_ROLE),
        schedule_coverage_mode="explicit",
        explicit_schedules=tuple(
            {
                "early": str(schedule["early"]),
                "middle": str(schedule["middle"]),
                "late": str(schedule["late"]),
            }
            for schedule in fixture_cfg_mod.EXPLICIT_SCHEDULES
        ),
        require_no_win10_objectives=bool(fixture_cfg_mod.REQUIRE_NO_WIN10_OBJECTIVES),
        require_full_text_effective=bool(fixture_cfg_mod.REQUIRE_FULL_TEXT_EFFECTIVE),
        disable_stage3_span_basin_k_sweep=bool(
            fixture_cfg_mod.DISABLE_STAGE3_SPAN_BASIN_K_SWEEP
        ),
        stage3_span_basin_k_sweep_values=tuple(
            int(x) for x in fixture_cfg_mod.STAGE3_SPAN_BASIN_K_SWEEP_VALUES
        ),
        stage3_tuning_preset_ids=active_preset_ids(),
        stage3_tuning_presets=build_active_presets(),
        dry_run_only=False,
        stop_on_error=True,
        max_jobs=None,
        max_wallclock_seconds=float(MAX_WALLCLOCK_SECONDS),
        resume_skip_completed=True,
        control_files=MATRIX_CONTROL_FILES,
        write_plan_json=True,
    )


def build_matrix_mainflow_state() -> dict[str, Any]:
    return build_matrix_mainflow_config().to_state(
        utc_now_iso_fn=fixture_api._utc_now_iso
    )


def run_study() -> None:
    install_active_presets()
    config = build_matrix_mainflow_config()
    panel_path = fixture_api._resolve_path(
        path_like=config.fixed_instance_panel_path,
        repo_root=REPO_ROOT,
    )
    panel_spec = load_fixed_cipher_panel_spec(panel_path)
    study_summary = {
        "run_label": RUN_LABEL,
        "experiment_run_id": EXPERIMENT_RUN_ID,
        "fixed_instance_panel_path": _relative_path(panel_path),
        "fixed_instance_panel_id": str(panel_spec.panel_id),
        "fixture_count": int(len(panel_spec.instance_fixture_ids)),
        "search_seed_count": int(len(panel_spec.search_seeds)),
        "search_seeds": [int(x) for x in panel_spec.search_seeds],
        "text_offsets": [int(x) for x in FIXED_TEXT_OFFSETS],
        "preset_ids": list(active_preset_ids()),
        "job_count": int(
            len(panel_spec.instance_fixture_ids)
            * len(panel_spec.search_seeds)
            * len(active_preset_ids())
        ),
        "max_wallclock_seconds": float(MAX_WALLCLOCK_SECONDS),
        "intended_wallclock_budget_hours": float(MAX_WALLCLOCK_SECONDS) / 3600.0,
        "mechanism_layer": MECHANISM_LAYER,
        "question": QUESTION,
        "suspicion": SUSPICION,
        "main_alternative": MAIN_ALTERNATIVE,
        "if_suspicion_true_expect": IF_SUSPICION_TRUE_EXPECT,
        "if_alternative_true_expect": IF_ALTERNATIVE_TRUE_EXPECT,
        "tomorrows_decision_rule": TOMORROWS_DECISION_RULE,
        "stop_condition": STOP_CONDITION,
        "budget_rationale": (
            "Use the exact retained 1111/search7004 wallclock anchor first and keep "
            "the first new-family compare to a two-job same-cell canary."
        ),
    }
    print(json.dumps(study_summary, sort_keys=True), flush=True)

    _run_mainflow_impl(
        state=build_matrix_mainflow_state(),
        repo_root=REPO_ROOT,
        resolve_path_fn=lambda p: fixture_api._resolve_path(
            path_like=p, repo_root=REPO_ROOT
        ),
        load_json_fn=load_json,
        write_json_fn=write_json,
        load_fixture_specs_fn=fixture_api.load_fixture_specs,
        load_fixed_cipher_panel_spec_fn=load_fixed_cipher_panel_spec,
        load_fixed_instance_spec_map_fn=load_fixed_instance_spec_map,
        resolve_period_columns_fn=fixture_api.resolve_period_columns,
        build_schedule_matrix_fn=fixture_api.build_schedule_matrix,
        build_fixture_jobs_fn=fixture_api.build_fixture_jobs,
        build_fixed_instance_jobs_fn=fixture_api.build_fixed_instance_jobs,
        build_plan_payload_fn=_build_plan_payload_impl,
        run_jobs_with_checkpoints_fn=run_jobs_with_checkpoints,
        load_run_state_fn=fixture_api._load_run_state,
        job_key_fn=fixture_api._job_key,
        run_job_fn=fixture_api.run_job,
        runtime_preflight_fn=run_runtime_preflight,
        print_fn=print,
    )
    refresh_catalog_safely(print_fn=print)


def main() -> None:
    run_study()


if __name__ == "__main__":
    main()
