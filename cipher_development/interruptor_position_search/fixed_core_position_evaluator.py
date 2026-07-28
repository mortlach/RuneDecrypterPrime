from __future__ import annotations

import hashlib
import inspect
from typing import Any, Sequence

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, by_name
from rune_decrypter_prime.api._resolve import resolve_scorer_aliases
from rune_decrypter_prime.api.normalize import normalize_scorer_params
from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
from rune_decrypter_prime.core.config import ScoringConfig
from rune_decrypter_prime.core.problem import ProblemInstance, ProblemSpec
from rune_decrypter_prime.core.types import Device, KEY_DTYPE

from .benchmark import InterruptorBenchmark
from .config import (
    DIRECTION,
    MAX_INTERRUPT_COUNT,
    MIN_INTERRUPT_COUNT,
    SCORER_PARAMS,
)

Subset = tuple[int, ...]


def _hash_ints(values: Sequence[int]) -> str:
    payload = ",".join(str(int(value)) for value in values).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


class FixedCorePositionEvaluator:
    """Score interruptor subsets while keeping the ordinary core key immutable."""

    def __init__(
        self,
        problem: Any,
        core_key: Sequence[int],
        pool: Sequence[int],
        min_count: int,
        max_count: int,
    ) -> None:
        self.problem = problem
        self.core_key = np.asarray(tuple(core_key), dtype=KEY_DTYPE).copy()
        self.core_key.setflags(write=False)
        self.pool = tuple(sorted(int(value) for value in pool))
        self.pool_set = frozenset(self.pool)
        self.min_count = int(min_count)
        self.max_count = int(max_count)
        self.used_test_key = False
        self.used_true_positions = False
        self.prefix_verified = False
        self.score_ledger: dict[Subset, float] = {}

        keyops = problem.keyops
        if int(getattr(keyops, "core_K", -1)) != len(self.core_key):
            raise ValueError("problem composite-key core length does not match fixed key")
        if int(getattr(keyops, "interrupt_K", -1)) != self.max_count:
            raise ValueError("problem composite-key tail length does not match max_count")
        if int(getattr(keyops, "interrupt_min", -1)) != self.min_count:
            raise ValueError("problem composite-key minimum count does not match")
        if tuple(int(v) for v in keyops.pool.tolist()) != self.pool:
            raise ValueError("problem composite-key pool does not match the declared pool")

        self.sentinel = int(keyops.sentinel)
        if self.sentinel >= 0:
            raise ValueError("canonical composite-key sentinel must be negative")
        self.encoder_identity = (
            f"{keyops.__class__.__module__}.{keyops.__class__.__qualname__}.normalize"
        )
        source = (inspect.getsourcefile(keyops.__class__) or "").replace("\\", "/")
        marker = "/src/rune_decrypter_prime/"
        self.encoder_source = (
            f"src/rune_decrypter_prime/{source.split(marker, 1)[1]}"
            if marker in source
            else source.rsplit("/", 1)[-1]
        )

    def _validate_subset(self, subset: Sequence[int]) -> Subset:
        candidate = tuple(int(value) for value in subset)
        if candidate != tuple(sorted(candidate)):
            raise ValueError("interruptor positions must be sorted")
        if len(set(candidate)) != len(candidate):
            raise ValueError("interruptor positions must be unique")
        if not self.min_count <= len(candidate) <= self.max_count:
            raise ValueError("interruptor position count is outside the search range")
        if any(value not in self.pool_set for value in candidate):
            raise ValueError("interruptor position is outside the full pool")
        return candidate

    def encode_subsets(self, subsets: Sequence[Sequence[int]]) -> np.ndarray:
        canonical = tuple(self._validate_subset(subset) for subset in subsets)
        if not canonical:
            return np.empty(
                (0, len(self.core_key) + self.max_count),
                dtype=KEY_DTYPE,
            )
        raw_rows = []
        for subset in canonical:
            tail = (*subset, *(self.sentinel,) * (self.max_count - len(subset)))
            raw_rows.append(np.asarray((*self.core_key.tolist(), *tail), dtype=KEY_DTYPE))
        encoded = np.asarray(self.problem.keyops.normalize(np.stack(raw_rows)), dtype=KEY_DTYPE)
        expected = np.tile(self.core_key, (len(canonical), 1))
        if not np.array_equal(encoded[:, : len(self.core_key)], expected):
            raise RuntimeError("canonical encoder changed the immutable core-key prefix")
        self.prefix_verified = True
        return np.ascontiguousarray(encoded, dtype=KEY_DTYPE)

    def score_subsets(self, subsets: tuple[Subset, ...]) -> np.ndarray:
        encoded = self.encode_subsets(subsets)
        scores = np.asarray(self.problem.evaluate_keys(encoded), dtype=np.float64)
        if scores.shape != (len(subsets),):
            raise ValueError("normal problem evaluator returned an unexpected score shape")
        if not np.all(np.isfinite(scores)):
            raise ValueError("normal problem evaluator returned a non-finite score")
        for subset, score in zip(subsets, scores.tolist()):
            self.score_ledger[self._validate_subset(subset)] = float(score)
        return scores

    def resolve_plaintext(self, subset: Sequence[int]) -> tuple[int, ...]:
        encoded = self.encode_subsets((tuple(subset),))
        plains = self.problem._decrypt_batch(encoded)
        if len(plains) != 1:
            raise RuntimeError("normal problem path did not resolve exactly one plaintext")
        return tuple(int(value) for value in np.asarray(plains[0]).reshape(-1).tolist())

    def context(self) -> dict[str, Any]:
        return {
            "fixed_core_key_sha256": _hash_ints(self.core_key.tolist()),
            "pool_sha256": _hash_ints(self.pool),
            "pool_size": len(self.pool),
            "min_count": self.min_count,
            "max_count": self.max_count,
            "canonical_encoder_identity": self.encoder_identity,
            "canonical_encoder_source": self.encoder_source,
            "position_control_used_test_key": self.used_test_key,
            "position_control_used_true_positions": self.used_true_positions,
            "position_control_fixed_core_prefix_verified": self.prefix_verified,
            "position_control_canonical_encoder_verified": True,
        }


