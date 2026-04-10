from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


def resolve_path(*, path_like: Path, repo_root: Path) -> Path:
    path = Path(path_like)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    return path


def _to_repo_rel(path: Path, *, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except Exception:
        return "<external>"


def build_plan_payload(
    *,
    repo_root: Path,
    campaign_path: Path,
    run_mode: str,
    instance_input_mode: str,
    profile_id: str,
    schedule_coverage_mode: str,
    schedules: Sequence[Mapping[str, Any]],
    fixtures: Sequence[Any],
    jobs: Sequence[Any],
    scoring_experiment_profiles: Sequence[str],
    enable_span_ab_pair: bool,
    span_ab_decision_role: str,
    require_no_win10_objectives: bool,
    require_full_text_effective: bool,
    disable_stage3_span_basin_k_sweep: bool,
    stage3_span_basin_k_sweep_values: Sequence[int],
    stage3_tuning_preset_ids: Sequence[str],
    stage3_tuning_presets: Mapping[str, Mapping[str, Any]] | None,
    dry_run_only: bool,
    max_wallclock_seconds: float | None,
    resume_skip_completed: bool,
    experiment_run_id: str,
    planned_job_keys_signature: str,
    run_state_path: Path,
    run_events_path: Path,
    fixture_length_override: int | None,
    fixed_instance_panel_path: Path | str | None,
    fixed_instance_panel_id: str | None,
    fixed_instance_search_seeds: Sequence[int] | None,
    period_columns: Mapping[int, Sequence[int]],
    resolve_path_fn: Callable[[Path], Path],
) -> dict[str, Any]:
    run_state_abs = resolve_path_fn(run_state_path)
    run_events_abs = resolve_path_fn(run_events_path)
    return {
        "campaign_config_path": _to_repo_rel(campaign_path, repo_root=repo_root),
        "run_mode": str(run_mode),
        "instance_input_mode": str(instance_input_mode),
        "profile_id": str(profile_id),
        "schedule_coverage_mode": str(schedule_coverage_mode),
        "schedule_count": int(len(schedules)),
        "fixture_count": int(len(fixtures)),
        "job_count": int(len(jobs)),
        "scoring_experiment_profiles": [str(x) for x in scoring_experiment_profiles],
        "enable_span_ab_pair": bool(enable_span_ab_pair),
        "span_ab_decision_role": str(span_ab_decision_role),
        "require_no_win10_objectives": bool(require_no_win10_objectives),
        "require_full_text_effective": bool(require_full_text_effective),
        "disable_stage3_span_basin_k_sweep": bool(disable_stage3_span_basin_k_sweep),
        "stage3_span_basin_k_sweep_values": [int(x) for x in stage3_span_basin_k_sweep_values],
        "stage3_tuning_preset_ids": [str(x) for x in stage3_tuning_preset_ids],
        "stage3_tuning_presets": {
            str(k): dict(v)
            for k, v in dict(stage3_tuning_presets or {}).items()
            if isinstance(v, Mapping)
        },
        "dry_run_only": bool(dry_run_only),
        "max_wallclock_seconds": (
            None if max_wallclock_seconds is None else float(max_wallclock_seconds)
        ),
        "resume_skip_completed": bool(resume_skip_completed),
        "experiment_run_id": str(experiment_run_id),
        "planned_job_keys_signature": str(planned_job_keys_signature),
        "run_state_path": _to_repo_rel(run_state_abs, repo_root=repo_root),
        "run_events_path": _to_repo_rel(run_events_abs, repo_root=repo_root),
        "fixture_length_override": (
            None if fixture_length_override is None else int(fixture_length_override)
        ),
        "fixed_instance_panel_path": (
            None
            if fixed_instance_panel_path is None
            else _to_repo_rel(resolve_path_fn(Path(fixed_instance_panel_path)), repo_root=repo_root)
        ),
        "fixed_instance_panel_id": (
            None if fixed_instance_panel_id is None else str(fixed_instance_panel_id)
        ),
        "fixed_instance_search_seeds": (
            []
            if fixed_instance_search_seeds is None
            else [int(x) for x in fixed_instance_search_seeds]
        ),
        "fixtures": [fx.as_dict() for fx in fixtures],
        "period_columns": {str(k): [int(c) for c in v] for k, v in period_columns.items()},
        "jobs": [job.as_dict() for job in jobs],
    }
