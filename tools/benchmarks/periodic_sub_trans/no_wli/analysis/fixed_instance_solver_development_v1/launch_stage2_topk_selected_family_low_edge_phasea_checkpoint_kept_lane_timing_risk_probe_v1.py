from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "launch_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1 as probe_mod,
)


RUNNER_PATH = (
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "run_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1.py"
)
WATCHDOG_INTERVAL_SECONDS = 60.0
EXPECTED_SECONDS = 1851.437
CAP_SECONDS = probe_mod.MAX_WALLCLOCK_SECONDS


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(round(float(seconds))))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _candidate_output_dirs(started_at: float) -> list[Path]:
    base_dir = probe_mod.live_mod.base_mod.replay_mod.OUTPUT_BASE_DIR
    candidates = [
        path
        for path in base_dir.glob(f"*__{probe_mod.RUN_LABEL}")
        if path.is_dir() and path.stat().st_mtime >= started_at - 5.0
    ]
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)


def _latest_state(started_at: float) -> tuple[Path | None, dict[str, Any]]:
    for output_dir in _candidate_output_dirs(started_at):
        state_path = output_dir / "matrix_run_state.json"
        state = _load_json(state_path)
        if state:
            return state_path, state
    return None, {}


def _stream_output(process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(line.rstrip(), flush=True)


def main() -> int:
    started_at = time.time()
    runner = REPO_ROOT / RUNNER_PATH
    print(
        "launch_started "
        f"label={probe_mod.RUN_LABEL} "
        f"runner={_relative_path(runner)} "
        f"expected_seconds={EXPECTED_SECONDS:.1f} "
        f"cap_seconds={CAP_SECONDS:.0f} "
        f"budget={_format_duration(CAP_SECONDS)}",
        flush=True,
    )
    process = subprocess.Popen(
        [sys.executable, str(runner)],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    stream_thread = threading.Thread(
        target=_stream_output,
        args=(process,),
        daemon=True,
    )
    stream_thread.start()

    while process.poll() is None:
        time.sleep(WATCHDOG_INTERVAL_SECONDS)
        elapsed = time.time() - started_at
        state_path, state = _latest_state(started_at)
        completed = int(state.get("completed_jobs") or 0)
        total = int(state.get("planned_jobs") or len(probe_mod.SEARCH_SEEDS))
        remaining_cap = max(0.0, CAP_SECONDS - elapsed)
        eta = max(0.0, EXPECTED_SECONDS - elapsed)
        state_relpath = _relative_path(state_path) if state_path else ""
        print(
            "watchdog_progress "
            f"completed={completed}/{total} "
            f"elapsed_seconds={elapsed:.0f} "
            f"eta_seconds={eta:.0f} "
            f"remaining_seconds={remaining_cap:.0f} "
            f"cap_seconds={CAP_SECONDS:.0f} "
            f"state_path={state_relpath}",
            flush=True,
        )

    stream_thread.join(timeout=10.0)
    elapsed = time.time() - started_at
    state_path, state = _latest_state(started_at)
    print(
        "launch_finished "
        f"exit_code={process.returncode} "
        f"elapsed_seconds={elapsed:.0f} "
        f"state_path={_relative_path(state_path) if state_path else ''} "
        f"recommendation={state.get('recommendation', {}).get('recommendation', '')}",
        flush=True,
    )
    return int(process.returncode or 0)


if __name__ == "__main__":
    raise SystemExit(main())
