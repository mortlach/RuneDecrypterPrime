from __future__ import annotations

"""Run WP6 Experiment B10 and conditionally the overnight-scale B100 panel."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cipher_development.two_period_overlay.experiment_b import (
    B10_EXPERIMENT_ID,
    B100_EXPERIMENT_ID,
    run_candidate_word_branches,
)

RUN_B10 = True
RUN_B100_WHEN_B10_GATE_PASSES = True
TIMING_LOG_PREFIX = "PACK04_TIMING_JSON="


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_result(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("experiment result must contain a JSON object")
    return value


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    pack_started_at = _utc_now_iso()
    pack_started = time.perf_counter()
    results: dict[str, dict[str, object]] = {}

    if RUN_B10:
        started_at = _utc_now_iso()
        started = time.perf_counter()
        print(f"[Pack 04] START {B10_EXPERIMENT_ID} {started_at}", flush=True)
        result_path = run_candidate_word_branches(repo_root, list_size=10)
        elapsed = time.perf_counter() - started
        payload = _read_result(result_path)
        summary = payload.get("result_summary")
        if not isinstance(summary, dict):
            raise RuntimeError("B10 result summary is missing")
        print(
            f"[Pack 04] END {B10_EXPERIMENT_ID} {_utc_now_iso()} elapsed_s={elapsed:.6f}",
            flush=True,
        )
        results[B10_EXPERIMENT_ID] = {
            "result_path": str(result_path),
            "elapsed_s": elapsed,
            "decision": payload.get("decision"),
            "progression_gate_passed": summary.get("progression_gate_passed"),
        }

        if (
            RUN_B100_WHEN_B10_GATE_PASSES
            and summary.get("progression_gate_passed") is True
        ):
            started_at = _utc_now_iso()
            started = time.perf_counter()
            print(f"[Pack 04] START {B100_EXPERIMENT_ID} {started_at}", flush=True)
            b100_path = run_candidate_word_branches(repo_root, list_size=100)
            b100_elapsed = time.perf_counter() - started
            b100_payload = _read_result(b100_path)
            b100_summary = b100_payload.get("result_summary")
            if not isinstance(b100_summary, dict):
                raise RuntimeError("B100 result summary is missing")
            print(
                f"[Pack 04] END {B100_EXPERIMENT_ID} {_utc_now_iso()} "
                f"elapsed_s={b100_elapsed:.6f}",
                flush=True,
            )
            results[B100_EXPERIMENT_ID] = {
                "result_path": str(b100_path),
                "elapsed_s": b100_elapsed,
                "decision": b100_payload.get("decision"),
                "progression_gate_passed": b100_summary.get("progression_gate_passed"),
            }
        else:
            print(
                "[Pack 04] B100 not started because the predeclared B10 gate did not pass.",
                flush=True,
            )

    timing = {
        "schema": "rdp.wp6.pack04.execution_timing.v1",
        "started_at_utc": pack_started_at,
        "finished_at_utc": _utc_now_iso(),
        "elapsed_s": time.perf_counter() - pack_started,
        "experiments": results,
    }
    print(TIMING_LOG_PREFIX + json.dumps(timing, sort_keys=True), flush=True)
    print(json.dumps(results, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
