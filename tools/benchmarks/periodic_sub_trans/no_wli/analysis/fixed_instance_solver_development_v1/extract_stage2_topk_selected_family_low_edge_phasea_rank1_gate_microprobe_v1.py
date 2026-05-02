from __future__ import annotations

import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1.py"
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
    extract_fixed_instance_solver_development_v1 as base_mod,
)


RUN_LABEL = "stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1"
MATRIX_BUNDLE_DIR = (
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
MATRIX_ROWS_CSV = (
    MATRIX_BUNDLE_DIR / "selected_family_low_edge_exact_replay_1111_matrix_rows.csv"
)
PHASEA_AUDIT_BUNDLE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
    / "20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1"
)
PHASEA_CASE_ROWS_JSONL = (
    PHASEA_AUDIT_BUNDLE_DIR
    / "stage2_topk_selected_family_low_edge_phasea_competitiveness_case_rows.jsonl"
)
PHASEA_SUMMARY_JSON = (
    PHASEA_AUDIT_BUNDLE_DIR
    / "stage2_topk_selected_family_low_edge_phasea_competitiveness_summary.json"
)
POLICY_ID = "selected_family_low_edge_eps_0p016_v1"
FAMILY_VIEW_ID = "prefix_hamming_le_24"
MECHANISM_LAYER = "selection"
GATE_ID = "rank1_init_ge_0p30"
GATE_METRIC = "phasea_rank1_init_match"
GATE_THRESHOLD = 0.30
NEXT_BRANCH_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_rank1_gate_persistence_microprobe"
)


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _utc_label() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _timestamp() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _print_progress(message: str) -> None:
    print(f"[{_timestamp()}] {message}", flush=True)


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


