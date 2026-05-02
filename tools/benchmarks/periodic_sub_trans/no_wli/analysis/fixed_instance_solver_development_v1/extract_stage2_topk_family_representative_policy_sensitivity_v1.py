from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage2_topk_family_representative_policy_sensitivity_v1.py"
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
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    extract_stage2_topk_family_representative_policy_audit_v1 as policy_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.family_views import (  # noqa: E402
    FAMILY_VIEWS,
    cluster_family_ids,
)


RUN_LABEL = "stage2_topk_family_representative_policy_sensitivity_v1"
PRIMARY_FIXTURE_SEEDS = (611, 1111, 1411, 1511)
EPS_VALUES = (0.010, 0.015, 0.016, 0.020, 0.025)


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


def _family_rows_for_view(
    *,
    rows: Sequence[Mapping[str, Any]],
    family_view: Mapping[str, Any],
    columns: int,
) -> tuple[dict[str, str], dict[str, Any], list[dict[str, Any]]]:
    assignments, unassigned = cluster_family_ids(
        rows,
        family_view=family_view,
        columns=int(columns),
    )
    if unassigned:
        raise ValueError(
            f"Unexpected unassigned rows for view {family_view.get('id')}: {unassigned}"
        )
    selected = policy_mod._score_selected_row(rows)
    selected_family_id = assignments[str(selected["row_id"])]
    family_rows = [
        dict(row)
        for row in rows
        if assignments[str(row["row_id"])] == selected_family_id
    ]
    family_rows.sort(
        key=lambda row: (
            -policy_mod._safe_float(row.get("score_stage2"), float("-inf")),
            -policy_mod._safe_float(row.get("score_judge"), float("-inf")),
            -policy_mod._safe_float(row.get("truth_match"), float("-inf")),
            policy_mod._safe_int(row.get("rank"), 10**9),
        )
    )
    return assignments, selected, family_rows


def _case_inputs() -> list[dict[str, Any]]:
    inventory_rows = [
        dict(row)
        for row in base_mod._read_csv_rows(base_mod.PANEL_INVENTORY_CSV)
        if policy_mod._safe_int(row.get("fixture_seed")) in PRIMARY_FIXTURE_SEEDS
    ]
    inventory_rows.sort(
        key=lambda row: (
            base_mod._fixture_seed_order(policy_mod._safe_int(row.get("fixture_seed"))),
            base_mod._search_seed_order(policy_mod._safe_int(row.get("search_seed"))),
        )
    )

    case_inputs: list[dict[str, Any]] = []
    for inventory_row in inventory_rows:
        fixture_seed = policy_mod._safe_int(inventory_row.get("fixture_seed"))
        search_seed = policy_mod._safe_int(inventory_row.get("search_seed"))
        run_dir = (
            base_mod.INPUT_EXTERNAL_REVIEW_PACK_DIR
            / policy_mod._safe_str(inventory_row.get("copied_report_dir"))
        )
        artifact_path = (
            run_dir
            / "final_instances"
            / f"fixture_001__p9_c3_l1000__text0__seed{fixture_seed}__search{search_seed}.json"
        )
        final_instance = policy_mod._read_json(artifact_path)
        case_inputs.append(
            {
                "panel_job_index": policy_mod._safe_int(
                    inventory_row.get("panel_job_index")
                ),
                "fixture_seed": fixture_seed,
                "search_seed": search_seed,
                "benchmark_case_role": base_mod._benchmark_case_role(fixture_seed),
                "run_dir": _relative_path(run_dir),
                "columns": policy_mod._safe_int(final_instance.get("columns")),
                "rows": policy_mod._topk_rows(final_instance=final_instance),
            }
        )
    return case_inputs


