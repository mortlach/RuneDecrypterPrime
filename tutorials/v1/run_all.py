from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Runner config (edit these in your IDE; no CLI args required)
# -----------------------------------------------------------------------------
SKIP_HARD = True
LIST_ONLY = False
STOP_ON_FIRST_FAILURE = False

# If INCLUDE is non-empty, only run the listed scripts (name or stem).
# Examples: "Tutorial_Autokey.py" or "Tutorial_Autokey"
INCLUDE: list[str] = []

# Always skip these scripts (name or stem), even if in INCLUDE.
EXCLUDE: list[str] = []


def _normalize_targets(targets: list[str]) -> set[str]:
    out: set[str] = set()
    for item in targets:
        name = item.strip()
        if not name:
            continue
        if name.endswith(".py"):
            out.add(name)
            out.add(name[:-3])
        else:
            out.add(name)
            out.add(f"{name}.py")
    return out


def _iter_scripts(base: Path) -> list[Path]:
    include = _normalize_targets(INCLUDE)
    exclude = _normalize_targets(EXCLUDE)
    scripts: list[Path] = []
    for path in sorted(base.glob("*.py")):
        name = path.name
        stem = path.stem
        if name in {"__init__.py", "run_all.py"}:
            continue
        if name.startswith("_"):
            continue
        if SKIP_HARD and name.endswith("_Hard.py"):
            continue
        if include and name not in include and stem not in include:
            continue
        if exclude and (name in exclude or stem in exclude):
            continue
        scripts.append(path)
    return scripts


def main() -> int:
    base = Path(__file__).resolve().parent
    scripts = _iter_scripts(base)
    if LIST_ONLY:
        for script in scripts:
            print(script.name)
        return 0

    repo_root = base.parents[2]
    env = os.environ.copy()
    src_path = repo_root / "src"
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{current}" if current else str(src_path)

    failures: list[str] = []
    for script in scripts:
        print(f"\n=== Running {script.name} ===")
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(repo_root),
            env=env,
        )
        if result.returncode != 0:
            failures.append(script.name)
            if STOP_ON_FIRST_FAILURE:
                break

    total = len(scripts)
    failed = len(failures)
    passed = total - failed
    print(f"\nSummary: total={total} passed={passed} failed={failed}")
    if SKIP_HARD:
        print("Note: SKIP_HARD=True (hard tutorials skipped).")

    if failures:
        print("\nFailures:")
        for name in failures:
            print(f"- {name}")
        return 1

    print("\nAll tutorials completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
