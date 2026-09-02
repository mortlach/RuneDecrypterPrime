from __future__ import annotations

from typing import Any

__all__ = [
    "as_lut_keys_int64_torch",
    "as_lut_logp_float32_torch",
    "lookup_logp_linear_probe",
    "xxh64_u32words_cpu",
    "xxh64_u32words_device",
    "pack_char_ngram",
    "pack_wli_ngram",
]


def __getattr__(name: str) -> Any:
    if name in {
        "as_lut_keys_int64_torch",
        "as_lut_logp_float32_torch",
        "xxh64_u32words_cpu",
        "xxh64_u32words_device",
    }:
        from . import hash as hash_backend

        return getattr(hash_backend, name)
    if name in {"pack_char_ngram", "pack_wli_ngram"}:
        from . import packing

        return getattr(packing, name)
    if name == "lookup_logp_linear_probe":
        from .probe import lookup_logp_linear_probe

        return lookup_logp_linear_probe
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
