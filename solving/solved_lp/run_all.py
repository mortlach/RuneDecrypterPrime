from __future__ import annotations

"Run every solved LP workbook file and require solved evidence."
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKBOOK_ROOT = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 300
WORKBOOK_SOLVES = (
    "01_A_Warning.py",
    "02_Welcome_Pilgrim.py",
    "03_Some_Wisdom.py",
    "04_Koan_A_Man.py",
    "05_Loss_Of_Divinity.py",
    "06_Koan_During_Lesson.py",
    "07_Instruction.py",
    "08_An_End.py",
    "09_Parable.py",
)
_STATUS_RE = re.compile("^status:\\s*(?P<value>\\S+)\\s*$", re.MULTILINE)
_MATCH_RE = re.compile(
    "^match_ratio:\\s*(?P<value>[0-9]+(?:\\.[0-9]+)?)\\s*$", re.MULTILINE
)


@dataclass(frozen=True)
class WorkbookRun:
    script: str
    status: str
    match_ratio: float
    elapsed_s: float


def _tail(text: str, *, lines: int = 40) -> str:
    return "\n".join(text.splitlines()[-lines:])


def _parse_solved_evidence(script: str, output: str) -> WorkbookRun:
    statuses = [match.group("value") for match in _STATUS_RE.finditer(output)]
    ratios = [float(match.group("value")) for match in _MATCH_RE.finditer(output)]
    if not statuses:
        raise RuntimeError(f"{script} did not print a status field")
    if not ratios:
        raise RuntimeError(f"{script} did not print a match_ratio field")
    status = statuses[-1]
    ratio = ratios[-1]
    if status != "solved" or ratio < 1.0:
        raise RuntimeError(
            f"{script} did not solve: status={status!r} match_ratio={ratio:.3f}"
        )
    return WorkbookRun(script=script, status=status, match_ratio=ratio, elapsed_s=0.0)


def run_workbook_script(script: str) -> WorkbookRun:
    script_path = WORKBOOK_ROOT / script
    if not script_path.is_file():
        raise FileNotFoundError(f"Missing workbook script: {script}")
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", str(script_path)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    elapsed_s = time.perf_counter() - started
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        raise RuntimeError(
            f"{script} exited with {completed.returncode}\n--- output tail ---\n{_tail(output)}"
        )
    result = _parse_solved_evidence(script, output)
    return WorkbookRun(
        script=result.script,
        status=result.status,
        match_ratio=result.match_ratio,
        elapsed_s=elapsed_s,
    )


def main() -> int:
    print("LP_WORKBOOK_RUN_ALL_BEGIN")
    passed: list[WorkbookRun] = []
    for script in WORKBOOK_SOLVES:
        result = run_workbook_script(script)
        passed.append(result)
        print(
            f"{script}: status={result.status} match_ratio={result.match_ratio:.3f} elapsed_s={result.elapsed_s:.3f}"
        )
    print(f"solves_passed: {len(passed)}")
    print("LP_WORKBOOK_RUN_ALL_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