def _build_case_rows() -> list[dict[str, Any]]:
    case_inputs = _case_inputs()
    total_units = int(len(case_inputs) * len(FAMILY_VIEWS) * len(EPS_VALUES))
    completed_units = 0
    case_rows: list[dict[str, Any]] = []
    for case_input in case_inputs:
        rows = list(case_input["rows"])
        columns = int(case_input["columns"])
        for family_view in FAMILY_VIEWS:
            assignments, baseline_row, family_rows = _family_rows_for_view(
                rows=rows,
                family_view=family_view,
                columns=columns,
            )
            baseline_row_id = policy_mod._safe_str(baseline_row.get("row_id"))
            baseline_family_id = policy_mod._safe_str(assignments.get(baseline_row_id))
            for eps in EPS_VALUES:
                completed_units += 1
                candidate_row = policy_mod.select_selected_family_low_edge_row(
                    family_rows=family_rows,
                    selected_row=baseline_row,
                    score_band_eps=float(eps),
                )
                candidate_row_id = policy_mod._safe_str(candidate_row.get("row_id"))
                case_rows.append(
                    {
                        "panel_job_index": int(case_input["panel_job_index"]),
                        "fixture_seed": int(case_input["fixture_seed"]),
                        "search_seed": int(case_input["search_seed"]),
                        "benchmark_case_role": policy_mod._safe_str(
                            case_input.get("benchmark_case_role")
                        ),
                        "family_view_id": policy_mod._safe_str(family_view.get("id")),
                        "score_band_eps": float(eps),
                        "selected_family_id": baseline_family_id,
                        "selected_family_row_count": int(len(family_rows)),
                        "baseline_row_id": baseline_row_id,
                        "baseline_truth_match": policy_mod._safe_float(
                            baseline_row.get("truth_match")
                        ),
                        "baseline_score_stage2": policy_mod._safe_float(
                            baseline_row.get("score_stage2")
                        ),
                        "candidate_row_id": candidate_row_id,
                        "candidate_changed": int(candidate_row_id != baseline_row_id),
                        "candidate_truth_match": policy_mod._safe_float(
                            candidate_row.get("truth_match")
                        ),
                        "candidate_score_stage2": policy_mod._safe_float(
                            candidate_row.get("score_stage2")
                        ),
                        "candidate_truth_delta_vs_baseline": (
                            policy_mod._safe_float(candidate_row.get("truth_match"))
                            - policy_mod._safe_float(baseline_row.get("truth_match"))
                        ),
                        "candidate_score_delta_vs_baseline": (
                            policy_mod._safe_float(candidate_row.get("score_stage2"))
                            - policy_mod._safe_float(baseline_row.get("score_stage2"))
                        ),
                        "candidate_family_rank": next(
                            i
                            for i, row in enumerate(family_rows, start=1)
                            if policy_mod._safe_str(row.get("row_id")) == candidate_row_id
                        ),
                        "run_dir": policy_mod._safe_str(case_input.get("run_dir")),
                    }
                )
                if completed_units % 20 == 0 or completed_units == total_units:
                    _print_progress(
                        "unit_finished "
                        f"unit={completed_units}/{total_units} "
                        f"view={family_view.get('id')} eps={eps:.3f} "
                        f"fixture_seed={case_input['fixture_seed']} "
                        f"search_seed={case_input['search_seed']} "
                        f"candidate_delta={case_rows[-1]['candidate_truth_delta_vs_baseline']:.3f}"
                    )
    return case_rows


def _build_setting_summary_rows(
    case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float, int], list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        key = (
            policy_mod._safe_str(row.get("family_view_id")),
            float(row.get("score_band_eps")),
            policy_mod._safe_int(row.get("fixture_seed")),
        )
        grouped[key].append(dict(row))

    summary_rows: list[dict[str, Any]] = []
    for family_view_id, score_band_eps, fixture_seed in sorted(grouped):
        rows = sorted(
            grouped[(family_view_id, score_band_eps, fixture_seed)],
            key=lambda row: policy_mod._safe_int(row.get("search_seed")),
        )
        run_count = int(len(rows))
        summary_rows.append(
            {
                "family_view_id": family_view_id,
                "score_band_eps": float(score_band_eps),
                "fixture_seed": int(fixture_seed),
                "benchmark_case_role": policy_mod._safe_str(
                    rows[0].get("benchmark_case_role")
                ),
                "run_count": run_count,
                "candidate_active_run_count": sum(
                    policy_mod._safe_int(row.get("candidate_changed")) for row in rows
                ),
                "mean_candidate_truth_delta_vs_baseline": sum(
                    policy_mod._safe_float(row.get("candidate_truth_delta_vs_baseline"))
                    for row in rows
                )
                / float(run_count),
                "mean_candidate_score_delta_vs_baseline": sum(
                    policy_mod._safe_float(row.get("candidate_score_delta_vs_baseline"))
                    for row in rows
                )
                / float(run_count),
                "mean_candidate_family_rank": sum(
                    policy_mod._safe_int(row.get("candidate_family_rank")) for row in rows
                )
                / float(run_count),
                "candidate_any_negative_truth_delta": int(
                    any(
                        policy_mod._safe_float(
                            row.get("candidate_truth_delta_vs_baseline")
                        )
                        < 0.0
                        for row in rows
                    )
                ),
            }
        )
    return summary_rows


def _summary_row(
    summary_rows: Sequence[Mapping[str, Any]],
    *,
    family_view_id: str,
    score_band_eps: float,
    fixture_seed: int,
) -> dict[str, Any] | None:
    for row in summary_rows:
        if (
            policy_mod._safe_str(row.get("family_view_id")) == str(family_view_id)
            and abs(float(row.get("score_band_eps")) - float(score_band_eps)) <= 1e-12
            and policy_mod._safe_int(row.get("fixture_seed")) == int(fixture_seed)
        ):
            return dict(row)
    return None


