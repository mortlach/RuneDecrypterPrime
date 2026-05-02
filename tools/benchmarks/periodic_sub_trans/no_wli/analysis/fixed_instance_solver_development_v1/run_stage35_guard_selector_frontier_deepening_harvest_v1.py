from __future__ import annotations

import csv
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage35_guard_selector_frontier_deepening_harvest_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


RUN_LABEL = "stage35_guard_selector_frontier_deepening_harvest_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
SOURCE_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/"
    "stage35_guard_selector_frontier_runtime_rows.csv"
)
MAX_WALLCLOCK_SECONDS = 8 * 60 * 60
PER_CELL_MAX_RUNTIME_SECONDS = 1800
MAX_CELLS = 36
MIN_SHALLOW_DELTA = 0.05
STOP_IF_FIRST_CELL_PROJECTS_OVER_BUDGET = True

STAGE35_CFG_OVERRIDE: dict[str, Any] = {
    "seed_keep": 4,
    "beam_width": 2,
    "archive_keep": 24,
    "rounds": 3,
    "mini_search_steps": 2,
    "mini_search_beam_width": 3,
    "mini_search_top_symbols": 12,
    "mini_search_final_keep": 4,
    "mini_search_keep_all_rows": 0,
    "max_runtime_seconds": PER_CELL_MAX_RUNTIME_SECONDS,
    "max_evals": 0,
    "accept_guard_passing_selector_mode": "top_score_then_search",
}


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(result):
        return float(default)
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(text)).strip("_")[:96]


def load_source_rows() -> list[dict[str, Any]]:
    path = REPO_ROOT / SOURCE_ROWS_REL
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            row = dict(raw)
            if str(row.get("stage35_selected", "")) != "1":
                continue
            if _safe_float(row.get("resume_minus_selected")) < MIN_SHALLOW_DELTA:
                continue
            rows.append(row)
    rows.sort(
        key=lambda row: (
            -_safe_float(row.get("resume_minus_selected")),
            -_safe_float(row.get("resume_best_match_ratio")),
            _safe_int(row.get("candidate_rank")),
            str(row.get("candidate_hash", "")),
        )
    )
    return rows[:MAX_CELLS]


def load_selected_row(*, artifact_path: Path, candidate_hash: str) -> dict[str, Any]:
    case = resume_mod.load_artifact_case(artifact_path=artifact_path)
    rows = resume_mod.load_phasec_frontier_rows(
        artifact_path=case.artifact_path,
        artifact=case.artifact,
    )
    for raw in rows:
        row = dict(raw)
        hashes = {
            str(row.get("candidate_hash", "") or ""),
            str(row.get("end_hash", "") or ""),
            str(row.get("start_hash", "") or ""),
        }
        if str(candidate_hash) in hashes:
            row["selector"] = "score_plus_novelty"
            return row
    raise ValueError(f"Candidate hash not found in frontier rows: {candidate_hash}")


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def result_row(
    *,
    output_dir: Path,
    cell_dir: Path,
    source_row: Mapping[str, Any],
    payload: Mapping[str, Any],
    elapsed_seconds: float,
) -> dict[str, Any]:
    stage35 = dict(payload.get("stage35", {}) or {})
    telemetry = dict(stage35.get("telemetry", {}) or {})
    retained = _safe_float(source_row.get("retained_best_match_ratio"))
    start = _safe_float(payload.get("selected_candidate_final_match"))
    resume = _safe_float(payload.get("resume_best_match_ratio"))
    return {
        "run_label": RUN_LABEL,
        "output_dir": _repo_rel(output_dir),
        "cell_output_dir": _repo_rel(cell_dir),
        "source_shallow_output_dir": str(source_row.get("output_dir", "") or ""),
        "artifact_relpath": str(source_row.get("artifact_relpath", "") or ""),
        "fixture_seed": _safe_int(source_row.get("fixture_seed")),
        "search_seed": _safe_int(source_row.get("search_seed")),
        "candidate_rank": _safe_int(source_row.get("candidate_rank")),
        "candidate_hash": str(source_row.get("candidate_hash", "") or ""),
        "shallow_resume_best_match_ratio": _safe_float(
            source_row.get("resume_best_match_ratio")
        ),
        "shallow_resume_minus_selected": _safe_float(
            source_row.get("resume_minus_selected")
        ),
        "retained_best_match_ratio": retained,
        "selected_start_match_ratio": start,
        "resume_best_match_ratio": resume,
        "resume_minus_retained": resume - retained,
        "resume_minus_selected": resume - start,
        "resume_minus_shallow": resume
        - _safe_float(source_row.get("resume_best_match_ratio")),
        "stage35_selected": _safe_int(stage35.get("selected")),
        "stage35_accept_reason": str(stage35.get("accept_reason", "") or ""),
        "stage35_selected_archive_rank": _safe_int(
            stage35.get("selected_archive_rank")
        ),
        "stage35_selected_via_guard_passing_selector": _safe_int(
            stage35.get("selected_via_guard_passing_selector")
        ),
        "stage35_rounds_completed": _safe_int(stage35.get("rounds_completed")),
        "stage35_evals": _safe_int(stage35.get("evals")),
        "stage35_archive_rows": len(list(stage35.get("archive_rows", []) or [])),
        "stage35_mini_search_count": _safe_int(telemetry.get("mini_search_count")),
        "stage35_rows_scored": _safe_int(telemetry.get("mini_search_rows_scored")),
        "elapsed_seconds": float(elapsed_seconds),
    }


