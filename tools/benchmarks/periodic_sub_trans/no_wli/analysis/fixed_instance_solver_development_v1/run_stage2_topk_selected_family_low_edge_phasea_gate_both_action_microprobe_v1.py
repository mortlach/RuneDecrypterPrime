from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
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
        "run_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1.py"
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
    verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004 as replay_mod,
)


RUN_LABEL = "stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1"
MECHANISM_LAYER = "selection"
FIXTURE_SEED = 1111
SEARCH_SEEDS = (7002, 7003)
LANE_ROLE_BY_SEED = {
    7002: "filtered_canary",
    7003: "kept_canary",
}
EXPECTED_GATE_VERDICT_BY_SEED = {
    7002: "filter",
    7003: "keep",
}
GATE_ID = "rank1_init_ge_0p30"
GATE_METRIC = "phaseA_rank1_init_match"
GATE_THRESHOLD = 0.30
ACTION_CONTRACT_ID = "phasea_rank1_gate_both_v1"
ACTION_CONTRACT_MODE = "fallback_and_early_stop"
INTENDED_WALLCLOCK_BUDGET_HOURS = 1.0
MAX_WALLCLOCK_SECONDS = INTENDED_WALLCLOCK_BUDGET_HOURS * 3600.0
REFERENCE_MATRIX_BUNDLE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
    / "20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1"
)
REFERENCE_MATRIX_ROWS_CSV = (
    REFERENCE_MATRIX_BUNDLE_DIR
    / "selected_family_low_edge_exact_replay_1111_matrix_rows.csv"
)
NEXT_BRANCH_LATE_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_gate_earlier_emission_microprobe"
)
NEXT_BRANCH_READY_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_gate_both_action_family_microbatch"
)
QUESTION = (
    "If the validated Phase-A rank-1 gate is wired as both fallback and early "
    "stop at the live decision point, does one filtered 1111 lane save real "
    "wallclock while one kept 1111 lane preserves the no-harm / positive exact "
    "read?"
)
SUSPICION = (
    "The filtered lane 7002 should stop immediately at the gate and fall back "
    "to the retained baseline, while the kept lane 7003 should continue and "
    "reproduce the prior clean positive exact replay."
)
MAIN_ALTERNATIVE = (
    "The gate may still be too late to save useful wallclock, or the keep path "
    "may perturb the previously trusted positive lane enough that the first "
    "action contract is not yet honest."
)
IF_SUSPICION_TRUE_EXPECT = (
    "7002 should emit a filter verdict, apply the fallback-and-stop contract, "
    "land at the retained baseline, and finish faster than its prior exact "
    "candidate replay; 7003 should emit keep, apply no stop, and reproduce its "
    "prior exact replay outcome."
)
IF_ALTERNATIVE_TRUE_EXPECT = (
    "7002 may fail to save time or may miss the fallback target, or 7003 may "
    "show harm relative to its prior exact replay, which would keep the branch "
    "in action refinement."
)
DECISION_RULE = (
    "Advance only if the filtered canary applies the both-action contract "
    "cleanly and the kept canary stays no-harm relative to the prior exact "
    "replay. If correctness passes but saved wallclock is still small because "
    "the verdict arrives late, refine toward earlier emission rather than a "
    "wider action batch."
)
STOP_CONDITION = (
    "This microbatch is budgeted from the completed exact replay anchors on the "
    "same selector family: 7002 took about 00:22:13 and 7003 took about "
    "00:21:54, for an anchored two-job total of about 00:44:08. After the "
    "first completed canary, recompute the projected two-job total from the "
    "observed completed row plus the remaining retained anchor. If that "
    "projection exceeds the 01:00:00 session budget, stop before launching the "
    "second canary."
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


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_str(value: Any) -> str:
    return str(value or "")


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(float(seconds))))
    hours, rem = divmod(total_seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True))
        handle.write("\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_utc_timestamp(value: str) -> datetime:
    return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )


def _print_progress(message: str) -> None:
    print(f"[{_utc_now_iso()}] {message}", flush=True)


