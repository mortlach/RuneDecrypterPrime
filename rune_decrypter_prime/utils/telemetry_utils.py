# ============================================================
# rune_decrypter_prime/utils/telemetry_utils.py
# Convenience accessors/printing for solver telemetry/run_meta.
# Read-only helpers; never raise; behaviour unchanged.
# ============================================================

from __future__ import annotations
from typing import Any, Iterable, Mapping

def telem(sol) -> dict:
    """Return the telemetry dict if present, else {}."""
    meta = getattr(sol, "meta", {}) or {}
    t = meta.get("telemetry")
    return t if isinstance(t, dict) else {}

def run_meta(sol) -> dict:
    """Return the run_meta summary if present, else {}."""
    meta = getattr(sol, "meta", {}) or {}
    rm = meta.get("run_meta")
    return rm if isinstance(rm, dict) else {}

def get(d: Mapping[str, Any] | None, path: str, default: Any = None) -> Any:
    """
    Safe dotted-path getter over nested dicts/lists/objects.

    Examples
    --------
    get(telem(sol), "optimizer.params.pop_size")
    get(telem(sol), "scorer.device")
    get(run_meta(sol), "tokens")
    """
    if not d or not path:
        return default
    cur: Any = d
    for part in path.split("."):
        try:
            if isinstance(cur, Mapping) and part in cur:
                cur = cur[part]
            elif isinstance(cur, (list, tuple)) and part.isdigit():
                cur = cur[int(part)]
            else:
                cur = getattr(cur, part)  # last-ditch for object-y blobs
        except Exception:
            return default
    return cur

def flatten(d: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dict to dotted paths → values (keeps simple lists intact)."""
    out: dict[str, Any] = {}
    for k, v in (d or {}).items():
        key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, Mapping):
            out.update(flatten(v, key))
        elif isinstance(v, (list, tuple)) and v and all(not isinstance(x, Mapping) for x in v):
            out[key] = v  # keep lists as-is if they’re not dict-like
        else:
            out[key] = v
    return out

def print_telem(sol, *, only: Iterable[str] | None = None) -> None:
    """Pretty-print telemetry; optionally restrict to specific dotted paths."""
    t = telem(sol)
    if not t:
        print("(no telemetry)")
        return
    if only:
        for p in only:
            print(f"{p}: {get(t, p)}")
        return
    flat = flatten(t)
    for k in sorted(flat):
        print(f"{k}: {flat[k]}")

# TODO: Consider exporting a stable set of “common telemetry keys” to help tutorials/tests.