def write_outputs(
    *,
    output_dir: Path,
    rows: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    completed_cells: int,
    total_cells: int,
    status: str,
    started: float,
) -> None:
    _write_csv(output_dir / "stage35_guard_selector_frontier_deepening_rows.csv", rows)
    _write_csv(output_dir / "stage35_guard_selector_frontier_deepening_errors.csv", errors)
    selected = [row for row in rows if int(row["stage35_selected"]) == 1]
    better_than_shallow = [
        row for row in selected if float(row["resume_minus_shallow"]) > 0.0
    ]
    worse_than_shallow = [
        row for row in selected if float(row["resume_minus_shallow"]) < 0.0
    ]
    elapsed = float(time.perf_counter() - started)
    summary = {
        "run_label": RUN_LABEL,
        "status": status,
        "output_dir": _repo_rel(output_dir),
        "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
        "per_cell_max_runtime_seconds": PER_CELL_MAX_RUNTIME_SECONDS,
        "max_cells": MAX_CELLS,
        "min_shallow_delta": MIN_SHALLOW_DELTA,
        "completed_cells": completed_cells,
        "total_cells": total_cells,
        "successful_cells": len(rows),
        "error_cells": len(errors),
        "stage35_selected_cells": len(selected),
        "better_than_shallow_cells": len(better_than_shallow),
        "worse_than_shallow_cells": len(worse_than_shallow),
        "elapsed_seconds": elapsed,
        "updated_utc": _utc_now_text(),
        "recommended_next": "extract_deepening_results_after_completion_or_wallclock_stop",
    }
    _write_json(
        output_dir / "stage35_guard_selector_frontier_deepening_summary.json",
        summary,
    )
    (output_dir / "stage35_guard_selector_frontier_deepening_readout.md").write_text(
        build_readout(summary),
        encoding="utf-8",
    )


def build_readout(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Stage35 Guard-Selector Frontier Deepening Harvest v1",
        "",
        "Question:",
        "",
        "- if the strongest shallow accepted cells get a deeper bounded Stage 3.5",
        "  follow-up, do they improve beyond the one-round result?",
        "",
        "Budget:",
        "",
        f"- max wallclock seconds: `{MAX_WALLCLOCK_SECONDS}`",
        f"- per-cell max runtime seconds: `{PER_CELL_MAX_RUNTIME_SECONDS}`",
        f"- max cells: `{MAX_CELLS}`",
        f"- shallow delta floor: `{MIN_SHALLOW_DELTA}`",
        "",
        "Coverage:",
        "",
        f"- status: `{summary['status']}`",
        f"- completed cells: `{summary['completed_cells']} / {summary['total_cells']}`",
        f"- successful cells: `{summary['successful_cells']}`",
        f"- error cells: `{summary['error_cells']}`",
        f"- selected cells: `{summary['stage35_selected_cells']}`",
        f"- better than shallow: `{summary['better_than_shallow_cells']}`",
        f"- worse than shallow: `{summary['worse_than_shallow_cells']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.3f}`",
    ]
    return "\n".join(lines).rstrip() + "\n"


