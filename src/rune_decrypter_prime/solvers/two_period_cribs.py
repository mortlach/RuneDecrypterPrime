from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Sequence

import numpy as np

from rune_decrypter_prime.api.pipeline_helpers import finalize_solution
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
from rune_decrypter_prime.api.two_period_cribs import (
    TWO_PERIOD_CRIBS_CONTRACT,
    TwoPeriodCribsRequest,
)
from rune_decrypter_prime.api.wrappers.by_name import cipher_instance
from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
from rune_decrypter_prime.core.config import HardCribConfig, ScoringConfig, Solution
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.types import Device, Direction
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

    @property
    def spans(self) -> tuple[CribSpan, ...]:
        return self.fixed_cribs + (() if self.candidate_crib is None else (self.candidate_crib,))


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
) -> CribConstraintSpace:
    key_length = period_a + period_b
    rows: list[np.ndarray] = []
    for span in spans:
        if span.start < 0 or span.stop > len(ciphertext):
            raise ValueError(f"crib {span.word!r} lies outside the ciphertext")
        for offset, plain in enumerate(span.runes):
            position = span.start + offset
            row = np.zeros(key_length + 1, dtype=np.int64)
            row[position % period_a] = 1
            row[period_a + position % period_b] = 1
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
        if tuple((int(a), int(b)) for a, b in wli[start:start + length]) == tuple(
            (offset, length) for offset in range(length)
        ):
            starts.append(start)
    return tuple(starts)


