from __future__ import annotations
from dataclasses import asdict, is_dataclass, replace
from typing import Dict, Any, Tuple

from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig, SolverConfig
from rune_decrypter_prime.core.config.logging_config import LoggingConfig
from rune_decrypter_prime.data.cipher_tests.baseline_registry import BASELINE
from rune_decrypter_prime.core.types import Device, ScorerImpl

# ---------------- internal utils ----------------

def _to_dict(dc_or_dict):
    if is_dataclass(dc_or_dict):
        return asdict(dc_or_dict)
    if isinstance(dc_or_dict, dict):
        return dict(dc_or_dict)
    try:
        return dict(dc_or_dict.__dict__)
    except Exception as e:
        raise TypeError(f"Unsupported config type: {type(dc_or_dict)!r}") from e


def _deep_merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def dataclass_overrides(dc_obj, overrides: Dict[str, Any] | None = None, /,
                        strict: bool = True, allow_new: bool = False, **kw):
    """
    Return a new dataclass instance with selected fields updated.

    - `overrides`: mapping of field -> value (positional-only for clarity)
    - `**kw`     : keyword overrides (applied after `overrides`)
    - `strict=True`: raise if an override key doesn't exist on the dataclass
    - `allow_new=False`: ignore unknown keys instead of raising (set True to attach extras)

    Both of these are accepted:
        dataclass_overrides(cfg, {"device":"cuda"}, key_length=12)
        dataclass_overrides(cfg, overrides={"device":"cuda"}, key_length=12)
    """
    if not is_dataclass(dc_obj):
        raise TypeError("dc_obj must be a dataclass instance")

    # Accept 'overrides=' if passed as a keyword (common pitfall with '/' in signatures)
    if "overrides" in kw:
        o2 = kw.pop("overrides") or {}
        overrides = _deep_merge(overrides or {}, o2)

    base = asdict(dc_obj)
    extra = _deep_merge(overrides or {}, kw)

    if not extra:
        return dc_obj

    if strict and not allow_new:
        unknown = set(extra) - set(base)
        if unknown:
            raise KeyError(f"Unknown override key(s): {sorted(unknown)}")

    # Apply only known fields unless allow_new=True
    applied = dict(base)
    if allow_new:
        applied.update(extra)
    else:
        for k, v in extra.items():
            if k in applied:
                applied[k] = v

    return replace(dc_obj, **applied)


def overrides_dict(base, extra: dict | None = None, *, strict: bool = False, allow_new: bool = True) -> dict:
    """
    Produce a plain dict of config overrides.

    - If `base` is a dataclass -> start from `asdict(base)`.
    - If `base` is already a dict -> shallow copy it.
    - If `base` is an object with attributes -> copy its __dict__.
    - Merge `extra` on top.
    - strict=True  -> raise on unknown keys in `extra`.
    - allow_new=False -> ignore unknown keys instead of raising.

    Always returns a dict.
    """
    if is_dataclass(base):
        out = asdict(base)
    elif isinstance(base, dict):
        out = dict(base)
    else:
        try:
            out = dict(base.__dict__)
        except Exception as e:
            raise TypeError(f"Unsupported base type for overrides_dict: {type(base)!r}") from e

    extra = dict(extra or {})
    if not extra:
        return out

    if strict:
        unknown = set(extra) - set(out)
        if unknown:
            raise KeyError(f"Unknown override key(s): {sorted(unknown)}")

    if allow_new:
        out.update(extra)
    else:
        for k, v in extra.items():
            if k in out:
                out[k] = v

    return out


# ---------------- public helpers ----------------

