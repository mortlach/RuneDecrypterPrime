# ============================================================
# rune_decrypter_prime/scoring/policy.py
# Shared scoring policies and helpers.
# ============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple


@dataclass(slots=True, frozen=True)
class Windowing:
    """
    Windowing policy for statistics-based scorers.
    Keep minimal for v1 — most logic remains in the scorer runtimes.
    """

    size: Optional[int] = None
    stride: Optional[int] = None


def validate_wli_pairs(wli: Optional[Sequence[Tuple[int, int]]]) -> bool:
    if wli is None:
        return True
    try:
        for a, b in wli:
            _ = int(a)
            _ = int(b)
        return True
    except Exception:
        return False
