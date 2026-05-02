from __future__ import annotations

import csv
import json
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
        "extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1.py"
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
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1 as live_mod,
)


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1"
)
FILE_STEM = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit"
)
READOUT_TITLE = (
    "# Stage-2 Selected-Family Phase-A Checkpoint Live-Canary Provenance Audit v1"
)
SOURCE_BUNDLE_DIR: Path | None = None
USE_LATEST_SOURCE_BUNDLE = True
REQUIRED_RECOMMENDATION_LAYERS = (
    "state",
    "final_event",
    "summary_derived",
    "recommendation_json",
    "readout",
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


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True))
        handle.write("\n")


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Refusing to write empty live-canary audit rows")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_rows_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _load_final_event(path: Path) -> dict[str, Any]:
    final_event: dict[str, Any] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            event = dict(json.loads(line))
            if event.get("event") == "run_finished":
                final_event = event
    return final_event


def _extract_readout_recommendation(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().lower() != "recommendation:":
            continue
        for candidate in lines[index + 1 : index + 5]:
            stripped = candidate.strip()
            if stripped.startswith("- `") and "`" in stripped[3:]:
                return stripped.split("`", 2)[1]
    return ""


def _resolve_source_bundle_dir() -> Path:
    if SOURCE_BUNDLE_DIR is not None:
        return SOURCE_BUNDLE_DIR
    if not USE_LATEST_SOURCE_BUNDLE:
        raise RuntimeError("SOURCE_BUNDLE_DIR is not set")
    candidates = [
        path
        for path in live_mod.base_mod.replay_mod.OUTPUT_BASE_DIR.glob(
            f"*__{live_mod.RUN_LABEL}"
        )
        if path.is_dir()
    ]
    if not candidates:
        raise RuntimeError("No live-canary source bundle exists yet")
    return sorted(candidates, key=lambda path: path.name)[-1]


def _state_recommendation(state_payload: Mapping[str, Any]) -> str:
    recommendation = state_payload.get("recommendation")
    if isinstance(recommendation, Mapping):
        return live_mod.base_mod._safe_str(recommendation.get("recommendation"))
    return live_mod.base_mod._safe_str(recommendation)


def _summary_derived_recommendation(summary_payload: Mapping[str, Any]) -> str:
    summary_row = dict(summary_payload.get("summary_row", {}))
    return live_mod._build_recommendation(summary_row)["recommendation"]


def _build_row_check(row: Mapping[str, Any]) -> dict[str, Any]:
    saved_action = live_mod.base_mod._safe_int(
        row.get("action_behaved_as_expected")
    )
    recomputed_action = live_mod.base_mod._action_behaved_as_expected_for_role(
        lane_role=live_mod.base_mod._safe_str(row.get("lane_role")),
        observed_gate_verdict=live_mod.base_mod._safe_str(
            row.get("observed_gate_verdict")
        ),
        expected_gate_verdict=live_mod.base_mod._safe_str(
            row.get("expected_gate_verdict")
        ),
        action_applied=live_mod.base_mod._safe_int(
            row.get("phasea_gate_action_applied")
        ),
        current_resume_best_match_ratio=live_mod.base_mod._safe_float(
            row.get("current_resume_best_match_ratio")
        ),
        baseline_best_match_ratio=live_mod.base_mod._safe_float(
            row.get("baseline_best_match_ratio")
        ),
        reference_resume_best_match_ratio=live_mod.base_mod._safe_float(
            row.get("reference_resume_best_match_ratio")
        ),
    )
    missing_required = live_mod._missing_required_row_fields(row)
    expected_verdict = live_mod.base_mod._safe_str(row.get("expected_gate_verdict"))
    observed_verdict = live_mod.base_mod._safe_str(row.get("observed_gate_verdict"))
    filter_contract_ok = (
        expected_verdict == "filter"
        and observed_verdict == "filter"
        and live_mod.base_mod._safe_int(row.get("phasea_gate_action_applied")) == 1
        and live_mod.base_mod._safe_int(row.get("action_stop_now")) == 1
        and live_mod.base_mod._safe_int(row.get("action_fallback_to_baseline")) == 1
        and live_mod.base_mod._safe_str(row.get("fallback_target"))
        == "retained_baseline"
        and live_mod.base_mod._safe_float(row.get("phaseA_best_init_match"))
        < float(live_mod.BEST_INIT_THRESHOLD)
    )
    keep_contract_ok = (
        expected_verdict == "keep"
        and observed_verdict == "keep"
        and live_mod.base_mod._safe_int(row.get("phasea_gate_action_applied")) == 0
        and live_mod.base_mod._safe_int(row.get("action_stop_now")) == 0
        and live_mod.base_mod._safe_int(row.get("action_fallback_to_baseline")) == 0
        and live_mod.base_mod._safe_str(row.get("fallback_target")) == ""
        and live_mod.base_mod._safe_float(row.get("phaseA_best_init_match"))
        >= float(live_mod.BEST_INIT_THRESHOLD)
    )
    action_contract_ok = int(
        live_mod.base_mod._safe_int(row.get("gate_checkpoint_restart_count")) == 32
        and (filter_contract_ok or keep_contract_ok)
    )
    return {
        "search_seed": live_mod.base_mod._safe_int(row.get("search_seed")),
        "lane_role": live_mod.base_mod._safe_str(row.get("lane_role")),
        "saved_action_behaved_as_expected": int(saved_action),
        "recomputed_action_behaved_as_expected": int(recomputed_action),
        "action_contract_ok": int(action_contract_ok),
        "missing_required_row_fields": missing_required,
        "row_mismatch": int(
            saved_action != recomputed_action
            or missing_required
            or action_contract_ok != 1
        ),
    }


def _build_summary_row(
    *,
    row_checks: list[Mapping[str, Any]],
    summary_payload: Mapping[str, Any],
    state_payload: Mapping[str, Any],
    final_event: Mapping[str, Any],
    recommendation_payload: Mapping[str, Any],
    readout_recommendation: str,
    source_bundle_dir: Path,
) -> dict[str, Any]:
    summary_row = dict(summary_payload.get("summary_row", {}))
    state_recommendation = _state_recommendation(state_payload)
    event_recommendation = live_mod.base_mod._safe_str(final_event.get("recommendation"))
    summary_recomputed_recommendation = _summary_derived_recommendation(summary_payload)
    recommendation_json_recommendation = live_mod.base_mod._safe_str(
        recommendation_payload.get("recommendation")
    )
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
    recommendation_values_match = int(
        recommendation_values_present and len(set(recommendation_values)) == 1
    )
    mismatched_seeds = [
        live_mod.base_mod._safe_int(row.get("search_seed"))
        for row in row_checks
        if live_mod.base_mod._safe_int(row.get("row_mismatch")) == 1
    ]
    completed_jobs = live_mod.base_mod._safe_int(state_payload.get("completed_jobs"))
    planned_jobs = live_mod.base_mod._safe_int(state_payload.get("planned_jobs"))
    bundle_complete = int(
        state_payload.get("status") == "completed"
        and completed_jobs == planned_jobs
        and completed_jobs == 1
        and len(row_checks) == 1
    )
    return {
        "run_label": RUN_LABEL,
        "source_bundle_dir": _relative_path(source_bundle_dir),
        "source_status": live_mod.base_mod._safe_str(state_payload.get("status")),
        "completed_jobs": completed_jobs,
        "planned_jobs": planned_jobs,
        "bundle_complete": int(bundle_complete),
        "state_recommendation": state_recommendation,
        "final_event_recommendation": event_recommendation,
        "summary_recomputed_recommendation": summary_recomputed_recommendation,
        "recommendation_json_recommendation": recommendation_json_recommendation,
        "readout_recommendation": readout_recommendation,
        "recommendation_values_present": int(recommendation_values_present),
        "missing_recommendation_layers": missing_recommendation_layers,
        "recommendation_values_match": int(recommendation_values_match),
        "row_mismatch_count": len(mismatched_seeds),
        "mismatched_search_seeds": mismatched_seeds,
        "observed_gate_verdict": summary_row.get("observed_gate_verdict", ""),
        "phaseA_best_init_match": summary_row.get("phaseA_best_init_match", ""),
        "action_stop_now": summary_row.get("action_stop_now", ""),
        "action_fallback_to_baseline": summary_row.get(
            "action_fallback_to_baseline", ""
        ),
        "fallback_target": summary_row.get("fallback_target", ""),
    }


def _build_recommendation(summary_row: Mapping[str, Any]) -> dict[str, Any]:
    clean = (
        live_mod.base_mod._safe_int(summary_row.get("bundle_complete")) == 1
        and live_mod.base_mod._safe_int(
            summary_row.get("recommendation_values_present")
        )
        == 1
        and live_mod.base_mod._safe_int(summary_row.get("recommendation_values_match"))
        == 1
        and live_mod.base_mod._safe_str(summary_row.get("state_recommendation"))
        == "advance"
        and live_mod.base_mod._safe_int(summary_row.get("row_mismatch_count")) == 0
    )
    if clean:
        return {
            "recommendation": "advance",
            "next_branch_label": "live_canary_review",
            "reason": (
                "The live-canary bundle is complete, all recommendation layers "
                "are present and advance, and row-level recomputation found "
                "zero mismatches."
            ),
        }
    return {
        "recommendation": "hold",
        "next_branch_label": "live_canary_harness_refine",
        "reason": (
            "The live-canary bundle is incomplete, recommendation layers are "
            "missing or split, or row-level recomputation found a mismatch."
        ),
    }


def _write_markdown(
    *,
    path: Path,
    summary_row: Mapping[str, Any],
    recommendation: Mapping[str, Any],
) -> None:
    missing_layers = list(summary_row.get("missing_recommendation_layers", []))
    missing_layer_text = ", ".join(str(item) for item in missing_layers) or "none"
    mismatched_seeds = list(summary_row.get("mismatched_search_seeds", []))
    mismatched_seed_text = ", ".join(str(item) for item in mismatched_seeds) or "none"
    lines = [
        READOUT_TITLE,
        "",
        "Recommendation:",
        f"- `{live_mod.base_mod._safe_str(recommendation.get('recommendation'))}`",
        (
            "- next branch: "
            f"`{live_mod.base_mod._safe_str(recommendation.get('next_branch_label'))}`"
        ),
        f"- reason: {live_mod.base_mod._safe_str(recommendation.get('reason'))}",
        "",
        "Source:",
        f"- bundle: `{summary_row.get('source_bundle_dir')}`",
        f"- status: `{summary_row.get('source_status')}`",
        f"- completed jobs: `{summary_row.get('completed_jobs')}` / `{summary_row.get('planned_jobs')}`",
        f"- bundle complete: `{summary_row.get('bundle_complete')}`",
        "",
        "Recommendation layers:",
        f"- state: `{summary_row.get('state_recommendation')}`",
        f"- final event: `{summary_row.get('final_event_recommendation')}`",
        f"- summary-derived: `{summary_row.get('summary_recomputed_recommendation')}`",
        f"- recommendation JSON: `{summary_row.get('recommendation_json_recommendation')}`",
        f"- readout: `{summary_row.get('readout_recommendation')}`",
        f"- values present: `{summary_row.get('recommendation_values_present')}`",
        f"- values match: `{summary_row.get('recommendation_values_match')}`",
        f"- missing layers: `{missing_layer_text}`",
        "",
        "Row recomputation:",
        f"- row mismatch count: `{summary_row.get('row_mismatch_count')}`",
        f"- mismatched seeds: `{mismatched_seed_text}`",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_audit() -> dict[str, Any]:
    source_bundle_dir = _resolve_source_bundle_dir()
    rows_csv = source_bundle_dir / f"{live_mod.FILE_STEM}_rows.csv"
    state_json = source_bundle_dir / "matrix_run_state.json"
    events_jsonl = source_bundle_dir / "matrix_run_events.jsonl"
    summary_json = source_bundle_dir / f"{live_mod.FILE_STEM}_summary.json"
    recommendation_json = (
        source_bundle_dir / f"{live_mod.FILE_STEM}_recommendation.json"
    )
    readout_md = source_bundle_dir / f"{live_mod.FILE_STEM}_readout.md"

    rows = _load_rows_csv(rows_csv)
    row_checks = [_build_row_check(row) for row in rows]
    state_payload = _load_json(state_json)
    final_event = _load_final_event(events_jsonl)
    summary_payload = _load_json(summary_json)
    recommendation_payload = _load_json(recommendation_json)
    readout_recommendation = _extract_readout_recommendation(
        readout_md.read_text(encoding="utf-8")
    )
    summary_row = _build_summary_row(
        row_checks=row_checks,
        summary_payload=summary_payload,
        state_payload=state_payload,
        final_event=final_event,
        recommendation_payload=recommendation_payload,
        readout_recommendation=readout_recommendation,
        source_bundle_dir=source_bundle_dir,
    )
    recommendation = _build_recommendation(summary_row)

    output_dir = (
        live_mod.base_mod.replay_mod.OUTPUT_BASE_DIR
        / f"{_utc_label()}__{RUN_LABEL}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    state_path = output_dir / "matrix_run_state.json"
    events_path = output_dir / "matrix_run_events.jsonl"
    rows_path = output_dir / f"{FILE_STEM}_rows.csv"
    summary_path = output_dir / f"{FILE_STEM}_summary.json"
    recommendation_path = output_dir / f"{FILE_STEM}_recommendation.json"
    readout_path = output_dir / f"{FILE_STEM}_readout.md"
    state = {
        "status": "completed",
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "source_bundle_dir": _relative_path(source_bundle_dir),
        "completed_jobs": 1,
        "planned_jobs": 1,
        "recommendation": recommendation,
        "created_at_utc": _utc_now_iso(),
    }
    _write_json(state_path, state)
    _append_jsonl(
        events_path,
        {
            "event": "run_started",
            "ts_utc": _utc_now_iso(),
            "source_bundle_dir": _relative_path(source_bundle_dir),
        },
    )
    _append_jsonl(
        events_path,
        {
            "event": "run_finished",
            "ts_utc": _utc_now_iso(),
            "status": "completed",
            "completed_jobs": 1,
            "recommendation": recommendation["recommendation"],
        },
    )
    _write_rows_csv(rows_path, row_checks)
    _write_json(
        summary_path,
        {"summary_row": summary_row, "output_dir": _relative_path(output_dir)},
    )
    _write_json(recommendation_path, recommendation)
    _write_markdown(
        path=readout_path,
        summary_row=summary_row,
        recommendation=recommendation,
    )
    refresh_catalog_safely(print_fn=print)
    return {
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "source_bundle_dir": _relative_path(source_bundle_dir),
        "summary_path": _relative_path(summary_path),
        "recommendation_path": _relative_path(recommendation_path),
        "rows_path": _relative_path(rows_path),
        "readout_path": _relative_path(readout_path),
        "recommendation": recommendation["recommendation"],
        "row_mismatch_count": summary_row["row_mismatch_count"],
        "recommendation_values_match": summary_row["recommendation_values_match"],
    }


def main() -> None:
    print(json.dumps(run_audit(), sort_keys=True))


if __name__ == "__main__":
    main()
