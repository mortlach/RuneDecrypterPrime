from __future__ import annotations

"""Port legacy solve-proof history into flavor-specific logs.

Current target:
- source: tools/benchmarks/solve_proof/proven_solve_pipeline_log.csv
- dest:   tools/benchmarks/solve_proof/proven_solve_pipeline_col_then_sub_log.csv

Non-destructive:
- source log is never modified
- destination is append-only
- dedupe is applied to avoid duplicate imports across repeated runs
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[4]
SOURCE_LOG = ROOT / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_log.csv"
DEST_LOG = ROOT / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_col_then_sub_log.csv"
MANIFEST = ROOT / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_col_then_sub_import_manifest.json"

DEFAULT_FIELDS = [
    "timestamp_utc",
    "run_id",
    "profile_id",
    "fixture_id",
    "text_id",
    "key_seed",
    "period",
    "columns",
    "length",
    "status",
    "solve_threshold",
    "best_match_ratio",
    "best_stage",
    "stage1_sub_key_match",
    "stage2_match_ratio",
    "stage3_match_ratio",
    "total_seconds",
    "total_evals",
    "notes",
]


def _read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fields = [str(x) for x in (reader.fieldnames or []) if str(x)]
        rows = [dict(row) for row in reader]
    return fields, rows


def _dedupe_key(row: Dict[str, str]) -> Tuple[str, ...]:
    return (
        str(row.get("timestamp_utc", "")),
        str(row.get("run_id", "")),
        str(row.get("fixture_id", "")),
        str(row.get("text_id", "")),
        str(row.get("key_seed", "")),
        str(row.get("status", "")),
        str(row.get("best_stage", "")),
        str(row.get("best_match_ratio", "")),
        str(row.get("notes", "")),
    )


def _is_compatible(row: Dict[str, str]) -> bool:
    fixture = str(row.get("fixture_id", "")).strip()
    if not fixture:
        return False
    try:
        int(str(row.get("text_id", "")).strip())
        int(str(row.get("key_seed", "")).strip())
    except Exception:
        return False
    return True


def _normalise_row(src: Dict[str, str], fields: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key in fields:
        out[str(key)] = str(src.get(str(key), ""))
    if not str(out.get("profile_id", "")).strip():
        out["profile_id"] = "legacy_pipeline_col_then_sub"
    return out


def port_history() -> Dict[str, object]:
    src_fields, src_rows = _read_csv(SOURCE_LOG)
    dst_fields, dst_rows = _read_csv(DEST_LOG)

    if not src_rows:
        result = {
            "source": str(SOURCE_LOG),
            "destination": str(DEST_LOG),
            "status": "no_source_rows",
            "imported": 0,
            "skipped_duplicates": 0,
            "skipped_incompatible": 0,
        }
        MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    fields = dst_fields if dst_fields else list(DEFAULT_FIELDS)
    existing = {_dedupe_key(r) for r in dst_rows}

    imported_rows: List[Dict[str, str]] = []
    skipped_duplicates = 0
    skipped_incompatible = 0

    for src in src_rows:
        if not _is_compatible(src):
            skipped_incompatible += 1
            continue
        row = _normalise_row(src, fields)
        key = _dedupe_key(row)
        if key in existing:
            skipped_duplicates += 1
            continue
        imported_rows.append(row)
        existing.add(key)

    if imported_rows:
        DEST_LOG.parent.mkdir(parents=True, exist_ok=True)
        write_header = (not DEST_LOG.exists()) or DEST_LOG.stat().st_size == 0
        with DEST_LOG.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            for row in imported_rows:
                writer.writerow({k: row.get(k, "") for k in fields})

    result = {
        "source": str(SOURCE_LOG),
        "destination": str(DEST_LOG),
        "source_rows": len(src_rows),
        "destination_existing_rows": len(dst_rows),
        "imported": len(imported_rows),
        "skipped_duplicates": int(skipped_duplicates),
        "skipped_incompatible": int(skipped_incompatible),
    }
    MANIFEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    result = port_history()
    print(
        "[history-port] done "
        f"imported={int(result.get('imported', 0))} "
        f"skipped_duplicates={int(result.get('skipped_duplicates', 0))} "
        f"skipped_incompatible={int(result.get('skipped_incompatible', 0))} "
        f"manifest={MANIFEST}"
    )


if __name__ == "__main__":
    main()

