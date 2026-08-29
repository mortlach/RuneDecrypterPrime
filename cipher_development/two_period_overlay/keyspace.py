from __future__ import annotations
import hashlib
import math
import time
from typing import Any, Callable, Mapping
import numpy as np
from cipher_development.shared.archive import (
    CandidateProvenance,
    CandidateRecord,
    candidate_id_for,
)
from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    DECISION_SCORE,
    MASTER_SEED,
    CRIB_RUNES,
    PRIMARY_CRIB,
    TARGET_BENCHMARK,
    BenchmarkSpec,
    RunBudget,
)

ScoreVariables = Callable[[np.ndarray], np.ndarray]


class CampaignWallclockExceeded(RuntimeError):
    pass


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise CampaignWallclockExceeded("campaign wall-clock safety limit reached")


def deterministic_key(benchmark: BenchmarkSpec = TARGET_BENCHMARK) -> np.ndarray:
    a = [(5 * i + 3) % benchmark.alphabet_size for i in range(benchmark.period_a)]
    b = [benchmark.gauge_value] + [
        (7 * i + 11) % benchmark.alphabet_size for i in range(1, benchmark.period_b)
    ]
    return np.asarray([*a, *b], dtype=np.uint8)


def rref_mod(
    matrix: np.ndarray, modulus: int = ALPHABET_SIZE
) -> tuple[np.ndarray, tuple[int, ...]]:
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1:
        raise ValueError("modulus must be an integer greater than one")
    out = np.asarray(matrix, dtype=np.int64).copy() % modulus
    row = 0
    pivots: list[int] = []
    for col in range(out.shape[1] - 1):
        if row == out.shape[0]:
            break
        found = np.flatnonzero(out[row:, col])
        if found.size == 0:
            continue
        selected = row + int(found[0])
        out[[row, selected]] = out[[selected, row]]
        try:
            inverse = pow(int(out[row, col]), -1, modulus)
        except ValueError as exc:
            raise ValueError("crib equations require an invertible pivot") from exc
        out[row] = out[row] * inverse % modulus
        for other in range(out.shape[0]):
            if other != row and out[other, col]:
                out[other] = (out[other] - out[other, col] * out[row]) % modulus
        pivots.append(col)
        row += 1
    for values in out:
        if not np.any(values[:-1]) and values[-1]:
            raise ValueError("contradictory crib equations")
    return (out, tuple(pivots))


def crib_space(
    ciphertext: np.ndarray,
    crib: np.ndarray,
    benchmark: BenchmarkSpec = TARGET_BENCHMARK,
) -> tuple[np.ndarray, np.ndarray, tuple[int, ...]]:
    """Return the gauge-fixed affine key space for all declared complete cribs.

    ``crib`` remains the frozen primary ``uncomfortable`` rune sequence for
    compatibility with the existing campaign and replay artifacts. Any additional
    complete-word oracle assistance is declared on ``benchmark.additional_cribs``.
    """
    ciphertext = np.asarray(ciphertext, dtype=np.uint8)
    crib = np.asarray(crib, dtype=np.uint8)
    if len(ciphertext) != benchmark.text_length:
        raise ValueError("ciphertext length does not match the benchmark")
    if len(crib) != len(CRIB_RUNES):
        raise ValueError("crib length does not match the frozen complete word")
    if tuple((int(value) for value in crib)) != PRIMARY_CRIB.runes:
        raise ValueError("primary crib runes do not match the frozen contract")
    rows: list[np.ndarray] = []
    spans = (
        (benchmark.crib_start, tuple((int(value) for value in crib))),
        *((item.start, item.runes) for item in benchmark.additional_cribs),
    )
    for start, runes in spans:
        for offset, plain in enumerate(runes):
            pos = start + offset
            row = np.zeros(benchmark.key_length + 1, dtype=np.int64)
            row[pos % benchmark.period_a] = 1
            row[benchmark.period_a + pos % benchmark.period_b] = 1
            row[-1] = (int(ciphertext[pos]) - int(plain)) % benchmark.alphabet_size
            rows.append(row)
    gauge = np.zeros(benchmark.key_length + 1, dtype=np.int64)
    gauge[benchmark.gauge_key_index] = 1
    gauge[-1] = benchmark.gauge_value
    rows.append(gauge)
    reduced, pivots = rref_mod(np.stack(rows), benchmark.alphabet_size)
    free = tuple((i for i in range(benchmark.key_length) if i not in pivots))
    particular = np.zeros(benchmark.key_length, dtype=np.int64)
    basis = np.zeros((benchmark.key_length, len(free)), dtype=np.int64)
    for j, col in enumerate(free):
        basis[col, j] = 1
    for row_index, pivot in enumerate(pivots):
        particular[pivot] = reduced[row_index, -1]
        for j, col in enumerate(free):
            basis[pivot, j] = -reduced[row_index, col]
    return (particular % benchmark.alphabet_size, basis % benchmark.alphabet_size, free)


def expand(
    variables: np.ndarray,
    particular: np.ndarray,
    basis: np.ndarray,
    benchmark: BenchmarkSpec = TARGET_BENCHMARK,
) -> np.ndarray:
    values = np.asarray(variables, dtype=np.int64)
    if values.ndim not in (1, 2):
        raise ValueError("affine variables must be a vector or matrix")
    one = values.ndim == 1
    if one:
        values = values[None, :]
    particular = np.asarray(particular, dtype=np.int64)
    basis = np.asarray(basis, dtype=np.int64)
    if particular.shape != (benchmark.key_length,):
        raise ValueError("particular solution has the wrong key length")
    if basis.shape != (benchmark.key_length, values.shape[1]):
        raise ValueError("basis shape does not match the variables and key length")
    keys = (particular[None, :] + values @ basis.T) % benchmark.alphabet_size
    keys = np.ascontiguousarray(keys, dtype=np.uint8)
    if not np.all(keys[:, benchmark.gauge_key_index] == benchmark.gauge_value):
        raise RuntimeError("expanded candidate violated the B[0] = 0 gauge")
    return keys[0] if one else keys


