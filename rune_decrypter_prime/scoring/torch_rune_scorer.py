# ============================================================
# rune_decrypter_prime/scoring/torch_rune_scorer.py
# ============================================================
"""
torch_rune_scorer.py — Torch-based scorer for 'pct.logp.winK'

Purpose
-------
Implements the normalized 'pct.logp.winK' objective on CPU/CUDA:
  per-position logp (device) → overlapping window means → ECDF (CPU) → convex mix → mean

Behavioral Guarantees
---------------------
- Only the 'pct.logp' family is implemented; other objectives raise a clear error.
- If the input length L < win, returns a constant floor value and records telemetry.
- Device-agnostic: tensors live on self.device; ECDF runs on CPU.
- Telemetry never raises; it’s best-effort.

Inputs/Outputs
--------------
- Inputs: pt_b (uint8 ndarray [B, L]); optional wli_b (uint8 ndarray).
- Output: float32 ndarray [B] in [0, 1].

Notes
-----
This file is deliberately conservative about behavior; changes here must not alter
numerical outputs without an explicit test update.
"""
# todo tidy this mf u
from __future__ import annotations
from typing import Iterable, Sequence, List, Dict, Any, Tuple
import numpy as np
import torch

# Lookup Tables
from rune_decrypter_prime.scoring.unified_tables import (
    TablesProvider,
    RuntimeTablesProvider,
)
# ECDF cache (same as NumPy runtime uses)
from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import ECDFCache
from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.scoring.base_scorer import BaseScorer
from rune_decrypter_prime.utils.telemetry import stash as _tstash
from rune_decrypter_prime.scoring.base_scorer import BaseScorer, normalize_objective as _norm_obj
from rune_decrypter_prime.core.config import ScoringConfig
from rune_decrypter_prime.core.config import CipherConfig

# ==================== Boundary dtype helpers (private) =====================

def _as_uint32_tokens_torch(arr, device: torch.device):
    """
    Convert a CPU array-like of token values (uint8/uint32) to a torch tensor on `device` with dtype uint32.
    Safe for hashing pipelines that expect 32-bit unsigned tokens.
    """
    t = torch.as_tensor(arr, device=device)
    if t.dtype != torch.uint32:
        t = t.to(torch.uint32)
    return t


def _as_int64_indices_torch(arr, device: torch.device):
    """
    Convert array-like indices to torch.int64 on `device` for safe gather/index_select ops.
    """
    return torch.as_tensor(arr, dtype=torch.int64, device=device)


def _as_lut_keys_int64_torch(keys_uint64, device: torch.device):
    """
    Prepare LUT keys for GPU/CPU use:
      - Input: numpy uint64 array (common in your tables)
      - Output: torch int64 tensor on `device`
    We reinterpret the 64-bit pattern as signed int64 (matching hashing/indexing).
    """
    if hasattr(keys_uint64, "dtype"):
        if keys_uint64.dtype == np.uint64:
            view_i64 = keys_uint64.view(np.int64)  # reinterpret without copy
            return torch.as_tensor(view_i64, dtype=torch.int64, device=device)
        if keys_uint64.dtype == np.int64:
            return torch.as_tensor(keys_uint64, dtype=torch.int64, device=device)
    t = torch.as_tensor(keys_uint64, device=device)
    return t.to(torch.int64)


def _as_lut_logp_float32_torch(logp, device: torch.device):
    """
    Prepare LUT log-probabilities:
      - Ensures torch.float32 on `device`.
    """
    t = torch.as_tensor(logp, device=device)
    if t.dtype != torch.float32:
        t = t.to(torch.float32)
    return t


