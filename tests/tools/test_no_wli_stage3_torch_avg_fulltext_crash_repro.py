from __future__ import annotations

import py_compile
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.tier_a

# Manual gate: keep this False for normal test runs.
# Set to True only when you intentionally want to execute the crash repro.
RUN_CRASH_REPRO = False

# Windows access-violation exit code seen in this repo's crash logs.
ACCESS_VIOLATION_RETURN_CODES = {-1073741819, 3221225477}
REPRO_TIMEOUT_SECONDS = 1800


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repro_script() -> Path:
    return _repo_root() / "tools/benchmarks/periodic_sub_trans/no_wli/repro_stage3_torch_avg_fulltext_access_violation.py"


def test_repro_script_exists_and_compiles():
    script = _repro_script()
    assert script.exists(), f"missing repro script: {script}"
    py_compile.compile(str(script), doraise=True)


@pytest.mark.skipif(not RUN_CRASH_REPRO, reason="manual crash repro disabled by default")
def test_repro_script_hits_native_access_violation():
    script = _repro_script()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(_repo_root()),
        capture_output=True,
        text=True,
        timeout=int(REPRO_TIMEOUT_SECONDS),
    )
    if proc.returncode not in ACCESS_VIOLATION_RETURN_CODES:
        details = (
            "repro did not hit expected access-violation.\n"
            f"returncode={proc.returncode}\n"
            f"stdout_tail={proc.stdout[-1000:]}\n"
            f"stderr_tail={proc.stderr[-1000:]}"
        )
        pytest.fail(details)

