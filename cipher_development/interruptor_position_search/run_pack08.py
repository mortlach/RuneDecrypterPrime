from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cipher_development.interruptor_position_search.benchmark import build_benchmark
from cipher_development.interruptor_position_search.config import (
    MAX_INTERRUPT_COUNT,
    MIN_INTERRUPT_COUNT,
    SCIENCE_BLOCK_IDS,
    SCIENCE_SEEDS,
    SciencePlan,
)
from cipher_development.interruptor_position_search.experiment import (
    RunSummary,
    run_exact_control,
    run_joint_canary,
    run_key_control,
    run_position_control,
    run_science_block,
    terminal_metrics,
    write_json,
)

RUN_ID = "interruptor_joint_science_v1_20260727_063208"
OUTPUT_ROOT = (
    REPO_ROOT.parents[1]
    / "run_outputs"
    / "cipher_development"
    / "interruptor_position_search"
)
RUN_ROOT = OUTPUT_ROOT / RUN_ID
RUN_CONTROLS = True
RUN_CANARY = True
RUN_SCIENCE = True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(name: str, **payload) -> None:
    print(
        f"[{_now()}] {name}: {json.dumps(payload, sort_keys=True)}",
        flush=True,
    )


def _summary_without_evidence(summary: RunSummary) -> dict:
    payload = summary.public_dict()
    payload.pop("evidence", None)
    return payload


def _summary_from_payload(payload: dict) -> RunSummary:
    restored = dict(payload)
    for name in ("found_key", "found_positions", "plaintext"):
        restored[name] = tuple(int(value) for value in restored.get(name, ()))
    restored.setdefault("evidence", None)
    return RunSummary(**restored)


def _load_summary(path: Path) -> RunSummary | None:
    if not path.is_file():
        return None
    return _summary_from_payload(json.loads(path.read_text(encoding="utf-8")))


def _control_ok(benchmark, result: RunSummary) -> bool:
    return bool(terminal_metrics(benchmark, result)["exact"])


def _persist_position_control(result: RunSummary) -> None:
    root = RUN_ROOT / "controls" / "position_only"
    evidence = result.evidence or {}
    write_json(root / "raw_result.json", _summary_without_evidence(result))
    for key, filename in (
        ("public_context", "public_context.json"),
        ("evaluator_context", "evaluator_context.json"),
        ("search_config", "search_config.json"),
        ("beam_trace", "beam_trace.json"),
        ("best_candidate", "best_candidate.json"),
        ("score_ledger_digest", "score_ledger_digest.json"),
    ):
        write_json(root / filename, evidence.get(key))


def _run_controls(benchmark) -> dict[str, RunSummary]:
    root = RUN_ROOT / "controls"
    completed: dict[str, RunSummary] = {}
    paths = {
        "exact_mechanics": root / "exact_mechanics" / "raw_result.json",
        "position_only": root / "position_only" / "raw_result.json",
        "key_only": root / "key_only" / "raw_result.json",
    }
    for label, path in paths.items():
        loaded = _load_summary(path)
        if loaded is not None:
            completed[label] = loaded
            _event("control_reused", label=label, path=path.relative_to(RUN_ROOT).as_posix())

    if "exact_mechanics" not in completed:
        _event("control_started", label="exact_mechanics")
        result = run_exact_control(benchmark)
        write_json(paths["exact_mechanics"], _summary_without_evidence(result))
        completed["exact_mechanics"] = result
        _event("control_completed", label="exact_mechanics", elapsed_s=result.elapsed_s)

    if "position_only" not in completed:
        _event("control_started", label="position_only")
        result = run_position_control(benchmark)
        _persist_position_control(result)
        completed["position_only"] = result
        _event(
            "control_completed",
            label="position_only",
            elapsed_s=result.elapsed_s,
            evaluations=result.evals,
        )

    if "key_only" not in completed:
        _event("control_started", label="key_only")
        result = run_key_control(benchmark)
        write_json(paths["key_only"], _summary_without_evidence(result))
        completed["key_only"] = result
        _event(
            "control_completed",
            label="key_only",
            elapsed_s=result.elapsed_s,
            evaluations=result.evals,
        )

    metrics = {
        label: terminal_metrics(benchmark, result)
        for label, result in completed.items()
    }
    write_json(root / "terminal_evaluation.json", metrics)
    if not all(_control_ok(benchmark, result) for result in completed.values()):
        raise RuntimeError("required control failed")
    return completed


