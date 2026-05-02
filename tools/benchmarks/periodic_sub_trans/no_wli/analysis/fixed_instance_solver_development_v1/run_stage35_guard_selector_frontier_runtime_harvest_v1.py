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
        "run_stage35_guard_selector_frontier_runtime_harvest_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


RUN_LABEL = "stage35_guard_selector_frontier_runtime_harvest_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
FIXED_RUNTIME_COMPLETED_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260429T011225Z__fixed_runtime_wallclock_reference_v1/"
    "fixed_runtime_completed_rows.csv"
)
MAX_WALLCLOCK_SECONDS = 8 * 60 * 60
PER_CELL_MAX_RUNTIME_SECONDS = 900
CANDIDATES_PER_ARTIFACT = 12
STOP_IF_FIRST_CELL_PROJECTS_OVER_BUDGET = True

STAGE35_CFG_OVERRIDE: dict[str, Any] = {
    "seed_keep": 2,
    "beam_width": 1,
    "archive_keep": 12,
    "rounds": 1,
    "mini_search_steps": 1,
    "mini_search_beam_width": 2,
    "mini_search_top_symbols": 10,
    "mini_search_final_keep": 2,
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


def _truth_match(plaintext_idx: Any, target_plaintext_idx: Any) -> float:
    pt = [int(x) for x in list(plaintext_idx or [])]
    target = [int(x) for x in list(target_plaintext_idx or [])]
    if not pt or not target:
        return 0.0
    count = min(len(pt), len(target))
    if count <= 0:
        return 0.0
    same = sum(1 for idx in range(count) if int(pt[idx]) == int(target[idx]))
    return float(same / len(target))


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


def _safe_slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(text)).strip("_")[:96]


def load_runtime_artifact_paths() -> list[Path]:
    csv_path = REPO_ROOT / FIXED_RUNTIME_COMPLETED_ROWS_REL
    paths: list[Path] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rel = str(row.get("path", "") or "")
            if not rel:
                continue
            path = REPO_ROOT / rel
            if path.exists() and path not in paths:
                paths.append(path)
    return paths


def select_frontier_rows(case: Any, *, artifact_index: int) -> list[dict[str, Any]]:
    rows = resume_mod.load_phasec_frontier_rows(
        artifact_path=case.artifact_path,
        artifact=case.artifact,
    )
    target = case.artifact.get("target_plaintext_idx", []) or []
    retained = _safe_float(case.artifact.get("best_match_ratio"))
    selected: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for raw in rows:
        row = dict(raw)
        if not row.get("final_key_idx") or not row.get("final_plaintext_idx"):
            continue
        candidate_hash = str(
            row.get("candidate_hash", "")
            or row.get("end_hash", "")
            or row.get("start_hash", "")
            or ""
        )
        if not candidate_hash or candidate_hash in seen_hashes:
            continue
        seen_hashes.add(candidate_hash)
        final_match = _truth_match(row.get("final_plaintext_idx", []), target)
        row["selector"] = "score_plus_novelty"
        row["_artifact_index"] = artifact_index
        row["_candidate_hash"] = candidate_hash
        row["_final_match"] = final_match
        row["_retained_best_match_ratio"] = retained
        row["_headroom_vs_retained"] = final_match - retained
        selected.append(row)
    selected.sort(
        key=lambda row: (
            -float(row.get("_headroom_vs_retained", 0.0) or 0.0),
            -float(row.get("_final_match", 0.0) or 0.0),
            -_safe_float(row.get("final_score")),
            str(row.get("_candidate_hash", "")),
        )
    )
    return selected[:CANDIDATES_PER_ARTIFACT]


