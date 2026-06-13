"""Unified façade that selects the NumPy or Torch rune scorer at runtime."""
from __future__ import annotations
from typing import Any, Iterable, Sequence, Dict
import numpy as np

from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.core.types import Device

class UnifiedRuneScorer:
    """
    Unified scorer façade (config-first).

    Selection rule:
      - If cfg_cipher.device starts with "cuda" and CUDA is available -> Torch backend
      - Else -> NumPy backend

    Public contract (stable across backends):
      • score(pt: Iterable[int], wli) -> float
      • batch_score(pts: Sequence[Iterable[int]], wlis) -> np.ndarray
      • to_text(pt: Iterable[int]) -> str
      • telemetry() -> {"impl": "...", "device": "...", "dtype": "float32|float64", ...}
    """

    def __init__(self, cfg_cipher, cfg_scorer_params, tables: Any | None = None):
        self.cfg_cipher = cfg_cipher
        self.cfg_scorer = cfg_scorer_params
        self._backend_name = "numpy"
        self._backend = None
        self._dtype = "float64"
        self._compute_dtype = "float32"
        self._acc_dtype = "float64"
        cfg_dtype = None
        cfg_compute = None
        cfg_acc = None
        if isinstance(cfg_scorer_params, dict):
            cfg_dtype = cfg_scorer_params.get("dtype")
            cfg_compute = cfg_scorer_params.get("compute_dtype")
            cfg_acc = cfg_scorer_params.get("acc_dtype")
        else:
            cfg_dtype = getattr(cfg_scorer_params, "dtype", None)
            cfg_compute = getattr(cfg_scorer_params, "compute_dtype", None)
            cfg_acc = getattr(cfg_scorer_params, "acc_dtype", None)
        if cfg_compute is not None:
            dt = str(getattr(cfg_compute, "value", cfg_compute)).strip().lower()
            if dt in {"float32", "float64"}:
                self._compute_dtype = dt
        if cfg_acc is not None:
            dt = str(getattr(cfg_acc, "value", cfg_acc)).strip().lower()
            if dt in {"float32", "float64"}:
                self._acc_dtype = dt
        if cfg_dtype is not None:
            dt = str(getattr(cfg_dtype, "value", cfg_dtype)).strip().lower()
            if dt in {"float32", "float64"}:
                self._dtype = dt
        if cfg_dtype is None:
            self._dtype = self._acc_dtype
        self._out_dtype = np.float64 if self._dtype == "float64" else np.float32

        device_req = "auto"
        cfg_device = getattr(cfg_cipher, "device", None)
        if isinstance(cfg_device, str):
            device_req = (cfg_device or "auto").strip().lower() or "auto"
        elif isinstance(cfg_device, Device):
            device_req = cfg_device.value
        elif cfg_device is not None:
            device_req = str(cfg_device).strip().lower() or "auto"

        dev_name, _xp = select_backend(device_req)
        if dev_name == "cuda":
            from rune_decrypter_prime.scoring.torch_rune_scorer import RuneScorerTorch
            self._backend = RuneScorerTorch(cfg_cipher, cfg_scorer_params, tables=tables)
            self._backend_name = "torch"
        if self._backend is None:
            from rune_decrypter_prime.scoring.rune_scorer import RuneScorer
            self._backend = RuneScorer(cfg_cipher, cfg_scorer_params)
            self._backend_name = "numpy"

    # ---------- Public API (delegate) ----------

    def score(self, plaintext: Iterable[int], wli_windows=None) -> float:
        return float(self._backend.score(plaintext, wli_windows))

    def batch_score(self, pts: Sequence[Iterable[int]], wlis=None) -> np.ndarray:
        return np.asarray(self._backend.batch_score(pts, wlis), dtype=self._out_dtype)

    def batch_score_with_raw(self, pts: Sequence[Iterable[int]], wlis=None) -> tuple[np.ndarray, np.ndarray]:
        if hasattr(self._backend, "batch_score_with_raw"):
            try:
                pct, raw = self._backend.batch_score_with_raw(pts, wlis)
            except NotImplementedError:
                pct = np.asarray(self._backend.batch_score(pts, wlis), dtype=self._out_dtype)
                return pct, pct.copy()
            return np.asarray(pct, dtype=self._out_dtype), np.asarray(raw, dtype=self._out_dtype)
        pct = np.asarray(self._backend.batch_score(pts, wlis), dtype=self._out_dtype)
        return pct, pct.copy()

    def score_with_raw(self, plaintext: Iterable[int], wli_windows=None) -> tuple[float, float]:
        if hasattr(self._backend, "score_with_raw"):
            try:
                return self._backend.score_with_raw(plaintext, wli_windows)
            except NotImplementedError:
                pct = float(self._backend.score(plaintext, wli_windows))
                return pct, pct
        pct = float(self._backend.score(plaintext, wli_windows))
        return pct, pct

    def supports_raw(self) -> bool:
        if hasattr(self._backend, "supports_raw"):
            try:
                return bool(self._backend.supports_raw())
            except Exception:
                return False
        return False

    def to_text(self, plaintext: Iterable[int]) -> str:
        # Prefer backend's to_text if available; else deterministic fallback.
        if hasattr(self._backend, "to_text"):
            try:
                return self._backend.to_text(plaintext)
            except NotImplementedError:
                pass
        # Fallback uses configured word-breaks if present
        wb = getattr(self.cfg_cipher, "wli_data", []) or []
        arr = np.asarray(plaintext, dtype=np.uint8).reshape(-1)
        wli = None
        try:
            if len(wb) == int(arr.size):
                wli = wb
        except Exception:
            wli = None
        return Runeglish.to_rune_latin(arr.tolist(), wli)

    # ---------- Telemetry (no guessing) ----------

    def telemetry(self) -> Dict[str, Any]:
        # Ask backend first
        if hasattr(self._backend, "telemetry"):
            try:
                tel = dict(self._backend.telemetry() or {})
            except Exception:
                tel = {}
        else:
            tel = {}

        # Normalise required keys
        tel.setdefault("impl", "torch" if self._backend_name == "torch" else "numpy")

        # Device preference: prefer backend-provided; else cfg/device or cpu
        if "device" not in tel or not tel["device"]:
            dev = getattr(self.cfg_cipher, "device", None)
            if isinstance(dev, Device):
                tel["device"] = dev.value
            elif isinstance(dev, str):
                tel["device"] = dev.strip().lower() or ("cuda" if self._backend_name == "torch" else "cpu")
            else:
                tel["device"] = "cuda" if self._backend_name == "torch" else "cpu"

        tel.setdefault("backend", self._backend_name)

        tel.setdefault("dtype", self._dtype)
        tel.setdefault("compute_dtype", self._compute_dtype)
        tel.setdefault("acc_dtype", self._acc_dtype)
        return tel
