#!/usr/bin/env python3
"""Run all canonical tutorials and write a timing report under output/.

Targets (import + main):
  - tutorials.v1.Tutorial_Vigenere_GeneralMap
  - tutorials.v1.Tutorial_ColumnarTransposition
  - tutorials.v1.Tutorial_MonoSubstitution_GA
  - tutorials.v1.Tutorial_MonoSubstitution_SA
  - tutorials.v1.Tutorial_MonoSubstitution_HYBRID

Notes:
  - This runner is for timing/health checks; correctness is covered by tests.
  - Only writes under output/tools/benchmarks/… and prints a repo‑relative path.
"""

from __future__ import annotations

import importlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import List, Dict, Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def git_short_hash() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root())
        return (out.decode().strip() or "nogit")
    except Exception:
        return "nogit"


TUTORIAL_MODULES: List[str] = [
    "tutorials.v1.Tutorial_Vigenere_GeneralMap",
    "tutorials.v1.Tutorial_ColumnarTransposition",
    "tutorials.v1.Tutorial_MonoSubstitution_GA",
    "tutorials.v1.Tutorial_MonoSubstitution_SA",
    "tutorials.v1.Tutorial_MonoSubstitution_HYBRID",
]


def run_one(modname: str) -> Dict[str, Any]:
    t0 = time.perf_counter()
    status = "ok"
    err = ""
    try:
        mod = importlib.import_module(modname)
        main = getattr(mod, "main", None)
        if callable(main):
            main()
        else:
            # Fallback: execute top-level import (some tutorials execute on import)
            pass
    except Exception as ex:
        status = "error"
        err = f"{ex.__class__.__name__}: {ex}"
    dt = time.perf_counter() - t0
    return {"name": modname, "status": status, "seconds": round(dt, 3), "error": err}


def write_reports(rows: List[Dict[str, Any]]) -> Path:
    root = repo_root()
    out_root = root / "output" / "tools" / "benchmarks"
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"{stamp}__bench__{git_short_hash()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    # CSV
    header = "name,status,seconds,error\n"
    csv = header + "\n".join(
        f"{r['name']},{r['status']},{r['seconds']},{r['error'].replace(',', ';')}" for r in rows
    ) + "\n"
    (run_dir / "tutorials_results.csv").write_text(csv, encoding="utf-8")
    # JSON
    (run_dir / "tutorials_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return run_dir


def main() -> int:
    rows = [run_one(m) for m in TUTORIAL_MODULES]
    # Console table
    print("name,status,seconds")
    for r in rows:
        print(f"{r['name']},{r['status']},{r['seconds']}")
    run_dir = write_reports(rows)
    try:
        rel = run_dir.relative_to(repo_root())
    except ValueError:
        rel = run_dir
    print(f"[run-all-tutorials] Reports written to {rel}")
    # Non-zero exit if any failed (useful for quick health checks)
    failed = [r for r in rows if r["status"] != "ok"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

