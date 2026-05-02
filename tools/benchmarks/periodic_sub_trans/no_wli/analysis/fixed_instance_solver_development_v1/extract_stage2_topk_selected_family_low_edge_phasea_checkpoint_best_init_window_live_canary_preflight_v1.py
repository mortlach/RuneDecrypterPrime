from __future__ import annotations

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
        "extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_preflight_v1.py"
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
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_preflight_v1"
)
FILE_STEM = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_preflight"
)
READOUT_TITLE = (
    "# Stage-2 Selected-Family Phase-A Checkpoint Live-Canary Preflight v1"
)
REQUIRED_RECOMMENDATION_LAYERS = (
    "state",
    "final_event",
    "summary_derived",
    "recommendation_json",
    "readout",
)
REQUIRED_PREFLIGHT_CHECKS = (
    "one_cell_only",
    "canary_seed_is_expected",
    "lane_role_is_expected",
    "lane_role_recognized",
    "expected_verdict_is_valid",
    "launch_guard_blocks_runtime",
    "contract_pinned",
    "decision_defers_before_restart32",
    "decision_matches_expected_at_restart32",
    "decision_fields_present",
    "reference_row_present",
    "reference_scores_present",
    "output_parent_ok",
    "audit_layers_declared",
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


def build_preflight_row(summary: Mapping[str, Any]) -> dict[str, Any]:
    search_seeds = list(summary.get("search_seeds", []))
    lane_role_by_seed = dict(summary.get("lane_role_by_seed", {}))
    expected_by_seed = dict(summary.get("expected_gate_verdict_by_seed", {}))
    expected_seed = int(live_mod.SEARCH_SEEDS[0])
    expected_lane_role = live_mod.LANE_ROLE_BY_SEED[expected_seed]
    expected_config_verdict = live_mod.EXPECTED_GATE_VERDICT_BY_SEED[expected_seed]
    lane_role = str(
        lane_role_by_seed.get(expected_seed)
        or lane_role_by_seed.get(str(expected_seed))
        or ""
    )
    expected_verdict = str(
        expected_by_seed.get(expected_seed) or expected_by_seed.get(str(expected_seed)) or ""
    )
    missing_decision_fields = list(summary.get("missing_decision_fields", []))
    reference_baseline = live_mod.base_mod._safe_float(
        summary.get("reference_baseline_best_match_ratio")
    )
    reference_selected = live_mod.base_mod._safe_float(
        summary.get("reference_resume_best_match_ratio")
    )
    audit_layers_declared = list(REQUIRED_RECOMMENDATION_LAYERS)

    row = {
        "run_label": live_mod.RUN_LABEL,
        "preflight_label": RUN_LABEL,
        "one_cell_only": int(search_seeds == [expected_seed]),
        "canary_seed_is_expected": int(search_seeds == [expected_seed]),
        "lane_role_is_expected": int(lane_role == expected_lane_role),
        "lane_role_recognized": int(
            lane_role in live_mod.base_mod.FILTERED_LANE_ROLES
            or lane_role in live_mod.base_mod.KEPT_LANE_ROLES
        ),
        "expected_verdict_is_valid": int(
            expected_verdict == expected_config_verdict
            and expected_verdict in {"filter", "keep"}
        ),
        "launch_guard_blocks_runtime": int(
            live_mod.base_mod._safe_int(summary.get("launch_approved")) == 0
        ),
        "contract_pinned": int(
            summary.get("rule_id") == live_mod.RULE_ID
            and live_mod.base_mod._safe_int(
                summary.get("window_start_restart_count")
            )
            == 32
            and live_mod.base_mod._approx_equal(
                live_mod.base_mod._safe_float(summary.get("best_init_threshold")),
                0.3865,
            )
            and summary.get("action_contract_id") == live_mod.ACTION_CONTRACT_ID
            and summary.get("action_contract_mode") == live_mod.ACTION_CONTRACT_MODE
        ),
        "decision_defers_before_restart32": live_mod.base_mod._safe_int(
            summary.get("defer_before_restart32")
        ),
        "decision_matches_expected_at_restart32": int(
            summary.get("checkpoint_decision_verdict") == expected_verdict
            and (
                (
                    expected_verdict == "filter"
                    and live_mod.base_mod._safe_int(
                        summary.get("checkpoint_decision_stop_now")
                    )
                    == 1
                    and live_mod.base_mod._safe_int(
                        summary.get("checkpoint_decision_fallback_to_baseline")
                    )
                    == 1
                    and summary.get("checkpoint_decision_fallback_target")
                    == "retained_baseline"
                )
                or (
                    expected_verdict == "keep"
                    and live_mod.base_mod._safe_int(
                        summary.get("checkpoint_decision_stop_now")
                    )
                    == 0
                    and live_mod.base_mod._safe_int(
                        summary.get("checkpoint_decision_fallback_to_baseline")
                    )
                    == 0
                    and summary.get("checkpoint_decision_fallback_target") == ""
                )
            )
        ),
        "decision_fields_present": int(not missing_decision_fields),
        "missing_decision_fields": missing_decision_fields,
        "reference_row_present": live_mod.base_mod._safe_int(
            summary.get("reference_row_present")
        ),
        "reference_scores_present": int(
            reference_baseline == reference_baseline
            and reference_selected == reference_selected
        ),
        "output_parent_ok": live_mod.base_mod._safe_int(
            summary.get("output_parent_ok")
        ),
        "audit_layers_declared": int(
            audit_layers_declared == list(REQUIRED_RECOMMENDATION_LAYERS)
        ),
        "required_recommendation_layers": audit_layers_declared,
    }
    row["failed_checks"] = [
        check_name
        for check_name in REQUIRED_PREFLIGHT_CHECKS
        if live_mod.base_mod._safe_int(row.get(check_name)) != 1
    ]
    row["preflight_checks_passed"] = int(not row["failed_checks"])
    return row


def build_recommendation(preflight_row: Mapping[str, Any]) -> dict[str, Any]:
    if live_mod.base_mod._safe_int(preflight_row.get("preflight_checks_passed")) == 1:
        return {
            "recommendation": "advance",
            "next_branch_label": "live_canary_launch_note",
            "reason": (
                "The one-cell live-canary harness is pinned to the reviewed "
                "contract, the launch guard is still blocking runtime, the "
                "decision surface emits required fields, and the audit layers "
                "are declared for post-run provenance checks."
            ),
        }
    return {
        "recommendation": "hold",
        "next_branch_label": "live_canary_harness_refine",
        "reason": (
            "The one-cell live-canary harness or audit surface is missing a "
            "required Day 2 preflight condition."
        ),
    }


def _write_markdown(
    *,
    path: Path,
    preflight_row: Mapping[str, Any],
    raw_summary: Mapping[str, Any],
    recommendation: Mapping[str, Any],
) -> None:
    failed_checks = list(preflight_row.get("failed_checks", []))
    failed_text = ", ".join(str(item) for item in failed_checks) or "none"
    missing_decision = list(preflight_row.get("missing_decision_fields", []))
    missing_decision_text = ", ".join(str(item) for item in missing_decision) or "none"
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
        "Canary contract:",
        f"- search seeds: `{raw_summary.get('search_seeds')}`",
        f"- lane roles: `{raw_summary.get('lane_role_by_seed')}`",
        f"- expected verdicts: `{raw_summary.get('expected_gate_verdict_by_seed')}`",
        f"- rule id: `{raw_summary.get('rule_id')}`",
        f"- restart count: `{raw_summary.get('window_start_restart_count')}`",
        f"- best-init threshold: `{raw_summary.get('best_init_threshold')}`",
        f"- launch guard approved: `{raw_summary.get('launch_approved')}`",
        "",
        "Checks:",
        f"- preflight checks passed: `{preflight_row.get('preflight_checks_passed')}`",
        f"- failed checks: `{failed_text}`",
        f"- missing decision fields: `{missing_decision_text}`",
        f"- output parent ok: `{preflight_row.get('output_parent_ok')}`",
        f"- required recommendation layers: `{', '.join(REQUIRED_RECOMMENDATION_LAYERS)}`",
        "",
        "Runtime boundary:",
        "- this preflight did not launch the live canary",
        "- live runtime remains blocked until a separate accepted launch note",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_preflight() -> dict[str, Any]:
    raw_summary = live_mod.build_preflight_summary()
    preflight_row = build_preflight_row(raw_summary)
    recommendation = build_recommendation(preflight_row)

    output_dir = (
        live_mod.base_mod.replay_mod.OUTPUT_BASE_DIR
        / f"{_utc_label()}__{RUN_LABEL}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    state_path = output_dir / "matrix_run_state.json"
    events_path = output_dir / "matrix_run_events.jsonl"
    summary_path = output_dir / f"{FILE_STEM}_summary.json"
    recommendation_path = output_dir / f"{FILE_STEM}_recommendation.json"
    readout_path = output_dir / f"{FILE_STEM}_readout.md"

    state_payload = {
        "status": "completed",
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "completed_jobs": 1,
        "planned_jobs": 1,
        "recommendation": recommendation,
        "live_runtime_launched": 0,
        "created_at_utc": _utc_now_iso(),
    }
    _write_json(state_path, state_payload)
    _append_jsonl(
        events_path,
        {
            "event": "run_started",
            "ts_utc": _utc_now_iso(),
            "output_dir": _relative_path(output_dir),
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
    _write_json(
        summary_path,
        {
            "summary_row": preflight_row,
            "raw_harness_summary": raw_summary,
            "output_dir": _relative_path(output_dir),
        },
    )
    _write_json(recommendation_path, recommendation)
    _write_markdown(
        path=readout_path,
        preflight_row=preflight_row,
        raw_summary=raw_summary,
        recommendation=recommendation,
    )
    refresh_catalog_safely(print_fn=print)
    return {
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "summary_path": _relative_path(summary_path),
        "recommendation_path": _relative_path(recommendation_path),
        "readout_path": _relative_path(readout_path),
        "recommendation": recommendation["recommendation"],
        "failed_checks": preflight_row["failed_checks"],
    }


def main() -> None:
    print(json.dumps(run_preflight(), sort_keys=True))


if __name__ == "__main__":
    main()