def build_fixed_core_position_evaluator(
    benchmark: InterruptorBenchmark,
) -> FixedCorePositionEvaluator:
    scoring_params = normalize_scorer_params(
        resolve_scorer_aliases(dict(SCORER_PARAMS))
    )
    scoring_cfg = ScoringConfig(**scoring_params)
    scoring_cfg.encoding_dir = Direction(DIRECTION)
    cipher_cfg = build_cipher_config(
        cipher=by_name.cipher("vigenere"),
        key=KeySpec.repeat(len=len(benchmark.key)),
        ciphertext=np.asarray(benchmark.ciphertext, dtype=np.uint8),
        wli=[list(pair) for pair in benchmark.wli],
        device=Device.CPU,
        encoding_dir=Direction(DIRECTION),
        initial_text_permutation_indices=None,
        initial_keys=None,
        interruptors={
            "mode": "pool",
            "pool": list(benchmark.pool),
            "min_count": MIN_INTERRUPT_COUNT,
            "max_count": MAX_INTERRUPT_COUNT,
            "search_strategy": "auto",
        },
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )
    instance = ProblemInstance.materialise(
        ProblemSpec(
            text="",
            text_encoding_direction=Direction(DIRECTION),
            cipher_cfg=cipher_cfg,
            scorer_params=scoring_cfg,
        )
    )
    return FixedCorePositionEvaluator(
        instance.problem,
        benchmark.key,
        benchmark.pool,
        MIN_INTERRUPT_COUNT,
        MAX_INTERRUPT_COUNT,
    )
