from __future__ import annotations

import hashlib
import json
import math
import time
from bisect import bisect_left
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Callable, Sequence

import numpy as np

from rdp.api.pipeline_helpers import finalize_solution
from rdp.api.stop_reason_contract import StopCategory, StopReason
from rdp.api.specs import CipherSpec, KeySpec
from rdp.api.two_period_cribs import (
    TWO_PERIOD_CRIBS_CONTRACT,
    TwoPeriodCribsRequest,
)
from rune_decrypter_prime.core.config import (
    HardCribConfig,
    InterruptorConfig,
    ScoringConfig,
    Solution,
)
from rune_decrypter_prime.core.config.cipher import materialize_cipher_config
from rune_decrypter_prime.core.engine.builders import build_cipher, build_scorer
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.types import (
    Device,
    Direction,
    ComputeDevice,
    CipherKind,
    InterruptorSearchStrategy,
    KeyKind,
    InterruptorMode,
    TextDirection,
)
from rune_decrypter_prime.utils.runeglish import Runeglish

_EPSILON = 1e-15


@dataclass(frozen=True, slots=True)
class CribSpan:
    word: str
    runes: tuple[int, ...]
    start: int

    @property
    def stop(self) -> int:
        return self.start + len(self.runes)


@dataclass(frozen=True, slots=True)
class CribConstraintSpace:
    modulus: int
    period_a: int
    period_b: int
    particular: tuple[int, ...]
    basis: tuple[tuple[int, ...], ...]
    free_columns: tuple[int, ...]

    @property
    def dimension(self) -> int:
        return len(self.free_columns)


@dataclass(frozen=True, slots=True)
class TwoPeriodBranch:
    branch_id: str
    fixed_cribs: tuple[CribSpan, ...]
    candidate_crib: CribSpan | None
    constraint_space: CribConstraintSpace
    interruptors: tuple[int, ...] = ()

    @property
    def spans(self) -> tuple[CribSpan, ...]:
        return self.fixed_cribs + (
            () if self.candidate_crib is None else (self.candidate_crib,)
        )


def rref_mod(matrix: np.ndarray, modulus: int) -> tuple[np.ndarray, tuple[int, ...]]:
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1:
        raise ValueError("modulus must be an integer greater than one")
    out = np.asarray(matrix, dtype=np.int64).copy() % modulus
    row = 0
    pivots: list[int] = []
    for col in range(out.shape[1] - 1):
        if row == out.shape[0]:
            break
        choices = np.flatnonzero(out[row:, col])
        if not choices.size:
            continue
        selected = row + int(choices[0])
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
    return out, tuple(pivots)


def derive_constraint_space(
    ciphertext: np.ndarray,
    spans: Sequence[CribSpan],
    *,
    period_a: int,
    period_b: int,
    modulus: int,
    interruptors: Sequence[int] = (),
) -> CribConstraintSpace:
    key_length = period_a + period_b
    resolved_interruptors = _validated_interruptor_positions(
        interruptors, len(ciphertext)
    )
    interruptor_set = set(resolved_interruptors)
    rows: list[np.ndarray] = []
    for span in spans:
        if span.start < 0 or span.stop > len(ciphertext):
            raise ValueError(f"crib {span.word!r} lies outside the ciphertext")
        for offset, plain in enumerate(span.runes):
            position = span.start + offset
            if position in interruptor_set:
                if int(ciphertext[position]) != int(plain):
                    raise ValueError(
                        f"crib {span.word!r} contradicts interruptor at position {position}"
                    )
                continue
            core_position = position - bisect_left(resolved_interruptors, position)
            row = np.zeros(key_length + 1, dtype=np.int64)
            row[core_position % period_a] = 1
            row[period_a + core_position % period_b] = 1
            row[-1] = (int(ciphertext[position]) - plain) % modulus
            rows.append(row)
    gauge = np.zeros(key_length + 1, dtype=np.int64)
    gauge[period_a] = 1
    rows.append(gauge)
    reduced, pivots = rref_mod(np.stack(rows), modulus)
    free = tuple(index for index in range(key_length) if index not in pivots)
    particular = np.zeros(key_length, dtype=np.int64)
    basis = np.zeros((key_length, len(free)), dtype=np.int64)
    for index, column in enumerate(free):
        basis[column, index] = 1
    for row_index, pivot in enumerate(pivots):
        particular[pivot] = reduced[row_index, -1]
        for index, column in enumerate(free):
            basis[pivot, index] = -reduced[row_index, column]
    return CribConstraintSpace(
        modulus=modulus,
        period_a=period_a,
        period_b=period_b,
        particular=tuple(int(x) for x in particular % modulus),
        basis=tuple(tuple(int(x) for x in row) for row in basis % modulus),
        free_columns=free,
    )


