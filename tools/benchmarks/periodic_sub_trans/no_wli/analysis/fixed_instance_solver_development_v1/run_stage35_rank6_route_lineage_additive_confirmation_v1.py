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
        "run_stage35_rank6_route_lineage_additive_confirmation_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


RUN_LABEL = "stage35_rank6_route_lineage_additive_confirmation_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
CONFIRMATION_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260430T151237Z__stage35_rank6_route_lineage_confirmation_prep_v1/"
    "stage35_rank6_route_lineage_confirmation_prep_rows.csv"
)
FRONTIER_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/"
    "stage35_guard_selector_frontier_runtime_rows.csv"
)
DEEP_JOIN_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/"
    "stage35_guard_selector_frontier_deepening_join_rows.csv"
)
DESIGN_NOTE_REL = Path(
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_stage35_rank6_route_lineage_additive_confirmation_design_2026-04-30.md"
)

MAX_WALLCLOCK_SECONDS = 2700
PER_CELL_MAX_RUNTIME_SECONDS = 600
STOP_IF_FIRST_EXECUTED_CELL_PROJECTS_OVER_BUDGET = True
ROUTE_NOVELTY_GATE = 173.5

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

CONFIRMATION_CELLS: list[dict[str, Any]] = [
    {
        "cell_label": "group_a_reproduction_611_7003",
        "fixture_seed": 611,
        "search_seed": 7003,
        "candidate_rank": 6,
        "candidate_hash": "826e5c871f444486",
        "purpose": "prior_deep_positive_reproduction",
        "expected_route_additive_decision": "keep",
    },
    {
        "cell_label": "group_a_safety_check_1111_7001",
        "fixture_seed": 1111,
        "search_seed": 7001,
        "candidate_rank": 6,
        "candidate_hash": "d94845511e181f7c",
        "purpose": "key_new_safety_check_shallow_negative",
        "expected_route_additive_decision": "keep",
    },
    {
        "cell_label": "group_a_reproduction_1411_7004",
        "fixture_seed": 1411,
        "search_seed": 7004,
        "candidate_rank": 6,
        "candidate_hash": "2632e79517bf1c7c",
        "purpose": "prior_deep_positive_boundary_reproduction",
        "expected_route_additive_decision": "keep",
    },
    {
        "cell_label": "group_a_reproduction_1411_7005",
        "fixture_seed": 1411,
        "search_seed": 7005,
        "candidate_rank": 6,
        "candidate_hash": "b47e22bc63e7c189",
        "purpose": "prior_deep_positive_boundary_reproduction",
        "expected_route_additive_decision": "keep",
    },
]


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


def _row_key(row: Mapping[str, Any]) -> tuple[int, int, int, str]:
    return (
        _safe_int(row.get("fixture_seed")),
        _safe_int(row.get("search_seed")),
        _safe_int(row.get("candidate_rank")),
        str(row.get("candidate_hash", "") or ""),
    )


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


def _read_csv_rows(rel_path: Path) -> list[dict[str, Any]]:
    path = REPO_ROOT / rel_path
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _read_first_by_key(rel_path: Path) -> dict[tuple[int, int, int, str], dict[str, Any]]:
    rows: dict[tuple[int, int, int, str], dict[str, Any]] = {}
    for row in _read_csv_rows(rel_path):
        rows.setdefault(_row_key(row), dict(row))
    return rows


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
        if candidate_hash in hashes:
            row["selector"] = "score_plus_novelty"
            return row
    raise ValueError(f"Candidate hash not found in frontier rows: {candidate_hash}")


def route_additive_decision(prep_row: Mapping[str, Any]) -> str:
    old_keep = _safe_int(prep_row.get("old_softened_keep")) == 1
    route_keep = (
        str(prep_row.get("candidate_source", "") or "") == "phaseA_selected"
        and _safe_int(prep_row.get("candidate_source_rank")) == 1
        and _safe_float(prep_row.get("candidate_novelty_distance_to_anchor"))
        >= ROUTE_NOVELTY_GATE
    )
    return "keep" if old_keep or route_keep else "reject"


