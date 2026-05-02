from __future__ import annotations

import json
import math
import sys
from contextlib import contextmanager
from pathlib import Path
from time import monotonic
from typing import Any, Iterator, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (  # noqa: E402
    refresh_catalog_safely,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1 as action_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_both_action_microprobe_v1 as base_mod,
)


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1"
)
FILE_STEM = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch"
)
READOUT_TITLE = (
    "# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Best-Init Window Family Microbatch v1"
)
MECHANISM_LAYER = "selection"
SEARCH_SEEDS = (7002, 7003, 7004)
LANE_ROLE_BY_SEED = {
    7002: "filtered_family",
    7003: "kept_family",
    7004: "kept_family",
}
EXPECTED_GATE_VERDICT_BY_SEED = {
    7002: "filter",
    7003: "keep",
    7004: "keep",
}
INTENDED_WALLCLOCK_BUDGET_HOURS = 1.5
MAX_WALLCLOCK_SECONDS = INTENDED_WALLCLOCK_BUDGET_HOURS * 3600.0
NEXT_BRANCH_ADVANCE_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_full_family_synthesis"
)
NEXT_BRANCH_REFINE_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_refine"
)
QUESTION = (
    "Does the restart32 best-init action contract generalize across the "
    "remaining fixed 1111 family lanes: filtered 7002 and kept 7003/7004?"
)
SUSPICION = (
    "7002 should flip to filter at restart32, fall back to baseline, and save "
    "real wallclock, while 7003 and 7004 should flip to keep at restart32 and "
    "stay no-harm relative to their prior exact replays."
)
MAIN_ALTERNATIVE = (
    "At least one remaining lane may fail the restart32 best-init contract, or "
    "7002 may still save too little wallclock to justify carrying the rule "
    "forward."
)
IF_SUSPICION_TRUE_EXPECT = (
    "7002 should emit filter, apply fallback plus early stop, and land at the "
    "retained baseline materially faster than its prior exact replay; 7003 "
    "and 7004 should emit keep, apply no action, and reproduce their prior "
    "exact replay outcomes."
)
IF_ALTERNATIVE_TRUE_EXPECT = (
    "7002 may not save enough wallclock, or one of 7003/7004 may drift enough "
    "that the provisional contract is not yet family-stable."
)
DECISION_RULE = (
    "Advance only if all three remaining lanes match the expected keep/filter "
    "split at restart32, 7002 saves real wallclock, and 7003/7004 stay "
    "no-harm relative to their prior exact replays. Refine if correctness "
    "holds but 7002 saves only a small wallclock share. Hold if any remaining "
    "lane fails the current action contract."
)
STOP_CONDITION = (
    "This microbatch is budgeted from completed same-family exact replays: "
    "7002 took about 00:22:13, 7003 took about 00:21:54, and 7004 took about "
    "00:24:17, for an anchored total of about 01:08:25. After each completed "
    "lane, recompute the projected three-lane total from observed elapsed plus "
    "remaining anchors. Stop before launching the next lane if the projection "
    "exceeds 01:30:00."
)


@contextmanager
def _patched_base_module() -> Iterator[None]:
    original_search_seeds = tuple(base_mod.SEARCH_SEEDS)
    original_lane_role_by_seed = dict(base_mod.LANE_ROLE_BY_SEED)
    original_expected_gate_verdict_by_seed = dict(base_mod.EXPECTED_GATE_VERDICT_BY_SEED)
    try:
        base_mod.SEARCH_SEEDS = tuple(SEARCH_SEEDS)
        base_mod.LANE_ROLE_BY_SEED = dict(LANE_ROLE_BY_SEED)
        base_mod.EXPECTED_GATE_VERDICT_BY_SEED = dict(EXPECTED_GATE_VERDICT_BY_SEED)
        yield
    finally:
        base_mod.SEARCH_SEEDS = original_search_seeds
        base_mod.LANE_ROLE_BY_SEED = original_lane_role_by_seed
        base_mod.EXPECTED_GATE_VERDICT_BY_SEED = original_expected_gate_verdict_by_seed


def _build_child_run_label(search_seed: int) -> str:
    return (
        "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_"
        f"exact_replay_1111_search{int(search_seed)}_v1"
    )