def _mean(values: Sequence[float]) -> float:
    finite = [value for value in values if value == value]
    if not finite:
        return float("nan")
    return float(sum(finite) / float(len(finite)))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True))
            handle.write("\n")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {_relative_path(path)}")
    fieldnames = list(dict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _phasea_gate_proxy_elapsed_seconds(
    progress_rows: Sequence[Mapping[str, Any]],
) -> float:
    for row in progress_rows:
        if _safe_str(row.get("phase")) == "phaseB":
            return _safe_float(row.get("elapsed_seconds"))
    phasea_rows = [
        dict(row) for row in progress_rows if _safe_str(row.get("phase")) == "phaseA"
    ]
    if phasea_rows:
        return max(_safe_float(row.get("elapsed_seconds")) for row in phasea_rows)
    return float("nan")


def build_counterfactual_row(
    *,
    matrix_row: Mapping[str, Any],
    case_row: Mapping[str, Any],
    attempt_status: Mapping[str, Any],
    resume_status: Mapping[str, Any],
    gate_proxy_elapsed_seconds: float,
) -> dict[str, Any]:
    baseline_best_match_ratio = _safe_float(matrix_row.get("baseline_best_match_ratio"))
    retained_stage3_reference_match_ratio = _safe_float(
        matrix_row.get("retained_stage3_reference_match_ratio")
    )
    resume_best_match_ratio = _safe_float(matrix_row.get("resume_best_match_ratio"))
    gate_metric_value = _safe_float(case_row.get(GATE_METRIC))
    gate_kept = gate_metric_value >= GATE_THRESHOLD
    counterfactual_best_match_ratio = (
        resume_best_match_ratio if gate_kept else baseline_best_match_ratio
    )
    attempt_elapsed_seconds = _safe_float(attempt_status.get("elapsed_seconds"))
    flow_elapsed_seconds = _safe_float(resume_status.get("flow_elapsed_seconds"))
    estimated_saved_attempt_seconds = 0.0
    estimated_saved_flow_seconds = 0.0
    if not gate_kept and gate_proxy_elapsed_seconds == gate_proxy_elapsed_seconds:
        estimated_saved_attempt_seconds = max(
            attempt_elapsed_seconds - gate_proxy_elapsed_seconds,
            0.0,
        )
        estimated_saved_flow_seconds = max(
            flow_elapsed_seconds - gate_proxy_elapsed_seconds,
            0.0,
        )
    return {
        "fixture_seed": _safe_int(matrix_row.get("fixture_seed")),
        "search_seed": _safe_int(matrix_row.get("search_seed")),
        "output_dir": _safe_str(matrix_row.get("output_dir")),
        "candidate_policy_id": POLICY_ID,
        "family_view_id": FAMILY_VIEW_ID,
        "gate_id": GATE_ID,
        "gate_metric_name": GATE_METRIC,
        "gate_threshold": GATE_THRESHOLD,
        "gate_metric_value": gate_metric_value,
        "gate_kept": int(1 if gate_kept else 0),
        "counterfactual_mode": (
            "candidate_replay_kept" if gate_kept else "baseline_fallback_after_phasea"
        ),
        "baseline_best_match_ratio": baseline_best_match_ratio,
        "retained_stage3_reference_match_ratio": retained_stage3_reference_match_ratio,
        "resume_best_match_ratio": resume_best_match_ratio,
        "counterfactual_best_match_ratio": counterfactual_best_match_ratio,
        "counterfactual_delta_vs_baseline": (
            counterfactual_best_match_ratio - baseline_best_match_ratio
        ),
        "counterfactual_delta_vs_retained_stage3_reference": (
            counterfactual_best_match_ratio - retained_stage3_reference_match_ratio
        ),
        "case_category": _safe_str(case_row.get("case_category")),
        "phasea_gate_proxy_elapsed_seconds": gate_proxy_elapsed_seconds,
        "attempt_elapsed_seconds": attempt_elapsed_seconds,
        "flow_elapsed_seconds": flow_elapsed_seconds,
        "estimated_saved_attempt_seconds": estimated_saved_attempt_seconds,
        "estimated_saved_flow_seconds": estimated_saved_flow_seconds,
        "attempt_status": _safe_str(attempt_status.get("status")),
        "resume_stop_reason": _safe_str(resume_status.get("stop_reason")),
    }


def build_recommendation(
    summary_row: Mapping[str, Any],
) -> dict[str, Any]:
    family_mean_delta_vs_baseline = _safe_float(
        summary_row.get("counterfactual_family_mean_delta_vs_baseline")
    )
    worst_delta_vs_baseline = _safe_float(
        summary_row.get("counterfactual_family_worst_delta_vs_baseline")
    )
    filtered_saved_attempt_share = _safe_float(
        summary_row.get("filtered_estimated_saved_attempt_share")
    )
    filtered_run_count = _safe_int(summary_row.get("filtered_run_count"))
    if (
        family_mean_delta_vs_baseline > 0.0
        and worst_delta_vs_baseline >= -0.02
        and filtered_run_count >= 1
        and filtered_saved_attempt_share >= 0.80
    ):
        return {
            "recommendation": "advance",
            "next_branch_label": NEXT_BRANCH_LABEL,
            "mechanism_layer": MECHANISM_LAYER,
            "candidate_policy_id": POLICY_ID,
            "gate_id": GATE_ID,
            "gate_metric_name": GATE_METRIC,
            "gate_threshold": GATE_THRESHOLD,
            "reason": (
                "The concrete Phase-A rank-1 gate turns the family counterfactual "
                "positive while avoiding almost all of the filtered lanes' wallclock, "
                "so the next honest step is to make that gate inspectable and "
                "actionable during real runs."
            ),
        }
    return {
        "recommendation": "refine",
        "next_branch_label": "",
        "mechanism_layer": MECHANISM_LAYER,
        "candidate_policy_id": POLICY_ID,
        "gate_id": GATE_ID,
        "gate_metric_name": GATE_METRIC,
        "gate_threshold": GATE_THRESHOLD,
        "reason": (
            "The concrete Phase-A gate looks interesting, but its current "
            "counterfactual outcome or runtime savings are not yet strong enough "
            "to justify gate-persistence work."
        ),
    }


def _build_counterfactual_rows() -> list[dict[str, Any]]:
    matrix_rows = list(csv.DictReader(MATRIX_ROWS_CSV.open(encoding="utf-8")))
    case_rows = {
        _safe_int(row.get("search_seed")): dict(row)
        for row in _read_jsonl(PHASEA_CASE_ROWS_JSONL)
    }
    counterfactual_rows: list[dict[str, Any]] = []
    total = int(len(matrix_rows))
    for index, matrix_row in enumerate(matrix_rows, start=1):
        search_seed = _safe_int(matrix_row.get("search_seed"))
        replay_output_dir = REPO_ROOT / Path(_safe_str(matrix_row.get("output_dir")))
        attempt_status = json.loads(
            (replay_output_dir / "attempt_status.json").read_text(encoding="utf-8")
        )
        resume_status = json.loads(
            (
                replay_output_dir / "resume_bundle" / "stage3_resume_status.json"
            ).read_text(encoding="utf-8")
        )
        progress_rows = _read_jsonl(
            replay_output_dir / "resume_bundle" / "stage3_resume_progress.jsonl"
        )
        gate_proxy_elapsed_seconds = _phasea_gate_proxy_elapsed_seconds(progress_rows)
        counterfactual_row = build_counterfactual_row(
            matrix_row=matrix_row,
            case_row=case_rows[search_seed],
            attempt_status=attempt_status,
            resume_status=resume_status,
            gate_proxy_elapsed_seconds=gate_proxy_elapsed_seconds,
        )
        counterfactual_rows.append(counterfactual_row)
        _print_progress(
            "case_finished "
            f"unit={index}/{total} search_seed={search_seed} "
            f"gate_kept={counterfactual_row['gate_kept']} "
            f"counterfactual_delta_vs_baseline="
            f"{counterfactual_row['counterfactual_delta_vs_baseline']:.3f} "
            f"saved_attempt_seconds="
            f"{counterfactual_row['estimated_saved_attempt_seconds']:.1f}"
        )
    counterfactual_rows.sort(key=lambda row: _safe_int(row.get("search_seed")))
    return counterfactual_rows


def _build_summary_row(
    counterfactual_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    kept_rows = [dict(row) for row in counterfactual_rows if _safe_int(row.get("gate_kept")) == 1]
    filtered_rows = [
        dict(row) for row in counterfactual_rows if _safe_int(row.get("gate_kept")) == 0
    ]
    filtered_saved_attempt_seconds = sum(
        _safe_float(row.get("estimated_saved_attempt_seconds")) for row in filtered_rows
    )
    filtered_attempt_seconds = sum(
        _safe_float(row.get("attempt_elapsed_seconds")) for row in filtered_rows
    )
    return {
        "gate_id": GATE_ID,
        "gate_metric_name": GATE_METRIC,
        "gate_threshold": GATE_THRESHOLD,
        "kept_run_count": int(len(kept_rows)),
        "filtered_run_count": int(len(filtered_rows)),
        "kept_search_seeds": ",".join(
            str(_safe_int(row.get("search_seed"))) for row in kept_rows
        ),
        "filtered_search_seeds": ",".join(
            str(_safe_int(row.get("search_seed"))) for row in filtered_rows
        ),
        "counterfactual_family_mean_delta_vs_baseline": _mean(
            [
                _safe_float(row.get("counterfactual_delta_vs_baseline"))
                for row in counterfactual_rows
            ]
        ),
        "counterfactual_family_mean_delta_vs_retained_stage3_reference": _mean(
            [
                _safe_float(
                    row.get("counterfactual_delta_vs_retained_stage3_reference")
                )
                for row in counterfactual_rows
            ]
        ),
        "counterfactual_family_worst_delta_vs_baseline": min(
            (
                _safe_float(row.get("counterfactual_delta_vs_baseline"))
                for row in counterfactual_rows
            ),
            default=float("nan"),
        ),
        "counterfactual_family_worst_delta_vs_retained_stage3_reference": min(
            (
                _safe_float(
                    row.get("counterfactual_delta_vs_retained_stage3_reference")
                )
                for row in counterfactual_rows
            ),
            default=float("nan"),
        ),
        "mean_phasea_gate_proxy_elapsed_seconds": _mean(
            [_safe_float(row.get("phasea_gate_proxy_elapsed_seconds")) for row in counterfactual_rows]
        ),
        "filtered_estimated_saved_attempt_seconds_total": filtered_saved_attempt_seconds,
        "filtered_estimated_saved_attempt_minutes_total": (
            filtered_saved_attempt_seconds / 60.0
        ),
        "filtered_estimated_saved_attempt_share": (
            filtered_saved_attempt_seconds / filtered_attempt_seconds
            if filtered_attempt_seconds > 0.0
            else float("nan")
        ),
        "filtered_estimated_saved_flow_seconds_total": sum(
            _safe_float(row.get("estimated_saved_flow_seconds")) for row in filtered_rows
        ),
        "filtered_case_categories": ",".join(
            _safe_str(row.get("case_category")) for row in filtered_rows
        ),
    }


def _write_markdown(
    output_dir: Path,
    *,
    counterfactual_rows: Sequence[Mapping[str, Any]],
    summary_row: Mapping[str, Any],
    recommendation: Mapping[str, Any],
) -> None:
    lines = [
        "# Stage-2 Topk Selected-Family Low-Edge Phase-A Rank-1 Gate Microprobe v1",
        "",
        "Question:",
        "- if we condition the concrete selector on `phasea_rank1_init_match >= 0.30` and fall back immediately on filtered lanes, does the fixed 1111 exact-family read become both safer and cheaper?",
        "",
        "Mechanism layer:",
        "- `selection`",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- next branch: `{_safe_str(recommendation.get('next_branch_label')) or 'none'}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Summary:",
        f"- gate: `{GATE_ID}`",
        f"- kept seeds: `{_safe_str(summary_row.get('kept_search_seeds')) or '-'}`",
        f"- filtered seeds: `{_safe_str(summary_row.get('filtered_search_seeds')) or '-'}`",
        f"- counterfactual family mean delta vs baseline: `{_safe_float(summary_row.get('counterfactual_family_mean_delta_vs_baseline')):.3f}`",
        f"- counterfactual family mean delta vs retained: `{_safe_float(summary_row.get('counterfactual_family_mean_delta_vs_retained_stage3_reference')):.3f}`",
        f"- total filtered saved attempt minutes: `{_safe_float(summary_row.get('filtered_estimated_saved_attempt_minutes_total')):.1f}`",
        f"- filtered saved attempt share: `{_safe_float(summary_row.get('filtered_estimated_saved_attempt_share')):.3f}`",
        "",
        "Per-seed counterfactual:",
        "",
        "| search seed | gate kept | mode | counterfactual delta vs baseline | counterfactual delta vs retained | gate proxy seconds | saved attempt seconds |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in counterfactual_rows:
        lines.append(
            f"| `{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_int(row.get('gate_kept'))}` | "
            f"`{_safe_str(row.get('counterfactual_mode'))}` | "
            f"`{_safe_float(row.get('counterfactual_delta_vs_baseline')):.3f}` | "
            f"`{_safe_float(row.get('counterfactual_delta_vs_retained_stage3_reference')):.3f}` | "
            f"`{_safe_float(row.get('phasea_gate_proxy_elapsed_seconds')):.1f}` | "
            f"`{_safe_float(row.get('estimated_saved_attempt_seconds')):.1f}` |"
        )
    (
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_readout.md"
    ).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_extract() -> dict[str, Any]:
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"matrix_bundle={_relative_path(MATRIX_BUNDLE_DIR)} "
        f"phasea_audit_bundle={_relative_path(PHASEA_AUDIT_BUNDLE_DIR)} "
        f"gate_id={GATE_ID}"
    )
    phasea_summary = json.loads(PHASEA_SUMMARY_JSON.read_text(encoding="utf-8"))
    if _safe_str(
        ((phasea_summary.get("recommendation") or {}).get("best_gate_id"))
    ) != GATE_ID:
        raise RuntimeError(
            f"Expected best gate {GATE_ID}, got "
            f"{_safe_str(((phasea_summary.get('recommendation') or {}).get('best_gate_id')))}"
        )

    counterfactual_rows = _build_counterfactual_rows()
    summary_row = _build_summary_row(counterfactual_rows)
    recommendation = build_recommendation(summary_row)

    output_dir = base_mod.OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_rows.jsonl",
        counterfactual_rows,
    )
    _write_csv(
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_rows.csv",
        counterfactual_rows,
    )
    _write_json(
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_summary.json",
        {
            "run_label": RUN_LABEL,
            "candidate_policy_id": POLICY_ID,
            "family_view_id": FAMILY_VIEW_ID,
            "gate_id": GATE_ID,
            "input_matrix_bundle": _relative_path(MATRIX_BUNDLE_DIR),
            "input_phasea_audit_bundle": _relative_path(PHASEA_AUDIT_BUNDLE_DIR),
            "summary_row": summary_row,
            "recommendation": recommendation,
            "output_dir": _relative_path(output_dir),
        },
    )
    _write_json(
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_recommendation.json",
        recommendation,
    )
    _write_markdown(
        output_dir,
        counterfactual_rows=counterfactual_rows,
        summary_row=summary_row,
        recommendation=recommendation,
    )
    refresh_catalog_safely(print_fn=print)

    result = {
        "run_label": RUN_LABEL,
        "recommendation": _safe_str(recommendation.get("recommendation")),
        "next_branch_label": _safe_str(recommendation.get("next_branch_label")),
        "gate_id": GATE_ID,
        "filtered_run_count": _safe_int(summary_row.get("filtered_run_count")),
        "counterfactual_family_mean_delta_vs_baseline": _safe_float(
            summary_row.get("counterfactual_family_mean_delta_vs_baseline")
        ),
        "filtered_estimated_saved_attempt_minutes_total": _safe_float(
            summary_row.get("filtered_estimated_saved_attempt_minutes_total")
        ),
        "output_dir": _relative_path(output_dir),
    }
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} "
        f"recommendation={result['recommendation']} "
        f"counterfactual_family_mean_delta_vs_baseline="
        f"{result['counterfactual_family_mean_delta_vs_baseline']:.3f} "
        f"saved_attempt_minutes_total="
        f"{result['filtered_estimated_saved_attempt_minutes_total']:.1f} "
        f"output_dir={result['output_dir']}"
    )
    return result


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
