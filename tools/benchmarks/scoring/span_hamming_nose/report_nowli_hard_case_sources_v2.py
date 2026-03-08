from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parents[4]
    _SRC = _ROOT / "src"
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    if _SRC.exists() and str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))


REPO_ROOT = Path(__file__).resolve().parents[4]
NOWLI_ROOT = Path("output/tools/benchmarks/periodic_sub_trans/no_wli")
OUTPUT_ROOT = Path("output/tools/benchmarks/scoring/span_hamming_nose_nowli_sources")
RUN_LABEL = "report_nowli_hard_case_sources_v2"


def _resolve_repo_path(path_like: Path | str) -> Path:
    path = Path(path_like).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    else:
        path = path.resolve()
    return path


def _utc_now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    nowli_root = _resolve_repo_path(NOWLI_ROOT)
    output_root = _resolve_repo_path(OUTPUT_ROOT)
    run_dir = output_root / f"{_utc_now_label()}__{RUN_LABEL}"
    run_dir.mkdir(parents=True, exist_ok=True)

    run_rows: list[dict] = []
    case_rows: list[dict] = []

    print("[report_nowli_hard_case_sources_v2] scanning no-WLI runs...")
    for run_path in sorted(nowli_root.iterdir()):
        if not run_path.is_dir():
            continue
        manifest_fp = run_path / "run_manifest.json"
        audit_fp = run_path / "iteration_audit_chain.csv"
        finals_dir = run_path / "final_instances"
        if not manifest_fp.exists() or not audit_fp.exists() or not finals_dir.exists():
            continue

        try:
            manifest = json.loads(manifest_fp.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

        final_jsons = sorted(finals_dir.glob("*.json"))
        if not final_jsons:
            continue

        status_counts: Counter[str] = Counter()
        stage_counts: Counter[str] = Counter()
        n_rows = 0
        n_existing_artifacts = 0
        ratios: list[float] = []

        with open(audit_fp, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                n_rows += 1
                status = str(row.get("status", "") or "")
                best_stage = str(row.get("best_stage", "") or "")
                status_counts[status] += 1
                stage_counts[best_stage] += 1
                try:
                    ratios.append(float(row.get("best_match_ratio", "nan")))
                except Exception:
                    pass

                artifact_rel = str(row.get("artifact_relpath", "") or "")
                artifact_fp = _resolve_repo_path(artifact_rel) if artifact_rel else Path()
                if artifact_rel and artifact_fp.exists():
                    n_existing_artifacts += 1
                case_rows.append(
                    {
                        "run_name": run_path.name,
                        "artifact_relpath": artifact_rel,
                        "artifact_exists": bool(artifact_rel and artifact_fp.exists()),
                        "status": status,
                        "best_stage": best_stage,
                        "best_match_ratio": row.get("best_match_ratio", ""),
                        "fixture_id": row.get("fixture_id", ""),
                        "text_id": row.get("text_id", ""),
                        "iteration_index": row.get("iteration_index", ""),
                        "key_seed": row.get("key_seed", ""),
                        "stop_reason": row.get("stop_reason", ""),
                    }
                )

        run_rows.append(
            {
                "run_name": run_path.name,
                "final_json_count": len(final_jsons),
                "audit_row_count": n_rows,
                "artifact_exists_count": n_existing_artifacts,
                "status_counts_json": json.dumps(dict(status_counts), sort_keys=True),
                "stage_counts_json": json.dumps(dict(stage_counts), sort_keys=True),
                "best_match_ratio_min": min(ratios) if ratios else 0.0,
                "best_match_ratio_max": max(ratios) if ratios else 0.0,
                "run_id": manifest.get("run_id", ""),
            }
        )

    runs_csv = run_dir / "runs.csv"
    cases_csv = run_dir / "cases.csv"
    config_json = run_dir / "run_config.json"

    _write_csv(
        runs_csv,
        run_rows,
        [
            "run_name",
            "final_json_count",
            "audit_row_count",
            "artifact_exists_count",
            "status_counts_json",
            "stage_counts_json",
            "best_match_ratio_min",
            "best_match_ratio_max",
            "run_id",
        ],
    )
    _write_csv(
        cases_csv,
        case_rows,
        [
            "run_name",
            "artifact_relpath",
            "artifact_exists",
            "status",
            "best_stage",
            "best_match_ratio",
            "fixture_id",
            "text_id",
            "iteration_index",
            "key_seed",
            "stop_reason",
        ],
    )
    config_json.write_text(
        json.dumps(
            {
                "nowli_root": str(nowli_root),
                "run_count": len(run_rows),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"  wrote runs: {runs_csv}")
    print(f"  wrote cases: {cases_csv}")
    print(f"  wrote config: {config_json}")


if __name__ == "__main__":
    main()
