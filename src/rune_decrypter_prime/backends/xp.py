# ============================================================
# rune_decrypter_prime/backends/xp.py
# Unified array backend adapter with optional CuPy/Torch support.
# Exposes a minimal NumPy-like API used by scoring/optimisers.
# No behavioural change: selection logic and ops preserved.
# ============================================================

from __future__ import annotations

# ---------- optional imports ----------
def _try_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None

import numpy as _np
_cp    = _try_import("cupy")     # None if not installed
_torch = _try_import("torch")    # None if not installed


def get_versions() -> dict:
    """Return available library versions. Keys only for libraries present."""
    out = {"numpy": getattr(_np, "__version__", None)}
    if _torch is not None:
        out["torch"] = getattr(_torch, "__version__", None)
    if _cp is not None:
        out["cupy"] = getattr(_cp, "__version__", None)
    return out


# ---------- capability probes ----------
def have_cupy() -> bool:
    """True iff CuPy is importable AND a CUDA/ROCm device is available."""
    if _cp is None:
        return False
    try:
        return int(_cp.cuda.runtime.getDeviceCount()) > 0
    except Exception:
        return False

def have_torch_cuda() -> bool:
    """True iff torch is importable AND reports CUDA available."""
    if _torch is None:
        return False
    try:
        return bool(_torch.cuda.is_available())
    except Exception:
        return False

def have_any_cuda() -> bool:
    return have_cupy() or have_torch_cuda()


# ---------- NumPy backend (always available) ----------
class _NumpyXP:
    backend = "numpy"
    device  = "cpu"

    # dtypes
    uint8   = _np.uint8
    int16   = _np.int16
    int64   = _np.int64
    float32 = _np.float32
    float64 = _np.float64

    # ops (NumPy passthroughs)
    def asarray(self, x, dtype=None):         return _np.asarray(x, dtype=dtype)
    def arange(self, n, dtype=None):          return _np.arange(int(n), dtype=dtype)
    def zeros(self, shape, dtype=None):       return _np.zeros(shape, dtype=dtype)
    def zeros_like(self, a, dtype=None):      return _np.zeros_like(a, dtype=dtype)
    def empty(self, shape, dtype=None):       return _np.empty(shape, dtype=dtype)
    def empty_like(self, a, dtype=None):      return _np.empty_like(a, dtype=dtype)
    def full(self, shape, fill_value, dtype=None): return _np.full(shape, fill_value, dtype=dtype)
    def concatenate(self, seq, axis=0):       return _np.concatenate([_np.asarray(a) for a in seq], axis=axis)
    def mod(self, a, m):                      return _np.mod(a, m)
    def take(self, a, idx):                   return _np.take(a, idx)
    def sum(self, a, axis=None):              return _np.sum(a, axis=axis)
    def astype(self, a, dtype):               return _np.asarray(a).astype(dtype)
    def to_numpy(self, a):                    return _np.asarray(a)
    def synchronize(self):                    return  # no-op on CPU


# ---------- CuPy backend (only if available) ----------
class _CuPyXP:
    backend = "cupy"
    device  = "cuda"

    def __init__(self):
        if not have_cupy():
            raise RuntimeError("CuPy backend requested but no CUDA device is available")
        # dtypes
        self.uint8   = _cp.uint8
        self.int16   = _cp.int16
        self.int64   = _cp.int64
        self.float32 = _cp.float32
        self.float64 = _cp.float64

    # ops
    def asarray(self, x, dtype=None):         return _cp.asarray(x, dtype=dtype)
    def arange(self, n, dtype=None):          return _cp.arange(int(n), dtype=dtype)
    def zeros(self, shape, dtype=None):       return _cp.zeros(shape, dtype=dtype)
    def zeros_like(self, a, dtype=None):      return _cp.zeros_like(a, dtype=dtype)
    def empty(self, shape, dtype=None):       return _cp.empty(shape, dtype=dtype)
    def empty_like(self, a, dtype=None):      return _cp.empty_like(a, dtype=dtype)
    def full(self, shape, fill_value, dtype=None): return _cp.full(shape, fill_value, dtype=dtype)
    def concatenate(self, seq, axis=0):       return _cp.concatenate([_cp.asarray(a) for a in seq], axis=axis)
    def mod(self, a, m):                      return _cp.mod(a, m)
    def take(self, a, idx):                   return _cp.take(a, idx)
    def sum(self, a, axis=None):              return _cp.sum(a, axis=axis)
    def astype(self, a, dtype):               return a.astype(dtype)
    def to_numpy(self, a):                    return _cp.asnumpy(a)
    def synchronize(self):                    _cp.cuda.Stream.null.synchronize()


