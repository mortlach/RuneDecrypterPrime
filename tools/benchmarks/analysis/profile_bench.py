#!/usr/bin/env python3
"""Profile canonical tutorials/functions with cProfile and write reports under output/.

Usage examples:
  # Profile all five canonical tutorials
  python tools/benchmarks/analysis/profile_bench.py --target all --top 30

  # Profile a specific module path (dotted import)
  python tools/benchmarks/analysis/profile_bench.py --target tutorials.v1.Tutorial_MonoSubstitution_GA --top 50

Outputs (per target) are written to output/tools/benchmarks/<timestamp>__bench__<git>/:
  - <safe_name>__profile.prof   (raw pstats)
  - <safe_name>__profile.txt    (top-N cumulative time)
  - <safe_name>__profile.json   (top-N as JSON)
  - <safe_name>__categories.json (cumtime by src/rune_decrypter_prime/<category>/)
"""

from __future__ import annotations

import argparse
import cProfile
import importlib
import io
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pstats
import sys


CANONICAL_MODULES = [
    "tutorials.v1.Tutorial_Vigenere_GeneralMap",
    "tutorials.v1.Tutorial_ColumnarTransposition",
    "tutorials.v1.Tutorial_MonoSubstitution_GA",
    "tutorials.v1.Tutorial_MonoSubstitution_SA",
    "tutorials.v1.Tutorial_MonoSubstitution_HYBRID",
]

CATEGORIES = [
    "scoring",
    "solvers",
    "keyops",
    "ciphers",
    "api",
    "telemetry",
    "core",
    "utils",
    "backends",
]


def repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in [cur.parent, *cur.parents]:
        if (parent / "src" / "rune_decrypter_prime").exists():
            return parent
    return cur.parents[0]


def git_short_hash() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root())
        return (out.decode().strip() or "nogit")
    except Exception:
        return "nogit"


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def ensure_out_dir(label: str = "profile") -> Path:
    base = repo_root() / "output" / "tools" / "benchmarks"
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base / f"{stamp}__bench__{label}__{git_short_hash()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_target(modname: str):
    # Ensure repo root is on sys.path for module imports
    root = repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    mod = importlib.import_module(modname)
    main = getattr(mod, "main", None)
    if callable(main):
        return main
    # If no main(), return a thunk that imports the module (no-op)
    return lambda: None


def category_breakdown(stats: pstats.Stats, top_n: int = 0) -> Dict[str, float]:
    """Sum cumulative time by top-level category folders under src/rune_decrypter_prime/."""
    root = repo_root()
    src = (root / "src" / "rune_decrypter_prime").resolve()
    out: Dict[str, float] = {c: 0.0 for c in CATEGORIES}
    for (filename, _lineno, _funcname), (_cc, _nc, _tt, ct, _callers) in stats.stats.items():
        try:
            p = Path(filename).resolve()
        except Exception:
            continue
        try:
            rel = p.relative_to(src)
        except Exception:
            continue
        parts = rel.parts
        if not parts:
            continue
        cat = parts[0]
        if cat in out:
            out[cat] += float(ct)
    return out


def top_functions(stats: pstats.Stats, top_n: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    # stats.stats: {(filename, line, funcname): (cc, nc, tt, ct, callers)}
    # We sort by cumulative time (ct)
    items: List[Tuple[Tuple[str, int, str], Tuple[int, int, float, float, Any]]] = list(stats.stats.items())
    items.sort(key=lambda kv: kv[1][3], reverse=True)
    for (filename, line, funcname), (cc, nc, tt, ct, _callers) in items[:top_n]:
        rows.append({
            "file": str(Path(filename)),
            "line": int(line),
            "func": funcname,
            "calls_primitive": int(cc),
            "calls_total": int(nc),
            "time_total": round(float(tt), 6),
            "time_cum": round(float(ct), 6),
        })
    return rows


def write_one(run_dir: Path, target_name: str, pr: cProfile.Profile, top_n: int) -> None:
    safe = safe_name(target_name)
    raw = run_dir / f"{safe}__profile.prof"
    txt = run_dir / f"{safe}__profile.txt"
    jsn = run_dir / f"{safe}__profile.json"
    cat = run_dir / f"{safe}__categories.json"

    pr.dump_stats(str(raw))
    st = pstats.Stats(pr)
    st.strip_dirs()
    st.sort_stats("cumtime")
    s = io.StringIO()
    st.print_stats(top_n)
    txt.write_text(s.getvalue(), encoding="utf-8")
    # JSON top-N
    tops = top_functions(st, top_n)
    jsn.write_text(json.dumps(tops, indent=2), encoding="utf-8")
    # Categories
    cats = category_breakdown(st)
    cat.write_text(json.dumps(cats, indent=2), encoding="utf-8")


def profile_target(target: str, run_dir: Path, top_n: int) -> Dict[str, Any]:
    fn = load_target(target)
    pr = cProfile.Profile()
    status = "ok"
    err = ""
    try:
        pr.enable()
        fn()
        pr.disable()
    except Exception as ex:
        pr.disable()
        status = "error"
        err = f"{ex.__class__.__name__}: {ex}"
    write_one(run_dir, target, pr, top_n)
    total = sum(v[2] for v in pstats.Stats(pr).stats.values())  # sum tottime
    return {"name": target, "status": status, "prof_total_time_s": round(float(total), 6), "error": err}


def main() -> int:
    ap = argparse.ArgumentParser(description="Profile canonical tutorials and write cProfile reports under output/.")
    ap.add_argument("--target", default="all", help="'all' or dotted module path (e.g., tutorials.v1.Tutorial_MonoSubstitution_GA)")
    ap.add_argument("--top", type=int, default=30, help="Top-N functions by cumulative time to include in text/JSON summaries")
    args = ap.parse_args()

    run_dir = ensure_out_dir(label="profile")
    targets = CANONICAL_MODULES if args.target == "all" else [args.target]
    rows = [profile_target(t, run_dir, args.top) for t in targets]
    # Console table
    print("name,status,prof_total_time_s")
    for r in rows:
        print(f"{r['name']},{r['status']},{r['prof_total_time_s']}")
    # Summary JSON
    (run_dir / "profile_summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    try:
        rel = run_dir.relative_to(repo_root())
    except ValueError:
        rel = run_dir
    print(f"[profile-bench] Reports written to {rel}")
    failed = [r for r in rows if r["status"] != "ok"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