def make_cipher_cfg(overrides: Dict[str, Any] | None = None, /, **kw) -> CipherConfig:
    """
    Safe cipher config with explicit defaults and flexible overrides.

    Defaults:
      device="cpu", name="vigenere", key_length=7,
      ciphertext=[], wli_data=[], text_transposition="ltr", key_transposition="ltr"

    You can pass overrides either positionally or as 'overrides='.
    """
    # Accept 'overrides=' if the caller passed it by keyword
    if "overrides" in kw:
        o2 = kw.pop("overrides") or {}
        overrides = _deep_merge(overrides or {}, o2)

    base = CipherConfig(
        device=Device.CPU,
        name="vigenere",
        key_length=7,
        ciphertext=[],
        wli_data=[],
        initial_text_permutation_indices=None,
        #key_transposition="ltr",
    )
    return dataclass_overrides(base, overrides, **kw)


def make_scorer_cfg(overrides: Dict[str, Any] | None = None, /, **kw) -> ScoringConfig:
    """
    Start from the tested scoring defaults in BASELINE['scoring'], then allow overrides.
    You can pass overrides either positionally or as 'overrides='.
    """
    if "overrides" in kw:
        o2 = kw.pop("overrides") or {}
        overrides = _deep_merge(overrides or {}, o2)

    baseline = dict(BASELINE.get("scoring", {}))
    merged = _deep_merge(baseline, overrides or {})
    merged = _deep_merge(merged, kw)

    if "impl" not in merged:
        merged["impl"] = ScorerImpl.AUTO

    d = ScoringConfig(**merged)
    return d


def make_logging_cfg(overrides: Dict[str, Any] | None = None, /, **kw) -> LoggingConfig:
    """
    Construct a LoggingConfig from BASELINE['logging'] with user overrides winning.

    Accepts both:
        make_logging_cfg({"verbose": False})
        make_logging_cfg(overrides={"print_progress": False}, write_jsonl=True)
    """
    if "overrides" in kw:
        o2 = kw.pop("overrides") or {}
        overrides = _deep_merge(overrides or {}, o2)

    base = dict(BASELINE.get("logging", {}))
    merged = _deep_merge(base, overrides or {})
    merged = _deep_merge(merged, kw)
    return LoggingConfig(**merged)


def make_optimizer_cfg(name: str = "beam", overrides: Dict[str, Any] | None = None, /, **kw) -> SolverConfig:
    """
    Build an OptimizerConfig with sensible defaults from BASELINE['budgets'][name].

    Examples:
        make_optimizer_cfg("beam", {"beam_width": 6})
        make_optimizer_cfg("ga", population=64, generations=100)

    Notes:
        • User overrides (dict or kwargs) always win.
        • BASELINE['seed'] is copied into params['seed'] unless the caller overrides it.
    """
    if "overrides" in kw:
        o2 = kw.pop("overrides") or {}
        overrides = _deep_merge(overrides or {}, o2)

    budgets = dict(BASELINE.get("budgets", {}))
    params = dict(budgets.get(name, {}))  # start from known budget or empty
    seed = int(BASELINE.get("seed", 0))
    params.setdefault("seed", seed)

    params = _deep_merge(params, overrides or {})
    params = _deep_merge(params, kw)

    return SolverConfig(name=name, params=params)


def _mk_cfgs(device: str = "cpu", encoding_dir: str = "ltr",
             cipher_overrides: Dict[str, Any] | None = None,
             scorer_overrides: Dict[str, Any] | None = None) -> Tuple[CipherConfig, ScoringConfig]:
    """
    Convenience wrapper for tests:
      - Pass device ('cpu' | 'torch' | 'cuda' | 'cuda:0'...) into CipherConfig
      - Pass direction ('ltr' | 'rtl') into ScoringConfig
      - Allow extra overrides for either side; user-provided values win.
    """
    # IMPORTANT: pass overrides POSITIONALLY to avoid the '/' pitfall.
    c_cfg = make_cipher_cfg({"device": device}, **(cipher_overrides or {}))
    s_cfg = make_scorer_cfg({"encoding_dir": encoding_dir}, **(scorer_overrides or {}))
    return c_cfg, s_cfg