# ------------------------- Hash (XXH64 over N x uint32) -------------------------
def _xxh64_u32words_cpu(tokens_u32: torch.Tensor | np.ndarray) -> np.ndarray:
    """CPU reference hashing; returns uint64 numpy array with same leading dims."""
    if isinstance(tokens_u32, torch.Tensor):
        t = tokens_u32.detach().cpu().numpy().astype(np.uint32, copy=False)
    else:
        t = tokens_u32
    assert t.dtype == np.uint32 and t.ndim >= 1
    n = t.shape[-1]
    assert n in (1, 2, 3, 4)
    u64 = np.uint64

    def rotl64(x: np.ndarray, r: int) -> np.ndarray:
        return ((x << r) | (x >> u64(64 - r))) & u64(0xFFFFFFFFFFFFFFFF)

    P1 = u64(0x9E3779B185EBCA87)
    P2 = u64(0xC2B2AE3D27D4EB4F)
    P3 = u64(0x165667B19E3779F9)
    P4 = u64(0x85EBCA77C2B2AE63)
    P5 = u64(0x27D4EB2F165667C5)
    MASK64 = u64(0xFFFFFFFFFFFFFFFF)

    total_len = u64(n * 4)
    h = (P5 + total_len) & MASK64
    t_u64 = t.astype(u64, copy=False)

    if n == 1:
        k1 = (t_u64[..., 0] * P2) & MASK64
        k1 = rotl64(k1, 31)
        k1 = (k1 * P1) & MASK64
        h ^= k1
        h = (rotl64(h, 27) * P1 + P4) & MASK64
    elif n == 2:
        k1 = ((t_u64[..., 0] | (t_u64[..., 1] << u64(32))) * P2) & MASK64
        k1 = rotl64(k1, 31)
        k1 = (k1 * P1) & MASK64
        h ^= k1
        h = (rotl64(h, 27) * P1 + P4) & MASK64
    elif n == 3:
        k1 = ((t_u64[..., 0] | (t_u64[..., 1] << u64(32))) * P2) & MASK64
        k1 = rotl64(k1, 31)
        k1 = (k1 * P1) & MASK64
        h ^= k1
        h = (rotl64(h, 27) * P1 + P4) & MASK64
        h ^= (t_u64[..., 2] * P1) & MASK64
        h = (rotl64(h, 23) * P2 + P3) & MASK64
    else:  # 4
        for i in range(4):
            k1 = (t_u64[..., i] * P2) & MASK64
            k1 = rotl64(k1, 31)
            k1 = (k1 * P1) & MASK64
            h ^= k1
            h = (rotl64(h, 27) * P1 + P4) & MASK64

    # avalanche
    h ^= (h >> u64(33))
    h = (h * P2) & MASK64
    h ^= (h >> u64(29))
    h = (h * P3) & MASK64
    h ^= (h >> u64(32))
    return h


def _xxh64_u32words_device(tokens_u32: torch.Tensor) -> torch.Tensor:
    """GPU hashing; falls back to CPU path if uint64 ops aren’t available on the device."""
    assert tokens_u32.dtype == torch.uint32
    n = tokens_u32.shape[-1]
    assert n in (1, 2, 3, 4)
    device = tokens_u32.device

    try:
        P1 = torch.tensor(0x9E3779B185EBCA87, dtype=torch.uint64, device=device)
        P2 = torch.tensor(0xC2B2AE3D27D4EB4F, dtype=torch.uint64, device=device)
        P3 = torch.tensor(0x165667B19E3779F9, dtype=torch.uint64, device=device)
        P4 = torch.tensor(0x85EBCA77C2B2AE63, dtype=torch.uint64, device=device)
        P5 = torch.tensor(0x27D4EB2F165667C5, dtype=torch.uint64, device=device)
        MASK64 = torch.tensor(0xFFFFFFFFFFFFFFFF, dtype=torch.uint64, device=device)

        total_len = torch.tensor(n * 4, dtype=torch.uint64, device=device)
        h = (P5 + total_len) & MASK64

        t = tokens_u32.to(torch.uint64)
        if n == 1:
            k1 = (t[..., 0] * P2) & MASK64
            k1 = ((k1 << 31) | (k1 >> (64 - 31))) & MASK64
            k1 = (k1 * P1) & MASK64
            h ^= k1
            h = (((h << 27) | (h >> (64 - 27))) * P1 + P4) & MASK64
        elif n == 2:
            k1 = ((t[..., 0] | (t[..., 1] << 32)) * P2) & MASK64
            k1 = ((k1 << 31) | (k1 >> (64 - 31))) & MASK64
            k1 = (k1 * P1) & MASK64
            h ^= k1
            h = (((h << 27) | (h >> (64 - 27))) * P1 + P4) & MASK64
        elif n == 3:
            k1 = ((t[..., 0] | (t[..., 1] << 32)) * P2) & MASK64
            k1 = ((k1 << 31) | (k1 >> (64 - 31))) & MASK64
            k1 = (k1 * P1) & MASK64
            h ^= k1
            h = (((h << 27) | (h >> (64 - 27))) * P1 + P4) & MASK64
            h ^= (t[..., 2] * P1) & MASK64
            h = (((h << 23) | (h >> (64 - 23))) * P2 + P3) & MASK64
        else:
            for i in range(4):
                k1 = (t[..., i] * P2) & MASK64
                k1 = ((k1 << 31) | (k1 >> (64 - 31))) & MASK64
                k1 = (k1 * P1) & MASK64
                h ^= k1
                h = (((h << 27) | (h >> (64 - 27))) * P1 + P4) & MASK64

        h ^= (h >> 33)
        h = (h * P2) & MASK64
        h ^= (h >> 29)
        h = (h * P3) & MASK64
        h ^= (h >> 32)
        return h.to(torch.int64)
    except Exception:
        # Fallback to CPU path and return on device
        return torch.from_numpy(_xxh64_u32words_cpu(tokens_u32).view(np.int64)).to(device)


