# # ============================================================
# # rune_decrypter_prime/scoring/torch_rune_scorer.py
# # Torch backend for the normalised 'pct.logp.win10' objective
# # ============================================================
# """
# torch_rune_scorer.py — Torch-based scorer for 'pct.logp.winK'
#
# Purpose
# -------
# Implements the normalized 'pct.logp.winK' objective on CPU/CUDA:
#   per-position logp (device) → overlapping window means → ECDF (CPU) → convex mix → mean
#
# Behavioral Guarantees
# ---------------------
# - Only the 'pct.logp' family is implemented; other objectives raise a clear error.
# - If the input length L < win, returns a constant floor value and records telemetry.
# - Device-agnostic: tensors live on self.device; ECDF runs on CPU.
# - Telemetry never raises; it’s best-effort.
#
# Inputs/Outputs
# --------------
# - Inputs: pt_b (uint8 ndarray [B, L]); optional wli_b (uint8 ndarray).
# - Output: float32 ndarray [B] in [0, 1].
#
# Notes
# -----
# This file is deliberately conservative about behavior; changes here must not alter
# numerical outputs without an explicit test update.
# """
# ============================================================
# rune_decrypter_prime/scoring/torch_rune_scorer.py
# ============================================================
from __future__ import annotations
from typing import Iterable, Sequence, List, Dict, Any, Tuple, Mapping
import numpy as np
import torch

from rune_decrypter_prime.scoring.unified_tables import (
    TablesProvider,
    RuntimeTablesProvider,
)
from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import ECDFCache
from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.scoring.base_scorer import BaseScorer, normalize_objective as _norm_obj
from rune_decrypter_prime.utils.telemetry import stash as _tstash  # canonical helper  ✔

# --------------------------- small utils ---------------------------

def _cfg_get(cfg: Any, key: str, default: Any = None) -> Any:
    """Tolerant getter for dicts / dataclasses / objects."""
    try:
        if isinstance(cfg, Mapping):
            return cfg.get(key, default)
    except Exception:
        pass
    # dataclass or object
    try:
        return getattr(cfg, key)
    except Exception:
        return default

def _as_lut_keys_int64_torch(keys_uint64, device: torch.device):
    import numpy as np
    if hasattr(keys_uint64, "dtype"):
        if keys_uint64.dtype == np.uint64:
            view_i64 = keys_uint64.view(np.int64)
            return torch.as_tensor(view_i64, dtype=torch.int64, device=device)
        if keys_uint64.dtype == np.int64:
            return torch.as_tensor(keys_uint64, dtype=torch.int64, device=device)
    t = torch.as_tensor(keys_uint64, device=device)
    return t.to(torch.int64)

def _as_lut_logp_float32_torch(logp, device: torch.device):
    t = torch.as_tensor(logp, device=device)
    if t.dtype != torch.float32:
        t = t.to(torch.float32)
    return t

def _xxh64_u32words_cpu(tokens_u32: torch.Tensor | np.ndarray) -> np.ndarray:
    import numpy as np
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

    P1 = u64(0x9E3779B185EBCA87); P2 = u64(0xC2B2AE3D27D4EB4F)
    P3 = u64(0x165667B19E3779F9); P4 = u64(0x85EBCA77C2B2AE63); P5 = u64(0x27D4EB2F165667C5)
    MASK64 = u64(0xFFFFFFFFFFFFFFFF)

    total_len = u64(n * 4)
    h = (P5 + total_len) & MASK64
    t_u64 = t.astype(u64, copy=False)

    if n == 1:
        k1 = (t_u64[..., 0] * P2) & MASK64
        k1 = rotl64(k1, 31); k1 = (k1 * P1) & MASK64
        h ^= k1; h = (rotl64(h, 27) * P1 + P4) & MASK64
    elif n == 2:
        k1 = ((t_u64[..., 0] | (t_u64[..., 1] << u64(32))) * P2) & MASK64
        k1 = rotl64(k1, 31); k1 = (k1 * P1) & MASK64
        h ^= k1; h = (rotl64(h, 27) * P1 + P4) & MASK64
    elif n == 3:
        k1 = ((t_u64[..., 0] | (t_u64[..., 1] << u64(32))) * P2) & MASK64
        k1 = rotl64(k1, 31); k1 = (k1 * P1) & MASK64
        h ^= k1; h = (rotl64(h, 27) * P1 + P4) & MASK64
        h ^= (t_u64[..., 2] * P1) & MASK64
        h = (rotl64(h, 23) * P2 + P3) & MASK64
    else:
        for i in range(4):
            k1 = (t_u64[..., i] * P2) & MASK64
            k1 = rotl64(k1, 31); k1 = (k1 * P1) & MASK64
            h ^= k1; h = (rotl64(h, 27) * P1 + P4) & MASK64

    h ^= (h >> u64(33)); h = (h * P2) & MASK64
    h ^= (h >> u64(29)); h = (h * P3) & MASK64
    h ^= (h >> u64(32))
    return h