def expand_reduced_key(values: np.ndarray, space: CribConstraintSpace) -> np.ndarray:
    variables = np.asarray(values, dtype=np.int64)
    one = variables.ndim == 1
    if variables.ndim not in (1, 2):
        raise ValueError("affine variables must be a vector or matrix")
    if one:
        variables = variables[None, :]
    particular = np.asarray(space.particular, dtype=np.int64)
    basis = np.asarray(space.basis, dtype=np.int64)
    if variables.shape[1] != space.dimension:
        raise ValueError("affine variable dimension mismatch")
    keys = (particular[None, :] + variables @ basis.T) % space.modulus
    keys = np.ascontiguousarray(keys, dtype=np.uint8)
    if np.any(keys[:, space.period_a] != 0):
        raise RuntimeError("expanded key violated the B[0] = 0 gauge")
    return keys[0] if one else keys


def _span(word: str, start: int, direction: Direction) -> CribSpan:
    encoded, _wli, _runes = Runeglish.encode_english_to_runes(
        word, direction=direction.value
    )
    return CribSpan(word=word, runes=tuple(int(x) for x in encoded), start=start)


def _complete_word_starts(wli: Sequence[Sequence[int]], length: int) -> tuple[int, ...]:
    starts: list[int] = []
    for start in range(0, len(wli) - length + 1):
        if tuple((int(a), int(b)) for a, b in wli[start : start + length]) == tuple(
            (offset, length) for offset in range(length)
        ):
            starts.append(start)
    return tuple(starts)


def _validated_interruptor_positions(
    interruptors: Sequence[int],
    text_length: int,
) -> tuple[int, ...]:
    positions = tuple(int(value) for value in interruptors)
    if tuple(sorted(set(positions))) != positions:
        raise ValueError("resolved interruptor positions must be sorted and unique")
    if any(position < 0 or position >= text_length for position in positions):
        raise ValueError(f"interruptor position lies outside text length {text_length}")
    return positions


def _resolve_interruptor_hypotheses(
    config: InterruptorConfig | None,
    text_length: int,
) -> tuple[tuple[int, ...], ...]:
    if config is None or config.mode is InterruptorMode.DISABLED:
        return ((),)
    if config.mode is InterruptorMode.EXACT:
        return (
            _validated_interruptor_positions(
                tuple(config.parameters["positions"]), text_length
            ),
        )

    pool = _validated_interruptor_positions(
        tuple(config.parameters["candidate_positions"]), text_length
    )
    min_count = int(config.parameters["minimum_count"])
    max_count = int(config.parameters["maximum_count"])
    combination_count = sum(
        math.comb(len(pool), count) for count in range(min_count, max_count + 1)
    )
    strategy = config.parameters["strategy"]
    if strategy == InterruptorSearchStrategy.KEY_OPERATIONS.value:
        raise ValueError(
            "two_period_cribs requires structural interruptor hypotheses; "
            "search_strategy='keyops' is unsupported"
        )
    if strategy == InterruptorSearchStrategy.AUTO.value and combination_count > int(
        config.parameters["maximum_combinations"]
    ):
        raise ValueError(
            "two_period_cribs structural interruptor search exceeds bruteforce_max; "
            "narrow the pool/count range, raise bruteforce_max, or explicitly request bruteforce"
        )
    return tuple(
        tuple(int(value) for value in picked)
        for count in range(min_count, max_count + 1)
        for picked in combinations(pool, count)
    )


def _branch_id(
    fixed_cribs: Sequence[CribSpan],
    candidate_crib: CribSpan | None,
    space: CribConstraintSpace,
    interruptors: Sequence[int] = (),
) -> str:
    payload = {
        "contract": TWO_PERIOD_CRIBS_CONTRACT,
        "modulus": space.modulus,
        "period_a": space.period_a,
        "period_b": space.period_b,
        "fixed_cribs": sorted(
            ({"runes": list(span.runes), "start": span.start} for span in fixed_cribs),
            key=lambda row: (row["start"], row["runes"]),
        ),
        "candidate_crib": (
            None
            if candidate_crib is None
            else {"runes": list(candidate_crib.runes), "start": candidate_crib.start}
        ),
    }
    resolved_interruptors = tuple(int(value) for value in interruptors)
    if resolved_interruptors:
        payload["interruptors"] = list(resolved_interruptors)
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return f"tpb_{digest}"


def _validate_candidate_position_contract(
    wli: Sequence[Sequence[int]],
    request: TwoPeriodCribsRequest,
    direction: Direction,
) -> None:
    """Validate caller-supplied candidate positions independently of structural branches."""
    for word in request.candidate_words:
        positions = request.positions_for(word)
        if positions is None:
            continue
        runes = _span(word, 0, direction).runes
        complete_starts = _complete_word_starts(wli, len(runes))
        invalid = tuple(
            position for position in positions if position not in complete_starts
        )
        if invalid:
            position = invalid[0]
            raise ValueError(
                f"candidate word {word!r} position {position} is not a complete "
                f"WLI span of rune length {len(runes)}"
            )


