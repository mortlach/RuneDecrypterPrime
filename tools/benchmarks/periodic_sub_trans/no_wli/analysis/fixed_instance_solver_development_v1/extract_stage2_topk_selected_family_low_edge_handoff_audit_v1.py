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
        "extract_stage2_topk_selected_family_low_edge_handoff_audit_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as ar  # noqa: E402
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (  # noqa: E402
    refresh_catalog_safely,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    extract_fixed_instance_solver_development_v1 as base_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    extract_stage2_topk_family_representative_policy_audit_v1 as policy_mod,
)


RUN_LABEL = "stage2_topk_selected_family_low_edge_handoff_audit_v1"
PRIMARY_FIXTURE_SEEDS = (611, 1111, 1411, 1511)
POLICY_ID = "selected_family_low_edge_eps_0p016_v1"
POLICY_SCORE_BAND_EPS = 0.016


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


def _list_edit_count(
    baseline: Sequence[Sequence[int]],
    candidate: Sequence[Sequence[int]],
) -> int:
    max_len = max(len(baseline), len(candidate))
    edit_count = 0
    for index in range(max_len):
        baseline_row = tuple(baseline[index]) if index < len(baseline) else None
        candidate_row = tuple(candidate[index]) if index < len(candidate) else None
        if baseline_row != candidate_row:
            edit_count += 1
    return int(edit_count)


def _build_case_rows() -> list[dict[str, Any]]:
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

    case_rows: list[dict[str, Any]] = []
    total = int(len(inventory_rows))
    for index, inventory_row in enumerate(inventory_rows, start=1):
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
        case = ar.load_artifact_case(artifact_path=artifact_path)
        saved_bundle = ar.prepare_stage3_resume_inputs_from_case(
            case,
            case.run_config,
            prefer_saved_stage3_prep=True,
        )
        saved_prep = dict(saved_bundle["stage3_prep"])
        final_instance = policy_mod._read_json(artifact_path)
        topk_rows = policy_mod._topk_rows(final_instance=final_instance)
        _, baseline_row, family_rows = policy_mod._family_rows_for_selected(
            rows=topk_rows,
            columns=policy_mod._safe_int(final_instance.get("columns")),
        )
        candidate_row = policy_mod.select_selected_family_low_edge_row(
            family_rows=family_rows,
            selected_row=baseline_row,
            score_band_eps=POLICY_SCORE_BAND_EPS,
        )
        candidate_prep = policy_mod._stage3_prep_for_best2_override(
            case=case,
            saved_bundle=saved_bundle,
            override_row=candidate_row,
        )
        baseline_best2_key = list(saved_bundle["stage2_resume"].best2_key)
        candidate_best2_key = list(candidate_row.get("key", []) or [])
        baseline_init3 = [
            list(key) for key in list(saved_prep.get("init3", []) or [])
        ]
        candidate_init3 = [
            list(key) for key in list(candidate_prep.get("init3", []) or [])
        ]
        baseline_promoted = [
            list(key) for key in list(saved_prep.get("promoted_keys", []) or [])
        ]
        candidate_promoted = [
            list(key) for key in list(candidate_prep.get("promoted_keys", []) or [])
        ]

        case_rows.append(
            {
                "panel_job_index": policy_mod._safe_int(
                    inventory_row.get("panel_job_index")
                ),
                "fixture_seed": fixture_seed,
                "search_seed": search_seed,
                "benchmark_case_role": base_mod._benchmark_case_role(fixture_seed),
                "candidate_policy_id": POLICY_ID,
                "baseline_row_id": policy_mod._safe_str(baseline_row.get("row_id")),
                "candidate_row_id": policy_mod._safe_str(candidate_row.get("row_id")),
                "candidate_changed": int(
                    policy_mod._safe_str(candidate_row.get("row_id"))
                    != policy_mod._safe_str(baseline_row.get("row_id"))
                ),
                "baseline_truth_match": policy_mod._safe_float(
                    baseline_row.get("truth_match")
                ),
                "candidate_truth_match": policy_mod._safe_float(
                    candidate_row.get("truth_match")
                ),
                "candidate_truth_delta_vs_baseline": (
                    policy_mod._safe_float(candidate_row.get("truth_match"))
                    - policy_mod._safe_float(baseline_row.get("truth_match"))
                ),
                "best2_key_changed": int(baseline_best2_key != candidate_best2_key),
                "stage3_promoted_keys_changed": int(
                    baseline_promoted != candidate_promoted
                ),
                "stage3_promoted_keys_edit_count": _list_edit_count(
                    baseline_promoted,
                    candidate_promoted,
                ),
                "stage3_promoted_keys_count": policy_mod._safe_int(
                    saved_prep.get("stage3_promoted_keys_count")
                ),
                "init3_changed": int(baseline_init3 != candidate_init3),
                "init3_edit_count": _list_edit_count(
                    baseline_init3,
                    candidate_init3,
                ),
                "init3_count": policy_mod._safe_int(saved_prep.get("init3_n")),
                "run_dir": _relative_path(run_dir),
            }
        )
        _print_progress(
            "case_finished "
            f"unit={index}/{total} fixture_seed={fixture_seed} search_seed={search_seed} "
            f"candidate_changed={case_rows[-1]['candidate_changed']} "
            f"best2_key_changed={case_rows[-1]['best2_key_changed']} "
            f"init3_edit_count={case_rows[-1]['init3_edit_count']}"
        )
    return case_rows


