from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1.py"
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
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_"
    "timing_postmortem_audit_v1"
)
QUESTION = (
    "After the restart32 best-init family microbatch passed semantically, what "
    "explains the kept 7004 wallclock inflation relative to its reference exact "
    "replays?"
)
SUSPICION = (
    "The 7004 slowdown should read as broad throughput loss across late Phase A "
    "and downstream search, not as a gate-logic or late-decision failure."
)
MAIN_ALTERNATIVE = (
    "The 7004 slowdown may still reflect a structural gate-action problem, such "
    "as repeated decision churn or a genuinely late keep decision."
)
DECISION_RULE = (
    "Advance only if the audit shows 7003 stays timing-stable under the same "
    "action wiring, 7004 decides keep early at restart32, and the extra "
    "wallclock on 7004 is already visible before and after the checkpoint. "
    "Otherwise refine."
)

RUN_SPECS: tuple[dict[str, str | int], ...] = (
    {
        "row_id": "7003_reference_exact",
        "search_seed": 7003,
        "run_role": "reference_exact",
        "relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260423T152531Z__stage2_topk_selected_family_low_edge_exact_replay_"
            "1111_search7003_v1"
        ),
    },
    {
        "row_id": "7003_family_microbatch",
        "search_seed": 7003,
        "run_role": "family_microbatch_keep",
        "relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260424T223042Z__stage2_topk_selected_family_low_edge_phasea_"
            "checkpoint_best_init_window_family_exact_replay_1111_search7003_v1"
        ),
    },
    {
        "row_id": "7004_reference_anchor",
        "search_seed": 7004,
        "run_role": "reference_exact_anchor",
        "relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260424T061020Z__stage2_topk_selected_family_low_edge_exact_replay_"
            "1111_search7004_v1"
        ),
    },
    {
        "row_id": "7004_reference_latest",
        "search_seed": 7004,
        "run_role": "reference_exact_latest",
        "relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260424T203709Z__stage2_topk_selected_family_low_edge_exact_replay_"
            "1111_search7004_v1"
        ),
    },
    {
        "row_id": "7004_family_microbatch",
        "search_seed": 7004,
        "run_role": "family_microbatch_keep",
        "relpath": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
            "fixed_instance_solver_development_v1/"
            "20260424T225245Z__stage2_topk_selected_family_low_edge_phasea_"
            "checkpoint_best_init_window_family_exact_replay_1111_search7004_v1"
        ),
    },
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_label() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _print_progress(message: str) -> None:
    print(f"[{_utc_now_iso()}] {message}", flush=True)


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return result if math.isfinite(result) else float("nan")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _append_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True))
            handle.write("\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _first_event(
    rows: Sequence[Mapping[str, Any]],
    *,
    event_name: str,
) -> dict[str, Any] | None:
    for row in rows:
        if _safe_str(row.get("event")) == event_name:
            return dict(row)
    return None


def _last_event(
    rows: Sequence[Mapping[str, Any]],
    *,
    event_name: str,
) -> dict[str, Any] | None:
    for row in reversed(rows):
        if _safe_str(row.get("event")) == event_name:
            return dict(row)
    return None


