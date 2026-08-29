from __future__ import annotations

import numpy as np

from rune_decrypter_prime.core.types import Stat


def apply_stat_transform(stat: Stat | str | None, values: np.ndarray) -> np.ndarray:
    """
    Canonical hook for stat direction/transform handling.

    Currently a no-op (higher-is-better for all stats), but centralized so
    future sign flips or transforms happen in one place.
    """
    if values is None:
        return values
    arr = np.asarray(values)
    if stat is None:
        return arr
    try:
        name = stat.value if isinstance(stat, Stat) else str(stat).lower()
    except Exception:
        name = str(stat).lower()
    if name in {"logp", "zsum", "madsum"}:
        return arr
    return arr
