from __future__ import annotations

import csv
import datetime as dt
import json
import math
import sys
import time
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
        "extract_stage2_topk_family_representative_policy_audit_v1.py"
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
from tools.benchmarks.periodic_sub_trans.no_wli.family_views import (  # noqa: E402
    find_family_view,
    cluster_family_ids,
)


RUN_LABEL = "stage2_topk_family_representative_policy_audit_v1"
PRIMARY_VIEW_ID = "prefix_hamming_le_24"
PRIMARY_VIEW = find_family_view(PRIMARY_VIEW_ID)
if PRIMARY_VIEW is None:
    raise RuntimeError(f"Missing family view: {PRIMARY_VIEW_ID}")
PRIMARY_FIXTURE_SEEDS = (611, 1111, 1511, 1411)
POLICY_ID = "selected_family_low_edge_eps_0p020_v1"
POLICY_SCORE_BAND_EPS = 0.020


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _utc_label() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _timestamp() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _print_progress(message: str) -> None:
    print(f"[{_timestamp()}] {message}", flush=True)


def _safe_str(value: Any) -> str:
    return str(value or "")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(number):
        return float(default)
    return float(number)


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


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _artifact_stem(*, fixture_seed: int, search_seed: int) -> str:
    return f"fixture_001__p9_c3_l1000__text0__seed{int(fixture_seed)}__search{int(search_seed)}"


