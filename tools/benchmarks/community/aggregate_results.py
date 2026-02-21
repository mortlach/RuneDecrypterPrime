from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.benchmarks.community._campaign_common import read_jsonl, write_json

ORDERS = ("col_then_sub", "sub_then_col")
PERIOD_RANGE = tuple(range(7, 14))
COLUMN_RANGE = tuple(range(1, 14))


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return float(default)
    if not math.isfinite(out):
        return float(default)
    return out


def _safe_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _group_summary_by_cell(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group = defaultdict(lambda: {"n": 0, "solved": 0, "match_sum": 0.0, "match_max": 0.0, "seconds_sum": 0.0, "evals_sum": 0.0})
    for row in rows:
        key = (
            str(row.get("text_fixture_id", "")),
            _safe_int(row.get("period")),
            _safe_int(row.get("columns")),
            str(row.get("order", "")),
        )
        g = group[key]
        g["n"] += 1
        solved = str(row.get("status", "")) == "solved"
        if solved:
            g["solved"] += 1
        match = _safe_float(row.get("best_match_ratio"), default=0.0)
        g["match_sum"] += match
        g["match_max"] = max(float(g["match_max"]), match)
        g["seconds_sum"] += _safe_float(row.get("total_seconds"), default=0.0)
        g["evals_sum"] += _safe_float(row.get("total_evals"), default=0.0)

    out: list[dict[str, Any]] = []
    for key in sorted(group.keys()):
        fixture, period, columns, order = key
        g = group[key]
        n = max(1, int(g["n"]))
        out.append(
            {
                "text_fixture_id": fixture,
                "period": period,
                "columns": columns,
                "order": order,
                "n_jobs": int(g["n"]),
                "n_solved": int(g["solved"]),
                "solve_rate": round(float(g["solved"]) / float(n), 6),
                "best_match_mean": round(float(g["match_sum"]) / float(n), 6),
                "best_match_max": round(float(g["match_max"]), 6),
                "total_seconds_mean": round(float(g["seconds_sum"]) / float(n), 6),
                "total_evals_mean": round(float(g["evals_sum"]) / float(n), 3),
            }
        )
    return out


def _group_summary_by_profile(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group = defaultdict(lambda: {"n": 0, "solved": 0, "match_sum": 0.0, "match_max": 0.0, "seconds_sum": 0.0, "evals_sum": 0.0})
    for row in rows:
        key = str(row.get("profile_id", ""))
        g = group[key]
        g["n"] += 1
        if str(row.get("status", "")) == "solved":
            g["solved"] += 1
        match = _safe_float(row.get("best_match_ratio"), default=0.0)
        g["match_sum"] += match
        g["match_max"] = max(float(g["match_max"]), match)
        g["seconds_sum"] += _safe_float(row.get("total_seconds"), default=0.0)
        g["evals_sum"] += _safe_float(row.get("total_evals"), default=0.0)

    out: list[dict[str, Any]] = []
    for profile_id in sorted(group.keys()):
        g = group[profile_id]
        n = max(1, int(g["n"]))
        out.append(
            {
                "profile_id": profile_id,
                "n_jobs": int(g["n"]),
                "n_solved": int(g["solved"]),
                "solve_rate": round(float(g["solved"]) / float(n), 6),
                "best_match_mean": round(float(g["match_sum"]) / float(n), 6),
                "best_match_max": round(float(g["match_max"]), 6),
                "total_seconds_mean": round(float(g["seconds_sum"]) / float(n), 6),
                "total_evals_mean": round(float(g["evals_sum"]) / float(n), 3),
            }
        )
    return out


def _solve_rate_heatmap_rows(rows: list[dict[str, Any]], *, order: str) -> list[dict[str, Any]]:
    group = defaultdict(lambda: {"n": 0, "solved": 0})
    for row in rows:
        if str(row.get("order")) != order:
            continue
        key = (_safe_int(row.get("period")), _safe_int(row.get("columns")))
        group[key]["n"] += 1
        if str(row.get("status")) == "solved":
            group[key]["solved"] += 1

    heatmap_rows: list[dict[str, Any]] = []
    for period in PERIOD_RANGE:
        out_row: dict[str, Any] = {"period": period}
        for col in COLUMN_RANGE:
            g = group.get((period, col))
            if not g or int(g["n"]) == 0:
                out_row[f"c{col}"] = ""
            else:
                out_row[f"c{col}"] = round(float(g["solved"]) / float(g["n"]), 6)
        heatmap_rows.append(out_row)
    return heatmap_rows


def _stop_reason_counts_by_cell(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group = defaultdict(int)
    for row in rows:
        key = (
            str(row.get("text_fixture_id", "")),
            _safe_int(row.get("period")),
            _safe_int(row.get("columns")),
            str(row.get("order", "")),
            str(row.get("stop_reason", "")),
        )
        group[key] += 1
    out: list[dict[str, Any]] = []
    for key in sorted(group.keys()):
        fixture, period, columns, order, stop_reason = key
        out.append(
            {
                "text_fixture_id": fixture,
                "period": period,
                "columns": columns,
                "order": order,
                "stop_reason": stop_reason,
                "count": int(group[key]),
            }
        )
    return out


def _stop_reason_counts_by_profile(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group = defaultdict(int)
    for row in rows:
        key = (str(row.get("profile_id", "")), str(row.get("stop_reason", "")))
        group[key] += 1
    out: list[dict[str, Any]] = []
    for key in sorted(group.keys()):
        profile_id, stop_reason = key
        out.append({"profile_id": profile_id, "stop_reason": stop_reason, "count": int(group[key])})
    return out


def aggregate_results(*, combined_results_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = read_jsonl(combined_results_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_by_cell = _group_summary_by_cell(rows)
    summary_by_profile = _group_summary_by_profile(rows)
    heat_col_then_sub = _solve_rate_heatmap_rows(rows, order="col_then_sub")
    heat_sub_then_col = _solve_rate_heatmap_rows(rows, order="sub_then_col")
    stop_by_cell = _stop_reason_counts_by_cell(rows)
    stop_by_profile = _stop_reason_counts_by_profile(rows)

    summary_by_cell_path = output_dir / "summary_by_cell.csv"
    summary_by_profile_path = output_dir / "summary_by_profile.csv"
    heat_col_then_sub_path = output_dir / "solve_rate_heatmap_order_col_then_sub.csv"
    heat_sub_then_col_path = output_dir / "solve_rate_heatmap_order_sub_then_col.csv"
    stop_by_cell_path = output_dir / "stop_reason_counts_by_cell.csv"
    stop_by_profile_path = output_dir / "stop_reason_counts_by_profile.csv"

    _write_csv(
        summary_by_cell_path,
        [
            "text_fixture_id",
            "period",
            "columns",
            "order",
            "n_jobs",
            "n_solved",
            "solve_rate",
            "best_match_mean",
            "best_match_max",
            "total_seconds_mean",
            "total_evals_mean",
        ],
        summary_by_cell,
    )
    _write_csv(
        summary_by_profile_path,
        [
            "profile_id",
            "n_jobs",
            "n_solved",
            "solve_rate",
            "best_match_mean",
            "best_match_max",
            "total_seconds_mean",
            "total_evals_mean",
        ],
        summary_by_profile,
    )
    _write_csv(
        heat_col_then_sub_path,
        ["period"] + [f"c{col}" for col in COLUMN_RANGE],
        heat_col_then_sub,
    )
    _write_csv(
        heat_sub_then_col_path,
        ["period"] + [f"c{col}" for col in COLUMN_RANGE],
        heat_sub_then_col,
    )
    _write_csv(
        stop_by_cell_path,
        ["text_fixture_id", "period", "columns", "order", "stop_reason", "count"],
        stop_by_cell,
    )
    _write_csv(
        stop_by_profile_path,
        ["profile_id", "stop_reason", "count"],
        stop_by_profile,
    )

    report = {
        "combined_results_path": str(combined_results_path),
        "input_rows": len(rows),
        "summary_by_cell_rows": len(summary_by_cell),
        "summary_by_profile_rows": len(summary_by_profile),
        "stop_reason_by_cell_rows": len(stop_by_cell),
        "stop_reason_by_profile_rows": len(stop_by_profile),
        "outputs": {
            "summary_by_cell": str(summary_by_cell_path),
            "summary_by_profile": str(summary_by_profile_path),
            "solve_rate_heatmap_order_col_then_sub": str(heat_col_then_sub_path),
            "solve_rate_heatmap_order_sub_then_col": str(heat_sub_then_col_path),
            "stop_reason_counts_by_cell": str(stop_by_cell_path),
            "stop_reason_counts_by_profile": str(stop_by_profile_path),
        },
    }
    write_json(output_dir / "aggregate_report.json", report)
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate combined community benchmark results (v1.1).")
    parser.add_argument("--combined-results", type=Path, required=True, help="path to combined_results.jsonl")
    parser.add_argument("--output-dir", type=Path, required=True, help="output directory")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = aggregate_results(combined_results_path=args.combined_results, output_dir=args.output_dir)
    print(
        "[community] aggregate complete "
        f"input_rows={report['input_rows']} summary_by_cell={report['summary_by_cell_rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