def _build_child_scope_note(search_seed: int) -> str:
    if int(search_seed) == 7002:
        return (
            "exact retained replay wires the restart32 best-init checkpoint rule "
            "as both fallback and early stop on the remaining filtered 1111 "
            "lane so the read measures family-generalized saved wallclock"
        )
    return (
        "exact retained replay wires the restart32 best-init checkpoint rule "
        "as both fallback and early stop on a remaining kept 1111 lane so the "
        "read checks family-generalized no-harm relative to the prior exact replay"
    )


def _summary_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    filtered_rows = [
        dict(row) for row in rows if base_mod._safe_str(row.get("lane_role")) == "filtered_family"
    ]
    kept_rows = [
        dict(row) for row in rows if base_mod._safe_str(row.get("lane_role")) == "kept_family"
    ]
    filtered_row = filtered_rows[0] if filtered_rows else {}
    filtered_behaved_as_expected = _row_behaved_as_expected(filtered_row)
    verdict_match_count = sum(
        1
        for row in rows
        if base_mod._safe_str(row.get("observed_gate_verdict"))
        == base_mod._safe_str(row.get("expected_gate_verdict"))
    )
    kept_no_harm_count = sum(
        1
        for row in kept_rows
        if _row_behaved_as_expected(row) == 1
    )
    return {
        "rule_id": action_mod.RULE_ID,
        "action_contract_id": action_mod.ACTION_CONTRACT_ID,
        "action_contract_mode": action_mod.ACTION_CONTRACT_MODE,
        "completed_run_count": int(len(rows)),
        "verdict_match_count": int(verdict_match_count),
        "filtered_search_seed": base_mod._safe_int(filtered_row.get("search_seed")),
        "filtered_gate_verdict": base_mod._safe_str(filtered_row.get("observed_gate_verdict")),
        "filtered_action_applied": base_mod._safe_int(
            filtered_row.get("phasea_gate_action_applied")
        ),
        "filtered_checkpoint_restart_count": base_mod._safe_int(
            filtered_row.get("gate_checkpoint_restart_count")
        ),
        "filtered_saved_attempt_seconds": base_mod._safe_float(
            filtered_row.get("actual_saved_attempt_seconds")
        ),
        "filtered_saved_attempt_share": base_mod._safe_float(
            filtered_row.get("actual_saved_attempt_share")
        ),
        "filtered_behaved_as_expected": int(filtered_behaved_as_expected),
        "kept_run_count": int(len(kept_rows)),
        "kept_no_harm_count": int(kept_no_harm_count),
        "kept_search_seeds": [base_mod._safe_int(row.get("search_seed")) for row in kept_rows],
        "kept_max_abs_delta_vs_reference_candidate": max(
            (
                abs(base_mod._safe_float(row.get("delta_vs_reference_candidate")))
                for row in kept_rows
            ),
            default=float("nan"),
        ),
        "kept_mean_delta_vs_baseline": base_mod._mean(
            [base_mod._safe_float(row.get("delta_vs_baseline")) for row in kept_rows]
        ),
        "family_mean_delta_vs_baseline": base_mod._mean(
            [base_mod._safe_float(row.get("delta_vs_baseline")) for row in rows]
        ),
        "mean_gate_checkpoint_share_of_reference_attempt": base_mod._mean(
            [
                base_mod._safe_float(row.get("gate_checkpoint_share_of_reference_attempt"))
                for row in rows
            ]
        ),
    }


def _build_recommendation(summary_row: Mapping[str, Any]) -> dict[str, Any]:
    completed = base_mod._safe_int(summary_row.get("completed_run_count"))
    filtered_ok = base_mod._safe_int(summary_row.get("filtered_behaved_as_expected")) == 1
    kept_no_harm_count = base_mod._safe_int(summary_row.get("kept_no_harm_count"))
    verdict_match_count = base_mod._safe_int(summary_row.get("verdict_match_count"))
    filtered_saved_attempt_share = base_mod._safe_float(
        summary_row.get("filtered_saved_attempt_share")
    )
    if (
        completed == len(SEARCH_SEEDS)
        and filtered_ok
        and kept_no_harm_count == 2
        and verdict_match_count == len(SEARCH_SEEDS)
    ):
        if filtered_saved_attempt_share >= 0.25:
            return {
                "recommendation": "advance",
                "next_branch_label": NEXT_BRANCH_ADVANCE_LABEL,
                "reason": (
                    "All remaining lanes matched the restart32 best-init action "
                    "contract, the filtered lane saved material wallclock, and "
                    "both kept lanes stayed no-harm."
                ),
            }
        return {
            "recommendation": "refine",
            "next_branch_label": NEXT_BRANCH_REFINE_LABEL,
            "reason": (
                "The remaining family lanes matched the restart32 best-init "
                "contract, but the filtered lane saved only a small wallclock share."
            ),
        }
    return {
        "recommendation": "hold",
        "next_branch_label": "",
        "reason": (
            "At least one remaining family lane failed the restart32 best-init "
            "action contract, so the branch should not widen yet."
        ),
    }


