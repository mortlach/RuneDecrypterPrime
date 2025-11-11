#!/usr/bin/env python3
"""Convenience runner that writes docs-lint reports into the canonical output tree."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_LINT_SCRIPT = REPO_ROOT / "tools" / "docs_lint" / "docs_lint.py"
SYMBOL_SCRIPT = REPO_ROOT / "tools" / "symbols" / "generate_symbol_index.py"
SYMBOL_OUTPUT = REPO_ROOT / "tools" / "out" / "project_symbol_index.txt"
OUTPUT_ROOT = REPO_ROOT / "output" / "tools" / "docs_lint"


def git_short_hash() -> str:
    try:
        result = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
        )
        value = result.decode().strip()
        return value or "nogit"
    except Exception:
        return "nogit"


def sanitize_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", label.strip())
    return cleaned or "manual"


def rel(path: Path) -> Path:
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run docs-lint with canonical output folders.")
    parser.add_argument(
        "--label",
        default="manual",
        help="Label inserted into the output folder name (default: manual).",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to launch docs_lint.py (default: current interpreter).",
    )
    parser.add_argument(
        "--docs-lint-script",
        default=str(DOCS_LINT_SCRIPT),
        help="Path to docs_lint.py (default: tools/docs_lint/docs_lint.py).",
    )
    parser.add_argument(
        "--symbol-script",
        default=str(SYMBOL_SCRIPT),
        help="Path to generate_symbol_index.py (default: tools/symbols/generate_symbol_index.py).",
    )
    parser.add_argument(
        "--no-refresh-symbols",
        dest="refresh_symbols",
        action="store_false",
        help="Skip regenerating the symbol index before running docs lint.",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=10,
        help=(
            "How many recent runs to keep under output/tools/docs_lint/ (default: 10). "
            "Older run folders are deleted after a successful run."
        ),
    )
    parser.set_defaults(refresh_symbols=True)
    args = parser.parse_args()

    git_hash = git_short_hash()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = sanitize_label(args.label or "manual")

    if args.refresh_symbols:
        SYMBOL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        symbol_cmd = [
            args.python,
            args.symbol_script,
            "--root",
            str(REPO_ROOT / "src" / "rune_decrypter_prime"),
        ]
        print(f"[docs-lint-runner] Refreshing symbol index -> {rel(SYMBOL_OUTPUT)}")
        with SYMBOL_OUTPUT.open("w", encoding="utf-8") as fh:
            result = subprocess.run(symbol_cmd, cwd=REPO_ROOT, stdout=fh, check=False)
        if result.returncode != 0:
            raise SystemExit(result.returncode)

    run_dir = OUTPUT_ROOT / f"{timestamp}__docs_lint__{label}__{git_hash}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Copy the symbol index into the run directory for reference.
    if SYMBOL_OUTPUT.exists():
        symbol_copy = run_dir / "project_symbol_index.txt"
        symbol_copy.write_text(SYMBOL_OUTPUT.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[docs-lint-runner] Copied symbol index -> {rel(symbol_copy)}")
        if args.refresh_symbols:
            try:
                SYMBOL_OUTPUT.unlink()
            except OSError:
                pass

    cmd = [args.python, args.docs_lint_script, "--out-dir", str(run_dir)]
    try:
        script_path = rel(Path(args.docs_lint_script))
    except Exception:
        script_path = args.docs_lint_script
    display_cmd = [args.python, str(script_path), "--out-dir", str(rel(run_dir))]
    print(f"[docs-lint-runner] Running: {' '.join(display_cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    print(f"[docs-lint-runner] Reports written to {rel(run_dir)}")

    # Cleanup: keep only the most recent N runs (by folder name which starts with timestamp)
    try:
        runs = [p for p in OUTPUT_ROOT.glob("*__docs_lint__*__*") if p.is_dir()]
        runs.sort(key=lambda p: p.name, reverse=True)
        for old in runs[args.keep:]:
            try:
                # Best-effort recursive delete
                for sub in sorted(old.rglob("*"), reverse=True):
                    if sub.is_file() or sub.is_symlink():
                        sub.unlink(missing_ok=True)
                for subdir in sorted([d for d in old.rglob("*") if d.is_dir()], reverse=True):
                    subdir.rmdir()
                old.rmdir()
                print(f"[docs-lint-runner] Pruned old run: {rel(old)}")
            except Exception:
                # Do not fail the run on cleanup issues
                pass
    except Exception:
        pass


if __name__ == "__main__":
    main()