def build_branches(
    ciphertext: np.ndarray,
    wli: Sequence[Sequence[int]],
    request: TwoPeriodCribsRequest,
    *,
    period_a: int,
    period_b: int,
    modulus: int,
    direction: Direction,
    interruptors: Sequence[int] = (),
) -> tuple[tuple[TwoPeriodBranch, ...], tuple[dict[str, Any], ...]]:
    resolved_interruptors = _validated_interruptor_positions(
        interruptors, len(ciphertext)
    )
    _validate_candidate_position_contract(wli, request, direction)
    fixed = tuple(_span(word, start, direction) for word, start in request.fixed_cribs)
    # Fixed evidence is authoritative: contradictions are a caller error.
    derive_constraint_space(
        ciphertext,
        fixed,
        period_a=period_a,
        period_b=period_b,
        modulus=modulus,
        interruptors=resolved_interruptors,
    )
    alternatives: list[CribSpan | None] = []
    rejected: list[dict[str, Any]] = []
    if not request.candidate_words:
        alternatives.append(None)
    for word in request.candidate_words:
        runes = _span(word, 0, direction).runes
        positions = request.positions_for(word)
        complete_starts = _complete_word_starts(wli, len(runes))
        if positions is None:
            positions = complete_starts
            if not positions:
                rejected.append(
                    {
                        "word": word,
                        "start": None,
                        "reason": f"no complete WLI span of rune length {len(runes)}",
                    }
                )
        else:
            if not positions:
                rejected.append(
                    {
                        "word": word,
                        "start": None,
                        "reason": "explicit candidate position list is empty",
                    }
                )
            invalid = tuple(
                position for position in positions if position not in complete_starts
            )
            if invalid:
                position = invalid[0]
                raise ValueError(
                    f"candidate word {word!r} position {position} is not a complete "
                    f"WLI span of rune length {len(runes)}"
                )
        alternatives.extend(CribSpan(word, runes, start) for start in positions)

    accepted: dict[str, TwoPeriodBranch] = {}
    for candidate in alternatives:
        spans = fixed + (() if candidate is None else (candidate,))
        try:
            space = derive_constraint_space(
                ciphertext,
                spans,
                period_a=period_a,
                period_b=period_b,
                modulus=modulus,
                interruptors=resolved_interruptors,
            )
        except ValueError as exc:
            rejected.append(
                {
                    "word": None if candidate is None else candidate.word,
                    "start": None if candidate is None else candidate.start,
                    "reason": str(exc),
                }
            )
            continue
        branch_id = _branch_id(fixed, candidate, space, resolved_interruptors)
        accepted.setdefault(
            branch_id,
            TwoPeriodBranch(branch_id, fixed, candidate, space, resolved_interruptors),
        )
    if not accepted:
        reasons = "; ".join(
            f"{row['word']!r} at {row['start']}: {row['reason']}" for row in rejected
        )
        detail = f": {reasons}" if reasons else ""
        raise ValueError(f"no compatible two-period crib branches remain{detail}")
    return tuple(accepted[key] for key in sorted(accepted)), tuple(rejected)


def derive_child_seed(root_seed: int, *parts: object) -> int:
    payload = ":".join(
        (str(root_seed), TWO_PERIOD_CRIBS_CONTRACT, *(str(x) for x in parts))
    )
    return int.from_bytes(
        hashlib.blake2b(
            payload.encode("utf-8"), digest_size=8, person=b"rdp-tp-cribs"
        ).digest(),
        "big",
    )


@dataclass(frozen=True, slots=True)
class CoordinateSearchResult:
    variables: np.ndarray
    score: float
    evaluations: int
    stop_reason: StopReason


def _coordinate_search_with_status(
    evaluate: Callable[[np.ndarray], np.ndarray],
    rng: np.random.Generator,
    variables: np.ndarray,
    sweeps: int,
    *,
    modulus: int = 29,
) -> CoordinateSearchResult:
    current = np.asarray(variables, dtype=np.uint8).copy()
    initial_scores = np.asarray(evaluate(current[None, :]), dtype=np.float64)
    if initial_scores.shape != (1,) or not np.all(np.isfinite(initial_scores)):
        raise RuntimeError("candidate evaluator returned invalid scores")
    current_score = float(initial_scores[0])
    evaluations = 1
    if current.size == 0:
        return CoordinateSearchResult(
            current,
            current_score,
            evaluations,
            StopReason.CONSTRAINT_SPACE_RESOLVED_EXACTLY,
        )
    for _sweep in range(sweeps):
        improved = False
        for index in rng.permutation(current.size):
            candidates = np.repeat(current[None, :], modulus, axis=0)
            candidates[:, index] = np.arange(modulus, dtype=np.uint8)
            scores = np.asarray(evaluate(candidates), dtype=np.float64)
            if scores.shape != (modulus,) or not np.all(np.isfinite(scores)):
                raise RuntimeError("candidate evaluator returned invalid scores")
            evaluations += modulus
            best = int(np.argmax(scores))
            if scores[best] > current_score + _EPSILON:
                current, current_score = candidates[best].copy(), float(scores[best])
                improved = True
        if not improved:
            return CoordinateSearchResult(
                current,
                current_score,
                evaluations,
                StopReason.NO_IMPROVEMENT_BUDGET_REACHED,
            )
    return CoordinateSearchResult(
        current,
        current_score,
        evaluations,
        StopReason.MAX_SWEEPS_REACHED,
    )


def coordinate_search(
    evaluate: Callable[[np.ndarray], np.ndarray],
    rng: np.random.Generator,
    variables: np.ndarray,
    sweeps: int,
    *,
    modulus: int = 29,
) -> tuple[np.ndarray, float, int]:
    """Compatibility wrapper retaining the established three-value return."""
    result = _coordinate_search_with_status(
        evaluate, rng, variables, sweeps, modulus=modulus
    )
    return result.variables, result.score, result.evaluations