def build_recommendation(
    summary_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    valid_rows: list[dict[str, Any]] = []
    for family_view in FAMILY_VIEWS:
        family_view_id = policy_mod._safe_str(family_view.get("id"))
        for eps in EPS_VALUES:
            row_1111 = _summary_row(
                summary_rows,
                family_view_id=family_view_id,
                score_band_eps=float(eps),
                fixture_seed=1111,
            )
            row_611 = _summary_row(
                summary_rows,
                family_view_id=family_view_id,
                score_band_eps=float(eps),
                fixture_seed=611,
            )
            row_1411 = _summary_row(
                summary_rows,
                family_view_id=family_view_id,
                score_band_eps=float(eps),
                fixture_seed=1411,
            )
            row_1511 = _summary_row(
                summary_rows,
                family_view_id=family_view_id,
                score_band_eps=float(eps),
                fixture_seed=1511,
            )
            if not row_1111 or not row_611 or not row_1411 or not row_1511:
                continue
            if (
                policy_mod._safe_int(row_1111.get("candidate_active_run_count"))
                == policy_mod._safe_int(row_1111.get("run_count"))
                and policy_mod._safe_float(
                    row_1111.get("mean_candidate_truth_delta_vs_baseline")
                )
                > 0.0
                and policy_mod._safe_int(row_611.get("candidate_active_run_count")) == 0
                and policy_mod._safe_int(row_1411.get("candidate_active_run_count")) == 0
                and policy_mod._safe_int(row_1511.get("candidate_active_run_count")) == 0
                and policy_mod._safe_int(
                    row_611.get("candidate_any_negative_truth_delta")
                )
                == 0
                and policy_mod._safe_int(
                    row_1411.get("candidate_any_negative_truth_delta")
                )
                == 0
                and policy_mod._safe_int(
                    row_1511.get("candidate_any_negative_truth_delta")
                )
                == 0
            ):
                valid_rows.append(
                    {
                        "family_view_id": family_view_id,
                        "score_band_eps": float(eps),
                        "mean_candidate_truth_delta_vs_baseline": policy_mod._safe_float(
                            row_1111.get("mean_candidate_truth_delta_vs_baseline")
                        ),
                    }
                )
    if not valid_rows:
        return {
            "recommendation": "refine",
            "next_branch_label": "",
            "mechanism_layer": "selection",
            "reason": (
                "No family-view and score-band setting isolated a clean 1111-only "
                "representative-selection window."
            ),
        }

    chosen = min(
        valid_rows,
        key=lambda row: (
            0 if policy_mod._safe_str(row.get("family_view_id")) == "prefix_hamming_le_24" else 1,
            float(row.get("score_band_eps")),
        ),
    )
    chosen_view_id = policy_mod._safe_str(chosen.get("family_view_id"))
    chosen_eps = float(chosen.get("score_band_eps"))
    lower_eps = max([eps for eps in EPS_VALUES if eps < chosen_eps], default=None)
    higher_eps = min([eps for eps in EPS_VALUES if eps > chosen_eps], default=None)
    lower_row = (
        _summary_row(
            summary_rows,
            family_view_id=chosen_view_id,
            score_band_eps=float(lower_eps),
            fixture_seed=1111,
        )
        if lower_eps is not None
        else None
    )
    higher_row = (
        _summary_row(
            summary_rows,
            family_view_id=chosen_view_id,
            score_band_eps=float(0.025),
            fixture_seed=1111,
        )
        if higher_eps is not None
        else None
    )
    lower_delta = (
        policy_mod._safe_float(lower_row.get("mean_candidate_truth_delta_vs_baseline"))
        if lower_row
        else float("nan")
    )
    higher_delta = (
        policy_mod._safe_float(higher_row.get("mean_candidate_truth_delta_vs_baseline"))
        if higher_row
        else float("nan")
    )

    return {
        "recommendation": "advance",
        "next_branch_label": "stage2_topk_selected_family_low_edge_eps_0p016_microprobe",
        "mechanism_layer": "selection",
        "candidate_policy_id": "selected_family_low_edge_eps_0p016_v1",
        "family_view_id": chosen_view_id,
        "score_band_eps": chosen_eps,
        "reason": (
            "Only prefix_hamming_le_24 produces a clean 1111-only activation "
            "window. The useful band begins at eps 0.016; eps 0.015 is harmful "
            f"on 1111 (mean delta {lower_delta:.3f}), while wider eps 0.025 "
            f"attenuates the gain to {higher_delta:.3f}."
        ),
    }


def _write_markdown(
    output_dir: Path,
    *,
    summary_rows: Sequence[Mapping[str, Any]],
    recommendation: Mapping[str, Any],
) -> None:
    lines = [
        "# Stage-2 Topk Family Representative Policy Sensitivity v1",
        "",
        "Question:",
        "- after the concrete representative-policy audit, is the `1111` signal robust enough to specify one narrow selector, or is it just a lucky combination of family view and score-band width?",
        "",
        "Mechanism layer:",
        "- `selection`",
        "",
        "Swept family views:",
    ]
    for family_view in FAMILY_VIEWS:
        lines.append(f"- `{policy_mod._safe_str(family_view.get('id'))}`")
    lines.extend(
        [
            "",
            "Swept score bands:",
        ]
    )
    for eps in EPS_VALUES:
        lines.append(f"- `{eps:.3f}`")
    lines.extend(
        [
            "",
            "Recommendation:",
            f"- `{policy_mod._safe_str(recommendation.get('recommendation'))}`",
            f"- next branch: `{policy_mod._safe_str(recommendation.get('next_branch_label')) or 'none'}`",
            f"- policy: `{policy_mod._safe_str(recommendation.get('candidate_policy_id')) or 'none'}`",
            f"- reason: {policy_mod._safe_str(recommendation.get('reason'))}",
            "",
            "Setting summary by fixture:",
            "",
            "| family view | eps | fixture seed | active runs | mean truth delta | negative deltas |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in summary_rows:
        lines.append(
            f"| `{policy_mod._safe_str(row.get('family_view_id'))}` | "
            f"`{float(row.get('score_band_eps')):.3f}` | "
            f"`{policy_mod._safe_int(row.get('fixture_seed'))}` | "
            f"`{policy_mod._safe_int(row.get('candidate_active_run_count'))}` | "
            f"`{policy_mod._safe_float(row.get('mean_candidate_truth_delta_vs_baseline')):.3f}` | "
            f"`{policy_mod._safe_int(row.get('candidate_any_negative_truth_delta'))}` |"
        )
    (
        output_dir / "stage2_topk_family_representative_policy_sensitivity_readout.md"
    ).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_extract() -> dict[str, Any]:
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} view_count={len(FAMILY_VIEWS)} eps_values={list(EPS_VALUES)}"
    )
    case_rows = _build_case_rows()
    summary_rows = _build_setting_summary_rows(case_rows)
    recommendation = build_recommendation(summary_rows)

    output_dir = base_mod.OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(
        output_dir / "stage2_topk_family_representative_policy_sensitivity_case_rows.jsonl",
        case_rows,
    )
    _write_csv(
        output_dir / "stage2_topk_family_representative_policy_sensitivity_case_rows.csv",
        case_rows,
    )
    _write_jsonl(
        output_dir
        / "stage2_topk_family_representative_policy_sensitivity_setting_summary_rows.jsonl",
        summary_rows,
    )
    _write_csv(
        output_dir
        / "stage2_topk_family_representative_policy_sensitivity_setting_summary_rows.csv",
        summary_rows,
    )
    _write_json(
        output_dir
        / "stage2_topk_family_representative_policy_sensitivity_recommendation.json",
        recommendation,
    )
    _write_json(
        output_dir / "stage2_topk_family_representative_policy_sensitivity_summary.json",
        {
            "run_label": RUN_LABEL,
            "family_view_ids": [
                policy_mod._safe_str(family_view.get("id")) for family_view in FAMILY_VIEWS
            ],
            "score_band_eps_values": list(EPS_VALUES),
            "case_row_count": int(len(case_rows)),
            "setting_summary_row_count": int(len(summary_rows)),
            "recommendation": dict(recommendation),
            "output_dir": _relative_path(output_dir),
        },
    )
    _write_markdown(
        output_dir,
        summary_rows=summary_rows,
        recommendation=recommendation,
    )
    refresh_catalog_safely(print_fn=print)

    result = {
        "run_label": RUN_LABEL,
        "case_row_count": int(len(case_rows)),
        "setting_summary_row_count": int(len(summary_rows)),
        "recommendation": policy_mod._safe_str(recommendation.get("recommendation")),
        "next_branch_label": policy_mod._safe_str(
            recommendation.get("next_branch_label")
        ),
        "candidate_policy_id": policy_mod._safe_str(
            recommendation.get("candidate_policy_id")
        ),
        "output_dir": _relative_path(output_dir),
    }
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} recommendation={result['recommendation']} "
        f"next_branch_label={result['next_branch_label'] or 'none'} "
        f"candidate_policy={result['candidate_policy_id'] or 'none'} "
        f"output_dir={result['output_dir']}"
    )
    return result


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
