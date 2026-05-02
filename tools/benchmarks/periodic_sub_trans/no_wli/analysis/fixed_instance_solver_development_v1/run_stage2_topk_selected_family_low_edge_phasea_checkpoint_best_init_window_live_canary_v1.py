from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from time import monotonic
from typing import Any, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1.py"
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
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1"
)
FILE_STEM = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary"
)
READOUT_TITLE = (
    "# Stage-2 Selected-Family Phase-A Checkpoint Best-Init Window Live Canary v1"
)
MECHANISM_LAYER = "selection / local rescue"
LIVE_CANARY_LAUNCH_APPROVED = False
FIXTURE_SEED = 1111
SEARCH_SEEDS = (7003,)
LANE_ROLE_BY_SEED = {7003: "kept_family"}
EXPECTED_GATE_VERDICT_BY_SEED = {7003: "keep"}
SELECTOR_ID = "selected_family_low_edge_eps_0p016_v1"
FAMILY_VIEW_ID = "prefix_hamming_le_24"
RULE_ID = action_mod.RULE_ID
WINDOW_START_RESTART_COUNT = action_mod.WINDOW_START_RESTART_COUNT
BEST_INIT_THRESHOLD = action_mod.BEST_INIT_THRESHOLD
ACTION_CONTRACT_ID = action_mod.ACTION_CONTRACT_ID
ACTION_CONTRACT_MODE = action_mod.ACTION_CONTRACT_MODE
INTENDED_WALLCLOCK_BUDGET_HOURS = 8.0
MAX_WALLCLOCK_SECONDS = INTENDED_WALLCLOCK_BUDGET_HOURS * 3600.0
NEXT_BRANCH_ADVANCE_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_review"
)
NEXT_BRANCH_REFINE_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_harness_refine"
)
QUESTION = (
    "Can the reviewed restart32 phaseA_best_init_match checkpoint be observed "
    "and audited safely in one live canary, without changing the rule or "
    "widening the claim?"
)
SUSPICION = (
    "Kept 7003 should show phaseA_best_init_match at or above 0.3865 at "
    "restart32, trigger keep with no action, preserve the selected-family "
    "path, and remain no-harm relative to the retained exact replay."
)
MAIN_ALTERNATIVE = (
    "The replay checkpoint may be too fitted to the retained fixed family, or "
    "the live evidence surface may be too incomplete for action decisions."
)
DECISION_RULE = (
    "Advance only if all required checkpoint fields and artefact layers are "
    "present, the decision recomputes at restart32, the action outcome matches "
    "the expected keep/filter contract, row recomputation has zero mismatches, "
    "and all recommendation layers agree. Otherwise hold."
)
STOP_CONDITION = (
    "Run exactly one kept/no-harm canary with an 08:00:00 cap. Stop and hold if "
    "the run exceeds the cap without usable checkpoint evidence."
)
REQUIRED_DECISION_FIELDS = (
    "action_decision_id",
    "action_contract_id",
    "action_contract_mode",
    "rule_id",
    "window_start_restart_count",
    "threshold",
    "phaseA_best_init_match",
    "gate_verdict",
    "expected_gate_verdict",
    "action_reason",
    "action_stop_now",
    "action_fallback_to_baseline",
    "fallback_target",
    "resume_best_stage",
    "resume_best_match_ratio",
)
REQUIRED_ROW_FIELDS = (
    "run_id",
    "fixture_seed",
    "search_seed",
    "lane_role",
    "selector_id",
    "family_view_id",
    "observed_gate_verdict",
    "expected_gate_verdict",
    "phasea_gate_action_applied",
    "gate_checkpoint_restart_count",
    "phaseA_best_init_match",
    "best_init_threshold",
    "action_decision_id",
    "action_stop_now",
    "action_fallback_to_baseline",
    "fallback_target",
    "current_resume_best_match_ratio",
    "baseline_best_match_ratio",
    "reference_resume_best_match_ratio",
    "delta_vs_baseline",
    "delta_vs_reference_candidate",
    "actual_saved_attempt_seconds",
    "actual_saved_attempt_share",
    "action_behaved_as_expected",
)


def _relative_path(path: Path) -> str:
    return base_mod._relative_path(path)


