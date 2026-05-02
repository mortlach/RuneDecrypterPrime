from __future__ import annotations

import csv
import json
import math
import sys
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
        "extract_stage35_rank6_selected_start_gate_safety_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


RUN_LABEL = "stage35_rank6_selected_start_gate_safety_v1"
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
JOIN_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/"
    "stage35_guard_selector_frontier_deepening_join_rows.csv"
)
GATE_RANK = 6
SELECTED_START_GATE = 0.437

PREDICTION_LEDGER = [
    {
        "prediction": "real_late_local_rescue_phenomenon",
        "probability": "75-85%",
        "comparison_note": (
            "The question is whether the broader rank/slice pattern remains "
            "visible after dedup and safety-gate checks."
        ),
    },
    {
        "prediction": "narrow_rank_or_slice_policy_can_improve_selected_cases",
        "probability": "50-65%",
        "comparison_note": (
            "The question is whether a useful subset remains after excluding "
            "observed regressions."
        ),
    },
    {
        "prediction": "general_production_policy_from_current_signal",
        "probability": "25-40%",
        "comparison_note": (
            "The expected failure mode is case-specific fine structure rather "
            "than a general rule."
        ),
    },
    {
        "prediction": "exact_selected_start_threshold_0p437_survives_as_is",
        "probability": "15-25%",
        "comparison_note": (
            "The threshold is posthoc and should be expected to move or be "
            "replaced by a broader feature."
        ),
    },
]


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


