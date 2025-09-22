# ============================================================
# rune_decrypter_prime/backends/device.py
# Resolve the execution device and return a NumPy-like xp shim.
# Prefers CUDA (Torch/CuPy) when requested/available; else CPU.
# ============================================================

from __future__ import annotations
import os
from .xp import select_backend, to_numpy

def get_device(requested: str | None = None):
    """
    Resolve device and return (device_str, xp).

    Priority
    --------
    - If `requested` is "cpu" or empty → CPU/NumPy.
    - Else prefer CUDA backends in the order governed by RDP_CUDA_BACKEND:
        • torch (default), then cupy
        • fall back to CPU if none succeed.

    Environment
    -----------
    - RDP_DEVICE=cpu|cuda:0|…   (anything truthy and not "cpu" triggers CUDA attempt)
    - RDP_CUDA_BACKEND=torch|cupy  (default "torch")
    """
    req = (requested or os.getenv("RDP_DEVICE") or "").lower()
    if not req or req == "cpu":
        _, xp = select_backend("np")
        return "cpu", xp

    pref = (os.getenv("RDP_CUDA_BACKEND") or "torch").lower()
    order = ["torch", "cupy"] if pref == "torch" else ["cupy", "torch"]
    for backend in order:
        try:
            _, xp = select_backend(backend)
            return "cuda", xp
        except Exception:
            # Try the next backend silently; caller receives a working xp regardless.
            pass

    # Fall back to CPU/NumPy
    _, xp = select_backend("np")
    return "cpu", xp

__all__ = ["get_device", "to_numpy"]
