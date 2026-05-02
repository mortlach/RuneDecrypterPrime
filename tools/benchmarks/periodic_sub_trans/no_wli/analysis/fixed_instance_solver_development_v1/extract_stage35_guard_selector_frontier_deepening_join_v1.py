from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage35_guard_selector_frontier_deepening_join_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


RUN_LABEL = "stage35_guard_selector_frontier_deepening_join_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
SHALLOW_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/"
    "stage35_guard_selector_frontier_runtime_rows.csv"
)
DEEP_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/"
    "stage35_guard_selector_frontier_deepening_rows.csv"
)


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(result):
        return float(default)
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _row_key(row: Mapping[str, Any]) -> tuple[int, int, int, str]:
    return (
        _safe_int(row.get("fixture_seed")),
        _safe_int(row.get("search_seed")),
        _safe_int(row.get("candidate_rank")),
        str(row.get("candidate_hash", "") or ""),
    )


def _mean(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        return 0.0
    return float(sum(vals) / len(vals))


def _bucket_delta(delta: float) -> str:
    if delta < 0.0:
        return "negative"
    if delta < 0.005:
        return "flat_to_plus_0p005"
    if delta < 0.010:
        return "plus_0p005_to_0p010"
    return "plus_0p010_or_more"


def _bucket_start(start: float) -> str:
    if start < 0.35:
        return "start_lt_0p35"
    if start < 0.45:
        return "start_0p35_to_0p45"
    return "start_ge_0p45"


def build_join_rows(
    *,
    shallow_rows: list[dict[str, str]],
    deep_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    shallow_by_key: dict[tuple[int, int, int, str], list[dict[str, str]]] = defaultdict(list)
    deep_by_key: dict[tuple[int, int, int, str], list[dict[str, str]]] = defaultdict(list)
    for row in shallow_rows:
        shallow_by_key[_row_key(row)].append(row)
    for row in deep_rows:
        deep_by_key[_row_key(row)].append(row)

    joined: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    for key in sorted(deep_by_key):
        fixture_seed, search_seed, candidate_rank, candidate_hash = key
        deep_group = deep_by_key[key]
        shallow_group = shallow_by_key.get(key, [])
        if len(deep_group) > 1 or len(shallow_group) > 1:
            duplicates.append(
                {
                    "fixture_seed": fixture_seed,
                    "search_seed": search_seed,
                    "candidate_rank": candidate_rank,
                    "candidate_hash": candidate_hash,
                    "shallow_duplicate_count": len(shallow_group),
                    "deep_duplicate_count": len(deep_group),
                    "shallow_cell_output_dirs": "|".join(
                        str(row.get("cell_output_dir", "") or "")
                        for row in shallow_group
                    ),
                    "deep_cell_output_dirs": "|".join(
                        str(row.get("cell_output_dir", "") or "")
                        for row in deep_group
                    ),
                }
            )

        # Keep one representative per key, while preserving duplicate counts.
        deep = deep_group[0]
        shallow = shallow_group[0] if shallow_group else {}
        retained = _safe_float(deep.get("retained_best_match_ratio"))
        selected_start = _safe_float(deep.get("selected_start_match_ratio"))
        shallow_resume = _safe_float(deep.get("shallow_resume_best_match_ratio"))
        deep_resume = _safe_float(deep.get("resume_best_match_ratio"))
        shallow_minus_selected = _safe_float(deep.get("shallow_resume_minus_selected"))
        deep_minus_selected = _safe_float(deep.get("resume_minus_selected"))
        deep_minus_shallow = _safe_float(deep.get("resume_minus_shallow"))
        shallow_minus_retained = shallow_resume - retained
        deep_minus_retained = deep_resume - retained
        joined.append(
            {
                "fixture_seed": fixture_seed,
                "search_seed": search_seed,
                "candidate_rank": candidate_rank,
                "candidate_hash": candidate_hash,
                "artifact_relpath": str(deep.get("artifact_relpath", "") or ""),
                "shallow_duplicate_count": len(shallow_group),
                "deep_duplicate_count": len(deep_group),
                "selected_source": str(shallow.get("selected_source", "") or ""),
                "selected_lane": str(shallow.get("selected_lane", "") or ""),
                "retained_best_match_ratio": retained,
                "selected_start_match_ratio": selected_start,
                "selected_headroom_vs_retained": selected_start - retained,
                "shallow_resume_best_match_ratio": shallow_resume,
                "deep_resume_best_match_ratio": deep_resume,
                "shallow_minus_selected": shallow_minus_selected,
                "deep_minus_selected": deep_minus_selected,
                "shallow_minus_retained": shallow_minus_retained,
                "deep_minus_retained": deep_minus_retained,
                "deep_minus_shallow": deep_minus_shallow,
                "deep_better_than_shallow": int(deep_minus_shallow > 0.0),
                "deep_worse_than_shallow": int(deep_minus_shallow < 0.0),
                "deep_delta_bucket": _bucket_delta(deep_minus_shallow),
                "selected_start_bucket": _bucket_start(selected_start),
                "shallow_stage35_accept_reason": str(
                    shallow.get("stage35_accept_reason", "") or ""
                ),
                "deep_stage35_accept_reason": str(
                    deep.get("stage35_accept_reason", "") or ""
                ),
                "shallow_selected_archive_rank": _safe_int(
                    shallow.get("stage35_selected_archive_rank")
                ),
                "deep_selected_archive_rank": _safe_int(
                    deep.get("stage35_selected_archive_rank")
                ),
                "shallow_via_guard_selector": _safe_int(
                    shallow.get("stage35_selected_via_guard_passing_selector")
                ),
                "deep_via_guard_selector": _safe_int(
                    deep.get("stage35_selected_via_guard_passing_selector")
                ),
                "shallow_elapsed_seconds": _safe_float(shallow.get("elapsed_seconds")),
                "deep_elapsed_seconds": _safe_float(deep.get("elapsed_seconds")),
            }
        )
    return joined, duplicates


def summarize_group(rows: list[Mapping[str, Any]], group_name: str, group_value: str) -> dict[str, Any]:
    deltas = [_safe_float(row.get("deep_minus_shallow")) for row in rows]
    return {
        "group_name": group_name,
        "group_value": group_value,
        "rows": len(rows),
        "better_than_shallow": sum(
            1 for row in rows if _safe_int(row.get("deep_better_than_shallow")) == 1
        ),
        "worse_than_shallow": sum(
            1 for row in rows if _safe_int(row.get("deep_worse_than_shallow")) == 1
        ),
        "mean_deep_minus_shallow": _mean(deltas),
        "min_deep_minus_shallow": min(deltas) if deltas else 0.0,
        "max_deep_minus_shallow": max(deltas) if deltas else 0.0,
        "mean_deep_minus_retained": _mean(
            _safe_float(row.get("deep_minus_retained")) for row in rows
        ),
        "mean_deep_elapsed_seconds": _mean(
            _safe_float(row.get("deep_elapsed_seconds")) for row in rows
        ),
    }


def build_summary_rows(joined: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary_rows: list[dict[str, Any]] = []
    for group_name in [
        "candidate_rank",
        "fixture_seed",
        "search_seed",
        "selected_start_bucket",
        "selected_lane",
        "shallow_stage35_accept_reason",
    ]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in joined:
            groups[str(row.get(group_name, "") or "")].append(row)
        for group_value in sorted(groups):
            summary_rows.append(
                summarize_group(groups[group_value], group_name, group_value)
            )
    return summary_rows


def _gate_stat(
    *,
    gate_name: str,
    gate_kind: str,
    rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    deltas = [_safe_float(row.get("deep_minus_shallow")) for row in rows]
    return {
        "gate_name": gate_name,
        "gate_kind": gate_kind,
        "rows": len(rows),
        "better_than_shallow": sum(1 for delta in deltas if delta > 0.0),
        "worse_than_shallow": sum(1 for delta in deltas if delta < 0.0),
        "mean_deep_minus_shallow": _mean(deltas),
        "min_deep_minus_shallow": min(deltas) if deltas else 0.0,
        "max_deep_minus_shallow": max(deltas) if deltas else 0.0,
        "mean_deep_minus_retained": _mean(
            _safe_float(row.get("deep_minus_retained")) for row in rows
        ),
        "candidate_hashes": "|".join(
            str(row.get("candidate_hash", "") or "") for row in rows
        ),
    }


def build_candidate_gate_rows(joined: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank6 = [row for row in joined if _safe_int(row.get("candidate_rank")) == 6]
    gate_rows: list[dict[str, Any]] = [
        _gate_stat(gate_name="rank6_all", gate_kind="mechanism_slice", rows=rank6)
    ]
    for threshold in [0.35, 0.40, 0.425, 0.437, 0.45, 0.475, 0.50]:
        kept = [
            row
            for row in rank6
            if _safe_float(row.get("selected_start_match_ratio")) >= threshold
        ]
        if kept:
            gate_rows.append(
                _gate_stat(
                    gate_name=f"rank6_selected_start_ge_{threshold:.3f}".replace(
                        ".", "p"
                    ),
                    gate_kind="posthoc_candidate_gate",
                    rows=kept,
                )
            )
    for threshold in [0.45, 0.50, 0.60, 0.70, 0.80]:
        kept = [
            row
            for row in rank6
            if _safe_float(row.get("shallow_resume_best_match_ratio")) >= threshold
        ]
        if kept:
            gate_rows.append(
                _gate_stat(
                    gate_name=f"rank6_shallow_resume_ge_{threshold:.2f}".replace(
                        ".", "p"
                    ),
                    gate_kind="posthoc_candidate_gate",
                    rows=kept,
                )
            )
    for threshold in [0.15, 0.20, 0.30, 0.40]:
        kept = [
            row
            for row in rank6
            if _safe_float(row.get("shallow_minus_selected")) >= threshold
        ]
        if kept:
            gate_rows.append(
                _gate_stat(
                    gate_name=f"rank6_shallow_delta_ge_{threshold:.2f}".replace(
                        ".", "p"
                    ),
                    gate_kind="posthoc_candidate_gate",
                    rows=kept,
                )
            )
    for search_seed in sorted({str(row.get("search_seed")) for row in rank6}):
        kept = [row for row in rank6 if str(row.get("search_seed")) == search_seed]
        gate_rows.append(
            _gate_stat(
                gate_name=f"rank6_search_seed_{search_seed}",
                gate_kind="diagnostic_seed_slice",
                rows=kept,
            )
        )
    gate_rows.sort(
        key=lambda row: (
            _safe_int(row.get("worse_than_shallow")),
            -_safe_int(row.get("better_than_shallow")),
            -_safe_int(row.get("rows")),
            str(row.get("gate_name", "")),
        )
    )
    return gate_rows


def build_recommendation(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "recommendation": "do_offline_rank6_safety_design_before_more_runtime",
        "claim": "deepening_is_real_but_modest_and_not_a_broad_policy_promotion",
        "rationale": [
            "The deduplicated deepening set improved over shallow on most rows.",
            "The effect size is modest and still includes regressions versus shallow.",
            "Rank 6 carries most of the positive signal but is not uniformly safe.",
        ],
        "next_step": (
            "Design a rank/slice-aware local-rescue policy from joined row "
            "features, then use a small canary only if the offline rule has an "
            "explicit no-regression gate."
        ),
        "summary": dict(summary),
    }


def build_readout(
    *,
    summary: Mapping[str, Any],
    rank_rows: list[Mapping[str, Any]],
    gate_rows: list[Mapping[str, Any]],
    worst_rows: list[Mapping[str, Any]],
    best_rows: list[Mapping[str, Any]],
) -> str:
    lines = [
        "# Stage35 Guard-Selector Frontier Deepening Join v1",
        "",
        "Question:",
        "",
        "- after deduplicating shallow/deepening rows, which slices look safe",
        "  enough to justify a narrower local-rescue policy design?",
        "",
        "Coverage:",
        "",
        f"- shallow rows: `{summary['shallow_rows']}`",
        f"- deep rows: `{summary['deep_rows']}`",
        f"- deduplicated joined rows: `{summary['joined_unique_rows']}`",
        f"- duplicate keys: `{summary['duplicate_keys']}`",
        "",
        "Main Result:",
        "",
        f"- better than shallow: `{summary['better_than_shallow']}`",
        f"- worse than shallow: `{summary['worse_than_shallow']}`",
        f"- mean deep minus shallow: `{summary['mean_deep_minus_shallow']:.6f}`",
        f"- best deep minus shallow: `{summary['best_deep_minus_shallow']:.6f}`",
        f"- worst deep minus shallow: `{summary['worst_deep_minus_shallow']:.6f}`",
        f"- mean deep minus retained: `{summary['mean_deep_minus_retained']:.6f}`",
        "",
        "Rank Summary:",
        "",
    ]
    for row in rank_rows:
        lines.append(
            "- rank `{}`: rows `{}`, better `{}`, worse `{}`, mean deep-shallow "
            "`{:.6f}`".format(
                row["group_value"],
                row["rows"],
                row["better_than_shallow"],
                row["worse_than_shallow"],
                float(row["mean_deep_minus_shallow"]),
            )
        )
    lines.extend(["", "Candidate Gate Sketch:", ""])
    for row in gate_rows[:8]:
        lines.append(
            "- `{}` ({}) rows `{}`, better `{}`, worse `{}`, mean `{:+.6f}`".format(
                row["gate_name"],
                row["gate_kind"],
                row["rows"],
                row["better_than_shallow"],
                row["worse_than_shallow"],
                float(row["mean_deep_minus_shallow"]),
            )
        )
    lines.extend(["", "Largest Positive Rows:", ""])
    for row in best_rows:
        lines.append(
            "- `{}/{} rank {}` `{}`: deep-shallow `{:+.6f}`, deep `{:.3f}`".format(
                row["fixture_seed"],
                row["search_seed"],
                row["candidate_rank"],
                row["candidate_hash"],
                float(row["deep_minus_shallow"]),
                float(row["deep_resume_best_match_ratio"]),
            )
        )
    lines.extend(["", "Regression Rows:", ""])
    for row in worst_rows:
        lines.append(
            "- `{}/{} rank {}` `{}`: deep-shallow `{:+.6f}`, shallow `{:.3f}`, deep `{:.3f}`".format(
                row["fixture_seed"],
                row["search_seed"],
                row["candidate_rank"],
                row["candidate_hash"],
                float(row["deep_minus_shallow"]),
                float(row["shallow_resume_best_match_ratio"]),
                float(row["deep_resume_best_match_ratio"]),
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- deepening remains a real but modest positive signal after deduplication",
            "- rank `6` carries most of the signal, but it is not uniformly safe",
            "- do not run another broad runtime batch until an explicit rank/slice",
            "  safety rule exists",
            "",
            "Recommended Next:",
            "",
            "- design an offline rank-6 safety rule with an explicit no-regression",
            "  gate before any further runtime",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_extract() -> dict[str, Any]:
    shallow_path = REPO_ROOT / SHALLOW_ROWS_REL
    deep_path = REPO_ROOT / DEEP_ROWS_REL
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    shallow_rows = _read_csv(shallow_path)
    deep_rows = _read_csv(deep_path)
    joined, duplicates = build_join_rows(
        shallow_rows=shallow_rows,
        deep_rows=deep_rows,
    )
    joined.sort(
        key=lambda row: (
            -_safe_float(row.get("deep_minus_shallow")),
            _safe_int(row.get("fixture_seed")),
            _safe_int(row.get("search_seed")),
            _safe_int(row.get("candidate_rank")),
            str(row.get("candidate_hash", "")),
        )
    )
    summary_rows = build_summary_rows(joined)
    gate_rows = build_candidate_gate_rows(joined)
    rank_rows = [
        row for row in summary_rows if str(row.get("group_name")) == "candidate_rank"
    ]
    best_rows = joined[:5]
    worst_rows = [
        row
        for row in sorted(
            joined,
            key=lambda item: _safe_float(item.get("deep_minus_shallow")),
        )
        if _safe_float(row.get("deep_minus_shallow")) < 0.0
    ]
    deltas = [_safe_float(row.get("deep_minus_shallow")) for row in joined]
    summary = {
        "run_label": RUN_LABEL,
        "status": "completed",
        "output_dir": _repo_rel(output_dir),
        "shallow_rows_path": _repo_rel(shallow_path),
        "deep_rows_path": _repo_rel(deep_path),
        "shallow_rows": len(shallow_rows),
        "deep_rows": len(deep_rows),
        "joined_unique_rows": len(joined),
        "duplicate_keys": len(duplicates),
        "better_than_shallow": sum(
            1 for row in joined if _safe_int(row.get("deep_better_than_shallow")) == 1
        ),
        "worse_than_shallow": sum(
            1 for row in joined if _safe_int(row.get("deep_worse_than_shallow")) == 1
        ),
        "mean_deep_minus_shallow": _mean(deltas),
        "best_deep_minus_shallow": max(deltas) if deltas else 0.0,
        "worst_deep_minus_shallow": min(deltas) if deltas else 0.0,
        "mean_deep_minus_selected": _mean(
            _safe_float(row.get("deep_minus_selected")) for row in joined
        ),
        "mean_deep_minus_retained": _mean(
            _safe_float(row.get("deep_minus_retained")) for row in joined
        ),
        "updated_utc": _utc_now_text(),
        "recommended_next": "offline_rank6_safety_rule_before_runtime",
    }
    _write_csv(
        output_dir / "stage35_guard_selector_frontier_deepening_join_rows.csv",
        joined,
    )
    _write_csv(
        output_dir / "stage35_guard_selector_frontier_deepening_join_duplicate_keys.csv",
        duplicates,
    )
    _write_csv(
        output_dir / "stage35_guard_selector_frontier_deepening_join_summary_rows.csv",
        summary_rows,
    )
    _write_csv(
        output_dir / "stage35_guard_selector_frontier_deepening_join_candidate_gate_rows.csv",
        gate_rows,
    )
    _write_json(
        output_dir / "stage35_guard_selector_frontier_deepening_join_summary.json",
        summary,
    )
    _write_json(
        output_dir / "stage35_guard_selector_frontier_deepening_join_recommendation.json",
        build_recommendation(summary),
    )
    (output_dir / "stage35_guard_selector_frontier_deepening_join_readout.md").write_text(
        build_readout(
            summary=summary,
            rank_rows=rank_rows,
            gate_rows=gate_rows,
            worst_rows=worst_rows,
            best_rows=best_rows,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_extract()


if __name__ == "__main__":
    main()