def run_harvest() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    queue = load_source_rows()
    total_cells = len(queue)
    print(
        json.dumps(
            {
                "event": "start",
                "run_label": RUN_LABEL,
                "output_dir": _repo_rel(output_dir),
                "total_cells": total_cells,
                "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
                "per_cell_max_runtime_seconds": PER_CELL_MAX_RUNTIME_SECONDS,
                "utc": _utc_now_text(),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    completed_cells = 0
    status = "completed"
    first_elapsed: float | None = None
    for cell_index, source_row in enumerate(queue, start=1):
        if float(time.perf_counter() - started) >= MAX_WALLCLOCK_SECONDS:
            status = "wallclock_budget_reached"
            break
        artifact_path = REPO_ROOT / str(source_row.get("artifact_relpath", "") or "")
        candidate_hash = str(source_row.get("candidate_hash", "") or "")
        cell_dir = output_dir / _safe_slug(
            f"cell_{cell_index:04d}_seed{source_row.get('fixture_seed')}_search{source_row.get('search_seed')}_rank{source_row.get('candidate_rank')}_{candidate_hash}"
        )
        cell_started = time.perf_counter()
        try:
            case = resume_mod.load_artifact_case(artifact_path=artifact_path)
            selected_row = load_selected_row(
                artifact_path=artifact_path,
                candidate_hash=candidate_hash,
            )
            payload = resume_mod.run_stage35_from_selected_trial_row(
                case,
                selected_row=selected_row,
                stage35_cfg_override=STAGE35_CFG_OVERRIDE,
                output_dir=cell_dir,
            )
            resume_mod.write_resume_bundle(payload, output_dir=cell_dir)
            cell_elapsed = float(time.perf_counter() - cell_started)
            rows.append(
                result_row(
                    output_dir=output_dir,
                    cell_dir=cell_dir,
                    source_row=source_row,
                    payload=payload,
                    elapsed_seconds=cell_elapsed,
                )
            )
        except Exception as exc:  # noqa: BLE001
            cell_elapsed = float(time.perf_counter() - cell_started)
            errors.append(
                {
                    "cell_index": cell_index,
                    "artifact_relpath": str(source_row.get("artifact_relpath", "")),
                    "candidate_hash": candidate_hash,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "elapsed_seconds": cell_elapsed,
                }
            )
        completed_cells = cell_index
        if first_elapsed is None:
            first_elapsed = cell_elapsed
            projected = float(first_elapsed * total_cells)
            print(
                json.dumps(
                    {
                        "event": "first_cell_projection",
                        "first_cell_elapsed_seconds": round(first_elapsed, 3),
                        "projected_serial_seconds": round(projected, 3),
                        "budget_seconds": MAX_WALLCLOCK_SECONDS,
                        "utc": _utc_now_text(),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            if STOP_IF_FIRST_CELL_PROJECTS_OVER_BUDGET and projected > MAX_WALLCLOCK_SECONDS:
                status = "stopped_after_first_cell_projection_over_budget"
        write_outputs(
            output_dir=output_dir,
            rows=rows,
            errors=errors,
            completed_cells=completed_cells,
            total_cells=total_cells,
            status="partial" if completed_cells < total_cells else status,
            started=started,
        )
        elapsed_total = float(time.perf_counter() - started)
        eta = (
            float((total_cells - completed_cells) / (completed_cells / elapsed_total))
            if completed_cells and elapsed_total > 0
            else 0.0
        )
        print(
            json.dumps(
                {
                    "event": "progress",
                    "completed_cells": completed_cells,
                    "total_cells": total_cells,
                    "successful_cells": len(rows),
                    "error_cells": len(errors),
                    "last_cell_elapsed_seconds": round(cell_elapsed, 3),
                    "elapsed_seconds": round(elapsed_total, 3),
                    "eta_seconds": round(eta, 3),
                    "utc": _utc_now_text(),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        if status == "stopped_after_first_cell_projection_over_budget":
            break
    write_outputs(
        output_dir=output_dir,
        rows=rows,
        errors=errors,
        completed_cells=completed_cells,
        total_cells=total_cells,
        status=status,
        started=started,
    )
    summary = json.loads(
        (
            output_dir / "stage35_guard_selector_frontier_deepening_summary.json"
        ).read_text(encoding="utf-8")
    )
    print(json.dumps(dict(summary, event="finish"), sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_harvest()


if __name__ == "__main__":
    main()
