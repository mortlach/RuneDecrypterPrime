from __future__ import annotations

"""
Report-only PhaseA14 span-Hamming data-taking queue.

Run this from the IDE when you have a long unattended window. It launches each
scan in a fresh Python process so mutable module-level scan settings cannot leak
between runs. No CLI arguments and no scorer/default behaviour changes.
"""

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root from queue script path")


REPO_ROOT = _find_repo_root()
ANALYSIS_DIR = REPO_ROOT / "tools/benchmarks/periodic_sub_trans/no_wli/analysis"
QUEUE_LABEL = "phaseA14_span_hamming_8hour_data_queue_v1"
QUEUE_OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / QUEUE_LABEL
CONTINUE_AFTER_FAILURE = False


@dataclass(frozen=True)
class QueueRun:
    run_id: str
    script_name: str
    purpose: str


QUEUE_RUNS: tuple[QueueRun, ...] = (
    QueueRun(
        run_id="long_norm500_reference",
        script_name="scan_phaseA_v0_14_span_hamming_500_exact_hd_long_ladder_full_v1.py",
        purpose="Reference PhaseA14 strict+normal lengths 5..14 exact-HD run at chunk length 500.",
    ),
    QueueRun(
        run_id="long_norm250_stability",
        script_name="scan_phaseA_v0_14_span_hamming_250_exact_hd_long_ladder_full_v1.py",
        purpose="Chunk-length stability check at 250 tokens.",
    ),
    QueueRun(
        run_id="long_norm750_stability",
        script_name="scan_phaseA_v0_14_span_hamming_750_exact_hd_long_ladder_full_v1.py",
        purpose="Chunk-length stability check at 750 tokens.",
    ),
    QueueRun(
        run_id="long_norm1000_stability",
        script_name="scan_phaseA_v0_14_span_hamming_1000_exact_hd_long_ladder_full_v1.py",
        purpose="Chunk-length stability check at 1000 tokens, if candidates are long enough.",
    ),
    QueueRun(
        run_id="normal_focus_norm500",
        script_name="scan_phaseA_v0_14_span_hamming_500_exact_hd_normal_focus_v1.py",
        purpose="PhaseA14 normal-only focused lengths 5..10 run around the current strongest damaged-language family.",
    ),
    QueueRun(
        run_id="strict_keep_gate_norm500",
        script_name="scan_phaseA_v0_14_span_hamming_500_exact_hd_strict_keep_gate_v1.py",
        purpose="PhaseA14 strict-only long-word HD0..2 keep-gate probe for rare high-confidence evidence.",
    ),
    QueueRun(
        run_id="all_lengths_norm500_reference",
        script_name="scan_phaseA_v0_14_span_hamming_500_exact_hd_all_ladder_full_v1.py",
        purpose="Completeness reference including lengths 1..14; inspect carefully because short Hamming features can be noisy.",
    ),
)


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    QUEUE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    state_path = QUEUE_OUTPUT_DIR / "phaseA14_span_hamming_8hour_data_queue_state.json"
    manifest_path = QUEUE_OUTPUT_DIR / "phaseA14_span_hamming_8hour_data_queue_manifest.json"
    log_dir = QUEUE_OUTPUT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "queue_label": QUEUE_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "continue_after_failure": CONTINUE_AFTER_FAILURE,
        "runs": [asdict(run) for run in QUEUE_RUNS],
        "caveats": [
            "report-only; no runtime solver behaviour changed",
            "each scan is launched in a fresh Python process",
            "uses PhaseA14 strict/normal staged assets only",
            "cap=100000 is intended as effectively uncapped; check cap-prune columns in each result",
            "all_lengths run includes short-word features and must not be treated as rank-gate evidence without review",
        ],
    }
    _write_json(manifest_path, manifest)

    completed: list[dict[str, object]] = []
    for idx, run in enumerate(QUEUE_RUNS, start=1):
        script_path = ANALYSIS_DIR / run.script_name
        entry = {
            "run_id": run.run_id,
            "script": _repo_rel(script_path),
            "purpose": run.purpose,
            "status": "running",
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "index": idx,
            "total": len(QUEUE_RUNS),
        }
        completed.append(entry)
        _write_json(
            state_path,
            {
                "queue_label": QUEUE_LABEL,
                "status": "running",
                "completed_runs": completed,
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        if not script_path.exists():
            entry["status"] = "missing_script"
            entry["finished_utc"] = datetime.now(timezone.utc).isoformat()
            _write_json(state_path, {"queue_label": QUEUE_LABEL, "status": "failed", "completed_runs": completed})
            raise FileNotFoundError(f"Missing queued scan script: {script_path}")

        print(f"[phaseA14_queue] starting {idx}/{len(QUEUE_RUNS)} {run.run_id}: {script_path.name}", flush=True)
        run_started = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        elapsed = time.perf_counter() - run_started
        log_path = log_dir / f"{idx:02d}_{run.run_id}.log"
        log_path.write_text(proc.stdout or "", encoding="utf-8")
        entry["returncode"] = int(proc.returncode)
        entry["elapsed_seconds"] = elapsed
        entry["log_path"] = _repo_rel(log_path)
        entry["finished_utc"] = datetime.now(timezone.utc).isoformat()
        entry["status"] = "complete" if proc.returncode == 0 else "failed"
        print(
            f"[phaseA14_queue] finished {run.run_id} status={entry['status']} "
            f"returncode={proc.returncode} elapsed={elapsed:.1f}s log={_repo_rel(log_path)}",
            flush=True,
        )
        _write_json(
            state_path,
            {
                "queue_label": QUEUE_LABEL,
                "status": "running" if proc.returncode == 0 else "failed",
                "completed_runs": completed,
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        if proc.returncode != 0 and not CONTINUE_AFTER_FAILURE:
            raise RuntimeError(f"Queued scan failed: {run.run_id}; see {_repo_rel(log_path)}")

    final_state = {
        "queue_label": QUEUE_LABEL,
        "status": "complete",
        "completed_runs": completed,
        "elapsed_seconds": time.perf_counter() - started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(state_path, final_state)
    print(f"[phaseA14_queue] complete elapsed={final_state['elapsed_seconds']:.1f}s", flush=True)


if __name__ == "__main__":
    main()
