# ============================================================
# rune_decrypter_prime/core/unified_rune_scorer.py   (Unified façade)
# Selects Torch or NumPy scorer based on cfg_cipher.device; stable public API.
# ============================================================
from __future__ import annotations
from typing import Any, Iterable, Sequence, Dict
import numpy as np

from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.core.types import Direction

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
      • telemetry() -> {"impl": "...", "device": "...", "dtype": "float32", ...}
    """

    def __init__(self, cfg_cipher, cfg_scorer_params, tables: Any | None = None):
        self.cfg_cipher = cfg_cipher
        self.cfg_scorer = cfg_scorer_params
        self._backend_name = "numpy"
        self._backend = None
        device_req = str(getattr(cfg_cipher, "device", "auto") or "auto")
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
        return np.asarray(self._backend.batch_score(pts, wlis), dtype=np.float32)

    def to_text(self, plaintext: Iterable[int]) -> str:
        # Prefer backend's to_text if available; else deterministic fallback.
        if hasattr(self._backend, "to_text"):
            try:
                return self._backend.to_text(plaintext)
            except Exception:
                pass
        # Fallback uses configured word-breaks if present
        wb = getattr(self.cfg_cipher, "wli_data", []) or []
        arr = np.asarray(plaintext, dtype=np.uint8).reshape(-1)
        # TODO(docs): Confirm correct fallback helper (Runeglish vs RuneAlphabet).
        return Runeglish.np_to_text(arr, wb)  # retain behaviour; name kept in comments

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
            tel["device"] = str(dev or ("cuda" if self._backend_name == "torch" else "cpu")).lower()

        # DType is fixed float32 for both current backends
        tel.setdefault("dtype", "float32")
        return tel
