from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from rune_decrypter_prime.api import (
    Direction,
    InterruptorConfig,
    KeySpec,
    SolverSpec,
    by_name,
    run,
)

from .benchmark import InterruptorBenchmark
from .fixed_core_position_evaluator import build_fixed_core_position_evaluator
from .fixed_core_position_search import search_fixed_core_positions
from .config import (
    CANARY_BEAM_WIDTH,
    CANARY_SEED,
    CONTROL_BEAM_WIDTH,
    CONTROL_PLATEAU_ROUNDS,
    CONTROL_SEED,
    DIRECTION,
    EXPAND_MODE,
    MAX_INTERRUPT_COUNT,
    MIN_INTERRUPT_COUNT,
    PLATEAU_MIN_DELTA,
    SCIENCE_BEAM_WIDTH,
    SCIENCE_PLATEAU_ROUNDS,
    SCORER_PARAMS,
)


@dataclass(frozen=True, slots=True)
class RunSummary:
    label: str
    seed: int
    elapsed_s: float
    score: float
    stop_reason: str | None
    evals: int
    found_key: tuple[int, ...]
    found_positions: tuple[int, ...]
    plaintext: tuple[int, ...]
    evidence: dict[str, Any] | None = None

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


def _solver(*, seed: int, beam_width: int, plateau_rounds: int, test_key=None):
    kwargs = {
        "beam_width": beam_width,
        "expand_mode": EXPAND_MODE,
        "plateau_rounds": plateau_rounds,
        "plateau_min_delta": PLATEAU_MIN_DELTA,
        "progress_pct": 2,
        "print_progress": True,
        "progress_preview_chars": 120,
        "seed": seed,
    }
    if test_key is not None:
        kwargs["test_key"] = list(test_key)
    return SolverSpec.beam(**kwargs)


def _pool_config(benchmark: InterruptorBenchmark) -> InterruptorConfig:
    return InterruptorConfig(
        mode="pool",
        pool=list(benchmark.pool),
        min_count=MIN_INTERRUPT_COUNT,
        max_count=MAX_INTERRUPT_COUNT,
        search_strategy="auto",
    )


def _execute(
    benchmark: InterruptorBenchmark,
    *,
    label: str,
    seed: int,
    interruptors=None,
    interruptors_exact=None,
    test_key=None,
    beam_width: int,
    plateau_rounds: int,
) -> RunSummary:
    started = time.monotonic()
    result = run(
        text=list(benchmark.ciphertext),
        cipher=by_name.cipher("vigenere"),
        key=KeySpec.repeat(len=len(benchmark.key)),
        solver=_solver(
            seed=seed,
            beam_width=beam_width,
            plateau_rounds=plateau_rounds,
            test_key=test_key,
        ),
        scorer_params=dict(SCORER_PARAMS),
        wli_data=[list(pair) for pair in benchmark.wli],
        encoding_dir=Direction(DIRECTION),
        telemetry_on=True,
        interruptors=interruptors,
        interruptors_exact=interruptors_exact,
        return_solver_report=True,
    )
    elapsed = time.monotonic() - started
    solution = result.solution
    raw_key = tuple(int(v) for v in (getattr(solution, "key", []) or []))
    key_len = len(benchmark.key)
    found_key = raw_key[:key_len]
    found_positions = tuple(sorted(int(v) for v in raw_key[key_len:] if int(v) >= 0))
    if interruptors_exact is not None and not found_positions:
        # Exact-mode positions are configuration, not searched composite-key state.
        found_positions = tuple(sorted(int(v) for v in interruptors_exact))
    plaintext = tuple(int(v) for v in getattr(solution, "plaintext_idx", []) or [])
    meta = getattr(solution, "meta", {}) or {}
    work = meta.get("work", {}) if isinstance(meta, dict) else {}
    telemetry = meta.get("telemetry", {}) if isinstance(meta, dict) else {}
    run_meta = telemetry.get("run", {}) if isinstance(telemetry, dict) else {}
    result_meta = run_meta.get("result", {}) if isinstance(run_meta, dict) else {}
    stop_reason = getattr(solution, "stop_reason", None)
    if stop_reason is None and isinstance(result_meta, dict):
        stop_reason = result_meta.get("reason")
    evals = int(getattr(solution, "evals", 0) or 0)
    if not evals and isinstance(work, dict):
        evals = int(work.get("evals", 0) or 0)
    return RunSummary(
        label=label,
        seed=seed,
        elapsed_s=float(elapsed),
        score=float(getattr(solution, "score", float("nan"))),
        stop_reason=stop_reason,
        evals=evals,
        found_key=found_key,
        found_positions=found_positions,
        plaintext=plaintext,
    )


def run_exact_control(benchmark: InterruptorBenchmark) -> RunSummary:
    return _execute(
        benchmark,
        label="exact_mechanics",
        seed=CONTROL_SEED,
        interruptors_exact=list(benchmark.true_positions),
        test_key=benchmark.key,
        beam_width=1,
        plateau_rounds=1,
    )


