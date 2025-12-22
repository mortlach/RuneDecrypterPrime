from __future__ import annotations
from typing import Any, Callable, Dict

from rune_decrypter_prime.core.types import KeyOpsFamily, ensure_keyops_family

# Registry storage: KeyOpsFamily -> factory (callable returning a KeyOpBase)
_REG: Dict[KeyOpsFamily, Callable[..., Any]] = {}


def _normalize_family(name: KeyOpsFamily | str) -> KeyOpsFamily:
    return ensure_keyops_family(name)


def register_keyop(name: KeyOpsFamily | str):
    """Decorator: register a KeyOps factory/class under a canonical family."""

    def _wrap(factory: Callable[..., Any]):
        family = _normalize_family(name)
        # Allow re-registration during dev, but always overwrite
        _REG[family] = factory
        return factory

    return _wrap


def has(name: KeyOpsFamily | str) -> bool:
    try:
        family = _normalize_family(name)
    except (TypeError, ValueError):
        return False
    return family in _REG


def get(name: KeyOpsFamily | str) -> Callable[..., Any]:
    family = _normalize_family(name)
    if family not in _REG:
        available_fams = ", ".join(sorted(fam.value for fam in _REG))
        raise KeyError(
            f"KeyOps '{name}' is not registered. Available: {available_fams}" if available_fams else
            f"KeyOps '{name}' is not registered."
        )
    return _REG[family]


def available() -> list[KeyOpsFamily]:
    return sorted(_REG.keys(), key=lambda fam: fam.value)


# ---- Canonical aliasing for ctor kwargs (kept from previous implementation) ---
def _alias_kwargs_for_family(family: KeyOpsFamily, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize legacy kwarg names to canonical ctor args per family."""
    fam = _normalize_family(family)
    out = dict(kwargs) if kwargs else {}

    # Common K aliases
    if "K" not in out:
        if "length" in out:
            out["K"] = out.pop("length")
        elif "L" in out:
            out["K"] = out.pop("L")

    # Family-specific
    if fam is KeyOpsFamily.VECTOR:
        if "mod" not in out:
            if "A" in out:
                out["mod"] = out.pop("A")
            elif "alphabet_size" in out:
                out["mod"] = out.pop("alphabet_size")
    elif fam is KeyOpsFamily.PERMUTATION:
        pass  # no extra aliases beyond K
    # Coerce to ints where present (robust to numpy scalars / strings)
    if "K" in out and out["K"] is not None:
        out["K"] = int(out["K"])
    if "mod" in out and out["mod"] is not None:
        out["mod"] = int(out["mod"])
    return out


# -----------------------------------------------------------------------------
def create(name: KeyOpsFamily | str, **kwargs: Any):
    """Construct a KeyOps instance by canonical family name or Enum."""
    family = _normalize_family(name)
    factory = get(family)
    canon_kwargs = _alias_kwargs_for_family(family, kwargs)
    try:
        return factory(**canon_kwargs)
    except TypeError as exc:
        factory_name = getattr(factory, "__name__", repr(factory))
        raise TypeError(
            f"{factory_name} could not be constructed for family='{family.value}' "
            f"with kwargs={canon_kwargs!r}. Original error: {exc}"
        ) from exc


# Ensure imports run registration side-effects
try:
    from . import permutation_ops  # registers KeyOpsFamily.PERMUTATION on import
except Exception:
    pass
try:
    from . import vector  # registers KeyOpsFamily.VECTOR on import
except Exception:
    pass
__all__ = ["register_keyop", "create", "get", "has", "available"]
