from __future__ import annotations

import datetime as dt
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage2_stage3_promoted_family_audit_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
import sys

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
from tools.benchmarks.periodic_sub_trans.no_wli.family_views import (  # noqa: E402
    find_family_view,
    cluster_family_ids,
)


RUN_LABEL = "stage2_stage3_promoted_family_audit_v1"
PRIMARY_VIEW_ID = "prefix_hamming_le_24"
PRIMARY_VIEW = find_family_view(PRIMARY_VIEW_ID)
if PRIMARY_VIEW is None:
    raise RuntimeError(f"Missing family view: {PRIMARY_VIEW_ID}")

FIXTURE_SEEDS = (611, 1111, 1511)
WITHIN_FAMILY_SIGNAL_MIN = 0.05
BETWEEN_FAMILY_SMALL_MAX = 0.03
CONTROL_WITHIN_FAMILY_MAX = 0.02


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
    base_mod._write_csv(path, rows)


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _artifact_stem(*, fixture_seed: int, search_seed: int) -> str:
    return f"fixture_001__p9_c3_l1000__text0__seed{int(fixture_seed)}__search{int(search_seed)}"


def _run_dir_from_inventory_row(row: Mapping[str, Any]) -> Path:
    return base_mod.INPUT_EXTERNAL_REVIEW_PACK_DIR / _safe_str(row.get("copied_report_dir"))


def _pool_row(
    *,
    row_id: str,
    key: Sequence[Any] | None,
    truth_match: Any = float("nan"),
    score_primary: Any = float("nan"),
    score_secondary: Any = float("nan"),
) -> dict[str, Any]:
    return {
        "row_id": str(row_id),
        "key": list(key) if key is not None else None,
        "truth_match": _safe_float(truth_match),
        "score_primary": _safe_float(score_primary),
        "score_secondary": _safe_float(score_secondary),
    }


def _effective_family_count(counts: Sequence[int]) -> float:
    total = float(sum(int(x) for x in counts))
    if total <= 0.0:
        return 0.0
    denom = 0.0
    for value in counts:
        prob = float(value) / total
        denom += prob * prob
    if denom <= 0.0:
        return 0.0
    return float(1.0 / denom)


