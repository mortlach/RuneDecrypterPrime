from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage3_entry_const_local_depth_handoff_7005_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


RUN_LABEL = "stage3_entry_const_local_depth_handoff_7005_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
HANDOFF_ROOT = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260412T053512632846Z__bench_solve_pipeline_no_wli__9557c0f/"
    "resume_handoffs/"
    "fixture_001__p9_c3_l1000__text0__seed1111__search7005"
)
ACTIVATION_OUTPUT_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260501T022336Z__stage3_entry_const_local_depth_handoff_activation_v1"
)

MAX_WALLCLOCK_SECONDS = 16 * 60 * 60
RETAINED_LEGACY_FULL_PIPELINE_SECONDS = 2.4790944444444443 * 3600.0
ENTRY_COUNT_WIDENING_FACTOR = 288.0 / 64.0

CONST_LOCAL_DEPTH_RUN_CONFIG_OVERRIDE = {
    "stage3": {
        "period_scaling": {
            "init_keys_cap": 288,
        },
        "entry": {
            "allocation_policy": "constant_local_depth",
            "mutations_per_promoted": 1,
        },
    },
}

QUESTION = (
    "Starting from the saved 1111/search7005 handoff, can constant-local-depth "
    "Stage-3 entry allocation improve beyond the retained 0.372 result without "
    "recomputing the full pipeline?"
)
SUSPICION = (
    "The 7005 handoff has low retained best match and selected-row headroom; "
    "the activation audit shows constant-local-depth widens init3 from 64 to "
    "288 while preserving the existing 64 legacy keys."
)
MAIN_ALTERNATIVE = (
    "The extra entry keys may only add cost, reproduce the retained route, or "
    "fail to convert the late headroom into a better accepted result."
)
STOP_CONDITION = (
    "Stop after one candidate Stage-3 resume completes, fails, or the external "
    "watchdog reaches 16h."
)


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict(rows[0]).keys()))
        writer.writeheader()
        writer.writerows([dict(row) for row in rows])


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if result != result:
        return float(default)
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return str(default)
    return str(value)


def _run_dir_from_handoff_root(handoff_root: Path) -> Path:
    marker = handoff_root.parts.index("resume_handoffs")
    return Path(*handoff_root.parts[:marker])


def _artifact_path_from_handoff(handoff_root: Path) -> Path:
    manifest = _read_json(handoff_root / "manifest.json")
    artifact_relpath = _safe_str(manifest.get("artifact_relpath"))
    if artifact_relpath:
        artifact_path = REPO_ROOT / artifact_relpath
        if artifact_path.exists():
            return artifact_path
    return _run_dir_from_handoff_root(handoff_root) / "best" / "best_instance.json"