def run_position_control(benchmark: InterruptorBenchmark) -> RunSummary:
    started = time.monotonic()
    evaluator = build_fixed_core_position_evaluator(benchmark)
    outcome = search_fixed_core_positions(
        pool=benchmark.pool,
        min_count=MIN_INTERRUPT_COUNT,
        max_count=MAX_INTERRUPT_COUNT,
        evaluate_subsets=evaluator.score_subsets,
        beam_width=512,
        maximum_rounds=24,
        plateau_rounds=8,
        minimum_delta=PLATEAU_MIN_DELTA,
        evaluation_batch_size=2048,
    )
    best = outcome.best.positions
    plaintext = evaluator.resolve_plaintext(best)
    context = evaluator.context()
    candidate_payload = (
        repr(benchmark.public_context()) + "|" + repr(best)
    ).encode("utf-8")
    ledger_lines = [
        f"{','.join(str(value) for value in subset)}|{score:.17g}"
        for subset, score in sorted(
            evaluator.score_ledger.items(),
            key=lambda item: (len(item[0]), item[0]),
        )
    ]
    evidence = {
        "public_context": benchmark.public_context(),
        "evaluator_context": context,
        "search_config": {
            "beam_width": 512,
            "maximum_rounds": 24,
            "plateau_rounds": 8,
            "minimum_delta": PLATEAU_MIN_DELTA,
            "evaluation_batch_size": 2048,
            "min_count": MIN_INTERRUPT_COUNT,
            "max_count": MAX_INTERRUPT_COUNT,
        },
        "beam_trace": [asdict(item) for item in outcome.rounds],
        "best_candidate": {
            "candidate_id": hashlib.sha256(candidate_payload).hexdigest(),
            "positions": list(best),
            "score": outcome.best.score,
        },
        "score_ledger_digest": {
            "algorithm": "sha256",
            "canonical_row_format": "comma-separated-positions|score-.17g",
            "row_count": len(ledger_lines),
            "sha256": hashlib.sha256(
                ("\n".join(ledger_lines) + "\n").encode("ascii")
            ).hexdigest(),
        },
    }
    return RunSummary(
        label="position_only",
        seed=CONTROL_SEED + 1,
        elapsed_s=float(time.monotonic() - started),
        score=float(outcome.best.score),
        stop_reason=outcome.stopped_reason,
        evals=outcome.evaluations,
        found_key=benchmark.key,
        found_positions=best,
        plaintext=plaintext,
        evidence=evidence,
    )


def run_key_control(benchmark: InterruptorBenchmark) -> RunSummary:
    return _execute(
        benchmark,
        label="key_only",
        seed=CONTROL_SEED + 2,
        interruptors_exact=list(benchmark.true_positions),
        beam_width=CONTROL_BEAM_WIDTH,
        plateau_rounds=CONTROL_PLATEAU_ROUNDS,
    )


def run_joint_canary(benchmark: InterruptorBenchmark) -> RunSummary:
    return _execute(
        benchmark,
        label="joint_canary",
        seed=CANARY_SEED,
        interruptors=_pool_config(benchmark),
        beam_width=CANARY_BEAM_WIDTH,
        plateau_rounds=CONTROL_PLATEAU_ROUNDS,
    )


def run_science_block(
    benchmark: InterruptorBenchmark,
    *,
    block_id: int,
    seed: int,
) -> RunSummary:
    return _execute(
        benchmark,
        label=f"science_block_{block_id}",
        seed=seed,
        interruptors=_pool_config(benchmark),
        beam_width=SCIENCE_BEAM_WIDTH,
        plateau_rounds=SCIENCE_PLATEAU_ROUNDS,
    )


def terminal_metrics(
    benchmark: InterruptorBenchmark,
    summary: RunSummary,
) -> dict[str, Any]:
    matches = sum(a == b for a, b in zip(summary.plaintext, benchmark.plaintext))
    true_set = set(benchmark.true_positions)
    found_set = set(summary.found_positions)
    tp = len(true_set & found_set)
    precision = tp / len(found_set) if found_set else (1.0 if not true_set else 0.0)
    recall = tp / len(true_set) if true_set else 1.0
    position_f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "label": summary.label,
        "plaintext_matches": matches,
        "plaintext_length": len(benchmark.plaintext),
        "plaintext_match_ratio": matches / len(benchmark.plaintext),
        "key_exact": summary.found_key == benchmark.key,
        "positions_exact": summary.found_positions == benchmark.true_positions,
        "position_precision": precision,
        "position_recall": recall,
        "position_f1": position_f1,
        "selected_count": len(summary.found_positions),
        "exact": (
            summary.plaintext == benchmark.plaintext
            and summary.found_key == benchmark.key
            and summary.found_positions == benchmark.true_positions
        ),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