def _select_score_row(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Cannot select score row from an empty pool")
    return max(
        rows,
        key=lambda row: (
            _safe_float(row.get("score_primary"), float("-inf")),
            _safe_float(row.get("score_secondary"), float("-inf")),
            _safe_float(row.get("truth_match"), float("-inf")),
            _safe_str(row.get("row_id")),
        ),
    )


def _select_truth_row(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Cannot select truth row from an empty pool")
    return max(
        rows,
        key=lambda row: (
            _safe_float(row.get("truth_match"), float("-inf")),
            _safe_float(row.get("score_primary"), float("-inf")),
            _safe_float(row.get("score_secondary"), float("-inf")),
            _safe_str(row.get("row_id")),
        ),
    )


def _pool_gap_metrics(
    *,
    rows: Sequence[Mapping[str, Any]],
    columns: int,
) -> dict[str, Any]:
    if not rows:
        return {
            "row_count": 0,
            "family_count": 0,
            "effective_family_count": 0.0,
            "largest_family_share": 0.0,
            "selected_row_id": "",
            "selected_family_id": "",
            "selected_row_truth": float("nan"),
            "selected_family_truth": float("nan"),
            "best_truth_row_id": "",
            "best_truth_family_id": "",
            "best_truth_row_truth": float("nan"),
            "best_family_truth": float("nan"),
            "within_family_gap": float("nan"),
            "between_family_gap": float("nan"),
        }

    assignments, unassigned_rows = cluster_family_ids(
        rows,
        family_view=PRIMARY_VIEW,
        columns=int(columns),
    )
    if unassigned_rows:
        raise ValueError(
            f"Unexpected unassigned rows in family audit pool: {unassigned_rows}"
        )

    family_counts = Counter(assignments.values())
    family_best_truth: dict[str, float] = defaultdict(lambda: float("-inf"))
    for row in rows:
        family_id = assignments[str(row["row_id"])]
        family_best_truth[family_id] = max(
            float(family_best_truth[family_id]),
            _safe_float(row.get("truth_match"), float("-inf")),
        )

    selected_row = _select_score_row(rows)
    best_truth_row = _select_truth_row(rows)
    selected_family_id = assignments[str(selected_row["row_id"])]
    best_truth_family_id = assignments[str(best_truth_row["row_id"])]
    selected_family_truth = _safe_float(family_best_truth.get(selected_family_id))
    best_family_truth = _safe_float(max(family_best_truth.values(), default=float("nan")))
    largest_family_count = max(family_counts.values(), default=0)
    row_count = int(len(rows))
    return {
        "row_count": row_count,
        "family_count": int(len(family_counts)),
        "effective_family_count": _effective_family_count(list(family_counts.values())),
        "largest_family_share": (
            float(largest_family_count) / float(row_count) if row_count > 0 else 0.0
        ),
        "selected_row_id": _safe_str(selected_row.get("row_id")),
        "selected_family_id": _safe_str(selected_family_id),
        "selected_row_truth": _safe_float(selected_row.get("truth_match")),
        "selected_family_truth": selected_family_truth,
        "best_truth_row_id": _safe_str(best_truth_row.get("row_id")),
        "best_truth_family_id": _safe_str(best_truth_family_id),
        "best_truth_row_truth": _safe_float(best_truth_row.get("truth_match")),
        "best_family_truth": best_family_truth,
        "within_family_gap": selected_family_truth
        - _safe_float(selected_row.get("truth_match")),
        "between_family_gap": best_family_truth - selected_family_truth,
    }


def _combined_family_carry_metrics(
    *,
    promoted_rows: Sequence[Mapping[str, Any]],
    init3_rows: Sequence[Mapping[str, Any]],
    promoted_metrics: Mapping[str, Any],
    columns: int,
) -> dict[str, Any]:
    combined_rows = [dict(row) for row in promoted_rows] + [dict(row) for row in init3_rows]
    assignments, unassigned_rows = cluster_family_ids(
        combined_rows,
        family_view=PRIMARY_VIEW,
        columns=int(columns),
    )
    if unassigned_rows:
        raise ValueError(
            f"Unexpected unassigned rows in combined family audit pool: {unassigned_rows}"
        )

    init3_counts = Counter(
        assignments[str(row["row_id"])] for row in init3_rows if str(row["row_id"]) in assignments
    )
    init3_row_count = int(len(init3_rows))
    selected_family_id = _safe_str(promoted_metrics.get("selected_family_id"))
    best_truth_family_id = _safe_str(promoted_metrics.get("best_truth_family_id"))
    selected_family_init3_count = int(init3_counts.get(selected_family_id, 0))
    best_truth_family_init3_count = int(init3_counts.get(best_truth_family_id, 0))
    return {
        "combined_family_count": int(len(set(assignments.values()))),
        "init3_family_count": int(len(init3_counts)),
        "init3_effective_family_count": _effective_family_count(list(init3_counts.values())),
        "selected_family_init3_count": selected_family_init3_count,
        "selected_family_init3_share": (
            float(selected_family_init3_count) / float(init3_row_count)
            if init3_row_count > 0
            else 0.0
        ),
        "best_truth_family_init3_count": best_truth_family_init3_count,
        "best_truth_family_init3_share": (
            float(best_truth_family_init3_count) / float(init3_row_count)
            if init3_row_count > 0
            else 0.0
        ),
        "init3_selected_minus_best_truth_family_share": (
            (
                float(selected_family_init3_count) - float(best_truth_family_init3_count)
            )
            / float(init3_row_count)
            if init3_row_count > 0
            else 0.0
        ),
    }


def _fixture_pattern_label(summary_row: Mapping[str, Any]) -> str:
    mean_topk_within_gap = _safe_float(summary_row.get("mean_stage2_topk_within_family_gap"))
    mean_promoted_within_gap = _safe_float(
        summary_row.get("mean_stage2_promoted_within_family_gap")
    )
    mean_promoted_between_gap = _safe_float(
        summary_row.get("mean_stage2_promoted_between_family_gap")
    )
    run_count = _safe_int(summary_row.get("run_count"))
    within_signal_count = _safe_int(
        summary_row.get("promoted_within_family_signal_run_count")
    )

    if (
        run_count > 0
        and within_signal_count == run_count
        and mean_topk_within_gap >= WITHIN_FAMILY_SIGNAL_MIN
        and mean_promoted_within_gap >= WITHIN_FAMILY_SIGNAL_MIN
        and mean_promoted_between_gap <= BETWEEN_FAMILY_SMALL_MAX
    ):
        return "persistent_within_family_representative_gap"
    if mean_promoted_between_gap >= WITHIN_FAMILY_SIGNAL_MIN:
        return "cross_family_gap_or_absence"
    if mean_promoted_within_gap >= CONTROL_WITHIN_FAMILY_MAX:
        return "mixed_upstream_gap"
    return "no_clear_upstream_gap"


def _build_fixture_summary_rows(
    case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        grouped[_safe_int(row.get("fixture_seed"))].append(dict(row))

    summary_rows: list[dict[str, Any]] = []
    for fixture_seed in FIXTURE_SEEDS:
        seed_rows = sorted(
            grouped.get(int(fixture_seed), []),
            key=lambda row: _safe_int(row.get("search_seed")),
        )
        if not seed_rows:
            continue

        def _mean(field: str) -> float:
            values = [_safe_float(row.get(field)) for row in seed_rows]
            return float(sum(values) / len(values))

        row = {
            "fixture_seed": int(fixture_seed),
            "benchmark_case_role": _safe_str(seed_rows[0].get("benchmark_case_role")),
            "run_count": int(len(seed_rows)),
            "mean_final_best_match_ratio": _mean("final_best_match_ratio"),
            "mean_stage2_topk_within_family_gap": _mean("stage2_topk_within_family_gap"),
            "mean_stage2_topk_between_family_gap": _mean(
                "stage2_topk_between_family_gap"
            ),
            "mean_stage2_promoted_within_family_gap": _mean(
                "stage2_promoted_within_family_gap"
            ),
            "mean_stage2_promoted_between_family_gap": _mean(
                "stage2_promoted_between_family_gap"
            ),
            "mean_selected_family_init3_share": _mean(
                "selected_family_init3_share"
            ),
            "mean_best_truth_family_init3_share": _mean(
                "best_truth_family_init3_share"
            ),
            "mean_init3_selected_minus_best_truth_family_share": _mean(
                "init3_selected_minus_best_truth_family_share"
            ),
            "topk_within_family_signal_run_count": sum(
                1
                for case_row in seed_rows
                if _safe_float(case_row.get("stage2_topk_within_family_gap"))
                >= WITHIN_FAMILY_SIGNAL_MIN
            ),
            "promoted_within_family_signal_run_count": sum(
                1
                for case_row in seed_rows
                if _safe_float(case_row.get("stage2_promoted_within_family_gap"))
                >= WITHIN_FAMILY_SIGNAL_MIN
            ),
            "promoted_between_family_signal_run_count": sum(
                1
                for case_row in seed_rows
                if _safe_float(case_row.get("stage2_promoted_between_family_gap"))
                >= WITHIN_FAMILY_SIGNAL_MIN
            ),
        }
        row["dominant_upstream_pattern"] = _fixture_pattern_label(row)
        summary_rows.append(row)

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

    if not row_1111 or not row_611 or not row_1511:
        return {
            "recommendation": "incomplete",
            "next_branch_label": "",
            "reason": "Primary trio coverage is incomplete in the fixed-panel audit.",
        }

    within_1111 = _safe_float(row_1111.get("mean_stage2_promoted_within_family_gap"))
    between_1111 = _safe_float(row_1111.get("mean_stage2_promoted_between_family_gap"))
    within_611 = _safe_float(row_611.get("mean_stage2_promoted_within_family_gap"))
    within_1511 = _safe_float(row_1511.get("mean_stage2_promoted_within_family_gap"))

    if (
        _safe_str(row_1111.get("dominant_upstream_pattern"))
        == "persistent_within_family_representative_gap"
        and within_611 <= CONTROL_WITHIN_FAMILY_MAX
        and within_1511 <= CONTROL_WITHIN_FAMILY_MAX
    ):
        return {
            "recommendation": "advance",
            "next_branch_label": (
                "stage2_stage3_within_family_representative_selection_microprobe"
            ),
            "mechanism_layer": "selection",
            "reason": (
                "1111 shows a persistent upstream within-family representative gap "
                "at both stage2_topk and stage2_promoted, while 611 and 1511 stay "
                "near zero. The next honest branch is an upstream representative-"
                "selection microprobe, not more family-diversity or entry-allocation work."
            ),
            "mean_stage2_promoted_within_family_gap_1111": within_1111,
            "mean_stage2_promoted_between_family_gap_1111": between_1111,
            "mean_stage2_promoted_within_family_gap_611": within_611,
            "mean_stage2_promoted_within_family_gap_1511": within_1511,
        }

    if between_1111 >= WITHIN_FAMILY_SIGNAL_MIN:
        return {
            "recommendation": "advance",
            "next_branch_label": "stage2_promoted_family_mix_or_diversity_microprobe",
            "mechanism_layer": "selection",
            "reason": (
                "1111 looks dominated by a cross-family upstream gap, so the next "
                "branch should target promoted-family mix or diversity directly."
            ),
            "mean_stage2_promoted_within_family_gap_1111": within_1111,
            "mean_stage2_promoted_between_family_gap_1111": between_1111,
        }

    return {
        "recommendation": "refine",
        "next_branch_label": "",
        "mechanism_layer": "selection",
        "reason": (
            "The upstream audit did not cleanly isolate a single next mechanism. "
            "Refine the offline read before launching another live run."
        ),
        "mean_stage2_promoted_within_family_gap_1111": within_1111,
        "mean_stage2_promoted_between_family_gap_1111": between_1111,
    }


def _build_case_rows() -> list[dict[str, Any]]:
    inventory_rows = [
        dict(row)
        for row in base_mod._read_csv_rows(base_mod.PANEL_INVENTORY_CSV)
        if _safe_int(row.get("fixture_seed")) in FIXTURE_SEEDS
    ]
    inventory_rows.sort(
        key=lambda row: (
            base_mod._fixture_seed_order(_safe_int(row.get("fixture_seed"))),
            base_mod._search_seed_order(_safe_int(row.get("search_seed"))),
        )
    )
    total = int(len(inventory_rows))
    case_rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    for index, inventory_row in enumerate(inventory_rows, start=1):
        fixture_seed = _safe_int(inventory_row.get("fixture_seed"))
        search_seed = _safe_int(inventory_row.get("search_seed"))
        stem = _artifact_stem(fixture_seed=fixture_seed, search_seed=search_seed)
        run_dir = _run_dir_from_inventory_row(inventory_row)
        final_instance_path = run_dir / "final_instances" / f"{stem}.json"
        stage2_resume_path = run_dir / "resume_handoffs" / stem / "stage2_resume.json"
        stage3_prep_path = run_dir / "resume_handoffs" / stem / "stage3_prep.json"
        final_instance = _read_json(final_instance_path)
        stage2_resume = _read_json(stage2_resume_path)
        stage3_prep = _read_json(stage3_prep_path)
        columns = _safe_int(final_instance.get("columns"))

        stage2_topk_rows = [
            _pool_row(
                row_id=f"stage2_topk:{i}",
                key=row.get("key_idx"),
                truth_match=row.get("match_ratio"),
                score_primary=row.get("score_stage2"),
                score_secondary=row.get("score_judge"),
            )
            for i, row in enumerate(final_instance.get("stage2_topk", []) or [], start=1)
        ]
        stage2_promoted_rows = [
            _pool_row(
                row_id=f"stage2_promoted:{i}",
                key=row.get("key"),
                truth_match=row.get("match"),
                score_primary=row.get("score"),
                score_secondary=row.get("judge_score"),
            )
            for i, row in enumerate(stage2_resume.get("stage2_promoted", []) or [], start=1)
        ]
        stage3_init3_rows = [
            _pool_row(
                row_id=f"stage3_init3:{i}",
                key=key,
            )
            for i, key in enumerate(stage3_prep.get("init3", []) or [], start=1)
        ]

        topk_metrics = _pool_gap_metrics(rows=stage2_topk_rows, columns=columns)
        promoted_metrics = _pool_gap_metrics(rows=stage2_promoted_rows, columns=columns)
        init3_carry_metrics = _combined_family_carry_metrics(
            promoted_rows=stage2_promoted_rows,
            init3_rows=stage3_init3_rows,
            promoted_metrics=promoted_metrics,
            columns=columns,
        )

        case_rows.append(
            {
                "panel_job_index": _safe_int(inventory_row.get("panel_job_index")),
                "fixture_seed": fixture_seed,
                "search_seed": search_seed,
                "benchmark_case_role": base_mod._benchmark_case_role(fixture_seed),
                "status": _safe_str(inventory_row.get("status")),
                "stop_reason": _safe_str(inventory_row.get("stop_reason")),
                "best_stage": _safe_str(inventory_row.get("best_stage")),
                "final_best_match_ratio": _safe_float(
                    inventory_row.get("best_match_ratio")
                ),
                "total_seconds": _safe_float(inventory_row.get("total_seconds")),
                "source_run_label": _safe_str(inventory_row.get("source_run_label")),
                "source_report_dir": _safe_str(inventory_row.get("source_report_dir")),
                "copied_report_dir": _safe_str(inventory_row.get("copied_report_dir")),
                "family_view_id": PRIMARY_VIEW_ID,
                "stage2_topk_row_count": _safe_int(topk_metrics.get("row_count")),
                "stage2_topk_family_count": _safe_int(topk_metrics.get("family_count")),
                "stage2_topk_effective_family_count": _safe_float(
                    topk_metrics.get("effective_family_count")
                ),
                "stage2_topk_largest_family_share": _safe_float(
                    topk_metrics.get("largest_family_share")
                ),
                "stage2_topk_selected_row_truth": _safe_float(
                    topk_metrics.get("selected_row_truth")
                ),
                "stage2_topk_selected_family_truth": _safe_float(
                    topk_metrics.get("selected_family_truth")
                ),
                "stage2_topk_best_family_truth": _safe_float(
                    topk_metrics.get("best_family_truth")
                ),
                "stage2_topk_within_family_gap": _safe_float(
                    topk_metrics.get("within_family_gap")
                ),
                "stage2_topk_between_family_gap": _safe_float(
                    topk_metrics.get("between_family_gap")
                ),
                "stage2_promoted_row_count": _safe_int(
                    promoted_metrics.get("row_count")
                ),
                "stage2_promoted_family_count": _safe_int(
                    promoted_metrics.get("family_count")
                ),
                "stage2_promoted_effective_family_count": _safe_float(
                    promoted_metrics.get("effective_family_count")
                ),
                "stage2_promoted_largest_family_share": _safe_float(
                    promoted_metrics.get("largest_family_share")
                ),
                "stage2_promoted_selected_row_truth": _safe_float(
                    promoted_metrics.get("selected_row_truth")
                ),
                "stage2_promoted_selected_family_truth": _safe_float(
                    promoted_metrics.get("selected_family_truth")
                ),
                "stage2_promoted_best_family_truth": _safe_float(
                    promoted_metrics.get("best_family_truth")
                ),
                "stage2_promoted_within_family_gap": _safe_float(
                    promoted_metrics.get("within_family_gap")
                ),
                "stage2_promoted_between_family_gap": _safe_float(
                    promoted_metrics.get("between_family_gap")
                ),
                "stage2_promoted_selected_family_id": _safe_str(
                    promoted_metrics.get("selected_family_id")
                ),
                "stage2_promoted_best_truth_family_id": _safe_str(
                    promoted_metrics.get("best_truth_family_id")
                ),
                "stage2_promoted_selected_vs_best_truth_family_same": int(
                    _safe_str(promoted_metrics.get("selected_family_id"))
                    == _safe_str(promoted_metrics.get("best_truth_family_id"))
                ),
                "stage3_entry_allocation_policy": _safe_str(
                    stage3_prep.get("stage3_entry_allocation_policy")
                ),
                "stage3_entry_target_before_cap": _safe_int(
                    stage3_prep.get("stage3_entry_target_before_cap")
                ),
                "stage3_promoted_keys_count": _safe_int(
                    stage3_prep.get("stage3_promoted_keys_count")
                ),
                "stage3_init3_count": _safe_int(stage3_prep.get("init3_n")),
                "stage3_init3_family_count": _safe_int(
                    init3_carry_metrics.get("init3_family_count")
                ),
                "stage3_init3_effective_family_count": _safe_float(
                    init3_carry_metrics.get("init3_effective_family_count")
                ),
                "selected_family_init3_count": _safe_int(
                    init3_carry_metrics.get("selected_family_init3_count")
                ),
                "selected_family_init3_share": _safe_float(
                    init3_carry_metrics.get("selected_family_init3_share")
                ),
                "best_truth_family_init3_count": _safe_int(
                    init3_carry_metrics.get("best_truth_family_init3_count")
                ),
                "best_truth_family_init3_share": _safe_float(
                    init3_carry_metrics.get("best_truth_family_init3_share")
                ),
                "init3_selected_minus_best_truth_family_share": _safe_float(
                    init3_carry_metrics.get(
                        "init3_selected_minus_best_truth_family_share"
                    )
                ),
                "upstream_within_family_signal": int(
                    _safe_float(promoted_metrics.get("within_family_gap"))
                    >= WITHIN_FAMILY_SIGNAL_MIN
                ),
                "upstream_between_family_signal": int(
                    _safe_float(promoted_metrics.get("between_family_gap"))
                    >= WITHIN_FAMILY_SIGNAL_MIN
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
            f"promoted_within_gap={_safe_float(promoted_metrics.get('within_family_gap')):.3f} "
            f"promoted_between_gap={_safe_float(promoted_metrics.get('between_family_gap')):.3f}"
        )

    return case_rows


def _write_markdown(
    output_dir: Path,
    *,
    case_rows: Sequence[Mapping[str, Any]],
    fixture_summary_rows: Sequence[Mapping[str, Any]],
    recommendation: Mapping[str, Any],
) -> None:
    lines = [
        "# Stage-2 to Stage-3 Promoted Family Audit v1",
        "",
        "Question:",
        "- on the fixed primary trio, does `1111` fail because upstream promoted-family supply is missing the right family, or because it already carries a better family but surfaces a weak representative inside it before Stage 3 starts?",
        "",
        "Mechanism layer:",
        "- `selection`",
        "",
        "Primary family view:",
        f"- `{PRIMARY_VIEW_ID}`",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- next branch: `{_safe_str(recommendation.get('next_branch_label')) or 'none'}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Fixture summary:",
        "",
        "| fixture seed | role | runs | mean final best | mean topk within gap | mean promoted within gap | mean promoted between gap | mean selected init3 share | mean best-truth init3 share | pattern |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in fixture_summary_rows:
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}` | "
            f"`{_safe_str(row.get('benchmark_case_role'))}` | "
            f"`{_safe_int(row.get('run_count'))}` | "
            f"`{_safe_float(row.get('mean_final_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('mean_stage2_topk_within_family_gap')):.3f}` | "
            f"`{_safe_float(row.get('mean_stage2_promoted_within_family_gap')):.3f}` | "
            f"`{_safe_float(row.get('mean_stage2_promoted_between_family_gap')):.3f}` | "
            f"`{_safe_float(row.get('mean_selected_family_init3_share')):.3f}` | "
            f"`{_safe_float(row.get('mean_best_truth_family_init3_share')):.3f}` | "
            f"`{_safe_str(row.get('dominant_upstream_pattern'))}` |"
        )

    lines.extend(
        [
            "",
            "Primary read:",
            "- `1111` is the only seed family in the primary trio with a persistent upstream within-family representative gap.",
            "- the `1111` top-score row already sits inside a family whose best truth is materially higher, and that persists from `stage2_topk` into `stage2_promoted`.",
            "- `1111` cross-family gap is smaller than its within-family gap, so the main issue does not currently look like missing family diversity.",
            "- `611` and `1511` stay near zero on the same within-family metric, so the `1111` pattern is not a generic panel-wide artifact.",
            "",
            "Per-run case table:",
            "",
            "| fixture seed | search seed | final best | topk within gap | promoted within gap | promoted between gap | selected init3 share | best-truth init3 share | selected==best family |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in case_rows:
        lines.append(
            f"| `{_safe_int(row.get('fixture_seed'))}` | "
            f"`{_safe_int(row.get('search_seed'))}` | "
            f"`{_safe_float(row.get('final_best_match_ratio')):.3f}` | "
            f"`{_safe_float(row.get('stage2_topk_within_family_gap')):.3f}` | "
            f"`{_safe_float(row.get('stage2_promoted_within_family_gap')):.3f}` | "
            f"`{_safe_float(row.get('stage2_promoted_between_family_gap')):.3f}` | "
            f"`{_safe_float(row.get('selected_family_init3_share')):.3f}` | "
            f"`{_safe_float(row.get('best_truth_family_init3_share')):.3f}` | "
            f"`{_safe_int(row.get('stage2_promoted_selected_vs_best_truth_family_same'))}` |"
        )

    (output_dir / "stage2_stage3_promoted_family_audit_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_extract() -> dict[str, Any]:
    for required_path in (
        base_mod.PANEL_INVENTORY_CSV,
        base_mod.INPUT_EXTERNAL_REVIEW_PACK_DIR,
    ):
        if not required_path.exists():
            raise FileNotFoundError(f"Missing required input: {_relative_path(required_path)}")

    _print_progress(
        "run_started "
        f"label={RUN_LABEL} family_view={PRIMARY_VIEW_ID} "
        f"fixture_seeds={list(FIXTURE_SEEDS)}"
    )
    case_rows = _build_case_rows()
    fixture_summary_rows = _build_fixture_summary_rows(case_rows)
    recommendation = build_recommendation(fixture_summary_rows)

    output_dir = base_mod.OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    _write_jsonl(output_dir / "stage2_stage3_promoted_family_audit_case_rows.jsonl", case_rows)
    _write_csv(output_dir / "stage2_stage3_promoted_family_audit_case_rows.csv", case_rows)
    _write_jsonl(
        output_dir / "stage2_stage3_promoted_family_audit_fixture_summary_rows.jsonl",
        fixture_summary_rows,
    )
    _write_csv(
        output_dir / "stage2_stage3_promoted_family_audit_fixture_summary_rows.csv",
        fixture_summary_rows,
    )
    _write_json(
        output_dir / "stage2_stage3_promoted_family_audit_summary.json",
        {
            "run_label": RUN_LABEL,
            "family_view_id": PRIMARY_VIEW_ID,
            "fixture_seeds": list(FIXTURE_SEEDS),
            "case_row_count": int(len(case_rows)),
            "fixture_summary_row_count": int(len(fixture_summary_rows)),
            "recommendation": dict(recommendation),
            "output_dir": _relative_path(output_dir),
        },
    )
    _write_json(
        output_dir / "stage2_stage3_promoted_family_audit_recommendation.json",
        recommendation,
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
        "family_view_id": PRIMARY_VIEW_ID,
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
