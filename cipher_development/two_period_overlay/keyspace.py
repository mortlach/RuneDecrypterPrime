from __future__ import annotations

import hashlib
import math
from typing import Any, Callable, Mapping

import numpy as np

from cipher_development.shared.archive import (
    CandidateProvenance,
    CandidateRecord,
    candidate_id_for,
)
from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    CRIB_START,
    DECISION_SCORE,
    MASTER_SEED,
    PERIOD_A,
    PERIOD_B,
    RunBudget,
)

ScoreVariables = Callable[[np.ndarray], np.ndarray]


def deterministic_key() -> np.ndarray:
    a = [(5 * i + 3) % ALPHABET_SIZE for i in range(PERIOD_A)]
    b = [0] + [(7 * i + 11) % ALPHABET_SIZE for i in range(1, PERIOD_B)]
    return np.asarray([*a, *b], dtype=np.uint8)


def rref_mod(matrix: np.ndarray) -> tuple[np.ndarray, tuple[int, ...]]:
    out = np.asarray(matrix, dtype=np.int64).copy() % ALPHABET_SIZE
    row = 0
    pivots: list[int] = []
    for col in range(out.shape[1] - 1):
        found = np.flatnonzero(out[row:, col])
        if found.size == 0:
            continue
        selected = row + int(found[0])
        out[[row, selected]] = out[[selected, row]]
        out[row] = out[row] * pow(int(out[row, col]), -1, ALPHABET_SIZE) % ALPHABET_SIZE
        for other in range(out.shape[0]):
            if other != row and out[other, col]:
                out[other] = (out[other] - out[other, col] * out[row]) % ALPHABET_SIZE
        pivots.append(col)
        row += 1
        if row == out.shape[0]:
            break
    for values in out:
        if not np.any(values[:-1]) and values[-1]:
            raise ValueError("contradictory crib equations")
    return out, tuple(pivots)


def crib_space(ciphertext: np.ndarray, crib: np.ndarray) -> tuple[np.ndarray, np.ndarray, tuple[int, ...]]:
    key_length = PERIOD_A + PERIOD_B
    rows: list[np.ndarray] = []
    for offset, plain in enumerate(np.asarray(crib, dtype=np.uint8).tolist()):
        pos = CRIB_START + offset
        row = np.zeros(key_length + 1, dtype=np.int64)
        row[pos % PERIOD_A] = 1
        row[PERIOD_A + (pos % PERIOD_B)] = 1
        row[-1] = (int(ciphertext[pos]) - int(plain)) % ALPHABET_SIZE
        rows.append(row)
    gauge = np.zeros(key_length + 1, dtype=np.int64)
    gauge[PERIOD_A] = 1
    rows.append(gauge)

    reduced, pivots = rref_mod(np.stack(rows))
    free = tuple(i for i in range(key_length) if i not in pivots)
    particular = np.zeros(key_length, dtype=np.int64)
    basis = np.zeros((key_length, len(free)), dtype=np.int64)
    for j, col in enumerate(free):
        basis[col, j] = 1
    for row_index, pivot in enumerate(pivots):
        particular[pivot] = reduced[row_index, -1]
        for j, col in enumerate(free):
            basis[pivot, j] = -reduced[row_index, col]
    return particular % ALPHABET_SIZE, basis % ALPHABET_SIZE, free


def expand(variables: np.ndarray, particular: np.ndarray, basis: np.ndarray) -> np.ndarray:
    values = np.asarray(variables, dtype=np.int64)
    one = values.ndim == 1
    if one:
        values = values[None, :]
    keys = (particular[None, :] + values @ basis.T) % ALPHABET_SIZE
    keys = np.ascontiguousarray(keys, dtype=np.uint8)
    if not np.all(keys[:, PERIOD_A] == 0):
        raise RuntimeError("expanded candidate violated B[0] = 0 gauge")
    return keys[0] if one else keys


def comparison_seed(index: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError("comparison index must be a non-negative integer")
    data = f"{MASTER_SEED}:paired:{index}".encode("ascii")
    return int.from_bytes(hashlib.blake2b(data, digest_size=8, person=b"rdp-wp3-seed").digest(), "big")


def control_start_seed(index: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError("control index must be a non-negative integer")
    data = f"{MASTER_SEED}:control:{index}".encode("ascii")
    return int.from_bytes(hashlib.blake2b(data, digest_size=8, person=b"rdp-wp3-seed").digest(), "big")


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
) -> tuple[np.ndarray, float, int]:
    current = np.asarray(variables, dtype=np.uint8).copy()
    current_score = float(_score(evaluate, current)[0])
    evaluations = 1
    for _ in range(sweeps):
        improved = False
        for index in rng.permutation(current.size):
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
    return current, current_score, evaluations


def anneal_and_polish(
    evaluate: ScoreVariables,
    variables: np.ndarray,
    budget: RunBudget,
    seed: int,
) -> tuple[np.ndarray, float, Mapping[str, Any]]:
    rng = np.random.default_rng(seed)
    current = np.asarray(variables, dtype=np.uint8).copy()
    current_score = float(_score(evaluate, current)[0])
    best, best_score = current.copy(), current_score
    evaluations = 1
    accepted = downhill = 0

    for _cycle in range(budget.sa_cycles):
        for step in range(budget.sa_steps):
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
            # Always consume the acceptance draw so paired arms keep equivalent RNG streams.
            if delta >= 0 or acceptance_draw < math.exp(delta / max(temperature, 1e-12)):
                current, current_score = proposal, proposal_score
                accepted += 1
                downhill += int(delta < 0)
                if current_score > best_score + 1e-15:
                    best, best_score = current.copy(), current_score

    polished, polished_score, polish_evaluations = coordinate_search(
        evaluate, rng, best, budget.coordinate_sweeps
    )
    evaluations += polish_evaluations
    if polished_score > best_score + 1e-15:
        best, best_score = polished, polished_score
    return best, best_score, {
        "evaluations": evaluations,
        "sa_proposals_attempted": budget.sa_steps * budget.sa_cycles,
        "accepted_sa_proposals": accepted,
        "accepted_downhill_proposals": downhill,
        "coordinate_polish_gain": polished_score - current_score,
    }


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
) -> CandidateRecord:
    variable_list = np.asarray(variables, dtype=np.uint8).astype(int).tolist()
    key_list = expand(np.asarray(variables, dtype=np.uint8), particular, basis).astype(int).tolist()
    identity = {"expanded_key": key_list}
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={"variables": variable_list, "expanded_key": key_list},
        scores={DECISION_SCORE: float(score)},
        provenance=CandidateProvenance(
            source=source,
            operation=operation,
            parent_ids=parent_ids,
            evaluation_index=evaluation_index,
        ),
    )

