# ============================================================
# rune_decrypter_prime/utils/telemetry_utils.py
# Convenience accessors/printing for solver telemetry/run_meta.
# Read-only helpers; never raise; behaviour unchanged.
# ============================================================

from __future__ import annotations
from typing import Any, Iterable, Mapping
from rune_decrypter_prime.io.logging_adapter import module_logger
from dataclasses import dataclass, is_dataclass
from dataclasses import is_dataclass, asdict
from enum import Enum
from typing import Any, Dict, Mapping, MutableMapping

logger = module_logger(__name__)

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
    get(telem(sol), "solver.params.pop_size")
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
        logger.info("(no telemetry)")
        return
    if only:
        for p in only:
            logger.debug(f"{p}: {get(t, p)}")
        return
    flat = flatten(t)
    for k in sorted(flat):
        logger.debug(f"{k}: {flat[k]}")

# --- Add at module level ---
def _upgrade_v1_time_keys(tel: dict) -> None:
    """Map legacy timing keys to v1 *_time_s keys (non-destructive)."""
    for old, new in (("decrypt_time", "decrypt_time_s"),
                     ("score_time", "score_time_s"),
                     ("wall_time", "wall_time_s")):
        if old in tel and new not in tel:
            try:
                tel[new] = float(tel[old])
            except Exception:
                tel[new] = tel[old]


_CANON_TIMING_KEYS = {
    "decrypt_time": "decrypt_time_s",
    "score_time": "score_time_s",
    # tolerate accidental leading underscore:
    "_decrypt_time": "decrypt_time_s",
    "_score_time": "score_time_s",
}

def canonicalize_timing_keys(payload: MutableMapping[str, Any]) -> None:
    """
    In-place: map any legacy timing keys to *_time_s. No-ops if already canonical.
    """
    for legacy, canon in _CANON_TIMING_KEYS.items():
        if legacy in payload and canon not in payload:
            payload[canon] = payload.pop(legacy)

def _enum_to_value(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {k: _enum_to_value(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Mapping):
        return {k: _enum_to_value(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(_enum_to_value(v) for v in obj)
    return obj

def stringify_for_telemetry(ctx: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Returns a deep-copied dict where any Enum/dataclass members are
    converted to JSON-friendly primitives. This is the ONLY place core
    turns Enums into strings (e.g., Direction -> "ltr"/"rtl").
    """
    return _enum_to_value(dict(ctx))

# TODO: Consider exporting a stable set of “common telemetry keys” to help tutorials/tests.
