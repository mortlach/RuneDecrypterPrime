"""Qualified non-answer warm start for the public P7/C7 tutorial."""

from __future__ import annotations

QUALIFICATION_RECIPE_ID = "periodic_columnar_decomposed_v2"
QUALIFICATION_CANDIDATE_ID = "6833118ceb72372e9af10e31f727dfdf3e2d34bb"

# Selected by the qualification's ciphertext-only char/WLI candidate reduction.
# This is the solver input, not the benchmark key or recovered key.
QUALIFIED_INITIAL_KEY: tuple[int, ...] = (
    18, 16, 14, 23, 27, 11, 0, 7, 2, 22, 5, 15, 21, 9, 20, 25, 8, 3,
    12, 24, 19, 1, 4, 28, 6, 13, 17, 10, 26, 19, 14, 9, 11, 7, 27, 5,
    0, 24, 2, 15, 22, 8, 21, 16, 18, 3, 17, 10, 23, 12, 4, 6, 1, 20,
    13, 25, 28, 26, 2, 24, 11, 25, 18, 26, 7, 14, 6, 15, 3, 22, 1, 27,
    0, 4, 20, 21, 10, 9, 13, 5, 19, 12, 17, 8, 23, 16, 28, 14, 0, 25,
    24, 15, 7, 20, 19, 13, 16, 2, 5, 22, 18, 3, 4, 1, 17, 27, 11, 21,
    10, 12, 28, 9, 23, 6, 26, 8, 19, 14, 11, 27, 4, 5, 20, 2, 23, 25,
    6, 13, 16, 1, 22, 0, 21, 24, 26, 3, 7, 12, 17, 18, 28, 9, 15, 10,
    8, 2, 27, 9, 7, 22, 0, 6, 14, 26, 15, 17, 13, 8, 19, 25, 3, 16,
    23, 21, 10, 12, 5, 24, 1, 4, 28, 11, 18, 20, 17, 11, 0, 8, 27, 7,
    6, 1, 26, 16, 18, 23, 14, 2, 20, 22, 4, 21, 9, 24, 15, 5, 13, 12,
    3, 28, 25, 19, 10, 3, 5, 6, 4, 2, 1, 0,
)


__all__ = [
    "QUALIFICATION_CANDIDATE_ID",
    "QUALIFICATION_RECIPE_ID",
    "QUALIFIED_INITIAL_KEY",
]
