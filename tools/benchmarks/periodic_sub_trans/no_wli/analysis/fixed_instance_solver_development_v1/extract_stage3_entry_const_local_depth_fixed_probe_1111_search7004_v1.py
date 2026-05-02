from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_fixed_instance_solver_development_v1 as base_mod,
    run_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1 as run_mod,
)


RUN_LABEL = run_mod.RUN_LABEL
OUTPUT_BASE_DIR = base_mod.OUTPUT_BASE_DIR
SOURCE_ROOT = (
    REPO_ROOT / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli"
)
RUN_PREFIX = "__bench_solve_pipeline_no_wli__"
RETAINED_COMPARE_ROWS_CSV = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
    / "20260415T160503Z__fixed_instance_solver_development_v1"
    / "1111_conversion_compare_rows.csv"
)
DEFAULT_ENTRY_ALLOCATION_POLICY = "legacy_fixed_budget"
DEFAULT_ENTRY_TARGET_BEFORE_CAP = 64
DEFAULT_INIT_KEYS_CAP = 192
DEFAULT_ENTRY_MUTATIONS_PER_PROMOTED = 1
DEFAULT_STAGE3_INIT3_COUNT = 64


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if result != result:
        return float(default)
    return result


def _safe_str(value: Any) -> str:
    return str(value or "")


