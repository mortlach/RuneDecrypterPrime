from __future__ import annotations

import csv
import datetime as dt
import json
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
        "extract_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1.py"
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


RUN_LABEL = "stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1"
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
POLICY_ID = "selected_family_low_edge_eps_0p016_v1"
FAMILY_VIEW_ID = "prefix_hamming_le_24"
MECHANISM_LAYER = "selection"
HARD_COLLAPSE_CATEGORIES = (
    "local_search_collapse_after_phasea",
    "phasea_competitiveness_below_floor",
)
NON_CATASTROPHIC_CATEGORIES = (
    "clean_exact_positive",
    "baseline_positive_near_retained",
    "competitive_near_floor",
)
THRESHOLD_SPECS = (
    ("phasea_rank1_init_match", 0.25),
    ("phasea_rank1_init_match", 0.30),
    ("phasea_rank1_init_match", 0.35),
    ("phasea_rank1_init_match", 0.38),
    ("phasea_rank1_init_match", 0.40),
    ("phasea_rank1_init_match", 0.42),
    ("phasea_rank1_init_match", 0.45),
    ("phasea_best_init_match", 0.25),
    ("phasea_best_init_match", 0.30),
    ("phasea_best_init_match", 0.35),
    ("phasea_best_init_match", 0.38),
    ("phasea_best_init_match", 0.40),
    ("phasea_best_init_match", 0.42),
    ("phasea_best_init_match", 0.45),
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


def _mean(values: Sequence[float]) -> float:
    finite = [value for value in values if value == value]
    if not finite:
        return float("nan")
    return float(sum(finite) / float(len(finite)))


def _first_phasea_rank(
    phasea_rows: Sequence[Mapping[str, Any]],
    rank: int,
) -> Mapping[str, Any]:
    for row in phasea_rows:
        if _safe_int(row.get("source_rank")) == rank:
            return dict(row)
    raise RuntimeError(f"Missing phaseA_selected row with source_rank={rank}")


def classify_case_category(case_row: Mapping[str, Any]) -> str:
    delta_vs_baseline = _safe_float(case_row.get("match_delta_vs_baseline"))
    delta_vs_retained = _safe_float(
        case_row.get("match_delta_vs_retained_stage3_reference")
    )
    baseline_best_match = _safe_float(case_row.get("baseline_best_match_ratio"))
    replay_best_match = _safe_float(case_row.get("resume_best_match_ratio"))
    stage3_best_match = _safe_float(case_row.get("stage3_best_match_ratio"))
    phasea_best_init_match = _safe_float(case_row.get("phasea_best_init_match"))

    if delta_vs_baseline > 0.0 and delta_vs_retained > 0.0:
        return "clean_exact_positive"
    if delta_vs_baseline > 0.0 and delta_vs_retained >= -0.01:
        return "baseline_positive_near_retained"
    if (
        baseline_best_match - replay_best_match <= 0.02
        and baseline_best_match - stage3_best_match <= 0.02
    ):
        return "competitive_near_floor"
    if stage3_best_match <= phasea_best_init_match - 0.10:
        return "local_search_collapse_after_phasea"
    return "phasea_competitiveness_below_floor"


def _build_case_rows() -> list[dict[str, Any]]:
    matrix_rows = list(csv.DictReader(MATRIX_ROWS_CSV.open(encoding="utf-8")))
    case_rows: list[dict[str, Any]] = []
    total = int(len(matrix_rows))
    for index, row in enumerate(matrix_rows, start=1):
        search_seed = _safe_int(row.get("search_seed"))
        replay_output_dir = REPO_ROOT / Path(_safe_str(row.get("output_dir")))
        stage3_flow = json.loads(
            (replay_output_dir / "resume_bundle" / "stage3_flow.json").read_text(
                encoding="utf-8"
            )
        )
        checkpoints = [
            json.loads(line)
            for line in (
                replay_output_dir / "resume_bundle" / "phasec_start_checkpoints.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        phasea_rows = [
            dict(checkpoint)
            for checkpoint in checkpoints
            if _safe_str(checkpoint.get("source")) == "phaseA_selected"
        ]
        rank1_phasea = _first_phasea_rank(phasea_rows, 1)
        best_phasea_init = max(
            phasea_rows,
            key=lambda checkpoint: _safe_float(checkpoint.get("init_match")),
        )
        best_phasea_final = max(
            phasea_rows,
            key=lambda checkpoint: _safe_float(checkpoint.get("final_match")),
        )

        case_row = {
            "fixture_seed": 1111,
            "search_seed": search_seed,
            "output_dir": _relative_path(replay_output_dir),
            "candidate_policy_id": POLICY_ID,
            "family_view_id": FAMILY_VIEW_ID,
            "baseline_best_match_ratio": _safe_float(
                row.get("baseline_best_match_ratio")
            ),
            "retained_stage3_reference_match_ratio": _safe_float(
                row.get("retained_stage3_reference_match_ratio")
            ),
            "resume_best_match_ratio": _safe_float(row.get("resume_best_match_ratio")),
            "match_delta_vs_baseline": _safe_float(row.get("match_delta_vs_baseline")),
            "match_delta_vs_retained_stage3_reference": _safe_float(
                row.get("match_delta_vs_retained_stage3_reference")
            ),
            "candidate_truth_delta_vs_baseline_row": _safe_float(
                row.get("candidate_truth_delta_vs_baseline_row")
            ),
            "resume_best_stage": _safe_str(row.get("resume_best_stage")),
            "stage3_best_match_ratio": _safe_float(stage3_flow.get("best3_match")),
            "stage3_best_score": _safe_float(stage3_flow.get("best3_score")),
            "phasea_rank1_init_match": _safe_float(rank1_phasea.get("init_match")),
            "phasea_rank1_final_match": _safe_float(rank1_phasea.get("final_match")),
            "phasea_rank1_score_gain": _safe_float(rank1_phasea.get("score_gain")),
            "phasea_rank1_plateau_would_stop": _safe_int(
                (rank1_phasea.get("shadow_stop_v1") or {}).get("plateau_would_stop")
            ),
            "phasea_best_init_match": _safe_float(best_phasea_init.get("init_match")),
            "phasea_best_init_rank": _safe_int(best_phasea_init.get("source_rank")),
            "phasea_best_final_match": _safe_float(
                best_phasea_final.get("final_match")
            ),
            "phasea_best_final_rank": _safe_int(best_phasea_final.get("source_rank")),
            "phasea_best_to_stage3_conversion_delta": (
                _safe_float(stage3_flow.get("best3_match"))
                - _safe_float(best_phasea_init.get("init_match"))
            ),
            "phasea_rank1_gap_vs_baseline": (
                _safe_float(rank1_phasea.get("init_match"))
                - _safe_float(row.get("baseline_best_match_ratio"))
            ),
            "stage3_best_gap_vs_baseline": (
                _safe_float(stage3_flow.get("best3_match"))
                - _safe_float(row.get("baseline_best_match_ratio"))
            ),
            "stage3_best_gap_vs_retained_stage3_reference": (
                _safe_float(stage3_flow.get("best3_match"))
                - _safe_float(row.get("retained_stage3_reference_match_ratio"))
            ),
        }
        case_row["case_category"] = classify_case_category(case_row)
        case_rows.append(case_row)
        _print_progress(
            "case_finished "
            f"unit={index}/{total} search_seed={search_seed} "
            f"category={case_row['case_category']} "
            f"rank1_init={case_row['phasea_rank1_init_match']:.3f} "
            f"delta_vs_baseline={case_row['match_delta_vs_baseline']:.3f}"
        )
    case_rows.sort(key=lambda row: _safe_int(row.get("search_seed")))
    return case_rows


def _gate_id(metric_name: str, threshold: float) -> str:
    metric_suffix = metric_name.replace("phasea_", "").replace("_match", "")
    threshold_text = f"{threshold:.2f}".replace(".", "p")
    return f"{metric_suffix}_ge_{threshold_text}"


def _build_threshold_summary_rows(
    case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    summary_rows: list[dict[str, Any]] = []
    for metric_name, threshold in THRESHOLD_SPECS:
        kept_rows = [
            dict(row)
            for row in case_rows
            if _safe_float(row.get(metric_name)) >= float(threshold)
        ]
        filtered_rows = [
            dict(row)
            for row in case_rows
            if _safe_float(row.get(metric_name)) < float(threshold)
        ]
        counterfactual_deltas_vs_baseline = [
            _safe_float(row.get("match_delta_vs_baseline")) for row in kept_rows
        ] + [0.0 for _ in filtered_rows]
        counterfactual_deltas_vs_retained = [
            _safe_float(row.get("match_delta_vs_retained_stage3_reference"))
            for row in kept_rows
        ] + [0.0 for _ in filtered_rows]
        filtered_categories = {
            _safe_str(row.get("case_category")) for row in filtered_rows
        }
        kept_categories = {_safe_str(row.get("case_category")) for row in kept_rows}
        filters_all_hard_collapses = all(
            category in filtered_categories for category in HARD_COLLAPSE_CATEGORIES
        )
        keeps_all_noncatastrophic = all(
            category in kept_categories for category in NON_CATASTROPHIC_CATEGORIES
        )
        summary_rows.append(
            {
                "gate_id": _gate_id(metric_name, threshold),
                "metric_name": metric_name,
                "threshold": float(threshold),
                "kept_run_count": int(len(kept_rows)),
                "filtered_run_count": int(len(filtered_rows)),
                "kept_search_seeds": ",".join(
                    str(_safe_int(row.get("search_seed"))) for row in kept_rows
                ),
                "filtered_search_seeds": ",".join(
                    str(_safe_int(row.get("search_seed"))) for row in filtered_rows
                ),
                "kept_mean_delta_vs_baseline": _mean(
                    [_safe_float(row.get("match_delta_vs_baseline")) for row in kept_rows]
                ),
                "filtered_mean_delta_vs_baseline": _mean(
                    [
                        _safe_float(row.get("match_delta_vs_baseline"))
                        for row in filtered_rows
                    ]
                ),
                "kept_worst_delta_vs_baseline": min(
                    (_safe_float(row.get("match_delta_vs_baseline")) for row in kept_rows),
                    default=float("nan"),
                ),
                "filtered_best_delta_vs_baseline": max(
                    (
                        _safe_float(row.get("match_delta_vs_baseline"))
                        for row in filtered_rows
                    ),
                    default=float("nan"),
                ),
                "counterfactual_family_mean_delta_vs_baseline": _mean(
                    counterfactual_deltas_vs_baseline
                ),
                "counterfactual_family_mean_delta_vs_retained": _mean(
                    counterfactual_deltas_vs_retained
                ),
                "counterfactual_family_worst_delta_vs_baseline": min(
                    counterfactual_deltas_vs_baseline,
                    default=float("nan"),
                ),
                "filters_all_hard_collapses": int(
                    1 if filters_all_hard_collapses else 0
                ),
                "keeps_all_noncatastrophic": int(
                    1 if keeps_all_noncatastrophic else 0
                ),
            }
        )
    return summary_rows


def build_recommendation(
    threshold_summary_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    viable_rows = [
        dict(row)
        for row in threshold_summary_rows
        if _safe_int(row.get("filters_all_hard_collapses")) == 1
        and _safe_int(row.get("keeps_all_noncatastrophic")) == 1
        and _safe_float(row.get("counterfactual_family_mean_delta_vs_baseline")) > 0.0
        and _safe_float(row.get("counterfactual_family_worst_delta_vs_baseline")) >= -0.02
    ]
    if viable_rows:
        best_row = max(
            viable_rows,
            key=lambda row: (
                _safe_float(row.get("counterfactual_family_mean_delta_vs_baseline")),
                -_safe_float(row.get("threshold")),
            ),
        )
        return {
            "recommendation": "advance",
            "next_branch_label": "stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe",
            "mechanism_layer": MECHANISM_LAYER,
            "candidate_policy_id": POLICY_ID,
            "best_gate_id": _safe_str(best_row.get("gate_id")),
            "best_metric_name": _safe_str(best_row.get("metric_name")),
            "best_threshold": _safe_float(best_row.get("threshold")),
            "reason": (
                "An early Phase-A competitiveness gate cleanly filters both hard "
                "collapse lanes while keeping all three non-catastrophic lanes, "
                "and the resulting counterfactual family mean delta versus "
                "baseline turns positive."
            ),
        }
    return {
        "recommendation": "refine",
        "next_branch_label": "",
        "mechanism_layer": MECHANISM_LAYER,
        "candidate_policy_id": POLICY_ID,
        "best_gate_id": "",
        "best_metric_name": "",
        "best_threshold": float("nan"),
        "reason": (
            "No simple early Phase-A competitiveness gate yet cleanly separates "
            "the non-catastrophic lanes from the hard collapse lanes."
        ),
    }


def _write_markdown(
    output_dir: Path,
    *,
    case_rows: Sequence[Mapping[str, Any]],
    threshold_summary_rows: Sequence[Mapping[str, Any]],
    recommendation: Mapping[str, Any],
) -> None:
    lines = [
        "# Stage-2 Topk Selected-Family Low-Edge Phase-A Competitiveness Audit v1",
        "",
        "Question:",
        "- after the mixed exact-family replay result, do simple early Phase-A challenger competitiveness signals separate the 1111 wins / near wins from the hard collapses cheaply enough to justify a conditioned rule?",
        "",
        "Mechanism layer:",
        "- `selection`",
        "",
        "Policy under audit:",
        f"- `{POLICY_ID}`",
        f"- family view: `{FAMILY_VIEW_ID}`",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- next branch: `{_safe_str(recommendation.get('next_branch_label')) or 'none'}`",
        f"- best gate: `{_safe_str(recommendation.get('best_gate_id')) or 'none'}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Per-seed case read:",
        "",
        "| search seed | case category | replay delta vs baseline | rank1 init | best init | best init rank | stage3 best | conversion delta |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in case_rows:
        lines.append(
            f"| `{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_str(row.get('case_category'))}` | "
            f"`{_safe_float(row.get('match_delta_vs_baseline')):.3f}` | "
            f"`{_safe_float(row.get('phasea_rank1_init_match')):.3f}` | "
            f"`{_safe_float(row.get('phasea_best_init_match')):.3f}` | "
            f"`{_safe_int(row.get('phasea_best_init_rank'))}` | "
            f"`{_safe_float(row.get('stage3_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('phasea_best_to_stage3_conversion_delta')):.3f}` |"
        )
    lines.extend(
        [
            "",
            "Gate sweep summary:",
            "",
            "| gate id | kept seeds | filtered seeds | kept mean delta | filtered mean delta | counterfactual family mean delta |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in threshold_summary_rows:
        lines.append(
            f"| `{_safe_str(row.get('gate_id'))}` | "
            f"`{_safe_str(row.get('kept_search_seeds')) or '-'}` | "
            f"`{_safe_str(row.get('filtered_search_seeds')) or '-'}` | "
            f"`{_safe_float(row.get('kept_mean_delta_vs_baseline')):.3f}` | "
            f"`{_safe_float(row.get('filtered_mean_delta_vs_baseline')):.3f}` | "
            f"`{_safe_float(row.get('counterfactual_family_mean_delta_vs_baseline')):.3f}` |"
        )
    (
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_readout.md"
    ).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_extract() -> dict[str, Any]:
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"matrix_bundle={_relative_path(MATRIX_BUNDLE_DIR)} "
        f"candidate_policy={POLICY_ID}"
    )
    case_rows = _build_case_rows()
    threshold_summary_rows = _build_threshold_summary_rows(case_rows)
    recommendation = build_recommendation(threshold_summary_rows)

    output_dir = base_mod.OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_competitiveness_case_rows.jsonl",
        case_rows,
    )
    _write_csv(
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_competitiveness_case_rows.csv",
        case_rows,
    )
    _write_jsonl(
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_competitiveness_threshold_summary_rows.jsonl",
        threshold_summary_rows,
    )
    _write_csv(
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_competitiveness_threshold_summary_rows.csv",
        threshold_summary_rows,
    )
    _write_json(
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_competitiveness_recommendation.json",
        recommendation,
    )
    _write_json(
        output_dir
        / "stage2_topk_selected_family_low_edge_phasea_competitiveness_summary.json",
        {
            "run_label": RUN_LABEL,
            "candidate_policy_id": POLICY_ID,
            "family_view_id": FAMILY_VIEW_ID,
            "case_row_count": int(len(case_rows)),
            "threshold_summary_row_count": int(len(threshold_summary_rows)),
            "recommendation": dict(recommendation),
            "input_matrix_bundle": _relative_path(MATRIX_BUNDLE_DIR),
            "output_dir": _relative_path(output_dir),
        },
    )
    _write_markdown(
        output_dir,
        case_rows=case_rows,
        threshold_summary_rows=threshold_summary_rows,
        recommendation=recommendation,
    )
    refresh_catalog_safely(print_fn=print)

    result = {
        "run_label": RUN_LABEL,
        "candidate_policy_id": POLICY_ID,
        "recommendation": _safe_str(recommendation.get("recommendation")),
        "next_branch_label": _safe_str(recommendation.get("next_branch_label")),
        "best_gate_id": _safe_str(recommendation.get("best_gate_id")),
        "best_threshold": _safe_float(recommendation.get("best_threshold")),
        "case_row_count": int(len(case_rows)),
        "threshold_summary_row_count": int(len(threshold_summary_rows)),
        "output_dir": _relative_path(output_dir),
    }
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} "
        f"recommendation={result['recommendation']} "
        f"best_gate={result['best_gate_id'] or 'none'} "
        f"output_dir={result['output_dir']}"
    )
    return result


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