# ---------- Torch backend (CPU or CUDA) ----------
class _TorchXP:
    backend = "torch"

    def __init__(self, device: str = "cpu"):
        if _torch is None:
            raise ImportError("torch not available")
        dev = device.lower()
        if dev not in ("cpu", "cuda"):
            raise ValueError(f"invalid torch device: {device}")
        if dev == "cuda" and not have_torch_cuda():
            raise RuntimeError("Torch CUDA requested but CUDA is not available")
        self.device = dev

        # dtypes
        self.uint8   = _torch.uint8
        self.int16   = _torch.int16
        self.int64   = _torch.int64
        self.float32 = _torch.float32
        self.float64 = _torch.float64

    # ops (NumPy-ish signatures)
    def asarray(self, x, dtype=None):
        t = _torch.as_tensor(x, device=self.device)
        return t.to(dtype) if dtype is not None else t

    def arange(self, n, dtype=None):
        t = _torch.arange(int(n), device=self.device)
        return t.to(dtype) if dtype is not None else t

    def zeros(self, shape, dtype=None):       return _torch.zeros(shape, dtype=dtype, device=self.device)
    def zeros_like(self, a, dtype=None):      return _torch.zeros_like(a, dtype=dtype, device=a.device) if dtype is not None else _torch.zeros_like(a)
    def empty(self, shape, dtype=None):       return _torch.empty(shape, dtype=dtype, device=self.device)
    def empty_like(self, a, dtype=None):      return _torch.empty_like(a, dtype=dtype, device=a.device) if dtype is not None else _torch.empty_like(a)
    def full(self, shape, fill_value, dtype=None): return _torch.full(shape, fill_value, dtype=dtype, device=self.device)
    def concatenate(self, seq, axis=0):       return _torch.cat(seq, dim=axis)
    def mod(self, a, m):                      return a.remainder(m)

    def take(self, a, idx):
        # Simple NumPy-like take, general enough for typical 1D/2D uses.
        if a.ndim == 1:
            return a[idx]
        t = a.reshape(-1)
        i = _torch.as_tensor(idx, dtype=_torch.int64, device=a.device).reshape(-1)
        out = _torch.index_select(t, 0, i)
        return out.reshape(idx.shape)

    def sum(self, a, axis=None):              return a.sum(dim=axis)
    def astype(self, a, dtype):               return a.to(dtype)
    def to_numpy(self, x):                    return x.detach().cpu().numpy()
    def synchronize(self):
        if self.device == "cuda":
            _torch.cuda.synchronize()


# ---------- public helpers ----------
def device_name(requested: str | None) -> str:
    """Return a human-ish device label for diagnostics."""
    req = (requested or "numpy").lower()
    if req in ("cupy", "cp"):
        return "cupy" if have_cupy() else "numpy"
    if req in ("torch", "pt", "pytorch", "cuda", "gpu"):
        if have_torch_cuda():
            return "torch-cuda"
        if _torch is not None:
            return "torch-cpu"
        return "numpy"
    return "numpy"


def sync():
    """Attempt to synchronise GPU queues if present (no-op on CPU)."""
    if have_cupy():
        _cp.cuda.Stream.null.synchronize()
        return
    if have_torch_cuda():
        _torch.cuda.synchronize()


def select_backend(requested: str | None = "auto"):
    """
    Returns (device_name, xp_instance) with a NumPy-like API.

    requested:
      - "auto"  : prefer CuPy, then Torch CUDA, then Torch CPU, else NumPy
      - "numpy"/"np"/"cpu": NumPy
      - "cupy"/"cp"/"cuda"/"gpu": GPU required (error if not available)
      - "torch"/"pt"/"pytorch": Torch (CUDA if available else CPU; error if torch missing)
    """
    req = (requested or "auto").lower()

    if req in ("numpy", "np", "cpu"):
        return "cpu", _NumpyXP()

    if req in ("cupy", "cp", "cuda", "gpu"):
        if have_cupy():
            return "cuda", _CuPyXP()
        if have_torch_cuda():
            return "cuda", _TorchXP(device="cuda")
        # Fail loudly if the user explicitly asked for CUDA but it's not available.
        raise RuntimeError("CUDA requested but CUDA is not available")

    if req in ("torch", "pt", "pytorch"):
        if _torch is None:
            raise ImportError("torch not available")
        if have_torch_cuda():
            return "cuda", _TorchXP(device="cuda")
        else:
            return "cpu", _TorchXP(device="cpu")

    # auto: best available
    if have_cupy():
        return "cuda", _CuPyXP()
    if have_torch_cuda():
        return "cuda", _TorchXP(device="cuda")
    if _torch is not None:
        return "cpu", _TorchXP(device="cpu")
    return "cpu", _NumpyXP()


def to_numpy(x):
    """Best-effort conversion of xp/torch/cupy arrays/tensors to NumPy."""
    if _torch is not None and hasattr(x, "detach") and hasattr(x, "cpu"):
        try:
            return x.detach().cpu().numpy()
        except Exception:
            pass
    if _cp is not None:
        try:
            if isinstance(x, _cp.ndarray):
                return _cp.asnumpy(x)
        except Exception:
            pass
    return _np.asarray(x)


__all__ = [
    "select_backend",
    "to_numpy",
    "have_cupy",
    "have_torch_cuda",
    "have_any_cuda",
    "device_name",
    "sync",
    "_NumpyXP",
    "_CuPyXP",
    "_TorchXP",
]
__all__ += ["get_versions"]

# TODO: Consider factoring common ‘ops’ docstrings/types across backends (no behaviour change).