def _build_phasea_provisional_gate_action_decider(
    *,
    reference_row: Mapping[str, Any],
    expected_gate_verdict: str,
) -> Any:
    baseline_best_match_ratio = base_mod._safe_float(
        reference_row.get("baseline_best_match_ratio")
    )
    baseline_best_stage = base_mod._safe_str(reference_row.get("baseline_best_stage"))

    def _decider(snapshot: Mapping[str, Any]) -> dict[str, Any]:
        checkpoint_count = base_mod._safe_int(
            snapshot.get("phaseA_checkpoint_restart_count")
        )
        if checkpoint_count < int(WINDOW_START_RESTART_COUNT):
            return {}
        best_value = base_mod._safe_float(snapshot.get("phaseA_best_init_match"))
        gate_verdict = (
            "keep" if best_value >= float(BEST_INIT_THRESHOLD) else "filter"
        )
        action_stop_now = int(gate_verdict == "filter")
        return {
            "action_decision_id": (
                f"{RULE_ID}:restart{checkpoint_count}:{gate_verdict}"
            ),
            "action_contract_id": ACTION_CONTRACT_ID,
            "action_contract_mode": ACTION_CONTRACT_MODE,
            "rule_id": RULE_ID,
            "window_start_restart_count": int(WINDOW_START_RESTART_COUNT),
            "threshold": float(BEST_INIT_THRESHOLD),
            "best_init_threshold": float(BEST_INIT_THRESHOLD),
            "best_init_match": float(best_value),
            "phaseA_best_init_match": float(best_value),
            "gate_verdict": str(gate_verdict),
            "expected_gate_verdict": str(expected_gate_verdict),
            "trigger_source": (
                "best_init_window_keep"
                if gate_verdict == "keep"
                else "best_init_window_filter"
            ),
            "action_reason": (
                "best_init_window_keep_restart32"
                if gate_verdict == "keep"
                else "best_init_window_filter_restart32"
            ),
            "action_stop_now": int(action_stop_now),
            "action_fallback_to_baseline": int(action_stop_now),
            "fallback_target": (
                "retained_baseline" if action_stop_now else ""
            ),
            "resume_best_stage": (
                str(baseline_best_stage) if action_stop_now else ""
            ),
            "resume_best_match_ratio": (
                float(baseline_best_match_ratio) if action_stop_now else float("nan")
            ),
            "resume_best_score": float("nan"),
        }

    return _decider


def _build_child_run_label(search_seed: int) -> str:
    return (
        "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_"
        f"live_canary_exact_replay_1111_search{int(search_seed)}_v1"
    )


def _build_child_scope_note(search_seed: int) -> str:
    return (
        "one-cell live canary wires the reviewed restart32 best-init checkpoint "
        "rule as no-action keep on kept 1111/search7003; the run tests evidence "
        "capture and selected-path preservation, not threshold tuning or broad "
        "runtime reopening"
    )


def _load_reference_row(search_seed: int) -> dict[str, Any]:
    original_search_seeds = tuple(base_mod.SEARCH_SEEDS)
    try:
        base_mod.SEARCH_SEEDS = tuple(SEARCH_SEEDS)
        rows = base_mod._load_reference_rows()
    finally:
        base_mod.SEARCH_SEEDS = original_search_seeds
    return dict(rows[int(search_seed)])


def _action_row_from_output(
    *,
    output_dir: Path,
    expected_gate_verdict: str,
) -> dict[str, Any]:
    progress_rows = base_mod._parse_progress_rows(
        output_dir / "resume_bundle" / "stage3_resume_progress.jsonl"
    )
    applied_row = base_mod._select_progress_row(
        progress_rows=progress_rows,
        event_name="stage3_phasea_gate_action_applied",
        expected_gate_verdict=expected_gate_verdict,
    )
    decision_row = base_mod._select_progress_row(
        progress_rows=progress_rows,
        event_name="stage3_phasea_gate_action_decision",
        expected_gate_verdict=expected_gate_verdict,
    )
    return dict(applied_row or decision_row)


