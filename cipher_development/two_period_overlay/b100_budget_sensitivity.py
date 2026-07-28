from __future__ import annotations

"""Post-hoc B100 scout-budget sensitivity and B1000 progression gate.

This diagnostic reads only a completed B100 run.  It does not alter or rerun
search.  Controlled-branch identity is opened only in this terminal diagnostic
and is used to decide whether a separately frozen compressed B1000 run is
scientifically and computationally justified.
"""

import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cipher_development.two_period_overlay.experiment_b import (
    B100_EXPERIMENT_ID,
    B1000_GLOBAL_SCOUT_CAPACITY,
    B1000_STARTS_PER_BRANCH,
)
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.staged_handoff import latest_completed_experiment

EXPERIMENT_ID = "b100_scout_budget_sensitivity_v1"
BLOCK_SIZES = (1, 2, 4, 8, 16, 32, 80, 160)
CAPACITIES = (40, 100, 200, 400)
FROZEN_BLOCK_SIZE = 8
FROZEN_SURVIVAL_CAPACITY = 200
MIN_SCORE_MARGIN = 0.05
PROJECTION_SAFETY_FACTOR = 1.10
OVERNIGHT_SECONDS = 8.0 * 60.0 * 60.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _numeric_summary(values: Sequence[float | int]) -> dict[str, float]:
    data = [float(value) for value in values]
    if not data or any(not math.isfinite(value) for value in data):
        raise ValueError("summary values must be finite and non-empty")
    ordered = sorted(data)
    def quantile(fraction: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * fraction
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight
    return {
        "minimum": min(data),
        "q25": quantile(0.25),
        "median": statistics.median(data),
        "q75": quantile(0.75),
        "maximum": max(data),
        "mean": statistics.fmean(data),
    }


def analyse_disjoint_blocks(
    attempts_by_branch: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    controlled_branch_id: str,
    block_size: int,
    capacities: Sequence[int] = CAPACITIES,
) -> dict[str, Any]:
    if block_size <= 0 or 160 % block_size != 0:
        raise ValueError("block_size must be a positive divisor of 160")
    if controlled_branch_id not in attempts_by_branch:
        raise ValueError("controlled branch is absent from attempts")
    branch_ids = tuple(sorted(attempts_by_branch))
    rows: list[dict[str, Any]] = []
    for start in range(0, 160, block_size):
        stop = start + block_size
        best: dict[str, float] = {}
        candidates: list[tuple[float, str, str]] = []
        for branch_id in branch_ids:
            subset = [
                row for row in attempts_by_branch[branch_id]
                if start <= int(row["input_index"]) < stop
            ]
            if len(subset) != block_size:
                raise ValueError(
                    f"branch {branch_id} does not contain the complete {start}:{stop} block"
                )
            best[branch_id] = max(float(row["final_score"]) for row in subset)
            candidates.extend(
                (float(row["final_score"]), branch_id, str(row["candidate_id"]))
                for row in subset
            )
        ranking = sorted(best, key=lambda branch_id: (-best[branch_id], branch_id))
        rank = ranking.index(controlled_branch_id) + 1
        second_best = max(
            score for branch_id, score in best.items()
            if branch_id != controlled_branch_id
        )
        row: dict[str, Any] = {
            "block_start": start,
            "block_stop": stop,
            "controlled_branch_rank": rank,
            "controlled_branch_best_score": best[controlled_branch_id],
            "best_false_branch_score": second_best,
            "score_margin": best[controlled_branch_id] - second_best,
            "capacities": {},
        }
        ordered_candidates = sorted(candidates, key=lambda item: (-item[0], item[1], item[2]))
        for capacity in capacities:
            selected = ordered_candidates[: min(int(capacity), len(ordered_candidates))]
            selected_branches = {item[1] for item in selected}
            row["capacities"][str(capacity)] = {
                "controlled_branch_survived": controlled_branch_id in selected_branches,
                "selected_branch_count": len(selected_branches),
            }
        rows.append(row)
    return {
        "block_size": block_size,
        "block_count": len(rows),
        "controlled_rank_summary": _numeric_summary(
            [row["controlled_branch_rank"] for row in rows]
        ),
        "score_margin_summary": _numeric_summary([row["score_margin"] for row in rows]),
        "top_1_block_count": sum(row["controlled_branch_rank"] == 1 for row in rows),
        "top_3_block_count": sum(row["controlled_branch_rank"] <= 3 for row in rows),
        "survival_counts": {
            str(capacity): sum(
                row["capacities"][str(capacity)]["controlled_branch_survived"]
                for row in rows
            )
            for capacity in capacities
        },
        "rows": rows,
    }


def _runtime_projection(
    *,
    source_scientific_elapsed_s: float,
    source_search_rows: Sequence[Mapping[str, Any]],
    source_selected_branch_count: int,
) -> dict[str, Any]:
    scout_elapsed = sum(
        float(row.get("elapsed_s", 0.0))
        for row in source_search_rows
        if row.get("stage") == "scout"
    )
    continuation_elapsed = sum(
        float(row.get("elapsed_s", 0.0)) + float(row.get("rescore_elapsed_s", 0.0))
        for row in source_search_rows
        if row.get("stage") in {"bridge", "judge", "final_union"}
    )
    if source_selected_branch_count <= 0:
        raise ValueError("source selected-branch count must be positive")
    continuation_per_branch = continuation_elapsed / source_selected_branch_count
    source_overhead = max(0.0, source_scientific_elapsed_s - scout_elapsed - continuation_elapsed)
    projected_scout = scout_elapsed * (
        B1000_STARTS_PER_BRANCH / 160.0
    ) * (1000.0 / 100.0)
    projected_continuation_upper = (
        continuation_per_branch * B1000_GLOBAL_SCOUT_CAPACITY
    )
    projected_overhead = max(600.0, source_overhead * 10.0)
    central = projected_scout + projected_continuation_upper + projected_overhead
    safety = central * PROJECTION_SAFETY_FACTOR
    return {
        "schema": "rdp.two_period_overlay.b1000_runtime_projection.v1",
        "basis": "measured B100 scout scaling plus a conservative 400-branch continuation upper bound",
        "source_list_size": 100,
        "target_list_size": 1000,
        "target_starts_per_branch": B1000_STARTS_PER_BRANCH,
        "target_global_scout_capacity": B1000_GLOBAL_SCOUT_CAPACITY,
        "projected_scout_elapsed_s": projected_scout,
        "continuation_elapsed_per_selected_branch_s": continuation_per_branch,
        "projected_continuation_upper_elapsed_s": projected_continuation_upper,
        "projected_overhead_elapsed_s": projected_overhead,
        "central_elapsed_s": central,
        "safety_factor": PROJECTION_SAFETY_FACTOR,
        "safety_adjusted_elapsed_s": safety,
        "overnight_available_s": OVERNIGHT_SECONDS,
    }


def run_b100_budget_sensitivity(repo_root: Path) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    repo_root = repo_root.resolve()
    source_run = latest_completed_experiment(repo_root, B100_EXPERIMENT_ID)
    source_result_path = source_run / "artifacts/experiment_result.json"
    source_result = _read_json(source_result_path)
    source_summary = source_result.get("result_summary")
    source_summary = source_summary if isinstance(source_summary, Mapping) else {}
    if source_result.get("decision") != "promote" or source_summary.get("progression_gate_passed") is not True:
        raise RuntimeError("the latest B100 run has not passed its progression gate")

    terminal = _read_json(source_run / "artifacts/experiment_b/terminal_branch_evaluation.json")
    controlled_branch_id = str(terminal["controlled_branch_id"])
    candidate_list = _read_json(source_run / "artifacts/experiment_b/candidate_list.json")
    candidates = candidate_list.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 100:
        raise RuntimeError("source B100 candidate list is incomplete")
    branch_ids = [str(item["branch_id"]) for item in candidates]
    attempts_by_branch: dict[str, list[dict[str, Any]]] = {}
    for branch_id in branch_ids:
        attempts = _read_json(
            source_run / f"artifacts/experiment_b/branches/{branch_id}/scout/attempts.json"
        )
        rows = attempts.get("rows")
        if not isinstance(rows, list) or len(rows) != 160:
            raise RuntimeError(f"source B100 scout attempts are incomplete for {branch_id}")
        attempts_by_branch[branch_id] = [dict(row) for row in rows]

    search_summary = _read_json(source_run / "artifacts/experiment_b/search_summary.json")
    search_rows = search_summary.get("rows")
    if not isinstance(search_rows, list):
        raise RuntimeError("source B100 search summary is invalid")
    source_timing = _read_json(source_run / "artifacts/execution_timing.json")
    source_selection = _read_json(
        source_run / "artifacts/experiment_b/shared/scout_selection_summary.json"
    )

    started_at = _utc_now_iso()
    started = time.perf_counter()
    block_results = {
        str(block_size): analyse_disjoint_blocks(
            attempts_by_branch,
            controlled_branch_id=controlled_branch_id,
            block_size=block_size,
        )
        for block_size in BLOCK_SIZES
    }
    frozen = block_results[str(FROZEN_BLOCK_SIZE)]
    projection = _runtime_projection(
        source_scientific_elapsed_s=float(source_timing["scientific_work_elapsed_s"]),
        source_search_rows=[dict(row) for row in search_rows],
        source_selected_branch_count=int(source_selection["selected_branch_count"]),
    )
    gate_checks = {
        "source_b100_promoted": True,
        "source_b100_exact_solution_persisted": bool(terminal.get("exact_solution_persisted")),
        "all_8_start_blocks_top_3": int(frozen["top_3_block_count"]) == int(frozen["block_count"]),
        "all_8_start_blocks_survive_top_200": int(frozen["survival_counts"][str(FROZEN_SURVIVAL_CAPACITY)]) == int(frozen["block_count"]),
        "minimum_8_start_score_margin_met": float(frozen["score_margin_summary"]["minimum"]) >= MIN_SCORE_MARGIN,
        "b1000_safety_projection_within_8_hours": float(projection["safety_adjusted_elapsed_s"]) <= OVERNIGHT_SECONDS,
    }
    gate_passed = all(gate_checks.values())

    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id=EXPERIMENT_ID,
        benchmark_id="alice_308_p13_p17_candidate_words_b100_budget_sensitivity_d08",
        question="Can the completed B100 scout evidence justify a compressed eight-start B1000 overnight run without rerunning B100?",
        hypothesis="The controlled branch remains robustly separated under disjoint reduced-start blocks and a conservative B1000 projection fits eight hours.",
        alternative="Reduced scout budgets lose or weakly separate the controlled branch, or conservative B1000 scaling exceeds eight hours.",
        decision_rule="Authorise B1000 only when every disjoint eight-start block ranks the controlled branch in the top three, every block survives a top-200 candidate selection, the minimum score margin is at least 0.05, and the safety-adjusted projection fits eight hours.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(FailureMechanism.RANKING, FailureMechanism.BUDGET, FailureMechanism.EVIDENCE_REPRODUCIBILITY),
        budget_seconds=15.0 * 60.0,
        budget_evaluations=None,
        lesson_ids=("CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "source_experiment_id": B100_EXPERIMENT_ID,
        "source_run_id": source_run.name,
        "block_sizes": list(BLOCK_SIZES),
        "capacities": list(CAPACITIES),
        "frozen_b1000_starts_per_branch": B1000_STARTS_PER_BRANCH,
        "frozen_b1000_global_scout_capacity": B1000_GLOBAL_SCOUT_CAPACITY,
        "terminal_diagnostic_only": True,
        "normal_search_performed": False,
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            source_rel = Path("artifacts/b100_budget_sensitivity/source_b100_gate.json")
            summary_rel = Path("artifacts/b100_budget_sensitivity/summary.json")
            timing_rel = Path("artifacts/execution_timing.json")
            _write_json(run_dir / source_rel, {
                "schema": "rdp.two_period_overlay.source_b100_gate.v1",
                "experiment_id": B100_EXPERIMENT_ID,
                "run_id": source_run.name,
                "decision": source_result.get("decision"),
                "progression_gate_passed": source_summary.get("progression_gate_passed"),
                "candidate_count": 100,
                "terminal_payload_copied": False,
            })
            _write_json(run_dir / summary_rel, {
                "schema": "rdp.two_period_overlay.b100_budget_sensitivity.v1",
                "source_run_id": source_run.name,
                "controlled_branch_id": controlled_branch_id,
                "block_results": block_results,
                "runtime_projection": projection,
                "gate_checks": gate_checks,
                "b1000_gate_passed": gate_passed,
                "frozen_b1000_configuration": {
                    "starts_per_branch": B1000_STARTS_PER_BRANCH,
                    "global_scout_capacity": B1000_GLOBAL_SCOUT_CAPACITY,
                    "scout_sweeps": 5,
                    "bridge_sweeps": 4,
                    "judge_sweeps": 3,
                },
            })
            elapsed = time.perf_counter() - started
            _write_json(run_dir / timing_rel, {
                "schema": "rdp.two_period_overlay.b100_budget_sensitivity_timing.v1",
                "started_at_utc": started_at,
                "finished_at_utc": _utc_now_iso(),
                "scientific_work_elapsed_s": elapsed,
            })
            result_path = run.finish(
                decision=ExperimentDecision.PROMOTE if gate_passed else ExperimentDecision.REFINE,
                stop_reason="done",
                result_summary={
                    "artifact": summary_rel.as_posix(),
                    "source_run_id": source_run.name,
                    "b1000_gate_passed": gate_passed,
                    "runtime_projection": projection,
                    "timing": _read_json(run_dir / timing_rel),
                },
                reference_evaluation={
                    "controlled_branch_id": controlled_branch_id,
                    "gate_checks": gate_checks,
                    "b1000_gate_passed": gate_passed,
                },
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, original_error=exc)
        raise
    if run_dir is None or result_path is None:
        raise RuntimeError("B100 budget sensitivity did not create a result")
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


__all__ = [
    "BLOCK_SIZES",
    "CAPACITIES",
    "EXPERIMENT_ID",
    "analyse_disjoint_blocks",
    "run_b100_budget_sensitivity",
]