def _mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return float("nan")
    return float(sum(finite) / float(len(finite)))


def _approx_equal(lhs: float, rhs: float, *, tol: float = 1.0e-9) -> bool:
    if not math.isfinite(lhs) or not math.isfinite(rhs):
        return False
    return abs(float(lhs) - float(rhs)) <= float(tol)


def _load_reference_rows() -> dict[int, dict[str, Any]]:
    rows = list(csv.DictReader(REFERENCE_MATRIX_ROWS_CSV.open(encoding="utf-8")))
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        search_seed = _safe_int(row.get("search_seed"))
        if search_seed not in SEARCH_SEEDS:
            continue
        output_dir = REPO_ROOT / Path(_safe_str(row.get("output_dir")))
        attempt_status = _load_json(output_dir / "attempt_status.json")
        summary = _load_json(output_dir / "selected_family_low_edge_exact_replay_summary.json")
        out[search_seed] = dict(
            search_seed=int(search_seed),
            output_dir=_safe_str(row.get("output_dir")),
            reference_attempt_elapsed_seconds=_safe_float(
                attempt_status.get("elapsed_seconds")
            ),
            baseline_best_match_ratio=_safe_float(
                row.get("baseline_best_match_ratio")
            ),
            retained_stage3_reference_match_ratio=_safe_float(
                row.get("retained_stage3_reference_match_ratio")
            ),
            reference_resume_best_match_ratio=_safe_float(
                row.get("resume_best_match_ratio")
            ),
            reference_match_delta_vs_baseline=_safe_float(
                row.get("match_delta_vs_baseline")
            ),
            reference_resume_best_stage=_safe_str(row.get("resume_best_stage")),
            reference_resume_source=_safe_str(row.get("resume_source")),
            baseline_best_stage=_safe_str(summary.get("baseline_best_stage")),
            candidate_truth_delta_vs_baseline_row=_safe_float(
                row.get("candidate_truth_delta_vs_baseline_row")
            ),
        )
    missing = [seed for seed in SEARCH_SEEDS if seed not in out]
    if missing:
        raise RuntimeError(f"Missing reference rows for seeds: {missing}")
    return out


def _anchored_total_seconds(reference_rows: Mapping[int, Mapping[str, Any]]) -> float:
    return float(
        sum(
            _safe_float(reference_rows[int(seed)]["reference_attempt_elapsed_seconds"])
            for seed in SEARCH_SEEDS
        )
    )


def _remaining_anchor_seconds(
    *,
    completed_seeds: list[int],
    reference_rows: Mapping[int, Mapping[str, Any]],
) -> float:
    return float(
        sum(
            _safe_float(reference_rows[int(seed)]["reference_attempt_elapsed_seconds"])
            for seed in SEARCH_SEEDS
            if int(seed) not in set(int(item) for item in completed_seeds)
        )
    )


def _project_total_seconds(
    *,
    completed_rows: list[Mapping[str, Any]],
    reference_rows: Mapping[int, Mapping[str, Any]],
) -> float:
    completed_elapsed = sum(
        _safe_float(row.get("elapsed_seconds"))
        for row in completed_rows
        if math.isfinite(_safe_float(row.get("elapsed_seconds")))
    )
    completed_seeds = [_safe_int(row.get("search_seed")) for row in completed_rows]
    return float(
        completed_elapsed
        + _remaining_anchor_seconds(
            completed_seeds=completed_seeds,
            reference_rows=reference_rows,
        )
    )


def _gate_verdict_from_metric(gate_metric_value: float) -> str:
    if not math.isfinite(gate_metric_value):
        return "unknown"
    if float(gate_metric_value) >= float(GATE_THRESHOLD):
        return "keep"
    return "filter"


