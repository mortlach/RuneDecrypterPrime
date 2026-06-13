# rune_decrypter_prime/core/engine/builders.py
from __future__ import annotations
from typing import Any, Mapping

from rune_decrypter_prime.core.types import Device, ScorerImpl, ensure_device, ensure_scorer_impl
from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.ciphers import registry as cipher_registry


def _cfg_get(cfg: Any, key: str, default: Any = None) -> Any:
    if isinstance(cfg, Mapping):
        return cfg.get(key, default)
    return getattr(cfg, key, default)


def build_cipher(cfg_cipher) -> Any:
    name = _cfg_get(cfg_cipher, "name", None)
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
    impl = ensure_scorer_impl(_cfg_get(s_cfg, "impl", ScorerImpl.AUTO))
    dev_raw = _cfg_get(c_cfg, "device", Device.CPU)
    device = ensure_device(dev_raw)

    # Resolve AUTO based on device.
    if impl is ScorerImpl.AUTO:
        impl = ScorerImpl.TORCH if device is Device.CUDA else ScorerImpl.NUMPY

    # Enforce CUDA availability if explicitly requested.
    if device is Device.CUDA:
        dev_name, _ = select_backend(Device.CUDA.value)
        if dev_name != Device.CUDA.value:
            raise RuntimeError(
                f"Requested accelerator is unavailable (resolved={dev_name!r})"
            )

    if impl is ScorerImpl.NUMPY:
        from rune_decrypter_prime.scoring.rune_scorer import RuneScorer

        return RuneScorer(c_cfg, s_cfg)

    if impl is ScorerImpl.TORCH:
        try:
            from rune_decrypter_prime.scoring.torch_rune_scorer import RuneScorerTorch
        except ModuleNotFoundError as exc:
            if exc.name == ScorerImpl.TORCH.value:
                requested_impl = ScorerImpl.TORCH.value
                fallback_impl = ScorerImpl.NUMPY.value
                fallback_device = Device.CPU.value
                raise RuntimeError(
                    f"Requested scorer implementation is unavailable: {requested_impl!r}. "
                    f"Install the matching optional package or use scorer impl={fallback_impl!r} "
                    f"with device={fallback_device!r}."
                ) from exc
            raise

        return RuneScorerTorch(c_cfg, s_cfg)

    if impl is ScorerImpl.UNIFIED:
        from rune_decrypter_prime.scoring.unified_rune_scorer import UnifiedRuneScorer

        return UnifiedRuneScorer(c_cfg, s_cfg)

    raise ValueError(f"Unknown scorer impl: {impl!r}")
