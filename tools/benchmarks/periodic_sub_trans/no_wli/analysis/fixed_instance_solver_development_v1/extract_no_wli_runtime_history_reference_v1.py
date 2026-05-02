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
        "extract_no_wli_runtime_history_reference_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


RUN_LABEL = "no_wli_runtime_history_reference_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
RUN_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli"


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if result != result:
        return float(default)
    return result


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return str(default)
    return str(value)


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _best_instance_paths(run_root: Path) -> list[Path]:
    return sorted(run_root.rglob("best_instance.json"))


def _run_dir_from_best_instance(path: Path) -> Path:
    if path.parent.name == "best":
        return path.parent.parent
    return path.parent


def load_runtime_row(best_instance_path: Path) -> dict[str, Any]:
    best_instance = _read_json(best_instance_path)
    run_dir = _run_dir_from_best_instance(best_instance_path)
    run_manifest_path = run_dir / "run_manifest.json"
    run_config_path = run_dir / "run_config.json"
    policy_spec_path = run_dir / "policy_spec.json"

    run_manifest = _read_json(run_manifest_path) if run_manifest_path.exists() else {}
    run_config = _read_json(run_config_path) if run_config_path.exists() else {}
    policy_spec = _read_json(policy_spec_path) if policy_spec_path.exists() else {}

    profile_id = _safe_str(
        best_instance.get("profile_id")
        or run_manifest.get("profile_id")
        or run_config.get("profile")
        or policy_spec.get("params", {}).get("profile")
        or "<missing>"
    )
    mode = _safe_str(
        best_instance.get("mode")
        or run_manifest.get("mode")
        or run_config.get("mode")
        or policy_spec.get("params", {}).get("run_mode")
        or "<missing>"
    )
    input_mode = _safe_str(best_instance.get("instance_input_mode") or run_config.get("instance_input_mode") or "generated")
    period = _safe_int(best_instance.get("period"))
    columns = _safe_int(best_instance.get("columns"))
    length = _safe_int(best_instance.get("length"))
    fixture_seed = _safe_int(best_instance.get("instance_source_key_seed"))
    search_seed = _safe_int(best_instance.get("search_seed"))
    elapsed_seconds = _safe_float(
        best_instance.get("total_seconds") or run_manifest.get("elapsed_seconds")
    )
    scoring_profile = _safe_str(
        run_manifest.get("scoring_experiment", {}).get("profile")
        or run_config.get("scoring_experiment", {}).get("profile")
    )
    stage1_scorer = _safe_str(run_config.get("scorer_schedule", {}).get("stage1"))
    stage2_scorer = _safe_str(run_config.get("scorer_schedule", {}).get("stage2"))
    stage3_scorer = _safe_str(run_config.get("scorer_schedule", {}).get("stage3"))
    shape_key = f"{input_mode}|p{period}|c{columns}|l{length}"

    return {
        "run_id": _safe_str(best_instance.get("run_id") or run_manifest.get("run_id")),
        "generated_utc": _safe_str(run_manifest.get("generated_utc")),
        "completed_utc": _safe_str(run_manifest.get("completed_utc")),
        "profile_id": profile_id,
        "mode": mode,
        "policy_id": _safe_str(policy_spec.get("policy_id")),
        "scoring_profile": scoring_profile,
        "instance_input_mode": input_mode,
        "shape_key": shape_key,
        "period": period,
        "columns": columns,
        "length": length,
        "fixture_seed": fixture_seed,
        "search_seed": search_seed,
        "best_stage": _safe_str(best_instance.get("best_stage")),
        "status": _safe_str(best_instance.get("status")),
        "outcome_code": _safe_str(best_instance.get("outcome_code")),
        "best_match_ratio": _safe_float(best_instance.get("best_match_ratio")),
        "elapsed_seconds": elapsed_seconds,
        "elapsed_hours": elapsed_seconds / 3600.0,
        "stage35_requested_cfg": _safe_int(best_instance.get("stage35_requested_cfg")),
        "stage35_rounds_completed": _safe_int(best_instance.get("stage35_rounds_completed")),
        "stage35_selected": _safe_int(best_instance.get("stage35_selected")),
        "stage1_scorer": stage1_scorer,
        "stage2_scorer": stage2_scorer,
        "stage3_scorer": stage3_scorer,
        "path": _relative_path(best_instance_path),
    }


