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
        "Could not locate repo root from run_stage35_rank6_local_rescue_canary_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


RUN_LABEL = "stage35_rank6_local_rescue_canary_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
JOIN_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/"
    "stage35_guard_selector_frontier_deepening_join_rows.csv"
)
MAX_WALLCLOCK_SECONDS = 2700
PER_CELL_MAX_RUNTIME_SECONDS = 600
STOP_IF_FIRST_EXECUTED_CELL_PROJECTS_OVER_BUDGET = True
SELECTED_START_GATE = 0.437
SHALLOW_DELTA_GATE = 0.400

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

CANARY_CELLS: list[dict[str, Any]] = [
    {
        "cell_label": "cell_a_hard_gate_keep",
        "fixture_seed": 1511,
        "search_seed": 7004,
        "candidate_rank": 6,
        "candidate_hash": "51b7dab086e94186",
        "expected_policy_decision": "keep",
        "purpose": "hard_gate_keep_near_threshold",
    },
    {
        "cell_label": "cell_b_shallow_delta_keep",
        "fixture_seed": 1111,
        "search_seed": 7002,
        "candidate_rank": 6,
        "candidate_hash": "74dfe3cb559629f7",
        "expected_policy_decision": "keep",
        "purpose": "shallow_delta_keep_largest_recovered_positive",
    },
    {
        "cell_label": "cell_c_observed_regression_reject",
        "fixture_seed": 1111,
        "search_seed": 7004,
        "candidate_rank": 6,
        "candidate_hash": "511a29668b8c44d1",
        "expected_policy_decision": "reject",
        "purpose": "observed_deepening_regression_reject",
    },
    {
        "cell_label": "cell_d_rejected_positive_audit",
        "fixture_seed": 1411,
        "search_seed": 7005,
        "candidate_rank": 6,
        "candidate_hash": "b47e22bc63e7c189",
        "expected_policy_decision": "reject",
        "purpose": "rejected_positive_opportunity_cost_audit",
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


def _read_join_rows() -> dict[tuple[int, int, int, str], dict[str, Any]]:
    path = REPO_ROOT / JOIN_ROWS_REL
    rows: dict[tuple[int, int, int, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            key = (
                _safe_int(raw.get("fixture_seed")),
                _safe_int(raw.get("search_seed")),
                _safe_int(raw.get("candidate_rank")),
                str(raw.get("candidate_hash", "") or ""),
            )
            rows[key] = dict(raw)
    return rows


def policy_decision(row: Mapping[str, Any]) -> str:
    if _safe_int(row.get("candidate_rank")) != 6:
        return "reject"
    if _safe_float(row.get("selected_start_match_ratio")) >= SELECTED_START_GATE:
        return "keep"
    if _safe_float(row.get("shallow_minus_selected")) >= SHALLOW_DELTA_GATE:
        return "keep"
    return "reject"


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


def build_skip_row(
    *,
    output_dir: Path,
    source_row: Mapping[str, Any],
    cell_cfg: Mapping[str, Any],
    cell_index: int,
    decision: str,
    elapsed_seconds: float,
) -> dict[str, Any]:
    return {
        "run_label": RUN_LABEL,
        "output_dir": _repo_rel(output_dir),
        "cell_output_dir": "",
        "cell_index": cell_index,
        "cell_label": str(cell_cfg["cell_label"]),
        "purpose": str(cell_cfg["purpose"]),
        "policy_decision": decision,
        "expected_policy_decision": str(cell_cfg["expected_policy_decision"]),
        "policy_decision_matches_expected": int(
            decision == str(cell_cfg["expected_policy_decision"])
        ),
        "cell_execution_status": "policy_skip",
        "artifact_relpath": str(source_row.get("artifact_relpath", "") or ""),
        "fixture_seed": _safe_int(source_row.get("fixture_seed")),
        "search_seed": _safe_int(source_row.get("search_seed")),
        "candidate_rank": _safe_int(source_row.get("candidate_rank")),
        "candidate_hash": str(source_row.get("candidate_hash", "") or ""),
        "retained_best_match_ratio": _safe_float(
            source_row.get("retained_best_match_ratio")
        ),
        "selected_start_match_ratio": _safe_float(
            source_row.get("selected_start_match_ratio")
        ),
        "shallow_resume_best_match_ratio": _safe_float(
            source_row.get("shallow_resume_best_match_ratio")
        ),
        "prior_deep_resume_best_match_ratio": _safe_float(
            source_row.get("deep_resume_best_match_ratio")
        ),
        "canary_resume_best_match_ratio": "",
        "shallow_minus_selected": _safe_float(source_row.get("shallow_minus_selected")),
        "prior_deep_minus_shallow": _safe_float(source_row.get("deep_minus_shallow")),
        "canary_minus_shallow": "",
        "canary_minus_prior_deep": "",
        "canary_minus_selected": "",
        "stage35_selected": 0,
        "stage35_accept_reason": "",
        "stage35_selected_archive_rank": 0,
        "stage35_evals": 0,
        "elapsed_seconds": float(elapsed_seconds),
    }


def build_executed_row(
    *,
    output_dir: Path,
    cell_dir: Path,
    source_row: Mapping[str, Any],
    cell_cfg: Mapping[str, Any],
    cell_index: int,
    decision: str,
    payload: Mapping[str, Any],
    elapsed_seconds: float,
) -> dict[str, Any]:
    stage35 = dict(payload.get("stage35", {}) or {})
    selected_start = _safe_float(payload.get("selected_candidate_final_match"))
    resume = _safe_float(payload.get("resume_best_match_ratio"))
    shallow = _safe_float(source_row.get("shallow_resume_best_match_ratio"))
    prior_deep = _safe_float(source_row.get("deep_resume_best_match_ratio"))
    return {
        "run_label": RUN_LABEL,
        "output_dir": _repo_rel(output_dir),
        "cell_output_dir": _repo_rel(cell_dir),
        "cell_index": cell_index,
        "cell_label": str(cell_cfg["cell_label"]),
        "purpose": str(cell_cfg["purpose"]),
        "policy_decision": decision,
        "expected_policy_decision": str(cell_cfg["expected_policy_decision"]),
        "policy_decision_matches_expected": int(
            decision == str(cell_cfg["expected_policy_decision"])
        ),
        "cell_execution_status": "executed",
        "artifact_relpath": str(source_row.get("artifact_relpath", "") or ""),
        "fixture_seed": _safe_int(source_row.get("fixture_seed")),
        "search_seed": _safe_int(source_row.get("search_seed")),
        "candidate_rank": _safe_int(source_row.get("candidate_rank")),
        "candidate_hash": str(source_row.get("candidate_hash", "") or ""),
        "retained_best_match_ratio": _safe_float(
            source_row.get("retained_best_match_ratio")
        ),
        "selected_start_match_ratio": selected_start,
        "shallow_resume_best_match_ratio": shallow,
        "prior_deep_resume_best_match_ratio": prior_deep,
        "canary_resume_best_match_ratio": resume,
        "shallow_minus_selected": _safe_float(source_row.get("shallow_minus_selected")),
        "prior_deep_minus_shallow": _safe_float(source_row.get("deep_minus_shallow")),
        "canary_minus_shallow": resume - shallow,
        "canary_minus_prior_deep": resume - prior_deep,
        "canary_minus_selected": resume - selected_start,
        "stage35_selected": _safe_int(stage35.get("selected")),
        "stage35_accept_reason": str(stage35.get("accept_reason", "") or ""),
        "stage35_selected_archive_rank": _safe_int(
            stage35.get("selected_archive_rank")
        ),
        "stage35_evals": _safe_int(stage35.get("evals")),
        "elapsed_seconds": float(elapsed_seconds),
    }


def build_readout(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Stage35 Rank6 Local-Rescue Canary v1",
        "",
        "Question:",
        "",
        "- does the softened rank-6 local-rescue policy execute the two expected",
        "  keep cells safely while rejecting the known regression and recording",
        "  rejected-positive opportunity cost?",
        "",
        "Coverage:",
        "",
        f"- status: `{summary['status']}`",
        f"- completed cells: `{summary['completed_cells']} / {summary['total_cells']}`",
        f"- executed cells: `{summary['executed_cells']}`",
        f"- skipped cells: `{summary['skipped_cells']}`",
        f"- error cells: `{summary['error_cells']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.3f}`",
        "",
        "Result:",
        "",
        f"- policy decision mismatches: `{summary['policy_decision_mismatches']}`",
        f"- executed cells nonnegative vs shallow: `{summary['executed_nonnegative_vs_shallow']}`",
        f"- executed cells regressed vs shallow: `{summary['executed_regressed_vs_shallow']}`",
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
    _write_csv(output_dir / "stage35_rank6_local_rescue_canary_rows.csv", rows)
    _write_csv(output_dir / "stage35_rank6_local_rescue_canary_errors.csv", errors)
    executed = [row for row in rows if row["cell_execution_status"] == "executed"]
    skipped = [row for row in rows if row["cell_execution_status"] == "policy_skip"]
    summary = {
        "run_label": RUN_LABEL,
        "status": status,
        "output_dir": _repo_rel(output_dir),
        "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
        "per_cell_max_runtime_seconds": PER_CELL_MAX_RUNTIME_SECONDS,
        "selected_start_gate": SELECTED_START_GATE,
        "shallow_delta_gate": SHALLOW_DELTA_GATE,
        "completed_cells": completed_cells,
        "total_cells": total_cells,
        "executed_cells": len(executed),
        "skipped_cells": len(skipped),
        "error_cells": len(errors),
        "policy_decision_mismatches": sum(
            1 for row in rows if int(row["policy_decision_matches_expected"]) != 1
        ),
        "executed_nonnegative_vs_shallow": sum(
            1 for row in executed if float(row["canary_minus_shallow"]) >= 0.0
        ),
        "executed_regressed_vs_shallow": sum(
            1 for row in executed if float(row["canary_minus_shallow"]) < 0.0
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
        "updated_utc": _utc_now_text(),
        "recommended_next": "analyze_canary_then_compare_against_prediction_ledger",
    }
    _write_json(output_dir / "stage35_rank6_local_rescue_canary_summary.json", summary)
    (output_dir / "stage35_rank6_local_rescue_canary_readout.md").write_text(
        build_readout(summary),
        encoding="utf-8",
    )


def run_canary() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    join_rows = _read_join_rows()
    total_cells = len(CANARY_CELLS)
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    completed_cells = 0
    status = "completed"
    executed_elapsed: list[float] = []
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
    for cell_index, cell_cfg in enumerate(CANARY_CELLS, start=1):
        if float(time.perf_counter() - started) >= MAX_WALLCLOCK_SECONDS:
            status = "wallclock_budget_reached"
            break
        key = (
            _safe_int(cell_cfg["fixture_seed"]),
            _safe_int(cell_cfg["search_seed"]),
            _safe_int(cell_cfg["candidate_rank"]),
            str(cell_cfg["candidate_hash"]),
        )
        source_row = join_rows[key]
        decision = policy_decision(source_row)
        cell_started = time.perf_counter()
        try:
            if decision == "keep":
                artifact_path = REPO_ROOT / str(source_row.get("artifact_relpath", "") or "")
                candidate_hash = str(source_row.get("candidate_hash", "") or "")
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
                executed_elapsed.append(cell_elapsed)
                rows.append(
                    build_executed_row(
                        output_dir=output_dir,
                        cell_dir=cell_dir,
                        source_row=source_row,
                        cell_cfg=cell_cfg,
                        cell_index=cell_index,
                        decision=decision,
                        payload=payload,
                        elapsed_seconds=cell_elapsed,
                    )
                )
                if len(executed_elapsed) == 1:
                    projected = cell_elapsed * sum(
                        1
                        for cfg in CANARY_CELLS
                        if str(cfg["expected_policy_decision"]) == "keep"
                    )
                    print(
                        json.dumps(
                            {
                                "event": "first_executed_cell_projection",
                                "first_executed_cell_elapsed_seconds": round(
                                    cell_elapsed,
                                    3,
                                ),
                                "projected_executed_seconds": round(projected, 3),
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
                        status = "stopped_after_first_executed_cell_projection_over_budget"
            else:
                cell_elapsed = float(time.perf_counter() - cell_started)
                rows.append(
                    build_skip_row(
                        output_dir=output_dir,
                        source_row=source_row,
                        cell_cfg=cell_cfg,
                        cell_index=cell_index,
                        decision=decision,
                        elapsed_seconds=cell_elapsed,
                    )
                )
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
                    "successful_rows": len(rows),
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
        if status == "stopped_after_first_executed_cell_projection_over_budget":
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
        (output_dir / "stage35_rank6_local_rescue_canary_summary.json").read_text(
            encoding="utf-8",
        )
    )
    print(json.dumps(dict(summary, event="finish"), sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_canary()


if __name__ == "__main__":
    main()
