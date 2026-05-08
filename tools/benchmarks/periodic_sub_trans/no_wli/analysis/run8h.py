from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


RUN_LABEL = "phaseA14_8h_heavy_queue_v1"
TARGET_SECONDS = 8 * 60 * 60

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[4]

QUEUE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / RUN_LABEL
)
LOG_DIR = QUEUE_DIR / "logs"
QUEUE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Job:
    name: str
    script: str


# These scripts should already exist from the v5 patch.
# The queue repeats useful families at many chunk sizes.
JOBS = [
    Job("both_long_norm250", "scan_phaseA_v0_14_span_hamming_250_exact_hd_long_ladder_full_v1.py"),
    Job("both_long_norm500", "scan_phaseA_v0_14_span_hamming_500_exact_hd_long_ladder_full_v1.py"),
    Job("both_long_norm750", "scan_phaseA_v0_14_span_hamming_750_exact_hd_long_ladder_full_v1.py"),
    Job("both_long_norm1000", "scan_phaseA_v0_14_span_hamming_1000_exact_hd_long_ladder_full_v1.py"),

    Job("normal_focus_norm250", "scan_phaseA_v0_14_span_hamming_250_exact_hd_normal_focus_v1.py"),
    Job("normal_focus_norm500", "scan_phaseA_v0_14_span_hamming_500_exact_hd_normal_focus_v1.py"),
    Job("normal_focus_norm750", "scan_phaseA_v0_14_span_hamming_750_exact_hd_normal_focus_v1.py"),
    Job("normal_focus_norm1000", "scan_phaseA_v0_14_span_hamming_1000_exact_hd_normal_focus_v1.py"),

    Job("strict_keep_norm250", "scan_phaseA_v0_14_span_hamming_250_exact_hd_strict_keep_gate_v1.py"),
    Job("strict_keep_norm500", "scan_phaseA_v0_14_span_hamming_500_exact_hd_strict_keep_gate_v1.py"),
    Job("strict_keep_norm750", "scan_phaseA_v0_14_span_hamming_750_exact_hd_strict_keep_gate_v1.py"),
    Job("strict_keep_norm1000", "scan_phaseA_v0_14_span_hamming_1000_exact_hd_strict_keep_gate_v1.py"),

    Job("all_lengths_norm500", "scan_phaseA_v0_14_span_hamming_500_exact_hd_all_ladder_full_v1.py"),
    Job("all_lengths_norm1000", "scan_phaseA_v0_14_span_hamming_1000_exact_hd_all_ladder_full_v1.py"),
]


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_job(job: Job, index: int, cycle: int) -> dict:
    script_path = THIS_DIR / job.script
    log_path = LOG_DIR / f"cycle{cycle:03d}_{index:02d}_{job.name}.log"

    record = {
        "cycle": cycle,
        "index": index,
        "name": job.name,
        "script": job.script,
        "script_path": str(script_path),
        "log_path": str(log_path),
        "status": "pending",
        "returncode": None,
        "elapsed_seconds": None,
    }

    if not script_path.exists():
        record["status"] = "missing_script"
        log_path.write_text(f"Missing script: {script_path}\n", encoding="utf-8")
        return record

    start = time.perf_counter()
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"[run8h] starting {job.name}\n")
        log.write(f"[run8h] script {script_path}\n")
        log.flush()

        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(REPO_ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )

        elapsed = time.perf_counter() - start
        log.write(f"\n[run8h] finished returncode={proc.returncode} elapsed={elapsed:.1f}s\n")

    record["returncode"] = proc.returncode
    record["elapsed_seconds"] = round(elapsed, 3)
    record["status"] = "complete" if proc.returncode == 0 else "failed"
    return record


def main() -> None:
    start = time.perf_counter()
    records: list[dict] = []
    cycle = 1

    manifest = {
        "run_label": RUN_LABEL,
        "target_seconds": TARGET_SECONDS,
        "queue_dir": str(QUEUE_DIR),
        "log_dir": str(LOG_DIR),
        "jobs": [asdict(job) for job in JOBS],
        "started_unix": time.time(),
    }
    write_json(QUEUE_DIR / "queue_manifest.json", manifest)

    print(f"[run8h] queue dir: {QUEUE_DIR}")
    print(f"[run8h] jobs per cycle: {len(JOBS)}")
    print(f"[run8h] target seconds: {TARGET_SECONDS}")

    while True:
        elapsed_total = time.perf_counter() - start
        if elapsed_total >= TARGET_SECONDS:
            print("[run8h] target window reached; stopping")
            break

        print(f"[run8h] starting cycle {cycle}")
        for index, job in enumerate(JOBS, start=1):
            elapsed_total = time.perf_counter() - start
            if elapsed_total >= TARGET_SECONDS:
                print("[run8h] target window reached mid-cycle; stopping")
                break

            print(f"[run8h] cycle {cycle} job {index}/{len(JOBS)}: {job.name}")
            record = run_job(job, index=index, cycle=cycle)
            records.append(record)
            print(
                f"[run8h] {record['status']} {job.name} "
                f"returncode={record['returncode']} elapsed={record['elapsed_seconds']}s"
            )

            write_json(QUEUE_DIR / "queue_state.json", {
                "run_label": RUN_LABEL,
                "elapsed_seconds": round(time.perf_counter() - start, 3),
                "completed_records": records,
            })

        cycle += 1

    summary = {
        "run_label": RUN_LABEL,
        "elapsed_seconds": round(time.perf_counter() - start, 3),
        "records": records,
        "complete_count": sum(1 for r in records if r["status"] == "complete"),
        "failed_count": sum(1 for r in records if r["status"] == "failed"),
        "missing_script_count": sum(1 for r in records if r["status"] == "missing_script"),
    }
    write_json(QUEUE_DIR / "queue_final_summary.json", summary)
    print(f"[run8h] final summary: {QUEUE_DIR / 'queue_final_summary.json'}")


if __name__ == "__main__":
    main()