def _topk_rows(
    *,
    final_instance: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(final_instance.get("stage2_topk", []) or [], start=1):
        rows.append(
            {
                "row_id": f"stage2_topk:{index}",
                "rank": _safe_int(row.get("rank"), index),
                "key": list(row.get("key_idx", []) or []),
                "truth_match": _safe_float(row.get("match_ratio")),
                "score_stage2": _safe_float(row.get("score_stage2")),
                "score_judge": _safe_float(row.get("score_judge")),
            }
        )
    return rows


def _score_selected_row(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return max(
        rows,
        key=lambda row: (
            _safe_float(row.get("score_stage2"), float("-inf")),
            _safe_float(row.get("score_judge"), float("-inf")),
            _safe_float(row.get("truth_match"), float("-inf")),
            -_safe_int(row.get("rank"), 10**9),
        ),
    )


def _family_rows_for_selected(
    *,
    rows: Sequence[Mapping[str, Any]],
    columns: int,
) -> tuple[dict[str, str], dict[str, Any], list[dict[str, Any]]]:
    assignments, unassigned = cluster_family_ids(
        rows,
        family_view=PRIMARY_VIEW,
        columns=int(columns),
    )
    if unassigned:
        raise ValueError(f"Unexpected unassigned topk rows: {unassigned}")
    selected = _score_selected_row(rows)
    selected_family_id = assignments[str(selected["row_id"])]
    family_rows = [
        dict(row)
        for row in rows
        if assignments[str(row["row_id"])] == selected_family_id
    ]
    family_rows.sort(
        key=lambda row: (
            -_safe_float(row.get("score_stage2"), float("-inf")),
            -_safe_float(row.get("score_judge"), float("-inf")),
            -_safe_float(row.get("truth_match"), float("-inf")),
            _safe_int(row.get("rank"), 10**9),
        )
    )
    return assignments, selected, family_rows


def select_selected_family_low_edge_row(
    *,
    family_rows: Sequence[Mapping[str, Any]],
    selected_row: Mapping[str, Any],
    score_band_eps: float,
) -> dict[str, Any]:
    selected_score = _safe_float(selected_row.get("score_stage2"))
    band_rows = [
        dict(row)
        for row in family_rows
        if (selected_score - _safe_float(row.get("score_stage2")))
        <= float(score_band_eps) + 1e-12
    ]
    if not band_rows:
        return dict(selected_row)
    return min(
        band_rows,
        key=lambda row: (
            _safe_float(row.get("score_stage2"), float("inf")),
            _safe_float(row.get("score_judge"), float("inf")),
            -_safe_int(row.get("rank"), 0),
        ),
    )


def _oracle_family_best_truth_row(
    family_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return max(
        family_rows,
        key=lambda row: (
            _safe_float(row.get("truth_match"), float("-inf")),
            _safe_float(row.get("score_stage2"), float("-inf")),
            _safe_float(row.get("score_judge"), float("-inf")),
            -_safe_int(row.get("rank"), 10**9),
        ),
    )


def _stage3_prep_for_best2_override(
    *,
    case: ar.phasec_replay_mod.ArtifactCase,
    saved_bundle: Mapping[str, Any],
    override_row: Mapping[str, Any],
) -> dict[str, Any]:
    resume = saved_bundle["stage2_resume"]
    override_resume = ar.Stage2ResumeInputs(
        best2_key=list(override_row.get("key", []) or []),
        best2_pt=list(resume.best2_pt),
        best2_score=_safe_float(override_row.get("score_stage2")),
        best2_match=_safe_float(override_row.get("truth_match")),
        best2_preview=_safe_str(resume.best2_preview),
        stage2_promoted=[dict(row) for row in list(resume.stage2_promoted)],
        stage2_entry_score=_safe_float(resume.stage2_entry_score),
        stage2_entry_score_judge=_safe_float(resume.stage2_entry_score_judge),
        stage2_topk_row_count=_safe_int(resume.stage2_topk_row_count),
        stage2_promote_top_cfg=_safe_int(resume.stage2_promote_top_cfg),
        stage2_promoted_from_topk_count=_safe_int(
            resume.stage2_promoted_from_topk_count
        ),
    )
    return ar._build_stage3_prep_from_stage2_resume(
        resume=override_resume,
        artifact=case.artifact,
        run_config=case.run_config,
    )


def _build_case_rows() -> list[dict[str, Any]]:
    inventory_rows = [
        dict(row)
        for row in base_mod._read_csv_rows(base_mod.PANEL_INVENTORY_CSV)
        if _safe_int(row.get("fixture_seed")) in PRIMARY_FIXTURE_SEEDS
    ]
    inventory_rows.sort(
        key=lambda row: (
            base_mod._fixture_seed_order(_safe_int(row.get("fixture_seed"))),
            base_mod._search_seed_order(_safe_int(row.get("search_seed"))),
        )
    )

    total = int(len(inventory_rows))
    started = time.perf_counter()
    case_rows: list[dict[str, Any]] = []
    for index, inventory_row in enumerate(inventory_rows, start=1):
        fixture_seed = _safe_int(inventory_row.get("fixture_seed"))
        search_seed = _safe_int(inventory_row.get("search_seed"))
        run_dir = (
            base_mod.INPUT_EXTERNAL_REVIEW_PACK_DIR
            / _safe_str(inventory_row.get("copied_report_dir"))
        )
        artifact_path = run_dir / "final_instances" / f"{_artifact_stem(fixture_seed=fixture_seed, search_seed=search_seed)}.json"
        case = ar.load_artifact_case(artifact_path=artifact_path)
        saved_bundle = ar.prepare_stage3_resume_inputs_from_case(
            case,
            case.run_config,
            prefer_saved_stage3_prep=True,
        )
        saved_prep = dict(saved_bundle["stage3_prep"])
        final_instance = _read_json(artifact_path)
        columns = _safe_int(final_instance.get("columns"))
        topk_rows = _topk_rows(final_instance=final_instance)
        assignments, baseline_row, family_rows = _family_rows_for_selected(
            rows=topk_rows,
            columns=columns,
        )
        candidate_row = select_selected_family_low_edge_row(
            family_rows=family_rows,
            selected_row=baseline_row,
            score_band_eps=POLICY_SCORE_BAND_EPS,
        )
        oracle_row = _oracle_family_best_truth_row(family_rows)
        candidate_prep = _stage3_prep_for_best2_override(
            case=case,
            saved_bundle=saved_bundle,
            override_row=candidate_row,
        )
        oracle_prep = _stage3_prep_for_best2_override(
            case=case,
            saved_bundle=saved_bundle,
            override_row=oracle_row,
        )

        baseline_row_id = _safe_str(baseline_row.get("row_id"))
        baseline_family_id = _safe_str(assignments.get(baseline_row_id))
        case_rows.append(
            {
                "panel_job_index": _safe_int(inventory_row.get("panel_job_index")),
                "fixture_seed": fixture_seed,
                "search_seed": search_seed,
                "benchmark_case_role": base_mod._benchmark_case_role(fixture_seed),
                "status": _safe_str(inventory_row.get("status")),
                "best_stage": _safe_str(inventory_row.get("best_stage")),
                "final_best_match_ratio": _safe_float(inventory_row.get("best_match_ratio")),
                "family_view_id": PRIMARY_VIEW_ID,
                "selected_family_id": baseline_family_id,
                "selected_family_row_count": int(len(family_rows)),
                "baseline_row_id": baseline_row_id,
                "baseline_family_rank": next(
                    i for i, row in enumerate(family_rows, start=1)
                    if _safe_str(row.get("row_id")) == baseline_row_id
                ),
                "baseline_truth_match": _safe_float(baseline_row.get("truth_match")),
                "baseline_score_stage2": _safe_float(baseline_row.get("score_stage2")),
                "candidate_policy_id": POLICY_ID,
                "candidate_row_id": _safe_str(candidate_row.get("row_id")),
                "candidate_changed": int(
                    _safe_str(candidate_row.get("row_id")) != baseline_row_id
                ),
                "candidate_family_rank": next(
                    i for i, row in enumerate(family_rows, start=1)
                    if _safe_str(row.get("row_id"))
                    == _safe_str(candidate_row.get("row_id"))
                ),
                "candidate_truth_match": _safe_float(candidate_row.get("truth_match")),
                "candidate_score_stage2": _safe_float(
                    candidate_row.get("score_stage2")
                ),
                "candidate_truth_delta_vs_baseline": (
                    _safe_float(candidate_row.get("truth_match"))
                    - _safe_float(baseline_row.get("truth_match"))
                ),
                "candidate_score_delta_vs_baseline": (
                    _safe_float(candidate_row.get("score_stage2"))
                    - _safe_float(baseline_row.get("score_stage2"))
                ),
                "oracle_row_id": _safe_str(oracle_row.get("row_id")),
                "oracle_family_rank": next(
                    i for i, row in enumerate(family_rows, start=1)
                    if _safe_str(row.get("row_id")) == _safe_str(oracle_row.get("row_id"))
                ),
                "oracle_truth_match": _safe_float(oracle_row.get("truth_match")),
                "oracle_score_stage2": _safe_float(oracle_row.get("score_stage2")),
                "oracle_truth_delta_vs_baseline": (
                    _safe_float(oracle_row.get("truth_match"))
                    - _safe_float(baseline_row.get("truth_match"))
                ),
                "candidate_matches_oracle": int(
                    _safe_str(candidate_row.get("row_id"))
                    == _safe_str(oracle_row.get("row_id"))
                ),
                "saved_init3_count": _safe_int(saved_prep.get("init3_n")),
                "candidate_init3_changed": int(
                    list(saved_prep.get("init3", []) or [])
                    != list(candidate_prep.get("init3", []) or [])
                ),
                "oracle_init3_changed": int(
                    list(saved_prep.get("init3", []) or [])
                    != list(oracle_prep.get("init3", []) or [])
                ),
                "run_dir": _relative_path(run_dir),
            }
        )

        elapsed_seconds = time.perf_counter() - started
        mean_seconds = elapsed_seconds / float(index)
        remaining = max(0, total - index)
        eta_seconds = mean_seconds * float(remaining)
        _print_progress(
            "case_finished "
            f"unit={index}/{total} fixture_seed={fixture_seed} search_seed={search_seed} "
            f"elapsed={elapsed_seconds:.1f}s eta={eta_seconds:.1f}s "
            f"candidate_changed={case_rows[-1]['candidate_changed']} "
            f"candidate_truth_delta={case_rows[-1]['candidate_truth_delta_vs_baseline']:.3f}"
        )

    return case_rows


def _build_fixture_summary_rows(
    case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        grouped[_safe_int(row.get("fixture_seed"))].append(dict(row))

    summary_rows: list[dict[str, Any]] = []
    for fixture_seed in sorted(grouped):
        rows = sorted(grouped[fixture_seed], key=lambda row: _safe_int(row.get("search_seed")))
        run_count = int(len(rows))
        summary_rows.append(
            {
                "fixture_seed": int(fixture_seed),
                "benchmark_case_role": _safe_str(rows[0].get("benchmark_case_role")),
                "run_count": run_count,
                "candidate_active_run_count": sum(
                    _safe_int(row.get("candidate_changed")) for row in rows
                ),
                "candidate_oracle_match_run_count": sum(
                    _safe_int(row.get("candidate_matches_oracle")) for row in rows
                ),
                "mean_candidate_truth_delta_vs_baseline": sum(
                    _safe_float(row.get("candidate_truth_delta_vs_baseline")) for row in rows
                )
                / float(run_count),
                "mean_oracle_truth_delta_vs_baseline": sum(
                    _safe_float(row.get("oracle_truth_delta_vs_baseline")) for row in rows
                )
                / float(run_count),
                "mean_candidate_score_delta_vs_baseline": sum(
                    _safe_float(row.get("candidate_score_delta_vs_baseline")) for row in rows
                )
                / float(run_count),
                "mean_candidate_family_rank": sum(
                    _safe_int(row.get("candidate_family_rank")) for row in rows
                )
                / float(run_count),
                "mean_oracle_family_rank": sum(
                    _safe_int(row.get("oracle_family_rank")) for row in rows
                )
                / float(run_count),
                "candidate_any_negative_truth_delta": int(
                    any(
                        _safe_float(row.get("candidate_truth_delta_vs_baseline")) < 0.0
                        for row in rows
                    )
                ),
            }
        )

    return summary_rows


def build_recommendation(
    fixture_summary_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    summary_by_seed = {
        _safe_int(row.get("fixture_seed")): dict(row) for row in fixture_summary_rows
    }
    row_1111 = summary_by_seed.get(1111)
    row_611 = summary_by_seed.get(611)
    row_1511 = summary_by_seed.get(1511)
    row_1411 = summary_by_seed.get(1411)

    if not row_1111 or not row_611 or not row_1511:
        return {
            "recommendation": "incomplete",
            "next_branch_label": "",
            "reason": "Primary fixture coverage incomplete for representative-policy audit.",
        }

    active_1111 = _safe_int(row_1111.get("candidate_active_run_count"))
    run_count_1111 = _safe_int(row_1111.get("run_count"))
    delta_1111 = _safe_float(row_1111.get("mean_candidate_truth_delta_vs_baseline"))
    negative_611 = _safe_int(row_611.get("candidate_any_negative_truth_delta"))
    negative_1511 = _safe_int(row_1511.get("candidate_any_negative_truth_delta"))
    active_611 = _safe_int(row_611.get("candidate_active_run_count"))
    active_1511 = _safe_int(row_1511.get("candidate_active_run_count"))
    active_1411 = _safe_int((row_1411 or {}).get("candidate_active_run_count"))

    if (
        active_1111 == run_count_1111
        and delta_1111 > 0.05
        and negative_611 == 0
        and negative_1511 == 0
        and active_611 == 0
        and active_1511 == 0
        and active_1411 == 0
    ):
        return {
            "recommendation": "advance",
            "next_branch_label": "stage2_topk_selected_family_low_edge_microprobe",
            "mechanism_layer": "selection",
            "candidate_policy_id": POLICY_ID,
            "reason": (
                "The family-band-edge selector stays inert on 611/1411/1511 and "
                "switches only on 1111, where it recovers the hidden stronger "
                "same-family representative on all five retained lanes."
            ),
        }

    return {
        "recommendation": "refine",
        "next_branch_label": "",
        "mechanism_layer": "selection",
        "candidate_policy_id": POLICY_ID,
        "reason": (
            "The family-band-edge selector does not yet isolate a clean narrow "
            "candidate across the fixed panel."
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
        "# Stage-2 Topk Family Representative Policy Audit v1",
        "",
        "Question:",
        "- after the upstream family audit, can one simple live-safe selector on the saved `stage2_topk` surface recover the hidden stronger `1111` representative without moving the controls?",
        "",
        "Mechanism layer:",
        "- `selection`",
        "",
        "Candidate policy:",
        f"- `{POLICY_ID}`",
        f"- choose the lowest-score row inside the score-selected family whose score is within `{POLICY_SCORE_BAND_EPS:.3f}` of the family score winner",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- next branch: `{_safe_str(recommendation.get('next_branch_label')) or 'none'}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Fixture summary:",
        "",
        "| fixture seed | role | runs | candidate active runs | oracle-match runs | mean candidate truth delta | mean oracle truth delta | negative deltas present |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in fixture_summary_rows:
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}` | "
            f"`{_safe_str(row.get('benchmark_case_role'))}` | "
            f"`{_safe_int(row.get('run_count'))}` | "
            f"`{_safe_int(row.get('candidate_active_run_count'))}` | "
            f"`{_safe_int(row.get('candidate_oracle_match_run_count'))}` | "
            f"`{_safe_float(row.get('mean_candidate_truth_delta_vs_baseline')):.3f}` | "
            f"`{_safe_float(row.get('mean_oracle_truth_delta_vs_baseline')):.3f}` | "
            f"`{_safe_int(row.get('candidate_any_negative_truth_delta'))}` |"
        )

    lines.extend(
        [
            "",
            "Per-run case table:",
            "",
            "| fixture seed | search seed | baseline truth | candidate truth | candidate delta | oracle truth | candidate changed | candidate==oracle | candidate rank | oracle rank | init3 changed |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in case_rows:
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}` | "
            f"`{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_float(row.get('baseline_truth_match')):.3f}` | "
            f"`{_safe_float(row.get('candidate_truth_match')):.3f}` | "
            f"`{_safe_float(row.get('candidate_truth_delta_vs_baseline')):.3f}` | "
            f"`{_safe_float(row.get('oracle_truth_match')):.3f}` | "
            f"`{_safe_int(row.get('candidate_changed'))}` | "
            f"`{_safe_int(row.get('candidate_matches_oracle'))}` | "
            f"`{_safe_int(row.get('candidate_family_rank'))}` | "
            f"`{_safe_int(row.get('oracle_family_rank'))}` | "
            f"`{_safe_int(row.get('candidate_init3_changed'))}` |"
        )

    (output_dir / "stage2_topk_family_representative_policy_audit_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


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
        output_dir / "stage2_topk_family_representative_policy_case_rows.jsonl",
        case_rows,
    )
    _write_csv(
        output_dir / "stage2_topk_family_representative_policy_case_rows.csv",
        case_rows,
    )
    _write_jsonl(
        output_dir / "stage2_topk_family_representative_policy_fixture_summary_rows.jsonl",
        fixture_summary_rows,
    )
    _write_csv(
        output_dir / "stage2_topk_family_representative_policy_fixture_summary_rows.csv",
        fixture_summary_rows,
    )
    _write_json(
        output_dir / "stage2_topk_family_representative_policy_recommendation.json",
        recommendation,
    )
    _write_json(
        output_dir / "stage2_topk_family_representative_policy_summary.json",
        {
            "run_label": RUN_LABEL,
            "candidate_policy_id": POLICY_ID,
            "family_view_id": PRIMARY_VIEW_ID,
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
        "recommendation": _safe_str(recommendation.get("recommendation")),
        "next_branch_label": _safe_str(recommendation.get("next_branch_label")),
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
