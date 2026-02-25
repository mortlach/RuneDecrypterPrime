from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_csv_rows(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    rows_list: List[Dict[str, Any]] = list(rows)
    if not rows_list:
        return

    fieldnames: List[str] = []
    seen: set[str] = set()
    for row in rows_list:
        for key in row.keys():
            k = str(key)
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_list:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def append_csv_row(
    path: Path,
    row: Dict[str, Any],
    *,
    merge_fieldnames: bool = False,
) -> None:
    if not row:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    new_fields = [str(k) for k in row.keys()]
    if (not path.exists()) or path.stat().st_size == 0:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=new_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerow({k: row.get(k, "") for k in new_fields})
        return

    old_fields: List[str] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        old_fields = [str(h) for h in header if str(h)]

    if not old_fields:
        old_fields = list(new_fields)

    needs_merge = merge_fieldnames and any(k not in old_fields for k in new_fields)
    if not needs_merge:
        fieldnames = old_fields
        safe_row = {k: row.get(k, "") for k in fieldnames}
        with path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writerow(safe_row)
        return

    merged_fields = list(old_fields)
    for key in new_fields:
        if key not in merged_fields:
            merged_fields.append(key)

    old_rows: List[Dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for rec in reader:
            clean = {str(k): v for k, v in rec.items() if k is not None}
            old_rows.append(clean)

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=merged_fields, extrasaction="ignore")
        writer.writeheader()
        for rec in old_rows:
            writer.writerow({k: rec.get(k, "") for k in merged_fields})
        writer.writerow({k: row.get(k, "") for k in merged_fields})


def write_pipeline_snapshot_files(
    *,
    run_dir: Path,
    instances: Sequence[Dict[str, Any]],
    stages: Sequence[Dict[str, Any]],
    summary: Dict[str, Any],
) -> None:
    write_json(run_dir / "instances.json", list(instances))
    write_json(run_dir / "stages.json", list(stages))
    write_json(run_dir / "summary.json", dict(summary))
    write_csv_rows(run_dir / "instances.csv", list(instances))
    write_csv_rows(run_dir / "stages.csv", list(stages))