def _profile(
    profile_id: str, hard_crib: HardCribConfig, direction: Direction
) -> ScoringConfig:
    profiles = {
        "S2": (False, True, (), (1, 2), 0.0, 1.0),
        "B1": (True, True, (2, 3), (2, 3), 0.25, 0.75),
        "F1": (True, True, (1, 2, 3, 4), (1, 2, 3, 4), 0.25, 0.75),
    }
    include_char, use_wli, char_orders, wli_orders, char_total, wli_total = profiles[
        profile_id
    ]
    return ScoringConfig(
        character_lane_enabled=include_char,
        word_length_lane_enabled=use_wli,
        character_ngram_order=max(char_orders, default=1),
        word_length_ngram_order=max(wli_orders, default=1),
        character_order_weights={}
        if not char_orders
        else {order: char_total / len(char_orders) for order in char_orders},
        word_length_order_weights={}
        if not wli_orders
        else {order: wli_total / len(wli_orders) for order in wli_orders},
        hard_crib=hard_crib,
    )


def profile_contract_hash(profile_id: str) -> str:
    cfg = _profile(profile_id, HardCribConfig(enabled=False), Direction.LTR)
    effective = cfg.effective_lm_model_weights()
    effective_pair = (
        float(sum(weight for channel, _n, weight in effective if channel == "char")),
        float(sum(weight for channel, _n, weight in effective if channel == "wli")),
    )
    payload = {
        "profile": profile_id,
        "character_lane_enabled": cfg.character_lane_enabled,
        "word_length_lane_enabled": cfg.word_length_lane_enabled,
        "character_ngram_order": cfg.character_ngram_order,
        "word_length_ngram_order": cfg.word_length_ngram_order,
        "character_order_weights": dict(cfg.character_order_weights or {}),
        "word_length_order_weights": dict(cfg.word_length_order_weights or {}),
        # A2 profile identity was defined by the effective aggregate channel
        # totals, even when per-order maps supplied them. Preserve that stable
        # contract while ScoringConfig keeps requested and derived fields separate.
        "weights": effective_pair,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _candidate_id(key: np.ndarray, interruptors: Sequence[int] = ()) -> str:
    key_bytes = bytes(np.asarray(key, dtype=np.uint8))
    resolved_interruptors = tuple(int(value) for value in interruptors)
    if not resolved_interruptors:
        payload = key_bytes
    else:
        payload = (
            key_bytes
            + b"|interruptors|"
            + json.dumps(list(resolved_interruptors), separators=(",", ":")).encode(
                "ascii"
            )
        )
    return "tpc_" + hashlib.sha256(payload).hexdigest()[:20]


def _records_digest(records: Sequence[tuple[str, float]]) -> str:
    payload = [
        [candidate_id, float(score).hex()] for candidate_id, score in sorted(records)
    ]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _deduplicated_union(
    *surfaces: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    union: dict[str, dict[str, Any]] = {}
    for surface in surfaces:
        for candidate_id in sorted(surface):
            union.setdefault(candidate_id, surface[candidate_id])
    return union


def _run_refinement_stage(
    *,
    stage_id: str,
    score_field: str,
    evaluate: Callable[[np.ndarray], np.ndarray],
    branch: TwoPeriodBranch,
    inputs: dict[str, dict[str, Any]],
    sweeps: int,
    root_seed: int,
    modulus: int,
) -> tuple[dict[str, dict[str, Any]], int, float]:
    started = time.perf_counter()
    evaluations = 0
    output: dict[str, dict[str, Any]] = {}
    for parent_id in sorted(inputs):
        parent = inputs[parent_id]
        rng = np.random.default_rng(
            derive_child_seed(root_seed, branch.branch_id, stage_id, parent_id)
        )
        search_result = _coordinate_search_with_status(
            evaluate,
            rng,
            np.asarray(parent["variables"], dtype=np.uint8),
            sweeps,
            modulus=modulus,
        )
        variables = search_result.variables
        score = search_result.score
        used = search_result.evaluations
        evaluations += used
        expanded = expand_reduced_key(variables, branch.constraint_space)
        candidate_id = _candidate_id(expanded, branch.interruptors)
        record = {
            "candidate_id": candidate_id,
            "branch_id": branch.branch_id,
            "interruptors": list(branch.interruptors),
            "variables": variables.astype(int).tolist(),
            "key": expanded.astype(int).tolist(),
            score_field: score,
            "source_stage": stage_id,
            "parent_id": parent_id,
            "search_stop_reason": search_result.stop_reason.value,
        }
        old = output.get(candidate_id)
        if old is None or score > float(old[score_field]) + _EPSILON:
            output[candidate_id] = record
    return output, evaluations, time.perf_counter() - started


def _stage_stop_reason(records: Sequence[dict[str, Any]]) -> StopReason:
    reasons = {str(record.get("search_stop_reason", "")) for record in records}
    reasons.discard("")
    if StopReason.MAX_SWEEPS_REACHED.value in reasons:
        return StopReason.MAX_SWEEPS_REACHED
    if StopReason.NO_IMPROVEMENT_BUDGET_REACHED.value in reasons:
        return StopReason.NO_IMPROVEMENT_BUDGET_REACHED
    if reasons == {StopReason.CONSTRAINT_SPACE_RESOLVED_EXACTLY.value}:
        return StopReason.CONSTRAINT_SPACE_RESOLVED_EXACTLY
    if not reasons:
        return StopReason.UNKNOWN_RUNTIME_REASON
    return StopReason(sorted(reasons)[0])


def _stage_stop_category(reason: StopReason) -> str:
    if reason in {
        StopReason.MAX_SWEEPS_REACHED,
        StopReason.NO_IMPROVEMENT_BUDGET_REACHED,
    }:
        return StopCategory.BUDGET.value
    if reason is StopReason.UNKNOWN_RUNTIME_REASON:
        return StopCategory.ERROR.value
    return StopCategory.SUCCESS.value


def _validate_cipher(cipher: CipherSpec, key: KeySpec) -> tuple[int, int, int]:
    if (
        not isinstance(cipher, CipherSpec)
        or cipher.kind is not CipherKind.TWO_PERIOD_VIGENERE
    ):
        raise ValueError("two_period_cribs requires CipherSpec.two_period_vigenere")
    parameters = cipher.parameters
    periods = [int(parameters["first_period"]), int(parameters["second_period"])]
    modulus = int(parameters["alphabet_size"])
    if modulus != 29:
        raise ValueError(
            "two_period_cribs currently requires the prime runic modulus 29"
        )
    if parameters["schedule"] != "overlay" or parameters["mask"] is not None:
        raise ValueError("two_period_cribs requires additive overlay scheduling")
    if not isinstance(key, KeySpec) or key.kind is not KeyKind.REPEATING:
        raise ValueError("two_period_cribs requires a repeating canonical key")
    if int(key.parameters["length"]) != sum(periods):
        raise ValueError("two_period_cribs key length must equal period_a + period_b")
    return periods[0], periods[1], modulus


def run_two_period_stages(
    *,
    ciphertext: np.ndarray,
    wli: Sequence[Sequence[int]],
    cipher: CipherSpec,
    key: KeySpec,
    request: TwoPeriodCribsRequest,
    device: Device,
    direction: Direction,
    telemetry_on: bool,
    interruptors: InterruptorConfig | dict[str, Any] | None = None,
    interruptors_exact: Sequence[int] | None = None,
    interruptors_pool: Sequence[int] | None = None,
    interruptors_max: int | None = None,
) -> Solution:
    started = time.perf_counter()
    period_a, period_b, modulus = _validate_cipher(cipher, key)
    if any(
        value is not None
        for value in (interruptors_exact, interruptors_pool, interruptors_max)
    ):
        raise ValueError(
            "typed interruptors cannot be combined with legacy interruptor inputs"
        )
    template_cfg = materialize_cipher_config(
        cipher=cipher,
        key_space=key,
        ciphertext=ciphertext,
        word_lengths=wli,
        compute_device=(
            ComputeDevice.CUDA if device is Device.CUDA else ComputeDevice.CPU
        ),
        text_direction=(
            TextDirection.LEFT_TO_RIGHT
            if direction is Direction.LTR
            else TextDirection.RIGHT_TO_LEFT
        ),
        text_permutation=None,
        initial_keys=None,
        interruptors=interruptors,
    )
    interruptor_cfg = template_cfg.interruptors_cfg
    interruptor_hypotheses = _resolve_interruptor_hypotheses(
        interruptor_cfg,
        len(ciphertext),
    )
    # Candidate-position validity is a caller contract, not a structural-hypothesis rejection.
    _validate_candidate_position_contract(wli, request, direction)
    branch_list: list[TwoPeriodBranch] = []
    rejection_list: list[dict[str, Any]] = []
    for resolved_interruptors in interruptor_hypotheses:
        try:
            resolved_branches, resolved_rejections = build_branches(
                ciphertext,
                wli,
                request,
                period_a=period_a,
                period_b=period_b,
                modulus=modulus,
                direction=direction,
                interruptors=resolved_interruptors,
            )
        except ValueError as exc:
            if (
                interruptor_cfg is None
                or interruptor_cfg.mode is not InterruptorMode.SEARCH
            ):
                raise
            rejection_list.append(
                {
                    "word": None,
                    "start": None,
                    "interruptors": list(resolved_interruptors),
                    "reason": str(exc),
                }
            )
            continue
        branch_list.extend(resolved_branches)
        rejection_list.extend(
            {
                **row,
                "interruptors": list(resolved_interruptors),
            }
            for row in resolved_rejections
        )
    if not branch_list:
        reasons = "; ".join(
            f"interruptors={row.get('interruptors', [])}: {row['reason']}"
            for row in rejection_list
        )
        detail = f": {reasons}" if reasons else ""
        raise ValueError(
            f"no compatible two-period interruptor/crib branches remain{detail}"
        )
    branches = tuple(sorted(branch_list, key=lambda branch: branch.branch_id))
    rejections = tuple(rejection_list)
    total_evaluations = 0
    all_union: dict[str, dict[str, Any]] = {}
    branch_summaries: list[dict[str, Any]] = []
    stage_summaries: list[dict[str, Any]] = []
    candidate_counts = {
        "scout_inputs": 0,
        "scout_generated_terminals": 0,
        "scout_unique_terminals": 0,
        "scout_duplicates": 0,
        "bridge_inputs": 0,
        "bridge_generated_terminals": 0,
        "bridge_unique_terminals": 0,
        "bridge_duplicates": 0,
        "judge_inputs": 0,
        "judge_generated_terminals": 0,
        "judge_unique_terminals": 0,
        "judge_duplicates": 0,
        "final_union_inputs": 0,
        "final_union_generated_terminals": 0,
        "final_union_unique_terminals": 0,
        "final_union_duplicates": 0,
    }
    final_problem: DecryptionProblem | None = None
    for branch in branches:
        fixed_characters = {
            span.start + offset: [int(value)]
            for span in branch.spans
            for offset, value in enumerate(span.runes)
        }
        hard_crib = HardCribConfig(enabled=True, fixed_characters=fixed_characters)
        problems: dict[str, DecryptionProblem] = {}
        branch_interruptors = (
            None
            if not branch.interruptors
            else InterruptorConfig.exact(branch.interruptors)
        )
        for profile_id in ("S2", "B1", "F1"):
            scoring = _profile(profile_id, hard_crib, direction)
            cipher_cfg = materialize_cipher_config(
                cipher=cipher,
                key_space=key,
                ciphertext=ciphertext,
                word_lengths=wli,
                compute_device=(
                    ComputeDevice.CUDA if device is Device.CUDA else ComputeDevice.CPU
                ),
                text_direction=(
                    TextDirection.LEFT_TO_RIGHT
                    if direction is Direction.LTR
                    else TextDirection.RIGHT_TO_LEFT
                ),
                initial_keys=None,
                text_permutation=None,
                interruptors=branch_interruptors,
            )
            problems[profile_id] = DecryptionProblem(
                cipher=build_cipher(cipher_cfg),
                scorer=build_scorer(cipher_cfg, scoring),
                c_cfg=cipher_cfg,
                s_cfg=scoring,
                enable_telemetry=telemetry_on,
            )

        def evaluator(profile_id: str) -> Callable[[np.ndarray], np.ndarray]:
            def evaluate(values: np.ndarray) -> np.ndarray:
                keys = expand_reduced_key(values, branch.constraint_space)
                if keys.ndim == 1:
                    keys = keys[None, :]
                return np.asarray(
                    problems[profile_id].evaluate_keys(keys), dtype=np.float64
                )

            return evaluate

        scout: dict[str, dict[str, Any]] = {}
        scout_started = time.perf_counter()
        scout_evaluations = 0
        scout_seeds = [
            derive_child_seed(request.effective_seed, branch.branch_id, "S2", index)
            for index in range(request.starts)
        ]
        for start_index in range(request.starts):
            rng = np.random.default_rng(scout_seeds[start_index])
            initial = rng.integers(
                0, modulus, size=branch.constraint_space.dimension, dtype=np.uint8
            )
            search_result = _coordinate_search_with_status(
                evaluator("S2"), rng, initial, 5, modulus=modulus
            )
            variables = search_result.variables
            score = search_result.score
            used = search_result.evaluations
            total_evaluations += used
            scout_evaluations += used
            expanded = expand_reduced_key(variables, branch.constraint_space)
            candidate_id = _candidate_id(expanded, branch.interruptors)
            record = {
                "candidate_id": candidate_id,
                "branch_id": branch.branch_id,
                "interruptors": list(branch.interruptors),
                "variables": variables.astype(int).tolist(),
                "key": expanded.astype(int).tolist(),
                "scout_score": score,
                "source_stage": "S2",
                "search_stop_reason": search_result.stop_reason.value,
            }
            old = scout.get(candidate_id)
            if old is None or score > old["scout_score"]:
                scout[candidate_id] = record
        scout_elapsed = time.perf_counter() - scout_started
        scout_best = max(float(record["scout_score"]) for record in scout.values())
        scout_stop_reason = _stage_stop_reason(tuple(scout.values()))
        candidate_counts["scout_inputs"] += request.starts
        candidate_counts["scout_generated_terminals"] += request.starts
        candidate_counts["scout_unique_terminals"] += len(scout)
        candidate_counts["scout_duplicates"] += request.starts - len(scout)
        stage_summaries.append(
            {
                "branch_id": branch.branch_id,
                "stage_id": "S2",
                "profile_id": "s2_wli12",
                "inputs": request.starts,
                "generated_terminals": request.starts,
                "unique_terminals": len(scout),
                "duplicates": request.starts - len(scout),
                "evaluations": scout_evaluations,
                "elapsed_s": scout_elapsed,
                "stop_category": _stage_stop_category(scout_stop_reason),
                "stop_reason": scout_stop_reason.value,
                "legacy_stop_reason": "done",
                "best_score": scout_best,
                "input_seed_digest": hashlib.sha256(
                    json.dumps(scout_seeds, separators=(",", ":")).encode("ascii")
                ).hexdigest(),
                "terminal_digest": _records_digest(
                    [
                        (candidate_id, record["scout_score"])
                        for candidate_id, record in scout.items()
                    ]
                ),
            }
        )

        bridge, bridge_evaluations, bridge_elapsed = _run_refinement_stage(
            stage_id="B1",
            score_field="bridge_score",
            evaluate=evaluator("B1"),
            branch=branch,
            inputs=scout,
            sweeps=4,
            root_seed=request.effective_seed,
            modulus=modulus,
        )
        total_evaluations += bridge_evaluations
        bridge_best = max(float(record["bridge_score"]) for record in bridge.values())
        bridge_stop_reason = _stage_stop_reason(tuple(bridge.values()))
        candidate_counts["bridge_inputs"] += len(scout)
        candidate_counts["bridge_generated_terminals"] += len(scout)
        candidate_counts["bridge_unique_terminals"] += len(bridge)
        candidate_counts["bridge_duplicates"] += len(scout) - len(bridge)
        stage_summaries.append(
            {
                "branch_id": branch.branch_id,
                "stage_id": "B1",
                "profile_id": "b1_char23_wli23",
                "inputs": len(scout),
                "generated_terminals": len(scout),
                "unique_terminals": len(bridge),
                "duplicates": len(scout) - len(bridge),
                "evaluations": bridge_evaluations,
                "elapsed_s": bridge_elapsed,
                "stop_category": _stage_stop_category(bridge_stop_reason),
                "stop_reason": bridge_stop_reason.value,
                "legacy_stop_reason": "done",
                "best_score": bridge_best,
                "terminal_digest": _records_digest(
                    [
                        (candidate_id, record["bridge_score"])
                        for candidate_id, record in bridge.items()
                    ]
                ),
            }
        )

        judge_inputs = _deduplicated_union(scout, bridge)
        judge, judge_evaluations, judge_elapsed = _run_refinement_stage(
            stage_id="F1",
            score_field="judge_score",
            evaluate=evaluator("F1"),
            branch=branch,
            inputs=judge_inputs,
            sweeps=3,
            root_seed=request.effective_seed,
            modulus=modulus,
        )
        total_evaluations += judge_evaluations
        judge_best = max(float(record["judge_score"]) for record in judge.values())
        judge_stop_reason = _stage_stop_reason(tuple(judge.values()))
        candidate_counts["judge_inputs"] += len(judge_inputs)
        candidate_counts["judge_generated_terminals"] += len(judge_inputs)
        candidate_counts["judge_unique_terminals"] += len(judge)
        candidate_counts["judge_duplicates"] += len(judge_inputs) - len(judge)
        stage_summaries.append(
            {
                "branch_id": branch.branch_id,
                "stage_id": "F1",
                "profile_id": "f1_char1234_wli1234",
                "inputs": len(judge_inputs),
                "generated_terminals": len(judge_inputs),
                "unique_terminals": len(judge),
                "duplicates": len(judge_inputs) - len(judge),
                "evaluations": judge_evaluations,
                "elapsed_s": judge_elapsed,
                "stop_category": _stage_stop_category(judge_stop_reason),
                "stop_reason": judge_stop_reason.value,
                "legacy_stop_reason": "done",
                "best_score": judge_best,
                "sweeps": 3,
                "mode": "coordinate_search",
                "terminal_digest": _records_digest(
                    [
                        (candidate_id, record["judge_score"])
                        for candidate_id, record in judge.items()
                    ]
                ),
            }
        )

        final_union = _deduplicated_union(scout, bridge, judge)
        ordered_ids = sorted(final_union)
        keys = np.asarray(
            [final_union[candidate_id]["key"] for candidate_id in ordered_ids],
            dtype=np.uint8,
        )
        final_started = time.perf_counter()
        scores = np.asarray(problems["F1"].evaluate_keys(keys), dtype=np.float64)
        if scores.shape != (len(keys),) or not np.all(np.isfinite(scores)):
            raise RuntimeError("final F1 evaluator returned invalid scores")
        final_elapsed = time.perf_counter() - final_started
        total_evaluations += len(keys)
        for candidate_id, score in zip(ordered_ids, scores):
            record = dict(final_union[candidate_id])
            record["final_score"] = float(score)
            previous = all_union.get(candidate_id)
            if (
                previous is None
                or float(score) > float(previous["final_score"]) + _EPSILON
                or (
                    abs(float(score) - float(previous["final_score"])) <= _EPSILON
                    and record["branch_id"] < previous["branch_id"]
                )
            ):
                all_union[candidate_id] = record
        candidate_counts["final_union_inputs"] += len(final_union)
        stage_summaries.append(
            {
                "branch_id": branch.branch_id,
                "stage_id": "final_union",
                "profile_id": "f1_char1234_wli1234",
                "inputs": len(final_union),
                "generated_terminals": 0,
                "unique_terminals": len(final_union),
                "duplicates": 0,
                "evaluations": len(final_union),
                "elapsed_s": final_elapsed,
                "stop_category": StopCategory.BUDGET.value,
                "stop_reason": StopReason.STATIC_RESCORE_COMPLETED.value,
                "legacy_stop_reason": "done",
                "best_score": float(np.max(scores)),
                "mode": "static_rescore",
                "terminal_digest": _records_digest(
                    list(zip(ordered_ids, (float(score) for score in scores)))
                ),
            }
        )
        branch_summaries.append(
            {
                "branch_id": branch.branch_id,
                "interruptors": list(branch.interruptors),
                "interruptor_count": len(branch.interruptors),
                "candidate_word": None
                if branch.candidate_crib is None
                else branch.candidate_crib.word,
                "candidate_start": None
                if branch.candidate_crib is None
                else branch.candidate_crib.start,
                "affine_dimension": branch.constraint_space.dimension,
                "scout_unique": len(scout),
                "bridge_unique": len(bridge),
                "judge_unique": len(judge),
                "final_union_unique": len(final_union),
            }
        )
        final_problem = problems["F1"]

    if not all_union or final_problem is None:
        raise RuntimeError("two_period_cribs produced no candidates")
    ranked = sorted(
        all_union.values(),
        key=lambda row: (
            -float(row["final_score"]),
            tuple(row["key"]),
            row["branch_id"],
        ),
    )
    best = ranked[0]
    best_key = np.asarray(best["key"], dtype=np.uint8)
    plaintext = build_cipher(template_cfg).decrypt_single(
        ciphertext=ciphertext,
        key=best_key,
        interrupt_idx=(None if not best["interruptors"] else best["interruptors"]),
    )
    elapsed = time.perf_counter() - started
    candidate_counts["final_union_unique_terminals"] = len(all_union)
    candidate_counts["final_union_duplicates"] = candidate_counts[
        "final_union_inputs"
    ] - len(all_union)
    winning_branch = next(
        item for item in branch_summaries if item["branch_id"] == best["branch_id"]
    )
    profile_hashes = {
        profile_id: profile_contract_hash(profile_id)
        for profile_id in ("S2", "B1", "F1")
    }
    metadata = {
        "contract": TWO_PERIOD_CRIBS_CONTRACT,
        "execution_route": "two_period_cribs",
        "requested_seed": request.requested_seed,
        "effective_seed": request.effective_seed,
        "period_a": period_a,
        "period_b": period_b,
        "gauge": {"stream": "B", "index": 0, "value": 0},
        "interruptors": {
            "requested": (
                {"mode": "disabled"}
                if interruptor_cfg is None
                else interruptor_cfg.to_dict()
            ),
            "resolution": "structural",
            "hypothesis_count": len(interruptor_hypotheses),
            "winning_positions": list(best["interruptors"]),
            "winning_count": len(best["interruptors"]),
        },
        "branch_count": len(branches),
        "rejected_branch_count": len(rejections),
        "rejected_branches": list(rejections),
        "branches": branch_summaries,
        "key_a": best_key[:period_a].astype(int).tolist(),
        "key_b": best_key[period_a:].astype(int).tolist(),
        "winning_branch": winning_branch,
        "derived_dimension": winning_branch["affine_dimension"],
        "profile_hashes": profile_hashes,
        "stage_summaries": stage_summaries,
        "candidate_counts": candidate_counts,
        "profiles": {
            profile_id: {
                "contract_hash": profile_hashes[profile_id],
                "role": {"S2": "scout", "B1": "bridge", "F1": "judge"}[profile_id],
                "sweeps": {"S2": 5, "B1": 4, "F1": 3}[profile_id],
            }
            for profile_id in ("S2", "B1", "F1")
        },
        "final_union_count": len(all_union),
        "best_candidate_id": best["candidate_id"],
        "best_branch_id": best["branch_id"],
        "split_key": {
            "A": best_key[:period_a].astype(int).tolist(),
            "B": best_key[period_a:].astype(int).tolist(),
        },
        "evaluation_count": total_evaluations,
    }
    solution = Solution(
        key=best_key.astype(int).tolist(),
        plaintext=np.asarray(plaintext, dtype=np.uint8).astype(int).tolist(),
        score=float(best["final_score"]),
        meta={"two_period_solve": metadata},
        evals=total_evaluations,
        step=(
            candidate_counts["scout_generated_terminals"]
            + candidate_counts["bridge_generated_terminals"]
            + candidate_counts["judge_generated_terminals"]
        ),
        wall_time_s=elapsed,
        stop_reason=StopReason.CONFIGURED_WORK_LIMIT_REACHED.value,
        device=device,
        direction=direction,
    )
    return finalize_solution(
        final_problem,
        solution,
        ciphertext=ciphertext,
        wli=wli,
        cipher=cipher,
        encoding_dir=direction,
        telemetry_on=telemetry_on,
        pipeline_block={
            "text_encoding_direction": direction.value,
            "input_permutation": {
                "kind": "none",
                "length": len(ciphertext),
                "hash": "",
            },
            "solver_route": "two_period_cribs",
        },
    )


__all__ = [
    "CribConstraintSpace",
    "CribSpan",
    "TwoPeriodBranch",
    "build_branches",
    "coordinate_search",
    "derive_child_seed",
    "derive_constraint_space",
    "expand_reduced_key",
    "profile_contract_hash",
    "rref_mod",
    "run_two_period_stages",
]