# ------------------------- Probe (linear) -------------------------
def _probe_linear(keys_i64: torch.Tensor,
                  logp_f32: torch.Tensor,
                  mask: int,
                  h: torch.Tensor,
                  fallback_logp: float) -> torch.Tensor:
    """
    Open-addressing linear probe with wrap-around.
    keys_i64/logp_f32: [T] on device
    h: [...], int64 hashes
    mask: power-of-two-1
    returns: float32 per hashed item
    """
    device = keys_i64.device
    kdtype = keys_i64.dtype
    idx = (h & torch.tensor(mask, dtype=kdtype, device=device)).to(torch.long)
    out = torch.full(h.shape, fill_value=fallback_logp, dtype=torch.float32, device=device)
    found = torch.zeros(h.shape, dtype=torch.bool, device=device)

    # bounded steps to keep deterministic
    for _ in range(1024):
        k = keys_i64[idx]
        is_empty = (k == 0)
        is_match = (k == h)
        take = (~found) & is_match
        if take.any():
            out[take] = logp_f32[idx[take]]
            found[take] = True
        cont = (~found) & (~is_empty)
        if not cont.any():
            break
        idx[cont] = (idx[cont] + 1) & mask
    return out


# =============================== Scorer ===================================
class RuneScorerTorch(BaseScorer):
    """
    Torch scorer with a normalized objective:
       - 'pct.logp.win10'  (OVERLAPPING windows, ECDF per window, convex mix, mean) -> [0,1]
    Legacy objectives remain available via the older path in _score_batch_impl.
    """

    def __init__(self, cfg_cipher, scfg_scorer_params, tables: TablesProvider | None = None):
        self.cfg_cipher = cfg_cipher
        self.cfg_scorer = scfg_scorer_params

        # Device (single canonical selector)
        device_req = str(getattr(cfg_cipher, "device", "auto") or "auto")
        dev_name, _xp = select_backend(device_req)
        self.device = torch.device("cuda" if dev_name == "cuda" else "cpu")

        self._encoding_dir = getattr(self.cfg_scorer, "encoding_dir", "fwd")

        self._include_char = bool(getattr(self.cfg_scorer,"include_char", True))
        self._use_word_breaks = bool(getattr(self.cfg_scorer,"use_word_breaks", True))
        self._use_wli_cfg = self._use_word_breaks  # keep legacy alias alive


        # todo base class stuff right here
        # --- Weights & orders selection ---
        # Prefer dict-weights (new model). If either map is non-empty, we are in dict mode.
        # todo this is the dict data class thing again
        # TODO: normalize dataclass vs dict access upstream
        char_map = getattr(self.cfg_scorer, "char_weights", None)
        if char_map is None or char_map == {}:
            if isinstance(self.cfg_scorer, dict):
                char_map = self.cfg_scorer.get("char_weights", {})
            else:
                char_map = {}
        wli_map = getattr(self.cfg_scorer, "char_weights", None)
        if wli_map is None or wli_map == {}:
            if isinstance(self.cfg_scorer, dict):
                wli_map = self.cfg_scorer.get("wli_weights", {})
            else:
                wli_map = {}
        # todo check this sketch af
        map_mode = (bool(char_map) or bool(wli_map))
        if map_mode:
            # Normalize maps and keep only positive weights; sort by n for deterministic order
            self._char_weights = {int(n): float(w) for n, w in char_map.items() if float(w) > 0.0}
            self._wli_weights = {int(n): float(w) for n, w in wli_map.items() if float(w) > 0.0}
            self._n_char = None
            self._n_wli = None
            # Orders for telemetry
            orders = {
                "char": sorted(self._char_weights) if (self._include_char and self._char_weights) else [],
                "wli": sorted(self._wli_weights) if (self._use_wli_cfg and self._wli_weights) else [],
            }
            # Sanity: at least one active model
            if not (orders["char"] or orders["wli"]):
                raise ValueError("char_weights/wli_weights provided but no active models; "
                                 "check include_char/use_word_breaks and weight maps.")
        else:
            # Legacy single-order path
            self._n_char = int(self.cfg_scorer.get("n_char", 2))
            self._n_wli = int(self.cfg_scorer.get("n_wli", 2))
            if not (1 <= self._n_char <= 4 and 1 <= self._n_wli <= 4):
                raise ValueError("n_char and n_wli must be in {1,2,3,4}")
            # Pair weights (normalized); disable when channels off
            w_char, w_wli = self.cfg_scorer.get("weights", (0.5, 0.5))
            if not self._include_char:
                w_char = 0.0
            if not self._use_wli_cfg:
                w_wli = 0.0
            s = (w_char + w_wli) or 1.0
            self._w_char = float(w_char / s)
            self._w_wli = float(w_wli / s)
            self._char_weights = None
            self._wli_weights = None
            # Orders for telemetry
            orders = {
                "char": [self._n_char] if self._include_char else [],
                "wli": [self._n_wli] if self._use_wli_cfg else [],
            }

        # Determinism
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

        # Config # todo legacy remove  safely
        self.n_char = int(getattr(self.cfg_scorer, "n_char", 2))
        self.n_wli = int(getattr(self.cfg_scorer, "n_wli", 2))
        self.win = int(getattr(self.cfg_scorer, "win", 10))
        self.stride = int(getattr(self.cfg_scorer, "stride", 1)) or 1

        #self.objective = str(getattr(cfg_scorer_params, "objective", "pct.logp.win10"))

        self.include_char = bool(getattr(self.cfg_scorer, "include_char", True))
        self.use_wli = bool(getattr(self.cfg_scorer, "use_word_breaks", True))
        self.se_mode = str(getattr(self.cfg_scorer, "se_mode", "nose")).lower()
        # todo prefer 'direction', fallback to 'dir', default to 'fwd'
        self.direction = str(
            getattr(self.cfg_scorer, "direction",
                    getattr(self.cfg_scorer, "dir", "fwd"))
        ).lower()

        # Weights: either pair (legacy) or per-model dicts
        self.weights = tuple(getattr(self.cfg_scorer, "weights", (0.5, 0.5)))
        self.char_weights: Dict[int, float] | None = getattr(self.cfg_scorer, "char_weights", None)
        self.wli_weights: Dict[int, float] | None = getattr(self.cfg_scorer, "wli_weights", None)

        # ECDF clamps
        self._ecdf_floor = float(getattr(self.cfg_scorer, "ecdf_floor", 1e-6))
        self._ecdf_ceiling = float(getattr(self.cfg_scorer, "_ecdf_ceiling", 1.0))

        # Dtype (telemetry only; runtime uses float32)
        self._dtype_str = str(getattr(self.cfg_scorer, "dtype", "float32"))

        # Tables provider (ngram hash -> logp)
        self._prov: TablesProvider | None = tables
        self._loaded_device = None
        self._tables: Dict[Tuple[str, int], Dict[str, Any]] = {}

        # ECDF cache (same buckets as NumPy runtime)
        self._ecdf = ECDFCache(root=getattr(self.cfg_scorer, "model_root", None))

        # todo errr
        # Windowing (honour cfg.win; tests set objective to pct.logp.win10 and really choosing other options could cause explosions, but they did all work at one point)
        self._win = int(getattr(self.cfg_scorer, "win", 10))
        self._stride = int(getattr(self.cfg_scorer, "stride", 1)) or 1

        # Runtime “position” mode (affects ECDF bucket selection)
        self._se = str(getattr(self.cfg_scorer, "se_mode", "nose")).lower()  # "nose" | "wise"

        # # Objective
        # self._objective = str(getattr(self.cfg_scorer, "objective", "pct.logp.win10")).lower()
        raw_obj = str(getattr(self.cfg_scorer, "objective", "pct.logp.win10"))
        norm_obj = _norm_obj(raw_obj, int(getattr(self, "win", 10)))
        self.objective = norm_obj
        self._objective = norm_obj

        # Channel usage
        self._include_char = bool(getattr(self.cfg_scorer, "include_char", True))
        self._use_wli_cfg = bool(getattr(self.cfg_scorer, "use_word_breaks", True))

        # Telemetry
        self._telemetry = {
            "impl": "numpy",  # kept as-is from your base; updated in telemetry()
            "device": "cuda",  # kept as-is from your base; updated in telemetry()
            "dir": self.direction,
            "dtype": self._dtype_str,
            "objective": self._objective,
            "win": self._win,
            "stride": self._stride,
            "ecdf_floor": self._ecdf_floor,
            "_ecdf_ceiling": self._ecdf_ceiling,
            "encoding_dir": self._encoding_dir,
            "orders": {
                "char": [self.n_char] if self._ecdf_ceiling else [],
                "wli": [self.n_wli] if self._use_wli_cfg else [],
            },
        }

    # ---------- tables ----------
    def ensure_loaded(self, device: torch.device) -> None:
        if self._loaded_device is not None and str(self._loaded_device) == str(device):
            return
        if self._prov is None:
            self._prov = RuntimeTablesProvider(self.cfg_cipher, self.cfg_scorer)
        self._tables.clear()

        need_char = self.include_char
        need_wli = self.use_wli

        if need_char:
            jt = self._prov.get_joint_table("char", int(self.n_char))
            self._tables[("char", int(self.n_char))] = {
                "keys": _as_lut_keys_int64_torch(jt.keys, device=device),
                "logp": _as_lut_logp_float32_torch(jt.logp, device=device),
                "mask": int(jt.mask),
                "stats": dict(jt.stats),
            }

        if need_wli:
            jt = self._prov.get_joint_table("wli", int(self.n_wli))
            self._tables[("wli", int(self.n_wli))] = {
                "keys": _as_lut_keys_int64_torch(jt.keys, device=device),
                "logp": _as_lut_logp_float32_torch(jt.logp, device=device),
                "mask": int(jt.mask),
                "stats": dict(jt.stats),
            }

        self._loaded_device = device

    def _ensure_table(self, model: str, n: int) -> Dict[str, Any]:
        if (model, int(n)) in self._tables:
            return self._tables[(model, int(n))]
        jt = self._prov.get_joint_table(model, int(n))
        d = {
            "keys": _as_lut_keys_int64_torch(jt.keys, device=self.device),
            "logp": _as_lut_logp_float32_torch(jt.logp, device=self.device),
            "mask": int(jt.mask),
            "stats": dict(jt.stats),
        }
        self._tables[(model, int(n))] = d
        return d

    # ---------- model selection ----------
    # ---------- model selection ----------
    def _active_models(self, use_wli_now: bool) -> List[Tuple[str, int, float]]:
        """
        Return a list of (channel, n, weight) and L1-normalize across the whole set.
        Dict-weight mode is used when maps exist; legacy single-order otherwise.
        """
        models: List[Tuple[str, int, float]] = []

        if (self._char_weights and len(self._char_weights) > 0) or (self._wli_weights and len(self._wli_weights) > 0):
            # Dict-weight mode
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

    # ---------- ECDF mapping ----------
    def _percentiles(self, model: str, n: int, means_np: np.ndarray) -> np.ndarray:
        # Load the same bucket used by NumPy runtime: (model, direction, pos, n, stat="logp")
        grid, q = self._ecdf.load(model=model, mode=self.direction, pos=self.se_mode, n=int(n), stat="logp")
        u = np.interp(means_np.astype(np.float32, copy=False), grid, q, left=0.0, right=1.0).astype(np.float32, copy=False)
        if self._ecdf_floor > 0.0:
            u = np.maximum(u, np.float32(self._ecdf_floor))
        if self._ecdf_ceiling < 1.0:
            u = np.minimum(u, np.float32(self._ecdf_ceiling))
        return u

    # ---------- tokens packing ----------
    def _pack_char_ngram(self, pt_t: torch.Tensor, n: int) -> torch.Tensor:
        B, L = pt_t.shape
        s = pt_t.stride()
        Wn = L - n + 1
        return (pt_t.as_strided((B, Wn, n), (s[0], s[1], s[1])) & 0x1F).to(torch.uint32)

    def _pack_wli_ngram(self, pt_t: torch.Tensor, wli_t: torch.Tensor, n: int) -> torch.Tensor:
        B, L = pt_t.shape
        s_pt = pt_t.stride()
        s_w = wli_t.stride()
        Wn = L - n + 1
        pt_win = pt_t.as_strided((B, Wn, n), (s_pt[0], s_pt[1], s_pt[1]))
        w_win = wli_t.as_strided((B, Wn, n, 2), (s_w[0], s_w[1], s_w[1], s_w[2]))
        rune = (pt_win & 0x1F).to(torch.int32)
        pos = (w_win[..., 0] & 0x3F).to(torch.int32)
        ln = (w_win[..., 1] & 0x3F).to(torch.int32)
        toks = torch.stack([rune[..., i] | (pos[..., i] << 5) | (ln[..., i] << 11) for i in range(n)], dim=-1)
        return toks.to(torch.uint32)

    # ---------- normalized path ----------
    def _score_pct_logp_win(self, pt_b: np.ndarray, wli_b: np.ndarray | None) -> np.ndarray:
        """
        per-position logp (device) -> overlapping window means (K=win-n+1) -> ECDF (CPU) -> convex mix -> mean
        returns (B,) float32 in [0,1]
        """
        self.ensure_loaded(self.device)
        B, L = int(pt_b.shape[0]), int(pt_b.shape[1])

        if L < int(self.win):
            out = np.full((B,), float(self._ecdf_floor), dtype=np.float32)
            # Telemetry (no-throw). Preserve existing keys/values.
            if B == 1:
                self._last_stats = {
                    "objective": f"pct.logp.win{int(self.win)}",
                    "score_mean": float(out[0]),
                    "score_std": 0.0,
                    "n_windows": 0,
                }
            else:
                self._last_stats = {
                    "objective": f"pct.logp.win{int(self.win)}",
                    "score_mean_batch": out.astype(np.float32, copy=False).tolist(),
                    "score_std_batch": [0.0] * B,
                    "n_windows": 0,
                }
            # ensure holder exists, then stash
            tele_holder = self.__dict__.setdefault("_telemetry", {})
            _tstash(tele_holder, **self._last_stats)

            # try:
            #     if not hasattr(self, "_last_stats"):
            #         self._last_stats = {}
            #     if not hasattr(self, "_telemetry"):
            #         self._telemetry = {}
            #     if B == 1:
            #         self._last_stats = {
            #             "objective": f"pct.logp.win{int(self.win)}",
            #             "score_mean": float(out[0]),
            #             "score_std": 0.0,
            #             "n_windows": 0,
            #         }
            #     else:
            #         self._last_stats = {
            #             "objective": f"pct.logp.win{int(self.win)}",
            #             "score_mean_batch": out.astype(np.float32, copy=False).tolist(),
            #             "score_std_batch": [0.0] * B,
            #             "n_windows": 0,
            #         }
            #     self._telemetry.update(self._last_stats)
            # except Exception:
            #     pass

            return out

        pt_t = torch.from_numpy(pt_b).to(self.device, dtype=torch.uint8, non_blocking=True)
        wli_t = None
        if wli_b is not None and self.use_wli:
            wli_t = torch.from_numpy(wli_b).to(self.device, dtype=torch.uint8, non_blocking=True)

        nwin = L - int(self.win) + 1
        mix = np.zeros((B, nwin), dtype=np.float32)

        for channel, n, w in self._active_models(self._use_wli_cfg):
            # per-position logp
            if channel == "char":
                toks = self._pack_char_ngram(pt_t, int(n))  # [B, Wn, n]
            else:
                if wli_t is None:
                    continue
                toks = self._pack_wli_ngram(pt_t, wli_t, int(n))  # [B, Wn, n]

            h = _xxh64_u32words_device(toks) if self.device.type == "cuda" else torch.from_numpy(
                _xxh64_u32words_cpu(toks).view(np.int64)
            ).to(self.device)

            tbl = self._ensure_table(channel, int(n))
            lp_seq = _probe_linear(
                tbl["keys"], tbl["logp"], tbl["mask"], h, tbl["stats"]["fallback_logp"]
            )  # [B, Wn]

            # Overlapping window means over K = win - n + 1
            K = int(self.win) - int(n) + 1
            if K <= 0 or lp_seq.shape[1] < K:
                means = torch.empty((B, 0), dtype=torch.float32, device=self.device)
            else:
                means = lp_seq.unfold(dimension=1, size=K, step=1).contiguous().mean(dim=-1)  # [B, nwin]

            # ECDF on CPU; returns numpy float32 in [0,1] with shape [B, nwin]
            u = self._percentiles(channel, int(n), means.detach().cpu().numpy())
            mix += float(w) * u

        # compute mean/std, stash telemetry, return mean
        score_mean_vec = mix.mean(axis=1).astype(np.float32, copy=False)
        score_std_vec = mix.std(axis=1).astype(np.float32, copy=False)

        try:
            # --- Telemetry (no-throw; centralized via util.telemetry.stash) ---

            # Base stats (single-batch vs multi-batch)
            if int(mix.shape[0]) == 1:
                self._last_stats = {
                    "objective": f"pct.logp.win{int(self.win)}",
                    "n_windows": int(mix.shape[1]),
                    "score_mean": float(score_mean_vec[0]),
                    "score_std": float(score_std_vec[0]),
                    "window_scores": mix[0].tolist(),
                }
            else:
                self._last_stats = {
                    "objective": f"pct.logp.win{int(self.win)}",
                    "n_windows": int(mix.shape[1]),
                    "score_mean_batch": score_mean_vec.astype(np.float32).tolist(),
                    "score_std_batch": score_std_vec.astype(np.float32).tolist(),
                }

            # Scorer sub-meta (parity with NumPy)
            scorer_meta = {
                "impl": "torch",
                "device": self.device.type,
                "dir": getattr(self, "direction", "fwd"),
                "dtype": "float32",
                "objective": f"pct.logp.win{int(self.win)}",
                "win": int(self.win),
                "stride": int(getattr(self, "stride", 1)),
                "ecdf_floor": float(self._ecdf_floor),
                "ecdf_ceiling": float(self._ecdf_ceiling),
                # optional back-compat for any consumer expecting the legacy underscore key
                "_ecdf_ceiling": float(self._ecdf_ceiling),
                # keep explicit 2-gram listing for parity with existing logs
                "orders": {"char": [2], "wli": [2]} if getattr(self, "use_wli", False) else {"char": [2]},
                "n_windows": int(mix.shape[1]),
                "direction": getattr(self, "direction", "fwd"),
            }

            # weights summary
            sum_w = 0.0
            active_models = []
            for ch, n, w in self._active_models(self._use_wli_cfg):
                active_models.append((ch, int(n), float(w)))
                try:
                    sum_w += float(w)
                except Exception:
                    # best-effort only; don't let weird types break telemetry
                    pass
            scorer_meta["active_models"] = active_models
            scorer_meta["sum_weights"] = float(sum_w)

            self._stash_stats(scorer=scorer_meta)  # sub-map
            self._stash_stats(**self._last_stats)  # mirror mean/std at top-level
        except Exception:
            pass

        return score_mean_vec.astype(np.float32, copy=False)

    # def _score_batch_impl(self, pt_b: np.ndarray, wli_b: np.ndarray | None) -> np.ndarray:
    #     """
    #     Unified scorer entry:
    #       - pct.logp.winK / pct.logp  => normalized path (_score_pct_logp_win)
    #       - legacy aliases (energy.logp, energy, logp.energy) => mapped to pct.logp.win{self.win}
    #       - anything else => deterministic error
    #     """
    #
    #     # ---- normalize objective (expunge legacy here) ----
    #     def _normalize_objective(obj: str, default_win: int) -> str:
    #         if not obj:
    #             return f"pct.logp.win{int(default_win)}"
    #         o = obj.lower().strip()
    #         if o in {"energy.logp", "energy", "logp.energy"}:
    #             return f"pct.logp.win{int(default_win)}"
    #         if o.startswith("pct.logp.win"):
    #             return o
    #         if o.startswith("pct.logp"):
    #             # allow "pct.logp" without explicit win -> use current window
    #             return f"pct.logp.win{int(default_win)}"
    #         return o  # leave as-is; we'll gate below
    #
    #     # cache-normalize on the instance so later telemetry reflects the mapped value
    #     self.objective = _normalize_objective(str(getattr(self, "objective", "")), int(getattr(self, "win", 10)))
    #
    #     obj = str(self.objective).lower().strip()
    #     if obj.startswith("pct.logp.win"):
    #         return self._score_pct_logp_win(pt_b, wli_b)
    #
    #     raise NotImplementedError(
    #         f"Torch scorer: objective '{self.objective}' is not implemented. Supported: pct.logp.winK"
    #     )
    def _score_batch_impl(self, pt_b: np.ndarray, wli_b: np.ndarray | None) -> np.ndarray:
        """
        Unified scorer entry:
          - pct.logp.winK / pct.logp  => normalized path (_score_pct_logp_win)
          - legacy aliases (energy.logp, energy, logp.energy) => mapped to pct.logp.win{self.win}
          - anything else => deterministic error
        """
        # normalize once per call (also stored on the instance)
        self.objective = _norm_obj(getattr(self, "objective", ""), int(getattr(self, "win", 10)))
        obj = str(self.objective).lower().strip()
        if obj.startswith("pct.logp.win"):
            return self._score_pct_logp_win(pt_b, wli_b)

        raise NotImplementedError(
            f"Torch scorer: objective '{self.objective}' is not implemented. Supported: pct.logp.winK"
        )

    # ---------- public API ----------
    def batch_score(self, pts: Sequence[Iterable[int]], wlis=None) -> np.ndarray:
        if not pts:
            return np.zeros((0,), dtype=np.float32)
        P = [np.asarray(p, np.uint8) for p in pts]
        pt_b = np.stack(P, axis=0)

        wli_b = None
        if wlis is not None and bool(self.use_wli):
            if isinstance(wlis, np.ndarray):
                if wlis.ndim == 2 and wlis.shape[1] == 2:
                    wli_b = np.stack([wlis] * len(P), axis=0).astype(np.uint8, copy=False)
                elif wlis.ndim == 3 and wlis.shape[0] == len(P) and wlis.shape[2] == 2:
                    wli_b = wlis.astype(np.uint8, copy=False)
                else:
                    raise ValueError("wlis must be (L,2) or (B,L,2)")
            elif isinstance(wlis, (list, tuple)) and len(wlis) == len(P):
                wli_b = np.stack([np.asarray(w, np.uint8) for w in wlis], axis=0)
            else:
                w0 = np.asarray(wlis, np.uint8)
                if w0.ndim == 2 and w0.shape[1] == 2:
                    wli_b = np.stack([w0] * len(P), axis=0)
                else:
                    raise ValueError("wlis list must be list[(L,2)] or a single (L,2)")

        return self._score_batch_impl(pt_b, wli_b)

    def score(self, pt: Iterable[int], wli=None) -> float:
        return float(self.batch_score([np.asarray(pt, np.uint8)], wli)[0])

    def telemetry(self) -> Dict[str, Any]:
        models = self._active_models(self._use_wli_cfg)
        self._telemetry.update({
            "impl": "torch",
            "device": self.device.type,
            "objective": self.objective,
            "win": self.win,
            "stride": self.stride,
            "ecdf_floor": self._ecdf_floor,
            "active_models": [(c, int(n), float(w)) for (c, n, w) in models],
            "sum_weights": float(sum(w for _, _, w in models)),
        })
        self._telemetry.update(getattr(self, "_last_stats", {}))
        return dict(self._telemetry)
