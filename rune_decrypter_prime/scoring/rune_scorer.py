# ============================================================
# rune_decrypter_prime/scoring/rune_scorer.py   (NumPy scorer)
# CPU implementation of the normalized 'pct.logp.winK' objective and legacy fallbacks.
# ============================================================
from __future__ import annotations
from typing import Iterable, List, Sequence, Dict, Any, Optional, Tuple, Mapping
import dataclasses
import numpy as np

from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import LmPrimeRuntime
from rune_decrypter_prime.scoring.base_scorer import (
    BaseScorer,
    STAT_KEYS,
    parse_objective as _parse_obj,
    normalize_objective as _norm_obj,
)
from rune_decrypter_prime.utils.telemetry import stash as _tstash

STAT_KEYS = ("logp", "zsum", "madsum")

def _normalize_scfg(s_cfg):
    """Normalise ScoringConfig/dataclass/dict to a flat dict (names stable)."""
    d = {
        "objective": "pct.logp.win10",
        "n_char": None,
        "n_wli": None,
        "win": 10,
        "direction": "fwd",
        "impl": None,
        "device": None,
        "dtype": "float32",
        "char_weights": {2: 1.0},  # e.g., {2:0.4, 3:0.6}
        "wli_weights": {2: 1.0},   # e.g., {2:0.4, 3:0.6}
        "se_mode": "nose",
        "stride": 1,
        "include_char": True,
        "use_word_breaks": True,
        "ecdf_floor": 1e-6,
        "ecdf_ceiling": 1.0,
        "alpha": 0.0,
        "smoothing": None,
        "oov_policy": None,
        "weights": (0.5, 0.5),     # fallback pair weights if maps are absent
    }
    if s_cfg is None:
        pass
    elif isinstance(s_cfg, dict):
        d.update(s_cfg)
    else:
        keys = d.keys()
        d.update({k: getattr(s_cfg, k) for k in keys if hasattr(s_cfg, k)})

    # Normalise aliases
    d["direction"] = d.get("direction") or d.get("dir") or "fwd"
    d.pop("dir", None)
    return d

def _cfg_get(obj: Any, key: str, default: Any = None) -> Any:
    """Robust config getter for dicts, dataclasses, and attr-like objects."""
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    if dataclasses.is_dataclass(obj):
        return getattr(obj, key, default)
    return getattr(obj, key, default)

def _cfg_first(obj: Any, keys: tuple[str, ...], default: Any = None) -> Any:
    """Return first present key from 'keys' across dict/dataclass/attr objects."""
    for k in keys:
        v = _cfg_get(obj, k, None)
        if v is not None:
            return v
    return default