def comparison_seed(index: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError("comparison index must be a non-negative integer")
    data = f"{MASTER_SEED}:paired:{index}".encode("ascii")
    return int.from_bytes(
        hashlib.blake2b(data, digest_size=8, person=b"rdp-wp3-seed").digest(), "big"
    )


def control_start_seed(index: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError("control index must be a non-negative integer")
    data = f"{MASTER_SEED}:control:{index}".encode("ascii")
    return int.from_bytes(
        hashlib.blake2b(data, digest_size=8, person=b"rdp-wp3-seed").digest(), "big"
    )


def _score(evaluate: ScoreVariables, variables: np.ndarray) -> np.ndarray:
    values = np.asarray(variables, dtype=np.uint8)
    batch = values[None, :] if values.ndim == 1 else values
    scores = np.asarray(evaluate(batch), dtype=np.float64)
    if scores.shape != (len(batch),) or not np.all(np.isfinite(scores)):
        raise RuntimeError("candidate evaluator returned invalid scores")
    return scores


def coordinate_search(
    evaluate: ScoreVariables,
    rng: np.random.Generator,
    variables: np.ndarray,
    sweeps: int,
    *,
    deadline: float | None = None,
) -> tuple[np.ndarray, float, int]:
    current = np.asarray(variables, dtype=np.uint8).copy()
    _check_deadline(deadline)
    current_score = float(_score(evaluate, current)[0])
    evaluations = 1
    for _ in range(sweeps):
        improved = False
        for index in rng.permutation(current.size):
            _check_deadline(deadline)
            candidates = np.repeat(current[None, :], ALPHABET_SIZE, axis=0)
            candidates[:, index] = np.arange(ALPHABET_SIZE, dtype=np.uint8)
            scores = _score(evaluate, candidates)
            evaluations += len(candidates)
            best = int(np.argmax(scores))
            if scores[best] > current_score + 1e-15:
                current = candidates[best].copy()
                current_score = float(scores[best])
                improved = True
        if not improved:
            break
    return (current, current_score, evaluations)


def anneal_and_polish(
    evaluate: ScoreVariables,
    variables: np.ndarray,
    budget: RunBudget,
    seed: int,
    *,
    deadline: float | None = None,
) -> tuple[np.ndarray, float, Mapping[str, Any]]:
    rng = np.random.default_rng(seed)
    current = np.asarray(variables, dtype=np.uint8).copy()
    _check_deadline(deadline)
    current_score = float(_score(evaluate, current)[0])
    best, best_score = (current.copy(), current_score)
    evaluations = 1
    accepted = downhill = 0
    for _cycle in range(budget.sa_cycles):
        for step in range(budget.sa_steps):
            _check_deadline(deadline)
            fraction = step / max(1, budget.sa_steps - 1)
            temperature = budget.sa_t0 * (budget.sa_tmin / budget.sa_t0) ** fraction
            index = int(rng.integers(0, current.size))
            old = int(current[index])
            new = int(rng.integers(0, ALPHABET_SIZE - 1))
            if new >= old:
                new += 1
            acceptance_draw = float(rng.random())
            proposal = current.copy()
            proposal[index] = new
            proposal_score = float(_score(evaluate, proposal)[0])
            evaluations += 1
            delta = proposal_score - current_score
            if delta >= 0 or acceptance_draw < math.exp(
                delta / max(temperature, 1e-12)
            ):
                current, current_score = (proposal, proposal_score)
                accepted += 1
                downhill += int(delta < 0)
                if current_score > best_score + 1e-15:
                    best, best_score = (current.copy(), current_score)
    pre_polish_best_score = best_score
    polished, polished_score, polish_evaluations = coordinate_search(
        evaluate, rng, best, budget.coordinate_sweeps, deadline=deadline
    )
    evaluations += polish_evaluations
    if polished_score > best_score + 1e-15:
        best, best_score = (polished, polished_score)
    return (
        best,
        best_score,
        {
            "evaluations": evaluations,
            "sa_proposals_attempted": budget.sa_steps * budget.sa_cycles,
            "accepted_sa_proposals": accepted,
            "accepted_downhill_proposals": downhill,
            "coordinate_polish_gain": polished_score - pre_polish_best_score,
        },
    )


def candidate_record(
    variables: np.ndarray,
    score: float,
    particular: np.ndarray,
    basis: np.ndarray,
    *,
    source: str,
    operation: str,
    evaluation_index: int,
    parent_ids: tuple[str, ...] = (),
    benchmark: BenchmarkSpec = TARGET_BENCHMARK,
) -> CandidateRecord:
    variable_list = np.asarray(variables, dtype=np.uint8).astype(int).tolist()
    key_list = (
        expand(np.asarray(variables, dtype=np.uint8), particular, basis, benchmark)
        .astype(int)
        .tolist()
    )
    identity = {"expanded_key": key_list}
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={
            "variables": variable_list,
            "expanded_key": key_list,
            "benchmark_id": benchmark.benchmark_id,
        },
        scores={DECISION_SCORE: float(score)},
        provenance=CandidateProvenance(
            source=source,
            operation=operation,
            parent_ids=parent_ids,
            evaluation_index=evaluation_index,
        ),
    )
