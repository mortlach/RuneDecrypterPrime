from __future__ import annotations

from typing import Any


__all__ = ["HammingBackend", "load_raw1grams_wordlists"]


def __getattr__(name: str) -> Any:
    if name == "HammingBackend":
        from .backend import HammingBackend

        return HammingBackend

    if name == "load_raw1grams_wordlists":
        from .loader import load_raw1grams_wordlists

        return load_raw1grams_wordlists

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
