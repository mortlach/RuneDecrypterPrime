# ============================================================
# rune_decrypter_prime/backends/device.py
# Resolve the execution device and return a NumPy-like xp shim.
# Prefers CUDA (Torch/CuPy) when requested/available; else CPU.
# ============================================================

from __future__ import annotations
from .xp import select_backend, to_numpy

def get_device(
    requested: str | None = None,
    *,
    cuda_backend_preference: str = "torch",
):
    """
    Resolve device and return (device_str, xp).

    Priority
    --------
    - If `requested` is "cpu" or empty, return CPU/NumPy.
    - Else prefer CUDA backends in the configured order.
    - Fall back to CPU if no CUDA backend is available.
    """
    req = (requested or "").lower()
    if not req or req == "cpu":
        _, xp = select_backend("np")
        return "cpu", xp

    pref = str(cuda_backend_preference or "torch").lower()
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