def _run_canary(benchmark) -> RunSummary:
    root = RUN_ROOT / "joint_canary"
    path = root / "raw_result.json"
    existing = _load_summary(path)
    if existing is not None:
        _event("canary_reused", path=path.relative_to(RUN_ROOT).as_posix())
        return existing
    _event("canary_started")
    result = run_joint_canary(benchmark)
    write_json(path, _summary_without_evidence(result))
    write_json(root / "terminal_evaluation.json", terminal_metrics(benchmark, result))
    _event(
        "canary_completed",
        elapsed_s=result.elapsed_s,
        evaluations=result.evals,
        stop_reason=result.stop_reason,
    )
    return result


def _run_science(benchmark) -> list[RunSummary]:
    plan = SciencePlan()
    science_started = time.monotonic()
    results: list[RunSummary] = []
    first_path = RUN_ROOT / "science" / f"block_{SCIENCE_BLOCK_IDS[0]}" / "raw_result.json"
    first = _load_summary(first_path)
    if first is None:
        block_root = first_path.parent
        write_json(
            block_root / "block_started.json",
            {
                "block_id": SCIENCE_BLOCK_IDS[0],
                "seed": SCIENCE_SEEDS[0],
                "started_utc": _now(),
                "configuration_fingerprint": RUN_ID,
            },
        )
        _event("science_block_started", block_id=SCIENCE_BLOCK_IDS[0])
        first = run_science_block(
            benchmark,
            block_id=SCIENCE_BLOCK_IDS[0],
            seed=SCIENCE_SEEDS[0],
        )
        write_json(first_path, _summary_without_evidence(first))
        write_json(
            block_root / "block_completed.json",
            {
                "block_id": SCIENCE_BLOCK_IDS[0],
                "completed_utc": _now(),
                "elapsed_s": first.elapsed_s,
                "evaluations": first.evals,
                "stop_reason": first.stop_reason,
            },
        )
        _event(
            "science_block_completed",
            block_id=SCIENCE_BLOCK_IDS[0],
            elapsed_s=first.elapsed_s,
            evaluations=first.evals,
        )
    else:
        _event("science_block_reused", block_id=SCIENCE_BLOCK_IDS[0])
    results.append(first)

    gate_path = RUN_ROOT / "runtime_gate.json"
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    else:
        elapsed = time.monotonic() - science_started
        projected_each = first.elapsed_s * plan.safety_factor
        available = plan.global_target_s - plan.reserve_s - elapsed
        remaining_authorized = min(
            len(SCIENCE_BLOCK_IDS) - 1,
            max(0, int(math.floor(available / projected_each)))
            if projected_each > 0
            else 0,
        )
        gate = {
            "first_block_elapsed_s": first.elapsed_s,
            "safety_factor": plan.safety_factor,
            "projected_each_s": projected_each,
            "available_s": available,
            "remaining_blocks_authorized": remaining_authorized,
            "truth_fields_used": [],
        }
        write_json(gate_path, gate)
    _event("runtime_gate", **gate)

    remaining = int(gate["remaining_blocks_authorized"])
    for block_id, seed in zip(
        SCIENCE_BLOCK_IDS[1 : 1 + remaining],
        SCIENCE_SEEDS[1 : 1 + remaining],
    ):
        block_root = RUN_ROOT / "science" / f"block_{block_id}"
        path = block_root / "raw_result.json"
        result = _load_summary(path)
        if result is None:
            write_json(
                block_root / "block_started.json",
                {
                    "block_id": block_id,
                    "seed": seed,
                    "started_utc": _now(),
                    "configuration_fingerprint": RUN_ID,
                },
            )
            _event("science_block_started", block_id=block_id)
            result = run_science_block(benchmark, block_id=block_id, seed=seed)
            write_json(path, _summary_without_evidence(result))
            write_json(
                block_root / "block_completed.json",
                {
                    "block_id": block_id,
                    "completed_utc": _now(),
                    "elapsed_s": result.elapsed_s,
                    "evaluations": result.evals,
                    "stop_reason": result.stop_reason,
                },
            )
            _event(
                "science_block_completed",
                block_id=block_id,
                elapsed_s=result.elapsed_s,
                evaluations=result.evals,
            )
        else:
            _event("science_block_reused", block_id=block_id)
        results.append(result)
    return results


