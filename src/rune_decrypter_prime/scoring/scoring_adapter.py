# ============================================================
# rune_decrypter_prime/scoring/score_adapter.py
# Thin facade over the existing scorer runtimes.
# ============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Sequence
import numpy as np
from rdp.core.types import Direction, ensure_direction

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
        if not hasattr(self.scorer, "batch_score"):
            raise AttributeError("scorer does not provide batch_score(...)")
        # direction is intentionally not threaded as a runtime arg; scorer direction
        # is part of scorer configuration in the current contract.
        scores = self.scorer.batch_score(toks, None)
        return np.asarray(scores, dtype=np.float64)

    # Single plaintext tokens (shape [L]) -> float
    def score_one_tokens(self, tok: Sequence[int]) -> float:
        if hasattr(self.scorer, "score"):
            return float(self.scorer.score(tok, None))
        v = self.score_batch_tokens([tok])
        return float(np.asarray(v, dtype=np.float64).reshape(-1)[0])