def _write_markdown(
    *,
    path: Path,
    rows: list[dict[str, Any]],
    summary_row: Mapping[str, Any],
    recommendation: Mapping[str, Any],
    state_payload: Mapping[str, Any],
) -> None:
    lines = [
        READOUT_TITLE,
        "",
        "Question:",
        f"- {QUESTION}",
        "",
        "Mechanism layer:",
        f"- `{MECHANISM_LAYER}`",
        "",
        "Recommendation:",
        f"- `{base_mod._safe_str(recommendation.get('recommendation'))}`",
        (
            "- next branch: "
            f"`{base_mod._safe_str(recommendation.get('next_branch_label')) or 'none'}`"
        ),
        f"- reason: {base_mod._safe_str(recommendation.get('reason'))}",
        "",
        "Summary:",
        (
            "- completed runs: "
            f"`{base_mod._safe_int(summary_row.get('completed_run_count'))}` / "
            f"`{len(SEARCH_SEEDS)}`"
        ),
        (
            "- verdict matches: "
            f"`{base_mod._safe_int(summary_row.get('verdict_match_count'))}` / "
            f"`{len(SEARCH_SEEDS)}`"
        ),
        (
            "- filtered lane: "
            f"`search{base_mod._safe_int(summary_row.get('filtered_search_seed'))}` / "
            f"verdict `{base_mod._safe_str(summary_row.get('filtered_gate_verdict'))}` / "
            f"action applied `{base_mod._safe_int(summary_row.get('filtered_action_applied'))}`"
        ),
        (
            "- filtered checkpoint restart: "
            f"`{base_mod._safe_int(summary_row.get('filtered_checkpoint_restart_count'))}`"
        ),
        (
            "- filtered saved attempt seconds: "
            f"`{base_mod._safe_float(summary_row.get('filtered_saved_attempt_seconds')):.1f}`"
        ),
        (
            "- filtered saved attempt share: "
            f"`{base_mod._safe_float(summary_row.get('filtered_saved_attempt_share')):.3f}`"
        ),
        (
            "- kept no-harm count: "
            f"`{base_mod._safe_int(summary_row.get('kept_no_harm_count'))}` / "
            f"`{base_mod._safe_int(summary_row.get('kept_run_count'))}`"
        ),
        (
            "- max absolute kept delta vs prior exact replay: "
            f"`{base_mod._safe_float(summary_row.get('kept_max_abs_delta_vs_reference_candidate')):.3f}`"
        ),
        (
            "- family mean delta vs baseline: "
            f"`{base_mod._safe_float(summary_row.get('family_mean_delta_vs_baseline')):.3f}`"
        ),
        (
            "- mean checkpoint share of prior exact attempts: "
            f"`{base_mod._safe_float(summary_row.get('mean_gate_checkpoint_share_of_reference_attempt')):.3f}`"
        ),
        f"- final status: `{base_mod._safe_str(state_payload.get('status'))}`",
        "",
        "Per-lane read:",
    ]
    for row in rows:
        lines.extend(
            [
                (
                    f"- `search{base_mod._safe_int(row.get('search_seed'))}` / "
                    f"`{base_mod._safe_str(row.get('lane_role'))}`"
                ),
                (
                    f"  - observed gate verdict "
                    f"`{base_mod._safe_str(row.get('observed_gate_verdict'))}`"
                ),
                (
                    f"  - expected gate verdict "
                    f"`{base_mod._safe_str(row.get('expected_gate_verdict'))}`"
                ),
                f"  - trigger `{base_mod._safe_str(row.get('trigger_source'))}`",
                (
                    f"  - checkpoint restart "
                    f"`{base_mod._safe_int(row.get('gate_checkpoint_restart_count'))}`"
                ),
                (
                    f"  - action applied "
                    f"`{base_mod._safe_int(row.get('phasea_gate_action_applied'))}`"
                ),
                f"  - elapsed `{base_mod._safe_str(row.get('elapsed'))}`",
                (
                    f"  - saved attempt seconds "
                    f"`{base_mod._safe_float(row.get('actual_saved_attempt_seconds')):.1f}`"
                ),
                (
                    f"  - delta vs prior exact replay "
                    f"`{base_mod._safe_float(row.get('delta_vs_reference_candidate')):.3f}`"
                ),
                (
                    f"  - delta vs baseline "
                    f"`{base_mod._safe_float(row.get('delta_vs_baseline')):.3f}`"
                ),
                (
                    f"  - behaved as expected "
                    f"`{_row_behaved_as_expected(row)}`"
                ),
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _row_behaved_as_expected(row: Mapping[str, Any]) -> int:
    return base_mod._action_behaved_as_expected_for_role(
        lane_role=base_mod._safe_str(row.get("lane_role")),
        observed_gate_verdict=base_mod._safe_str(row.get("observed_gate_verdict")),
        expected_gate_verdict=base_mod._safe_str(row.get("expected_gate_verdict")),
        action_applied=base_mod._safe_int(row.get("phasea_gate_action_applied")),
        current_resume_best_match_ratio=base_mod._safe_float(
            row.get("current_resume_best_match_ratio")
        ),
        baseline_best_match_ratio=base_mod._safe_float(
            row.get("baseline_best_match_ratio")
        ),
        reference_resume_best_match_ratio=base_mod._safe_float(
            row.get("reference_resume_best_match_ratio")
        ),
    )


def run_microbatch() -> dict[str, Any]:
    started = monotonic()
    started_at_utc = base_mod._utc_now_iso()
    output_dir = action_mod.base_mod.replay_mod.OUTPUT_BASE_DIR / f"{base_mod._utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    state_path = output_dir / "matrix_run_state.json"
    events_path = output_dir / "matrix_run_events.jsonl"
    rows_csv_path = output_dir / f"{FILE_STEM}_rows.csv"
    rows_jsonl_path = output_dir / f"{FILE_STEM}_rows.jsonl"
    summary_path = output_dir / f"{FILE_STEM}_summary.json"
    recommendation_path = output_dir / f"{FILE_STEM}_recommendation.json"
    readout_path = output_dir / f"{FILE_STEM}_readout.md"

    with _patched_base_module():
        reference_rows = base_mod._load_reference_rows()
        anchored_total_seconds = base_mod._anchored_total_seconds(reference_rows)
        state_payload: dict[str, Any] = {
            "status": "running",
            "started_at_utc": started_at_utc,
            "updated_at_utc": started_at_utc,
            "run_label": RUN_LABEL,
            "output_dir": base_mod._relative_path(output_dir),
            "mechanism_layer": MECHANISM_LAYER,
            "question": QUESTION,
            "suspicion": SUSPICION,
            "main_alternative": MAIN_ALTERNATIVE,
            "if_suspicion_true_expect": IF_SUSPICION_TRUE_EXPECT,
            "if_alternative_true_expect": IF_ALTERNATIVE_TRUE_EXPECT,
            "decision_rule": DECISION_RULE,
            "stop_condition": STOP_CONDITION,
            "planned_jobs": len(SEARCH_SEEDS),
            "completed_jobs": 0,
            "budget_hours": INTENDED_WALLCLOCK_BUDGET_HOURS,
            "anchored_total_elapsed": base_mod._format_duration(anchored_total_seconds),
            "reference_matrix_bundle": base_mod._relative_path(base_mod.REFERENCE_MATRIX_BUNDLE_DIR),
        }
        base_mod._write_json(state_path, state_payload)
        base_mod._append_jsonl(
            events_path,
            {
                "event": "run_started",
                "ts_utc": base_mod._utc_now_iso(),
                "output_dir": base_mod._relative_path(output_dir),
                "planned_jobs": len(SEARCH_SEEDS),
                "budget_hours": INTENDED_WALLCLOCK_BUDGET_HOURS,
                "anchored_total_elapsed": base_mod._format_duration(anchored_total_seconds),
                "rule_id": action_mod.RULE_ID,
            },
        )
        base_mod._print_progress(
            "run_started "
            f"label={RUN_LABEL} "
            f"output_dir={base_mod._relative_path(output_dir)} "
            f"units={len(SEARCH_SEEDS)} "
            f"budget={base_mod._format_duration(MAX_WALLCLOCK_SECONDS)} "
            f"anchored_total={base_mod._format_duration(anchored_total_seconds)} "
            f"rule_id={action_mod.RULE_ID}"
        )

        rows: list[dict[str, Any]] = []
        for index, search_seed in enumerate(SEARCH_SEEDS, start=1):
            projected_total_seconds = base_mod._project_total_seconds(
                completed_rows=rows,
                reference_rows=reference_rows,
            )
            if projected_total_seconds > float(MAX_WALLCLOCK_SECONDS):
                state_payload.update(
                    {
                        "status": "stopped_over_budget",
                        "updated_at_utc": base_mod._utc_now_iso(),
                        "projected_total_seconds": float(projected_total_seconds),
                        "projected_total_elapsed": base_mod._format_duration(projected_total_seconds),
                        "completed_jobs": len(rows),
                    }
                )
                base_mod._write_json(state_path, state_payload)
                base_mod._print_progress(
                    "run_stopped_over_budget "
                    f"completed={len(rows)}/{len(SEARCH_SEEDS)} "
                    f"projected_total={base_mod._format_duration(projected_total_seconds)} "
                    f"budget={base_mod._format_duration(MAX_WALLCLOCK_SECONDS)}"
                )
                break

            lane_role = base_mod._safe_str(LANE_ROLE_BY_SEED.get(int(search_seed)))
            expected_gate_verdict = base_mod._safe_str(
                EXPECTED_GATE_VERDICT_BY_SEED.get(int(search_seed))
            )
            reference_row = reference_rows[int(search_seed)]
            base_mod._append_jsonl(
                events_path,
                {
                    "event": "job_started",
                    "ts_utc": base_mod._utc_now_iso(),
                    "unit": int(index),
                    "units": len(SEARCH_SEEDS),
                    "search_seed": int(search_seed),
                    "lane_role": lane_role,
                    "expected_gate_verdict": expected_gate_verdict,
                },
            )
            base_mod._print_progress(
                "job_started "
                f"unit={index}/{len(SEARCH_SEEDS)} "
                f"search_seed={search_seed} "
                f"lane_role={lane_role} "
                f"expected_gate_verdict={expected_gate_verdict}"
            )
            child_run_summary = base_mod.replay_mod.run_verification(
                search_seed=int(search_seed),
                run_label=_build_child_run_label(search_seed),
                phasea_provisional_gate_action_decider=(
                    action_mod._build_phasea_provisional_gate_action_decider(
                        reference_row=reference_row,
                        expected_gate_verdict=expected_gate_verdict,
                    )
                ),
                scope_note_override=_build_child_scope_note(search_seed),
            )
            row = base_mod._build_row_from_child_output(
                search_seed=int(search_seed),
                child_output_dir_relpath=base_mod._safe_str(child_run_summary.get("output_dir")),
                reference_row=reference_row,
            )
            rows.append(row)
            base_mod._append_jsonl(rows_jsonl_path, row)
            projected_total_seconds = base_mod._project_total_seconds(
                completed_rows=rows,
                reference_rows=reference_rows,
            )
            remaining_eta_seconds = max(
                0.0,
                projected_total_seconds
                - sum(
                    base_mod._safe_float(item.get("elapsed_seconds"))
                    for item in rows
                    if math.isfinite(base_mod._safe_float(item.get("elapsed_seconds")))
                ),
            )
            state_payload.update(
                {
                    "status": "running",
                    "updated_at_utc": base_mod._utc_now_iso(),
                    "completed_jobs": len(rows),
                    "latest_completed_search_seed": int(search_seed),
                    "latest_completed_output_dir": base_mod._safe_str(row.get("output_dir")),
                    "projected_total_seconds": float(projected_total_seconds),
                    "projected_total_elapsed": base_mod._format_duration(projected_total_seconds),
                }
            )
            base_mod._write_json(state_path, state_payload)
            base_mod._append_jsonl(
                events_path,
                {
                    "event": "job_finished",
                    "ts_utc": base_mod._utc_now_iso(),
                    "unit": int(index),
                    "units": len(SEARCH_SEEDS),
                    "search_seed": int(search_seed),
                    "lane_role": lane_role,
                    "observed_gate_verdict": base_mod._safe_str(row.get("observed_gate_verdict")),
                    "action_applied": base_mod._safe_int(row.get("phasea_gate_action_applied")),
                    "elapsed_seconds": base_mod._safe_float(row.get("elapsed_seconds")),
                    "saved_attempt_seconds": base_mod._safe_float(
                        row.get("actual_saved_attempt_seconds")
                    ),
                },
            )
            base_mod._print_progress(
                "job_finished "
                f"unit={index}/{len(SEARCH_SEEDS)} "
                f"search_seed={search_seed} "
                f"gate_verdict={base_mod._safe_str(row.get('observed_gate_verdict'))} "
                f"action_applied={base_mod._safe_int(row.get('phasea_gate_action_applied'))} "
                f"saved_attempt_seconds={base_mod._safe_float(row.get('actual_saved_attempt_seconds')):.1f} "
                f"elapsed={base_mod._safe_str(row.get('elapsed'))} "
                f"eta={base_mod._format_duration(remaining_eta_seconds)}"
            )

        summary_row = _summary_row(rows)
        recommendation = _build_recommendation(summary_row)
        base_mod._write_rows_csv(rows_csv_path, rows)
        base_mod._write_json(
            summary_path,
            {"summary_row": summary_row, "output_dir": base_mod._relative_path(output_dir)},
        )
        base_mod._write_json(recommendation_path, recommendation)
        _write_markdown(
            path=readout_path,
            rows=rows,
            summary_row=summary_row,
            recommendation=recommendation,
            state_payload=state_payload,
        )
        refresh_catalog_safely(print_fn=print)

        elapsed_seconds = float(monotonic() - started)
        final_status = (
            base_mod._safe_str(state_payload.get("status"))
            if base_mod._safe_str(state_payload.get("status")) == "stopped_over_budget"
            else "completed"
        )
        state_payload.update(
            {
                "status": final_status,
                "updated_at_utc": base_mod._utc_now_iso(),
                "elapsed_seconds": float(elapsed_seconds),
                "elapsed": base_mod._format_duration(elapsed_seconds),
                "completed_jobs": len(rows),
                "summary_json": base_mod._relative_path(summary_path),
                "recommendation_json": base_mod._relative_path(recommendation_path),
                "rows_csv": base_mod._relative_path(rows_csv_path),
                "rows_jsonl": base_mod._relative_path(rows_jsonl_path),
                "readout_md": base_mod._relative_path(readout_path),
                "recommendation": dict(recommendation),
            }
        )
        base_mod._write_json(state_path, state_payload)
        base_mod._append_jsonl(
            events_path,
            {
                "event": "run_finished",
                "ts_utc": base_mod._utc_now_iso(),
                "status": final_status,
                "completed_jobs": len(rows),
                "recommendation": base_mod._safe_str(recommendation.get("recommendation")),
                "elapsed_seconds": float(elapsed_seconds),
            },
        )
        base_mod._print_progress(
            "run_finished "
            f"label={RUN_LABEL} "
            f"status={final_status} "
            f"completed_jobs={len(rows)}/{len(SEARCH_SEEDS)} "
            f"elapsed={base_mod._format_duration(elapsed_seconds)} "
            f"recommendation={base_mod._safe_str(recommendation.get('recommendation'))} "
            f"output_dir={base_mod._relative_path(output_dir)}"
        )
        return {
            "run_label": RUN_LABEL,
            "output_dir": base_mod._relative_path(output_dir),
            "state_path": base_mod._relative_path(state_path),
            "summary_path": base_mod._relative_path(summary_path),
            "recommendation_path": base_mod._relative_path(recommendation_path),
            "rows_csv_path": base_mod._relative_path(rows_csv_path),
            "completed_jobs": len(rows),
            "recommendation": base_mod._safe_str(recommendation.get("recommendation")),
        }


def main() -> None:
    print(json.dumps(run_microbatch(), sort_keys=True))


if __name__ == "__main__":
    main()