def _first_gate_decision(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if _safe_str(row.get("event")) == "stage3_phasea_gate_action_decision":
            return dict(row)
    return None


def _event_count(rows: Sequence[Mapping[str, Any]], *, event_name: str) -> int:
    return sum(1 for row in rows if _safe_str(row.get("event")) == event_name)


def _phaseb_step_heartbeat(
    rows: Sequence[Mapping[str, Any]],
    *,
    step: int,
) -> dict[str, Any] | None:
    result: dict[str, Any] | None = None
    for row in rows:
        if (
            _safe_str(row.get("event")) == "stage3_heartbeat"
            and _safe_str(row.get("phase")) == "phaseB"
            and _safe_int(row.get("step")) == int(step)
        ):
            result = dict(row)
    return result


def _restart64_provisional(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    result: dict[str, Any] | None = None
    for row in rows:
        if (
            _safe_str(row.get("event")) == "stage3_phasea_provisional_gate_snapshot"
            and _safe_int(row.get("phaseA_checkpoint_restart_count")) == 64
        ):
            result = dict(row)
    return result


def _elapsed_label(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0.0:
        return ""
    total = int(round(seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _run_row(run_spec: Mapping[str, Any]) -> dict[str, Any]:
    run_dir = REPO_ROOT / _safe_str(run_spec.get("relpath"))
    attempt_status = _load_json(run_dir / "attempt_status.json")
    resume_status = _load_json(run_dir / "resume_bundle" / "stage3_resume_status.json")
    progress_rows = _load_jsonl(run_dir / "resume_bundle" / "stage3_resume_progress.jsonl")

    first_gate_decision = _first_gate_decision(progress_rows)
    latest_gate_decision = _last_event(
        progress_rows,
        event_name="stage3_phasea_gate_action_decision",
    )
    phaseb_2112 = _phaseb_step_heartbeat(progress_rows, step=2112)
    restart64 = _restart64_provisional(progress_rows)

    return {
        "row_id": _safe_str(run_spec.get("row_id")),
        "search_seed": _safe_int(run_spec.get("search_seed")),
        "run_role": _safe_str(run_spec.get("run_role")),
        "output_dir": _relative_path(run_dir),
        "phasea_provisional_gate_action_enabled": _safe_int(
            attempt_status.get("phasea_provisional_gate_action_enabled")
        ),
        "elapsed_seconds": _safe_float(attempt_status.get("elapsed_seconds")),
        "elapsed": _safe_str(attempt_status.get("elapsed")),
        "flow_elapsed_seconds": _safe_float(resume_status.get("flow_elapsed_seconds")),
        "heartbeat_count": _safe_int(resume_status.get("heartbeat_count")),
        "resume_best_match_ratio": _safe_float(resume_status.get("resume_best_match_ratio")),
        "resume_best_stage": _safe_str(resume_status.get("resume_best_stage")),
        "first_gate_decision_restart_count": _safe_int(
            (first_gate_decision or {}).get("phaseA_checkpoint_restart_count")
        ),
        "first_gate_decision_elapsed_seconds": _safe_float(
            (first_gate_decision or {}).get("phaseA_checkpoint_elapsed_seconds")
        ),
        "first_gate_decision_elapsed_share": (
            _safe_float((first_gate_decision or {}).get("phaseA_checkpoint_elapsed_seconds"))
            / _safe_float(attempt_status.get("elapsed_seconds"))
            if _safe_float(attempt_status.get("elapsed_seconds")) > 0.0
            else float("nan")
        ),
        "first_gate_decision_verdict": _safe_str(
            (first_gate_decision or {}).get("gate_verdict")
        ),
        "gate_decision_event_count": _event_count(
            progress_rows,
            event_name="stage3_phasea_gate_action_decision",
        ),
        "latest_gate_decision_restart_count": _safe_int(
            (latest_gate_decision or {}).get("phaseA_checkpoint_restart_count")
        ),
        "latest_gate_decision_elapsed_seconds": _safe_float(
            (latest_gate_decision or {}).get("phaseA_checkpoint_elapsed_seconds")
        ),
        "restart64_provisional_elapsed_seconds": _safe_float(
            (restart64 or {}).get("phaseA_checkpoint_elapsed_seconds")
        ),
        "restart64_best_init_match": _safe_float(
            (restart64 or {}).get("phaseA_best_init_match")
        ),
        "phaseb_step2112_elapsed_seconds": _safe_float(
            (phaseb_2112 or {}).get("elapsed_seconds")
        ),
        "phaseb_step2112_evals_total": _safe_int((phaseb_2112 or {}).get("evals_total")),
        "phaseb_step2112_eval_rate": (
            _safe_int((phaseb_2112 or {}).get("evals_total"))
            / _safe_float((phaseb_2112 or {}).get("elapsed_seconds"))
            if _safe_float((phaseb_2112 or {}).get("elapsed_seconds")) > 0.0
            else float("nan")
        ),
    }


def _find_row(rows: Sequence[Mapping[str, Any]], row_id: str) -> dict[str, Any]:
    for row in rows:
        if _safe_str(row.get("row_id")) == row_id:
            return dict(row)
    raise KeyError(f"Missing row_id={row_id}")


def _ratio(numerator: float, denominator: float) -> float:
    if not math.isfinite(numerator) or not math.isfinite(denominator) or denominator <= 0.0:
        return float("nan")
    return float(numerator / denominator)


def _build_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ref7003 = _find_row(rows, "7003_reference_exact")
    fam7003 = _find_row(rows, "7003_family_microbatch")
    ref7004_anchor = _find_row(rows, "7004_reference_anchor")
    ref7004_latest = _find_row(rows, "7004_reference_latest")
    fam7004 = _find_row(rows, "7004_family_microbatch")

    ratio7003_elapsed = _ratio(
        _safe_float(fam7003.get("elapsed_seconds")),
        _safe_float(ref7003.get("elapsed_seconds")),
    )
    ratio7003_phaseb = _ratio(
        _safe_float(fam7003.get("phaseb_step2112_elapsed_seconds")),
        _safe_float(ref7003.get("phaseb_step2112_elapsed_seconds")),
    )
    ratio7004_elapsed_anchor = _ratio(
        _safe_float(fam7004.get("elapsed_seconds")),
        _safe_float(ref7004_anchor.get("elapsed_seconds")),
    )
    ratio7004_elapsed_latest = _ratio(
        _safe_float(fam7004.get("elapsed_seconds")),
        _safe_float(ref7004_latest.get("elapsed_seconds")),
    )
    ratio7004_phasea_latest = _ratio(
        _safe_float(fam7004.get("restart64_provisional_elapsed_seconds")),
        _safe_float(ref7004_latest.get("restart64_provisional_elapsed_seconds")),
    )
    ratio7004_phaseb_latest = _ratio(
        _safe_float(fam7004.get("phaseb_step2112_elapsed_seconds")),
        _safe_float(ref7004_latest.get("phaseb_step2112_elapsed_seconds")),
    )

    first_keep_restart = _safe_int(fam7004.get("first_gate_decision_restart_count"))
    first_keep_share = _safe_float(fam7004.get("first_gate_decision_elapsed_share"))
    stable_control = (
        math.isfinite(ratio7003_elapsed)
        and ratio7003_elapsed <= 1.05
        and math.isfinite(ratio7003_phaseb)
        and ratio7003_phaseb <= 1.10
    )
    broad_7004_slowdown = (
        math.isfinite(ratio7004_elapsed_anchor)
        and ratio7004_elapsed_anchor >= 1.30
        and math.isfinite(ratio7004_phasea_latest)
        and ratio7004_phasea_latest >= 1.30
        and math.isfinite(ratio7004_phaseb_latest)
        and ratio7004_phaseb_latest >= 1.50
    )
    early_keep = (
        first_keep_restart == 32
        and math.isfinite(first_keep_share)
        and first_keep_share <= 0.35
    )

    if stable_control and broad_7004_slowdown and early_keep:
        recommendation = "advance"
        next_branch = (
            "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_"
            "subtopic_synthesis"
        )
        reason = (
            "7003 stays timing-stable under the same action wiring, while 7004 "
            "shows broad late-PhaseA and downstream throughput loss after an "
            "already-early keep decision. The anomaly does not read like a gate-"
            "logic failure."
        )
        review_ready = 1
        live_runtime_reopen_recommended = 0
    else:
        recommendation = "refine"
        next_branch = (
            "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_"
            "timing_followup"
        )
        reason = (
            "The current timing evidence does not cleanly separate control stability, "
            "early keep timing, and broad 7004 slowdown, so the anomaly remains "
            "insufficiently explained."
        )
        review_ready = 0
        live_runtime_reopen_recommended = 0

    return {
        "question": QUESTION,
        "suspicion": SUSPICION,
        "alternative": MAIN_ALTERNATIVE,
        "decision_rule": DECISION_RULE,
        "family7003_elapsed_ratio_vs_reference": ratio7003_elapsed,
        "family7003_phaseb_step2112_elapsed_ratio_vs_reference": ratio7003_phaseb,
        "family7004_elapsed_ratio_vs_anchor_reference": ratio7004_elapsed_anchor,
        "family7004_elapsed_ratio_vs_latest_reference": ratio7004_elapsed_latest,
        "family7004_restart64_elapsed_ratio_vs_latest_reference": ratio7004_phasea_latest,
        "family7004_phaseb_step2112_elapsed_ratio_vs_latest_reference": ratio7004_phaseb_latest,
        "family7004_first_keep_restart_count": first_keep_restart,
        "family7004_first_keep_elapsed_seconds": _safe_float(
            fam7004.get("first_gate_decision_elapsed_seconds")
        ),
        "family7004_first_keep_elapsed_share": first_keep_share,
        "family7004_gate_decision_event_count": _safe_int(
            fam7004.get("gate_decision_event_count")
        ),
        "review_ready": int(review_ready),
        "live_runtime_reopen_recommended": int(live_runtime_reopen_recommended),
        "recommendation": recommendation,
        "next_branch": next_branch,
        "reason": reason,
    }


def _build_readout(*, rows: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> str:
    lines = [
        "# Phase-A Checkpoint Best-Init Window Timing Postmortem Audit",
        "",
        "Question:",
        f"- {QUESTION}",
        "",
        "Outcome:",
        f"- recommendation: `{_safe_str(summary.get('recommendation'))}`",
        f"- review ready: `{_safe_int(summary.get('review_ready'))}`",
        f"- live runtime reopen recommended: `{_safe_int(summary.get('live_runtime_reopen_recommended'))}`",
        f"- reason: {_safe_str(summary.get('reason'))}",
        "",
        "Key timing ratios:",
        f"- `7003` family elapsed / reference: `{_safe_float(summary.get('family7003_elapsed_ratio_vs_reference')):.3f}`",
        f"- `7003` family Phase-B step2112 elapsed / reference: `{_safe_float(summary.get('family7003_phaseb_step2112_elapsed_ratio_vs_reference')):.3f}`",
        f"- `7004` family elapsed / anchor reference: `{_safe_float(summary.get('family7004_elapsed_ratio_vs_anchor_reference')):.3f}`",
        f"- `7004` family elapsed / latest reference: `{_safe_float(summary.get('family7004_elapsed_ratio_vs_latest_reference')):.3f}`",
        f"- `7004` family restart64 elapsed / latest reference: `{_safe_float(summary.get('family7004_restart64_elapsed_ratio_vs_latest_reference')):.3f}`",
        f"- `7004` family Phase-B step2112 elapsed / latest reference: `{_safe_float(summary.get('family7004_phaseb_step2112_elapsed_ratio_vs_latest_reference')):.3f}`",
        f"- `7004` first keep checkpoint: `restart{_safe_int(summary.get('family7004_first_keep_restart_count'))}`",
        f"- `7004` first keep elapsed share: `{_safe_float(summary.get('family7004_first_keep_elapsed_share')):.3f}`",
        "",
        "Per-run rows:",
    ]
    for row in rows:
        lines.extend(
            [
                f"- `{_safe_str(row.get('row_id'))}`",
                f"  - elapsed: `{_safe_str(row.get('elapsed'))}`",
                f"  - flow elapsed seconds: `{_safe_float(row.get('flow_elapsed_seconds')):.3f}`",
                f"  - restart64 provisional elapsed seconds: `{_safe_float(row.get('restart64_provisional_elapsed_seconds')):.3f}`",
                f"  - Phase-B step2112 elapsed seconds: `{_safe_float(row.get('phaseb_step2112_elapsed_seconds')):.3f}`",
                f"  - Phase-B step2112 eval rate: `{_safe_float(row.get('phaseb_step2112_eval_rate')):.1f}`",
                f"  - first gate decision restart: `restart{_safe_int(row.get('first_gate_decision_restart_count'))}`",
                f"  - first gate decision elapsed seconds: `{_safe_float(row.get('first_gate_decision_elapsed_seconds')):.3f}`",
                f"  - gate decision count: `{_safe_int(row.get('gate_decision_event_count'))}`",
                f"  - resume best match ratio: `{_safe_float(row.get('resume_best_match_ratio')):.3f}`",
            ]
        )
    return "\n".join(lines) + "\n"


def run_audit(*, output_dir: Path | None = None) -> dict[str, Any]:
    actual_output_dir = output_dir or (
        REPO_ROOT
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "analysis"
        / "fixed_instance_solver_development_v1"
        / f"{_utc_label()}__{RUN_LABEL}"
    )
    actual_output_dir.mkdir(parents=True, exist_ok=False)

    rows = [_run_row(run_spec) for run_spec in RUN_SPECS]
    summary = _build_summary(rows)
    recommendation = {
        "recommendation": _safe_str(summary.get("recommendation")),
        "next_branch": _safe_str(summary.get("next_branch")),
        "review_ready": _safe_int(summary.get("review_ready")),
        "live_runtime_reopen_recommended": _safe_int(
            summary.get("live_runtime_reopen_recommended")
        ),
        "reason": _safe_str(summary.get("reason")),
    }

    _write_csv(
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_rows.csv",
        rows,
    )
    _append_jsonl(
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_rows.jsonl",
        rows,
    )
    _write_json(
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_summary.json",
        summary,
    )
    _write_json(
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_recommendation.json",
        recommendation,
    )
    (
        actual_output_dir
        / "selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_readout.md"
    ).write_text(_build_readout(rows=rows, summary=summary), encoding="utf-8")
    refresh_catalog_safely()
    return {
        "output_dir": _relative_path(actual_output_dir),
        "recommendation": _safe_str(summary.get("recommendation")),
        "review_ready": _safe_int(summary.get("review_ready")),
        "live_runtime_reopen_recommended": _safe_int(
            summary.get("live_runtime_reopen_recommended")
        ),
        "reason": _safe_str(summary.get("reason")),
    }


def main() -> None:
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} question={json.dumps(QUESTION)}"
    )
    result = run_audit()
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} recommendation={result['recommendation']} "
        f"review_ready={result['review_ready']} "
        f"live_runtime_reopen_recommended={result['live_runtime_reopen_recommended']} "
        f"output_dir={result['output_dir']}"
    )


if __name__ == "__main__":
    main()
