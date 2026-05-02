from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
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
        "extract_phaseb_challenger_supply_matrix_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_fixed_instance_solver_development_v1 as base_mod,
    run_phaseb_challenger_supply_matrix_v1 as run_mod,
)

RUN_LABEL = run_mod.RUN_LABEL
OUTPUT_BASE_DIR = base_mod.OUTPUT_BASE_DIR
SOURCE_ROOT = REPO_ROOT / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli"
RUN_PREFIX = "__bench_solve_pipeline_no_wli__"


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


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


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
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
                elif isinstance(value, (list, dict)):
                    payload[key] = json.dumps(value, sort_keys=True)
                else:
                    payload[key] = value
            writer.writerow(payload)


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _stage3_diagnostics(best_instance: Mapping[str, Any]) -> Mapping[str, Any]:
    diagnostics = best_instance.get("stage3_diagnostics")
    if isinstance(diagnostics, Mapping):
        return diagnostics
    return {}


def _winner_candidate_hash(best_instance: Mapping[str, Any]) -> str:
    diagnostics = _stage3_diagnostics(best_instance)
    for row in list(diagnostics.get("phaseC_start_summaries", []) or []):
        if not isinstance(row, Mapping):
            continue
        if _safe_int(row.get("became_global_best")) == 1:
            return _safe_str(row.get("candidate_hash"))
    return ""