def _build_fixture_summary_rows(
    case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        grouped[policy_mod._safe_int(row.get("fixture_seed"))].append(dict(row))

    summary_rows: list[dict[str, Any]] = []
    for fixture_seed in sorted(grouped):
        rows = sorted(
            grouped[fixture_seed],
            key=lambda row: policy_mod._safe_int(row.get("search_seed")),
        )
        run_count = int(len(rows))
        summary_rows.append(
            {
                "fixture_seed": int(fixture_seed),
                "benchmark_case_role": policy_mod._safe_str(
                    rows[0].get("benchmark_case_role")
                ),
                "run_count": run_count,
                "candidate_active_run_count": sum(
                    policy_mod._safe_int(row.get("candidate_changed")) for row in rows
                ),
                "best2_key_changed_run_count": sum(
                    policy_mod._safe_int(row.get("best2_key_changed")) for row in rows
                ),
                "init3_changed_run_count": sum(
                    policy_mod._safe_int(row.get("init3_changed")) for row in rows
                ),
                "mean_candidate_truth_delta_vs_baseline": sum(
                    policy_mod._safe_float(row.get("candidate_truth_delta_vs_baseline"))
                    for row in rows
                )
                / float(run_count),
                "mean_init3_edit_count": sum(
                    policy_mod._safe_int(row.get("init3_edit_count")) for row in rows
                )
                / float(run_count),
                "mean_stage3_promoted_keys_edit_count": sum(
                    policy_mod._safe_int(row.get("stage3_promoted_keys_edit_count"))
                    for row in rows
                )
                / float(run_count),
            }
        )
    return summary_rows


def build_recommendation(
    fixture_summary_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    summary_by_seed = {
        policy_mod._safe_int(row.get("fixture_seed")): dict(row)
        for row in fixture_summary_rows
    }
    row_1111 = summary_by_seed.get(1111)
    row_611 = summary_by_seed.get(611)
    row_1411 = summary_by_seed.get(1411)
    row_1511 = summary_by_seed.get(1511)
    if not row_1111 or not row_611 or not row_1411 or not row_1511:
        return {
            "recommendation": "incomplete",
            "next_branch_label": "",
            "mechanism_layer": "selection",
            "reason": "Primary fixture coverage incomplete for handoff audit.",
        }

    if (
        policy_mod._safe_int(row_1111.get("best2_key_changed_run_count"))
        == policy_mod._safe_int(row_1111.get("run_count"))
        and policy_mod._safe_int(row_1111.get("init3_changed_run_count"))
        == policy_mod._safe_int(row_1111.get("run_count"))
        and policy_mod._safe_float(row_1111.get("mean_init3_edit_count")) >= 1.0
        and policy_mod._safe_int(row_611.get("best2_key_changed_run_count")) == 0
        and policy_mod._safe_int(row_611.get("init3_changed_run_count")) == 0
        and policy_mod._safe_int(row_1411.get("best2_key_changed_run_count")) == 0
        and policy_mod._safe_int(row_1411.get("init3_changed_run_count")) == 0
        and policy_mod._safe_int(row_1511.get("best2_key_changed_run_count")) == 0
        and policy_mod._safe_int(row_1511.get("init3_changed_run_count")) == 0
    ):
        return {
            "recommendation": "advance",
            "next_branch_label": "stage2_topk_selected_family_low_edge_eps_0p016_microprobe",
            "mechanism_layer": "selection",
            "candidate_policy_id": POLICY_ID,
            "reason": (
                "The concrete selector changes best2_key and the saved Stage-3 "
                "handoff on all five retained 1111 lanes, while remaining inert "
                "on 611, 1411, and 1511."
            ),
        }

    return {
        "recommendation": "refine",
        "next_branch_label": "",
        "mechanism_layer": "selection",
        "candidate_policy_id": POLICY_ID,
        "reason": (
            "The concrete selector does not yet show a clean 1111-only Stage-3 "
            "handoff change pattern."
        ),
    }


def _write_markdown(
    output_dir: Path,
    *,
    case_rows: Sequence[Mapping[str, Any]],
    fixture_summary_rows: Sequence[Mapping[str, Any]],
    recommendation: Mapping[str, Any],
) -> None:
    lines = [
        "# Stage-2 Topk Selected-Family Low-Edge Handoff Audit v1",
        "",
        "Question:",
        "- after narrowing the selector to `selected_family_low_edge_eps_0p016_v1`, does it materially change the saved Stage-2 to Stage-3 handoff on `1111`, or is it effectively a no-op before Stage 3 starts?",
        "",
        "Mechanism layer:",
        "- `selection`",
        "",
        "Policy:",
        f"- `{POLICY_ID}`",
        f"- family view: `{policy_mod.PRIMARY_VIEW_ID}`",
        f"- score band eps: `{POLICY_SCORE_BAND_EPS:.3f}`",
        "",
        "Recommendation:",
        f"- `{policy_mod._safe_str(recommendation.get('recommendation'))}`",
        f"- next branch: `{policy_mod._safe_str(recommendation.get('next_branch_label')) or 'none'}`",
        f"- reason: {policy_mod._safe_str(recommendation.get('reason'))}",
        "",
        "Fixture summary:",
        "",
        "| fixture seed | role | active runs | best2 changed | init3 changed | mean truth delta | mean init3 edit count | mean promoted edit count |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in fixture_summary_rows:
        lines.append(
            f"| `{policy_mod._safe_int(row.get('fixture_seed'))}` | "
            f"`{policy_mod._safe_str(row.get('benchmark_case_role'))}` | "
            f"`{policy_mod._safe_int(row.get('candidate_active_run_count'))}` | "
            f"`{policy_mod._safe_int(row.get('best2_key_changed_run_count'))}` | "
            f"`{policy_mod._safe_int(row.get('init3_changed_run_count'))}` | "
            f"`{policy_mod._safe_float(row.get('mean_candidate_truth_delta_vs_baseline')):.3f}` | "
            f"`{policy_mod._safe_float(row.get('mean_init3_edit_count')):.1f}` | "
            f"`{policy_mod._safe_float(row.get('mean_stage3_promoted_keys_edit_count')):.1f}` |"
        )
    lines.extend(
        [
            "",
            "Per-run case table:",
            "",
            "| fixture seed | search seed | candidate changed | best2 changed | init3 changed | init3 edit count | promoted edit count | truth delta |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in case_rows:
        lines.append(
            f"| `{policy_mod._safe_int(row.get('fixture_seed'))}` | "
            f"`{policy_mod._safe_int(row.get('search_seed'))}` | "
            f"`{policy_mod._safe_int(row.get('candidate_changed'))}` | "
            f"`{policy_mod._safe_int(row.get('best2_key_changed'))}` | "
            f"`{policy_mod._safe_int(row.get('init3_changed'))}` | "
            f"`{policy_mod._safe_int(row.get('init3_edit_count'))}` | "
            f"`{policy_mod._safe_int(row.get('stage3_promoted_keys_edit_count'))}` | "
            f"`{policy_mod._safe_float(row.get('candidate_truth_delta_vs_baseline')):.3f}` |"
        )
    (
        output_dir / "stage2_topk_selected_family_low_edge_handoff_audit_readout.md"
    ).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_extract() -> dict[str, Any]:
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} candidate_policy={POLICY_ID} "
        f"score_band_eps={POLICY_SCORE_BAND_EPS:.3f}"
    )
    case_rows = _build_case_rows()
    fixture_summary_rows = _build_fixture_summary_rows(case_rows)
    recommendation = build_recommendation(fixture_summary_rows)

    output_dir = base_mod.OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(
        output_dir / "stage2_topk_selected_family_low_edge_handoff_audit_case_rows.jsonl",
        case_rows,
    )
    _write_csv(
        output_dir / "stage2_topk_selected_family_low_edge_handoff_audit_case_rows.csv",
        case_rows,
    )
    _write_jsonl(
        output_dir
        / "stage2_topk_selected_family_low_edge_handoff_audit_fixture_summary_rows.jsonl",
        fixture_summary_rows,
    )
    _write_csv(
        output_dir
        / "stage2_topk_selected_family_low_edge_handoff_audit_fixture_summary_rows.csv",
        fixture_summary_rows,
    )
    _write_json(
        output_dir / "stage2_topk_selected_family_low_edge_handoff_audit_recommendation.json",
        recommendation,
    )
    _write_json(
        output_dir / "stage2_topk_selected_family_low_edge_handoff_audit_summary.json",
        {
            "run_label": RUN_LABEL,
            "candidate_policy_id": POLICY_ID,
            "score_band_eps": POLICY_SCORE_BAND_EPS,
            "case_row_count": int(len(case_rows)),
            "fixture_summary_row_count": int(len(fixture_summary_rows)),
            "recommendation": dict(recommendation),
            "output_dir": _relative_path(output_dir),
        },
    )
    _write_markdown(
        output_dir,
        case_rows=case_rows,
        fixture_summary_rows=fixture_summary_rows,
        recommendation=recommendation,
    )
    refresh_catalog_safely(print_fn=print)

    result = {
        "run_label": RUN_LABEL,
        "candidate_policy_id": POLICY_ID,
        "case_row_count": int(len(case_rows)),
        "fixture_summary_row_count": int(len(fixture_summary_rows)),
        "recommendation": policy_mod._safe_str(recommendation.get("recommendation")),
        "next_branch_label": policy_mod._safe_str(
            recommendation.get("next_branch_label")
        ),
        "output_dir": _relative_path(output_dir),
    }
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} recommendation={result['recommendation']} "
        f"next_branch_label={result['next_branch_label'] or 'none'} "
        f"output_dir={result['output_dir']}"
    )
    return result


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