def _xxh64_u32words_device(tokens_u32: torch.Tensor) -> torch.Tensor:
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
        def _rotl(x, r): return ((x << r) | (x >> (64 - r))) & MASK64

        if n == 1:
            k1 = _rotl(t[..., 0] * P2, 31) * P1 & MASK64
            h ^= k1; h = (_rotl(h, 27) * P1 + P4) & MASK64
        elif n == 2:
            k1 = _rotl((t[..., 0] | (t[..., 1] << 32)) * P2, 31) * P1 & MASK64
            h ^= k1; h = (_rotl(h, 27) * P1 + P4) & MASK64
        elif n == 3:
            k1 = _rotl((t[..., 0] | (t[..., 1] << 32)) * P2, 31) * P1 & MASK64
            h ^= k1; h = (_rotl(h, 27) * P1 + P4) & MASK64
            h ^= (t[..., 2] * P1) & MASK64
            h = (_rotl(h, 23) * P2 + P3) & MASK64
        else:
            for i in range(4):
                k1 = _rotl(t[..., i] * P2, 31) * P1 & MASK64
                h ^= k1; h = (_rotl(h, 27) * P1 + P4) & MASK64

        h ^= (h >> 33); h = (h * P2) & MASK64
        h ^= (h >> 29); h = (h * P3) & MASK64
        h ^= (h >> 32)
        return h.to(torch.int64)
    except Exception:
        import numpy as np
        return torch.from_numpy(_xxh64_u32words_cpu(tokens_u32).view(np.int64)).to(device)

# ===================================================================