def _build_row_from_child_output(
    *,
    search_seed: int,
    child_output_dir_relpath: str,
    reference_row: Mapping[str, Any],
) -> dict[str, Any]:
    original_search_seeds = tuple(base_mod.SEARCH_SEEDS)
    original_lane_roles = dict(base_mod.LANE_ROLE_BY_SEED)
    original_expected_verdicts = dict(base_mod.EXPECTED_GATE_VERDICT_BY_SEED)
    try:
        base_mod.SEARCH_SEEDS = tuple(SEARCH_SEEDS)
        base_mod.LANE_ROLE_BY_SEED = dict(LANE_ROLE_BY_SEED)
        base_mod.EXPECTED_GATE_VERDICT_BY_SEED = dict(
            EXPECTED_GATE_VERDICT_BY_SEED
        )
        base_row = base_mod._build_row_from_child_output(
            search_seed=int(search_seed),
            child_output_dir_relpath=child_output_dir_relpath,
            reference_row=reference_row,
        )
    finally:
        base_mod.SEARCH_SEEDS = original_search_seeds
        base_mod.LANE_ROLE_BY_SEED = original_lane_roles
        base_mod.EXPECTED_GATE_VERDICT_BY_SEED = original_expected_verdicts
    output_dir = REPO_ROOT / Path(child_output_dir_relpath)
    attempt_status = base_mod._load_json(output_dir / "attempt_status.json")
    selector_summary = base_mod._load_json(
        output_dir / "selected_family_low_edge_exact_replay_summary.json"
    )
    expected_gate_verdict = base_mod._safe_str(
        EXPECTED_GATE_VERDICT_BY_SEED.get(int(search_seed))
    )
    action_row = _action_row_from_output(
        output_dir=output_dir,
        expected_gate_verdict=expected_gate_verdict,
    )
    row = dict(base_row)
    row.update(
        {
            "run_id": base_mod._safe_str(attempt_status.get("run_label"))
            or _build_child_run_label(search_seed),
            "fixture_seed": int(FIXTURE_SEED),
            "selector_id": base_mod._safe_str(
                selector_summary.get("candidate_policy_id")
            )
            or SELECTOR_ID,
            "family_view_id": base_mod._safe_str(selector_summary.get("family_view_id"))
            or FAMILY_VIEW_ID,
            "action_decision_id": base_mod._safe_str(
                action_row.get("action_decision_id")
            ),
            "action_stop_now": base_mod._safe_int(action_row.get("action_stop_now")),
            "action_fallback_to_baseline": base_mod._safe_int(
                action_row.get("action_fallback_to_baseline")
            ),
            "fallback_target": base_mod._safe_str(action_row.get("fallback_target")),
            "phaseA_best_init_match": base_mod._safe_float(
                action_row.get("phaseA_best_init_match", action_row.get("best_init_match"))
            ),
            "best_init_threshold": base_mod._safe_float(
                action_row.get("best_init_threshold", action_row.get("threshold"))
            ),
        }
    )
    row["action_behaved_as_expected"] = base_mod._action_behaved_as_expected_for_role(
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
    return row


def _missing_required_row_fields(row: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    expected_gate_verdict = base_mod._safe_str(row.get("expected_gate_verdict"))
    for field_name in REQUIRED_ROW_FIELDS:
        value = row.get(field_name)
        if expected_gate_verdict == "keep" and field_name == "fallback_target":
            continue
        if value is None or value == "":
            missing.append(field_name)
            continue
        if isinstance(value, float) and not math.isfinite(value):
            missing.append(field_name)
    return missing


def _summary_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row = dict(rows[0]) if rows else {}
    missing_fields = _missing_required_row_fields(row) if row else list(REQUIRED_ROW_FIELDS)
    return {
        "rule_id": RULE_ID,
        "selector_id": SELECTOR_ID,
        "family_view_id": FAMILY_VIEW_ID,
        "action_contract_id": ACTION_CONTRACT_ID,
        "action_contract_mode": ACTION_CONTRACT_MODE,
        "completed_run_count": int(len(rows)),
        "planned_run_count": int(len(SEARCH_SEEDS)),
        "search_seed": base_mod._safe_int(row.get("search_seed")),
        "lane_role": base_mod._safe_str(row.get("lane_role")),
        "observed_gate_verdict": base_mod._safe_str(row.get("observed_gate_verdict")),
        "expected_gate_verdict": base_mod._safe_str(row.get("expected_gate_verdict")),
        "phasea_gate_action_applied": base_mod._safe_int(
            row.get("phasea_gate_action_applied")
        ),
        "action_stop_now": base_mod._safe_int(row.get("action_stop_now")),
        "action_fallback_to_baseline": base_mod._safe_int(
            row.get("action_fallback_to_baseline")
        ),
        "fallback_target": base_mod._safe_str(row.get("fallback_target")),
        "gate_checkpoint_restart_count": base_mod._safe_int(
            row.get("gate_checkpoint_restart_count")
        ),
        "phaseA_best_init_match": base_mod._safe_float(
            row.get("phaseA_best_init_match")
        ),
        "best_init_threshold": base_mod._safe_float(row.get("best_init_threshold")),
        "actual_saved_attempt_seconds": base_mod._safe_float(
            row.get("actual_saved_attempt_seconds")
        ),
        "actual_saved_attempt_share": base_mod._safe_float(
            row.get("actual_saved_attempt_share")
        ),
        "delta_vs_baseline": base_mod._safe_float(row.get("delta_vs_baseline")),
        "delta_vs_reference_candidate": base_mod._safe_float(
            row.get("delta_vs_reference_candidate")
        ),
        "action_behaved_as_expected": base_mod._safe_int(
            row.get("action_behaved_as_expected")
        ),
        "missing_required_row_fields": missing_fields,
        "required_row_fields_present": int(not missing_fields),
    }


def _build_recommendation(summary_row: Mapping[str, Any]) -> dict[str, Any]:
    missing_fields = list(summary_row.get("missing_required_row_fields", []))
    expected_verdict = base_mod._safe_str(summary_row.get("expected_gate_verdict"))
    observed_verdict = base_mod._safe_str(summary_row.get("observed_gate_verdict"))
    filter_contract_clean = (
        expected_verdict == "filter"
        and observed_verdict == "filter"
        and base_mod._safe_int(summary_row.get("phasea_gate_action_applied")) == 1
        and base_mod._safe_int(summary_row.get("action_stop_now")) == 1
        and base_mod._safe_int(summary_row.get("action_fallback_to_baseline")) == 1
        and base_mod._safe_str(summary_row.get("fallback_target")) == "retained_baseline"
        and base_mod._safe_float(summary_row.get("phaseA_best_init_match"))
        < float(BEST_INIT_THRESHOLD)
    )
    keep_contract_clean = (
        expected_verdict == "keep"
        and observed_verdict == "keep"
        and base_mod._safe_int(summary_row.get("phasea_gate_action_applied")) == 0
        and base_mod._safe_int(summary_row.get("action_stop_now")) == 0
        and base_mod._safe_int(summary_row.get("action_fallback_to_baseline")) == 0
        and base_mod._safe_str(summary_row.get("fallback_target")) == ""
        and base_mod._safe_float(summary_row.get("phaseA_best_init_match"))
        >= float(BEST_INIT_THRESHOLD)
    )
    clean = (
        base_mod._safe_int(summary_row.get("completed_run_count")) == len(SEARCH_SEEDS)
        and not missing_fields
        and base_mod._safe_int(summary_row.get("gate_checkpoint_restart_count")) == 32
        and (filter_contract_clean or keep_contract_clean)
        and base_mod._safe_int(summary_row.get("action_behaved_as_expected")) == 1
    )
    if clean:
        return {
            "recommendation": "advance",
            "next_branch_label": NEXT_BRANCH_ADVANCE_LABEL,
            "reason": (
                "The one-cell live canary produced a complete restart32 "
                f"{expected_verdict} decision and the action outcome matched "
                "the canary contract."
            ),
        }
    return {
        "recommendation": "hold",
        "next_branch_label": NEXT_BRANCH_REFINE_LABEL,
        "reason": (
            "The one-cell live canary is missing required evidence, did not "
            "produce the expected keep/filter action, or did not preserve the "
            "action contract cleanly."
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
    row = dict(rows[0]) if rows else {}
    missing_fields = summary_row.get("missing_required_row_fields", [])
    missing_text = ", ".join(str(item) for item in missing_fields) or "none"
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
        f"- completed runs: `{base_mod._safe_int(summary_row.get('completed_run_count'))}` / `{len(SEARCH_SEEDS)}`",
        f"- search seed: `{base_mod._safe_int(summary_row.get('search_seed'))}`",
        f"- lane role: `{base_mod._safe_str(summary_row.get('lane_role'))}`",
        f"- observed verdict: `{base_mod._safe_str(summary_row.get('observed_gate_verdict'))}`",
        f"- expected verdict: `{base_mod._safe_str(summary_row.get('expected_gate_verdict'))}`",
        f"- checkpoint restart: `{base_mod._safe_int(summary_row.get('gate_checkpoint_restart_count'))}`",
        f"- phaseA best-init match: `{base_mod._safe_float(summary_row.get('phaseA_best_init_match')):.3f}`",
        f"- threshold: `{base_mod._safe_float(summary_row.get('best_init_threshold')):.4f}`",
        f"- action applied: `{base_mod._safe_int(summary_row.get('phasea_gate_action_applied'))}`",
        f"- stop now: `{base_mod._safe_int(summary_row.get('action_stop_now'))}`",
        f"- fallback to baseline: `{base_mod._safe_int(summary_row.get('action_fallback_to_baseline'))}`",
        f"- fallback target: `{base_mod._safe_str(summary_row.get('fallback_target'))}`",
        f"- saved attempt seconds: `{base_mod._safe_float(summary_row.get('actual_saved_attempt_seconds')):.1f}`",
        f"- saved attempt share: `{base_mod._safe_float(summary_row.get('actual_saved_attempt_share')):.3f}`",
        f"- required row fields present: `{base_mod._safe_int(summary_row.get('required_row_fields_present'))}`",
        f"- missing required row fields: `{missing_text}`",
        f"- final status: `{base_mod._safe_str(state_payload.get('status'))}`",
        "",
        "Per-canary read:",
        f"- `search{base_mod._safe_int(row.get('search_seed'))}` / `{base_mod._safe_str(row.get('lane_role'))}`",
        f"  - selector `{base_mod._safe_str(row.get('selector_id'))}`",
        f"  - family view `{base_mod._safe_str(row.get('family_view_id'))}`",
        f"  - action decision `{base_mod._safe_str(row.get('action_decision_id'))}`",
        f"  - current/baseline `{base_mod._safe_float(row.get('current_resume_best_match_ratio')):.3f}` / `{base_mod._safe_float(row.get('baseline_best_match_ratio')):.3f}`",
        f"  - behaved as expected `{base_mod._safe_int(row.get('action_behaved_as_expected'))}`",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_rows_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        base_mod._append_jsonl(path, row)


def build_preflight_summary() -> dict[str, Any]:
    search_seed = int(SEARCH_SEEDS[0])
    expected_gate_verdict = base_mod._safe_str(
        EXPECTED_GATE_VERDICT_BY_SEED.get(search_seed)
    )
    probe_best_init = 0.490 if expected_gate_verdict == "keep" else 0.378
    reference_row = _load_reference_row(search_seed)
    decider = _build_phasea_provisional_gate_action_decider(
        reference_row=reference_row,
        expected_gate_verdict=expected_gate_verdict,
    )
    defer_decision = decider(
        {
            "phaseA_checkpoint_restart_count": 16,
            "phaseA_best_init_match": probe_best_init,
        }
    )
    checkpoint_decision = decider(
        {
            "phaseA_checkpoint_restart_count": 32,
            "phaseA_checkpoint_elapsed_seconds": 1.0,
            "phaseA_checkpoint_fraction": 0.25,
            "phaseA_best_init_match": probe_best_init,
        }
    )
    missing_decision_fields = [
        field_name
        for field_name in REQUIRED_DECISION_FIELDS
        if not (
            expected_gate_verdict == "keep"
            and field_name
            in {"fallback_target", "resume_best_stage", "resume_best_match_ratio"}
        )
        and checkpoint_decision.get(field_name) in (None, "")
    ]
    output_base_dir = base_mod.replay_mod.OUTPUT_BASE_DIR
    output_parent_ok = (
        output_base_dir.resolve().is_relative_to(REPO_ROOT.resolve())
        and output_base_dir.parent.exists()
    )
    return {
        "run_label": RUN_LABEL,
        "launch_approved": int(LIVE_CANARY_LAUNCH_APPROVED),
        "fixture_seed": int(FIXTURE_SEED),
        "search_seeds": list(SEARCH_SEEDS),
        "lane_role_by_seed": dict(LANE_ROLE_BY_SEED),
        "expected_gate_verdict_by_seed": dict(EXPECTED_GATE_VERDICT_BY_SEED),
        "selector_id": SELECTOR_ID,
        "family_view_id": FAMILY_VIEW_ID,
        "rule_id": RULE_ID,
        "window_start_restart_count": int(WINDOW_START_RESTART_COUNT),
        "best_init_threshold": float(BEST_INIT_THRESHOLD),
        "action_contract_id": ACTION_CONTRACT_ID,
        "action_contract_mode": ACTION_CONTRACT_MODE,
        "budget_hours": float(INTENDED_WALLCLOCK_BUDGET_HOURS),
        "defer_before_restart32": int(defer_decision == {}),
        "checkpoint_decision_verdict": base_mod._safe_str(
            checkpoint_decision.get("gate_verdict")
        ),
        "checkpoint_decision_stop_now": base_mod._safe_int(
            checkpoint_decision.get("action_stop_now")
        ),
        "checkpoint_decision_fallback_to_baseline": base_mod._safe_int(
            checkpoint_decision.get("action_fallback_to_baseline")
        ),
        "checkpoint_decision_fallback_target": base_mod._safe_str(
            checkpoint_decision.get("fallback_target")
        ),
        "missing_decision_fields": missing_decision_fields,
        "reference_matrix_rows_csv": _relative_path(base_mod.REFERENCE_MATRIX_ROWS_CSV),
        "reference_row_present": int(bool(reference_row)),
        "reference_baseline_best_match_ratio": base_mod._safe_float(
            reference_row.get("baseline_best_match_ratio")
        ),
        "reference_resume_best_match_ratio": base_mod._safe_float(
            reference_row.get("reference_resume_best_match_ratio")
        ),
        "required_row_fields": list(REQUIRED_ROW_FIELDS),
        "output_base_dir": _relative_path(output_base_dir),
        "output_parent_ok": int(output_parent_ok),
    }


def run_live_canary() -> dict[str, Any]:
    if not LIVE_CANARY_LAUNCH_APPROVED:
        return build_launch_blocked_payload()

    started = monotonic()
    started_at_utc = base_mod._utc_now_iso()
    output_dir = base_mod.replay_mod.OUTPUT_BASE_DIR / f"{base_mod._utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    state_path = output_dir / "matrix_run_state.json"
    events_path = output_dir / "matrix_run_events.jsonl"
    rows_csv_path = output_dir / f"{FILE_STEM}_rows.csv"
    rows_jsonl_path = output_dir / f"{FILE_STEM}_rows.jsonl"
    summary_path = output_dir / f"{FILE_STEM}_summary.json"
    recommendation_path = output_dir / f"{FILE_STEM}_recommendation.json"
    readout_path = output_dir / f"{FILE_STEM}_readout.md"
    state_payload: dict[str, Any] = {
        "status": "running",
        "started_at_utc": started_at_utc,
        "updated_at_utc": started_at_utc,
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "mechanism_layer": MECHANISM_LAYER,
        "question": QUESTION,
        "suspicion": SUSPICION,
        "main_alternative": MAIN_ALTERNATIVE,
        "decision_rule": DECISION_RULE,
        "stop_condition": STOP_CONDITION,
        "planned_jobs": len(SEARCH_SEEDS),
        "completed_jobs": 0,
        "budget_hours": INTENDED_WALLCLOCK_BUDGET_HOURS,
        "reference_matrix_bundle": _relative_path(base_mod.REFERENCE_MATRIX_BUNDLE_DIR),
    }
    base_mod._write_json(state_path, state_payload)
    base_mod._append_jsonl(
        events_path,
        {
            "event": "run_started",
            "ts_utc": base_mod._utc_now_iso(),
            "output_dir": _relative_path(output_dir),
            "planned_jobs": len(SEARCH_SEEDS),
            "budget_hours": INTENDED_WALLCLOCK_BUDGET_HOURS,
            "rule_id": RULE_ID,
        },
    )
    base_mod._print_progress(
        "run_started "
        f"label={RUN_LABEL} output_dir={_relative_path(output_dir)} "
        f"units={len(SEARCH_SEEDS)} budget={base_mod._format_duration(MAX_WALLCLOCK_SECONDS)} "
        f"rule_id={RULE_ID}"
    )

    rows: list[dict[str, Any]] = []
    for index, search_seed in enumerate(SEARCH_SEEDS, start=1):
        lane_role = base_mod._safe_str(LANE_ROLE_BY_SEED.get(int(search_seed)))
        expected_gate_verdict = base_mod._safe_str(
            EXPECTED_GATE_VERDICT_BY_SEED.get(int(search_seed))
        )
        reference_row = _load_reference_row(int(search_seed))
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
        child_run_summary = base_mod.replay_mod.run_verification(
            search_seed=int(search_seed),
            run_label=_build_child_run_label(search_seed),
            phasea_provisional_gate_action_decider=(
                _build_phasea_provisional_gate_action_decider(
                    reference_row=reference_row,
                    expected_gate_verdict=expected_gate_verdict,
                )
            ),
            scope_note_override=_build_child_scope_note(search_seed),
        )
        row = _build_row_from_child_output(
            search_seed=int(search_seed),
            child_output_dir_relpath=base_mod._safe_str(child_run_summary.get("output_dir")),
            reference_row=reference_row,
        )
        rows.append(row)
        state_payload.update(
            {
                "status": "running",
                "updated_at_utc": base_mod._utc_now_iso(),
                "completed_jobs": len(rows),
                "latest_completed_search_seed": int(search_seed),
                "latest_completed_output_dir": base_mod._safe_str(row.get("output_dir")),
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

    summary_row = _summary_row(rows)
    recommendation = _build_recommendation(summary_row)
    base_mod._write_rows_csv(rows_csv_path, rows)
    _write_rows_jsonl(rows_jsonl_path, rows)
    base_mod._write_json(
        summary_path,
        {"summary_row": summary_row, "output_dir": _relative_path(output_dir)},
    )
    base_mod._write_json(recommendation_path, recommendation)

    elapsed_seconds = float(monotonic() - started)
    final_status = "completed"
    state_payload.update(
        {
            "status": final_status,
            "updated_at_utc": base_mod._utc_now_iso(),
            "elapsed_seconds": float(elapsed_seconds),
            "elapsed": base_mod._format_duration(elapsed_seconds),
            "completed_jobs": len(rows),
            "summary_json": _relative_path(summary_path),
            "recommendation_json": _relative_path(recommendation_path),
            "rows_csv": _relative_path(rows_csv_path),
            "rows_jsonl": _relative_path(rows_jsonl_path),
            "readout_md": _relative_path(readout_path),
            "recommendation": dict(recommendation),
        }
    )
    _write_markdown(
        path=readout_path,
        rows=rows,
        summary_row=summary_row,
        recommendation=recommendation,
        state_payload=state_payload,
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
    refresh_catalog_safely(print_fn=print)
    base_mod._print_progress(
        "run_finished "
        f"label={RUN_LABEL} status={final_status} "
        f"completed_jobs={len(rows)}/{len(SEARCH_SEEDS)} "
        f"elapsed={base_mod._format_duration(elapsed_seconds)} "
        f"recommendation={base_mod._safe_str(recommendation.get('recommendation'))} "
        f"output_dir={_relative_path(output_dir)}"
    )
    return {
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "state_path": _relative_path(state_path),
        "summary_path": _relative_path(summary_path),
        "recommendation_path": _relative_path(recommendation_path),
        "rows_csv_path": _relative_path(rows_csv_path),
        "completed_jobs": len(rows),
        "recommendation": base_mod._safe_str(recommendation.get("recommendation")),
    }


def build_launch_blocked_payload() -> dict[str, Any]:
    return {
        "run_label": RUN_LABEL,
        "status": "launch_blocked",
        "recommendation": "hold",
        "reason": (
            "LIVE_CANARY_LAUNCH_APPROVED is false. Run the Day 2 preflight "
            "and record an accepted launch note before editing the hardcoded "
            "guard for a separate PowerShell launch."
        ),
        "search_seeds": list(SEARCH_SEEDS),
        "budget_hours": float(INTENDED_WALLCLOCK_BUDGET_HOURS),
        "rule_id": RULE_ID,
        "window_start_restart_count": int(WINDOW_START_RESTART_COUNT),
        "best_init_threshold": float(BEST_INIT_THRESHOLD),
    }


def main() -> None:
    print(json.dumps(run_live_canary(), sort_keys=True))


if __name__ == "__main__":
    main()