def build_result_row(
    *,
    output_dir: Path,
    cell_dir: Path,
    cell_cfg: Mapping[str, Any],
    cell_index: int,
    prep_row: Mapping[str, Any],
    frontier_row: Mapping[str, Any],
    deep_row: Mapping[str, Any] | None,
    decision: str,
    payload: Mapping[str, Any],
    elapsed_seconds: float,
) -> dict[str, Any]:
    stage35 = dict(payload.get("stage35", {}) or {})
    selected_start = _safe_float(payload.get("selected_candidate_final_match"))
    shallow = _safe_float(frontier_row.get("resume_best_match_ratio"))
    prior_deep = (
        _safe_float(deep_row.get("deep_resume_best_match_ratio"))
        if deep_row is not None
        else ""
    )
    resume = _safe_float(payload.get("resume_best_match_ratio"))
    prior_deep_delta = (
        ""
        if prior_deep == ""
        else resume - float(prior_deep)
    )
    return {
        "run_label": RUN_LABEL,
        "output_dir": _repo_rel(output_dir),
        "cell_output_dir": _repo_rel(cell_dir),
        "cell_index": cell_index,
        "cell_label": str(cell_cfg["cell_label"]),
        "purpose": str(cell_cfg["purpose"]),
        "route_additive_decision": decision,
        "expected_route_additive_decision": str(
            cell_cfg["expected_route_additive_decision"]
        ),
        "decision_matches_expected": int(
            decision == str(cell_cfg["expected_route_additive_decision"])
        ),
        "confirmation_group": str(prep_row.get("confirmation_group", "") or ""),
        "old_softened_keep": _safe_int(prep_row.get("old_softened_keep")),
        "route_lineage_keep": _safe_int(prep_row.get("route_lineage_keep")),
        "candidate_source": str(prep_row.get("candidate_source", "") or ""),
        "candidate_source_rank": _safe_int(prep_row.get("candidate_source_rank")),
        "candidate_novelty_distance_to_anchor": _safe_float(
            prep_row.get("candidate_novelty_distance_to_anchor")
        ),
        "artifact_relpath": str(frontier_row.get("artifact_relpath", "") or ""),
        "fixture_seed": _safe_int(frontier_row.get("fixture_seed")),
        "search_seed": _safe_int(frontier_row.get("search_seed")),
        "candidate_rank": _safe_int(frontier_row.get("candidate_rank")),
        "candidate_hash": str(frontier_row.get("candidate_hash", "") or ""),
        "retained_best_match_ratio": _safe_float(
            frontier_row.get("retained_best_match_ratio")
        ),
        "selected_start_match_ratio": selected_start,
        "shallow_resume_best_match_ratio": shallow,
        "prior_deep_resume_best_match_ratio": prior_deep,
        "confirmation_resume_best_match_ratio": resume,
        "shallow_minus_selected": _safe_float(
            frontier_row.get("resume_minus_selected")
        ),
        "confirmation_minus_shallow": resume - shallow,
        "confirmation_minus_prior_deep": prior_deep_delta,
        "confirmation_minus_selected": resume - selected_start,
        "stage35_selected": _safe_int(stage35.get("selected")),
        "stage35_accept_reason": str(stage35.get("accept_reason", "") or ""),
        "stage35_selected_archive_rank": _safe_int(
            stage35.get("selected_archive_rank")
        ),
        "stage35_selected_via_guard_passing_selector": _safe_int(
            stage35.get("selected_via_guard_passing_selector")
        ),
        "stage35_evals": _safe_int(stage35.get("evals")),
        "elapsed_seconds": float(elapsed_seconds),
    }


