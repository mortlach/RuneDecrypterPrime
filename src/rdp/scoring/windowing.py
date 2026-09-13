"""
Windowing helpers for LMPrime-style scoring.

Window semantics:
  - W = number of n-grams per window (not rune count).
  - NOSE: L_n = W + n - 1
  - WISE: L_n = W + n + 1  (adds start/end tags)
"""

from __future__ import annotations

from typing import Dict, Iterable

from rdp.core.types import SeMode

START_TAG: int = 29
END_TAG: int = 30


def _norm_se_mode(se_mode: SeMode | str) -> str:
    if hasattr(se_mode, "value"):
        return str(getattr(se_mode, "value")).lower()
    return str(se_mode).lower()


def span_core_tokens(*, n: int, W: int) -> int:
    """Interior token span used to produce W n-grams of order n."""
    n_i = int(n)
    W_i = int(W)
    if n_i <= 0 or W_i <= 0:
        raise ValueError("n and W must be positive")
    return W_i + n_i - 1


def span_with_tags(*, n: int, W: int, se_mode: SeMode | str) -> int:
    """Full window span including tags (WISE) or not (NOSE)."""
    core = span_core_tokens(n=n, W=W)
    se = _norm_se_mode(se_mode)
    if se == "nose":
        return core
    if se == "wise":
        return core + 2
    raise ValueError("se_mode must be 'nose' or 'wise'")


def span_map(*, n_set: Iterable[int], W: int, se_mode: SeMode | str) -> Dict[int, int]:
    """Map n -> L_n using the agreed window semantics."""
    out: Dict[int, int] = {}
    for n in n_set:
        out[int(n)] = span_with_tags(n=int(n), W=W, se_mode=se_mode)
    return out


def span_max(*, n_set: Iterable[int], W: int, se_mode: SeMode | str) -> int:
    """Return L_max over n_set."""
    spans = span_map(n_set=n_set, W=W, se_mode=se_mode)
    if not spans:
        raise ValueError("n_set must not be empty")
    return max(spans.values())


def aligned_window_count(*, length: int, n_set: Iterable[int], W: int, se_mode: SeMode | str, stride: int = 1) -> int:
    """Compute the aligned window count using L_max and stride.

    `length` must be the effective sequence length used for windowing:
      - NOSE: length = len(pt)
      - WISE: length = len(pt) - 2 if tags already present (interior length),
              otherwise len(pt) (tags will be injected per window).
    """
    L_max = span_max(n_set=n_set, W=W, se_mode=se_mode)
    stride_i = int(stride)
    if stride_i <= 0:
        raise ValueError("stride must be >= 1")
    if length < L_max:
        return 0
    return ((int(length) - int(L_max)) // stride_i) + 1


__all__ = [
    "START_TAG",
    "END_TAG",
    "span_core_tokens",
    "span_with_tags",
    "span_map",
    "span_max",
    "aligned_window_count",
]
