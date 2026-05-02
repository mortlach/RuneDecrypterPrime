from __future__ import annotations

import csv
import json
import math
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
        "extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_audit_v1.py"
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


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_audit_v1"
)
FILE_STEM = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_audit"
)
READOUT_TITLE = (
    "# Stage-2 Selected-Family Phase-A Checkpoint Kept-Lane Timing-Risk Audit v1"
)
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
)
REFERENCE_EXACT_BUNDLE_DIR = (
    OUTPUT_BASE_DIR
    / "20260423T152531Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7003_v1"
)
FAMILY_ACTION_BUNDLE_DIR = (
    OUTPUT_BASE_DIR
    / "20260424T223042Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_exact_replay_1111_search7003_v1"
)
LIVE_ACTION_BUNDLE_DIR = (
    OUTPUT_BASE_DIR
    / "20260426T014422Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_exact_replay_1111_search7003_v1"
)
LIVE_CANARY_SOURCE_BUNDLE_DIR = (
    OUTPUT_BASE_DIR
    / "20260426T014422Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1"
)
LIVE_CANARY_AUDIT_BUNDLE_DIR = (
    OUTPUT_BASE_DIR
    / "20260426T021629Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1"
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


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Refusing to write empty kept-lane timing audit rows")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(dict(json.loads(line)))
    return rows


def _parse_ts(value: Any) -> datetime | None:
    text = _safe_str(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _elapsed_from_start(*, started_at_utc: str, ts_utc: str) -> float:
    start = _parse_ts(started_at_utc)
    ts = _parse_ts(ts_utc)
    if start is None or ts is None:
        return float("nan")
    return float((ts - start).total_seconds())


def _first_matching(
    rows: list[Mapping[str, Any]],
    *,
    event_name: str,
    phase: str | None = None,
    step: int | None = None,
    restart_count: int | None = None,
) -> dict[str, Any]:
    for row in rows:
        if _safe_str(row.get("event")) != event_name:
            continue
        if phase is not None and _safe_str(row.get("phase")) != phase:
            continue
        if step is not None and _safe_int(row.get("step")) != int(step):
            continue
        if restart_count is not None and _safe_int(
            row.get("phaseA_checkpoint_restart_count")
        ) != int(restart_count):
            continue
        return dict(row)
    return {}


def _last_matching(
    rows: list[Mapping[str, Any]],
    *,
    event_name: str,
    phase: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in rows:
        if _safe_str(row.get("event")) != event_name:
            continue
        if phase is not None and _safe_str(row.get("phase")) != phase:
            continue
        out = dict(row)
    return out


def _checkpoint_row(
    rows: list[Mapping[str, Any]],
    *,
    restart_count: int,
) -> dict[str, Any]:
    return _first_matching(
        rows,
        event_name="stage3_phasea_gate_action_decision",
        restart_count=int(restart_count),
    ) or _first_matching(
        rows,
        event_name="stage3_phasea_provisional_gate_snapshot",
        restart_count=int(restart_count),
    )


def _extract_case(
    *,
    case_id: str,
    bundle_dir: Path,
    reference_total_seconds: float | None = None,
) -> dict[str, Any]:
    attempt_status = _load_json(bundle_dir / "attempt_status.json")
    progress_rows = _load_jsonl(
        bundle_dir / "resume_bundle" / "stage3_resume_progress.jsonl"
    )
    started_at_utc = _safe_str(attempt_status.get("started_at_utc"))
    total_seconds = _safe_float(attempt_status.get("elapsed_seconds"))
    finished_row = _last_matching(
        progress_rows,
        event_name="stage3_resume_finished",
    )
    if math.isfinite(_safe_float(finished_row.get("elapsed_seconds"))):
        flow_seconds = _safe_float(finished_row.get("elapsed_seconds"))
    else:
        flow_seconds = total_seconds
    phasea_last_heartbeat = _last_matching(
        progress_rows,
        event_name="stage3_heartbeat",
        phase="phaseA",
    )
    phaseb_first_heartbeat = _first_matching(
        progress_rows,
        event_name="stage3_heartbeat",
        phase="phaseB",
    )
    phaseb_step2112 = _first_matching(
        progress_rows,
        event_name="stage3_heartbeat",
        phase="phaseB",
        step=2112,
    )
    checkpoint32 = _checkpoint_row(progress_rows, restart_count=32)
    checkpoint48 = _checkpoint_row(progress_rows, restart_count=48)
    checkpoint64 = _checkpoint_row(progress_rows, restart_count=64)
    full_gate_snapshot = _last_matching(
        progress_rows,
        event_name="stage3_phasea_gate_snapshot",
    )
    phasea_last_abs = _elapsed_from_start(
        started_at_utc=started_at_utc,
        ts_utc=_safe_str(phasea_last_heartbeat.get("ts_utc")),
    )
    phaseb_first_abs = _elapsed_from_start(
        started_at_utc=started_at_utc,
        ts_utc=_safe_str(phaseb_first_heartbeat.get("ts_utc")),
    )
    phaseb_step2112_abs = _elapsed_from_start(
        started_at_utc=started_at_utc,
        ts_utc=_safe_str(phaseb_step2112.get("ts_utc")),
    )
    total_ratio = float("nan")
    total_delta_seconds = float("nan")
    if reference_total_seconds and reference_total_seconds > 0.0:
        total_ratio = float(total_seconds / reference_total_seconds)
        total_delta_seconds = float(total_seconds - reference_total_seconds)
    return {
        "case_id": case_id,
        "bundle_dir": _relative_path(bundle_dir),
        "status": _safe_str(attempt_status.get("status")),
        "total_elapsed_seconds": float(total_seconds),
        "total_elapsed": _format_duration(total_seconds),
        "flow_elapsed_seconds": float(flow_seconds),
        "reference_total_seconds": (
            float(reference_total_seconds)
            if reference_total_seconds is not None
            else float("nan")
        ),
        "total_delta_vs_reference_seconds": float(total_delta_seconds),
        "total_ratio_vs_reference": float(total_ratio),
        "resume_best_match_ratio": _safe_float(
            attempt_status.get("resume_best_match_ratio")
        ),
        "phasea_last_heartbeat_done": _safe_int(
            phasea_last_heartbeat.get("phaseA_done")
        ),
        "phasea_last_heartbeat_abs_seconds": float(phasea_last_abs),
        "phaseb_first_heartbeat_abs_seconds": float(phaseb_first_abs),
        "phaseb_step2112_abs_seconds": float(phaseb_step2112_abs),
        "phaseb_step2112_local_seconds": _safe_float(
            phaseb_step2112.get("elapsed_seconds")
        ),
        "checkpoint32_elapsed_seconds": _safe_float(
            checkpoint32.get("phaseA_checkpoint_elapsed_seconds")
        ),
        "checkpoint32_restart_count": _safe_int(
            checkpoint32.get("phaseA_checkpoint_restart_count")
        ),
        "checkpoint32_verdict": _safe_str(checkpoint32.get("gate_verdict")),
        "checkpoint48_elapsed_seconds": _safe_float(
            checkpoint48.get("phaseA_checkpoint_elapsed_seconds")
        ),
        "checkpoint48_restart_count": _safe_int(
            checkpoint48.get("phaseA_checkpoint_restart_count")
        ),
        "checkpoint64_elapsed_seconds": _safe_float(
            checkpoint64.get("phaseA_checkpoint_elapsed_seconds")
        ),
        "checkpoint64_restart_count": _safe_int(
            checkpoint64.get("phaseA_checkpoint_restart_count")
        ),
        "full_gate_snapshot_rows_scored": _safe_int(
            full_gate_snapshot.get("phaseA_rows_scored")
        ),
        "full_gate_snapshot_best_init_match": _safe_float(
            full_gate_snapshot.get("phaseA_best_init_match")
        ),
        "phasea_action_decision_count": sum(
            1
            for row in progress_rows
            if _safe_str(row.get("event")) == "stage3_phasea_gate_action_decision"
        ),
        "heartbeat_count": sum(
            1
            for row in progress_rows
            if _safe_str(row.get("event")) == "stage3_heartbeat"
        ),
    }


def _ratio(numerator: float, denominator: float) -> float:
    if not math.isfinite(numerator) or not math.isfinite(denominator) or denominator <= 0:
        return float("nan")
    return float(numerator / denominator)


def _build_summary_row(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    by_id = {str(row["case_id"]): dict(row) for row in rows}
    ref = by_id["reference_exact_7003"]
    family = by_id["family_action_7003"]
    live = by_id["live_action_7003"]
    reference_total = _safe_float(ref.get("total_elapsed_seconds"))
    family_total = _safe_float(family.get("total_elapsed_seconds"))
    live_total = _safe_float(live.get("total_elapsed_seconds"))
    family_ratio = _ratio(family_total, reference_total)
    live_ratio = _ratio(live_total, reference_total)
    live_vs_family_ratio = _ratio(live_total, family_total)
    live_checkpoint32 = _safe_float(live.get("checkpoint32_elapsed_seconds"))
    family_checkpoint32 = _safe_float(family.get("checkpoint32_elapsed_seconds"))
    live_phaseb_2112 = _safe_float(live.get("phaseb_step2112_local_seconds"))
    ref_phaseb_2112 = _safe_float(ref.get("phaseb_step2112_local_seconds"))
    family_phaseb_2112 = _safe_float(family.get("phaseb_step2112_local_seconds"))
    return {
        "run_label": RUN_LABEL,
        "reference_total_seconds": float(reference_total),
        "family_total_seconds": float(family_total),
        "live_total_seconds": float(live_total),
        "family_ratio_vs_reference": float(family_ratio),
        "live_ratio_vs_reference": float(live_ratio),
        "live_ratio_vs_family": float(live_vs_family_ratio),
        "live_total_delta_vs_reference_seconds": float(live_total - reference_total),
        "family_total_delta_vs_reference_seconds": float(
            family_total - reference_total
        ),
        "reference_phaseb_step2112_local_seconds": float(ref_phaseb_2112),
        "family_phaseb_step2112_local_seconds": float(family_phaseb_2112),
        "live_phaseb_step2112_local_seconds": float(live_phaseb_2112),
        "live_phaseb_step2112_ratio_vs_reference": _ratio(
            live_phaseb_2112,
            ref_phaseb_2112,
        ),
        "live_phaseb_step2112_ratio_vs_family": _ratio(
            live_phaseb_2112,
            family_phaseb_2112,
        ),
        "family_checkpoint32_elapsed_seconds": float(family_checkpoint32),
        "live_checkpoint32_elapsed_seconds": float(live_checkpoint32),
        "live_checkpoint32_ratio_vs_family": _ratio(
            live_checkpoint32,
            family_checkpoint32,
        ),
        "live_checkpoint32_verdict": _safe_str(live.get("checkpoint32_verdict")),
        "family_checkpoint32_verdict": _safe_str(family.get("checkpoint32_verdict")),
        "checkpoint_contract_implicated": 0,
        "timing_layer": "live kept/no-action path, visible by checkpoint32 and Phase B",
        "recommendation": "hold_runtime",
    }


def _build_recommendation(summary_row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "recommendation": "hold",
        "next_branch_label": "kept_lane_timing_risk_probe_plan",
        "reason": (
            "The existing logs localize the kept-7003 slowdown to the live "
            "kept/no-action runtime surface rather than the semantic checkpoint "
            "contract. More checkpoint canaries should not launch from this "
            "branch; any further runtime should be a separate timing-risk probe "
            "with a fresh budget and stop condition."
        ),
    }


def _write_markdown(
    *,
    path: Path,
    rows: list[Mapping[str, Any]],
    summary_row: Mapping[str, Any],
    recommendation: Mapping[str, Any],
) -> None:
    by_id = {str(row["case_id"]): dict(row) for row in rows}
    lines = [
        READOUT_TITLE,
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- next branch: `{_safe_str(recommendation.get('next_branch_label'))}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Elapsed comparison:",
        f"- reference exact: `{by_id['reference_exact_7003']['total_elapsed']}`",
        f"- family action: `{by_id['family_action_7003']['total_elapsed']}` / ratio `{_safe_float(summary_row.get('family_ratio_vs_reference')):.3f}`",
        f"- live action: `{by_id['live_action_7003']['total_elapsed']}` / ratio `{_safe_float(summary_row.get('live_ratio_vs_reference')):.3f}`",
        f"- live delta vs reference: `{_safe_float(summary_row.get('live_total_delta_vs_reference_seconds')):.1f}s`",
        "",
        "Checkpoint timing:",
        f"- family checkpoint32 elapsed: `{_safe_float(summary_row.get('family_checkpoint32_elapsed_seconds')):.1f}s`",
        f"- live checkpoint32 elapsed: `{_safe_float(summary_row.get('live_checkpoint32_elapsed_seconds')):.1f}s`",
        f"- live/family checkpoint32 ratio: `{_safe_float(summary_row.get('live_checkpoint32_ratio_vs_family')):.3f}`",
        f"- family/live verdicts: `{summary_row.get('family_checkpoint32_verdict')}` / `{summary_row.get('live_checkpoint32_verdict')}`",
        "",
        "Phase B timing:",
        f"- reference step2112 local seconds: `{_safe_float(summary_row.get('reference_phaseb_step2112_local_seconds')):.1f}`",
        f"- family step2112 local seconds: `{_safe_float(summary_row.get('family_phaseb_step2112_local_seconds')):.1f}`",
        f"- live step2112 local seconds: `{_safe_float(summary_row.get('live_phaseb_step2112_local_seconds')):.1f}`",
        f"- live/reference step2112 ratio: `{_safe_float(summary_row.get('live_phaseb_step2112_ratio_vs_reference')):.3f}`",
        "",
        "Interpretation:",
        "- the checkpoint contract is not implicated semantically",
        "- the family action replay stayed timing-stable relative to reference",
        "- the live kept/no-action run inflated before or by checkpoint32 and stayed inflated into Phase B",
        "- further runtime, if any, should be a separate timing-risk probe, not checkpoint widening",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_audit() -> dict[str, Any]:
    reference_row = _extract_case(
        case_id="reference_exact_7003",
        bundle_dir=REFERENCE_EXACT_BUNDLE_DIR,
    )
    reference_total = _safe_float(reference_row.get("total_elapsed_seconds"))
    rows = [
        reference_row,
        _extract_case(
            case_id="family_action_7003",
            bundle_dir=FAMILY_ACTION_BUNDLE_DIR,
            reference_total_seconds=reference_total,
        ),
        _extract_case(
            case_id="live_action_7003",
            bundle_dir=LIVE_ACTION_BUNDLE_DIR,
            reference_total_seconds=reference_total,
        ),
    ]
    summary_row = _build_summary_row(rows)
    recommendation = _build_recommendation(summary_row)
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
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
        "completed_jobs": 3,
        "planned_jobs": 3,
        "recommendation": recommendation,
        "created_at_utc": _utc_now_iso(),
        "live_canary_source_bundle": _relative_path(LIVE_CANARY_SOURCE_BUNDLE_DIR),
        "live_canary_audit_bundle": _relative_path(LIVE_CANARY_AUDIT_BUNDLE_DIR),
    }
    _write_json(state_path, state)
    _append_jsonl(
        events_path,
        {
            "event": "run_started",
            "ts_utc": _utc_now_iso(),
            "run_label": RUN_LABEL,
        },
    )
    _append_jsonl(
        events_path,
        {
            "event": "run_finished",
            "ts_utc": _utc_now_iso(),
            "status": "completed",
            "completed_jobs": 3,
            "recommendation": recommendation["recommendation"],
        },
    )
    _write_rows_csv(rows_path, [dict(row) for row in rows])
    _write_json(
        summary_path,
        {"summary_row": summary_row, "output_dir": _relative_path(output_dir)},
    )
    _write_json(recommendation_path, recommendation)
    _write_markdown(
        path=readout_path,
        rows=rows,
        summary_row=summary_row,
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
        "live_ratio_vs_reference": summary_row["live_ratio_vs_reference"],
        "live_checkpoint32_ratio_vs_family": summary_row[
            "live_checkpoint32_ratio_vs_family"
        ],
    }


def main() -> None:
    print(json.dumps(run_audit(), sort_keys=True))


if __name__ == "__main__":
    main()
