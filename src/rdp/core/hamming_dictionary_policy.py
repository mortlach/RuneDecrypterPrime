from __future__ import annotations

from enum import Enum


class HammingDictionaryPolicy(Enum):
    STRICT = "strict"
    NORMAL = "normal"
    BROAD = "broad"
    RESEARCH = "research"


def ensure_hamming_dictionary_policy(
    value: HammingDictionaryPolicy | str,
) -> HammingDictionaryPolicy:
    if isinstance(value, HammingDictionaryPolicy):
        return value
    key = str(value).strip().lower()
    for member in HammingDictionaryPolicy:
        if member.value == key:
            return member
    raise ValueError(f"Unknown hamming dictionary policy: {value!r}")


__all__ = [
    "HammingDictionaryPolicy",
    "ensure_hamming_dictionary_policy",
]
