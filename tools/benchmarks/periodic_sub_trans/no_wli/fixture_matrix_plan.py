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
    profile_id: str,
    schedule_coverage_mode: str,
    schedules: Sequence[Mapping[str, Any]],
    fixtures: Sequence[Any],
    jobs: Sequence[Any],
    scoring_experiment_profiles: Sequence[str],
    require_no_win10_objectives: bool,
    require_full_text_effective: bool,
    disable_stage3_span_basin_k_sweep: bool,
    stage3_span_basin_k_sweep_values: Sequence[int],
    dry_run_only: bool,
    max_wallclock_seconds: float | None,
    resume_skip_completed: bool,
    run_state_path: Path,
    run_events_path: Path,
    fixture_length_override: int | None,
    period_columns: Mapping[int, Sequence[int]],
    resolve_path_fn: Callable[[Path], Path],
) -> dict[str, Any]:
    run_state_abs = resolve_path_fn(run_state_path)
    run_events_abs = resolve_path_fn(run_events_path)
    return {
        "campaign_config_path": _to_repo_rel(campaign_path, repo_root=repo_root),
        "run_mode": str(run_mode),
        "profile_id": str(profile_id),
        "schedule_coverage_mode": str(schedule_coverage_mode),
        "schedule_count": int(len(schedules)),
        "fixture_count": int(len(fixtures)),
        "job_count": int(len(jobs)),
        "scoring_experiment_profiles": [str(x) for x in scoring_experiment_profiles],
        "require_no_win10_objectives": bool(require_no_win10_objectives),
        "require_full_text_effective": bool(require_full_text_effective),
        "disable_stage3_span_basin_k_sweep": bool(disable_stage3_span_basin_k_sweep),
        "stage3_span_basin_k_sweep_values": [int(x) for x in stage3_span_basin_k_sweep_values],
        "dry_run_only": bool(dry_run_only),
        "max_wallclock_seconds": (
            None if max_wallclock_seconds is None else float(max_wallclock_seconds)
        ),
        "resume_skip_completed": bool(resume_skip_completed),
        "run_state_path": _to_repo_rel(run_state_abs, repo_root=repo_root),
        "run_events_path": _to_repo_rel(run_events_abs, repo_root=repo_root),
        "fixture_length_override": (
            None if fixture_length_override is None else int(fixture_length_override)
        ),
        "fixtures": [fx.as_dict() for fx in fixtures],
        "period_columns": {str(k): [int(c) for c in v] for k, v in period_columns.items()},
        "jobs": [job.as_dict() for job in jobs],
    }
