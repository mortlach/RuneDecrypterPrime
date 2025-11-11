# ============================================================
# rune_decrypter_prime/scoring/score_adapter.py
# Thin facade over the existing scorer runtimes.
# ============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Sequence
import numpy as np
from rune_decrypter_prime.core.types import Direction, ensure_direction

@dataclass(slots=True)
class ScoringAdapter:
    """
    Adapter that gives solvers a single numeric interface
    while delegating all work to the underlying scorer.
    """
    scorer: Any
    direction: Direction

    def __post_init__(self):
        self.direction = ensure_direction(self.direction)

    # Batch score plaintext tokens (shape [N,L] or list-of-seqs) -> float64[N]
    def score_batch_tokens(self, toks: Sequence[Sequence[int]]) -> np.ndarray:
        scores = self.scorer.score_tokens(toks, direction=self.direction)
        return np.asarray(scores, dtype=np.float64)

    # Single plaintext tokens (shape [L]) -> float
    def score_one_tokens(self, tok: Sequence[int]) -> float:
        v = self.scorer.score_tokens([tok], direction=self.direction)
        return float(np.asarray(v, dtype=np.float64)[0])
