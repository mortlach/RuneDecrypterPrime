from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "regenerate_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_reconciled_v1.py"
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
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1 as family_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_both_action_microprobe_v1 as base_mod,
)


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_reconciled_v1"
)
FILE_STEM = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch"
)
SOURCE_BUNDLE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
    / "20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1"
)
SOURCE_ROWS_CSV = SOURCE_BUNDLE_DIR / f"{FILE_STEM}_rows.csv"
OUTPUT_ROOT = base_mod.replay_mod.OUTPUT_BASE_DIR
PROVENANCE_NOTE = (
    "Reconciled derived bundle regenerated from the 2026-04-24 family "
    "microbatch measurement rows after the shared role contract was fixed. "
    "The raw per-lane measurement columns are retained; "
    "action_behaved_as_expected, summary, recommendation, readout, state, "
    "and final event are regenerated through the corrected role-contract path."
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _recompute_row_action_contract(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["action_behaved_as_expected"] = base_mod._action_behaved_as_expected_for_role(
        lane_role=base_mod._safe_str(out.get("lane_role")),
        observed_gate_verdict=base_mod._safe_str(out.get("observed_gate_verdict")),
        expected_gate_verdict=base_mod._safe_str(out.get("expected_gate_verdict")),
        action_applied=base_mod._safe_int(out.get("phasea_gate_action_applied")),
        current_resume_best_match_ratio=base_mod._safe_float(
            out.get("current_resume_best_match_ratio")
        ),
        baseline_best_match_ratio=base_mod._safe_float(
            out.get("baseline_best_match_ratio")
        ),
        reference_resume_best_match_ratio=base_mod._safe_float(
            out.get("reference_resume_best_match_ratio")
        ),
    )
    return out


def _write_rows_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def regenerate_reconciled_bundle() -> dict[str, Any]:
    output_dir = OUTPUT_ROOT / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    state_path = output_dir / "matrix_run_state.json"
    events_path = output_dir / "matrix_run_events.jsonl"
    rows_csv_path = output_dir / f"{FILE_STEM}_rows.csv"
    rows_jsonl_path = output_dir / f"{FILE_STEM}_rows.jsonl"
    summary_path = output_dir / f"{FILE_STEM}_summary.json"
    recommendation_path = output_dir / f"{FILE_STEM}_recommendation.json"
    readout_path = output_dir / f"{FILE_STEM}_readout.md"

    rows = [_recompute_row_action_contract(row) for row in _load_rows(SOURCE_ROWS_CSV)]
    summary_row = family_mod._summary_row(rows)
    recommendation = family_mod._build_recommendation(summary_row)
    started_at_utc = _utc_now_iso()

    state_payload: dict[str, Any] = {
        "status": "completed",
        "started_at_utc": started_at_utc,
        "updated_at_utc": started_at_utc,
        "run_label": RUN_LABEL,
        "output_dir": base_mod._relative_path(output_dir),
        "source_bundle_dir": base_mod._relative_path(SOURCE_BUNDLE_DIR),
        "provenance_note": PROVENANCE_NOTE,
        "mechanism_layer": family_mod.MECHANISM_LAYER,
        "question": family_mod.QUESTION,
        "decision_rule": family_mod.DECISION_RULE,
        "planned_jobs": len(family_mod.SEARCH_SEEDS),
        "completed_jobs": len(rows),
        "summary_json": base_mod._relative_path(summary_path),
        "recommendation_json": base_mod._relative_path(recommendation_path),
        "rows_csv": base_mod._relative_path(rows_csv_path),
        "rows_jsonl": base_mod._relative_path(rows_jsonl_path),
        "readout_md": base_mod._relative_path(readout_path),
        "recommendation": dict(recommendation),
    }

    base_mod._write_json(state_path, state_payload)
    base_mod._append_jsonl(
        events_path,
        {
            "event": "run_started",
            "ts_utc": started_at_utc,
            "output_dir": base_mod._relative_path(output_dir),
            "source_bundle_dir": base_mod._relative_path(SOURCE_BUNDLE_DIR),
            "planned_jobs": len(family_mod.SEARCH_SEEDS),
            "provenance_note": PROVENANCE_NOTE,
        },
    )
    for index, row in enumerate(rows, start=1):
        base_mod._append_jsonl(
            events_path,
            {
                "event": "job_finished",
                "ts_utc": started_at_utc,
                "unit": int(index),
                "units": len(rows),
                "search_seed": base_mod._safe_int(row.get("search_seed")),
                "lane_role": base_mod._safe_str(row.get("lane_role")),
                "observed_gate_verdict": base_mod._safe_str(
                    row.get("observed_gate_verdict")
                ),
                "action_applied": base_mod._safe_int(
                    row.get("phasea_gate_action_applied")
                ),
                "action_behaved_as_expected": base_mod._safe_int(
                    row.get("action_behaved_as_expected")
                ),
                "reconciled": 1,
            },
        )

    base_mod._write_rows_csv(rows_csv_path, rows)
    _write_rows_jsonl(rows_jsonl_path, rows)
    base_mod._write_json(
        summary_path,
        {
            "summary_row": summary_row,
            "output_dir": base_mod._relative_path(output_dir),
            "source_bundle_dir": base_mod._relative_path(SOURCE_BUNDLE_DIR),
            "provenance_note": PROVENANCE_NOTE,
        },
    )
    base_mod._write_json(recommendation_path, recommendation)
    family_mod._write_markdown(
        path=readout_path,
        rows=rows,
        summary_row=summary_row,
        recommendation=recommendation,
        state_payload=state_payload,
    )
    base_mod._append_jsonl(
        events_path,
        {
            "event": "run_finished",
            "ts_utc": _utc_now_iso(),
            "status": "completed",
            "completed_jobs": len(rows),
            "recommendation": base_mod._safe_str(recommendation.get("recommendation")),
            "reconciled": 1,
        },
    )
    refresh_catalog_safely(print_fn=print)

    result = {
        "run_label": RUN_LABEL,
        "output_dir": base_mod._relative_path(output_dir),
        "state_path": base_mod._relative_path(state_path),
        "summary_path": base_mod._relative_path(summary_path),
        "recommendation_path": base_mod._relative_path(recommendation_path),
        "rows_csv_path": base_mod._relative_path(rows_csv_path),
        "readout_path": base_mod._relative_path(readout_path),
        "completed_jobs": len(rows),
        "recommendation": base_mod._safe_str(recommendation.get("recommendation")),
    }
    print(json.dumps(result, sort_keys=True))
    return result


def main() -> None:
    regenerate_reconciled_bundle()


if __name__ == "__main__":
    main()
