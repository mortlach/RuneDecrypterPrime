from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


ALPHABET_SIZE = 29


class HardCribMode(str, Enum):
    HARD = "hard"


def _coerce_key_int(raw_key: Any, *, field_name: str, min_value: int) -> int:
    try:
        key = int(raw_key)
    except Exception as exc:  # pragma: no cover - defensive
        raise TypeError(f"{field_name} keys must be integers, got {raw_key!r}") from exc
    if key < min_value:
        raise ValueError(f"{field_name} keys must be >= {min_value}")
    return key


def _normalize_rune_sequence(
    seq_like: Sequence[Any],
    *,
    field_name: str,
    allow_empty: bool = False,
    dedupe: bool = False,
) -> Tuple[int, ...]:
    if not isinstance(seq_like, (list, tuple)):
        raise TypeError(f"{field_name} entries must be lists/tuples of rune indices")
    if (not allow_empty) and len(seq_like) == 0:
        raise ValueError(f"{field_name} entries cannot be empty")

    out: list[int] = []
    seen: set[int] = set()
    for raw in seq_like:
        try:
            v = int(raw)
        except Exception as exc:  # pragma: no cover - defensive
            raise TypeError(f"{field_name} rune indices must be integers, got {raw!r}") from exc
        if v < 0 or v >= ALPHABET_SIZE:
            raise ValueError(f"{field_name} rune indices must be in [0..{ALPHABET_SIZE - 1}]")
        if dedupe:
            if v in seen:
                continue
            seen.add(v)
        out.append(v)
    if (not allow_empty) and len(out) == 0:
        raise ValueError(f"{field_name} entries cannot be empty")
    return tuple(out)


def _normalize_fixed_chars(raw_map: Mapping[Any, Any] | None) -> Dict[int, Tuple[int, ...]]:
    if not raw_map:
        return {}
    out: Dict[int, Tuple[int, ...]] = {}
    for raw_pos, raw_allowed in raw_map.items():
        pos = _coerce_key_int(raw_pos, field_name="fixed_chars", min_value=0)
        allowed = _normalize_rune_sequence(raw_allowed, field_name="fixed_chars", dedupe=True)
        out[pos] = allowed
    return out


def _normalize_word_sequences(
    raw_sequences: Any,
    *,
    field_name: str,
    expected_len: int | None = None,
) -> Tuple[Tuple[int, ...], ...]:
    if not isinstance(raw_sequences, (list, tuple)):
        raise TypeError(f"{field_name} values must be a list/tuple of rune-index word sequences")
    if len(raw_sequences) == 0:
        raise ValueError(f"{field_name} values cannot be empty")

    out: list[Tuple[int, ...]] = []
    seen: set[Tuple[int, ...]] = set()
    for idx, raw_word in enumerate(raw_sequences):
        word = _normalize_rune_sequence(raw_word, field_name=f"{field_name}[{idx}]")
        if expected_len is not None and len(word) != int(expected_len):
            raise ValueError(
                f"{field_name}[{idx}] length {len(word)} does not match expected word length {int(expected_len)}"
            )
        if word in seen:
            continue
        seen.add(word)
        out.append(word)

    if len(out) == 0:
        raise ValueError(f"{field_name} values cannot be empty")
    return tuple(out)


def _normalize_per_word_allowed(raw_map: Mapping[Any, Any] | None) -> Dict[int, Tuple[Tuple[int, ...], ...]]:
    if not raw_map:
        return {}
    out: Dict[int, Tuple[Tuple[int, ...], ...]] = {}
    for raw_word_idx, raw_sequences in raw_map.items():
        word_idx = _coerce_key_int(raw_word_idx, field_name="per_word_allowed", min_value=0)
        seqs = _normalize_word_sequences(raw_sequences, field_name=f"per_word_allowed[{word_idx}]")
        out[word_idx] = seqs
    return out


def _normalize_global_allowed_by_len(raw_map: Mapping[Any, Any] | None) -> Dict[int, Tuple[Tuple[int, ...], ...]]:
    if not raw_map:
        return {}
    out: Dict[int, Tuple[Tuple[int, ...], ...]] = {}
    for raw_word_len, raw_sequences in raw_map.items():
        word_len = _coerce_key_int(raw_word_len, field_name="global_allowed_by_len", min_value=1)
        seqs = _normalize_word_sequences(
            raw_sequences,
            field_name=f"global_allowed_by_len[{word_len}]",
            expected_len=word_len,
        )
        out[word_len] = seqs
    return out


@dataclass
class HardCribConfig:
    enabled: bool = False
    mode: HardCribMode | str = HardCribMode.HARD
    require_wli_for_word_rules: bool = True
    fixed_chars: Dict[int, Tuple[int, ...]] | Mapping[Any, Any] | None = None
    per_word_allowed: Dict[int, Tuple[Tuple[int, ...], ...]] | Mapping[Any, Any] | None = None
    global_allowed_by_len: Dict[int, Tuple[Tuple[int, ...], ...]] | Mapping[Any, Any] | None = None

    def __post_init__(self) -> None:
        self.enabled = bool(self.enabled)
        self.require_wli_for_word_rules = bool(self.require_wli_for_word_rules)
        if isinstance(self.mode, HardCribMode):
            self.mode = self.mode
        else:
            self.mode = HardCribMode(str(self.mode).strip().lower())
        if self.mode is not HardCribMode.HARD:
            raise ValueError("hard_crib.mode must be 'hard'")

        self.fixed_chars = _normalize_fixed_chars(self.fixed_chars)  # type: ignore[arg-type]
        self.per_word_allowed = _normalize_per_word_allowed(self.per_word_allowed)  # type: ignore[arg-type]
        self.global_allowed_by_len = _normalize_global_allowed_by_len(self.global_allowed_by_len)  # type: ignore[arg-type]

    @property
    def has_word_rules(self) -> bool:
        return bool(self.per_word_allowed) or bool(self.global_allowed_by_len)

    @property
    def has_any_rules(self) -> bool:
        return bool(self.fixed_chars) or self.has_word_rules

    def asdict(self) -> Dict[str, Any]:
        return {
            "enabled": bool(self.enabled),
            "mode": self.mode.value if isinstance(self.mode, HardCribMode) else str(self.mode),
            "require_wli_for_word_rules": bool(self.require_wli_for_word_rules),
            "fixed_chars": {int(k): [int(v) for v in vals] for k, vals in (self.fixed_chars or {}).items()},
            "per_word_allowed": {
                int(k): [[int(x) for x in word] for word in words]
                for k, words in (self.per_word_allowed or {}).items()
            },
            "global_allowed_by_len": {
                int(k): [[int(x) for x in word] for word in words]
                for k, words in (self.global_allowed_by_len or {}).items()
            },
        }


def normalize_hard_crib_config(value: Any) -> Optional[HardCribConfig]:
    if value is None:
        return None
    if isinstance(value, HardCribConfig):
        return value
    if isinstance(value, dict):
        allowed = {
            "enabled",
            "mode",
            "require_wli_for_word_rules",
            "fixed_chars",
            "per_word_allowed",
            "global_allowed_by_len",
        }
        unknown = sorted(k for k in value.keys() if k not in allowed)
        if unknown:
            bad = ", ".join(unknown)
            ok = ", ".join(sorted(allowed))
            raise ValueError(f"Unknown hard_crib field(s): {bad}. Allowed: {ok}")
        return HardCribConfig(**value)
    raise TypeError("hard_crib must be a HardCribConfig or dict")