def build_queue() -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for artifact_index, artifact_path in enumerate(load_runtime_artifact_paths(), start=1):
        try:
            case = resume_mod.load_artifact_case(artifact_path=artifact_path)
            candidate_rows = select_frontier_rows(case, artifact_index=artifact_index)
        except Exception as exc:  # noqa: BLE001 - queueing should be salvageable.
            print(
                json.dumps(
                    {
                        "event": "queue_artifact_error",
                        "artifact_relpath": _repo_rel(artifact_path),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            continue
        for candidate_rank, selected_row in enumerate(candidate_rows, start=1):
            queue.append(
                {
                    "artifact_path": artifact_path,
                    "artifact_index": artifact_index,
                    "candidate_rank": candidate_rank,
                    "candidate_hash": str(selected_row.get("_candidate_hash", "")),
                    "selected_row": selected_row,
                    "fixture_seed": _safe_int(
                        case.artifact.get("instance_source_key_seed", 0)
                    ),
                    "search_seed": _safe_int(case.artifact.get("search_seed", 0)),
                    "retained_best_match_ratio": _safe_float(
                        case.artifact.get("best_match_ratio")
                    ),
                    "selected_start_match_ratio": _safe_float(
                        selected_row.get("_final_match")
                    ),
                    "selected_headroom_vs_retained": _safe_float(
                        selected_row.get("_headroom_vs_retained")
                    ),
                }
            )
    queue.sort(
        key=lambda item: (
            -float(item["selected_headroom_vs_retained"]),
            int(item["fixture_seed"]),
            int(item["search_seed"]),
            int(item["candidate_rank"]),
        )
    )
    return queue


def _stage35_status(stage35: Mapping[str, Any]) -> str:
    return str(stage35.get("status", "") or stage35.get("outcome_status", "") or "")


def _stage35_reason(stage35: Mapping[str, Any]) -> str:
    return str(stage35.get("reason", "") or stage35.get("outcome_reason", "") or "")


def build_result_row(
    *,
    output_dir: Path,
    cell_dir: Path,
    queue_item: Mapping[str, Any],
    payload: Mapping[str, Any],
    elapsed_seconds: float,
) -> dict[str, Any]:
    stage35 = dict(payload.get("stage35", {}) or {})
    telemetry = dict(stage35.get("telemetry", {}) or {})
    retained = _safe_float(queue_item.get("retained_best_match_ratio"))
    selected_start = _safe_float(payload.get("selected_candidate_final_match"))
    resume_match = _safe_float(payload.get("resume_best_match_ratio"))
    return {
        "run_label": RUN_LABEL,
        "output_dir": _repo_rel(output_dir),
        "cell_output_dir": _repo_rel(cell_dir),
        "artifact_relpath": _repo_rel(Path(queue_item["artifact_path"])),
        "artifact_index": int(queue_item["artifact_index"]),
        "candidate_rank": int(queue_item["candidate_rank"]),
        "fixture_seed": int(queue_item["fixture_seed"]),
        "search_seed": int(queue_item["search_seed"]),
        "candidate_hash": str(queue_item["candidate_hash"]),
        "selected_source": str(
            dict(queue_item["selected_row"]).get("source", "") or ""
        ),
        "selected_lane": str(dict(queue_item["selected_row"]).get("lane", "") or ""),
        "retained_best_match_ratio": retained,
        "selected_start_match_ratio": selected_start,
        "selected_headroom_vs_retained": selected_start - retained,
        "resume_best_match_ratio": resume_match,
        "resume_minus_retained": resume_match - retained,
        "resume_minus_selected": resume_match - selected_start,
        "stage35_status": _stage35_status(stage35),
        "stage35_reason": _stage35_reason(stage35),
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
    _write_csv(output_dir / "stage35_guard_selector_frontier_runtime_rows.csv", rows)
    _write_csv(output_dir / "stage35_guard_selector_frontier_runtime_errors.csv", errors)
    elapsed = float(time.perf_counter() - started)
    selected_rows = [row for row in rows if int(row["stage35_selected"]) == 1]
    positive_rows = [
        row for row in selected_rows if float(row["resume_minus_selected"]) > 0.0
    ]
    negative_rows = [
        row for row in selected_rows if float(row["resume_minus_selected"]) < 0.0
    ]
    summary = {
        "run_label": RUN_LABEL,
        "status": status,
        "output_dir": _repo_rel(output_dir),
        "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
        "per_cell_max_runtime_seconds": PER_CELL_MAX_RUNTIME_SECONDS,
        "candidates_per_artifact": CANDIDATES_PER_ARTIFACT,
        "completed_cells": completed_cells,
        "total_cells": total_cells,
        "coverage": float(completed_cells / total_cells) if total_cells else 0.0,
        "successful_cells": len(rows),
        "error_cells": len(errors),
        "stage35_selected_cells": len(selected_rows),
        "selected_positive_vs_start": len(positive_rows),
        "selected_negative_vs_start": len(negative_rows),
        "elapsed_seconds": elapsed,
        "updated_utc": _utc_now_text(),
        "recommended_next": "extract_results_after_completion_or_wallclock_stop",
    }
    _write_json(output_dir / "stage35_guard_selector_frontier_runtime_summary.json", summary)
    (output_dir / "stage35_guard_selector_frontier_runtime_readout.md").write_text(
        build_readout(summary=summary),
        encoding="utf-8",
    )


def build_readout(*, summary: Mapping[str, Any]) -> str:
    lines = [
        "# Stage35 Guard-Selector Frontier Runtime Harvest v1",
        "",
        "Question:",
        "",
        "- across retained fixed-panel artefacts and multiple saved frontier rows per",
        "  artefact, where does one bounded strict guard-selector Stage 3.5 rescue",
        "  actually accept useful local improvements?",
        "",
        "Budget:",
        "",
        f"- max wallclock seconds: `{MAX_WALLCLOCK_SECONDS}`",
        f"- per-cell max runtime seconds: `{PER_CELL_MAX_RUNTIME_SECONDS}`",
        f"- candidates per artefact: `{CANDIDATES_PER_ARTIFACT}`",
        "- stop condition: queue exhausted, wallclock budget reached, or first-cell",
        "  projection exceeds the session budget",
        "",
        "Current Coverage:",
        "",
        f"- status: `{summary['status']}`",
        f"- completed cells: `{summary['completed_cells']} / {summary['total_cells']}`",
        f"- successful cells: `{summary['successful_cells']}`",
        f"- error cells: `{summary['error_cells']}`",
        f"- Stage 3.5 selected cells: `{summary['stage35_selected_cells']}`",
        f"- selected positive vs start: `{summary['selected_positive_vs_start']}`",
        f"- selected negative vs start: `{summary['selected_negative_vs_start']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.3f}`",
    ]
    return "\n".join(lines).rstrip() + "\n"


def run_harvest() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    queue = build_queue()
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
    first_cell_elapsed: float | None = None
    for cell_index, item in enumerate(queue, start=1):
        elapsed_total = float(time.perf_counter() - started)
        if elapsed_total >= MAX_WALLCLOCK_SECONDS:
            status = "wallclock_budget_reached"
            break
        cell_slug = _safe_slug(
            f"cell_{cell_index:04d}_seed{item['fixture_seed']}_search{item['search_seed']}_rank{item['candidate_rank']}_{item['candidate_hash']}"
        )
        cell_dir = output_dir / cell_slug
        case = resume_mod.load_artifact_case(artifact_path=Path(item["artifact_path"]))
        cell_started = time.perf_counter()
        try:
            payload = resume_mod.run_stage35_from_selected_trial_row(
                case,
                selected_row=dict(item["selected_row"]),
                stage35_cfg_override=STAGE35_CFG_OVERRIDE,
                output_dir=cell_dir,
            )
            resume_mod.write_resume_bundle(payload, output_dir=cell_dir)
            cell_elapsed = float(time.perf_counter() - cell_started)
            rows.append(
                build_result_row(
                    output_dir=output_dir,
                    cell_dir=cell_dir,
                    queue_item=item,
                    payload=payload,
                    elapsed_seconds=cell_elapsed,
                )
            )
        except Exception as exc:  # noqa: BLE001 - long harvest must be extractable.
            cell_elapsed = float(time.perf_counter() - cell_started)
            errors.append(
                {
                    "cell_index": cell_index,
                    "artifact_relpath": _repo_rel(Path(item["artifact_path"])),
                    "candidate_hash": str(item["candidate_hash"]),
                    "fixture_seed": int(item["fixture_seed"]),
                    "search_seed": int(item["search_seed"]),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "elapsed_seconds": cell_elapsed,
                }
            )
        completed_cells = cell_index
        if first_cell_elapsed is None:
            first_cell_elapsed = cell_elapsed
            projected = float(first_cell_elapsed * total_cells)
            print(
                json.dumps(
                    {
                        "event": "first_cell_projection",
                        "first_cell_elapsed_seconds": round(first_cell_elapsed, 3),
                        "projected_serial_seconds": round(projected, 3),
                        "budget_seconds": MAX_WALLCLOCK_SECONDS,
                        "utc": _utc_now_text(),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            if (
                STOP_IF_FIRST_CELL_PROJECTS_OVER_BUDGET
                and projected > float(MAX_WALLCLOCK_SECONDS)
            ):
                status = "stopped_after_first_cell_projection_over_budget"
                write_outputs(
                    output_dir=output_dir,
                    rows=rows,
                    errors=errors,
                    completed_cells=completed_cells,
                    total_cells=total_cells,
                    status=status,
                    started=started,
                )
                break

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
        rate = float(completed_cells / elapsed_total) if elapsed_total > 0 else 0.0
        remaining = max(total_cells - completed_cells, 0)
        eta_seconds = float(remaining / rate) if rate > 0 else 0.0
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
                    "eta_seconds": round(eta_seconds, 3),
                    "utc": _utc_now_text(),
                },
                sort_keys=True,
            ),
            flush=True,
        )

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
        (output_dir / "stage35_guard_selector_frontier_runtime_summary.json").read_text(
            encoding="utf-8"
        )
    )
    print(json.dumps(dict(summary, event="finish"), sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_harvest()


if __name__ == "__main__":
    main()