def _build_phasea_gate_action_decider(
    *,
    reference_row: Mapping[str, Any],
    expected_gate_verdict: str,
) -> Any:
    baseline_best_match_ratio = _safe_float(reference_row.get("baseline_best_match_ratio"))
    baseline_best_stage = _safe_str(reference_row.get("baseline_best_stage"))

    def _decider(snapshot: Mapping[str, Any]) -> dict[str, Any]:
        gate_metric_value = _safe_float(snapshot.get(GATE_METRIC))
        gate_verdict = _gate_verdict_from_metric(gate_metric_value)
        action_stop_now = int(1 if gate_verdict == "filter" else 0)
        return {
            "action_contract_id": ACTION_CONTRACT_ID,
            "action_contract_mode": ACTION_CONTRACT_MODE,
            "gate_id": GATE_ID,
            "gate_metric_name": GATE_METRIC,
            "gate_threshold": float(GATE_THRESHOLD),
            "gate_metric_value": float(gate_metric_value),
            "gate_verdict": str(gate_verdict),
            "expected_gate_verdict": str(expected_gate_verdict),
            "action_reason": (
                "gate_filter_below_threshold"
                if gate_verdict == "filter"
                else (
                    "gate_keep_meets_threshold"
                    if gate_verdict == "keep"
                    else "gate_metric_unusable"
                )
            ),
            "action_stop_now": int(action_stop_now),
            "action_fallback_to_baseline": int(action_stop_now),
            "resume_best_stage": (
                str(baseline_best_stage) if action_stop_now else ""
            ),
            "resume_best_match_ratio": (
                float(baseline_best_match_ratio)
                if action_stop_now
                else float("nan")
            ),
            "resume_best_score": float("nan"),
        }

    return _decider


def _build_child_run_label(search_seed: int) -> str:
    return (
        "stage2_topk_selected_family_low_edge_phasea_gate_both_action_exact_replay_"
        f"1111_search{int(search_seed)}_v1"
    )


def _build_child_scope_note(search_seed: int) -> str:
    lane_role = _safe_str(LANE_ROLE_BY_SEED.get(int(search_seed)))
    if lane_role == "filtered_canary":
        return (
            "exact retained replay wires the validated Phase-A gate as both "
            "fallback and early stop on the filtered 1111 canary so the read "
            "measures actual saved wallclock rather than a shadow estimate"
        )
    return (
        "exact retained replay wires the validated Phase-A gate as both "
        "fallback and early stop on the kept 1111 canary so the read checks "
        "that the keep path stays no-harm relative to the prior exact replay"
    )


