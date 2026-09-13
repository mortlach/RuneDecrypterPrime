"""Solve a P7/C7 periodic-columnar problem from a qualified non-answer warm start.

Kaeding orders this search by the raw LM statistic while the public scorer stays
percentile log probability. Reference plaintext verifies recovery only after the
solve. Expect exact recovery. This will likely take tens of minutes on a CPU,
depending on its specifications.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Sequence
from typing import Any

import numpy as np

from rdp import api
from rdp.data.runeglish import Runeglish
from tutorials.v1.data.periodic_columnar_p7_warm_start import (
    QUALIFIED_INITIAL_KEY,
)
from tutorials.v1.data.plaintext_fixtures import long_plaintext_string
from tutorials.v1.support import tutorial_pretty as pretty

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALPHABET_SIZE = 29
PERIOD = 7
COLUMNS = 7
PLAINTEXT_LENGTH = 2_489
BENCHMARK_KEY_SEED = 54_321
SOLVER_SEED = 12_446
MIN_MATCH_RATIO = 1.0
PROGRESS_PERCENT_INTERVAL = 10


def _complete_word_prefix(
    plaintext: Sequence[int],
    word_lengths: Sequence[Sequence[int]],
    *,
    limit: int,
) -> tuple[tuple[int, ...], tuple[tuple[int, int], ...]]:
    end = min(limit, len(plaintext), len(word_lengths))
    while end > 0:
        position, word_length = (int(value) for value in word_lengths[end - 1])
        if position == word_length - 1:
            break
        end -= 1
    if end <= 0:
        raise ValueError("plaintext limit does not contain a complete word")
    return (
        tuple(int(value) for value in plaintext[:end]),
        tuple((int(position), int(length)) for position, length in word_lengths[:end]),
    )


def build_run_spec() -> tuple[api.RunSpec, api.RuneIndices]:
    direction = api.TextDirection.RTL
    plaintext, word_lengths, _ = Runeglish.encode_english_to_runes(
        long_plaintext_string,
        direction=direction,
    )
    plaintext_indices, word_lengths = _complete_word_prefix(
        plaintext,
        word_lengths,
        limit=PLAINTEXT_LENGTH,
    )
    rng = np.random.default_rng(BENCHMARK_KEY_SEED)
    benchmark_key: api.ConcreteKey = tuple(
        int(value)
        for value in np.concatenate(
            [
                *(rng.permutation(ALPHABET_SIZE) for _ in range(PERIOD)),
                rng.permutation(COLUMNS),
            ]
        )
    )
    cipher = api.CipherSpec.periodic_columnar(
        period=PERIOD,
        columns=COLUMNS,
        order=api.advanced.PeriodicColumnarOrder.COLUMNAR_THEN_SUBSTITUTION,
        alphabet_size=ALPHABET_SIZE,
    )
    ciphertext = api.encrypt(
        plaintext_indices,
        cipher=cipher,
        key=benchmark_key,
    )
    scoring = api.ScoringConfig(
        character_lane_enabled=True,
        wli_lane_enabled=False,
        character_order_weights={3: 0.5, 4: 0.5},
        wli_order_weights={},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )
    solver = api.SolverSpec.kaeding(
        steps=360,
        restarts=1,
        inner_batch_size=192,
        column_interval=1,
        column_batch_size=384,
        block_schedule=api.advanced.KaedingBlockSchedule.ROUND_ROBIN,
        target_score=None,
        seed=SOLVER_SEED,
        slip_policy=api.advanced.KaedingSlipPolicy.ON_STALL,
        slip_interval=60,
        slip_blocks=1,
        stall_rounds=220,
        stall_slip_limit=3,
        slip_swaps=50,
        stop_after_stall_slip_limit=False,
        use_raw_score=True,
    )
    request = api.RunSpec(
        problem_input=api.RuneInput(
            value=ciphertext,
            word_length_information=word_lengths,
        ),
        cipher=cipher,
        key_space=api.KeySpec.periodic_columnar(
            period=PERIOD,
            columns=COLUMNS,
            alphabet_size=ALPHABET_SIZE,
        ),
        solver=solver,
        scoring=scoring,
        initial_keys=(QUALIFIED_INITIAL_KEY,),
        telemetry_enabled=True,
        text_direction=direction,
        compute_device=api.ComputeDevice.CPU,
    )
    return request, plaintext_indices


def _progress(payload: dict[str, Any], _key: Sequence[int] | None = None) -> None:
    percent = int(payload.get("pct", 0) or 0)
    if percent <= 0 or percent % PROGRESS_PERCENT_INTERVAL:
        return
    score = payload.get("best_score")
    score_text = "n/a" if score is None else f"{float(score):.6f}"
    print(
        "[Kaeding] "
        f"{percent}% "
        f"step={int(payload.get('step', 0) or 0)} "
        f"evaluations={int(payload.get('evals', 0) or 0)} "
        f"percentile={score_text}",
        flush=True,
    )


def _match_ratio(recovered: Sequence[int] | None, expected: Sequence[int]) -> float:
    if recovered is None or len(recovered) != len(expected) or not expected:
        return 0.0
    return sum(
        int(left) == int(right) for left, right in zip(recovered, expected)
    ) / len(expected)


def main() -> api.RunResult:
    pretty.print_tutorial_contract(
        name="Periodic columnar P7/C7 with a qualified warm start",
        cipher="periodic columnar (columnar then substitution)",
        solver="one-start Kaeding",
        direction="right_to_left",
        expected_result="exact plaintext recovery",
        uses_reference_stop_score=False,
    )
    print(
        "This will likely take tens of minutes on a CPU, depending on its specifications."
    )
    print("Search ordering: raw LM statistic; public scorer: percentile log probability.")

    request, expected_plaintext = build_run_spec()
    started = time.perf_counter()
    result = api.run(
        request,
        progress_callback=_progress,
    )
    elapsed = time.perf_counter() - started
    ratio = _match_ratio(result.plaintext_indices, expected_plaintext)
    changed_positions = (
        None
        if result.key is None
        else sum(
            int(left) != int(right)
            for left, right in zip(result.key, QUALIFIED_INITIAL_KEY)
        )
    )
    print(f"Solver stop reason: {result.status.stop_reason.value}")
    print(f"Solver runtime reason: {result.status.runtime_reason}")
    print(f"Steps: {result.solver_report.steps}")
    print(f"Evaluations: {result.solver_report.evaluations}")
    print(f"Public score: {result.score}")
    print(f"Raw LM statistic: {result.telemetry['kaeding']['best_raw']}")
    print(f"Warm-start positions changed: {changed_positions}")
    print(f"Elapsed seconds: {elapsed:.3f}")
    print(f"Match ratio: {ratio:.3f}")
    print(f"Exact recovery: {tuple(result.plaintext_indices or ()) == expected_plaintext} ({len(expected_plaintext)} runes)")
    pretty.print_summary_spacer()
    api.display.print_result(
        result,
        spec=request,
        options=api.display.SummaryOptions.for_tutorial(),
    )
    if ratio < MIN_MATCH_RATIO:
        raise RuntimeError(f"Solve failed: match_ratio={ratio:.6f}")
    return result


if __name__ == "__main__":
    main()