def load_runtime_rows(run_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for best_instance_path in _best_instance_paths(run_root):
        try:
            rows.append(load_runtime_row(best_instance_path))
        except Exception:
            continue
    rows.sort(key=lambda row: (row["shape_key"], row["fixture_seed"], row["search_seed"], row["run_id"]))
    return rows


def summarize_group(rows: Iterable[dict[str, Any]], key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in key_fields)].append(row)
    out: list[dict[str, Any]] = []
    for key in sorted(grouped):
        members = grouped[key]
        hours = [float(row["elapsed_hours"]) for row in members]
        match_ratios = [float(row["best_match_ratio"]) for row in members]
        summary = {field: value for field, value in zip(key_fields, key)}
        summary.update(
            {
                "run_count": len(members),
                "min_hours": min(hours),
                "mean_hours": statistics.mean(hours),
                "max_hours": max(hours),
                "min_best_match_ratio": min(match_ratios),
                "mean_best_match_ratio": statistics.mean(match_ratios),
                "max_best_match_ratio": max(match_ratios),
            }
        )
        out.append(summary)
    return out


def build_markdown(
    rows: list[dict[str, Any]],
    shape_rows: list[dict[str, Any]],
    fixed_cell_rows: list[dict[str, Any]],
) -> str:
    generated_runs = sum(1 for row in rows if row["instance_input_mode"] == "generated")
    fixed_runs = sum(1 for row in rows if row["instance_input_mode"] == "fixed_ciphertext")
    top_shapes = sorted(shape_rows, key=lambda row: (-int(row["run_count"]), row["shape_key"]))[:12]
    lines = [
        "# No-WLI Runtime History Reference v1",
        "",
        "Scope:",
        "- retained completed no-WLI runtime bundles under `output/tools/benchmarks/periodic_sub_trans/no_wli/`",
        f"- total completed runs counted: `{len(rows)}`",
        f"- generated-input runs: `{generated_runs}`",
        f"- fixed-input runs: `{fixed_runs}`",
        "",
        "Why this note exists:",
        "- prior runtime work already contains useful wallclock evidence",
        "- planning should use retained elapsed-time history instead of calling a batch \"overnight\" by intuition",
        "",
        "Top run shapes by retained count:",
        "",
        "| shape | runs | min_hours | mean_hours | max_hours | mean_best_match |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in top_shapes:
        lines.append(
            "| `{shape_key}` | `{run_count}` | `{min_hours:.2f}` | `{mean_hours:.2f}` | `{max_hours:.2f}` | `{mean_best_match_ratio:.3f}` |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Fixed `p9/c3/l1000` retained cell timings:",
            "",
            "| fixture_seed | search_seed | runs | min_hours | mean_hours | max_hours | mean_best_match |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in fixed_cell_rows:
        lines.append(
            "| `{fixture_seed}` | `search{search_seed}` | `{run_count}` | `{min_hours:.2f}` | `{mean_hours:.2f}` | `{max_hours:.2f}` | `{mean_best_match_ratio:.3f}` |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Use cases:",
            "- use `runtime_history_rows.csv` when you need exact past run settings and durations",
            "- use `runtime_shape_summary.csv` for quick shape-level budgeting",
            "- use `runtime_fixed_p9c3l1000_cell_summary.csv` before any new fixed-panel runtime launch",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def run_extract() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    rows = load_runtime_rows(RUN_ROOT)
    shape_rows = summarize_group(rows, ("shape_key", "instance_input_mode", "period", "columns", "length"))
    family_rows = summarize_group(rows, ("profile_id", "mode", "instance_input_mode"))
    fixed_rows = [
        row
        for row in rows
        if row["instance_input_mode"] == "fixed_ciphertext"
        and int(row["period"]) == 9
        and int(row["columns"]) == 3
        and int(row["length"]) == 1000
    ]
    fixed_cell_rows = summarize_group(fixed_rows, ("fixture_seed", "search_seed"))

    _write_csv(output_dir / "runtime_history_rows.csv", rows)
    _write_csv(output_dir / "runtime_shape_summary.csv", shape_rows)
    _write_csv(output_dir / "runtime_profile_mode_summary.csv", family_rows)
    _write_csv(output_dir / "runtime_fixed_p9c3l1000_cell_summary.csv", fixed_cell_rows)
    (output_dir / "no_wli_runtime_history_reference.md").write_text(
        build_markdown(rows, shape_rows, fixed_cell_rows),
        encoding="utf-8",
    )

    summary = {
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "completed_run_count": len(rows),
        "shape_count": len(shape_rows),
        "profile_mode_count": len(family_rows),
        "fixed_p9c3l1000_cell_count": len(fixed_cell_rows),
    }
    _write_json(output_dir / "run_summary.json", summary)
    return summary


def main() -> None:
    print(json.dumps(run_extract(), sort_keys=True))


if __name__ == "__main__":
    main()
