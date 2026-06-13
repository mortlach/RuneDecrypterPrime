# ============================================================
# rune_decrypter_prime/scoring/language_model/paths.py   (LM path helpers)
# Utilities to resolve packaged language-model roots and expand index patterns.
# Pure-config; no env/CLI lookups.
# ============================================================

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Iterable, Union, Dict, Tuple

from rune_decrypter_prime.core.config import ScoringConfig
from rune_decrypter_prime.data.asset_paths import resolve_assets_path, to_repo_relative

# __file__ = .../src/rune_decrypter_prime/scoring/language_model/paths.py
_MODULE_PATH = Path(__file__).resolve()

# Single source of truth for the built-in minimal model folder.
_DEFAULT_LM_NAME = "lmp"
_DEFAULT_LM_ASSETS_REL = Path("language_model")


def _assets_lm_base() -> Path:
    return resolve_assets_path(str(_DEFAULT_LM_ASSETS_REL), start=_MODULE_PATH)


def _display_path(path: Path) -> str:
    """
    Prefer repository-relative path strings in user-facing messages
    to avoid leaking machine-specific absolute paths.
    """
    return to_repo_relative(Path(path), start=_MODULE_PATH)


def _coerce_model_root(value: Union[str, os.PathLike, Path, None]) -> Path:
    """
    Coerce a model_root value into an absolute Path under the packaged LM root,
    unless it is already an absolute path.

    Behaviour:
      - None or empty string -> "<repo>/assets/language_model/lmp"
      - Relative path        -> interpreted under "<repo>/assets/language_model"
      - Absolute path        -> used as-is
    """
    # Default if value is None or empty string
    if value is None or (isinstance(value, str) and not value.strip()):
        value = _DEFAULT_LM_NAME

    p = Path(value)
    if not p.is_absolute():
        p = _assets_lm_base() / p
    return p.resolve()


def resolve_lm_root(cfg: Union[ScoringConfig, Mapping[str, Any], None]) -> Path:
    """
    Resolve a language-model root folder from a config object or mapping.

    Semantics:
      - None or empty config/model_root -> packaged default (_DEFAULT_LM_NAME).
      - Relative str/path -> relative to <repo>/assets/language_model.
      - Absolute path -> used as-is.

    Raises:
      FileNotFoundError with a friendly list of available packaged models when absent.
    """
    # Pull model_root from either a dataclass or a dict-like; allow None config
    model_root = None
    if cfg is None:
        model_root = None
    elif hasattr(cfg, "model_root"):
        model_root = getattr(cfg, "model_root")
    elif isinstance(cfg, Mapping):
        model_root = cfg.get("model_root")

    root = _coerce_model_root(model_root)

    if not root.exists():
        lm_base = _assets_lm_base()
        # Build a friendly error enumerating available local asset models
        try:
            options = [d.name for d in lm_base.iterdir() if d.is_dir()]
            options.sort()
            available = ", ".join(options) if options else "(none)"
        except Exception:
            available = "(unavailable)"

        raise FileNotFoundError(
            f"Language-model root not found at: {_display_path(root)}\n"
            f"Requested: {model_root!r}; base: {_display_path(lm_base)}\n"
            f"Available local asset models: {available}"
        )

    return root


@dataclass(frozen=True)
class LmIndex:
    version: str
    base: str
    ecdf_root: str
    joint_root: str
    models: dict


def load_index(root: Path) -> LmIndex:
    """
    Load the language-model index from <root>/index.json.

    - Purely config-driven: no environment variables, no CLI fallbacks.
    - Returns an LmIndex so callers can use attribute access (idx.models, idx.base, ...).
    - Validates a couple of basic expectations to fail early and clearly.
    """
    idx_path = root / "index.json"

    try:
        with idx_path.open("r", encoding="utf-8") as fh:
            data: Dict[str, Any] = json.load(fh)
    except FileNotFoundError:
        # Keep this blunt and config-centric; no env/CLI mentioned.
        raise FileNotFoundError(
            f"LM index.json not found at: {_display_path(idx_path)}\n"
            f"(root was resolved from config to: {_display_path(root)})"
        ) from None
    except json.JSONDecodeError as e:
        raise ValueError(f"LM index.json is malformed at {idx_path}: {e}") from e

    if "models" not in data:
        raise ValueError(
            f"LM index.json at {idx_path} missing required key 'models'. "
            f"Top-level keys present: {list(data.keys())}"
        )

    return LmIndex(**data)


# --- Compatibility shims expected by language_model_prime.py ---

def default_lm_root() -> Path:
    """Repository assets-relative default LM root."""
    return (_assets_lm_base() / _DEFAULT_LM_NAME).resolve()


def expand_pattern(root: Path, pattern: Union[str, Iterable[str]], **subs) -> Path:
    """
    Expand an index pattern into a concrete file path.

    - `pattern` can be a string or list of strings.
    - Supported tokens: %%MODE%%, %%POS%%, %%N%%, %%STAT%%, plus any custom
      keys passed via **subs (case-insensitive, we replace %%KEY%% by value).
    - If globbing is present, require exactly one match (raise when 0 or >1).
    - Always returns a single Path (absolute).
    """
    root = root.resolve()
    patterns = [pattern] if isinstance(pattern, str) else list(pattern)

    # Token substitution (generic: any %%KEY%% from **subs)
    def _subst(p: str) -> str:
        out = p
        for k, v in subs.items():
            token = f"%%{str(k).upper()}%%"
            out = out.replace(token, str(v))
        return out

    def _has_glob(name: str) -> bool:
        return any(ch in name for ch in "*?[]")

    errors: list[str] = []
    for pat in patterns:
        sub = _subst(pat)
        p = root / sub
        parent, name = p.parent, p.name

        if _has_glob(name):
            matches = sorted(parent.glob(name))
            if len(matches) == 1:
                return matches[0].resolve()
            errors.append(f"{sub!r} -> {len(matches)} matches under {parent}")
        else:
            return p.resolve()

    raise FileNotFoundError(
        "Could not resolve pattern to a single path.\n"
        + "\n".join(f"- {e}" for e in errors)
    )


__all__ = ["resolve_lm_root", "load_index", "default_lm_root", "expand_pattern"]

# TODO(docs): Add a short example in docs/extending for custom LM roots and patterns.
