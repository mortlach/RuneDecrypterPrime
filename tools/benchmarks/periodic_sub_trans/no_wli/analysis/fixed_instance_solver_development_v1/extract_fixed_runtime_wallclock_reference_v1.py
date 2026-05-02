from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_fixed_runtime_wallclock_reference_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


RUN_LABEL = "fixed_runtime_wallclock_reference_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
BEST_INSTANCE_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli"
TARGET_PERIOD = 9
TARGET_COLUMNS = 3
TARGET_LENGTH = 1000
TARGET_INPUT_MODE = "fixed_ciphertext"


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if result != result:
        return float(default)
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def is_target_fixed_runtime_best_instance(payload: dict[str, Any]) -> bool:
    return (
        str(payload.get("instance_input_mode", "")) == TARGET_INPUT_MODE
        and _safe_int(payload.get("period")) == TARGET_PERIOD
        and _safe_int(payload.get("columns")) == TARGET_COLUMNS
        and _safe_int(payload.get("length")) == TARGET_LENGTH
    )


def load_completed_fixed_runtime_rows(best_instance_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for best_instance_path in best_instance_root.rglob("best_instance.json"):
        payload = _read_json(best_instance_path)
        if not is_target_fixed_runtime_best_instance(payload):
            continue
        rows.append(
            {
                "run_id": str(payload.get("run_id", "")),
                "fixture_seed": _safe_int(payload.get("instance_source_key_seed")),
                "search_seed": _safe_int(payload.get("search_seed")),
                "elapsed_seconds": _safe_float(payload.get("total_seconds")),
                "elapsed_hours": _safe_float(payload.get("total_seconds")) / 3600.0,
                "best_match_ratio": _safe_float(payload.get("best_match_ratio")),
                "best_stage": str(payload.get("best_stage", "")),
                "status": str(payload.get("status", "")),
                "outcome_code": str(payload.get("outcome_code", "")),
                "path": _relative_path(best_instance_path),
            }
        )
    rows.sort(key=lambda row: (row["fixture_seed"], row["search_seed"], row["run_id"]))
    return rows


def summarize_group(
    rows: Iterable[dict[str, Any]],
    key_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in key_fields)].append(row)
    summary_rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        members = grouped[key]
        elapsed_hours = [float(row["elapsed_hours"]) for row in members]
        best_matches = [float(row["best_match_ratio"]) for row in members]
        payload = {
            field: value for field, value in zip(key_fields, key)
        }
        payload.update(
            {
                "run_count": len(members),
                "min_hours": min(elapsed_hours),
                "mean_hours": statistics.mean(elapsed_hours),
                "max_hours": max(elapsed_hours),
                "min_best_match_ratio": min(best_matches),
                "mean_best_match_ratio": statistics.mean(best_matches),
                "max_best_match_ratio": max(best_matches),
            }
        )
        summary_rows.append(payload)
    return summary_rows


def build_planning_note(
    completed_row_count: int,
    cell_rows: list[dict[str, Any]],
    seed_rows: list[dict[str, Any]],
    search_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# Fixed Runtime Wallclock Reference v1",
        "",
        "Scope:",
        "- retained completed `fixed_ciphertext` no-WLI runs only",
        "- target basis: `p9 / c3 / l1000`",
        f"- retained completed runs counted: `{int(completed_row_count)}`",
        "",
        "Why this note exists:",
        "- runtime planning should not treat \"one overnight run\" as a generic unit",
        "- use retained cell timings before launching any new long runtime job or matrix",
        "",
        "Current high-signal read:",
    ]
    if seed_rows:
        slowest_seed = max(seed_rows, key=lambda row: float(row["max_hours"]))
        fastest_seed = min(seed_rows, key=lambda row: float(row["mean_hours"]))
        lines.extend(
            [
                f"- slowest retained fixture family so far: `{int(slowest_seed['fixture_seed'])}` with max `{float(slowest_seed['max_hours']):.2f}h`",
                f"- cheapest retained fixture family so far: `{int(fastest_seed['fixture_seed'])}` with mean `{float(fastest_seed['mean_hours']):.2f}h`",
            ]
        )
    if search_rows:
        slowest_search = max(search_rows, key=lambda row: float(row["max_hours"]))
        lines.append(
            f"- heaviest retained search seed so far: `search{int(slowest_search['search_seed'])}` with max `{float(slowest_search['max_hours']):.2f}h`"
        )
    lines.extend(
        [
            "",
            "Planning rules:",
            "- use exact cell history first when a matching retained cell exists",
            "- otherwise use the worse of fixture-family max and search-seed max as the first conservative budget anchor",
            "- do not call a batch \"overnight\" unless the serial sum fits with margin",
            "- if a first canary already overshoots the intended session budget, stop and rescope",
            "",
            "Per-cell retained timings:",
            "",
            "| fixture_seed | search_seed | runs | min_hours | mean_hours | max_hours | mean_best_match | max_best_match |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in cell_rows:
        lines.append(
            "| `{fixture_seed}` | `search{search_seed}` | `{run_count}` | "
            "`{min_hours:.2f}` | `{mean_hours:.2f}` | `{max_hours:.2f}` | "
            "`{mean_best_match_ratio:.3f}` | `{max_best_match_ratio:.3f}` |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Per-fixture summary:",
            "",
            "| fixture_seed | runs | min_hours | mean_hours | max_hours |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in seed_rows:
        lines.append(
            "| `{fixture_seed}` | `{run_count}` | `{min_hours:.2f}` | `{mean_hours:.2f}` | `{max_hours:.2f}` |".format(
                fixture_seed=row["fixture_seed"],
                run_count=row["run_count"],
                min_hours=row["min_hours"],
                mean_hours=row["mean_hours"],
                max_hours=row["max_hours"],
            )
        )
    lines.extend(
        [
            "",
            "Per-search-seed summary:",
            "",
            "| search_seed | runs | min_hours | mean_hours | max_hours |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in search_rows:
        lines.append(
            "| `search{search_seed}` | `{run_count}` | `{min_hours:.2f}` | `{mean_hours:.2f}` | `{max_hours:.2f}` |".format(
                search_seed=row["search_seed"],
                run_count=row["run_count"],
                min_hours=row["min_hours"],
                mean_hours=row["mean_hours"],
                max_hours=row["max_hours"],
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def run_extract() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    rows = load_completed_fixed_runtime_rows(BEST_INSTANCE_ROOT)
    cell_summary = summarize_group(rows, ("fixture_seed", "search_seed"))
    seed_summary = summarize_group(rows, ("fixture_seed",))
    search_summary = summarize_group(rows, ("search_seed",))

    _write_csv(output_dir / "fixed_runtime_completed_rows.csv", rows)
    _write_csv(output_dir / "fixed_runtime_cell_summary.csv", cell_summary)
    _write_csv(output_dir / "fixed_runtime_fixture_seed_summary.csv", seed_summary)
    _write_csv(output_dir / "fixed_runtime_search_seed_summary.csv", search_summary)
    (output_dir / "fixed_runtime_wallclock_reference.md").write_text(
        build_planning_note(len(rows), cell_summary, seed_summary, search_summary),
        encoding="utf-8",
    )

    summary = {
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "completed_row_count": len(rows),
        "cell_count": len(cell_summary),
        "fixture_seed_count": len(seed_summary),
        "search_seed_count": len(search_summary),
    }
    _write_json(output_dir / "run_summary.json", summary)
    return summary


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
