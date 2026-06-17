from __future__ import annotations

"""Validation reference for the solved Welcome Pilgrim LP text.

This module is intentionally separate from `solve.py` so the solve entrypoint
stays readable. The canonical text is used only after a solve attempt, to compute
and print match quality. It is not supplied to the solver as a key, stop score,
crib, candidate pool, or search hint.

The LP text really contains WIDSOM rather than WISDOM; preserve that typo.
"""

CANONICAL_WELCOME_PILGRIM_TEXT = (
    "WELCOME WELCOME PILGRIM TO THE GREAT JOURNEY TOWARD THE END OF ALL THINGS "
    "IT IS NOT AN EASY TRIP BUT FOR THOSE WHO FIND THEIR WAY HERE IT IS A "
    "NECESSARY ONE ALONG THE WAY YOU WILL FIND AN END TO ALL STRUGGLE AND "
    "SUFFERING YOUR INNOCENCE YOUR ILLUSIONS YOUR CERTAINTY AND YOUR REALITY "
    "ULTIMATELY YOU WILL DISCOVER AN END TO SELF IT IS THROUGH THIS PILGRIMAGE "
    "THAT WE SHAPE OURSELVES AND OUR REALITIES JOURNEY DEEP WITHIN AND YOU "
    "WILL ARRIVE OUTSIDE LIKE THE INSTAR IT IS ONLY THROUGH GOING WITHIN THAT "
    "WE MAY EMERGE WIDSOM YOU ARE A BEING UNTO YOURSELF YOU ARE A LAW UNTO "
    "YOURSELF EACH INTELLIGENCE IS HOLY FOR ALL THAT LIVES IS HOLY AN "
    "INSTRUCTION COMMAND YOUR OWN SELF"
)

# Canonical solved Welcome Pilgrim plaintext as Runeglish positions, derived from
# the solved LP reference sheet and aligned to the master-transcript WLI. Keep
# this numeric form for stable regression checks across tokenisation changes.
CANONICAL_WELCOME_PILGRIM_IDX: tuple[int, ...] = (
    7, 18, 20, 5, 3, 19, 18, 7, 18, 20, 5, 3, 19, 18, 13, 10, 20, 6, 4, 10,
    19, 16, 3, 2, 18, 6, 4, 28, 16, 11, 3, 1, 4, 9, 18, 26, 16, 3, 7, 24,
    4, 23, 2, 18, 18, 9, 23, 3, 0, 24, 20, 20, 2, 21, 15, 10, 16, 10, 15, 9,
    3, 16, 24, 9, 28, 15, 26, 16, 4, 10, 13, 17, 1, 16, 0, 3, 4, 2, 3, 15,
    18, 7, 8, 3, 0, 10, 9, 23, 2, 18, 10, 4, 7, 24, 26, 8, 18, 4, 18, 10,
    16, 10, 15, 24, 9, 18, 5, 18, 15, 15, 24, 4, 26, 3, 9, 18, 24, 20, 3, 21,
    2, 18, 7, 24, 26, 26, 3, 1, 7, 10, 20, 20, 0, 10, 9, 23, 24, 9, 18, 9,
    23, 16, 3, 24, 20, 20, 15, 16, 4, 1, 6, 6, 20, 18, 24, 9, 23, 15, 1, 0,
    0, 18, 4, 21, 26, 3, 1, 4, 10, 9, 9, 3, 5, 18, 9, 5, 18, 26, 3, 1,
    4, 10, 20, 20, 1, 15, 27, 9, 15, 26, 3, 1, 4, 5, 18, 4, 16, 24, 10, 9,
    16, 26, 24, 9, 23, 26, 3, 1, 4, 4, 28, 20, 10, 16, 26, 1, 20, 16, 10, 19,
    24, 16, 18, 20, 26, 26, 3, 1, 7, 10, 20, 20, 23, 10, 15, 5, 3, 1, 18, 4,
    24, 9, 18, 9, 23, 16, 3, 15, 18, 20, 0, 10, 16, 10, 15, 2, 4, 3, 1, 6,
    8, 2, 10, 15, 13, 10, 20, 6, 4, 10, 19, 24, 6, 18, 2, 24, 16, 7, 18, 15,
    8, 24, 13, 18, 3, 1, 4, 15, 18, 20, 1, 18, 15, 24, 9, 23, 3, 1, 4, 4,
    28, 20, 10, 16, 10, 18, 15, 11, 3, 1, 4, 9, 18, 26, 23, 18, 18, 13, 7, 10,
    2, 10, 9, 24, 9, 23, 26, 3, 1, 7, 10, 20, 20, 24, 4, 4, 10, 1, 18, 3,
    1, 16, 15, 10, 23, 18, 20, 10, 5, 18, 2, 18, 10, 9, 15, 16, 24, 4, 10, 16,
    10, 15, 3, 9, 20, 26, 2, 4, 3, 1, 6, 8, 6, 3, 21, 7, 10, 2, 10, 9,
    2, 24, 16, 7, 18, 19, 24, 26, 18, 19, 18, 4, 6, 18, 7, 10, 23, 15, 3, 19,
    26, 3, 1, 24, 4, 18, 24, 17, 18, 21, 1, 9, 16, 3, 26, 3, 1, 4, 15, 18,
    20, 0, 26, 3, 1, 24, 4, 18, 24, 20, 24, 7, 1, 9, 16, 3, 26, 3, 1, 4,
    15, 18, 20, 0, 28, 5, 8, 10, 9, 16, 18, 20, 20, 10, 6, 18, 9, 5, 18, 10,
    15, 8, 3, 20, 26, 0, 3, 4, 24, 20, 20, 2, 24, 16, 20, 10, 1, 18, 15, 10,
    15, 8, 3, 20, 26, 24, 9, 10, 9, 15, 16, 4, 1, 5, 16, 27, 9, 5, 3, 19,
    19, 24, 9, 23, 26, 3, 1, 4, 3, 7, 9, 15, 18, 20, 0,
)

__all__ = ["CANONICAL_WELCOME_PILGRIM_IDX", "CANONICAL_WELCOME_PILGRIM_TEXT"]