def _build_row_from_child_output(
    *,
    search_seed: int,
    child_output_dir_relpath: str,
    reference_row: Mapping[str, Any],
) -> dict[str, Any]:
    output_dir = REPO_ROOT / Path(child_output_dir_relpath)
    attempt_status = _load_json(output_dir / "attempt_status.json")
    run_summary = _load_json(output_dir / "run_summary.json")
    selector_summary = _load_json(
        output_dir / "selected_family_low_edge_exact_replay_summary.json"
    )
    resume_status = _load_json(output_dir / "resume_bundle" / "stage3_resume_status.json")
    snapshot_relpath = _safe_str(attempt_status.get("phasea_gate_snapshot_json_relpath"))
    snapshot_path = REPO_ROOT / Path(snapshot_relpath) if snapshot_relpath else Path()
    snapshot_exists = bool(snapshot_relpath) and snapshot_path.exists()
    snapshot_payload = _load_json(snapshot_path) if snapshot_exists else {}
    started_at_utc = _safe_str(attempt_status.get("started_at_utc"))
    snapshot_ts = _safe_str(snapshot_payload.get("ts_utc"))
    snapshot_elapsed_seconds = float("nan")
    if started_at_utc and snapshot_ts:
        snapshot_elapsed_seconds = (
            _parse_utc_timestamp(snapshot_ts) - _parse_utc_timestamp(started_at_utc)
        ).total_seconds()
    total_elapsed_seconds = _safe_float(attempt_status.get("elapsed_seconds"))
    snapshot_elapsed_share = float("nan")
    if (
        math.isfinite(snapshot_elapsed_seconds)
        and math.isfinite(total_elapsed_seconds)
        and total_elapsed_seconds > 0.0
    ):
        snapshot_elapsed_share = snapshot_elapsed_seconds / total_elapsed_seconds

    decision_row = dict(
        (resume_status.get("latest_phasea_gate_action_decision") or {})
    )
    applied_row = dict((resume_status.get("latest_phasea_gate_action_applied") or {}))
    observed_gate_metric_value = _safe_float(
        decision_row.get("gate_metric_value", snapshot_payload.get(GATE_METRIC))
    )
    observed_gate_verdict = _safe_str(
        decision_row.get("gate_verdict")
        or applied_row.get("gate_verdict")
        or _gate_verdict_from_metric(observed_gate_metric_value)
    )
    action_applied = _safe_int(
        attempt_status.get(
            "phasea_gate_action_applied",
            selector_summary.get("phasea_gate_action_applied"),
        )
    )
    reference_attempt_elapsed_seconds = _safe_float(
        reference_row.get("reference_attempt_elapsed_seconds")
    )
    actual_saved_attempt_seconds = float("nan")
    actual_saved_attempt_share = float("nan")
    if (
        math.isfinite(reference_attempt_elapsed_seconds)
        and math.isfinite(total_elapsed_seconds)
        and reference_attempt_elapsed_seconds > 0.0
    ):
        actual_saved_attempt_seconds = (
            reference_attempt_elapsed_seconds - total_elapsed_seconds
        )
        actual_saved_attempt_share = (
            actual_saved_attempt_seconds / reference_attempt_elapsed_seconds
        )
    baseline_best_match_ratio = _safe_float(reference_row.get("baseline_best_match_ratio"))
    reference_resume_best_match_ratio = _safe_float(
        reference_row.get("reference_resume_best_match_ratio")
    )
    current_resume_best_match_ratio = _safe_float(
        run_summary.get("resume_best_match_ratio")
    )
    delta_vs_reference_candidate = (
        current_resume_best_match_ratio - reference_resume_best_match_ratio
    )
    lane_role = _safe_str(LANE_ROLE_BY_SEED.get(int(search_seed)))
    expected_gate_verdict = _safe_str(
        EXPECTED_GATE_VERDICT_BY_SEED.get(int(search_seed))
    )
    if lane_role == "filtered_canary":
        action_behaved_as_expected = int(
            1
            if (
                observed_gate_verdict == expected_gate_verdict
                and action_applied == 1
                and _approx_equal(
                    current_resume_best_match_ratio,
                    baseline_best_match_ratio,
                )
            )
            else 0
        )
    else:
        action_behaved_as_expected = int(
            1
            if (
                observed_gate_verdict == expected_gate_verdict
                and action_applied == 0
                and _approx_equal(
                    current_resume_best_match_ratio,
                    reference_resume_best_match_ratio,
                )
            )
            else 0
        )
    return {
        "search_seed": int(search_seed),
        "lane_role": lane_role,
        "status": _safe_str(attempt_status.get("status")),
        "output_dir": child_output_dir_relpath,
        "elapsed_seconds": float(total_elapsed_seconds),
        "elapsed": _safe_str(attempt_status.get("elapsed")),
        "reference_attempt_elapsed_seconds": float(reference_attempt_elapsed_seconds),
        "actual_saved_attempt_seconds": float(actual_saved_attempt_seconds),
        "actual_saved_attempt_share": float(actual_saved_attempt_share),
        "baseline_best_match_ratio": float(baseline_best_match_ratio),
        "reference_resume_best_match_ratio": float(reference_resume_best_match_ratio),
        "current_resume_best_match_ratio": float(current_resume_best_match_ratio),
        "delta_vs_reference_candidate": float(delta_vs_reference_candidate),
        "delta_vs_baseline": _safe_float(run_summary.get("match_delta_vs_baseline")),
        "candidate_truth_delta_vs_baseline_row": _safe_float(
            selector_summary.get("candidate_truth_delta_vs_baseline_row")
        ),
        "phasea_gate_snapshot_present": int(1 if snapshot_exists else 0),
        "phasea_gate_snapshot_elapsed_seconds": float(snapshot_elapsed_seconds),
        "phasea_gate_snapshot_elapsed_share": float(snapshot_elapsed_share),
        "phasea_gate_action_decision_written": _safe_int(
            resume_status.get("phasea_gate_action_decision_written")
        ),
        "phasea_gate_action_applied": int(action_applied),
        "gate_metric_name": GATE_METRIC,
        "gate_metric_value": float(observed_gate_metric_value),
        "observed_gate_verdict": observed_gate_verdict,
        "expected_gate_verdict": expected_gate_verdict,
        "action_contract_id": _safe_str(
            attempt_status.get(
                "phasea_gate_action_contract_id",
                selector_summary.get("phasea_gate_action_contract_id"),
            )
        ),
        "action_contract_mode": _safe_str(
            attempt_status.get(
                "phasea_gate_action_mode",
                selector_summary.get("phasea_gate_action_mode"),
            )
        ),
        "action_reason": _safe_str(
            attempt_status.get(
                "phasea_gate_action_reason",
                selector_summary.get("phasea_gate_action_reason"),
            )
            or decision_row.get("action_reason")
            or applied_row.get("action_reason")
        ),
        "action_behaved_as_expected": int(action_behaved_as_expected),
    }


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Refusing to write empty action microprobe rows")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _build_summary_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    filtered_row = next(
        (dict(row) for row in rows if _safe_str(row.get("lane_role")) == "filtered_canary"),
        {},
    )
    kept_row = next(
        (dict(row) for row in rows if _safe_str(row.get("lane_role")) == "kept_canary"),
        {},
    )
    return {
        "action_contract_id": ACTION_CONTRACT_ID,
        "action_contract_mode": ACTION_CONTRACT_MODE,
        "gate_id": GATE_ID,
        "gate_metric_name": GATE_METRIC,
        "gate_threshold": float(GATE_THRESHOLD),
        "completed_run_count": int(len(rows)),
        "filtered_canary_search_seed": _safe_int(filtered_row.get("search_seed")),
        "filtered_canary_gate_verdict": _safe_str(filtered_row.get("observed_gate_verdict")),
        "filtered_canary_action_applied": _safe_int(
            filtered_row.get("phasea_gate_action_applied")
        ),
        "filtered_canary_saved_attempt_seconds": _safe_float(
            filtered_row.get("actual_saved_attempt_seconds")
        ),
        "filtered_canary_saved_attempt_share": _safe_float(
            filtered_row.get("actual_saved_attempt_share")
        ),
        "filtered_canary_behaved_as_expected": _safe_int(
            filtered_row.get("action_behaved_as_expected")
        ),
        "kept_canary_search_seed": _safe_int(kept_row.get("search_seed")),
        "kept_canary_gate_verdict": _safe_str(kept_row.get("observed_gate_verdict")),
        "kept_canary_action_applied": _safe_int(
            kept_row.get("phasea_gate_action_applied")
        ),
        "kept_canary_delta_vs_reference_candidate": _safe_float(
            kept_row.get("delta_vs_reference_candidate")
        ),
        "kept_canary_behaved_as_expected": _safe_int(
            kept_row.get("action_behaved_as_expected")
        ),
        "mean_gate_snapshot_elapsed_share": _mean(
            [_safe_float(row.get("phasea_gate_snapshot_elapsed_share")) for row in rows]
        ),
    }


