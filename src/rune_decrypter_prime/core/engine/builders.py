# rune_decrypter_prime/core/engine/builders.py
from __future__ import annotations
from typing import Any, Dict, Type

from rune_decrypter_prime.core.types import Device, ScorerImpl, ensure_device, ensure_scorer_impl
from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.ciphers import registry as cipher_registry

def build_cipher(cfg_cipher) -> Any:
    name = getattr(cfg_cipher, "name", None)
    if not name:
        raise ValueError("Cipher config must include a 'name' field")
    name = str(name).lower()
    if not cipher_registry.has(name):
        avail = ", ".join(cipher_registry.available())
        raise KeyError(f"Unknown cipher '{name}'. Available: {avail}")
    CipherCtor = cipher_registry.get(name)
    cipher = CipherCtor(cfg_cipher)
    if not hasattr(cipher, "cfg"):
        setattr(cipher, "cfg", cfg_cipher)
    return cipher

def build_scorer(c_cfg, s_cfg):
    impl = ensure_scorer_impl(getattr(s_cfg, "impl", ScorerImpl.AUTO))
    dev_raw = getattr(c_cfg, "device", Device.CPU)
    device = ensure_device(dev_raw)

    # Resolve AUTO based on device
    if impl is ScorerImpl.AUTO:
        impl = ScorerImpl.TORCH if device is Device.CUDA else ScorerImpl.NUMPY

    # Enforce CUDA availability if requested
    if device is Device.CUDA:
        dev_name, _ = select_backend(Device.CUDA.value)
        assert dev_name == Device.CUDA.value, f"Expected {Device.CUDA.value} backend, got {dev_name!r}"

    # Concrete implementations
    from rune_decrypter_prime.scoring.rune_scorer import RuneScorer
    from rune_decrypter_prime.scoring.torch_rune_scorer import RuneScorerTorch
    from rune_decrypter_prime.scoring.unified_rune_scorer import UnifiedRuneScorer

    if impl is ScorerImpl.NUMPY:
        return RuneScorer(c_cfg, s_cfg)
    elif impl is ScorerImpl.TORCH:
        return RuneScorerTorch(c_cfg, s_cfg)
    elif impl is ScorerImpl.UNIFIED:
        return UnifiedRuneScorer(c_cfg, s_cfg)
    elif impl is ScorerImpl.AUTO:
        return RuneScorer(c_cfg, s_cfg)
    else:
        raise ValueError(f"Unknown scorer impl: {impl!r}")
