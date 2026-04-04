from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path("output/tools/benchmarks/periodic_sub_trans/no_wli")
CATALOG_ROOT = Path("output/tools/benchmarks/periodic_sub_trans/no_wli_catalog")

RUN_PREFIX = "__bench_solve_pipeline_no_wli__"
SPECIAL_ANALYSIS_DIRS = (
    "phasec_rescue_replay",
    "phasec_slice_signal_analysis",
    "stage35_substitution_replay",
    "word_ngram_tiebreak_profile",
    "legacy_import",
)


def _read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iso_utc_from_stat(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()


def _rel(path: Path) -> str:
    return str(path).replace("\\", "/")


def _count_jsonl_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
    except Exception:
        return 0


def _artifact_stage35_selected(data: dict[str, Any]) -> int:
    direct = data.get("stage35_selected", None)
    if isinstance(direct, (int, float, bool)):
        return int(direct)
    diag = data.get("stage3_diagnostics", {})
    if isinstance(diag, dict):
        nested = diag.get("stage35_selected", None)
        if isinstance(nested, (int, float, bool)):
            return int(nested)
    return 0


def _artifact_seed(data: dict[str, Any]) -> int | None:
    for key in ("key_seed", "seed"):
        value = data.get(key, None)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
    return None


def _build_run_manifest() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_dir in sorted(
        (
            child
            for child in SOURCE_ROOT.iterdir()
            if child.is_dir() and RUN_PREFIX in child.name
        ),
        key=lambda path: path.name,
    ):
        final_files = sorted(run_dir.glob("final_instances/*.json"))
        best_ratio = float("nan")
        best_score = float("nan")
        best_final_path = ""
        stage35_selected_count = 0
        for final_path in final_files:
            data = _read_json(final_path)
            if not isinstance(data, dict):
                continue
            ratio = data.get("best_match_ratio")
            score = data.get("best_score")
            if isinstance(ratio, (int, float)) and (
                best_final_path == "" or float(ratio) > best_ratio
            ):
                best_ratio = float(ratio)
                if isinstance(score, (int, float)):
                    best_score = float(score)
                best_final_path = _rel(final_path)
            if _artifact_stage35_selected(data) == 1:
                stage35_selected_count += 1
        checkpoint_path = run_dir / "phasec_start_checkpoints.jsonl"
        row = {
            "run_dir": run_dir.name,
            "run_path": _rel(run_dir),
            "last_write_utc": _iso_utc_from_stat(run_dir),
            "has_run_config": int((run_dir / "run_config.json").exists()),
            "has_stages": int((run_dir / "stages.json").exists()),
            "final_instance_count": len(final_files),
            "best_match_ratio": "" if best_final_path == "" else f"{best_ratio:.6f}",
            "best_score": "" if best_final_path == "" else f"{best_score:.6f}",
            "best_final_instance_path": best_final_path,
            "has_phasec_checkpoints": int(checkpoint_path.exists()),
            "phasec_checkpoint_rows": _count_jsonl_rows(checkpoint_path),
            "stage35_selected_count": stage35_selected_count,
        }
        rows.append(row)
    return rows


def _build_special_manifest() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in SPECIAL_ANALYSIS_DIRS:
        base = SOURCE_ROOT / name
        if not base.exists():
            continue
        for child in sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.name):
            summary_path = child / "summary.json"
            row = {
                "category": name,
                "name": child.name,
                "path": _rel(child),
                "last_write_utc": _iso_utc_from_stat(child),
                "has_summary_json": int(summary_path.exists()),
                "summary_path": _rel(summary_path) if summary_path.exists() else "",
            }
            rows.append(row)
    return rows


def _build_state_manifest() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for child in sorted(SOURCE_ROOT.iterdir(), key=lambda p: p.name):
        if child.is_dir():
            continue
        if not child.name.startswith("fixture_matrix_"):
            continue
        rows.append(
            {
                "name": child.name,
                "path": _rel(child),
                "last_write_utc": _iso_utc_from_stat(child),
                "size_bytes": child.stat().st_size,
                "kind": (
                    "run_state"
                    if "_run_state_" in child.name
                    else "run_events"
                    if "_run_events_" in child.name
                    else "plan"
                    if "_plan_" in child.name
                    else "other"
                ),
            }
        )
    return rows