def _build_recommendation(summary_row: Mapping[str, Any]) -> dict[str, Any]:
    filtered_ok = _safe_int(summary_row.get("filtered_canary_behaved_as_expected")) == 1
    kept_ok = _safe_int(summary_row.get("kept_canary_behaved_as_expected")) == 1
    filtered_saved_attempt_share = _safe_float(
        summary_row.get("filtered_canary_saved_attempt_share")
    )
    if filtered_ok and kept_ok:
        if filtered_saved_attempt_share >= 0.25:
            return {
                "recommendation": "advance",
                "next_branch_label": NEXT_BRANCH_READY_LABEL,
                "reason": (
                    "The both-action contract behaved correctly on the filtered and "
                    "kept canaries, and the filtered lane already saved material "
                    "wallclock."
                ),
            }
        return {
            "recommendation": "refine",
            "next_branch_label": NEXT_BRANCH_LATE_LABEL,
            "reason": (
                "The both-action contract behaved correctly on both canaries, but "
                "the filtered lane still saved only a small share of wallclock, so "
                "the next honest step is earlier verdict emission rather than a "
                "wider action batch."
            ),
        }
    return {
        "recommendation": "hold",
        "next_branch_label": "",
        "reason": (
            "At least one canary failed the first both-action correctness contract, "
            "so the branch should not widen yet."
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
        "# Stage-2 Topk Selected-Family Low-Edge Phase-A Gate Both-Action Microprobe v1",
        "",
        "Question:",
        f"- {QUESTION}",
        "",
        "Mechanism layer:",
        f"- `{MECHANISM_LAYER}`",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- next branch: `{_safe_str(recommendation.get('next_branch_label')) or 'none'}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Summary:",
        f"- completed runs: `{_safe_int(summary_row.get('completed_run_count'))}` / `{len(SEARCH_SEEDS)}`",
        f"- filtered canary: `search{_safe_int(summary_row.get('filtered_canary_search_seed'))}` / verdict `{_safe_str(summary_row.get('filtered_canary_gate_verdict'))}` / action applied `{_safe_int(summary_row.get('filtered_canary_action_applied'))}`",
        f"- filtered saved attempt seconds: `{_safe_float(summary_row.get('filtered_canary_saved_attempt_seconds')):.1f}`",
        f"- filtered saved attempt share: `{_safe_float(summary_row.get('filtered_canary_saved_attempt_share')):.3f}`",
        f"- kept canary: `search{_safe_int(summary_row.get('kept_canary_search_seed'))}` / verdict `{_safe_str(summary_row.get('kept_canary_gate_verdict'))}` / action applied `{_safe_int(summary_row.get('kept_canary_action_applied'))}`",
        f"- kept delta vs prior exact replay: `{_safe_float(summary_row.get('kept_canary_delta_vs_reference_candidate')):.3f}`",
        f"- mean gate snapshot share: `{_safe_float(summary_row.get('mean_gate_snapshot_elapsed_share')):.3f}`",
        f"- final status: `{_safe_str(state_payload.get('status'))}`",
        "",
        "Per-canary read:",
    ]
    for row in rows:
        lines.extend(
            [
                f"- `search{_safe_int(row.get('search_seed'))}` / `{_safe_str(row.get('lane_role'))}`",
                f"  - observed gate verdict `{_safe_str(row.get('observed_gate_verdict'))}`",
                f"  - expected gate verdict `{_safe_str(row.get('expected_gate_verdict'))}`",
                f"  - action applied `{_safe_int(row.get('phasea_gate_action_applied'))}`",
                f"  - elapsed `{_safe_str(row.get('elapsed'))}`",
                f"  - saved attempt seconds `{_safe_float(row.get('actual_saved_attempt_seconds')):.1f}`",
                f"  - delta vs prior exact replay `{_safe_float(row.get('delta_vs_reference_candidate')):.3f}`",
                f"  - behaved as expected `{_safe_int(row.get('action_behaved_as_expected'))}`",
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_microprobe() -> dict[str, Any]:
    started = monotonic()
    started_at_utc = _utc_now_iso()
    reference_rows = _load_reference_rows()
    output_dir = replay_mod.OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    state_path = output_dir / "matrix_run_state.json"
    events_path = output_dir / "matrix_run_events.jsonl"
    rows_csv_path = output_dir / "stage2_topk_selected_family_low_edge_phasea_gate_both_action_rows.csv"
    rows_jsonl_path = output_dir / "stage2_topk_selected_family_low_edge_phasea_gate_both_action_rows.jsonl"
    summary_path = output_dir / "stage2_topk_selected_family_low_edge_phasea_gate_both_action_summary.json"
    recommendation_path = output_dir / "stage2_topk_selected_family_low_edge_phasea_gate_both_action_recommendation.json"
    readout_path = output_dir / "stage2_topk_selected_family_low_edge_phasea_gate_both_action_readout.md"
    anchored_total_seconds = _anchored_total_seconds(reference_rows)
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
        "if_suspicion_true_expect": IF_SUSPICION_TRUE_EXPECT,
        "if_alternative_true_expect": IF_ALTERNATIVE_TRUE_EXPECT,
        "decision_rule": DECISION_RULE,
        "stop_condition": STOP_CONDITION,
        "planned_jobs": len(SEARCH_SEEDS),
        "completed_jobs": 0,
        "budget_hours": INTENDED_WALLCLOCK_BUDGET_HOURS,
        "anchored_total_elapsed": _format_duration(anchored_total_seconds),
        "reference_matrix_bundle": _relative_path(REFERENCE_MATRIX_BUNDLE_DIR),
    }
    _write_json(state_path, state_payload)
    _append_jsonl(
        events_path,
        {
            "event": "run_started",
            "ts_utc": _utc_now_iso(),
            "output_dir": _relative_path(output_dir),
            "planned_jobs": len(SEARCH_SEEDS),
            "budget_hours": INTENDED_WALLCLOCK_BUDGET_HOURS,
            "anchored_total_elapsed": _format_duration(anchored_total_seconds),
        },
    )
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"output_dir={_relative_path(output_dir)} "
        f"units={len(SEARCH_SEEDS)} "
        f"budget={_format_duration(MAX_WALLCLOCK_SECONDS)} "
        f"anchored_total={_format_duration(anchored_total_seconds)}"
    )

    rows: list[dict[str, Any]] = []
    for index, search_seed in enumerate(SEARCH_SEEDS, start=1):
        projected_total_seconds = _project_total_seconds(
            completed_rows=rows,
            reference_rows=reference_rows,
        )
        if projected_total_seconds > float(MAX_WALLCLOCK_SECONDS):
            state_payload.update(
                {
                    "status": "stopped_over_budget",
                    "updated_at_utc": _utc_now_iso(),
                    "projected_total_seconds": float(projected_total_seconds),
                    "projected_total_elapsed": _format_duration(projected_total_seconds),
                    "completed_jobs": len(rows),
                }
            )
            _write_json(state_path, state_payload)
            _print_progress(
                "run_stopped_over_budget "
                f"completed={len(rows)}/{len(SEARCH_SEEDS)} "
                f"projected_total={_format_duration(projected_total_seconds)} "
                f"budget={_format_duration(MAX_WALLCLOCK_SECONDS)}"
            )
            break

        lane_role = _safe_str(LANE_ROLE_BY_SEED.get(int(search_seed)))
        expected_gate_verdict = _safe_str(
            EXPECTED_GATE_VERDICT_BY_SEED.get(int(search_seed))
        )
        _append_jsonl(
            events_path,
            {
                "event": "job_started",
                "ts_utc": _utc_now_iso(),
                "unit": int(index),
                "units": len(SEARCH_SEEDS),
                "search_seed": int(search_seed),
                "lane_role": lane_role,
                "expected_gate_verdict": expected_gate_verdict,
            },
        )
        _print_progress(
            "job_started "
            f"unit={index}/{len(SEARCH_SEEDS)} "
            f"search_seed={search_seed} "
            f"lane_role={lane_role} "
            f"expected_gate_verdict={expected_gate_verdict}"
        )
        reference_row = reference_rows[int(search_seed)]
        child_run_summary = replay_mod.run_verification(
            search_seed=int(search_seed),
            run_label=_build_child_run_label(search_seed),
            phasea_gate_action_decider=_build_phasea_gate_action_decider(
                reference_row=reference_row,
                expected_gate_verdict=expected_gate_verdict,
            ),
            scope_note_override=_build_child_scope_note(search_seed),
        )
        row = _build_row_from_child_output(
            search_seed=int(search_seed),
            child_output_dir_relpath=_safe_str(child_run_summary.get("output_dir")),
            reference_row=reference_row,
        )
        rows.append(row)
        _append_jsonl(rows_jsonl_path, row)
        projected_total_seconds = _project_total_seconds(
            completed_rows=rows,
            reference_rows=reference_rows,
        )
        remaining_eta_seconds = max(
            0.0,
            projected_total_seconds
            - sum(
                _safe_float(item.get("elapsed_seconds"))
                for item in rows
                if math.isfinite(_safe_float(item.get("elapsed_seconds")))
            ),
        )
        state_payload.update(
            {
                "status": "running",
                "updated_at_utc": _utc_now_iso(),
                "completed_jobs": len(rows),
                "latest_completed_search_seed": int(search_seed),
                "latest_completed_output_dir": _safe_str(row.get("output_dir")),
                "projected_total_seconds": float(projected_total_seconds),
                "projected_total_elapsed": _format_duration(projected_total_seconds),
            }
        )
        _write_json(state_path, state_payload)
        _append_jsonl(
            events_path,
            {
                "event": "job_finished",
                "ts_utc": _utc_now_iso(),
                "unit": int(index),
                "units": len(SEARCH_SEEDS),
                "search_seed": int(search_seed),
                "lane_role": lane_role,
                "observed_gate_verdict": _safe_str(row.get("observed_gate_verdict")),
                "action_applied": _safe_int(row.get("phasea_gate_action_applied")),
                "elapsed_seconds": _safe_float(row.get("elapsed_seconds")),
                "saved_attempt_seconds": _safe_float(
                    row.get("actual_saved_attempt_seconds")
                ),
            },
        )
        _print_progress(
            "job_finished "
            f"unit={index}/{len(SEARCH_SEEDS)} "
            f"search_seed={search_seed} "
            f"gate_verdict={_safe_str(row.get('observed_gate_verdict'))} "
            f"action_applied={_safe_int(row.get('phasea_gate_action_applied'))} "
            f"saved_attempt_seconds={_safe_float(row.get('actual_saved_attempt_seconds')):.1f} "
            f"elapsed={_safe_str(row.get('elapsed'))} "
            f"eta={_format_duration(remaining_eta_seconds)}"
        )

    summary_row = _build_summary_row(rows)
    recommendation = _build_recommendation(summary_row)
    _write_rows_csv(rows_csv_path, rows)
    _write_json(summary_path, {"summary_row": summary_row, "output_dir": _relative_path(output_dir)})
    _write_json(recommendation_path, recommendation)
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
        _safe_str(state_payload.get("status"))
        if _safe_str(state_payload.get("status")) == "stopped_over_budget"
        else "completed"
    )
    state_payload.update(
        {
            "status": final_status,
            "updated_at_utc": _utc_now_iso(),
            "elapsed_seconds": float(elapsed_seconds),
            "elapsed": _format_duration(elapsed_seconds),
            "completed_jobs": len(rows),
            "summary_json": _relative_path(summary_path),
            "recommendation_json": _relative_path(recommendation_path),
            "rows_csv": _relative_path(rows_csv_path),
            "rows_jsonl": _relative_path(rows_jsonl_path),
            "readout_md": _relative_path(readout_path),
            "recommendation": dict(recommendation),
        }
    )
    _write_json(state_path, state_payload)
    _append_jsonl(
        events_path,
        {
            "event": "run_finished",
            "ts_utc": _utc_now_iso(),
            "status": final_status,
            "completed_jobs": len(rows),
            "recommendation": _safe_str(recommendation.get("recommendation")),
            "elapsed_seconds": float(elapsed_seconds),
        },
    )
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} "
        f"status={final_status} "
        f"completed_jobs={len(rows)}/{len(SEARCH_SEEDS)} "
        f"elapsed={_format_duration(elapsed_seconds)} "
        f"recommendation={_safe_str(recommendation.get('recommendation'))} "
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
        "recommendation": _safe_str(recommendation.get("recommendation")),
    }


def main() -> None:
    print(json.dumps(run_microprobe(), sort_keys=True))


if __name__ == "__main__":
    main()
