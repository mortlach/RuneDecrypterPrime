#!/usr/bin/env python3
"""Compare two benchmark result JSON files.

Usage:
  python tools/benchmarks/compare_runs.py <old.json> <new.json>

Prints a table with absolute and percent deltas. Flags >20% slowdowns.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    # Accept list of rows or object with rows
    if isinstance(data, dict) and "rows" in data:
        return data["rows"]
    if isinstance(data, list):
        return data
    raise SystemExit(f"Unrecognised JSON format: {path}")


def index_by_name(rows):
    return {r["name"]: r for r in rows}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: compare_runs.py <old.json> <new.json>")
        return 2
    old = index_by_name(load(Path(argv[1])))
    new = index_by_name(load(Path(argv[2])))
    names = sorted(set(old) | set(new))
    print("name,old_seconds,new_seconds,delta_s,delta_pct")
    slow = 0
    for name in names:
        o = old.get(name)
        n = new.get(name)
        osec = float(o["seconds"]) if o else float("nan")
        nsec = float(n["seconds"]) if n else float("nan")
        if not (o and n):
            print(f"{name},{osec},{nsec},,")
            continue
        ds = nsec - osec
        pct = (ds / osec * 100.0) if osec > 0 else float("inf")
        print(f"{name},{osec:.3f},{nsec:.3f},{ds:.3f},{pct:.1f}%")
        if pct > 20.0:
            slow += 1
    if slow:
        print(f"[compare] WARNING: {slow} case(s) slowed by >20%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