class RuneScorer(BaseScorer):
    """
    NumPy scorer using LanguageModelPrime runtime.

    Default/modern objective:
        "pct.logp.winK" (K=self._win): overlapping windows → mean logp per window
        → ECDF percentile per window → convex model mix → mean across windows.
        Returns float in [0, 1]; semantics match Torch backend.

    Legacy objectives (kept for compatibility):
        "energy.*", "avg.*", "neglogp" (single full-length window).
    """

    # ---------- ctor ----------
    def __init__(self, cfg: CipherConfig, s_cfg: ScoringConfig):
        self.cfg = cfg
        self.s_cfg = _normalize_scfg(s_cfg)

        # Cipher’s text transposition (telemetry only; not used for LM lookup)
        self._encoding_from_cipher = self._norm_dir(
            _cfg_first(cfg, ("text_transposition", "encoding_dir", "direction", "dir"), "fwd")
        )

        # Canonical scorer direction (prefer explicit scorer config)
        enc_val = _cfg_first(self.s_cfg, ("encoding_dir", "direction", "dir"), None)
        self.encoding_dir = self._norm_dir(str(enc_val or "fwd"))

        # Channel usage
        self._include_char = bool(self.s_cfg.get("include_char", True))
        self._use_word_breaks = bool(self.s_cfg.get("use_word_breaks", True))
        self._use_wli_cfg = self._use_word_breaks  # legacy alias

        # Objective + windowing
        raw_obj = str(self.s_cfg.get("objective", "pct.logp.win10"))
        self._win = int(self.s_cfg.get("win", 10))
        self._stride = int(self.s_cfg.get("stride", 1)) or 1
        self._se = str(self.s_cfg.get("se_mode", "nose")).lower()  # "nose"|"wise"
        self._objective = _norm_obj(raw_obj, self._win)

        # --- Weights & orders selection ---
        char_map = self.s_cfg.get("char_weights") or {}
        wli_map = self.s_cfg.get("wli_weights") or {}
        map_mode = (bool(char_map) or bool(wli_map))

        if map_mode:
            # Dict-weight mode
            self._char_weights = {int(n): float(w) for n, w in char_map.items() if float(w) > 0.0}
            self._wli_weights = {int(n): float(w) for n, w in wli_map.items() if float(w) > 0.0}
            self._n_char = None
            self._n_wli = None
            orders = {
                "char": sorted(self._char_weights) if (self._include_char and self._char_weights) else [],
                "wli": sorted(self._wli_weights) if (self._use_wli_cfg and self._wli_weights) else [],
            }
            if not (orders["char"] or orders["wli"]):
                raise ValueError("char_weights/wli_weights provided but no active models; "
                                 "check include_char/use_word_breaks and weight maps.")
        else:
            # Legacy single-order path
            self._n_char = int(self.s_cfg.get("n_char", 2))
            self._n_wli = int(self.s_cfg.get("n_wli", 2))
            if not (1 <= self._n_char <= 4 and 1 <= self._n_wli <= 4):
                raise ValueError("n_char and n_wli must be in {1,2,3,4}")
            w_char, w_wli = self.s_cfg.get("weights", (0.5, 0.5))
            if not self._include_char:
                w_char = 0.0
            if not self._use_wli_cfg:
                w_wli = 0.0
            s = (w_char + w_wli) or 1.0
            self._w_char = float(w_char / s)
            self._w_wli = float(w_wli / s)
            self._char_weights = None
            self._wli_weights = None
            orders = {
                "char": [self._n_char] if self._include_char else [],
                "wli": [self._n_wli] if self._use_wli_cfg else [],
            }

        # ECDF clamps + dtype
        self._ecdf_floor = float(self.s_cfg.get("ecdf_floor", 1e-6))
        self._ecdf_ceiling = float(self.s_cfg.get("ecdf_ceiling", 1.0))
        self._dtype_str = str(self.s_cfg.get("dtype", "float32"))

        # Language Model runtime (tables + ECDF)
        self._rt = LmPrimeRuntime(
            root=self.s_cfg.get("model_root", None),
            smoothing=self.s_cfg.get("smoothing", None),
            alpha=float(self.s_cfg.get("alpha", 0.0) or 0.0),
            oov_policy=self.s_cfg.get("oov_policy", None),
            include_char=self._include_char,
        )
        self._ecdf = self._rt.ecdf

        # Telemetry skeleton
        self._telemetry = {
            "name": "rune",
            "impl": "numpy",
            "device": "cpu",
            "dtype": self._dtype_str,
            "objective": self._objective,
            "win": self._win,
            "stride": self._stride,
            "ecdf_floor": self._ecdf_floor,
            "ecdf_ceiling": self._ecdf_ceiling,
            "encoding_dir": self.encoding_dir,
            "orders": orders,
        }

    # ---------- helpers ----------
    @staticmethod
    def _norm_dir(x: str | None) -> str:
        x = (x or "fwd").lower()
        return "rev" if x in ("rev", "reverse", "bwd", "back") else "fwd"

    @staticmethod
    def _u8(a) -> np.ndarray:
        x = np.asarray(a, dtype=np.uint8)
        if x.ndim == 0:
            x = x.reshape(1)
        elif x.ndim > 1:
            x = x.reshape(-1)
        return np.ascontiguousarray(x, dtype=np.uint8)

    @staticmethod
    def _to_wli_L2(w) -> np.ndarray:
        arr = np.asarray(w, dtype=np.uint8)
        if arr.ndim != 2 or arr.shape[1] != 2:
            raise ValueError(f"WLI windows must be shape (L,2); got {arr.shape}")
        return np.ascontiguousarray(arr, dtype=np.uint8)

    @staticmethod
    def _extract(bucket_out: dict, objective: str) -> np.ndarray:
        fam, stat, _win = _parse_obj(objective)
        if fam in ("pct", "energy") and stat:
            if stat not in STAT_KEYS:
                raise ValueError(f"unknown {fam} stat: {stat}")
            return bucket_out[fam][stat]
        if objective == "avg.logp":
            return bucket_out["avg"]["logp"]
        if objective == "avg.zsum":
            return bucket_out["avg"]["zsum"]
        if objective == "avg.madsum":
            return bucket_out["avg"]["madsum"]
        if objective == "neglogp":
            return -bucket_out["avg"]["logp"]
        raise ValueError(f"unknown objective: {objective}")

    def _active_models(self, use_wli_now: bool):
        """
        Return list of (channel, n, weight) for active models.
        If per-model maps exist, they select models; else single-order with pair weights.
        Output weights are L1-normalised so the mix stays in [0,1].
        """
        models = []
        # Dict-weight mode
        if (self._char_weights and len(self._char_weights) > 0) or (
            self._wli_weights and len(self._wli_weights) > 0
        ):
            if self._include_char and self._char_weights:
                for n, w in self._char_weights.items():
                    models.append(("char", int(n), float(w)))
            if use_wli_now and self._wli_weights:
                for n, w in self._wli_weights.items():
                    models.append(("wli", int(n), float(w)))
        else:
            # Legacy path
            if self._include_char:
                models.append(("char", int(self._n_char), float(self._w_char)))
            if use_wli_now:
                models.append(("wli", int(self._n_wli), float(self._w_wli)))

        tot = sum(w for _, _, w in models) or 1.0
        return [(c, n, w / tot) for (c, n, w) in models]

    def _windows(self, pt: np.ndarray, wli: Optional[np.ndarray]) -> Tuple[List[np.ndarray], Optional[List[np.ndarray]]]:
        """Build overlapping windows of length self._win, stride=1."""
        L = int(pt.shape[0])
        win = int(self._win)
        if L < win:
            return [], None if wli is None else []
        starts = range(0, L - win + 1, 1)
        pt_w = [np.ascontiguousarray(pt[s:s + win], dtype=np.uint8) for s in starts]
        if wli is None:
            return pt_w, None
        wli_w = [np.ascontiguousarray(wli[s:s + win, :], dtype=np.uint8) for s in starts]
        return pt_w, wli_w

    def score(self, plaintext: Iterable[int], wli_windows=None) -> float:
        """
        Scalar score API. Uses the normalised per-window path for standard objectives
        ('pct.logp', 'pct.logp.winK', 'energy.logp'). Falls back to legacy only for
        truly non-standard objectives.
        """
        pt = self._u8(plaintext)
        fam, stat, _win_hint = _parse_obj(self._objective)

        # Normalised vector path for recognised families
        if fam in ("pct", "energy") and stat:
            wli = None
            if wli_windows is not None:
                wli = self._to_wli_L2(wli_windows)
            pt_w, wli_w = self._windows(pt, wli)
            if len(pt_w) == 0:
                return float(self._ecdf_floor)

            use_wli_now = bool(self._use_wli_cfg and (wli_w is not None))
            models = self._active_models(use_wli_now)

            perwin = np.zeros((len(pt_w),), dtype=np.float32)
            for channel, n, w in models:
                if channel == "char":
                    call = self._rt.score_char_nose if self._se == "nose" else self._rt.score_char_wise
                    out = call(self.encoding_dir, int(n), self._win, pt_w)
                else:
                    call = self._rt.score_wli_nose if self._se == "nose" else self._rt.score_wli_wise
                    out = call(self.encoding_dir, int(n), self._win, pt_w, wli_w)

                # Extract requested family/stat (ignore '.winK' suffix)
                try:
                    u = out[fam][stat].astype(np.float32, copy=False)
                except Exception:
                    val = self._extract(out, self._objective)
                    if np.isscalar(val):
                        u = np.full((len(pt_w),), np.float32(val), dtype=np.float32)
                    else:
                        u = np.asarray(val, dtype=np.float32, copy=False)

                # Clamp only for percentile family
                if fam == "pct":
                    if self._ecdf_floor > 0.0:
                        u = np.maximum(u, np.float32(self._ecdf_floor))
                    if self._ecdf_ceiling < 1.0:
                        u = np.minimum(u, np.float32(self._ecdf_ceiling))

                perwin += float(w) * u

            mix32 = np.asarray(perwin, dtype=np.float32)
            score_mean = float(mix32.mean())
            score_std = float(mix32.std())

            # Mirror stats into telemetry (tests expect these keys present)
            self._stash_stats(dtype="float32",
            scorer={"impl": "numpy", "device": "cpu"},
            score_mean=score_mean, score_std=score_std, n_windows=int(len(mix32)))

            try:
                self._last_stats = {
                    "objective": f"{fam}.{stat}.win{int(self._win)}",
                    "n_windows": int(len(mix32)),
                    "score_mean": score_mean,
                    "score_std": score_std,
                    "window_scores": mix32.tolist(),
                }
            except Exception:
                pass
            return np.float32(score_mean)

        # Non-standard objective: legacy path
        return self._score_scalar_legacy(pt, wli_windows)

    def _score_scalar_legacy(self, pt_u8: np.ndarray, wli_windows=None) -> float:
        """
        Legacy single-window scoring path (kept for compatibility / expert use).
        """
        # CHAR
        if self._include_char:
            char_call = self._rt.score_char_nose if self._se == "nose" else self._rt.score_char_wise
            char_out = char_call(self.encoding_dir, self._n_char, self._win, [pt_u8])
            char_val = self._extract(char_out, self._objective)[0]
        else:
            char_val = 0.0

        # WLI
        use_wli_now = bool(self._use_wli_cfg) and (wli_windows is not None)
        if use_wli_now:
            wli = self._to_wli_L2(wli_windows)
            wli_call = self._rt.score_wli_nose if self._se == "nose" else self._rt.score_wli_wise
            wli_out = wli_call(self.encoding_dir, self._n_wli, self._win, [pt_u8], [wli])
            wli_val = self._extract(wli_out, self._objective)[0]
        else:
            wli_val = 0.0

        # Weights (renormalise if a channel inactive)
        w_c, w_w = self._w_char, self._w_wli
        if not self._include_char:
            w_c = 0.0
        if not use_wli_now:
            w_w = 0.0
        s = (w_c + w_w) or 1.0
        w_c /= s
        w_w /= s
        return float(w_c * float(char_val) + w_w * float(wli_val))

    def batch_score(self, pts: Sequence[Iterable[int]], wlis=None) -> np.ndarray:
        """
        Public API: returns a NumPy float32 vector of shape (B,).
        Telemetry must always include {"dtype": "float32"}.
        """
        # Empty batch: (0,) vector
        if not pts:
            try:
                self._last_stats = {
                    "objective": str(self._objective),
                    "n_windows": 0,
                    "score_mean": float(self._ecdf_floor),
                    "score_std": 0.0,
                    "window_scores": [],
                }
                self._stash_stats(dtype="float32", scorer={"impl": "numpy", "device": "cpu"})
            except Exception:
                pass
            return np.zeros((0,), dtype=np.float32)

        # Normalise and validate input
        P: List[np.ndarray] = [self._u8(p) for p in pts]
        N = len(P)
        L0 = int(P[0].shape[0])
        for i, p in enumerate(P):
            if int(p.shape[0]) != L0:
                raise ValueError(f"all plaintexts must have same length; item {i} has {p.shape[0]} vs {L0}")

        # Modern path for 'pct.logp.*'
        if self._objective.startswith("pct.logp"):
            win = int(self._win)
            nwin = max(0, L0 - win + 1)
            if nwin == 0:
                out = np.full((N,), np.float32(self._ecdf_floor), dtype=np.float32)
                try:
                    self._stash_stats(
                        dtype="float32",
                        scorer={"impl": "numpy", "device": "cpu"},
                        score_mean_batch=out.tolist(),
                        score_std_batch=[0.0] * N,
                        n_windows=int(nwin),
                    )
                except Exception:
                    pass
                return out

            # Prepare WLI once if provided (shape [L,2])
            # wli_mat = None
            # if wlis is not None:
            #     wli_mat = self._to_wli_L2(wlis)
            # Prepare WLI(s):
            #  - single ndarray(L,2) → use for all items
            #  - sequence of length N with each (L,2) → use per-item
            wli_single = None
            wli_list = None
            if wlis is not None:
                if isinstance(wlis, (list, tuple)):
                    wli_list = [self._to_wli_L2(w) for w in wlis]
                    if len(wli_list) != N:
                        raise ValueError(f"wlis list length {len(wli_list)} != batch size {N}")
                else:
                    wli_single = self._to_wli_L2(wlis)

            out = np.zeros((N,), dtype=np.float32)
            stds = np.zeros((N,), dtype=np.float32)
            for i in range(N):
                # out[i] = self.score(P[i], wli_mat)
                wli_i = wli_single if (wli_single is not None) else (wli_list[i] if wli_list is not None else None)
                out[i] = self.score(P[i], wli_i)
                try:
                    stds[i] = np.float32(float(getattr(self, "_last_stats", {}).get("score_std", 0.0)))
                except Exception:
                    stds[i] = np.float32(0.0)
            # Record batch-level telemetry (best-effort, no-throw)
            try:
                self._stash_stats(
                    dtype="float32",
                    scorer={"impl": "numpy", "device": "cpu"},
                    score_mean_batch=out.tolist(),
                    score_std_batch=stds.tolist(),
                    n_windows=int(nwin),
                )
            except Exception:
                pass
            return out