def _branch_id(spans: Sequence[CribSpan], space: CribConstraintSpace) -> str:
    payload = {
        "contract": TWO_PERIOD_CRIBS_CONTRACT,
        "spans": sorted((list(span.runes), span.start) for span in spans),
        "particular": list(space.particular),
        "basis": [list(row) for row in space.basis],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return f"tpb_{digest}"


def build_branches(
    ciphertext: np.ndarray,
    wli: Sequence[Sequence[int]],
    request: TwoPeriodCribsRequest,
    *,
    period_a: int,
    period_b: int,
    modulus: int,
    direction: Direction,
) -> tuple[tuple[TwoPeriodBranch, ...], tuple[dict[str, Any], ...]]:
    fixed = tuple(_span(word, start, direction) for word, start in request.fixed_cribs)
    # Fixed evidence is authoritative: contradictions are a caller error.
    derive_constraint_space(
        ciphertext, fixed, period_a=period_a, period_b=period_b, modulus=modulus
    )
    alternatives: list[CribSpan | None] = []
    if not request.candidate_words:
        alternatives.append(None)
    for word in request.candidate_words:
        runes = _span(word, 0, direction).runes
        positions = request.positions_for(word)
        if positions is None:
            positions = _complete_word_starts(wli, len(runes))
        alternatives.extend(CribSpan(word, runes, start) for start in positions)

    accepted: dict[str, TwoPeriodBranch] = {}
    rejected: list[dict[str, Any]] = []
    for candidate in alternatives:
        spans = fixed + (() if candidate is None else (candidate,))
        try:
            space = derive_constraint_space(
                ciphertext,
                spans,
                period_a=period_a,
                period_b=period_b,
                modulus=modulus,
            )
        except ValueError as exc:
            rejected.append({
                "word": None if candidate is None else candidate.word,
                "start": None if candidate is None else candidate.start,
                "reason": str(exc),
            })
            continue
        branch_id = _branch_id(spans, space)
        accepted.setdefault(branch_id, TwoPeriodBranch(branch_id, fixed, candidate, space))
    if not accepted:
        raise ValueError("no compatible two-period crib branches remain")
    return tuple(accepted[key] for key in sorted(accepted)), tuple(rejected)


def derive_child_seed(root_seed: int, *parts: object) -> int:
    payload = ":".join((str(root_seed), TWO_PERIOD_CRIBS_CONTRACT, *(str(x) for x in parts)))
    return int.from_bytes(
        hashlib.blake2b(payload.encode("utf-8"), digest_size=8, person=b"rdp-tp-cribs").digest(),
        "big",
    )


def coordinate_search(
    evaluate: Callable[[np.ndarray], np.ndarray],
    rng: np.random.Generator,
    variables: np.ndarray,
    sweeps: int,
    *,
    modulus: int = 29,
) -> tuple[np.ndarray, float, int]:
    current = np.asarray(variables, dtype=np.uint8).copy()
    current_score = float(np.asarray(evaluate(current[None, :]), dtype=np.float64)[0])
    evaluations = 1
    for _ in range(sweeps):
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
            break
    return current, current_score, evaluations


def _profile(profile_id: str, hard_crib: HardCribConfig, direction: Direction) -> ScoringConfig:
    profiles = {
        "S2": (False, True, (), (1, 2), 0.0, 1.0),
        "B1": (True, True, (2, 3), (2, 3), 0.25, 0.75),
        "F1": (True, True, (1, 2, 3, 4), (1, 2, 3, 4), 0.25, 0.75),
    }
    include_char, use_wli, char_orders, wli_orders, char_total, wli_total = profiles[profile_id]
    return ScoringConfig(
        objective="pct.logp.win10",
        include_char=include_char,
        use_word_breaks=use_wli,
        n_char=max(char_orders, default=1),
        n_wli=max(wli_orders, default=1),
        char_weights={} if not char_orders else {order: char_total / len(char_orders) for order in char_orders},
        wli_weights={} if not wli_orders else {order: wli_total / len(wli_orders) for order in wli_orders},
        weights=(char_total, wli_total),
        encoding_dir=direction,
        hard_crib=hard_crib,
    )


def profile_contract_hash(profile_id: str) -> str:
    cfg = _profile(profile_id, HardCribConfig(enabled=False), Direction.LTR)
    payload = {
        "profile": profile_id,
        "include_char": cfg.include_char,
        "use_word_breaks": cfg.use_word_breaks,
        "n_char": cfg.n_char,
        "n_wli": cfg.n_wli,
        "char_weights": cfg.char_weights,
        "wli_weights": cfg.wli_weights,
        "weights": cfg.weights,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _candidate_id(key: np.ndarray) -> str:
    return "tpc_" + hashlib.sha256(bytes(np.asarray(key, dtype=np.uint8))).hexdigest()[:20]


def _records_digest(records: Sequence[tuple[str, float]]) -> str:
    payload = [[candidate_id, float(score).hex()] for candidate_id, score in sorted(records)]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_cipher(cipher: CipherSpec, key: KeySpec) -> tuple[int, int, int]:
    if not isinstance(cipher, CipherSpec) or cipher.kind != "wrapper":
        raise ValueError("two_period_cribs requires the scheduled_stream_lookup wrapper")
    if cipher.wrapper_core != "scheduled_stream_lookup":
        raise ValueError("two_period_cribs requires scheduled_stream_lookup")
    extra = dict(cipher.extra or {})
    allowed = {"streams", "schedule", "operation", "alphabet_size"}
    unsupported = sorted(set(extra) - allowed)
    if unsupported:
        raise ValueError(f"unsupported two-period cipher options: {unsupported}")
    streams = extra.get("streams")
    if not isinstance(streams, list) or len(streams) != 2:
        raise ValueError("two_period_cribs requires exactly two streams")
    periods: list[int] = []
    for expected_name, stream in zip(("A", "B"), streams):
        if not isinstance(stream, dict) or str(stream.get("kind", "")).lower() != "periodic":
            raise ValueError("two_period_cribs requires two periodic streams")
        stream_extra = sorted(set(stream) - {"name", "kind", "period"})
        if stream_extra:
            raise ValueError(f"unsupported two-period stream options: {stream_extra}")
        if str(stream.get("name", expected_name)) != expected_name:
            raise ValueError("two-period streams must be ordered A then B")
        periods.append(int(stream.get("period", 0)))
    if any(period <= 0 for period in periods):
        raise ValueError("two-period stream periods must be positive")
    modulus = int(extra.get("alphabet_size", cipher.N))
    if modulus != 29:
        raise ValueError("two_period_cribs currently requires the prime runic modulus 29")
    if str(extra.get("schedule", "")) != "overlay" or str(extra.get("operation", "")) != "add":
        raise ValueError("two_period_cribs requires additive overlay scheduling")
    if not isinstance(key, KeySpec) or key.plan != "repeat":
        raise ValueError("two_period_cribs requires a repeating canonical key")
    if int(key.params.get("len", 0)) != sum(periods):
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
) -> Solution:
    started = time.perf_counter()
    period_a, period_b, modulus = _validate_cipher(cipher, key)
    branches, rejections = build_branches(
        ciphertext,
        wli,
        request,
        period_a=period_a,
        period_b=period_b,
        modulus=modulus,
        direction=direction,
    )
    cipher_obj = cipher_instance(cipher)
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
        "final_inputs": 0,
        "final_generated_terminals": 0,
        "final_unique_terminals": 0,
        "final_duplicates": 0,
    }
    final_problem: DecryptionProblem | None = None

    for branch in branches:
        fixed_chars = {
            span.start + offset: [int(value)]
            for span in branch.spans
            for offset, value in enumerate(span.runes)
        }
        hard_crib = HardCribConfig(enabled=True, fixed_chars=fixed_chars)
        problems: dict[str, DecryptionProblem] = {}
        for profile_id in ("S2", "B1", "F1"):
            scoring = _profile(profile_id, hard_crib, direction)
            cipher_cfg = build_cipher_config(
                cipher=cipher,
                key=key,
                ciphertext=ciphertext,
                wli=wli,
                device=device,
                encoding_dir=direction,
                initial_text_permutation_indices=None,
                initial_keys=None,
                interruptors=None,
                interruptors_exact=None,
                interruptors_pool=None,
                interruptors_max=None,
            )
            problems[profile_id] = DecryptionProblem(
                cipher=cipher_obj,
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
                return np.asarray(problems[profile_id].evaluate_keys(keys), dtype=np.float64)
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
            variables, score, used = coordinate_search(
                evaluator("S2"), rng, initial, 5, modulus=modulus
            )
            total_evaluations += used
            scout_evaluations += used
            expanded = expand_reduced_key(variables, branch.constraint_space)
            candidate_id = _candidate_id(expanded)
            record = {
                "candidate_id": candidate_id,
                "branch_id": branch.branch_id,
                "variables": variables.astype(int).tolist(),
                "key": expanded.astype(int).tolist(),
                "scout_score": score,
                "source_stage": "S2",
            }
            old = scout.get(candidate_id)
            if old is None or score > old["scout_score"]:
                scout[candidate_id] = record
        scout_elapsed = time.perf_counter() - scout_started
        scout_best = max(float(record["scout_score"]) for record in scout.values())
        candidate_counts["scout_inputs"] += request.starts
        candidate_counts["scout_generated_terminals"] += request.starts
        candidate_counts["scout_unique_terminals"] += len(scout)
        candidate_counts["scout_duplicates"] += request.starts - len(scout)
        stage_summaries.append({
            "branch_id": branch.branch_id,
            "stage_id": "S2",
            "profile_id": "s2_wli12",
            "inputs": request.starts,
            "generated_terminals": request.starts,
            "unique_terminals": len(scout),
            "duplicates": request.starts - len(scout),
            "evaluations": scout_evaluations,
            "elapsed_s": scout_elapsed,
            "stop_reason": "done",
            "best_score": scout_best,
            "input_seed_digest": hashlib.sha256(
                json.dumps(scout_seeds, separators=(",", ":")).encode("ascii")
            ).hexdigest(),
            "terminal_digest": _records_digest(
                [(candidate_id, record["scout_score"]) for candidate_id, record in scout.items()]
            ),
        })

        bridge: dict[str, dict[str, Any]] = {}
        bridge_started = time.perf_counter()
        bridge_evaluations = 0
        for parent_id in sorted(scout):
            parent = scout[parent_id]
            rng = np.random.default_rng(
                derive_child_seed(request.effective_seed, branch.branch_id, "B1", parent_id)
            )
            variables, score, used = coordinate_search(
                evaluator("B1"),
                rng,
                np.asarray(parent["variables"], dtype=np.uint8),
                4,
                modulus=modulus,
            )
            total_evaluations += used
            bridge_evaluations += used
            expanded = expand_reduced_key(variables, branch.constraint_space)
            candidate_id = _candidate_id(expanded)
            record = {
                "candidate_id": candidate_id,
                "branch_id": branch.branch_id,
                "variables": variables.astype(int).tolist(),
                "key": expanded.astype(int).tolist(),
                "bridge_score": score,
                "source_stage": "B1",
                "parent_id": parent_id,
            }
            old = bridge.get(candidate_id)
            if old is None or score > old["bridge_score"]:
                bridge[candidate_id] = record
        bridge_elapsed = time.perf_counter() - bridge_started
        bridge_best = max(float(record["bridge_score"]) for record in bridge.values())
        candidate_counts["bridge_inputs"] += len(scout)
        candidate_counts["bridge_generated_terminals"] += len(scout)
        candidate_counts["bridge_unique_terminals"] += len(bridge)
        candidate_counts["bridge_duplicates"] += len(scout) - len(bridge)
        stage_summaries.append({
            "branch_id": branch.branch_id,
            "stage_id": "B1",
            "profile_id": "b1_char23_wli23",
            "inputs": len(scout),
            "generated_terminals": len(scout),
            "unique_terminals": len(bridge),
            "duplicates": len(scout) - len(bridge),
            "evaluations": bridge_evaluations,
            "elapsed_s": bridge_elapsed,
            "stop_reason": "done",
            "best_score": bridge_best,
            "terminal_digest": _records_digest(
                [(candidate_id, record["bridge_score"]) for candidate_id, record in bridge.items()]
            ),
        })

        union = dict(scout)
        for candidate_id, record in bridge.items():
            union.setdefault(candidate_id, record)
        ordered_ids = sorted(union)
        keys = np.asarray([union[candidate_id]["key"] for candidate_id in ordered_ids], dtype=np.uint8)
        final_started = time.perf_counter()
        scores = np.asarray(problems["F1"].evaluate_keys(keys), dtype=np.float64)
        final_elapsed = time.perf_counter() - final_started
        total_evaluations += len(keys)
        for candidate_id, score in zip(ordered_ids, scores):
            record = dict(union[candidate_id])
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
        candidate_counts["final_inputs"] += len(union)
        candidate_counts["final_unique_terminals"] += len(union)
        stage_summaries.append({
            "branch_id": branch.branch_id,
            "stage_id": "F1",
            "profile_id": "f1_char1234_wli1234",
            "inputs": len(union),
            "generated_terminals": 0,
            "unique_terminals": len(union),
            "duplicates": 0,
            "evaluations": len(union),
            "elapsed_s": final_elapsed,
            "stop_reason": "done",
            "best_score": float(np.max(scores)),
            "mode": "static_rescore",
            "terminal_digest": _records_digest(
                list(zip(ordered_ids, (float(score) for score in scores)))
            ),
        })
        branch_summaries.append({
            "branch_id": branch.branch_id,
            "candidate_word": None if branch.candidate_crib is None else branch.candidate_crib.word,
            "candidate_start": None if branch.candidate_crib is None else branch.candidate_crib.start,
            "affine_dimension": branch.constraint_space.dimension,
            "scout_unique": len(scout),
            "bridge_unique": len(bridge),
            "final_union_unique": len(union),
        })
        final_problem = problems["F1"]

    if not all_union or final_problem is None:
        raise RuntimeError("two_period_cribs produced no candidates")
    ranked = sorted(
        all_union.values(),
        key=lambda row: (-float(row["final_score"]), tuple(row["key"]), row["branch_id"]),
    )
    best = ranked[0]
    best_key = np.asarray(best["key"], dtype=np.uint8)
    plaintext = final_problem.resolve_plaintext(best_key)
    if plaintext is None:
        plaintext = cipher_obj.decrypt_single(ciphertext=ciphertext, key=best_key)
    elapsed = time.perf_counter() - started
    candidate_counts["final_unique_terminals"] = len(all_union)
    candidate_counts["final_duplicates"] = candidate_counts["final_inputs"] - len(all_union)
    winning_branch = next(
        item for item in branch_summaries if item["branch_id"] == best["branch_id"]
    )
    profile_hashes = {
        profile_id: profile_contract_hash(profile_id) for profile_id in ("S2", "B1", "F1")
    }
    metadata = {
        "contract": TWO_PERIOD_CRIBS_CONTRACT,
        "execution_route": "two_period_cribs",
        "requested_seed": request.requested_seed,
        "effective_seed": request.effective_seed,
        "period_a": period_a,
        "period_b": period_b,
        "gauge": {"stream": "B", "index": 0, "value": 0},
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
                "role": {"S2": "scout", "B1": "bridge", "F1": "static_final"}[profile_id],
                "sweeps": {"S2": 5, "B1": 4, "F1": 0}[profile_id],
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
        step=request.starts * len(branches),
        wall_time_s=elapsed,
        stop_reason="done",
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
            "input_permutation": {"kind": "none", "length": len(ciphertext), "hash": ""},
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
