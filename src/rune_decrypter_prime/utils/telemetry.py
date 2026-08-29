# ============================================================
# rune_decrypter_prime/utils/telemetry.py
# Tiny, no-throw helpers for uniform telemetry dictionaries.
# Contract-only surface; never raises; behaviour unchanged.
# ============================================================

from __future__ import annotations
from typing import Any, Dict, Optional


def stash(holder: Optional[Dict[str, Any]], /, **fields: Any) -> None:
    """
    Safely update a telemetry dictionary.

    Parameters
    ----------
    holder : dict | None
        Telemetry dict to update. If None or not a dict, this is a no-op.
    **fields
        Key-value pairs merged into the holder.
    """
    if isinstance(holder, dict):
        try:
            holder.update(fields)
        except Exception:
            # Telemetry must never interfere with core logic.
            pass


def event(name: str, /, **kv: Any) -> Dict[str, Any]:
    """
    Build a simple event map. No logging side effects here.

    Examples
    --------
    >>> event("optimizer_progress", gen=3, best=0.12)
    {'type': 'optimizer_progress', 'gen': 3, 'best': 0.12}
    """
    out = {"type": str(name)}
    out.update(kv)
    return out
