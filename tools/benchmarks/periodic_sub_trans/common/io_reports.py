from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


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

