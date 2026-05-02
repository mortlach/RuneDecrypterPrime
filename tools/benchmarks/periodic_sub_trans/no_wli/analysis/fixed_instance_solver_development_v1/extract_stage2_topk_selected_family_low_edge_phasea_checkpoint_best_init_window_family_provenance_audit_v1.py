from __future__ import annotations

import csv
import json
import re
import sys
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
        "extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1.py"
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
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_both_action_microprobe_v1 as base_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1 as family_mod,
)


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1"
)
FILE_STEM = (
    "selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance"
)
READOUT_TITLE = (
    "# Phase-A Checkpoint Best-Init Window Family Provenance Audit"
)
MECHANISM_LAYER = "selection"
SOURCE_BUNDLE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
    / "20260425T170754Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_reconciled_v1"
)
ROWS_CSV = (
    SOURCE_BUNDLE_DIR
    / "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_rows.csv"
)
STATE_JSON = SOURCE_BUNDLE_DIR / "matrix_run_state.json"
EVENTS_JSONL = SOURCE_BUNDLE_DIR / "matrix_run_events.jsonl"
SUMMARY_JSON = (
    SOURCE_BUNDLE_DIR
    / "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_summary.json"
)
RECOMMENDATION_JSON = (
    SOURCE_BUNDLE_DIR
    / "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_recommendation.json"
)
READOUT_MD = (
    SOURCE_BUNDLE_DIR
    / "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_readout.md"
)
NEXT_BRANCH_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_family_reconciliation_rerun"
)
QUESTION = (
    "Is the decisive remaining-family restart32 best-init bundle evidence-clean "
    "enough for external review, or does it still contain provenance/reporting "
    "mismatches across rows, state, events, summary, recommendation, and readout?"
)
SUSPICION = (
    "The raw measurement columns likely support the carried checkpoint split, "
    "but the original row/control layer still contains stale mismatches caused "
    "by role-label drift."
)
MAIN_ALTERNATIVE = (
    "The bundle may already be evidence-clean, or the later regenerated "
    "summary/readout may have introduced a different mismatch than the one "
    "suggested by review."
)
DECISION_RULE = (
    "Hold if any required recommendation layer is missing, any recommendation "
    "layer disagrees, or any row-level action_behaved_as_expected value "
    "disagrees with the recomputed shared role-contract logic. Advance only if "
    "all inspected artefacts are present and agree."
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_label() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Refusing to write empty provenance-audit rows")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_rows(path: Path) -> list[dict[str, Any]]:
    return [dict(row) for row in csv.DictReader(path.open(encoding="utf-8"))]


def _load_final_run_finished_event(path: Path) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = dict(json.loads(line))
            if base_mod._safe_str(payload.get("event")) == "run_finished":
                events.append(payload)
    return events[-1] if events else {}


def _extract_readout_recommendation(text: str) -> str:
    match = re.search(r"(?ms)^Recommendation:\s*\n- `([^`]+)`", text)
    return str(match.group(1)) if match else ""


def _build_row_check(row: Mapping[str, Any]) -> dict[str, Any]:
    saved_value = base_mod._safe_int(row.get("action_behaved_as_expected"))
    recomputed_value = base_mod._action_behaved_as_expected_for_role(
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
    return {
        "search_seed": base_mod._safe_int(row.get("search_seed")),
        "lane_role": base_mod._safe_str(row.get("lane_role")),
        "observed_gate_verdict": base_mod._safe_str(row.get("observed_gate_verdict")),
        "expected_gate_verdict": base_mod._safe_str(row.get("expected_gate_verdict")),
        "phasea_gate_action_applied": base_mod._safe_int(
            row.get("phasea_gate_action_applied")
        ),
        "baseline_best_match_ratio": base_mod._safe_float(
            row.get("baseline_best_match_ratio")
        ),
        "reference_resume_best_match_ratio": base_mod._safe_float(
            row.get("reference_resume_best_match_ratio")
        ),
        "current_resume_best_match_ratio": base_mod._safe_float(
            row.get("current_resume_best_match_ratio")
        ),
        "saved_action_behaved_as_expected": int(saved_value),
        "recomputed_action_behaved_as_expected": int(recomputed_value),
        "row_mismatch": int(saved_value != recomputed_value),
    }


def _build_summary_row(
    *,
    row_checks: list[dict[str, Any]],
    summary_payload: Mapping[str, Any],
    state_payload: Mapping[str, Any],
    final_event: Mapping[str, Any],
    recommendation_payload: Mapping[str, Any],
    readout_recommendation: str,
) -> dict[str, Any]:
    mismatched_rows = [
        row for row in row_checks if base_mod._safe_int(row.get("row_mismatch")) == 1
    ]
    summary_recomputed_recommendation = base_mod._safe_str(
        family_mod._build_recommendation(
            dict(summary_payload.get("summary_row", {}))
        ).get("recommendation")
    )
    state_recommendation = base_mod._safe_str(
        state_payload.get("recommendation", {}).get("recommendation")
    )
    event_recommendation = base_mod._safe_str(final_event.get("recommendation"))
    recommendation_json_recommendation = base_mod._safe_str(
        recommendation_payload.get("recommendation")
    )
    readout_recommendation = base_mod._safe_str(readout_recommendation)
    completed_jobs = base_mod._safe_int(state_payload.get("completed_jobs"))
    planned_jobs = base_mod._safe_int(state_payload.get("planned_jobs"))
    recommendation_layers = {
        "state": state_recommendation,
        "final_event": event_recommendation,
        "summary_derived": summary_recomputed_recommendation,
        "recommendation_json": recommendation_json_recommendation,
        "readout": readout_recommendation,
    }
    missing_recommendation_layers = [
        layer for layer, value in recommendation_layers.items() if not value
    ]
    recommendation_values = list(recommendation_layers.values())
    recommendation_values_present = not missing_recommendation_layers
    return {
        "source_bundle_dir": _relative_path(SOURCE_BUNDLE_DIR),
        "source_status": base_mod._safe_str(state_payload.get("status")),
        "completed_jobs": int(completed_jobs),
        "planned_jobs": int(planned_jobs),
        "bundle_complete": int(planned_jobs > 0 and completed_jobs == planned_jobs),
        "row_count": int(len(row_checks)),
        "row_mismatch_count": int(len(mismatched_rows)),
        "mismatched_search_seeds": [
            base_mod._safe_int(row.get("search_seed")) for row in mismatched_rows
        ],
        "recommendation_values_present": int(recommendation_values_present),
        "missing_recommendation_layers": missing_recommendation_layers,
        "recommendation_values_match": int(
            recommendation_values_present and len(set(recommendation_values)) == 1
        ),
        "state_recommendation": state_recommendation,
        "event_recommendation": event_recommendation,
        "summary_recomputed_recommendation": summary_recomputed_recommendation,
        "recommendation_json_recommendation": recommendation_json_recommendation,
        "readout_recommendation": readout_recommendation,
    }


def _write_markdown(
    *,
    path: Path,
    summary_row: Mapping[str, Any],
    recommendation: Mapping[str, Any],
    row_checks: list[dict[str, Any]],
) -> None:
    mismatched_rows = [row for row in row_checks if base_mod._safe_int(row.get("row_mismatch")) == 1]
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
        f"- next branch: `{base_mod._safe_str(recommendation.get('next_branch_label')) or 'none'}`",
        f"- reason: {base_mod._safe_str(recommendation.get('reason'))}",
        "",
        "Summary:",
        (
            "- recommendation values match: "
            f"`{base_mod._safe_int(summary_row.get('recommendation_values_match'))}`"
        ),
        (
            "- recommendation values present: "
            f"`{base_mod._safe_int(summary_row.get('recommendation_values_present'))}`"
        ),
        (
            "- missing recommendation layers: "
            f"`{', '.join(summary_row.get('missing_recommendation_layers', [])) or 'none'}`"
        ),
        (
            "- source status: "
            f"`{base_mod._safe_str(summary_row.get('source_status'))}`"
        ),
        (
            "- completed jobs: "
            f"`{base_mod._safe_int(summary_row.get('completed_jobs'))}` / "
            f"`{base_mod._safe_int(summary_row.get('planned_jobs'))}`"
        ),
        (
            "- bundle complete: "
            f"`{base_mod._safe_int(summary_row.get('bundle_complete'))}`"
        ),
        (
            "- row mismatch count: "
            f"`{base_mod._safe_int(summary_row.get('row_mismatch_count'))}`"
        ),
        (
            "- mismatched search seeds: "
            f"`{base_mod._safe_str(summary_row.get('mismatched_search_seeds'))}`"
        ),
        (
            "- state recommendation: "
            f"`{base_mod._safe_str(summary_row.get('state_recommendation'))}`"
        ),
        (
            "- final event recommendation: "
            f"`{base_mod._safe_str(summary_row.get('event_recommendation'))}`"
        ),
        (
            "- summary recomputed recommendation: "
            f"`{base_mod._safe_str(summary_row.get('summary_recomputed_recommendation'))}`"
        ),
        (
            "- recommendation json recommendation: "
            f"`{base_mod._safe_str(summary_row.get('recommendation_json_recommendation'))}`"
        ),
        (
            "- readout recommendation: "
            f"`{base_mod._safe_str(summary_row.get('readout_recommendation'))}`"
        ),
        "",
        "Row checks:",
    ]
    for row in mismatched_rows or row_checks:
        lines.extend(
            [
                f"- `search{base_mod._safe_int(row.get('search_seed'))}` / `{base_mod._safe_str(row.get('lane_role'))}`",
                f"  - saved action_behaved_as_expected `{base_mod._safe_int(row.get('saved_action_behaved_as_expected'))}`",
                f"  - recomputed action_behaved_as_expected `{base_mod._safe_int(row.get('recomputed_action_behaved_as_expected'))}`",
                f"  - observed gate verdict `{base_mod._safe_str(row.get('observed_gate_verdict'))}`",
                f"  - expected gate verdict `{base_mod._safe_str(row.get('expected_gate_verdict'))}`",
                f"  - action applied `{base_mod._safe_int(row.get('phasea_gate_action_applied'))}`",
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_audit() -> dict[str, Any]:
    output_dir = (
        base_mod.replay_mod.OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    rows_csv_path = output_dir / f"{FILE_STEM}_row_checks.csv"
    summary_path = output_dir / f"{FILE_STEM}_summary.json"
    recommendation_path = output_dir / f"{FILE_STEM}_recommendation.json"
    readout_path = output_dir / f"{FILE_STEM}_readout.md"

    rows = _load_rows(ROWS_CSV)
    state_payload = _load_json(STATE_JSON)
    summary_payload = _load_json(SUMMARY_JSON)
    recommendation_payload = _load_json(RECOMMENDATION_JSON)
    final_event = _load_final_run_finished_event(EVENTS_JSONL)
    readout_text = READOUT_MD.read_text(encoding="utf-8")
    row_checks = [_build_row_check(row) for row in rows]
    mismatched_rows = [
        row for row in row_checks if base_mod._safe_int(row.get("row_mismatch")) == 1
    ]

    readout_recommendation = _extract_readout_recommendation(readout_text)
    summary_row = _build_summary_row(
        row_checks=row_checks,
        summary_payload=summary_payload,
        state_payload=state_payload,
        final_event=final_event,
        recommendation_payload=recommendation_payload,
        readout_recommendation=readout_recommendation,
    )
    recommendation_values_match = base_mod._safe_int(
        summary_row.get("recommendation_values_match")
    )
    bundle_complete = base_mod._safe_int(summary_row.get("bundle_complete")) == 1
    if recommendation_values_match == 1 and not mismatched_rows and bundle_complete:
        recommendation = {
            "recommendation": "advance",
            "next_branch_label": "",
            "reason": (
                "The decisive remaining-family bundle is internally consistent "
                "across its inspected artefact layers."
            ),
        }
    else:
        recommendation = {
            "recommendation": "hold",
            "next_branch_label": NEXT_BRANCH_LABEL,
            "reason": (
                "The decisive remaining-family bundle is incomplete or still "
                "contains at least one recommendation mismatch or row-level "
                "behaved-as-expected mismatch, so the external-review handoff "
                "is not yet evidence-clean."
            ),
        }

    _write_rows_csv(rows_csv_path, row_checks)
    _write_json(
        summary_path,
        {
            "question": QUESTION,
            "suspicion": SUSPICION,
            "alternative": MAIN_ALTERNATIVE,
            "decision_rule": DECISION_RULE,
            "summary_row": summary_row,
            "output_dir": _relative_path(output_dir),
        },
    )
    _write_json(recommendation_path, recommendation)
    _write_markdown(
        path=readout_path,
        summary_row=summary_row,
        recommendation=recommendation,
        row_checks=row_checks,
    )
    refresh_catalog_safely(print_fn=print)
    print(
        json.dumps(
            {
                "output_dir": _relative_path(output_dir),
                "recommendation": recommendation["recommendation"],
                "row_mismatch_count": len(mismatched_rows),
                "recommendation_values_match": recommendation_values_match,
            },
            sort_keys=True,
        )
    )
    return {
        "output_dir": _relative_path(output_dir),
        "summary_path": _relative_path(summary_path),
        "recommendation_path": _relative_path(recommendation_path),
        "readout_path": _relative_path(readout_path),
    }


def main() -> None:
    run_audit()


if __name__ == "__main__":
    main()