def _build_candidate_prep(
    *,
    artifact: Mapping[str, Any],
    run_config: Mapping[str, Any],
    stage2_resume_raw: Mapping[str, Any],
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    stage2_resume = resume_mod._coerce_stage2_resume_inputs(stage2_resume_raw)
    candidate_run_config = resume_mod._deep_merge_mapping(
        run_config,
        CONST_LOCAL_DEPTH_RUN_CONFIG_OVERRIDE,
    )
    candidate_stage3_prep = resume_mod._build_stage3_prep_from_stage2_resume(
        resume=stage2_resume,
        artifact=artifact,
        run_config=candidate_run_config,
    )
    return stage2_resume, candidate_run_config, candidate_stage3_prep


def _build_readout(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Stage3 Entry Constant-Local-Depth Handoff 7005 v1",
        "",
        "Question:",
        "",
        f"- {QUESTION}",
        "",
        "Coverage:",
        "",
        f"- status: `{summary['status']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.3f}`",
        f"- output dir: `{summary['output_dir']}`",
        "",
        "Result:",
        "",
        f"- retained best: `{float(summary['retained_best_match_ratio']):.3f}`",
        f"- resume best: `{float(summary['resume_best_match_ratio']):.3f}`",
        f"- delta versus retained: `{float(summary['delta_vs_retained']):+.3f}`",
        f"- legacy init3: `{summary['legacy_init3_n']}`",
        f"- candidate init3: `{summary['candidate_init3_n']}`",
        "",
        "Recommendation:",
        "",
        f"- `{summary['recommended_next']}`",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _write_outputs(
    *,
    output_dir: Path,
    rows: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    summary: Mapping[str, Any],
) -> None:
    _write_csv(
        output_dir / "stage3_entry_const_local_depth_handoff_7005_rows.csv",
        rows,
    )
    _write_csv(
        output_dir / "stage3_entry_const_local_depth_handoff_7005_errors.csv",
        errors,
    )
    _write_json(
        output_dir / "stage3_entry_const_local_depth_handoff_7005_summary.json",
        summary,
    )
    (output_dir / "stage3_entry_const_local_depth_handoff_7005_readout.md").write_text(
        _build_readout(summary),
        encoding="utf-8",
    )
    _write_json(output_dir / "run_summary.json", summary)


def run_study() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    cell_dir = output_dir / "cell_0001_1111_search7005_const_local_depth"
    started = time.perf_counter()
    artifact_path = _artifact_path_from_handoff(HANDOFF_ROOT)
    case = resume_mod.load_artifact_case(artifact_path=artifact_path)
    run_config = _read_json(_run_dir_from_handoff_root(HANDOFF_ROOT) / "run_config.json")
    artifact = _read_json(artifact_path)
    saved_stage2_resume_raw = _read_json(HANDOFF_ROOT / "stage2_resume.json")
    saved_stage3_prep = _read_json(HANDOFF_ROOT / "stage3_prep.json")
    stage2_resume, candidate_run_config, candidate_stage3_prep = _build_candidate_prep(
        artifact=artifact,
        run_config=run_config,
        stage2_resume_raw=saved_stage2_resume_raw,
    )
    launch_manifest = {
        "run_label": RUN_LABEL,
        "output_dir": _repo_rel(output_dir),
        "cell_output_dir": _repo_rel(cell_dir),
        "handoff_root": _repo_rel(HANDOFF_ROOT),
        "activation_output_dir": _repo_rel(ACTIVATION_OUTPUT_DIR),
        "artifact_relpath": _repo_rel(artifact_path),
        "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
        "retained_legacy_full_pipeline_seconds": RETAINED_LEGACY_FULL_PIPELINE_SECONDS,
        "entry_count_widening_factor": ENTRY_COUNT_WIDENING_FACTOR,
        "question": QUESTION,
        "suspicion": SUSPICION,
        "main_alternative": MAIN_ALTERNATIVE,
        "stop_condition": STOP_CONDITION,
        "run_config_override": CONST_LOCAL_DEPTH_RUN_CONFIG_OVERRIDE,
        "legacy_init3_n": _safe_int(saved_stage3_prep.get("init3_n")),
        "candidate_init3_n": _safe_int(candidate_stage3_prep.get("init3_n")),
        "legacy_entry_policy": _safe_str(
            saved_stage3_prep.get("stage3_entry_allocation_policy")
        ),
        "candidate_entry_policy": _safe_str(
            candidate_stage3_prep.get("stage3_entry_allocation_policy")
        ),
        "runtime_launched": 1,
        "started_utc": _utc_now_text(),
    }
    _write_json(output_dir / "launch_manifest.json", launch_manifest)
    print(json.dumps(dict(launch_manifest, event="start"), sort_keys=True), flush=True)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    status = "completed"
    payload: dict[str, Any] = {}
    try:
        payload = resume_mod.run_stage3_resume_from_artifact(
            case,
            output_dir=cell_dir,
            run_config_override=CONST_LOCAL_DEPTH_RUN_CONFIG_OVERRIDE,
            stage2_resume_override=stage2_resume,
            stage3_prep_override=candidate_stage3_prep,
            resume_source_override="saved_handoff_stage2_const_local_depth_prep",
        )
        resume_mod.write_resume_bundle(payload, output_dir=cell_dir)
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        errors.append(
            {
                "error_type": type(exc).__name__,
                "error": str(exc),
                "elapsed_seconds": float(time.perf_counter() - started),
            }
        )
    elapsed_seconds = float(time.perf_counter() - started)
    retained_best = _safe_float(artifact.get("best_match_ratio"))
    resume_best = _safe_float(payload.get("resume_best_match_ratio"), retained_best)
    row = {
        "run_label": RUN_LABEL,
        "status": status,
        "output_dir": _repo_rel(output_dir),
        "cell_output_dir": _repo_rel(cell_dir),
        "handoff_root": _repo_rel(HANDOFF_ROOT),
        "artifact_relpath": _repo_rel(artifact_path),
        "fixture_seed": 1111,
        "search_seed": 7005,
        "retained_best_match_ratio": retained_best,
        "retained_best_stage": _safe_str(artifact.get("best_stage")),
        "resume_best_match_ratio": resume_best,
        "resume_best_stage": _safe_str(payload.get("resume_best_stage")),
        "resume_best_score": _safe_float(payload.get("resume_best_score")),
        "delta_vs_retained": resume_best - retained_best,
        "legacy_init3_n": _safe_int(saved_stage3_prep.get("init3_n")),
        "candidate_init3_n": _safe_int(candidate_stage3_prep.get("init3_n")),
        "legacy_entry_policy": _safe_str(
            saved_stage3_prep.get("stage3_entry_allocation_policy")
        ),
        "candidate_entry_policy": _safe_str(
            candidate_stage3_prep.get("stage3_entry_allocation_policy")
        ),
        "candidate_entry_target_before_cap": _safe_int(
            candidate_stage3_prep.get("stage3_entry_target_before_cap")
        ),
        "candidate_entry_cap": _safe_int(candidate_stage3_prep.get("stage3_entry_cap")),
        "stage35_enabled_effective": _safe_int(
            payload.get("stage35_enabled_effective")
        ),
        "elapsed_seconds": elapsed_seconds,
    }
    rows.append(row)
    if status == "completed" and row["delta_vs_retained"] > 0.0:
        recommended_next = "analyze_before_second_handoff_cell"
    elif status == "completed":
        recommended_next = "close_or_refine_const_local_depth_handoff_after_analysis"
    else:
        recommended_next = "inspect_error_or_partial_stage3_resume_status"
    summary = {
        **row,
        "error_count": len(errors),
        "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
        "updated_utc": _utc_now_text(),
        "recommended_next": recommended_next,
    }
    _write_outputs(output_dir=output_dir, rows=rows, errors=errors, summary=summary)
    print(json.dumps(dict(summary, event="finish"), sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_study()


if __name__ == "__main__":
    main()