def main() -> int:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    benchmark = build_benchmark()
    write_json(RUN_ROOT / "benchmark_public_context.json", benchmark.public_context())
    write_json(
        RUN_ROOT / "contract_preflight.json",
        {
            "run_id": RUN_ID,
            "created_utc": _now(),
            "repo_root": REPO_ROOT.name,
            "python": sys.version,
            "count_range": [MIN_INTERRUPT_COUNT, MAX_INTERRUPT_COUNT],
            "pool_size": len(benchmark.pool),
            "science_blocks": list(SCIENCE_BLOCK_IDS),
            "science_seeds": list(SCIENCE_SEEDS),
            "terminal_truth_opened": False,
        },
    )
    write_json(
        RUN_ROOT / "runner_status.json",
        {"status": "running", "phase": "controls", "updated_utc": _now()},
    )
    _event("pack08_started", run_id=RUN_ID, output_root=str(RUN_ROOT))

    try:
        if RUN_CONTROLS:
            _run_controls(benchmark)
        write_json(
            RUN_ROOT / "runner_status.json",
            {"status": "running", "phase": "canary", "updated_utc": _now()},
        )
        if RUN_CANARY:
            _run_canary(benchmark)

        write_json(
            RUN_ROOT / "runner_status.json",
            {"status": "running", "phase": "science", "updated_utc": _now()},
        )
        science_results = _run_science(benchmark) if RUN_SCIENCE else []

        # Terminal truth opens only after all authorised search blocks return.
        terminal = [terminal_metrics(benchmark, item) for item in science_results]
        exact_count = sum(bool(item["exact"]) for item in terminal)
        strong_count = sum(
            item["plaintext_match_ratio"] >= 0.99 and item["position_f1"] >= 0.8
            for item in terminal
        )
        if len(terminal) >= 2 and exact_count >= 2:
            decision = "promote"
        elif exact_count == 1 or strong_count >= 2:
            decision = "refine"
        elif len(terminal) >= 2:
            decision = "close"
        else:
            decision = "incomplete"
        write_json(
            RUN_ROOT / "terminal_evaluation.json",
            {
                "science_blocks_completed": len(terminal),
                "exact_blocks": exact_count,
                "strong_blocks": strong_count,
                "decision": decision,
                "blocks": terminal,
                "terminal_truth_opened_after_search": True,
            },
        )
        write_json(
            RUN_ROOT / "runner_status.json",
            {
                "status": "complete",
                "decision": decision,
                "science_blocks_completed": len(terminal),
                "updated_utc": _now(),
            },
        )
        _event(
            "pack08_completed",
            decision=decision,
            science_blocks_completed=len(terminal),
        )
        return 0
    except BaseException as exc:
        write_json(
            RUN_ROOT / "runner_status.json",
            {
                "status": "failed",
                "phase": "execution",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "updated_utc": _now(),
            },
        )
        _event("pack08_failed", error_type=type(exc).__name__, error=str(exc))
        raise


if __name__ == "__main__":
    raise SystemExit(main())