def _build_notable_artifacts(run_rows: list[dict[str, Any]]) -> dict[str, Any]:
    final_rows: list[dict[str, Any]] = []
    for run_row in run_rows:
        best_path = str(run_row.get("best_final_instance_path") or "")
        if not best_path:
            continue
        final_path = Path(best_path)
        data = _read_json(final_path)
        if not isinstance(data, dict):
            continue
        final_rows.append(
            {
                "path": best_path,
                "best_match_ratio": float(data.get("best_match_ratio", float("nan"))),
                "best_score": float(data.get("best_score", float("nan"))),
                "best_stage": data.get("best_stage"),
                "period": data.get("period"),
                "columns": data.get("columns"),
                "length": data.get("length"),
                "seed": _artifact_seed(data),
                "stage35_selected": _artifact_stage35_selected(data),
            }
        )
    final_rows = [row for row in final_rows if isinstance(row["best_match_ratio"], float)]
    best_overall = sorted(
        final_rows,
        key=lambda row: (
            -float(row["best_match_ratio"]),
            -float(row["best_score"]),
            str(row["path"]),
        ),
    )[:20]
    best_p9_c3 = [
        row
        for row in best_overall
        if int(row.get("period") or 0) == 9 and int(row.get("columns") or 0) == 3
    ]
    if len(best_p9_c3) < 10:
        best_p9_c3 = sorted(
            (
                row
                for row in final_rows
                if int(row.get("period") or 0) == 9 and int(row.get("columns") or 0) == 3
            ),
            key=lambda row: (
                -float(row["best_match_ratio"]),
                -float(row["best_score"]),
                str(row["path"]),
            ),
        )[:10]
    return {
        "best_overall": best_overall,
        "best_p9_c3": best_p9_c3,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    CATALOG_ROOT.mkdir(parents=True, exist_ok=True)

    run_rows = _build_run_manifest()
    special_rows = _build_special_manifest()
    state_rows = _build_state_manifest()
    notable = _build_notable_artifacts(run_rows)

    inventory = {
        "catalog_version": "v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "source_root": _rel(SOURCE_ROOT),
        "catalog_root": _rel(CATALOG_ROOT),
        "run_dir_count": len(run_rows),
        "final_instance_count": sum(int(row["final_instance_count"]) for row in run_rows),
        "phasec_checkpoint_run_count": sum(
            int(row["has_phasec_checkpoints"]) for row in run_rows
        ),
        "stage35_selected_run_count": sum(
            1 for row in run_rows if int(row["stage35_selected_count"]) > 0
        ),
        "special_analysis_dir_count": len(special_rows),
        "fixture_matrix_file_count": len(state_rows),
        "external_mirror_note": (
            "Compared on 2026-03-21 against the DJ-MINI no_wli tree; "
            "all 61 remote run dirs were already present locally, so no remote-only "
            "no_wli run data needed copying."
        ),
    }

    _write_csv(CATALOG_ROOT / "run_manifest.csv", run_rows)
    _write_csv(CATALOG_ROOT / "special_analysis_manifest.csv", special_rows)
    _write_csv(CATALOG_ROOT / "fixture_matrix_files.csv", state_rows)
    (CATALOG_ROOT / "inventory_summary.json").write_text(
        json.dumps(inventory, indent=2),
        encoding="utf-8",
    )
    (CATALOG_ROOT / "notable_artifacts.json").write_text(
        json.dumps(notable, indent=2),
        encoding="utf-8",
    )
    _write_csv(
        CATALOG_ROOT / "best_p9_c3_runs.csv",
        list(notable.get("best_p9_c3", [])),
    )

    print(_rel(CATALOG_ROOT))


def refresh_catalog_safely(*, print_fn=print) -> None:
    try:
        main()
    except Exception as exc:
        print_fn(
            f"[no_wli_output_catalog] refresh_failed error={exc}",
        )


if __name__ == "__main__":
    main()
