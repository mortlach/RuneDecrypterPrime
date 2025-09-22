# ============================================================
# rune_decrypter_prime/ciphers/registry.py
# ============================================================
"""
Cipher registry to enable zero‑touch additions of new ciphers.

One‑time engine hook (factory):
>>> from rune_decrypter_prime.ciphers.legacy import registry as cipher_registry
>>> def build_cipher(cfg):
...     name = getattr(cfg, "name", "vigenere").lower()
...     if cipher_registry.has(name):
...         return cipher_registry.get(name)(cfg)
...     # else: fallback to legacy mapping
"""
from __future__ import annotations
from typing import Dict, Callable, Any

_REGISTRY: Dict[str, Callable[[Any], Any]] = {}

def register_cipher(name: str):
    key = name.lower().strip()
    def _deco(ctor: Callable[[Any], Any]):
        if key in _REGISTRY:
            raise ValueError(f"Cipher '{key}' already registered")
        _REGISTRY[key] = ctor
        setattr(ctor, "cipher_name", key)
        return ctor
    return _deco

def has(name: str) -> bool:
    return name.lower().strip() in _REGISTRY

def get(name: str) -> Callable[[Any], Any]:
    key = name.lower().strip()
    if key not in _REGISTRY:
        raise KeyError(f"Unknown cipher '{key}'. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[key]

def available() -> list[str]:
    return sorted(_REGISTRY)