class RuneScorerTorch(BaseScorer):
    """
    Torch scorer for 'pct.logp.winK'. Behaviour matches NumPy runtime.
    """

    def __init__(self, cfg_cipher, scorer_cfg) -> None:
        # device
        device_req = str(_cfg_get(cfg_cipher, "device", "auto") or "auto")
        dev_name, _xp = select_backend(device_req)
        self.device = torch.device("cuda" if dev_name == "cuda" else "cpu")

        # core flags / numbers
        self.include_char = bool(_cfg_get(scorer_cfg, "include_char", True))
        self.use_wli = bool(_cfg_get(scorer_cfg, "use_word_breaks", True))
        self.n_char = int(_cfg_get(scorer_cfg, "n_char", 2))
        self.n_wli  = int(_cfg_get(scorer_cfg, "n_wli", 2))
        self.win    = int(_cfg_get(scorer_cfg, "win", 10))
        self.stride = int(_cfg_get(scorer_cfg, "stride", 1)) or 1

        # direction naming drift: accept encoding_dir or direction; default ltr
        self.direction = str(_cfg_get(scorer_cfg, "encoding_dir",
                           _cfg_get(scorer_cfg, "direction", "ltr"))).lower()

        # weights: legacy pair or dict maps
        self.weights = tuple(_cfg_get(scorer_cfg, "weights", (0.5, 0.5)))
        self.char_weights = _cfg_get(scorer_cfg, "char_weights", None)
        self.wli_weights  = _cfg_get(scorer_cfg, "wli_weights", None)

        # objective (Enum-only in v1)
        from rune_decrypter_prime.core.types import ObjectiveFamily, Stat, ObjectiveSpec
        obj = _cfg_get(scorer_cfg, "objective", None)
        if not (hasattr(obj, "family") and hasattr(obj, "stat")):
            # No objective provided: build the v1 default Enum spec using current win
            obj = ObjectiveSpec(ObjectiveFamily.PCT, Stat.LOGP, int(self.win))
        self.objective = obj

        # ECDF config
        self._ecdf_floor   = float(_cfg_get(scorer_cfg, "ecdf_floor", 1e-6))
        self._ecdf_ceiling = float(_cfg_get(scorer_cfg, "ecdf_ceiling", 1.0))

        # telemetry holders (no-throw)
        self._telemetry: Dict[str, Any] = {
            "impl": "torch", "device": self.device.type,
            "objective": self.objective, "win": int(self.win),
            "stride": int(self.stride), "ecdf_floor": self._ecdf_floor,
            "_ecdf_ceiling": self._ecdf_ceiling, "encoding_dir": self.direction,
        }
        self._last_stats: Dict[str, Any] = {}

        # Optional Hamming backend (shared C++ module)
        self._hamming_backend = None
        raw_hw = _cfg_get(scorer_cfg, "hamming_weight", None)
        hw_max_default = float(_cfg_get(scorer_cfg, "hamming_weight_max", 0.01) or 0.0)
        if raw_hw is None:
            if bool(_cfg_get(scorer_cfg, "hamming_enabled", False)):
                self._hamming_weight = hw_max_default
            else:
                self._hamming_weight = 0.0
        else:
            self._hamming_weight = float(raw_hw)
        self._hamming_weight_max: float = float(_cfg_get(scorer_cfg, "hamming_weight_max", hw_max_default))
        self._hamming_ramp_start: float = float(_cfg_get(scorer_cfg, "hamming_ramp_start_frac", 0.2) or 0.0)
        self._hamming_ramp_end: float = float(_cfg_get(scorer_cfg, "hamming_ramp_end_frac", 0.7) or 1.0)
        self._hamming_max_hd: int = int(_cfg_get(scorer_cfg, "hamming_max_hd", 2 ** 31 - 1))
        self._hamming_direction_mode: str = str(_cfg_get(scorer_cfg, "hamming_direction_mode", "match") or "match").lower()
        self._hamming_enabled: bool = bool(_cfg_get(scorer_cfg, "hamming_enabled", False) or self._hamming_weight != 0.0)
        self._hamming_length_weights = None
        try:
            lw = _cfg_get(scorer_cfg, "hamming_length_weights")
            if lw:
                self._hamming_length_weights = {int(k): float(v) for k, v in dict(lw).items()}
        except Exception:
            self._hamming_length_weights = None

        if self._hamming_enabled:
            try:
                from rune_decrypter_prime.scoring.hamming.loader import load_raw1grams_wordlists
                from rune_decrypter_prime.scoring.hamming.backend import HammingBackend

                wl_dir = _cfg_get(scorer_cfg, "hamming_wordlist_dir")
                build_rtl = bool(_cfg_get(scorer_cfg, "hamming_build_rtl", False))
                wl_ltr, wl_rtl = load_raw1grams_wordlists(wl_dir, build_rtl=build_rtl)
                self._hamming_backend = HammingBackend(
                    wl_ltr,
                    wl_rtl if build_rtl else None,
                    max_hd=self._hamming_max_hd,
                    length_weights=self._hamming_length_weights,
                )
            except Exception:
                self._hamming_backend = None

        # tables provider + caches
        self._prov: TablesProvider | None = None
        self._tables: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self._loaded_device: torch.device | None = None
        self._ecdf = ECDFCache(root=_cfg_get(scorer_cfg, "model_root", None))

        # det settings
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

        # store originals for ensure_loaded
        self._cfg_cipher = cfg_cipher
        self._cfg_scorer = scorer_cfg

    # ---------- provider & tables ----------
    def ensure_loaded(self, device: torch.device) -> None:
        if (self._loaded_device is not None) and (str(self._loaded_device) == str(device)):
            return
        if self._prov is None:
            self._prov = RuntimeTablesProvider(self._cfg_cipher, self._cfg_scorer)
        self._tables.clear()
        if self.include_char:
            jt = self._prov.get_joint_table("char", int(self.n_char))
            self._tables[("char", int(self.n_char))] = {
                "keys": _as_lut_keys_int64_torch(jt.keys, device=device),
                "logp": _as_lut_logp_float32_torch(jt.logp, device=device),
                "mask": int(jt.mask),
                "stats": dict(jt.stats),
            }
        if self.use_wli:
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

    # ---------- model set ----------
    def _active_models(self, use_wli_now: bool) -> List[Tuple[str, int, float]]:
        models: List[Tuple[str, int, float]] = []
        if (self.char_weights or self.wli_weights):
            if self.include_char and isinstance(self.char_weights, Mapping):
                for n, w in self.char_weights.items():
                    if float(w) > 0: models.append(("char", int(n), float(w)))
            if use_wli_now and isinstance(self.wli_weights, Mapping):
                for n, w in self.wli_weights.items():
                    if float(w) > 0: models.append(("wli", int(n), float(w)))
        else:
            w_char, w_wli = self.weights if self.weights else (0.5, 0.5)
            if not self.include_char: w_char = 0.0
            if not use_wli_now:       w_wli = 0.0
            s = (w_char + w_wli) or 1.0
            if self.include_char: models.append(("char", int(self.n_char), float(w_char / s)))
            if use_wli_now:       models.append(("wli",  int(self.n_wli),  float(w_wli / s)))
        tot = sum(w for _, _, w in models) or 1.0
        return [(c, n, w / tot) for (c, n, w) in models]

    # ---------- pct.logp.winK ----------
    def _percentiles(self, model: str, n: int, means_np: np.ndarray) -> np.ndarray:
        # todo link to objectivesepc
        # Ensure ECDF gets a plain "ltr"/"rtl" string
        mode = self.direction.value if hasattr(self.direction, "value") else str(self.direction).split(".")[-1].lower()
        grid, q = self._ecdf.load(model=model, mode=mode, pos="nose", n=int(n), stat="logp")
        u = np.interp(means_np.astype(np.float32, copy=False), grid, q, left=0.0, right=1.0).astype(np.float32, copy=False)
        if self._ecdf_floor > 0.0: u = np.maximum(u, np.float32(self._ecdf_floor))
        if self._ecdf_ceiling < 1.0: u = np.minimum(u, np.float32(self._ecdf_ceiling))
        return u

    def _pack_char_ngram(self, pt_t: torch.Tensor, n: int) -> torch.Tensor:
        B, L = pt_t.shape; s = pt_t.stride(); Wn = L - n + 1
        return (pt_t.as_strided((B, Wn, n), (s[0], s[1], s[1])) & 0x1F).to(torch.uint32)

    def _pack_wli_ngram(self, pt_t: torch.Tensor, wli_t: torch.Tensor, n: int) -> torch.Tensor:
        B, L = pt_t.shape
        s_pt = pt_t.stride(); s_w = wli_t.stride(); Wn = L - n + 1
        pt_win = pt_t.as_strided((B, Wn, n), (s_pt[0], s_pt[1], s_pt[1]))
        w_win  = wli_t.as_strided((B, Wn, n, 2), (s_w[0], s_w[1], s_w[1], s_w[2]))
        rune = (pt_win & 0x1F).to(torch.int32)
        pos  = (w_win[..., 0] & 0x3F).to(torch.int32)
        ln   = (w_win[..., 1] & 0x3F).to(torch.int32)
        toks = torch.stack([rune[..., i] | (pos[..., i] << 5) | (ln[..., i] << 11) for i in range(n)], dim=-1)
        return toks.to(torch.uint32)

    def _score_pct_logp_win(self, pt_b: np.ndarray, wli_b: np.ndarray | None) -> np.ndarray:
        self.ensure_loaded(self.device)
        B, L = int(pt_b.shape[0]), int(pt_b.shape[1])

        if L < int(self.win):
            out = np.full((B,), float(self._ecdf_floor), dtype=np.float32)
            # single/batch stats
            if B == 1:
                self._last_stats = {"objective": f"pct.logp.win{int(self.win)}",
                                    "score_mean": float(out[0]), "score_std": 0.0, "n_windows": 0}
            else:
                self._last_stats = {"objective": f"pct.logp.win{int(self.win)}", "n_windows": 0,
                                    "score_mean_batch": out.astype(np.float32, copy=False).tolist(),
                                    "score_std_batch": [0.0] * B}
            _tstash(self._telemetry, **self._last_stats)
            return out

        pt_t = torch.from_numpy(pt_b).to(self.device, dtype=torch.uint8, non_blocking=True)
        wli_t = None
        if (wli_b is not None) and self.use_wli:
            wli_t = torch.from_numpy(wli_b).to(self.device, dtype=torch.uint8, non_blocking=True)

        nwin = L - int(self.win) + 1
        mix = np.zeros((B, nwin), dtype=np.float32)
        raw_mix = np.zeros((B, nwin), dtype=np.float32)
        components = {} if B == 1 else None

        for channel, n, w in self._active_models(self.use_wli):
            toks = self._pack_char_ngram(pt_t, int(n)) if channel == "char" else (
                   self._pack_wli_ngram(pt_t, wli_t, int(n)) if wli_t is not None else None)
            if toks is None:  # WLI disabled at runtime
                continue

            h = (_xxh64_u32words_device(toks) if self.device.type == "cuda"
                 else torch.from_numpy(_xxh64_u32words_cpu(toks).view(np.int64)).to(self.device))

            tbl = self._ensure_table(channel, int(n))
            keys_i64 = tbl["keys"]; logp_f32 = tbl["logp"]; mask = int(tbl["mask"])
            fb = float(tbl["stats"]["fallback_logp"])

            # linear probe (device)
            # simplified inline open addressing
            idx = (h & torch.tensor(mask, dtype=keys_i64.dtype, device=self.device)).to(torch.long)
            out = torch.full(h.shape, fill_value=fb, dtype=torch.float32, device=self.device)
            found = torch.zeros(h.shape, dtype=torch.bool, device=self.device)
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

            K = int(self.win) - int(n) + 1
            if K <= 0 or out.shape[1] < K:
                means = torch.empty((B, 0), dtype=torch.float32, device=self.device)
            else:
                means = out.unfold(dimension=1, size=K, step=1).contiguous().mean(dim=-1)  # [B, nwin]

            means_np = means.detach().cpu().numpy()
            u = self._percentiles(channel, int(n), means_np)
            mix += float(w) * u
            raw_mix += float(w) * means_np
            if components is not None:
                label = f"{'char' if channel == 'char' else 'wli'}_n{int(n)}"
                components[label] = {
                    "pct": float(np.mean(u)),
                    "raw": float(np.mean(means_np)),
                }

        score_mean_vec = mix.mean(axis=1).astype(np.float32, copy=False)
        score_std_vec  = mix.std(axis=1).astype(np.float32, copy=False)
        raw_mean_vec = raw_mix.mean(axis=1).astype(np.float32, copy=False)
        raw_std_vec = raw_mix.std(axis=1).astype(np.float32, copy=False)

        hamming_batch = None
        hamming_avg_batch = None
        if self._hamming_backend is not None and wli_b is not None:
            try:
                totals: list[float] = []
                avgs: list[float] = []
                for i in range(B):
                    stats = self._hamming_backend.total_min_hd_stats(
                        pt_b[i].tolist(),
                        wli_b[i].tolist(),
                        direction=self.direction,
                        mode=self._hamming_direction_mode,
                    )
                    totals.append(float(stats.get("total_hd", 0.0)))
                    avgs.append(float(stats.get("avg_hd_word", stats.get("total_hd", 0.0))))
                penalties_arr = np.asarray(avgs, dtype=np.float32)
                score_mean_vec = score_mean_vec - self._hamming_weight * penalties_arr
                raw_mean_vec = raw_mean_vec - self._hamming_weight * penalties_arr
                hamming_batch = np.asarray(totals, dtype=np.float32)
                hamming_avg_batch = penalties_arr
            except Exception:
                hamming_batch = None
                hamming_avg_batch = None

        window_pcts = None
        if B == 1 and mix.shape[1] > 0:
            try:
                window_pcts = {
                    "p10": float(np.percentile(mix[0], 10.0)),
                    "p50": float(np.percentile(mix[0], 50.0)),
                    "p90": float(np.percentile(mix[0], 90.0)),
                }
            except Exception:
                window_pcts = None

        # record telemetry (no-throw)
        try:
            if B == 1:
                objective = {
                    "pct": float(score_mean_vec[0]),
                    "raw": float(raw_mean_vec[0]),
                    "components": (components if components is not None else {}),
                    "windows": (window_pcts if window_pcts is not None else {}),
                }
                self._last_stats = {
                    "objective": f"pct.logp.win{int(self.win)}",
                    "n_windows": int(mix.shape[1]),
                    "score_mean": float(score_mean_vec[0]),
                    "score_std": float(score_std_vec[0]),
                    "raw_score_mean": float(raw_mean_vec[0]),
                    "raw_score_std": float(raw_std_vec[0]),
                    "hamming_total_hd": (float(hamming_batch[0]) if hamming_batch is not None else None),
                    "hamming_avg_hd": (float(hamming_avg_batch[0]) if hamming_avg_batch is not None else None),
                    "hamming_weight": self._hamming_weight,
                    "objective_stats": objective,
                }
            else:
                self._last_stats = {
                    "objective": f"pct.logp.win{int(self.win)}",
                    "n_windows": int(mix.shape[1]),
                    "score_mean_batch": score_mean_vec.tolist(),
                    "score_std_batch": score_std_vec.tolist(),
                    "raw_score_mean_batch": raw_mean_vec.tolist(),
                    "raw_score_std_batch": raw_std_vec.tolist(),
                    "hamming_total_hd_batch": (hamming_batch.tolist() if hamming_batch is not None else None),
                    "hamming_avg_hd_batch": (hamming_avg_batch.tolist() if hamming_avg_batch is not None else None),
                    "hamming_weight": self._hamming_weight,
                }
            _tstash(self._telemetry, **self._last_stats)

            # active models snapshot
            am = [(c, int(n), float(w)) for (c, n, w) in self._active_models(self.use_wli)]
            _tstash(self._telemetry, active_models=am,
                    sum_weights=float(sum(w for _, _, w in am)))
        except Exception:
            pass

        try:
            self._last_raw_batch = raw_mean_vec.astype(np.float32, copy=False)
            self._last_raw_std_batch = raw_std_vec.astype(np.float32, copy=False)
        except Exception:
            pass

        return score_mean_vec

    def set_hamming_progress(self, progress: float) -> None:
        """
        Optional hook for solvers: update the effective Hamming weight using a
        piecewise-linear ramp based on progress in [0,1].
        """
        if not self._hamming_enabled:
            return
        try:
            from rune_decrypter_prime.scoring.hamming.anneal import compute_hamming_weight
            self._hamming_weight = float(compute_hamming_weight(progress, self._hamming_weight_max, self._hamming_ramp_start, self._hamming_ramp_end))
        except Exception:
            pass

    # ---------- BaseScorer API ----------

    def _score_batch_impl(self, pt_b: np.ndarray, wli_b: np.ndarray | None) -> np.ndarray:
        # Enforce ObjectiveSpec(PCT, LOGP, win=K) at the base; sets self.win
        _ = self._require_objective_pct_logp_win()
        return self._score_pct_logp_win(pt_b, wli_b)

    def batch_score(self, pts: Sequence[Iterable[int]], wlis=None) -> np.ndarray:
        if not pts:
            return np.zeros((0,), dtype=np.float32)
        P = [np.asarray(p, np.uint8) for p in pts]
        pt_b = np.stack(P, axis=0)

        wli_b = None
        if wlis is not None:
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

    def batch_score_with_raw(self, pts: Sequence[Iterable[int]], wlis=None) -> Tuple[np.ndarray, np.ndarray]:
        pct = self.batch_score(pts, wlis)
        raw = getattr(self, "_last_raw_batch", None)
        if raw is None:
            try:
                raw = pct.copy()
            except Exception:
                raw = pct
        return pct.astype(np.float32, copy=False), np.asarray(raw, dtype=np.float32)

    def score_with_raw(self, pt: Iterable[int], wli=None) -> Tuple[float, float]:
        pct, raw = self.batch_score_with_raw([np.asarray(pt, np.uint8)], wli)
        return float(pct[0]), float(raw[0])

    def last_stats(self) -> Dict[str, Any]:
        return dict(self._last_stats or {})

    def telemetry(self) -> Dict[str, Any]:
        out = dict(self._telemetry or {})
        out.update(self._last_stats or {})
        return out