def _supply_metrics(best_instance: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = _stage3_diagnostics(best_instance)
    start_rows = [
        dict(row)
        for row in list(diagnostics.get("phaseC_start_summaries", []) or [])
        if isinstance(row, Mapping)
    ]
    candidate_pool_rows = [
        dict(row)
        for row in list(diagnostics.get("phaseC_candidate_pool_rows", []) or [])
        if isinstance(row, Mapping)
    ]
    selected_hashes = {
        _safe_str(row.get("candidate_hash"))
        for row in start_rows
        if _safe_str(row.get("candidate_hash"))
    }
    non_anchor_selected_phaseb_topk_count = sum(
        1
        for row in start_rows[1:]
        if _safe_str(row.get("source")) == "phaseB_topk"
    )
    non_selected_phaseb_rows = [
        row
        for row in candidate_pool_rows
        if _safe_str(row.get("source")) == "phaseB_topk"
        and _safe_int(row.get("selected_by_phasec_start")) == 0
    ]
    challenger_hashes = [
        _safe_str(row.get("candidate_hash"))
        for row in non_selected_phaseb_rows
        if _safe_str(row.get("candidate_hash"))
    ]
    unique_challenger_hashes = list(dict.fromkeys(challenger_hashes))
    true_spare_hashes = [
        challenger_hash
        for challenger_hash in unique_challenger_hashes
        if challenger_hash not in selected_hashes
    ]
    duplicate_of_selected_count = int(
        len(unique_challenger_hashes) - len(true_spare_hashes)
    )
    non_anchor_slots = max(0, len(start_rows) - 1)
    unique_challenger_count = int(len(unique_challenger_hashes))
    true_spare_count = int(len(true_spare_hashes))
    quota_engageable = int(
        true_spare_count > 0
        and non_anchor_selected_phaseb_topk_count < non_anchor_slots
    )
    replacement_engageable = int(true_spare_count > 0)
    return {
        "phaseb_downstream_selected_count": _safe_int(
            diagnostics.get("phaseB_downstream_selected_count")
        ),
        "phaseb_selected_unique_end_hash": _safe_int(
            diagnostics.get("phaseB_selected_unique_end_hash")
        ),
        "phaseb_topk_saved_count": _safe_int(
            diagnostics.get("phaseB_topk_saved_count")
        ),
        "phaseb_topk_saved_unique_end_hash": _safe_int(
            diagnostics.get("phaseB_topk_saved_unique_end_hash")
        ),
        "non_anchor_selected_phaseb_topk_count": int(
            non_anchor_selected_phaseb_topk_count
        ),
        "non_selected_phaseb_topk_challenger_count": int(len(non_selected_phaseb_rows)),
        "non_selected_phaseb_topk_unique_challenger_count": int(unique_challenger_count),
        "non_selected_phaseb_topk_duplicate_of_selected_count": int(
            duplicate_of_selected_count
        ),
        "non_selected_phaseb_topk_challenger_hashes": unique_challenger_hashes,
        "non_selected_phaseb_topk_true_spare_unique_challenger_count": int(
            true_spare_count
        ),
        "non_selected_phaseb_topk_true_spare_hashes": list(true_spare_hashes),
        "quota_engageable": int(quota_engageable),
        "replacement_engageable": int(replacement_engageable),
        "phasec_winner_candidate_hash": _winner_candidate_hash(best_instance),
        "phasec_winner_source": _safe_str(diagnostics.get("phaseC_final_winner_source")),
        "phasec_winner_lane": _safe_str(diagnostics.get("phaseC_final_winner_lane")),
    }


def _baseline_rows_by_case() -> dict[tuple[int, int], dict[str, Any]]:
    panel_inventory_rows = base_mod._read_csv_rows(base_mod.PANEL_INVENTORY_CSV)
    best_instances = base_mod._load_best_instances_from_external_pack(panel_inventory_rows)
    baseline_by_case: dict[tuple[int, int], dict[str, Any]] = {}
    for panel_row in panel_inventory_rows:
        fixture_seed = base_mod._safe_int(panel_row.get("fixture_seed"))
        search_seed = base_mod._safe_int(panel_row.get("search_seed"))
        best_instance = dict(best_instances[(fixture_seed, search_seed)])
        baseline_by_case[(fixture_seed, search_seed)] = {
            "panel_job_index": base_mod._safe_int(panel_row.get("panel_job_index")),
            "source_run_label": base_mod._safe_str(panel_row.get("source_run_label")),
            "benchmark_case_role": base_mod._benchmark_case_role(fixture_seed),
            "retained_best_match_ratio": base_mod._safe_float(
                best_instance.get("best_match_ratio")
            ),
            **_supply_metrics(best_instance),
        }
    return baseline_by_case


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
    spec_by_id = {
        _safe_str(spec.get("preset_id")): dict(spec)
        for spec in run_mod.ACTIVE_SUPPLY_PRESET_SPECS
    }
    for preset_id, raw in plan_presets.items():
        raw_dict = dict(raw) if isinstance(raw, Mapping) else {}
        spec = spec_by_id.get(str(preset_id), {})
        summary_by_id[str(preset_id)] = {
            "preset_id": str(preset_id),
            "phaseb_top_n": _safe_int(raw_dict.get("force_stage3_phaseb_top_n")),
            "stage3_topk_limit": _safe_int(raw_dict.get("force_stage3_topk_limit")),
            "tie_eps": _safe_float(raw_dict.get("force_stage3_span_basin_judge_tie_eps")),
            "tie_max_seeds": _safe_int(
                raw_dict.get("force_stage3_span_basin_judge_tie_max_seeds")
            ),
            "stage35_enabled": int(
                1 if bool(raw_dict.get("force_stage35_enabled", False)) else 0
            ),
            "summary_label": _safe_str(spec.get("summary_label")) or str(preset_id),
        }
    return summary_by_id


def _fingerprint_key(
    *,
    instance_fixture_id: str,
    search_seed: int,
    phaseb_top_n: int,
    stage3_topk_limit: int,
    tie_eps: float,
    tie_max_seeds: int,
    stage35_enabled: int,
) -> tuple[str, int, int, int, str, int, int]:
    return (
        str(instance_fixture_id),
        int(search_seed),
        int(phaseb_top_n),
        int(stage3_topk_limit),
        f"{float(tie_eps):.6f}",
        int(tie_max_seeds),
        int(stage35_enabled),
    )


def _expected_fingerprint_for_job(
    *,
    job: Mapping[str, Any],
    preset_summary: Mapping[str, Any],
) -> tuple[str, int, int, int, str, int, int]:
    return _fingerprint_key(
        instance_fixture_id=_safe_str(job.get("instance_fixture_id")),
        search_seed=_safe_int(job.get("search_seed")),
        phaseb_top_n=_safe_int(preset_summary.get("phaseb_top_n")),
        stage3_topk_limit=_safe_int(preset_summary.get("stage3_topk_limit")),
        tie_eps=_safe_float(preset_summary.get("tie_eps")),
        tie_max_seeds=_safe_int(preset_summary.get("tie_max_seeds")),
        stage35_enabled=_safe_int(preset_summary.get("stage35_enabled")),
    )


def _run_fingerprint(run_config: Mapping[str, Any]) -> tuple[str, int, int, int, str, int, int]:
    instance_fixture_ids = list(run_config.get("instance_fixture_ids", []) or [])
    search_seeds = list(run_config.get("search_seeds", []) or [])
    stage3 = dict(run_config.get("stage3", {}) or {})
    two_phase = dict(stage3.get("two_phase", {}) or {})
    span_basin = dict(stage3.get("span_basin_judge", {}) or {})
    root_stage35 = run_config.get("stage35")
    stage35_enabled = 0
    if isinstance(root_stage35, Mapping):
        stage35_enabled = int(bool(root_stage35.get("enabled", True)))
    return _fingerprint_key(
        instance_fixture_id=_safe_str(instance_fixture_ids[0] if instance_fixture_ids else ""),
        search_seed=_safe_int(search_seeds[0] if search_seeds else 0),
        phaseb_top_n=_safe_int(two_phase.get("phase_b_top_n")),
        stage3_topk_limit=_safe_int(
            dict(run_config.get("artifacts", {}) or {}).get("stage3_topk")
        ),
        tie_eps=_safe_float(span_basin.get("tie_eps")),
        tie_max_seeds=_safe_int(span_basin.get("tie_max_seeds")),
        stage35_enabled=int(stage35_enabled),
    )


def _completed_sort_key(run_manifest: Mapping[str, Any], run_dir: Path) -> tuple[str, float]:
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


def _candidate_runs_by_fingerprint(
    expected_fingerprints: set[tuple[str, int, int, int, str, int, int]],
    *,
    window_start: datetime | None,
    window_end: datetime | None,
) -> dict[tuple[str, int, int, int, str, int, int], dict[str, Any]]:
    matches: dict[tuple[str, int, int, int, str, int, int], list[dict[str, Any]]] = defaultdict(list)
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
        fingerprint = _run_fingerprint(run_config)
        if fingerprint not in expected_fingerprints:
            continue
        run_manifest = (
            _read_json(run_manifest_path) if run_manifest_path.exists() else {}
        )
        if not _run_manifest_within_window(
            run_manifest,
            run_dir=run_dir,
            window_start=window_start,
            window_end=window_end,
        ):
            continue
        matches[fingerprint].append(
            {
                "run_dir": run_dir,
                "run_config": run_config,
                "best_instance": _read_json(best_instance_path),
                "run_manifest": run_manifest,
            }
        )
    selected: dict[tuple[str, int, int, int, str, int, int], dict[str, Any]] = {}
    for fingerprint, rows in matches.items():
        selected[fingerprint] = max(
            rows,
            key=lambda row: _completed_sort_key(
                row.get("run_manifest", {}),
                Path(row["run_dir"]),
            ),
        )
    return selected


def build_case_rows() -> tuple[list[dict[str, Any]], list[str], int]:
    plan_payload = _plan_payload()
    preset_summary_by_id = _plan_preset_summary_by_id(plan_payload)
    jobs = list(plan_payload.get("jobs", []) or [])
    window_start, window_end = _runtime_window(plan_payload)
    expected_fingerprints = {
        _expected_fingerprint_for_job(
            job=dict(job),
            preset_summary=preset_summary_by_id[
                _safe_str(dict(job).get("stage3_tuning_preset_id"))
            ],
        )
        for job in jobs
    }
    matched_runs = _candidate_runs_by_fingerprint(
        expected_fingerprints,
        window_start=window_start,
        window_end=window_end,
    )
    baseline_by_case = _baseline_rows_by_case()

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
        matched = matched_runs.get(fingerprint)
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

        best_instance = dict(matched["best_instance"])
        supply = _supply_metrics(best_instance)
        fixture_seed = _safe_int(best_instance.get("instance_source_key_seed"))
        search_seed = _safe_int(best_instance.get("search_seed"))
        baseline = dict(baseline_by_case[(fixture_seed, search_seed)])
        run_manifest = dict(matched.get("run_manifest", {}))
        rows.append(
            {
                "experiment_run_id": run_mod.EXPERIMENT_RUN_ID,
                "preset_id": preset_id,
                "config_label": _safe_str(preset_summary.get("summary_label")),
                "phaseb_top_n": _safe_int(preset_summary.get("phaseb_top_n")),
                "stage3_topk_limit": _safe_int(preset_summary.get("stage3_topk_limit")),
                "fixture_seed": int(fixture_seed),
                "search_seed": int(search_seed),
                "benchmark_case_role": _safe_str(baseline.get("benchmark_case_role")),
                "panel_job_index": _safe_int(baseline.get("panel_job_index")),
                "run_dir": _relative_path(Path(matched["run_dir"])),
                "best_stage": _safe_str(best_instance.get("best_stage")),
                "status": _safe_str(best_instance.get("status")),
                "elapsed_seconds": _safe_float(run_manifest.get("elapsed_seconds")),
                "best_match_ratio": _safe_float(best_instance.get("best_match_ratio")),
                "retained_best_match_ratio": _safe_float(
                    baseline.get("retained_best_match_ratio")
                ),
                "best_match_delta_vs_retained": (
                    _safe_float(best_instance.get("best_match_ratio"))
                    - _safe_float(baseline.get("retained_best_match_ratio"))
                ),
                "phaseb_downstream_selected_count": _safe_int(
                    supply.get("phaseb_downstream_selected_count")
                ),
                "retained_phaseb_downstream_selected_count": _safe_int(
                    baseline.get("phaseb_downstream_selected_count")
                ),
                "phaseb_selected_unique_end_hash": _safe_int(
                    supply.get("phaseb_selected_unique_end_hash")
                ),
                "retained_phaseb_selected_unique_end_hash": _safe_int(
                    baseline.get("phaseb_selected_unique_end_hash")
                ),
                "phaseb_topk_saved_count": _safe_int(supply.get("phaseb_topk_saved_count")),
                "retained_phaseb_topk_saved_count": _safe_int(
                    baseline.get("phaseb_topk_saved_count")
                ),
                "phaseb_topk_saved_count_delta": _safe_int(
                    supply.get("phaseb_topk_saved_count")
                )
                - _safe_int(baseline.get("phaseb_topk_saved_count")),
                "phaseb_topk_saved_unique_end_hash": _safe_int(
                    supply.get("phaseb_topk_saved_unique_end_hash")
                ),
                "retained_phaseb_topk_saved_unique_end_hash": _safe_int(
                    baseline.get("phaseb_topk_saved_unique_end_hash")
                ),
                "phaseb_topk_saved_unique_end_hash_delta": _safe_int(
                    supply.get("phaseb_topk_saved_unique_end_hash")
                )
                - _safe_int(baseline.get("phaseb_topk_saved_unique_end_hash")),
                "non_anchor_selected_phaseb_topk_count": _safe_int(
                    supply.get("non_anchor_selected_phaseb_topk_count")
                ),
                "retained_non_anchor_selected_phaseb_topk_count": _safe_int(
                    baseline.get("non_anchor_selected_phaseb_topk_count")
                ),
                "non_selected_phaseb_topk_challenger_count": _safe_int(
                    supply.get("non_selected_phaseb_topk_challenger_count")
                ),
                "retained_non_selected_phaseb_topk_challenger_count": _safe_int(
                    baseline.get("non_selected_phaseb_topk_challenger_count")
                ),
                "non_selected_phaseb_topk_unique_challenger_count": _safe_int(
                    supply.get("non_selected_phaseb_topk_unique_challenger_count")
                ),
                "retained_non_selected_phaseb_topk_unique_challenger_count": _safe_int(
                    baseline.get("non_selected_phaseb_topk_unique_challenger_count")
                ),
                "non_selected_phaseb_topk_unique_challenger_count_delta": _safe_int(
                    supply.get("non_selected_phaseb_topk_unique_challenger_count")
                )
                - _safe_int(
                    baseline.get("non_selected_phaseb_topk_unique_challenger_count")
                ),
                "non_selected_phaseb_topk_true_spare_unique_challenger_count": _safe_int(
                    supply.get("non_selected_phaseb_topk_true_spare_unique_challenger_count")
                ),
                "retained_non_selected_phaseb_topk_true_spare_unique_challenger_count": _safe_int(
                    baseline.get("non_selected_phaseb_topk_true_spare_unique_challenger_count")
                ),
                "non_selected_phaseb_topk_true_spare_unique_challenger_count_delta": _safe_int(
                    supply.get("non_selected_phaseb_topk_true_spare_unique_challenger_count")
                )
                - _safe_int(
                    baseline.get("non_selected_phaseb_topk_true_spare_unique_challenger_count")
                ),
                "non_selected_phaseb_topk_duplicate_of_selected_count": _safe_int(
                    supply.get("non_selected_phaseb_topk_duplicate_of_selected_count")
                ),
                "non_selected_phaseb_topk_challenger_hashes": list(
                    supply.get("non_selected_phaseb_topk_challenger_hashes", [])
                ),
                "non_selected_phaseb_topk_true_spare_hashes": list(
                    supply.get("non_selected_phaseb_topk_true_spare_hashes", [])
                ),
                "quota_engageable": _safe_int(supply.get("quota_engageable")),
                "replacement_engageable": _safe_int(
                    supply.get("replacement_engageable")
                ),
                "phasec_winner_candidate_hash": _safe_str(
                    supply.get("phasec_winner_candidate_hash")
                ),
                "phasec_winner_source": _safe_str(supply.get("phasec_winner_source")),
                "phasec_winner_lane": _safe_str(supply.get("phasec_winner_lane")),
                "retained_phasec_winner_candidate_hash": _safe_str(
                    baseline.get("phasec_winner_candidate_hash")
                ),
                "retained_phasec_winner_source": _safe_str(
                    baseline.get("phasec_winner_source")
                ),
                "retained_phasec_winner_lane": _safe_str(
                    baseline.get("phasec_winner_lane")
                ),
            }
        )

    return (
        sorted(
            rows,
            key=lambda row: (
                _safe_str(row.get("preset_id")),
                _safe_int(row.get("fixture_seed")),
                _safe_int(row.get("search_seed")),
            ),
        ),
        sorted(missing_jobs),
        int(len(jobs)),
    )


def build_config_summary_rows(
    case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows_by_preset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        rows_by_preset[_safe_str(row.get("preset_id"))].append(dict(row))

    summary_rows: list[dict[str, Any]] = []
    for spec in run_mod.ACTIVE_SUPPLY_PRESET_SPECS:
        preset_id = _safe_str(spec.get("preset_id"))
        config_rows = rows_by_preset.get(preset_id, [])
        if not config_rows:
            continue
        summary_rows.append(
            {
                "preset_id": preset_id,
                "config_label": _safe_str(spec.get("summary_label")),
                "phaseb_top_n": _safe_int(config_rows[0].get("phaseb_top_n")),
                "stage3_topk_limit": _safe_int(config_rows[0].get("stage3_topk_limit")),
                "case_count": int(len(config_rows)),
                "mean_elapsed_hours": sum(
                    _safe_float(row.get("elapsed_seconds")) for row in config_rows
                )
                / (3600.0 * len(config_rows)),
                "mean_best_match_ratio": sum(
                    _safe_float(row.get("best_match_ratio")) for row in config_rows
                )
                / len(config_rows),
                "mean_best_match_delta_vs_retained": sum(
                    _safe_float(row.get("best_match_delta_vs_retained"))
                    for row in config_rows
                )
                / len(config_rows),
                "mean_phaseb_topk_saved_count_delta": sum(
                    _safe_int(row.get("phaseb_topk_saved_count_delta"))
                    for row in config_rows
                )
                / len(config_rows),
                "mean_phaseb_topk_saved_unique_end_hash_delta": sum(
                    _safe_int(row.get("phaseb_topk_saved_unique_end_hash_delta"))
                    for row in config_rows
                )
                / len(config_rows),
                "mean_non_selected_phaseb_topk_true_spare_unique_challenger_delta": sum(
                    _safe_int(
                        row.get(
                            "non_selected_phaseb_topk_true_spare_unique_challenger_count_delta"
                        )
                    )
                    for row in config_rows
                )
                / len(config_rows),
                "cases_with_spare_challengers_ge_1": sum(
                    1
                    for row in config_rows
                    if _safe_int(
                        row.get("non_selected_phaseb_topk_true_spare_unique_challenger_count")
                    )
                    >= 1
                ),
                "cases_with_spare_challengers_ge_2": sum(
                    1
                    for row in config_rows
                    if _safe_int(
                        row.get("non_selected_phaseb_topk_true_spare_unique_challenger_count")
                    )
                    >= 2
                ),
                "cases_with_spare_challengers_ge_3": sum(
                    1
                    for row in config_rows
                    if _safe_int(
                        row.get("non_selected_phaseb_topk_true_spare_unique_challenger_count")
                    )
                    >= 3
                ),
                "cases_with_quota_engageable": sum(
                    _safe_int(row.get("quota_engageable")) for row in config_rows
                ),
                "cases_with_replacement_engageable": sum(
                    _safe_int(row.get("replacement_engageable")) for row in config_rows
                ),
                "max_unique_challenger_count": max(
                    _safe_int(
                        row.get("non_selected_phaseb_topk_true_spare_unique_challenger_count")
                    )
                    for row in config_rows
                ),
            }
        )
    return summary_rows


def build_recommendation(
    summary_rows: Sequence[Mapping[str, Any]],
    *,
    missing_job_count: int,
    expected_job_count: int,
) -> dict[str, Any]:
    if missing_job_count > 0:
        best_row = (
            max(
                (dict(row) for row in summary_rows),
                key=lambda row: (
                    _safe_int(row.get("cases_with_spare_challengers_ge_2")),
                    _safe_int(row.get("cases_with_spare_challengers_ge_1")),
                    _safe_float(
                        row.get("mean_non_selected_phaseb_topk_true_spare_unique_challenger_delta")
                    ),
                    _safe_float(row.get("mean_phaseb_topk_saved_unique_end_hash_delta")),
                    _safe_float(row.get("mean_best_match_delta_vs_retained")),
                ),
            )
            if summary_rows
            else {}
        )
        matched_job_count = max(0, int(expected_job_count) - int(missing_job_count))
        return {
            "recommendation": "incomplete",
            "best_preset_id": _safe_str(best_row.get("preset_id")),
            "best_config_label": _safe_str(best_row.get("config_label")),
            "reason": (
                "Only a partial runtime slice completed "
                f"({matched_job_count}/{int(expected_job_count)} jobs). "
                "Treat the output as rescued partial evidence, not a full-study decision."
            ),
        }
    if not summary_rows:
        return {
            "recommendation": "close",
            "best_preset_id": "",
            "best_config_label": "",
            "reason": "No completed supply-study rows were available.",
        }
    best_row = max(
        (dict(row) for row in summary_rows),
        key=lambda row: (
            _safe_int(row.get("cases_with_spare_challengers_ge_2")),
            _safe_int(row.get("cases_with_spare_challengers_ge_1")),
            _safe_float(
                row.get("mean_non_selected_phaseb_topk_true_spare_unique_challenger_delta")
            ),
            _safe_float(row.get("mean_phaseb_topk_saved_unique_end_hash_delta")),
            _safe_float(row.get("mean_best_match_delta_vs_retained")),
        ),
    )
    spare_ge_1 = _safe_int(best_row.get("cases_with_spare_challengers_ge_1"))
    spare_ge_2 = _safe_int(best_row.get("cases_with_spare_challengers_ge_2"))
    quota_cases = _safe_int(best_row.get("cases_with_quota_engageable"))
    mean_saved_unique_delta = _safe_float(
        best_row.get("mean_phaseb_topk_saved_unique_end_hash_delta")
    )
    if spare_ge_1 >= 3 and spare_ge_2 >= 2 and quota_cases >= 2:
        recommendation = "promote"
        reason = (
            "One config creates real spare non-selected phaseB_topk challengers "
            "across several cases, and the downstream quota/replacement levers "
            "become genuinely engageable."
        )
    elif spare_ge_1 >= 1 or mean_saved_unique_delta > 0.0:
        recommendation = "refine"
        reason = (
            "Supply increased on at least part of the slice, but the challenger "
            "counts are still narrow or too small to reopen downstream work cleanly."
        )
    else:
        recommendation = "close"
        reason = (
            "Wider upstream supply did not create meaningful spare non-selected "
            "phaseB_topk challengers on this runtime slice."
        )
    return {
        "recommendation": recommendation,
        "best_preset_id": _safe_str(best_row.get("preset_id")),
        "best_config_label": _safe_str(best_row.get("config_label")),
        "reason": reason,
    }


def write_markdown(
    output_dir: Path,
    *,
    case_rows: Sequence[Mapping[str, Any]],
    summary_rows: Sequence[Mapping[str, Any]],
    recommendation: Mapping[str, Any],
    expected_job_count: int,
    missing_jobs: Sequence[str],
) -> None:
    matched_job_count = int(len(case_rows))
    lines = [
        "# Phase-B Challenger Supply Matrix",
        "",
        "Question:",
        "- can wider upstream Phase-B saved challenger supply create spare non-selected phaseB_topk challengers that make downstream Phase-C quota or replacement policies genuinely engageable?",
        "",
        "Operational slice:",
        f"- panel: `{_relative_path(REPO_ROOT / run_mod.PRIMARY_TRIO_PANEL_PATH)}`",
        f"- presets: `{', '.join(run_mod.active_preset_ids())}`",
        "- stage35: `off`",
        "",
        "Coverage:",
        f"- completed jobs: `{matched_job_count}/{int(expected_job_count)}`",
        f"- missing jobs: `{int(len(missing_jobs))}`",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- best config: `{_safe_str(recommendation.get('best_config_label'))}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Per-config summary:",
        "",
        "| config | phaseB_top_n | save_topk | cases | spare>=1 | spare>=2 | spare>=3 | quota engageable | replacement engageable | mean unique challenger delta | mean saved unique delta | mean match delta vs retained |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| `{_safe_str(row.get('config_label'))}` | "
            f"`{_safe_int(row.get('phaseb_top_n'))}` | "
            f"`{_safe_int(row.get('stage3_topk_limit'))}` | "
            f"`{_safe_int(row.get('case_count'))}` | "
            f"`{_safe_int(row.get('cases_with_spare_challengers_ge_1'))}` | "
            f"`{_safe_int(row.get('cases_with_spare_challengers_ge_2'))}` | "
            f"`{_safe_int(row.get('cases_with_spare_challengers_ge_3'))}` | "
            f"`{_safe_int(row.get('cases_with_quota_engageable'))}` | "
            f"`{_safe_int(row.get('cases_with_replacement_engageable'))}` | "
            f"`{_safe_float(row.get('mean_non_selected_phaseb_topk_true_spare_unique_challenger_delta')):.2f}` | "
            f"`{_safe_float(row.get('mean_phaseb_topk_saved_unique_end_hash_delta')):.2f}` | "
            f"`{_safe_float(row.get('mean_best_match_delta_vs_retained')):.3f}` |"
        )
    lines.extend(
        [
            "",
            "Per-case rows:",
            "",
            "| config | case | saved_count delta | saved_unique delta | spare challengers | quota | replacement | match delta | winner |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in case_rows:
        lines.append(
            f"| `{_safe_str(row.get('config_label'))}` | "
            f"`{_safe_int(row.get('fixture_seed'))}/search{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_int(row.get('phaseb_topk_saved_count_delta'))}` | "
            f"`{_safe_int(row.get('phaseb_topk_saved_unique_end_hash_delta'))}` | "
            f"`{_safe_int(row.get('non_selected_phaseb_topk_true_spare_unique_challenger_count'))}` | "
            f"`{_safe_int(row.get('quota_engageable'))}` | "
            f"`{_safe_int(row.get('replacement_engageable'))}` | "
            f"`{_safe_float(row.get('best_match_delta_vs_retained')):.3f}` | "
            f"`{_safe_str(row.get('phasec_winner_source'))}/{_safe_str(row.get('phasec_winner_lane'))}` |"
        )
    if missing_jobs:
        lines.extend(
            [
                "",
                "Missing jobs:",
            ]
        )
        for job in list(missing_jobs):
            lines.append(f"- `{_safe_str(job)}`")
    (output_dir / "phaseb_challenger_supply_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_extract() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    case_rows, missing_jobs, expected_job_count = build_case_rows()
    summary_rows = build_config_summary_rows(case_rows)
    recommendation = build_recommendation(
        summary_rows,
        missing_job_count=int(len(missing_jobs)),
        expected_job_count=int(expected_job_count),
    )
    summary = {
        "run_label": RUN_LABEL,
        "experiment_run_id": run_mod.EXPERIMENT_RUN_ID,
        "plan_output_path": _relative_path(REPO_ROOT / run_mod.MATRIX_CONTROL_FILES.plan_output_path),
        "panel_path": _relative_path(REPO_ROOT / run_mod.PRIMARY_TRIO_PANEL_PATH),
        "expected_job_count": int(expected_job_count),
        "matched_job_count": int(len(case_rows)),
        "missing_job_count": int(len(missing_jobs)),
        "completion_fraction": (
            0.0
            if int(expected_job_count) <= 0
            else float(len(case_rows)) / float(expected_job_count)
        ),
        "missing_jobs": list(missing_jobs),
        "case_count": int(len(case_rows)),
        "config_count": int(len(summary_rows)),
        "recommendation": dict(recommendation),
        "config_summary_rows": summary_rows,
        "output_dir": _relative_path(output_dir),
    }

    _write_jsonl(output_dir / "phaseb_challenger_supply_case_rows.jsonl", case_rows)
    _write_csv(output_dir / "phaseb_challenger_supply_case_rows.csv", case_rows)
    _write_csv(output_dir / "phaseb_challenger_supply_config_summary.csv", summary_rows)
    _write_json(output_dir / "phaseb_challenger_supply_summary.json", summary)
    _write_json(output_dir / "phaseb_challenger_supply_recommendation.json", recommendation)
    _write_json(output_dir / "phaseb_challenger_supply_missing_jobs.json", list(missing_jobs))
    write_markdown(
        output_dir,
        case_rows=case_rows,
        summary_rows=summary_rows,
        recommendation=recommendation,
        expected_job_count=int(expected_job_count),
        missing_jobs=missing_jobs,
    )

    run_summary = {
        "output_dir": _relative_path(output_dir),
        "expected_job_count": int(expected_job_count),
        "matched_job_count": int(len(case_rows)),
        "missing_job_count": int(len(missing_jobs)),
        "case_count": int(len(case_rows)),
        "config_count": int(len(summary_rows)),
        "recommendation": _safe_str(recommendation.get("recommendation")),
        "best_preset_id": _safe_str(recommendation.get("best_preset_id")),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
