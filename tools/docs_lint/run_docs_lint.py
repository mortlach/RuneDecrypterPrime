#!/usr/bin/env python3
"""
Run a docs lint command, enforce output-path hygiene, and write a structured report.

Default behaviour:
- Execute command from repository root.
- Save reports under output/tools/docs_lint/<run_id>/.
- Fail if any created/modified file is outside output/.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EXCLUDE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[2]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _git_short(root: Path) -> str:
    dotgit = root / ".git"
    try:
        if dotgit.is_file():
            pointer = dotgit.read_text(encoding="utf-8").strip()
            if pointer.startswith("gitdir:"):
                dotgit = (root / pointer.split(":", 1)[1].strip()).resolve()
        head = dotgit / "HEAD"
        if not head.exists():
            return "nogit"
        head_text = head.read_text(encoding="utf-8").strip()
        if head_text.startswith("ref:"):
            ref_rel = head_text.split(" ", 1)[1].strip()
            ref_file = dotgit / ref_rel
            if ref_file.exists():
                return ref_file.read_text(encoding="utf-8").strip()[:7]
        return head_text[:7] if head_text else "nogit"
    except Exception:
        return "nogit"


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    snap: dict[str, tuple[int, int]] = {}
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            try:
                if not path.is_file():
                    continue
                rel = path.relative_to(root).as_posix()
                stat = path.stat()
                snap[rel] = (int(stat.st_mtime_ns), int(stat.st_size))
            except Exception:
                continue
    return snap


def _outside_output_changes(
    before: dict[str, tuple[int, int]],
    after: dict[str, tuple[int, int]],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for rel, meta in after.items():
        kind = ""
        if rel not in before:
            kind = "created"
        elif before[rel] != meta:
            kind = "modified"
        if not kind:
            continue
        if rel.startswith("output/"):
            continue
        issues.append({"kind": kind, "path": rel})
    return sorted(issues, key=lambda x: (x["path"], x["kind"]))


def _format_report_md(report: dict) -> str:
    lines = [
        "# Docs Lint Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Return code: `{report['returncode']}`",
        f"- Label: `{report['label']}`",
        f"- Run id: `{report['run_id']}`",
        f"- Started (UTC): `{report['started_utc']}`",
        f"- Finished (UTC): `{report['finished_utc']}`",
        f"- Duration (s): `{report['duration_s']:.3f}`",
        f"- Command: `{report['command_display']}`",
        "",
    ]
    if report["outside_output_changes"]:
        lines.append("## Files Written Outside output/")
        lines.append("")
        for item in report["outside_output_changes"]:
            lines.append(f"- `{item['kind']}`: `{item['path']}`")
        lines.append("")
    else:
        lines.extend(["## Files Written Outside output/", "", "- None", ""])
    lines.extend(
        [
            "## Logs",
            "",
            f"- Stdout: `{report['stdout_file']}`",
            f"- Stderr: `{report['stderr_file']}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run docs lint and keep reports under output/.")
    parser.add_argument("--label", default="manual", help="Short run label used in report folder name.")
    parser.add_argument(
        "--allow-outside-output",
        action="store_true",
        help="Do not fail when files are created/modified outside output/.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run (prefix with --).")
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("error: command is required (example: run_docs_lint.py -- python -m pytest tests/docs -q)")
        return 2

    root = _repo_root()
    run_id = f"{_now_utc().strftime('%Y%m%dT%H%M%SZ')}__docs_lint__{args.label}__{_git_short(root)}"
    out_dir = root / "output" / "tools" / "docs_lint" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    started = _now_utc()
    before = _snapshot(root)
    t0 = time.perf_counter()
    proc = subprocess.run(command, cwd=str(root), text=True, capture_output=True)
    duration = time.perf_counter() - t0
    after = _snapshot(root)
    finished = _now_utc()

    outside = _outside_output_changes(before, after)
    status = "pass"
    if proc.returncode != 0:
        status = "lint_failed"
    elif outside and not args.allow_outside_output:
        status = "output_guard_failed"

    stdout_path = out_dir / "stdout.txt"
    stderr_path = out_dir / "stderr.txt"
    stdout_path.write_text(proc.stdout or "", encoding="utf-8")
    stderr_path.write_text(proc.stderr or "", encoding="utf-8")

    report = {
        "status": status,
        "returncode": int(proc.returncode),
        "label": args.label,
        "run_id": run_id,
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "duration_s": float(duration),
        "command": command,
        "command_display": " ".join(shlex.quote(part) for part in command),
        "outside_output_changes": outside,
        "stdout_file": stdout_path.relative_to(root).as_posix(),
        "stderr_file": stderr_path.relative_to(root).as_posix(),
    }

    report_json = out_dir / "docs_lint_report.json"
    report_md = out_dir / "docs_lint_report.md"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md.write_text(_format_report_md(report), encoding="utf-8")

    print(f"[docs-lint] run_id={run_id}")
    print(f"[docs-lint] report={report_json.relative_to(root).as_posix()}")
    print(f"[docs-lint] status={status}")

    if status == "pass":
        return 0
    if status == "lint_failed":
        return int(proc.returncode) if proc.returncode else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