def _mean(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        return 0.0
    return float(sum(vals) / len(vals))


def _gate_decision(row: Mapping[str, Any]) -> str:
    if _safe_int(row.get("candidate_rank")) != GATE_RANK:
        return "reject_non_rank6"
    if _safe_float(row.get("selected_start_match_ratio")) >= SELECTED_START_GATE:
        return "keep"
    return "reject_below_selected_start_gate"


def build_deep_gate_rows(join_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in join_rows:
        if _safe_int(raw.get("candidate_rank")) != GATE_RANK:
            continue
        decision = _gate_decision(raw)
        deep_minus_shallow = _safe_float(raw.get("deep_minus_shallow"))
        rows.append(
            {
                "fixture_seed": _safe_int(raw.get("fixture_seed")),
                "search_seed": _safe_int(raw.get("search_seed")),
                "candidate_rank": _safe_int(raw.get("candidate_rank")),
                "candidate_hash": str(raw.get("candidate_hash", "") or ""),
                "gate_decision": decision,
                "selected_start_match_ratio": _safe_float(
                    raw.get("selected_start_match_ratio")
                ),
                "retained_best_match_ratio": _safe_float(
                    raw.get("retained_best_match_ratio")
                ),
                "shallow_resume_best_match_ratio": _safe_float(
                    raw.get("shallow_resume_best_match_ratio")
                ),
                "deep_resume_best_match_ratio": _safe_float(
                    raw.get("deep_resume_best_match_ratio")
                ),
                "shallow_minus_selected": _safe_float(raw.get("shallow_minus_selected")),
                "deep_minus_selected": _safe_float(raw.get("deep_minus_selected")),
                "deep_minus_shallow": deep_minus_shallow,
                "deep_minus_retained": _safe_float(raw.get("deep_minus_retained")),
                "deep_better_than_shallow": int(deep_minus_shallow > 0.0),
                "deep_worse_than_shallow": int(deep_minus_shallow < 0.0),
                "selected_source": str(raw.get("selected_source", "") or ""),
                "selected_lane": str(raw.get("selected_lane", "") or ""),
            }
        )
    rows.sort(
        key=lambda row: (
            str(row["gate_decision"]),
            -_safe_float(row["deep_minus_shallow"]),
            _safe_int(row["fixture_seed"]),
            _safe_int(row["search_seed"]),
        )
    )
    return rows


def build_shallow_gate_rows(shallow_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, int, int, str]] = set()
    for raw in shallow_rows:
        if _safe_int(raw.get("candidate_rank")) != GATE_RANK:
            continue
        if _safe_int(raw.get("stage35_selected")) != 1:
            continue
        key = (
            _safe_int(raw.get("fixture_seed")),
            _safe_int(raw.get("search_seed")),
            _safe_int(raw.get("candidate_rank")),
            str(raw.get("candidate_hash", "") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        selected_delta = _safe_float(raw.get("resume_minus_selected"))
        rows.append(
            {
                "fixture_seed": key[0],
                "search_seed": key[1],
                "candidate_rank": key[2],
                "candidate_hash": key[3],
                "gate_decision": _gate_decision(raw),
                "selected_start_match_ratio": _safe_float(
                    raw.get("selected_start_match_ratio")
                ),
                "retained_best_match_ratio": _safe_float(
                    raw.get("retained_best_match_ratio")
                ),
                "shallow_resume_best_match_ratio": _safe_float(
                    raw.get("resume_best_match_ratio")
                ),
                "shallow_minus_selected": selected_delta,
                "shallow_minus_retained": _safe_float(raw.get("resume_minus_retained")),
                "shallow_positive_vs_selected": int(selected_delta > 0.0),
                "shallow_negative_vs_selected": int(selected_delta < 0.0),
                "selected_source": str(raw.get("selected_source", "") or ""),
                "selected_lane": str(raw.get("selected_lane", "") or ""),
            }
        )
    rows.sort(
        key=lambda row: (
            str(row["gate_decision"]),
            -_safe_float(row["shallow_minus_selected"]),
            _safe_int(row["fixture_seed"]),
            _safe_int(row["search_seed"]),
        )
    )
    return rows


def _summarize_deep(rows: list[Mapping[str, Any]], decision: str) -> dict[str, Any]:
    subset = [row for row in rows if str(row.get("gate_decision")) == decision]
    deltas = [_safe_float(row.get("deep_minus_shallow")) for row in subset]
    return {
        "gate_decision": decision,
        "rows": len(subset),
        "better_than_shallow": sum(1 for delta in deltas if delta > 0.0),
        "worse_than_shallow": sum(1 for delta in deltas if delta < 0.0),
        "mean_deep_minus_shallow": _mean(deltas),
        "min_deep_minus_shallow": min(deltas) if deltas else 0.0,
        "max_deep_minus_shallow": max(deltas) if deltas else 0.0,
        "mean_deep_minus_selected": _mean(
            _safe_float(row.get("deep_minus_selected")) for row in subset
        ),
        "mean_deep_minus_retained": _mean(
            _safe_float(row.get("deep_minus_retained")) for row in subset
        ),
    }


def _summarize_shallow(rows: list[Mapping[str, Any]], decision: str) -> dict[str, Any]:
    subset = [row for row in rows if str(row.get("gate_decision")) == decision]
    deltas = [_safe_float(row.get("shallow_minus_selected")) for row in subset]
    return {
        "gate_decision": decision,
        "rows": len(subset),
        "positive_vs_selected": sum(1 for delta in deltas if delta > 0.0),
        "negative_vs_selected": sum(1 for delta in deltas if delta < 0.0),
        "mean_shallow_minus_selected": _mean(deltas),
        "min_shallow_minus_selected": min(deltas) if deltas else 0.0,
        "max_shallow_minus_selected": max(deltas) if deltas else 0.0,
    }


def build_readout(
    *,
    summary: Mapping[str, Any],
    deep_rows: list[Mapping[str, Any]],
    shallow_rows: list[Mapping[str, Any]],
) -> str:
    rejected_deep_positives = [
        row
        for row in deep_rows
        if str(row.get("gate_decision")) != "keep"
        and _safe_int(row.get("deep_better_than_shallow")) == 1
    ]
    rejected_deep_positives.sort(
        key=lambda row: -_safe_float(row.get("deep_minus_shallow"))
    )
    lines = [
        "# Stage35 Rank6 Selected-Start Gate Safety v1",
        "",
        "Prediction Ledger:",
        "",
    ]
    for item in PREDICTION_LEDGER:
        lines.append(
            "- `{}`: `{}`".format(item["prediction"], item["probability"])
        )
    lines.extend(
        [
            "",
            "Chat Reminder:",
            "",
            "- when this analysis branch closes, explicitly compare the final",
            "  outcome against the prediction ledger in chat",
            "",
            "Gate:",
            "",
            f"- candidate rank: `{GATE_RANK}`",
            f"- selected-start threshold: `{SELECTED_START_GATE}`",
            "",
            "Deepening Evidence:",
            "",
            f"- rank-6 unique rows: `{summary['deep_rank6_rows']}`",
            f"- kept rows: `{summary['deep_keep_rows']}`",
            f"- kept better/worse: `{summary['deep_keep_better']} / {summary['deep_keep_worse']}`",
            f"- rejected rows: `{summary['deep_reject_rows']}`",
            f"- rejected better/worse: `{summary['deep_reject_better']} / {summary['deep_reject_worse']}`",
            f"- all observed rank-6 deepening regressions removed: `{summary['all_deep_rank6_regressions_removed']}`",
            "",
            "Shallow Evidence:",
            "",
            f"- rank-6 selected shallow rows: `{summary['shallow_rank6_rows']}`",
            f"- shallow kept rows: `{summary['shallow_keep_rows']}`",
            f"- shallow kept positives/negatives: `{summary['shallow_keep_positive']} / {summary['shallow_keep_negative']}`",
            f"- shallow rejected positives/negatives: `{summary['shallow_reject_positive']} / {summary['shallow_reject_negative']}`",
            "",
            "Rejected Deepening Positives:",
            "",
        ]
    )
    for row in rejected_deep_positives:
        lines.append(
            "- `{}/{} rank {}` `{}`: deep-shallow `{:+.6f}`, deep-selected `{:+.6f}`".format(
                row["fixture_seed"],
                row["search_seed"],
                row["candidate_rank"],
                row["candidate_hash"],
                _safe_float(row.get("deep_minus_shallow")),
                _safe_float(row.get("deep_minus_selected")),
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- the gate removes the observed rank-6 deepening regressions",
            "- the gate is too conservative to promote directly because it rejects",
            "  several real positives, including a large `1111/search7002` row",
            "- the exact threshold remains posthoc and should not be treated as a",
            "  validated rule",
            "",
            "Recommendation:",
            "",
            "- do not launch runtime from this gate as-is",
            "- next useful step is a predeclared policy sketch that either softens",
            "  the selected-start gate or combines it with a second non-seed feature",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_extract() -> dict[str, Any]:
    shallow_path = REPO_ROOT / SHALLOW_ROWS_REL
    join_path = REPO_ROOT / JOIN_ROWS_REL
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    shallow_rows = build_shallow_gate_rows(_read_csv(shallow_path))
    deep_rows = build_deep_gate_rows(_read_csv(join_path))
    deep_keep = _summarize_deep(deep_rows, "keep")
    deep_reject = _summarize_deep(deep_rows, "reject_below_selected_start_gate")
    shallow_keep = _summarize_shallow(shallow_rows, "keep")
    shallow_reject = _summarize_shallow(
        shallow_rows,
        "reject_below_selected_start_gate",
    )
    observed_deep_regressions = [
        row for row in deep_rows if _safe_int(row.get("deep_worse_than_shallow")) == 1
    ]
    kept_deep_regressions = [
        row
        for row in observed_deep_regressions
        if str(row.get("gate_decision")) == "keep"
    ]
    rejected_deep_positives = [
        row
        for row in deep_rows
        if str(row.get("gate_decision")) != "keep"
        and _safe_int(row.get("deep_better_than_shallow")) == 1
    ]
    summary = {
        "run_label": RUN_LABEL,
        "status": "completed",
        "output_dir": _repo_rel(output_dir),
        "shallow_rows_path": _repo_rel(shallow_path),
        "join_rows_path": _repo_rel(join_path),
        "gate_rank": GATE_RANK,
        "selected_start_gate": SELECTED_START_GATE,
        "deep_rank6_rows": len(deep_rows),
        "deep_keep_rows": int(deep_keep["rows"]),
        "deep_keep_better": int(deep_keep["better_than_shallow"]),
        "deep_keep_worse": int(deep_keep["worse_than_shallow"]),
        "deep_keep_mean_delta_vs_shallow": float(deep_keep["mean_deep_minus_shallow"]),
        "deep_reject_rows": int(deep_reject["rows"]),
        "deep_reject_better": int(deep_reject["better_than_shallow"]),
        "deep_reject_worse": int(deep_reject["worse_than_shallow"]),
        "deep_reject_mean_delta_vs_shallow": float(
            deep_reject["mean_deep_minus_shallow"]
        ),
        "observed_deep_rank6_regressions": len(observed_deep_regressions),
        "kept_deep_rank6_regressions": len(kept_deep_regressions),
        "all_deep_rank6_regressions_removed": int(len(kept_deep_regressions) == 0),
        "rejected_deep_positive_rows": len(rejected_deep_positives),
        "shallow_rank6_rows": len(shallow_rows),
        "shallow_keep_rows": int(shallow_keep["rows"]),
        "shallow_keep_positive": int(shallow_keep["positive_vs_selected"]),
        "shallow_keep_negative": int(shallow_keep["negative_vs_selected"]),
        "shallow_keep_mean_delta_vs_selected": float(
            shallow_keep["mean_shallow_minus_selected"]
        ),
        "shallow_reject_rows": int(shallow_reject["rows"]),
        "shallow_reject_positive": int(shallow_reject["positive_vs_selected"]),
        "shallow_reject_negative": int(shallow_reject["negative_vs_selected"]),
        "shallow_reject_mean_delta_vs_selected": float(
            shallow_reject["mean_shallow_minus_selected"]
        ),
        "interpretation": (
            "gate_removes_observed_rank6_deepening_regressions_but_rejects_real_positives"
        ),
        "recommendation": "do_not_runtime_canary_gate_as_is_design_predeclared_softened_rule",
        "chat_reminder": (
            "When this analysis branch closes, compare final outcome against "
            "the prediction ledger in chat."
        ),
        "updated_utc": _utc_now_text(),
    }
    _write_csv(
        output_dir / "stage35_rank6_selected_start_gate_safety_deep_rows.csv",
        deep_rows,
    )
    _write_csv(
        output_dir / "stage35_rank6_selected_start_gate_safety_shallow_rows.csv",
        shallow_rows,
    )
    _write_csv(
        output_dir / "stage35_rank6_selected_start_gate_safety_deep_summary_rows.csv",
        [deep_keep, deep_reject],
    )
    _write_csv(
        output_dir / "stage35_rank6_selected_start_gate_safety_shallow_summary_rows.csv",
        [shallow_keep, shallow_reject],
    )
    _write_json(
        output_dir / "stage35_rank6_selected_start_gate_safety_summary.json",
        summary,
    )
    _write_json(
        output_dir / "stage35_rank6_selected_start_gate_prediction_ledger.json",
        {
            "prediction_ledger": PREDICTION_LEDGER,
            "chat_reminder": summary["chat_reminder"],
        },
    )
    (
        output_dir / "stage35_rank6_selected_start_gate_safety_readout.md"
    ).write_text(
        build_readout(summary=summary, deep_rows=deep_rows, shallow_rows=shallow_rows),
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_extract()


if __name__ == "__main__":
    main()