def _parse_utc_timestamp(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True))
            handle.write("\n")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    fieldnames = list(dict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload: dict[str, Any] = {}
            for key, value in dict(row).items():
                if isinstance(value, float) and not math.isfinite(value):
                    payload[key] = ""
                elif isinstance(value, (dict, list)):
                    payload[key] = json.dumps(value, sort_keys=True)
                else:
                    payload[key] = value
            writer.writerow(payload)


def _plan_payload() -> dict[str, Any]:
    plan_path = REPO_ROOT / run_mod.MATRIX_CONTROL_FILES.plan_output_path
    if not plan_path.exists():
        raise FileNotFoundError(
            f"Missing runtime plan output: {_relative_path(plan_path)}"
        )
    payload = _read_json(plan_path)
    experiment_run_id = _safe_str(payload.get("experiment_run_id"))
    if experiment_run_id != str(run_mod.EXPERIMENT_RUN_ID):
        raise ValueError(
            "Unexpected experiment_run_id in plan output: "
            f"expected {run_mod.EXPERIMENT_RUN_ID} got {experiment_run_id}"
        )
    return payload


def _runtime_window(
    plan_payload: Mapping[str, Any],
) -> tuple[datetime | None, datetime | None]:
    run_state_rel = _safe_str(plan_payload.get("run_state_path"))
    if not run_state_rel:
        return (None, None)
    run_state_path = REPO_ROOT / run_state_rel
    if not run_state_path.exists():
        return (None, None)
    run_state = _read_json(run_state_path)
    completed_jobs = _safe_int(run_state.get("completed_jobs"))
    remaining_jobs = _safe_int(run_state.get("remaining_jobs"))
    job_count = _safe_int(plan_payload.get("job_count"))
    started_raw = _safe_str(run_state.get("started_utc"))
    updated_raw = _safe_str(run_state.get("updated_utc"))
    stopped_early = _safe_int(run_state.get("stopped_early"))
    if (
        completed_jobs <= 0
        and not stopped_early
        and updated_raw == started_raw
        and (job_count <= 0 or remaining_jobs >= job_count)
    ):
        return (None, None)
    started_utc = _parse_utc_timestamp(run_state.get("started_utc"))
    updated_utc = _parse_utc_timestamp(
        run_state.get("updated_utc") or run_state.get("completed_utc")
    )
    return (started_utc, updated_utc)


def _plan_preset_summary_by_id(
    plan_payload: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    plan_presets = dict(plan_payload.get("stage3_tuning_presets", {}) or {})
    summary_by_id: dict[str, dict[str, Any]] = {}
    for preset_id, raw in plan_presets.items():
        raw_dict = dict(raw) if isinstance(raw, Mapping) else {}
        summary_by_id[str(preset_id)] = {
            "preset_id": str(preset_id),
            "summary_label": "entry_const_local_depth_probe",
            "phaseb_top_n": _safe_int(raw_dict.get("force_stage3_phaseb_top_n"), 32),
            "entry_allocation_policy": (
                _safe_str(raw_dict.get("force_stage3_entry_allocation_policy"))
                or DEFAULT_ENTRY_ALLOCATION_POLICY
            ),
            "init_keys_cap": _safe_int(
                raw_dict.get("force_stage3_init_keys_cap"),
                DEFAULT_INIT_KEYS_CAP,
            ),
            "entry_mutations_per_promoted": _safe_int(
                raw_dict.get("force_stage3_entry_mutations_per_promoted"),
                DEFAULT_ENTRY_MUTATIONS_PER_PROMOTED,
            ),
            "stage35_enabled": int(
                1 if bool(raw_dict.get("force_stage35_enabled", True)) else 0
            ),
        }
    return summary_by_id


def _fingerprint_key(
    *,
    instance_fixture_id: str,
    search_seed: int,
    phaseb_top_n: int,
    entry_allocation_policy: str,
    init_keys_cap: int,
    entry_mutations_per_promoted: int,
    stage35_enabled: int,
) -> tuple[str, int, int, str, int, int, int]:
    return (
        str(instance_fixture_id),
        int(search_seed),
        int(phaseb_top_n),
        str(entry_allocation_policy),
        int(init_keys_cap),
        int(entry_mutations_per_promoted),
        int(stage35_enabled),
    )


def _expected_fingerprint_for_job(
    *,
    job: Mapping[str, Any],
    preset_summary: Mapping[str, Any],
) -> tuple[str, int, int, str, int, int, int]:
    return _fingerprint_key(
        instance_fixture_id=_safe_str(job.get("instance_fixture_id")),
        search_seed=_safe_int(job.get("search_seed")),
        phaseb_top_n=_safe_int(preset_summary.get("phaseb_top_n")),
        entry_allocation_policy=_safe_str(
            preset_summary.get("entry_allocation_policy")
        ),
        init_keys_cap=_safe_int(preset_summary.get("init_keys_cap")),
        entry_mutations_per_promoted=_safe_int(
            preset_summary.get("entry_mutations_per_promoted")
        ),
        stage35_enabled=_safe_int(preset_summary.get("stage35_enabled")),
    )


def _run_fingerprint(
    run_config: Mapping[str, Any],
) -> tuple[str, int, int, str, int, int, int]:
    instance_fixture_ids = list(run_config.get("instance_fixture_ids", []) or [])
    search_seeds = list(run_config.get("search_seeds", []) or [])
    stage3 = dict(run_config.get("stage3", {}) or {})
    two_phase = dict(stage3.get("two_phase", {}) or {})
    entry = dict(stage3.get("entry", {}) or {})
    period_scaling = dict(stage3.get("period_scaling", {}) or {})
    stage35 = dict(stage3.get("stage35", {}) or {})
    return _fingerprint_key(
        instance_fixture_id=_safe_str(
            instance_fixture_ids[0] if instance_fixture_ids else ""
        ),
        search_seed=_safe_int(search_seeds[0] if search_seeds else 0),
        phaseb_top_n=_safe_int(two_phase.get("phase_b_top_n")),
        entry_allocation_policy=(
            _safe_str(entry.get("allocation_policy")) or DEFAULT_ENTRY_ALLOCATION_POLICY
        ),
        init_keys_cap=_safe_int(period_scaling.get("init_keys_cap")),
        entry_mutations_per_promoted=_safe_int(
            entry.get("mutations_per_promoted"),
            DEFAULT_ENTRY_MUTATIONS_PER_PROMOTED,
        ),
        stage35_enabled=int(1 if bool(stage35.get("enabled", False)) else 0),
    )


def _completed_sort_key(
    run_manifest: Mapping[str, Any], run_dir: Path
) -> tuple[str, float]:
    completed_utc = _safe_str(run_manifest.get("completed_utc"))
    return (completed_utc, float(run_dir.stat().st_mtime))


def _run_manifest_within_window(
    run_manifest: Mapping[str, Any],
    *,
    run_dir: Path,
    window_start: datetime | None,
    window_end: datetime | None,
) -> bool:
    if window_start is None and window_end is None:
        return True
    manifest_dt = _parse_utc_timestamp(
        run_manifest.get("completed_utc") or run_manifest.get("updated_utc")
    )
    if manifest_dt is None:
        manifest_dt = datetime.fromtimestamp(
            float(run_dir.stat().st_mtime), tz=timezone.utc
        )
    slack = timedelta(minutes=15)
    if window_start is not None and manifest_dt < (window_start - slack):
        return False
    if window_end is not None and manifest_dt > (window_end + slack):
        return False
    return True


def _candidate_run_for_fingerprint(
    expected_fingerprint: tuple[str, int, int, str, int, int, int],
    *,
    window_start: datetime | None,
    window_end: datetime | None,
) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    for run_dir in sorted(SOURCE_ROOT.iterdir(), key=lambda path: path.name):
        if not run_dir.is_dir() or RUN_PREFIX not in run_dir.name:
            continue
        run_config_path = run_dir / "run_config.json"
        best_instance_path = run_dir / "best" / "best_instance.json"
        run_manifest_path = run_dir / "run_manifest.json"
        if not run_config_path.exists() or not best_instance_path.exists():
            continue
        run_config = _read_json(run_config_path)
        if _safe_str(run_config.get("instance_input_mode")) != "fixed_ciphertext":
            continue
        if _run_fingerprint(run_config) != expected_fingerprint:
            continue
        run_manifest = _read_json(run_manifest_path) if run_manifest_path.exists() else {}
        if not _run_manifest_within_window(
            run_manifest,
            run_dir=run_dir,
            window_start=window_start,
            window_end=window_end,
        ):
            continue
        rows.append(
            {
                "run_dir": run_dir,
                "run_config": run_config,
                "best_instance": _read_json(best_instance_path),
                "run_manifest": run_manifest,
            }
        )
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: _completed_sort_key(
            row.get("run_manifest", {}),
            Path(row["run_dir"]),
        ),
    )


def _retained_reference_row() -> dict[str, Any]:
    rows = base_mod._read_csv_rows(RETAINED_COMPARE_ROWS_CSV)
    for row in rows:
        if (
            _safe_int(row.get("fixture_seed")) == 1111
            and _safe_int(row.get("search_seed")) == 7004
        ):
            return dict(row)
    raise ValueError("Missing retained reference row for 1111/search7004")


def _handoff_dir(run_dir: Path, *, instance_fixture_id: str, search_seed: int) -> Path:
    return run_dir / "resume_handoffs" / f"{instance_fixture_id}__search{int(search_seed)}"


def _stage3_handoff_payloads(
    run_dir: Path,
    *,
    instance_fixture_id: str,
    search_seed: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    handoff_dir = _handoff_dir(
        run_dir,
        instance_fixture_id=instance_fixture_id,
        search_seed=search_seed,
    )
    stage3_prep_path = handoff_dir / "stage3_prep.json"
    manifest_path = handoff_dir / "manifest.json"
    if not stage3_prep_path.exists():
        raise FileNotFoundError(
            f"Missing stage3_prep.json: {_relative_path(stage3_prep_path)}"
        )
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest.json: {_relative_path(manifest_path)}")
    return (_read_json(stage3_prep_path), _read_json(manifest_path))


def build_case_rows() -> tuple[list[dict[str, Any]], list[str], int]:
    plan_payload = _plan_payload()
    preset_summary_by_id = _plan_preset_summary_by_id(plan_payload)
    jobs = list(plan_payload.get("jobs", []) or [])
    window_start, window_end = _runtime_window(plan_payload)
    retained = _retained_reference_row()
    rows: list[dict[str, Any]] = []
    missing_jobs: list[str] = []

    for job in jobs:
        job_dict = dict(job)
        preset_id = _safe_str(job_dict.get("stage3_tuning_preset_id"))
        preset_summary = preset_summary_by_id[preset_id]
        fingerprint = _expected_fingerprint_for_job(
            job=job_dict,
            preset_summary=preset_summary,
        )
        matched = _candidate_run_for_fingerprint(
            fingerprint,
            window_start=window_start,
            window_end=window_end,
        )
        if matched is None:
            missing_jobs.append(
                "|".join(
                    [
                        preset_id,
                        _safe_str(job_dict.get("instance_fixture_id")),
                        f"search{_safe_int(job_dict.get('search_seed'))}",
                    ]
                )
            )
            continue

        run_dir = Path(matched["run_dir"])
        run_config = dict(matched["run_config"])
        best_instance = dict(matched["best_instance"])
        run_manifest = dict(matched.get("run_manifest", {}))
        instance_fixture_id = _safe_str(best_instance.get("instance_fixture_id"))
        search_seed = _safe_int(best_instance.get("search_seed"))
        stage3_prep, handoff_manifest = _stage3_handoff_payloads(
            run_dir,
            instance_fixture_id=instance_fixture_id,
            search_seed=search_seed,
        )
        stage2_to_stage3 = dict(handoff_manifest.get("stage2_to_stage3", {}) or {})
        rows.append(
            {
                "experiment_run_id": run_mod.EXPERIMENT_RUN_ID,
                "preset_id": preset_id,
                "config_label": _safe_str(preset_summary.get("summary_label")),
                "fixture_seed": _safe_int(best_instance.get("instance_source_key_seed")),
                "search_seed": search_seed,
                "benchmark_case_role": base_mod._benchmark_case_role(
                    _safe_int(best_instance.get("instance_source_key_seed"))
                ),
                "run_dir": _relative_path(run_dir),
                "elapsed_seconds": _safe_float(
                    run_manifest.get("elapsed_seconds"),
                    _safe_float(best_instance.get("total_seconds"), 0.0),
                ),
                "best_stage": _safe_str(best_instance.get("best_stage")),
                "best_match_ratio": _safe_float(best_instance.get("best_match_ratio")),
                "retained_best_stage": _safe_str(retained.get("best_stage")),
                "retained_best_match_ratio": _safe_float(
                    retained.get("best_match_ratio")
                ),
                "retained_mapped_family_max_final_match": _safe_float(
                    retained.get("max_mapped_family_by_final_match")
                ),
                "best_match_delta_vs_retained": (
                    _safe_float(best_instance.get("best_match_ratio"))
                    - _safe_float(retained.get("best_match_ratio"))
                ),
                "best_match_delta_vs_mapped_family_max": (
                    _safe_float(best_instance.get("best_match_ratio"))
                    - _safe_float(retained.get("max_mapped_family_by_final_match"))
                ),
                "outcome_status": _safe_str(best_instance.get("status")),
                "stop_reason": _safe_str(best_instance.get("stop_reason")),
                "text_offsets": list(run_config.get("text_offsets", []) or []),
                "stage35_enabled": int(
                    1
                    if bool(
                        dict(run_config.get("stage3", {}) or {})
                        .get("stage35", {})
                        .get("enabled", False)
                    )
                    else 0
                ),
                "entry_allocation_policy": _safe_str(
                    stage3_prep.get("stage3_entry_allocation_policy")
                ),
                "entry_target_before_cap": _safe_int(
                    stage3_prep.get("stage3_entry_target_before_cap")
                ),
                "entry_cap": _safe_int(stage3_prep.get("stage3_entry_cap")),
                "entry_cap_applied": int(
                    1 if bool(stage3_prep.get("stage3_entry_cap_applied")) else 0
                ),
                "init3_n": _safe_int(stage3_prep.get("init3_n")),
                "stage3_promoted_keys_count": _safe_int(
                    stage3_prep.get("stage3_promoted_keys_count")
                ),
                "stage3_init3_count": _safe_int(
                    stage2_to_stage3.get("stage3_init3_count")
                ),
                "phaseb_top_n": _safe_int(stage3_prep.get("stage3_phaseB_top_n")),
                "baseline_candidate_source": _safe_str(
                    retained.get("baseline_candidate_source")
                ),
                "baseline_candidate_lane": _safe_str(
                    retained.get("baseline_candidate_lane")
                ),
            }
        )

    return (rows, sorted(missing_jobs), int(len(jobs)))


def build_recommendation(
    case_rows: Sequence[Mapping[str, Any]],
    *,
    missing_job_count: int,
    expected_job_count: int,
) -> dict[str, Any]:
    if missing_job_count > 0:
        matched_job_count = max(0, int(expected_job_count) - int(missing_job_count))
        return {
            "recommendation": "incomplete",
            "best_preset_id": "",
            "best_match_delta_vs_retained": float("nan"),
            "reason": (
                "The probe did not produce a completed artifact "
                f"({matched_job_count}/{int(expected_job_count)} jobs complete). "
                "Treat it as operationally incomplete, not as a branch decision."
            ),
        }

    if not case_rows:
        return {
            "recommendation": "incomplete",
            "best_preset_id": "",
            "best_match_delta_vs_retained": float("nan"),
            "reason": "No completed probe row was found.",
        }

    row = dict(case_rows[0])
    best_match_delta_vs_retained = _safe_float(row.get("best_match_delta_vs_retained"))
    best_match_delta_vs_mapped_family_max = _safe_float(
        row.get("best_match_delta_vs_mapped_family_max")
    )
    widened_target = _safe_int(row.get("entry_target_before_cap")) - int(
        DEFAULT_ENTRY_TARGET_BEFORE_CAP
    )
    widened_init3 = _safe_int(row.get("stage3_init3_count")) - int(
        DEFAULT_STAGE3_INIT3_COUNT
    )
    elapsed_hours = _safe_float(row.get("elapsed_seconds"), 0.0) / 3600.0
    budget_hours = float(run_mod.MAX_WALLCLOCK_SECONDS) / 3600.0
    budget_fit = elapsed_hours <= budget_hours
    executed_widening = widened_target > 0 or widened_init3 > 0

    if best_match_delta_vs_retained >= 0.005 and executed_widening and budget_fit:
        recommendation = "advance"
        reason = (
            "The completed candidate beat the retained control reference with real "
            "executed widening inside the intended session budget."
        )
    elif best_match_delta_vs_retained >= 0.0 and executed_widening:
        recommendation = "refine"
        reason = (
            "The candidate cleared or matched the retained control reference, but "
            "the read is still narrow or budget-fragile."
        )
    else:
        recommendation = "close"
        if not executed_widening:
            reason = (
                "The probe did not show real executed widening, so the mechanism "
                "claim stayed too weak."
            )
        else:
            reason = (
                "The candidate stayed flat or worse than the retained control "
                "reference on the stable 1111/search7004 lane."
            )

    return {
        "recommendation": recommendation,
        "best_preset_id": _safe_str(row.get("preset_id")),
        "best_match_delta_vs_retained": best_match_delta_vs_retained,
        "best_match_delta_vs_mapped_family_max": best_match_delta_vs_mapped_family_max,
        "widened_target": widened_target,
        "widened_init3": widened_init3,
        "elapsed_hours": elapsed_hours,
        "budget_hours": budget_hours,
        "budget_fit": int(1 if budget_fit else 0),
        "reason": reason,
    }


def write_markdown(
    output_dir: Path,
    *,
    case_rows: Sequence[Mapping[str, Any]],
    recommendation: Mapping[str, Any],
    expected_job_count: int,
    missing_jobs: Sequence[str],
) -> None:
    retained = _retained_reference_row()
    matched_job_count = int(len(case_rows))
    lines = [
        "# Stage-3 Entry Constant-Local-Depth Fixed Probe 1111/search7004 v1",
        "",
        "Question:",
        "- on fixed `1111/search7004`, can the bounded Stage-3 entry candidate beat the retained control reference inside an honest `~8h` one-job session?",
        "",
        "Retained fixed reference:",
        "- case: `1111/search7004`",
        f"- retained best stage: `{_safe_str(retained.get('best_stage'))}`",
        f"- retained best match: `{_safe_float(retained.get('best_match_ratio')):.3f}`",
        f"- retained mapped-family max final match: `{_safe_float(retained.get('max_mapped_family_by_final_match')):.3f}`",
        f"- retained baseline lane: `{_safe_str(retained.get('baseline_candidate_source'))}/{_safe_str(retained.get('baseline_candidate_lane'))}`",
        "",
        "Coverage:",
        f"- completed jobs: `{matched_job_count}/{int(expected_job_count)}`",
        f"- missing jobs: `{int(len(missing_jobs))}`",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Probe read:",
        "",
        "| config | best stage | best match | delta vs retained | delta vs mapped-family max | elapsed_hours | entry policy | entry target | entry cap | init3_n | stage3_init3_count | promoted keys |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in case_rows:
        lines.append(
            f"| `{_safe_str(row.get('config_label'))}` | "
            f"`{_safe_str(row.get('best_stage'))}` | "
            f"`{_safe_float(row.get('best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('best_match_delta_vs_retained')):.3f}` | "
            f"`{_safe_float(row.get('best_match_delta_vs_mapped_family_max')):.3f}` | "
            f"`{_safe_float(row.get('elapsed_seconds')) / 3600.0:.2f}` | "
            f"`{_safe_str(row.get('entry_allocation_policy'))}` | "
            f"`{_safe_int(row.get('entry_target_before_cap'))}` | "
            f"`{_safe_int(row.get('entry_cap'))}` | "
            f"`{_safe_int(row.get('init3_n'))}` | "
            f"`{_safe_int(row.get('stage3_init3_count'))}` | "
            f"`{_safe_int(row.get('stage3_promoted_keys_count'))}` |"
        )
    if matched_job_count >= 1:
        lines.extend(
            [
                "",
                "Direct probe interpretation:",
                f"- best minus retained: `{_safe_float(recommendation.get('best_match_delta_vs_retained')):.3f}`",
                f"- best minus mapped-family max: `{_safe_float(recommendation.get('best_match_delta_vs_mapped_family_max')):.3f}`",
                f"- widened entry target vs legacy default: `{_safe_int(recommendation.get('widened_target'))}`",
                f"- widened stage3_init3_count vs legacy default: `{_safe_int(recommendation.get('widened_init3'))}`",
                f"- elapsed hours: `{_safe_float(recommendation.get('elapsed_hours')):.2f}` / budget `{_safe_float(recommendation.get('budget_hours')):.2f}`",
            ]
        )
    if missing_jobs:
        lines.extend(["", "Missing jobs:"])
        for job in missing_jobs:
            lines.append(f"- `{_safe_str(job)}`")
    (
        output_dir
        / "stage3_entry_const_local_depth_fixed_probe_1111_search7004_readout.md"
    ).write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_extract() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    case_rows, missing_jobs, expected_job_count = build_case_rows()
    recommendation = build_recommendation(
        case_rows,
        missing_job_count=int(len(missing_jobs)),
        expected_job_count=int(expected_job_count),
    )
    summary = {
        "run_label": RUN_LABEL,
        "experiment_run_id": run_mod.EXPERIMENT_RUN_ID,
        "plan_output_path": _relative_path(
            REPO_ROOT / run_mod.MATRIX_CONTROL_FILES.plan_output_path
        ),
        "panel_path": _relative_path(REPO_ROOT / run_mod.FIXED_PANEL_PATH),
        "expected_job_count": int(expected_job_count),
        "matched_job_count": int(len(case_rows)),
        "missing_job_count": int(len(missing_jobs)),
        "missing_jobs": list(missing_jobs),
        "recommendation": dict(recommendation),
        "retained_reference_row": _retained_reference_row(),
        "output_dir": _relative_path(output_dir),
    }

    _write_jsonl(
        output_dir
        / "stage3_entry_const_local_depth_fixed_probe_1111_search7004_rows.jsonl",
        case_rows,
    )
    _write_csv(
        output_dir
        / "stage3_entry_const_local_depth_fixed_probe_1111_search7004_rows.csv",
        case_rows,
    )
    _write_json(
        output_dir
        / "stage3_entry_const_local_depth_fixed_probe_1111_search7004_summary.json",
        summary,
    )
    _write_json(
        output_dir
        / "stage3_entry_const_local_depth_fixed_probe_1111_search7004_recommendation.json",
        recommendation,
    )
    write_markdown(
        output_dir,
        case_rows=case_rows,
        recommendation=recommendation,
        expected_job_count=int(expected_job_count),
        missing_jobs=missing_jobs,
    )

    run_summary = {
        "output_dir": _relative_path(output_dir),
        "matched_job_count": int(len(case_rows)),
        "missing_job_count": int(len(missing_jobs)),
        "recommendation": _safe_str(recommendation.get("recommendation")),
        "best_preset_id": _safe_str(recommendation.get("best_preset_id")),
        "best_match_delta_vs_retained": _safe_float(
            recommendation.get("best_match_delta_vs_retained")
        ),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
