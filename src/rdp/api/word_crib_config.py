from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


def _normalize_word_weights(mapping: Mapping[str, Any] | None) -> Dict[str, float]:
    if not mapping:
        return {}
    out: Dict[str, float] = {}
    for raw_word, raw_weight in mapping.items():
        if raw_word is None:
            continue
        word = str(raw_word).strip().upper()
        if not word:
            continue
        try:
            weight = float(raw_weight) if raw_weight is not None else 0.0
        except Exception as exc:  # pragma: no cover - defensive
            raise TypeError(
                f"Word crib weights must be numeric, got {raw_weight!r}"
            ) from exc
        out[word] = weight
    return out


def _normalize_short_dict(
    mapping: Mapping[int, Mapping[str, Any]] | None,
) -> Dict[int, Dict[str, float]]:
    if not mapping:
        return {}
    out: Dict[int, Dict[str, float]] = {}
    for length_key, entries in mapping.items():
        try:
            length = int(length_key)
        except Exception as exc:  # pragma: no cover - defensive
            raise TypeError(
                f"Short-word crib keys must be integers, got {length_key!r}"
            ) from exc
        if length <= 0:
            continue
        normalized = _normalize_word_weights(entries)
        if normalized:
            out[length] = normalized
    return out


def _normalize_per_word(
    mapping: Mapping[int, Mapping[str, Any]] | None,
) -> Dict[int, Dict[str, float]]:
    if not mapping:
        return {}
    out: Dict[int, Dict[str, float]] = {}
    for idx_key, entries in mapping.items():
        try:
            index = int(idx_key)
        except Exception as exc:  # pragma: no cover - defensive
            raise TypeError(
                f"Per-word crib keys must be integers, got {idx_key!r}"
            ) from exc
        if index < 0:
            continue
        normalized = _normalize_word_weights(entries)
        if normalized:
            out[index] = normalized
    return out


@dataclass
class WordCribConfig:
    """
    High-level word-level constraints for bigram_sub.

    - ``short_word_dict`` maps word length -> {word: weight}
    - ``per_word_cribs`` maps 0-based word index -> {word: weight}
    """

    enabled: bool = False
    max_short_length: int = 3
    short_word_dict: Dict[int, Dict[str, float]] = field(default_factory=dict)
    per_word_cribs: Dict[int, Dict[str, float]] = field(default_factory=dict)


def normalize_word_crib_config(value: Any) -> Optional[WordCribConfig]:
    if value is None:
        return None
    if isinstance(value, WordCribConfig):
        return value
    if isinstance(value, dict):
        enabled = bool(value.get("enabled", False))
        max_short = int(value.get("max_short_length", 3) or 0)
        if max_short < 0:
            max_short = 0
        short_dict = _normalize_short_dict(value.get("short_word_dict"))
        per_word = _normalize_per_word(value.get("per_word_cribs"))
        return WordCribConfig(
            enabled=enabled,
            max_short_length=max_short,
            short_word_dict=short_dict,
            per_word_cribs=per_word,
        )
    raise TypeError(
        "short_word_crib must be a WordCribConfig instance or a dict "
        "with keys {enabled, max_short_length, short_word_dict, per_word_cribs}"
    )