def build_readout(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Stage35 Rank6 Route-Lineage Additive Confirmation v1",
        "",
        "Question:",
        "",
        "- can route-lineage be used as an additive rescue rule for old-rejected",
        "  rank-6 rows without adding a confirmed regression?",
        "",
        "Coverage:",
        "",
        f"- status: `{summary['status']}`",
        f"- completed cells: `{summary['completed_cells']} / {summary['total_cells']}`",
        f"- successful cells: `{summary['successful_cells']}`",
        f"- error cells: `{summary['error_cells']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.3f}`",
        "",
        "Result:",
        "",
        f"- decision mismatches: `{summary['decision_mismatches']}`",
        f"- nonnegative versus shallow: `{summary['nonnegative_vs_shallow']}`",
        f"- regressed versus shallow: `{summary['regressed_vs_shallow']}`",
        f"- key safety cell nonnegative: `{summary['key_safety_cell_nonnegative']}`",
        "",
        "Recommendation:",
        "",
        f"- `{summary['recommended_next']}`",
    ]
    return "\n".join(lines).rstrip() + "\n"


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
    _write_csv(
        output_dir / "stage35_rank6_route_lineage_additive_confirmation_rows.csv",
        rows,
    )
    _write_csv(
        output_dir / "stage35_rank6_route_lineage_additive_confirmation_errors.csv",
        errors,
    )
    key_rows = [
        row for row in rows if row["cell_label"] == "group_a_safety_check_1111_7001"
    ]
    key_nonnegative = (
        int(float(key_rows[0]["confirmation_minus_shallow"]) >= 0.0)
        if key_rows
        else 0
    )
    summary = {
        "run_label": RUN_LABEL,
        "status": status,
        "output_dir": _repo_rel(output_dir),
        "design_note": _repo_rel(REPO_ROOT / DESIGN_NOTE_REL),
        "confirmation_rows_path": _repo_rel(REPO_ROOT / CONFIRMATION_ROWS_REL),
        "frontier_rows_path": _repo_rel(REPO_ROOT / FRONTIER_ROWS_REL),
        "deep_join_rows_path": _repo_rel(REPO_ROOT / DEEP_JOIN_ROWS_REL),
        "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
        "per_cell_max_runtime_seconds": PER_CELL_MAX_RUNTIME_SECONDS,
        "route_novelty_gate": ROUTE_NOVELTY_GATE,
        "completed_cells": completed_cells,
        "total_cells": total_cells,
        "successful_cells": len(rows),
        "error_cells": len(errors),
        "decision_mismatches": sum(
            1 for row in rows if int(row["decision_matches_expected"]) != 1
        ),
        "nonnegative_vs_shallow": sum(
            1 for row in rows if float(row["confirmation_minus_shallow"]) >= 0.0
        ),
        "regressed_vs_shallow": sum(
            1 for row in rows if float(row["confirmation_minus_shallow"]) < 0.0
        ),
        "key_safety_cell_nonnegative": key_nonnegative,
        "group_b_replacement_warning": (
            "strict_route_lineage_is_not_a_replacement_because_group_B_contains_"
            "old_keep_route_reject_rows_with_existing_positive_evidence"
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
        "updated_utc": _utc_now_text(),
        "recommended_next": (
            "analyze_confirmation_before_any_wider_union_policy_runtime"
        ),
    }
    _write_json(
        output_dir / "stage35_rank6_route_lineage_additive_confirmation_summary.json",
        summary,
    )
    (
        output_dir / "stage35_rank6_route_lineage_additive_confirmation_readout.md"
    ).write_text(build_readout(summary), encoding="utf-8")


def run_confirmation() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    prep_rows = _read_first_by_key(CONFIRMATION_ROWS_REL)
    frontier_rows = _read_first_by_key(FRONTIER_ROWS_REL)
    deep_rows = _read_first_by_key(DEEP_JOIN_ROWS_REL)
    total_cells = len(CONFIRMATION_CELLS)
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    completed_cells = 0
    status = "completed"
    first_elapsed: float | None = None
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
    for cell_index, cell_cfg in enumerate(CONFIRMATION_CELLS, start=1):
        if float(time.perf_counter() - started) >= MAX_WALLCLOCK_SECONDS:
            status = "wallclock_budget_reached"
            break
        key = _row_key(cell_cfg)
        prep_row = prep_rows[key]
        frontier_row = frontier_rows[key]
        deep_row = deep_rows.get(key)
        decision = route_additive_decision(prep_row)
        cell_started = time.perf_counter()
        try:
            if decision != "keep":
                raise ValueError(f"Unexpected route-additive decision: {decision}")
            artifact_path = REPO_ROOT / str(frontier_row.get("artifact_relpath", "") or "")
            candidate_hash = str(frontier_row.get("candidate_hash", "") or "")
            case = resume_mod.load_artifact_case(artifact_path=artifact_path)
            selected_row = load_selected_row(
                artifact_path=artifact_path,
                candidate_hash=candidate_hash,
            )
            cell_dir = output_dir / _safe_slug(
                f"cell_{cell_index:04d}_{cell_cfg['cell_label']}_{cell_cfg['fixture_seed']}_{cell_cfg['search_seed']}_{candidate_hash}"
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
                build_result_row(
                    output_dir=output_dir,
                    cell_dir=cell_dir,
                    cell_cfg=cell_cfg,
                    cell_index=cell_index,
                    prep_row=prep_row,
                    frontier_row=frontier_row,
                    deep_row=deep_row,
                    decision=decision,
                    payload=payload,
                    elapsed_seconds=cell_elapsed,
                )
            )
            if first_elapsed is None:
                first_elapsed = cell_elapsed
                projected = cell_elapsed * total_cells
                print(
                    json.dumps(
                        {
                            "event": "first_cell_projection",
                            "first_cell_elapsed_seconds": round(cell_elapsed, 3),
                            "projected_serial_seconds": round(projected, 3),
                            "budget_seconds": MAX_WALLCLOCK_SECONDS,
                            "utc": _utc_now_text(),
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
                if (
                    STOP_IF_FIRST_EXECUTED_CELL_PROJECTS_OVER_BUDGET
                    and projected > MAX_WALLCLOCK_SECONDS
                ):
                    status = "stopped_after_first_cell_projection_over_budget"
        except Exception as exc:  # noqa: BLE001
            cell_elapsed = float(time.perf_counter() - cell_started)
            errors.append(
                {
                    "cell_index": cell_index,
                    "cell_label": str(cell_cfg["cell_label"]),
                    "fixture_seed": int(cell_cfg["fixture_seed"]),
                    "search_seed": int(cell_cfg["search_seed"]),
                    "candidate_rank": int(cell_cfg["candidate_rank"]),
                    "candidate_hash": str(cell_cfg["candidate_hash"]),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "elapsed_seconds": cell_elapsed,
                }
            )
        completed_cells = cell_index
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
            output_dir
            / "stage35_rank6_route_lineage_additive_confirmation_summary.json"
        ).read_text(encoding="utf-8")
    )
    print(json.dumps(dict(summary, event="finish"), sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_confirmation()


if __name__ == "__main__":
    main()
