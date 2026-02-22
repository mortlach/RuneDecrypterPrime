#!/usr/bin/env python3
"""
validate_outputs.py — Run a command and assert that all created/modified files
live under the repo's `output/` tree. Fails with a non-zero exit if any
new/changed file is detected outside `output/`.

Usage:
  python tools/benchmarks/repo_tools/ci/validate_outputs.py -- <command ...>

Notes:
  - Only checks new or modified regular files (not dirs) by mtime/size.
  - Excludes typical VCS/venv/caches.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, Tuple


EXCLUDE_DIRS = {".git", ".idea", ".vscode", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "venv", ".venv"}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]


def snapshot(root: Path) -> Dict[Path, Tuple[int, int]]:
    out: Dict[Path, Tuple[int, int]] = {}
    for p in root.rglob("*"):
        try:
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            st = p.stat()
            out[rel] = (int(st.st_mtime), int(st.st_size))
        except Exception:
            continue
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Assert commands write only under output/.")
    ap.add_argument("--", dest="dashdash", action="store_true", help="Separator before command.")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run (prefix with --).")
    args = ap.parse_args()

    if not args.cmd:
        print("usage: validate_outputs.py -- <command...>")
        sys.exit(2)

    repo = _repo_root()
    before = snapshot(repo)

    proc = subprocess.run(args.cmd, cwd=str(repo))
    if proc.returncode != 0:
        sys.exit(proc.returncode)

    after = snapshot(repo)

    offenders = []
    for rel, meta in after.items():
        if rel not in before:
            # newly created file
            if not rel.parts or rel.parts[0] != "output":
                offenders.append(("created", rel))
        else:
            if meta != before[rel]:
                if not rel.parts or rel.parts[0] != "output":
                    offenders.append(("modified", rel))

    if offenders:
        print("[validate-outputs] Found files outside output/:")
        for kind, rel in offenders:
            print(f"  - {kind}: {rel}")
        sys.exit(1)
    else:
        print("[validate-outputs] OK: all writes under output/")


if __name__ == "__main__":
    main()
