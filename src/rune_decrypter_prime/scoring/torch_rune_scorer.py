# # ============================================================
# # rune_decrypter_prime/scoring/torch_rune_scorer.py
# # Torch backend for scoring objectives
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
# - Supports pct/energy (logp, win10) and avg.logp objectives.
# - If the input length L < win, returns a constant floor value and records telemetry.
# - Device-agnostic: tensors live on self.device; ECDF runs on CPU.
# - Telemetry never raises; it’s best-effort.
#
# Inputs/Outputs
# --------------
# - Inputs: pt_b (uint8 ndarray [B, L]); optional wli_b (uint8 ndarray).
# - Output: float32 (default) or float64 ndarray [B] in [0, 1].
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
from rune_decrypter_prime.scoring.stat_transform import apply_stat_transform
from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.scoring.base_scorer import BaseScorer, normalize_objective as _norm_obj
from rune_decrypter_prime.scoring.windowing import START_TAG, END_TAG
from rune_decrypter_prime.utils.telemetry import stash as _tstash  # canonical helper  ✔
from rune_decrypter_prime.core.types import (
    Direction,
    SeMode,
    AvgWindowPolicy,
    ensure_direction,
    ensure_se_mode,
    ensure_avg_window_policy,
)

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

def _validate_u32_hash_input_cpu(tokens_u32: torch.Tensor | np.ndarray) -> np.ndarray:
    arr: np.ndarray
    if isinstance(tokens_u32, torch.Tensor):
        arr = tokens_u32.detach().cpu().numpy()
    else:
        arr = np.asarray(tokens_u32)
    if arr.dtype != np.uint32:
        raise ValueError(f"xxh64 cpu hash expects uint32 tokens, got dtype={arr.dtype}")
    if arr.ndim < 1:
        raise ValueError("xxh64 cpu hash expects rank >= 1 input")
    n = int(arr.shape[-1])
    if n not in (1, 2, 3, 4):
        raise ValueError(f"xxh64 cpu hash expects n-gram width in [1..4], got n={n}")
    return arr

def _validate_u32_hash_input_device(tokens_u32: torch.Tensor) -> torch.Tensor:
    if not isinstance(tokens_u32, torch.Tensor):
        raise TypeError("xxh64 device hash expects a torch.Tensor input")
    if tokens_u32.dtype != torch.uint32:
        raise ValueError(f"xxh64 device hash expects torch.uint32 tokens, got dtype={tokens_u32.dtype}")
    if tokens_u32.ndim < 1:
        raise ValueError("xxh64 device hash expects rank >= 1 input")
    n = int(tokens_u32.shape[-1])
    if n not in (1, 2, 3, 4):
        raise ValueError(f"xxh64 device hash expects n-gram width in [1..4], got n={n}")
    return tokens_u32

def _xxh64_u32words_cpu(tokens_u32: torch.Tensor | np.ndarray) -> np.ndarray:
    t = _validate_u32_hash_input_cpu(tokens_u32)
    n = t.shape[-1]
    u64 = np.uint64

    def rotl64(x: np.ndarray, r: int) -> np.ndarray:
        return ((x << r) | (x >> u64(64 - r))) & u64(0xFFFFFFFFFFFFFFFF)

    P1 = u64(0x9E3779B185EBCA87); P2 = u64(0xC2B2AE3D27D4EB4F)
    P3 = u64(0x165667B19E3779F9); P4 = u64(0x85EBCA77C2B2AE63); P5 = u64(0x27D4EB2F165667C5)
    MASK64 = u64(0xFFFFFFFFFFFFFFFF)

    total_len = u64(n * 4)
    h = (P5 + total_len) & MASK64
    t_u64 = t.astype(u64, copy=False)

    pairs = n // 2
    for i in range(pairs):
        k1 = (t_u64[..., 2 * i] | (t_u64[..., 2 * i + 1] << u64(32))) & MASK64
        k1 = (k1 * P2) & MASK64
        k1 = rotl64(k1, 31); k1 = (k1 * P1) & MASK64
        h ^= k1; h = (rotl64(h, 27) * P1 + P4) & MASK64

    if n % 2 == 1:
        k1 = (t_u64[..., -1] * P1) & MASK64
        h ^= k1
        h = (rotl64(h, 23) * P2 + P3) & MASK64

    h ^= (h >> u64(33)); h = (h * P2) & MASK64
    h ^= (h >> u64(29)); h = (h * P3) & MASK64
    h ^= (h >> u64(32))
    return h

def _xxh64_u32words_device(tokens_u32: torch.Tensor) -> torch.Tensor:
    tokens_u32 = _validate_u32_hash_input_device(tokens_u32)
    n = tokens_u32.shape[-1]
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

        pairs = n // 2
        for i in range(pairs):
            k1 = (t[..., 2 * i] | (t[..., 2 * i + 1] << 32)) & MASK64
            k1 = (k1 * P2) & MASK64
            k1 = _rotl(k1, 31) * P1 & MASK64
            h ^= k1; h = (_rotl(h, 27) * P1 + P4) & MASK64

        if n % 2 == 1:
            k1 = (t[..., -1] * P1) & MASK64
            h ^= k1
            h = (_rotl(h, 23) * P2 + P3) & MASK64

        h ^= (h >> 33); h = (h * P2) & MASK64
        h ^= (h >> 29); h = (h * P3) & MASK64
        h ^= (h >> 32)
        return h.to(torch.int64)
    except Exception:
        return torch.from_numpy(_xxh64_u32words_cpu(tokens_u32).view(np.int64)).to(device)

def _lookup_logp_linear_probe(
    h: torch.Tensor,
    keys_i64: torch.Tensor,
    logp_f32: torch.Tensor,
    mask: int,
    fallback_logp: float,
    *,
    max_probes: int = 1024,
) -> tuple[torch.Tensor, int, bool]:
    if max_probes <= 0:
        raise ValueError("max_probes must be >= 1")
    if h.dtype != torch.int64:
        h = h.to(torch.int64)
    if keys_i64.dtype != torch.int64:
        raise ValueError(f"keys_i64 must be torch.int64, got {keys_i64.dtype}")
    if logp_f32.dtype != torch.float32:
        raise ValueError(f"logp_f32 must be torch.float32, got {logp_f32.dtype}")
    if keys_i64.numel() == 0:
        raise ValueError("keys_i64 must not be empty")
    if mask < 0:
        raise ValueError("mask must be >= 0")
    if keys_i64.device != h.device or logp_f32.device != h.device:
        raise ValueError("h, keys_i64, and logp_f32 must be on the same device")

    idx = (h & torch.tensor(mask, dtype=keys_i64.dtype, device=h.device)).to(torch.long)
    out = torch.full(h.shape, fill_value=float(fallback_logp), dtype=torch.float32, device=h.device)
    found = torch.zeros(h.shape, dtype=torch.bool, device=h.device)
    probe_exhausted = False

    for _ in range(int(max_probes)):
        k = keys_i64[idx]
        is_empty = (k == 0)
        is_match = (k == h)
        take = (~found) & is_match
        if bool(take.any()):
            out[take] = logp_f32[idx[take]]
            found[take] = True
        cont = (~found) & (~is_empty)
        if not bool(cont.any()):
            break
        idx[cont] = (idx[cont] + 1) & int(mask)
    else:
        probe_exhausted = bool(((~found) & (keys_i64[idx] != 0)).any().item())

    unresolved = int((~found).sum().item())
    return out, unresolved, probe_exhausted

# ===================================================================

class RuneScorerTorch(BaseScorer):
    """
    Torch scorer for pct/energy logp and avg.logp objectives.
    """

    def __init__(self, cfg_cipher, scorer_cfg, tables: TablesProvider | None = None) -> None:
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
        def _dtype_str(value: Any, default: str) -> str:
            if value is None:
                return default
            if hasattr(value, "value"):
                return str(getattr(value, "value")).lower()
            return str(value).lower()
        compute_dt = _dtype_str(_cfg_get(scorer_cfg, "compute_dtype", None), "float32")
        acc_dt = _dtype_str(_cfg_get(scorer_cfg, "acc_dtype", None), "float64")
        out_dt = _dtype_str(_cfg_get(scorer_cfg, "dtype", None), acc_dt)
        if compute_dt not in {"float32", "float64"}:
            compute_dt = "float32"
        if acc_dt not in {"float32", "float64"}:
            acc_dt = "float64"
        if out_dt not in {"float32", "float64"}:
            out_dt = acc_dt
        self._compute_dtype = compute_dt
        self._acc_dtype = acc_dt
        self._dtype = out_dt
        self._score_dtype = np.float64 if self._acc_dtype == "float64" else np.float32

        # direction + se_mode (strict in core; UI may normalize earlier)
        raw_dir = _cfg_get(scorer_cfg, "encoding_dir",
                           _cfg_get(scorer_cfg, "direction", Direction.LTR))
        self.direction = ensure_direction(raw_dir)
        self.se_mode = ensure_se_mode(_cfg_get(scorer_cfg, "se_mode", SeMode.NOSE))
        if self.se_mode is SeMode.WISE:
            raise ValueError("WISE mode is not supported yet; use NOSE.")

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
        if getattr(obj, "family", None) in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
            if getattr(obj, "stat", None) is None:
                obj = ObjectiveSpec(getattr(obj, "family"), Stat.LOGP, getattr(obj, "win", None))
            win = getattr(obj, "win", None)
            if win is None:
                win = int(self.win)
                obj = ObjectiveSpec(getattr(obj, "family"), obj.stat, win)
            if int(win) != 10:
                raise ValueError("pct/energy objectives only support win=10 in the current LM tables.")
            self.win = int(win)
        if getattr(obj, "family", None) is ObjectiveFamily.AVG:
            win = getattr(obj, "win", None)
            if win is None:
                win = int(self.win)
                obj = ObjectiveSpec(ObjectiveFamily.AVG, obj.stat or Stat.LOGP, win)
            self.win = int(win)
        self.objective = obj
        self._avg_window_policy: AvgWindowPolicy = ensure_avg_window_policy(
            _cfg_get(scorer_cfg, "avg_window_policy", AvgWindowPolicy.FIXED_WIN)
        )

        # ECDF config
        self._ecdf_clamp_min = float(_cfg_get(scorer_cfg, "ecdf_clamp_min",
                                              _cfg_get(scorer_cfg, "ecdf_floor", 1e-6)))
        self._ecdf_clamp_max = float(_cfg_get(scorer_cfg, "ecdf_clamp_max",
                                              _cfg_get(scorer_cfg, "ecdf_ceiling",
                                                       float(np.nextafter(np.float32(1.0), np.float32(0.0))))))
        if not (0.0 < self._ecdf_clamp_min < 1.0 and 0.0 < self._ecdf_clamp_max < 1.0):
            raise ValueError("ecdf_clamp_min/max must be in (0,1) for ENERGY-safe scoring")
        if self._ecdf_clamp_min >= self._ecdf_clamp_max:
            raise ValueError("ecdf_clamp_min must be < ecdf_clamp_max")
        self._diagnostics_enabled = bool(_cfg_get(scorer_cfg, "diagnostics_enabled", False))

        # telemetry holders (no-throw)
        win_effective: Any = (
            "full_text"
            if (getattr(self.objective, "family", None) is ObjectiveFamily.AVG and self._avg_window_policy is AvgWindowPolicy.FULL_TEXT)
            else int(self.win)
        )
        self._telemetry: Dict[str, Any] = {
            "impl": "torch", "device": self.device.type,
            "objective": self.objective, "win": int(self.win),
            "stride": int(self.stride), "ecdf_clamp_min": self._ecdf_clamp_min,
            "ecdf_clamp_max": self._ecdf_clamp_max, "encoding_dir": self.direction,
            "dtype": self._dtype,
            "compute_dtype": self._compute_dtype,
            "acc_dtype": self._acc_dtype,
            "avg_window_policy": self._avg_window_policy.value,
            "win_configured": int(self.win),
            "win_effective": win_effective,
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

        # Optional span-hamming backend (pure Python dictionary span matcher)
        self._span_hamming_backend = None
        self._span_hamming_weight = float(_cfg_get(scorer_cfg, "span_hamming_weight", 0.0) or 0.0)
        self._span_hamming_enabled = bool(
            _cfg_get(scorer_cfg, "span_hamming_enabled", False) or self._span_hamming_weight != 0.0
        )
        if self._span_hamming_enabled:
            try:
                from rune_decrypter_prime.scoring.span_hamming import SpanHammingBackend, SpanHammingConfig

                span_cfg = SpanHammingConfig(
                    len_min=int(_cfg_get(scorer_cfg, "span_hamming_len_min", 3)),
                    len_max=int(_cfg_get(scorer_cfg, "span_hamming_len_max", 14)),
                    max_hd=int(_cfg_get(scorer_cfg, "span_hamming_max_hd", 2)),
                    max_candidates_per_window=int(
                        _cfg_get(scorer_cfg, "span_hamming_max_candidates_per_window", 256)
                    ),
                    max_intervals_considered_per_start=int(
                        _cfg_get(scorer_cfg, "span_hamming_max_intervals_considered_per_start", 4)
                    ),
                    min_quality_threshold=float(
                        _cfg_get(scorer_cfg, "span_hamming_min_quality_threshold", 1e-9)
                    ),
                    debug_return_intervals=bool(
                        _cfg_get(scorer_cfg, "span_hamming_debug_return_intervals", False)
                    ),
                )
                wl_dir = _cfg_get(scorer_cfg, "span_hamming_wordlist_dir", None)
                require_selected = bool(_cfg_get(scorer_cfg, "span_hamming_require_selected", True))
                self._span_hamming_backend = SpanHammingBackend(
                    config=span_cfg,
                    wordlist_dir=wl_dir,
                    require_selected=require_selected,
                )
            except Exception:
                self._span_hamming_backend = None
        self._telemetry["span_hamming_enabled"] = bool(
            self._span_hamming_backend is not None and self._span_hamming_weight != 0.0
        )
        self._telemetry["span_hamming_weight"] = float(self._span_hamming_weight)

        # tables provider + caches
        self._prov: TablesProvider | None = (
            tables if (tables is not None and hasattr(tables, "get_joint_table")) else None
        )
        self._tables: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self._loaded_device: torch.device | None = None
        self._ecdf_root = _cfg_get(scorer_cfg, "model_root", None)
        self._ecdf_prefer_float32 = (self._acc_dtype != "float64")
        self._ecdf: ECDFCache | None = None

        # det settings
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

        # store originals for ensure_loaded
        self._cfg_cipher = cfg_cipher
        self._cfg_scorer = scorer_cfg

    def _ensure_ecdf(self) -> ECDFCache:
        if self._ecdf is None:
            self._ecdf = ECDFCache(
                root=self._ecdf_root,
                prefer_float32=self._ecdf_prefer_float32,
            )
        return self._ecdf

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

    def _objective_id(
        self,
        stat_name: str,
        variant: str,
        W: int,
        n_set: Sequence[int],
        direction: str,
        se_mode: str,
    ) -> str:
        fam = getattr(self.objective.family, "value", str(self.objective.family))
        channels = []
        if self.include_char:
            channels.append("char")
        if self.use_wli:
            channels.append("wli")
        ch_part = "_".join(channels) if channels else "none"
        n_part = "n" + "_".join(str(int(n)) for n in n_set)
        return f"{fam}.{stat_name}.{variant}.W{int(W)}.{n_part}.{ch_part}.{direction}.{se_mode}"

    def _objective_label(
        self,
        stat_name: str,
        variant: str,
        W: int,
        n_set: Sequence[int],
        direction: str,
        se_mode: str,
    ) -> str:
        fam = getattr(self.objective.family, "value", str(self.objective.family))
        fam_label = {
            "pct": "Percentile of",
            "energy": "Energy of",
            "avg": "Average",
        }.get(fam, fam)
        variant_label = "interior" if "interior" in variant else "total"
        channels = []
        if self.include_char:
            channels.append("char")
        if self.use_wli:
            channels.append("wli")
        ch_part = "+".join(channels) if channels else "none"
        n_part = ",".join(str(int(n)) for n in n_set)
        return f"{fam_label} {stat_name} per n-gram ({variant_label}), W={int(W)}, n={n_part}, {ch_part}, {direction}, {se_mode}"

    # ---------- pct.logp.winK ----------
    def _percentiles(self, model: str, n: int, means_np: np.ndarray, *, se_name: str) -> np.ndarray:
        # Ensure ECDF gets a plain "ltr"/"rtl" string
        ecdf = self._ensure_ecdf()
        mode = self.direction.value if hasattr(self.direction, "value") else str(self.direction).split(".")[-1].lower()
        ecdf.validate_clamp_range(
            model=model,
            mode=mode,
            pos=se_name,
            n=int(n),
            stat="logp",
            win=int(self.win),
            clamp_min=self._ecdf_clamp_min,
            clamp_max=self._ecdf_clamp_max,
        )
        grid, q = ecdf.load(model=model, mode=mode, pos=se_name, n=int(n), stat="logp", win=int(self.win))
        score_dtype = self._score_dtype
        means_cast = np.asarray(means_np, dtype=score_dtype)
        u = ecdf.interp_percentile(grid, q, means_cast)
        u = np.clip(u, score_dtype(self._ecdf_clamp_min), score_dtype(self._ecdf_clamp_max))
        return u.astype(score_dtype, copy=False)

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
        ecdf = self._ensure_ecdf()
        B, L = int(pt_b.shape[0]), int(pt_b.shape[1])
        from rune_decrypter_prime.core.types import ObjectiveFamily, Stat

        se_name = BaseScorer._se_name(self.se_mode)
        if se_name != "nose":
            raise ValueError("Torch scorer currently supports se_mode='nose' only")

        stat = getattr(self.objective, "stat", None)
        if stat not in (None, Stat.LOGP):
            raise ValueError("torch backend only supports pct/energy for logp stat")
        stat_name = "logp"
        want_energy = getattr(self.objective, "family", None) is ObjectiveFamily.ENERGY
        W = int(self.win)
        stride = int(self.stride) if int(self.stride) > 0 else 1
        score_dtype = self._score_dtype

        models = self._active_models(self.use_wli)
        n_set = sorted({int(n) for _, n, _ in models})
        if not n_set:
            raise ValueError("No active models; check weights and include/use flags")
        n_max = max(n_set)
        L_max = W + n_max - 1
        L_n_map = {int(n): (int(W) + int(n) - 1) for n in n_set}
        nwin_aligned = max(0, L - L_max + 1)

        variant = "mean_per_ngram_interior" if se_name == "wise" else "mean_per_ngram_total"
        total_eval = (W + 2) if se_name == "wise" else W
        interior_eval = W if se_name == "wise" else W

        if nwin_aligned <= 0:
            pct_floor = score_dtype(self._ecdf_clamp_min)
            energy_floor = float(ecdf.energy(np.asarray([pct_floor], dtype=score_dtype))[0])
            score_val = energy_floor if want_energy else float(pct_floor)
            out = np.full((B,), score_val, dtype=score_dtype)
            penalty_hamming_vec = np.zeros((B,), dtype=score_dtype)
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
                    penalties_arr = np.asarray(avgs, dtype=score_dtype)
                    penalty_hamming_vec = -score_dtype(self._hamming_weight) * penalties_arr
                    hamming_batch = np.asarray(totals, dtype=score_dtype)
                    hamming_avg_batch = penalties_arr
                except Exception:
                    hamming_batch = None
                    hamming_avg_batch = None
            stats: Dict[str, Any] = {
                "score_std": 0.0,
                "n_windows": 0,
                "window.win_ngrams": int(W),
                "window.se_mode": se_name,
                "window.n_set": list(n_set),
                "window.stride_runes": int(stride),
                "window.L_n": L_n_map,
                "window.L_max": int(L_max),
                "window.n_windows": 0,
                "stat.name": stat_name,
                "stat.variant": variant,
                "stat.ngrams_total": int(total_eval),
                **({"stat.ngrams_interior": int(interior_eval)} if se_name == "wise" else {}),
                "direction": self.direction.value,
                "avg_window_policy": self._avg_window_policy.value,
                "objective.id": self._objective_id(stat_name, variant, W, n_set, self.direction.value, se_name),
                "objective.label": self._objective_label(stat_name, variant, W, n_set, self.direction.value, se_name),
                "lut.fallback_hits_total": 0,
                "lut.probe_exhausted": False,
                "lut.probe_exhausted_models": [],
                "lut.max_probes": 1024,
            }
            if B == 1:
                stats["score_mean"] = float(out[0])
                stats["stat.mean_per_ngram_penalized"] = float(penalty_hamming_vec[0])
                stats["penalty_hamming"] = float(penalty_hamming_vec[0])
                stats["hamming_total_hd"] = (float(hamming_batch[0]) if hamming_batch is not None else None)
                stats["hamming_avg_hd"] = (float(hamming_avg_batch[0]) if hamming_avg_batch is not None else None)
                stats["hamming_weight"] = self._hamming_weight
                stats["objective_stats"] = {
                    f"pct_{stat_name}_{variant}": pct_floor,
                    f"energy_{stat_name}_{variant}": energy_floor,
                    f"{stat_name}_mean_per_ngram_total": 0.0,
                    f"{stat_name}_mean_per_ngram_interior": 0.0,
                    f"{stat_name}_mean_per_ngram_penalized": float(penalty_hamming_vec[0]),
                    "penalty_hamming": float(penalty_hamming_vec[0]),
                    "components": {},
                    "windows": {},
                    "n_windows": 0,
                    "score_mean": float(out[0]),
                }
            else:
                stats["score_mean_batch"] = out.astype(score_dtype, copy=False).tolist()
                stats["score_std_batch"] = [0.0] * B
                stats["penalty_hamming_batch"] = penalty_hamming_vec.astype(score_dtype, copy=False).tolist()
                stats["hamming_total_hd_batch"] = (hamming_batch.tolist() if hamming_batch is not None else None)
                stats["hamming_avg_hd_batch"] = (hamming_avg_batch.tolist() if hamming_avg_batch is not None else None)
                stats["hamming_weight"] = self._hamming_weight
            _tstash(self._telemetry, **stats)
            self._last_stats = stats
            try:
                self._last_raw_batch = out.astype(score_dtype, copy=False)
                self._last_raw_std_batch = np.zeros_like(out, dtype=score_dtype)
            except Exception:
                pass
            return out

        pt_t = torch.from_numpy(pt_b).to(self.device, dtype=torch.uint8, non_blocking=True)
        wli_t = None
        if (wli_b is not None) and self.use_wli:
            wli_t = torch.from_numpy(wli_b).to(self.device, dtype=torch.uint8, non_blocking=True)

        nwin = ((nwin_aligned - 1) // stride) + 1
        pct_mix = np.zeros((B, nwin), dtype=score_dtype)
        stat_total_mix = np.zeros((B, nwin), dtype=score_dtype)
        components = {} if B == 1 else None

        asset_ids: list[str] = []
        asset_fps: list[str] = []
        interp_dtypes: list[str] = []
        meta_json_list: list[str] = []
        lut_fallback_hits_total = 0
        lut_probe_exhausted_models: list[str] = []

        for channel, n, w in models:
            model_name = "char" if channel == "char" else "wli"
            toks = self._pack_char_ngram(pt_t, int(n)) if channel == "char" else (
                self._pack_wli_ngram(pt_t, wli_t, int(n)) if wli_t is not None else None)
            if toks is None:
                continue

            h = (_xxh64_u32words_device(toks) if self.device.type == "cuda"
                 else torch.from_numpy(_xxh64_u32words_cpu(toks).view(np.int64)).to(self.device))

            tbl = self._ensure_table(channel, int(n))
            keys_i64 = tbl["keys"]; logp_f32 = tbl["logp"]; mask = int(tbl["mask"])
            fb = float(tbl["stats"]["fallback_logp"])
            out, unresolved, probe_exhausted = _lookup_logp_linear_probe(
                h, keys_i64, logp_f32, mask, fb, max_probes=1024
            )
            lut_fallback_hits_total += int(unresolved)
            if probe_exhausted:
                lut_probe_exhausted_models.append(f"{model_name}_n{int(n)}")

            K = int(W)
            if K <= 0 or out.shape[1] < K:
                means = torch.empty(
                    (B, 0),
                    dtype=(torch.float64 if self._acc_dtype == "float64" else torch.float32),
                    device=self.device,
                )
            else:
                if self._acc_dtype == "float64":
                    means_full = out.to(torch.float64).unfold(dimension=1, size=K, step=1).contiguous().mean(dim=-1)
                else:
                    means_full = out.unfold(dimension=1, size=K, step=1).contiguous().mean(dim=-1)
                means_full = means_full[:, :nwin_aligned]
                if stride != 1:
                    means_full = means_full[:, ::stride]
                means = means_full

            means_np = means.detach().cpu().numpy()
            means_np = apply_stat_transform("logp", means_np)
            means_np = np.asarray(means_np, dtype=score_dtype)
            u = self._percentiles(channel, int(n), means_np, se_name=se_name)
            pct_mix += score_dtype(w) * u
            stat_total_mix += score_dtype(w) * means_np
            if components is not None:
                label = f"{'char' if channel == 'char' else 'wli'}_n{int(n)}"
                components[label] = {
                    f"{stat_name}_mean_per_ngram_total": float(np.mean(means_np)),
                    f"{stat_name}_mean_per_ngram_interior": float(np.mean(means_np)),
                }

            asset_ids.append(ecdf.asset_id(model=model_name,
                                                 mode=self.direction.value,
                                                 pos=se_name,
                                                 n=int(n), stat=stat_name, win=int(self.win)))
            asset_fps.append(ecdf.meta_hash(model=model_name,
                                                  mode=self.direction.value,
                                                  pos=se_name,
                                                  n=int(n), stat=stat_name, win=int(self.win)))
            interp_dtypes.append(ecdf.interp_dtype(model=model_name,
                                                         mode=self.direction.value,
                                                         pos=se_name,
                                                         n=int(n), stat=stat_name, win=int(self.win)))
            if self._diagnostics_enabled:
                try:
                    import json as _json
                    meta = ecdf.meta(model=model_name, mode=self.direction.value,
                                           pos=se_name, n=int(n), stat=stat_name, win=int(self.win))
                    meta_json_list.append(_json.dumps(meta, sort_keys=True))
                except Exception:
                    pass

        pct_mean_vec = np.asarray(pct_mix.mean(axis=1, dtype=score_dtype), dtype=score_dtype)
        pct_std_vec = np.asarray(pct_mix.std(axis=1, dtype=score_dtype), dtype=score_dtype)
        energy_perwin = ecdf.energy(pct_mix)
        energy_mean_vec = np.asarray(energy_perwin.mean(axis=1, dtype=score_dtype), dtype=score_dtype)
        energy_std_vec = np.asarray(energy_perwin.std(axis=1, dtype=score_dtype), dtype=score_dtype)
        score_mean_vec = energy_mean_vec if want_energy else pct_mean_vec
        score_std_vec = energy_std_vec if want_energy else pct_std_vec

        stat_total_mean_vec = np.asarray(stat_total_mix.mean(axis=1, dtype=score_dtype), dtype=score_dtype)
        stat_total_std_vec = np.asarray(stat_total_mix.std(axis=1, dtype=score_dtype), dtype=score_dtype)
        stat_interior_mean_vec = stat_total_mean_vec
        stat_interior_std_vec = stat_total_std_vec
        stat_variant_mean_vec = stat_interior_mean_vec if se_name == "wise" else stat_total_mean_vec
        stat_variant_std_vec = stat_interior_std_vec if se_name == "wise" else stat_total_std_vec

        penalty_hamming_vec = np.zeros_like(stat_variant_mean_vec)
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
                penalties_arr = np.asarray(avgs, dtype=score_dtype)
                penalty_hamming_vec = -score_dtype(self._hamming_weight) * penalties_arr
                hamming_batch = np.asarray(totals, dtype=score_dtype)
                hamming_avg_batch = penalties_arr
            except Exception:
                hamming_batch = None
                hamming_avg_batch = None

        stat_penalized_vec = stat_variant_mean_vec + penalty_hamming_vec

        window_metric = energy_perwin if want_energy else pct_mix
        window_pcts = None
        if B == 1 and pct_mix.shape[1] > 0:
            try:
                window_pcts = {
                    "p10": float(np.percentile(window_metric[0], 10.0)),
                    "p50": float(np.percentile(window_metric[0], 50.0)),
                    "p90": float(np.percentile(window_metric[0], 90.0)),
                }
            except Exception:
                window_pcts = None

        try:
            if B == 1:
                objective = {
                    f"pct_{stat_name}_{variant}": float(pct_mean_vec[0]),
                    f"energy_{stat_name}_{variant}": float(energy_mean_vec[0]),
                    f"{stat_name}_mean_per_ngram_total": float(stat_total_mean_vec[0]),
                    f"{stat_name}_mean_per_ngram_interior": float(stat_interior_mean_vec[0]),
                    f"{stat_name}_mean_per_ngram_penalized": float(stat_penalized_vec[0]),
                    "penalty_hamming": float(penalty_hamming_vec[0]),
                    "components": (components if components is not None else {}),
                    "windows": (window_pcts if window_pcts is not None else {}),
                    "n_windows": int(pct_mix.shape[1]),
                    "score_mean": float(score_mean_vec[0]),
                }
                self._last_stats = {
                    "n_windows": int(pct_mix.shape[1]),
                    "score_mean": float(score_mean_vec[0]),
                    "score_std": float(score_std_vec[0]),
                    "stat.mean_per_ngram_total.mean": float(stat_total_mean_vec[0]),
                    "stat.mean_per_ngram_total.std": float(stat_total_std_vec[0]),
                    "stat.mean_per_ngram_interior.mean": float(stat_interior_mean_vec[0]),
                    "stat.mean_per_ngram_interior.std": float(stat_interior_std_vec[0]),
                    "stat.mean_per_ngram_penalized": float(stat_penalized_vec[0]),
                    "stat.std_per_ngram_penalized": float(stat_variant_std_vec[0]),
                    "penalty_hamming": float(penalty_hamming_vec[0]),
                    "hamming_total_hd": (float(hamming_batch[0]) if hamming_batch is not None else None),
                    "hamming_avg_hd": (float(hamming_avg_batch[0]) if hamming_avg_batch is not None else None),
                    "hamming_weight": self._hamming_weight,
                    "objective_stats": objective,
                    "window.win_ngrams": int(W),
                    "window.se_mode": se_name,
                    "window.n_set": list(n_set),
                    "window.stride_runes": int(stride),
                    "window.L_n": L_n_map,
                    "window.L_max": int(L_max),
                    "window.n_windows": int(pct_mix.shape[1]),
                    "stat.name": stat_name,
                    "stat.variant": variant,
                    "stat.ngrams_total": int(total_eval),
                    **({"stat.ngrams_interior": int(interior_eval)} if se_name == "wise" else {}),
                    "direction": self.direction.value,
                    "objective.id": self._objective_id(stat_name, variant, W, n_set, self.direction.value, se_name),
                    "objective.label": self._objective_label(stat_name, variant, W, n_set, self.direction.value, se_name),
                    "ecdf.asset_id": asset_ids[0] if len(asset_ids) == 1 else asset_ids,
                    "ecdf.asset_fingerprint": asset_fps[0] if len(asset_fps) == 1 else asset_fps,
                    "ecdf.disk_dtype": "float64",
                    "ecdf.canonical_dtype": "float64",
                    "ecdf.compute_dtype": interp_dtypes[0] if len(interp_dtypes) == 1 else interp_dtypes,
                    "ecdf.meta_hash": asset_fps[0] if len(asset_fps) == 1 else asset_fps,
                    "ecdf.interp": "linear",
                    "ecdf.interp_dtype": interp_dtypes[0] if len(interp_dtypes) == 1 else interp_dtypes,
                    "ecdf.clamp_min": float(self._ecdf_clamp_min),
                    "ecdf.clamp_max": float(self._ecdf_clamp_max),
                    "lut.fallback_hits_total": int(lut_fallback_hits_total),
                    "lut.probe_exhausted": bool(lut_probe_exhausted_models),
                    "lut.probe_exhausted_models": list(lut_probe_exhausted_models),
                    "lut.max_probes": 1024,
                }
            else:
                self._last_stats = {
                    "n_windows": int(pct_mix.shape[1]),
                    "score_mean_batch": score_mean_vec.tolist(),
                    "score_std_batch": score_std_vec.tolist(),
                    "stat.mean_per_ngram_penalized_batch": stat_penalized_vec.tolist(),
                    "stat.std_per_ngram_penalized_batch": stat_variant_std_vec.tolist(),
                    "penalty_hamming_batch": penalty_hamming_vec.tolist(),
                    "hamming_total_hd_batch": (hamming_batch.tolist() if hamming_batch is not None else None),
                    "hamming_avg_hd_batch": (hamming_avg_batch.tolist() if hamming_avg_batch is not None else None),
                    "hamming_weight": self._hamming_weight,
                    "window.win_ngrams": int(W),
                    "window.se_mode": se_name,
                    "window.n_set": list(n_set),
                    "window.stride_runes": int(stride),
                    "window.L_n": L_n_map,
                    "window.L_max": int(L_max),
                    "window.n_windows": int(pct_mix.shape[1]),
                    "stat.name": stat_name,
                    "stat.variant": variant,
                    "stat.ngrams_total": int(total_eval),
                    **({"stat.ngrams_interior": int(interior_eval)} if se_name == "wise" else {}),
                    "direction": self.direction.value,
                    "objective.id": self._objective_id(stat_name, variant, W, n_set, self.direction.value, se_name),
                    "objective.label": self._objective_label(stat_name, variant, W, n_set, self.direction.value, se_name),
                    "ecdf.asset_id": asset_ids[0] if len(asset_ids) == 1 else asset_ids,
                    "ecdf.asset_fingerprint": asset_fps[0] if len(asset_fps) == 1 else asset_fps,
                    "ecdf.disk_dtype": "float64",
                    "ecdf.canonical_dtype": "float64",
                    "ecdf.compute_dtype": interp_dtypes[0] if len(interp_dtypes) == 1 else interp_dtypes,
                    "ecdf.meta_hash": asset_fps[0] if len(asset_fps) == 1 else asset_fps,
                    "ecdf.interp": "linear",
                    "ecdf.interp_dtype": interp_dtypes[0] if len(interp_dtypes) == 1 else interp_dtypes,
                    "ecdf.clamp_min": float(self._ecdf_clamp_min),
                    "ecdf.clamp_max": float(self._ecdf_clamp_max),
                    "lut.fallback_hits_total": int(lut_fallback_hits_total),
                    "lut.probe_exhausted": bool(lut_probe_exhausted_models),
                    "lut.probe_exhausted_models": list(lut_probe_exhausted_models),
                    "lut.max_probes": 1024,
                }
            if self._diagnostics_enabled and meta_json_list:
                self._last_stats["ecdf.meta_json"] = meta_json_list
            _tstash(self._telemetry, **self._last_stats)

            am = [(c, int(n), float(w)) for (c, n, w) in self._active_models(self.use_wli)]
            _tstash(self._telemetry, active_models=am,
                    sum_weights=float(sum(w for _, _, w in am)))
        except Exception:
            pass

        try:
            self._last_raw_batch = stat_penalized_vec.astype(score_dtype, copy=False)
            self._last_raw_std_batch = stat_variant_std_vec.astype(score_dtype, copy=False)
        except Exception:
            pass

        return score_mean_vec

    def _score_raw_logp_full_text(self, pt_b: np.ndarray, wli_b: np.ndarray | None) -> np.ndarray:
        self.ensure_loaded(self.device)
        B, L = int(pt_b.shape[0]), int(pt_b.shape[1])
        from rune_decrypter_prime.core.types import Stat

        se_name = BaseScorer._se_name(self.se_mode)
        if se_name != "nose":
            raise ValueError("Torch scorer currently supports se_mode='nose' only")

        stat = getattr(self.objective, "stat", None)
        if stat not in (None, Stat.LOGP):
            raise ValueError("torch backend only supports avg.logp")
        stat_name = "logp"
        W = int(self.win)
        score_dtype = self._score_dtype

        models_all = self._active_models(self.use_wli)
        active_models: list[tuple[str, int, float, int]] = []
        skipped_short: dict[str, int] = {}
        for channel, n, w in models_all:
            n_i = int(n)
            ngrams = int(L - n_i + 1)
            if ngrams <= 0:
                skipped_short[f"{channel}_n{n_i}"] = int(ngrams)
                continue
            active_models.append((channel, n_i, float(w), int(ngrams)))

        if not active_models:
            out = np.zeros((B,), dtype=score_dtype)
            stats: Dict[str, Any] = {
                "n_windows": 0,
                "score_std": 0.0,
                "window.win_ngrams": int(W),
                "window.win_configured": int(W),
                "window.win_effective": "full_text",
                "window.win_ignored": True,
                "window.se_mode": se_name,
                "window.n_set": [],
                "window.stride_runes": int(self.stride),
                "window.L_n": {},
                "window.L_max": int(L),
                "window.n_windows": 0,
                "stat.name": stat_name,
                "stat.variant": "mean_per_ngram_total",
                "stat.ngrams_total": 0,
                "stat.ngrams_total_by_model": {},
                "direction": self.direction.value,
                "avg_window_policy": self._avg_window_policy.value,
                "objective.id": self._objective_id(stat_name, "mean_per_ngram_total", W, [], self.direction.value, se_name),
                "objective.label": self._objective_label(stat_name, "mean_per_ngram_total", W, [], self.direction.value, se_name),
                "lut.fallback_hits_total": 0,
                "lut.probe_exhausted": False,
                "lut.probe_exhausted_models": [],
                "lut.max_probes": 1024,
            }
            if B == 1:
                stats.update(
                    score_mean=float(out[0]),
                    **{"stat.mean_per_ngram_penalized": float(out[0])},
                    objective_stats={
                        "logp_mean_per_ngram_total": 0.0,
                        "logp_mean_per_ngram_interior": 0.0,
                        "logp_mean_per_ngram_penalized": 0.0,
                        "penalty_hamming": 0.0,
                        "components": {},
                        "windows": {},
                        "n_windows": 0,
                        "score_mean": 0.0,
                        "skipped_short_models": skipped_short,
                    },
                )
            else:
                stats.update(
                    score_mean_batch=out.astype(score_dtype, copy=False).tolist(),
                    score_std_batch=[0.0] * B,
                    **{"stat.mean_per_ngram_penalized_batch": out.astype(score_dtype, copy=False).tolist()},
                )
            self._last_stats = stats
            _tstash(self._telemetry, **self._last_stats)
            try:
                self._last_raw_batch = out.astype(score_dtype, copy=False)
                self._last_raw_std_batch = np.zeros_like(out, dtype=score_dtype)
            except Exception:
                pass
            return out

        wsum = float(sum(w for _, _, w, _ in active_models))
        active_models = [(ch, n, (w / wsum), ngrams) for ch, n, w, ngrams in active_models]
        n_set = sorted({int(n) for _, n, _, _ in active_models})

        pt_t = torch.from_numpy(pt_b).to(self.device, dtype=torch.uint8, non_blocking=True)
        wli_t = None
        if (wli_b is not None) and self.use_wli:
            wli_t = torch.from_numpy(wli_b).to(self.device, dtype=torch.uint8, non_blocking=True)

        stat_total_mean_vec = np.zeros((B,), dtype=score_dtype)
        components = {} if B == 1 else None
        ngrams_by_model: Dict[str, int] = {}
        lut_fallback_hits_total = 0
        lut_probe_exhausted_models: list[str] = []

        for channel, n, w_norm, ngrams in active_models:
            model_name = "char" if channel == "char" else "wli"
            toks = self._pack_char_ngram(pt_t, int(n)) if channel == "char" else (
                self._pack_wli_ngram(pt_t, wli_t, int(n)) if wli_t is not None else None
            )
            if toks is None:
                continue

            h = (
                _xxh64_u32words_device(toks)
                if self.device.type == "cuda"
                else torch.from_numpy(_xxh64_u32words_cpu(toks).view(np.int64)).to(self.device)
            )

            tbl = self._ensure_table(channel, int(n))
            keys_i64 = tbl["keys"]
            logp_f32 = tbl["logp"]
            mask = int(tbl["mask"])
            fb = float(tbl["stats"]["fallback_logp"])
            out, unresolved, probe_exhausted = _lookup_logp_linear_probe(
                h, keys_i64, logp_f32, mask, fb, max_probes=1024
            )
            lut_fallback_hits_total += int(unresolved)
            if probe_exhausted:
                lut_probe_exhausted_models.append(f"{model_name}_n{int(n)}")

            out_np = np.asarray(out.detach().cpu().numpy(), dtype=score_dtype)
            out_np = np.asarray(apply_stat_transform("logp", out_np), dtype=score_dtype)
            mean_vec = np.asarray(out_np.mean(axis=1, dtype=score_dtype), dtype=score_dtype)
            stat_total_mean_vec += score_dtype(w_norm) * mean_vec

            label = f"{model_name}_n{int(n)}"
            ngrams_by_model[label] = int(ngrams)
            if components is not None:
                components[label] = {
                    "logp_mean_per_ngram_total": float(mean_vec[0]),
                    "logp_mean_per_ngram_interior": float(mean_vec[0]),
                    "ngram_count": int(ngrams),
                    "weight": float(w_norm),
                }

        stat_variant_mean_vec = stat_total_mean_vec
        stat_variant_std_vec = np.zeros_like(stat_variant_mean_vec)

        penalty_hamming_vec = np.zeros_like(stat_variant_mean_vec)
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
                penalties_arr = np.asarray(avgs, dtype=score_dtype)
                penalty_hamming_vec = -score_dtype(self._hamming_weight) * penalties_arr
                hamming_batch = np.asarray(totals, dtype=score_dtype)
                hamming_avg_batch = penalties_arr
            except Exception:
                hamming_batch = None
                hamming_avg_batch = None

        stat_penalized_vec = stat_variant_mean_vec + penalty_hamming_vec
        ngram_ref = int(max(ngrams_by_model.values()) if ngrams_by_model else 0)

        if B == 1:
            objective = {
                "logp_mean_per_ngram_total": float(stat_total_mean_vec[0]),
                "logp_mean_per_ngram_interior": float(stat_total_mean_vec[0]),
                "logp_mean_per_ngram_penalized": float(stat_penalized_vec[0]),
                "penalty_hamming": float(penalty_hamming_vec[0]),
                "components": (components if components is not None else {}),
                "windows": {
                    "p10": float(stat_variant_mean_vec[0]),
                    "p50": float(stat_variant_mean_vec[0]),
                    "p90": float(stat_variant_mean_vec[0]),
                },
                "n_windows": 1,
                "score_mean": float(stat_penalized_vec[0]),
                "skipped_short_models": skipped_short,
            }
            self._last_stats = {
                "n_windows": 1,
                "score_mean": float(stat_penalized_vec[0]),
                "score_std": float(stat_variant_std_vec[0]),
                "stat.mean_per_ngram_total.mean": float(stat_total_mean_vec[0]),
                "stat.mean_per_ngram_total.std": 0.0,
                "stat.mean_per_ngram_interior.mean": float(stat_total_mean_vec[0]),
                "stat.mean_per_ngram_interior.std": 0.0,
                "stat.mean_per_ngram_penalized": float(stat_penalized_vec[0]),
                "stat.std_per_ngram_penalized": float(stat_variant_std_vec[0]),
                "penalty_hamming": float(penalty_hamming_vec[0]),
                "hamming_total_hd": (float(hamming_batch[0]) if hamming_batch is not None else None),
                "hamming_avg_hd": (float(hamming_avg_batch[0]) if hamming_avg_batch is not None else None),
                "hamming_weight": self._hamming_weight,
                "objective_stats": objective,
                "window.win_ngrams": int(W),
                "window.win_configured": int(W),
                "window.win_effective": "full_text",
                "window.win_ignored": True,
                "window.se_mode": se_name,
                "window.n_set": list(n_set),
                "window.stride_runes": int(self.stride),
                "window.L_n": {int(n): int(L) for _, n, _, _ in active_models},
                "window.L_max": int(L),
                "window.n_windows": 1,
                "stat.name": stat_name,
                "stat.variant": "mean_per_ngram_total",
                "stat.ngrams_total": int(ngram_ref),
                "stat.ngrams_total_by_model": {k: int(v) for k, v in ngrams_by_model.items()},
                "direction": self.direction.value,
                "avg_window_policy": self._avg_window_policy.value,
                "objective.id": self._objective_id(stat_name, "mean_per_ngram_total", W, n_set, self.direction.value, se_name),
                "objective.label": self._objective_label(stat_name, "mean_per_ngram_total", W, n_set, self.direction.value, se_name),
                "lut.fallback_hits_total": int(lut_fallback_hits_total),
                "lut.probe_exhausted": bool(lut_probe_exhausted_models),
                "lut.probe_exhausted_models": list(lut_probe_exhausted_models),
                "lut.max_probes": 1024,
            }
        else:
            self._last_stats = {
                "n_windows": 1,
                "score_mean_batch": stat_penalized_vec.tolist(),
                "score_std_batch": stat_variant_std_vec.tolist(),
                "stat.mean_per_ngram_penalized_batch": stat_penalized_vec.tolist(),
                "stat.std_per_ngram_penalized_batch": stat_variant_std_vec.tolist(),
                "penalty_hamming_batch": penalty_hamming_vec.tolist(),
                "hamming_total_hd_batch": (hamming_batch.tolist() if hamming_batch is not None else None),
                "hamming_avg_hd_batch": (hamming_avg_batch.tolist() if hamming_avg_batch is not None else None),
                "hamming_weight": self._hamming_weight,
                "window.win_ngrams": int(W),
                "window.win_configured": int(W),
                "window.win_effective": "full_text",
                "window.win_ignored": True,
                "window.se_mode": se_name,
                "window.n_set": list(n_set),
                "window.stride_runes": int(self.stride),
                "window.L_n": {int(n): int(L) for _, n, _, _ in active_models},
                "window.L_max": int(L),
                "window.n_windows": 1,
                "stat.name": stat_name,
                "stat.variant": "mean_per_ngram_total",
                "stat.ngrams_total": int(ngram_ref),
                "stat.ngrams_total_by_model": {k: int(v) for k, v in ngrams_by_model.items()},
                "direction": self.direction.value,
                "avg_window_policy": self._avg_window_policy.value,
                "objective.id": self._objective_id(stat_name, "mean_per_ngram_total", W, n_set, self.direction.value, se_name),
                "objective.label": self._objective_label(stat_name, "mean_per_ngram_total", W, n_set, self.direction.value, se_name),
                "lut.fallback_hits_total": int(lut_fallback_hits_total),
                "lut.probe_exhausted": bool(lut_probe_exhausted_models),
                "lut.probe_exhausted_models": list(lut_probe_exhausted_models),
                "lut.max_probes": 1024,
            }

        _tstash(self._telemetry, **self._last_stats)
        try:
            self._last_raw_batch = stat_penalized_vec.astype(score_dtype, copy=False)
            self._last_raw_std_batch = stat_variant_std_vec.astype(score_dtype, copy=False)
        except Exception:
            pass
        return stat_penalized_vec

    def _score_raw_logp_win(self, pt_b: np.ndarray, wli_b: np.ndarray | None) -> np.ndarray:
        if self._avg_window_policy is AvgWindowPolicy.FULL_TEXT:
            return self._score_raw_logp_full_text(pt_b, wli_b)
        self.ensure_loaded(self.device)
        B, L = int(pt_b.shape[0]), int(pt_b.shape[1])
        from rune_decrypter_prime.core.types import Stat

        se_name = BaseScorer._se_name(self.se_mode)
        if se_name != "nose":
            raise ValueError("Torch scorer currently supports se_mode='nose' only")

        stat = getattr(self.objective, "stat", None)
        if stat not in (None, Stat.LOGP):
            raise ValueError("torch backend only supports avg.logp")
        stat_name = "logp"
        W = int(self.win)
        stride = int(self.stride) if int(self.stride) > 0 else 1
        score_dtype = self._score_dtype

        models = self._active_models(self.use_wli)
        n_set = sorted({int(n) for _, n, _ in models})
        if not n_set:
            raise ValueError("No active models; check weights and include/use flags")
        n_max = max(n_set)
        L_max = W + n_max - 1
        L_n_map = {int(n): (int(W) + int(n) - 1) for n in n_set}
        nwin_aligned = max(0, L - L_max + 1)

        variant = "mean_per_ngram_interior" if se_name == "wise" else "mean_per_ngram_total"
        total_eval = (W + 2) if se_name == "wise" else W
        interior_eval = W if se_name == "wise" else W

        if nwin_aligned <= 0:
            out = np.zeros((B,), dtype=score_dtype)
            stats: Dict[str, Any] = {
                "score_std": 0.0,
                "n_windows": 0,
                "window.win_ngrams": int(W),
                "window.se_mode": se_name,
                "window.n_set": list(n_set),
                "window.stride_runes": int(stride),
                "window.L_n": L_n_map,
                "window.L_max": int(L_max),
                "window.n_windows": 0,
                "stat.name": stat_name,
                "stat.variant": variant,
                "stat.ngrams_total": int(total_eval),
                **({"stat.ngrams_interior": int(interior_eval)} if se_name == "wise" else {}),
                "direction": self.direction.value,
                "objective.id": self._objective_id(stat_name, variant, W, n_set, self.direction.value, se_name),
                "objective.label": self._objective_label(stat_name, variant, W, n_set, self.direction.value, se_name),
                "lut.fallback_hits_total": 0,
                "lut.probe_exhausted": False,
                "lut.probe_exhausted_models": [],
                "lut.max_probes": 1024,
            }
            if B == 1:
                stats["score_mean"] = float(out[0])
                stats["objective_stats"] = {
                    f"{stat_name}_mean_per_ngram_total": 0.0,
                    f"{stat_name}_mean_per_ngram_interior": 0.0,
                    f"{stat_name}_mean_per_ngram_penalized": 0.0,
                    "penalty_hamming": 0.0,
                    "components": {},
                    "windows": {},
                    "n_windows": 0,
                    "score_mean": float(out[0]),
                }
            else:
                stats["score_mean_batch"] = out.astype(score_dtype, copy=False).tolist()
                stats["score_std_batch"] = [0.0] * B
            _tstash(self._telemetry, **stats)
            self._last_stats = stats
            try:
                self._last_raw_batch = out.astype(score_dtype, copy=False)
                self._last_raw_std_batch = np.zeros_like(out, dtype=score_dtype)
            except Exception:
                pass
            return out

        pt_t = torch.from_numpy(pt_b).to(self.device, dtype=torch.uint8, non_blocking=True)
        wli_t = None
        if (wli_b is not None) and self.use_wli:
            wli_t = torch.from_numpy(wli_b).to(self.device, dtype=torch.uint8, non_blocking=True)

        nwin = ((nwin_aligned - 1) // stride) + 1
        stat_total_mix = np.zeros((B, nwin), dtype=score_dtype)
        components = {} if B == 1 else None
        lut_fallback_hits_total = 0
        lut_probe_exhausted_models: list[str] = []

        for channel, n, w in models:
            model_name = "char" if channel == "char" else "wli"
            toks = self._pack_char_ngram(pt_t, int(n)) if channel == "char" else (
                self._pack_wli_ngram(pt_t, wli_t, int(n)) if wli_t is not None else None)
            if toks is None:
                continue

            h = (_xxh64_u32words_device(toks) if self.device.type == "cuda"
                 else torch.from_numpy(_xxh64_u32words_cpu(toks).view(np.int64)).to(self.device))

            tbl = self._ensure_table(channel, int(n))
            keys_i64 = tbl["keys"]; logp_f32 = tbl["logp"]; mask = int(tbl["mask"])
            fb = float(tbl["stats"]["fallback_logp"])
            out, unresolved, probe_exhausted = _lookup_logp_linear_probe(
                h, keys_i64, logp_f32, mask, fb, max_probes=1024
            )
            lut_fallback_hits_total += int(unresolved)
            if probe_exhausted:
                lut_probe_exhausted_models.append(f"{model_name}_n{int(n)}")

            K = int(W)
            if K <= 0 or out.shape[1] < K:
                means = torch.empty(
                    (B, 0),
                    dtype=(torch.float64 if self._acc_dtype == "float64" else torch.float32),
                    device=self.device,
                )
            else:
                if self._acc_dtype == "float64":
                    means_full = out.to(torch.float64).unfold(dimension=1, size=K, step=1).contiguous().mean(dim=-1)
                else:
                    means_full = out.unfold(dimension=1, size=K, step=1).contiguous().mean(dim=-1)
                means_full = means_full[:, :nwin_aligned]
                if stride != 1:
                    means_full = means_full[:, ::stride]
                means = means_full

            means_np = means.detach().cpu().numpy()
            means_np = apply_stat_transform("logp", means_np)
            means_np = np.asarray(means_np, dtype=score_dtype)
            stat_total_mix += score_dtype(w) * means_np
            if components is not None:
                label = f"{model_name}_n{int(n)}"
                components[label] = {
                    f"{stat_name}_mean_per_ngram_total": float(np.mean(means_np)),
                    f"{stat_name}_mean_per_ngram_interior": float(np.mean(means_np)),
                }

        stat_total_mean_vec = np.asarray(stat_total_mix.mean(axis=1, dtype=score_dtype), dtype=score_dtype)
        stat_total_std_vec = np.asarray(stat_total_mix.std(axis=1, dtype=score_dtype), dtype=score_dtype)
        stat_interior_mean_vec = stat_total_mean_vec
        stat_interior_std_vec = stat_total_std_vec
        stat_variant_mean_vec = stat_interior_mean_vec if se_name == "wise" else stat_total_mean_vec
        stat_variant_std_vec = stat_interior_std_vec if se_name == "wise" else stat_total_std_vec

        penalty_hamming_vec = np.zeros_like(stat_variant_mean_vec)
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
                penalties_arr = np.asarray(avgs, dtype=score_dtype)
                penalty_hamming_vec = -score_dtype(self._hamming_weight) * penalties_arr
                hamming_batch = np.asarray(totals, dtype=score_dtype)
                hamming_avg_batch = penalties_arr
            except Exception:
                hamming_batch = None
                hamming_avg_batch = None

        stat_penalized_vec = stat_variant_mean_vec + penalty_hamming_vec

        window_pcts = None
        if B == 1 and stat_total_mix.shape[1] > 0:
            try:
                window_pcts = {
                    "p10": float(np.percentile(stat_total_mix[0], 10.0)),
                    "p50": float(np.percentile(stat_total_mix[0], 50.0)),
                    "p90": float(np.percentile(stat_total_mix[0], 90.0)),
                }
            except Exception:
                window_pcts = None

        try:
            if B == 1:
                objective = {
                    f"{stat_name}_mean_per_ngram_total": float(stat_total_mean_vec[0]),
                    f"{stat_name}_mean_per_ngram_interior": float(stat_interior_mean_vec[0]),
                    f"{stat_name}_mean_per_ngram_penalized": float(stat_penalized_vec[0]),
                    "penalty_hamming": float(penalty_hamming_vec[0]),
                    "components": (components if components is not None else {}),
                    "windows": (window_pcts if window_pcts is not None else {}),
                    "n_windows": int(stat_total_mix.shape[1]),
                    "score_mean": float(stat_penalized_vec[0]),
                }
                self._last_stats = {
                    "n_windows": int(stat_total_mix.shape[1]),
                    "score_mean": float(stat_penalized_vec[0]),
                    "score_std": float(stat_variant_std_vec[0]),
                    "stat.mean_per_ngram_total.mean": float(stat_total_mean_vec[0]),
                    "stat.mean_per_ngram_total.std": float(stat_total_std_vec[0]),
                    "stat.mean_per_ngram_interior.mean": float(stat_interior_mean_vec[0]),
                    "stat.mean_per_ngram_interior.std": float(stat_interior_std_vec[0]),
                    "stat.mean_per_ngram_penalized": float(stat_penalized_vec[0]),
                    "stat.std_per_ngram_penalized": float(stat_variant_std_vec[0]),
                    "penalty_hamming": float(penalty_hamming_vec[0]),
                    "hamming_total_hd": (float(hamming_batch[0]) if hamming_batch is not None else None),
                    "hamming_avg_hd": (float(hamming_avg_batch[0]) if hamming_avg_batch is not None else None),
                    "hamming_weight": self._hamming_weight,
                    "objective_stats": objective,
                    "window.win_ngrams": int(W),
                    "window.se_mode": se_name,
                    "window.n_set": list(n_set),
                    "window.stride_runes": int(stride),
                    "window.L_n": L_n_map,
                    "window.L_max": int(L_max),
                    "window.n_windows": int(stat_total_mix.shape[1]),
                    "stat.name": stat_name,
                    "stat.variant": variant,
                    "stat.ngrams_total": int(total_eval),
                    **({"stat.ngrams_interior": int(interior_eval)} if se_name == "wise" else {}),
                    "direction": self.direction.value,
                    "avg_window_policy": self._avg_window_policy.value,
                    "objective.id": self._objective_id(stat_name, variant, W, n_set, self.direction.value, se_name),
                    "objective.label": self._objective_label(stat_name, variant, W, n_set, self.direction.value, se_name),
                    "lut.fallback_hits_total": int(lut_fallback_hits_total),
                    "lut.probe_exhausted": bool(lut_probe_exhausted_models),
                    "lut.probe_exhausted_models": list(lut_probe_exhausted_models),
                    "lut.max_probes": 1024,
                }
            else:
                self._last_stats = {
                    "n_windows": int(stat_total_mix.shape[1]),
                    "score_mean_batch": stat_penalized_vec.tolist(),
                    "score_std_batch": stat_variant_std_vec.tolist(),
                    "stat.mean_per_ngram_penalized_batch": stat_penalized_vec.tolist(),
                    "stat.std_per_ngram_penalized_batch": stat_variant_std_vec.tolist(),
                    "penalty_hamming_batch": penalty_hamming_vec.tolist(),
                    "hamming_total_hd_batch": (hamming_batch.tolist() if hamming_batch is not None else None),
                    "hamming_avg_hd_batch": (hamming_avg_batch.tolist() if hamming_avg_batch is not None else None),
                    "hamming_weight": self._hamming_weight,
                    "window.win_ngrams": int(W),
                    "window.se_mode": se_name,
                    "window.n_set": list(n_set),
                    "window.stride_runes": int(stride),
                    "window.L_n": L_n_map,
                    "window.L_max": int(L_max),
                    "window.n_windows": int(stat_total_mix.shape[1]),
                    "stat.name": stat_name,
                    "stat.variant": variant,
                    "stat.ngrams_total": int(total_eval),
                    **({"stat.ngrams_interior": int(interior_eval)} if se_name == "wise" else {}),
                    "direction": self.direction.value,
                    "avg_window_policy": self._avg_window_policy.value,
                    "objective.id": self._objective_id(stat_name, variant, W, n_set, self.direction.value, se_name),
                    "objective.label": self._objective_label(stat_name, variant, W, n_set, self.direction.value, se_name),
                    "lut.fallback_hits_total": int(lut_fallback_hits_total),
                    "lut.probe_exhausted": bool(lut_probe_exhausted_models),
                    "lut.probe_exhausted_models": list(lut_probe_exhausted_models),
                    "lut.max_probes": 1024,
                }
            _tstash(self._telemetry, **self._last_stats)
        except Exception:
            pass

        try:
            self._last_raw_batch = stat_penalized_vec.astype(score_dtype, copy=False)
            self._last_raw_std_batch = stat_variant_std_vec.astype(score_dtype, copy=False)
        except Exception:
            pass

        return stat_penalized_vec

    def _apply_span_hamming_bonus_batch(self, scores: np.ndarray, pt_b: np.ndarray) -> np.ndarray:
        backend = getattr(self, "_span_hamming_backend", None)
        weight = float(getattr(self, "_span_hamming_weight", 0.0))
        if backend is None or weight == 0.0:
            return scores
        if pt_b.ndim != 2 or scores.ndim != 1:
            return scores
        B = int(pt_b.shape[0])
        if B == 0:
            return scores

        span_raw = np.zeros((B,), dtype=self._score_dtype)
        span_cov = np.zeros((B,), dtype=self._score_dtype)
        span_q = np.zeros((B,), dtype=self._score_dtype)
        for i in range(B):
            try:
                stats = backend.score(pt_b[i].tolist())
                span_raw[i] = float(stats.span_raw)
                span_cov[i] = float(stats.coverage)
                span_q[i] = float(stats.quality)
            except Exception:
                span_raw[i] = 0.0
                span_cov[i] = 0.0
                span_q[i] = 0.0

        bonus = (weight * span_raw).astype(self._score_dtype, copy=False)
        out = np.asarray(scores, dtype=self._score_dtype) + bonus

        try:
            raw = getattr(self, "_last_raw_batch", None)
            if raw is not None:
                raw_arr = np.asarray(raw, dtype=self._score_dtype).reshape(-1)
                if raw_arr.shape[0] == B:
                    self._last_raw_batch = raw_arr + bonus
        except Exception:
            pass

        try:
            stats = self._last_stats if isinstance(self._last_stats, dict) else {}
            stats["span_hamming_bonus_batch"] = bonus.tolist()
            stats["span_hamming_raw_batch"] = span_raw.tolist()
            stats["span_hamming_coverage_batch"] = span_cov.tolist()
            stats["span_hamming_quality_batch"] = span_q.tolist()
            stats["span_hamming_weight"] = weight
            stats["score_mean_base_batch"] = np.asarray(scores, dtype=self._score_dtype).tolist()
            stats["score_mean_batch"] = out.tolist()
            if B == 1:
                base0 = float(scores[0])
                bonus0 = float(bonus[0])
                out0 = float(out[0])
                stats["span_hamming_bonus"] = bonus0
                stats["span_hamming_raw"] = float(span_raw[0])
                stats["span_hamming_coverage"] = float(span_cov[0])
                stats["span_hamming_quality"] = float(span_q[0])
                stats["score_mean_base"] = base0
                stats["score_mean"] = out0
                if "stat.mean_per_ngram_penalized" in stats:
                    stats["stat.mean_per_ngram_penalized"] = float(stats["stat.mean_per_ngram_penalized"]) + bonus0
                obj = stats.get("objective_stats")
                if isinstance(obj, dict):
                    obj["span_hamming_bonus"] = bonus0
                    obj["span_hamming_weight"] = weight
                    obj["span_hamming_raw"] = float(span_raw[0])
                    obj["span_hamming_coverage"] = float(span_cov[0])
                    obj["span_hamming_quality"] = float(span_q[0])
                    if "score_mean" in obj:
                        obj["score_mean"] = float(obj["score_mean"]) + bonus0
                    if "logp_mean_per_ngram_penalized" in obj:
                        obj["logp_mean_per_ngram_penalized"] = float(obj["logp_mean_per_ngram_penalized"]) + bonus0
                    stat_name = stats.get("stat.name")
                    if isinstance(stat_name, str):
                        key = f"{stat_name}_mean_per_ngram_penalized"
                        if key in obj:
                            obj[key] = float(obj[key]) + bonus0
            self._last_stats = stats
            _tstash(
                self._telemetry,
                span_hamming_weight=weight,
                span_hamming_bonus_batch=bonus.tolist(),
                span_hamming_raw_batch=span_raw.tolist(),
                span_hamming_coverage_batch=span_cov.tolist(),
                span_hamming_quality_batch=span_q.tolist(),
                score_mean_batch=out.tolist(),
                score_mean_base_batch=np.asarray(scores, dtype=self._score_dtype).tolist(),
            )
        except Exception:
            pass

        return out

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
        obj = getattr(self, "objective", None)
        fam = getattr(obj, "family", None)
        if fam is None:
            _ = self._require_objective_pct_logp_win()
            return self._score_pct_logp_win(pt_b, wli_b)
        from rune_decrypter_prime.core.types import ObjectiveFamily, Stat
        if fam is ObjectiveFamily.AVG:
            if getattr(obj, "stat", None) not in (None, Stat.LOGP):
                raise ValueError("torch backend only supports avg.logp for raw objectives.")
            return self._score_raw_logp_win(pt_b, wli_b)
        _ = self._require_objective_pct_logp_win()
        return self._score_pct_logp_win(pt_b, wli_b)

    def batch_score(self, pts: Sequence[Iterable[int]], wlis=None) -> np.ndarray:
        if pts is None:
            return np.zeros((0,), dtype=np.float64)
        if isinstance(pts, np.ndarray):
            if pts.size == 0:
                return np.zeros((0,), dtype=np.float64)
            if pts.ndim == 1:
                pts_iter: Sequence[Iterable[int]] = [np.asarray(pts, dtype=np.uint8).reshape(-1)]
            elif pts.ndim == 2:
                pts_iter = pts
            else:
                raise ValueError("pts must be rank-1 or rank-2 when provided as np.ndarray")
        else:
            try:
                if len(pts) == 0:
                    return np.zeros((0,), dtype=np.float64)
                pts_iter = pts
            except Exception:
                pts_iter = list(pts)
                if len(pts_iter) == 0:
                    return np.zeros((0,), dtype=np.float64)
        P: list[np.ndarray] = []
        for p in pts_iter:
            arr = np.asarray(p, dtype=np.int64).reshape(-1)
            if (arr < 0).any() or (arr > 30).any():
                raise ValueError("Torch scorer expects rune tokens in [0..30]")
            P.append(arr.astype(np.uint8, copy=False))
        pt_b = np.stack(P, axis=0)
        if self.se_mode is SeMode.NOSE:
            if np.any((pt_b == START_TAG) | (pt_b == END_TAG)):
                raise ValueError("NOSE input must not include boundary tags")

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
        if wli_b is not None:
            if (wli_b[..., 0] > 63).any() or (wli_b[..., 1] > 63).any():
                raise ValueError("WLI entries must be <= 63 for torch scorer")

        scores = self._score_batch_impl(pt_b, wli_b)
        scores = self._apply_span_hamming_bonus_batch(scores, pt_b)
        return scores.astype(np.float64, copy=False)

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
        return pct, np.asarray(raw, dtype=np.float64)

    def score_with_raw(self, pt: Iterable[int], wli=None) -> Tuple[float, float]:
        pct, raw = self.batch_score_with_raw([np.asarray(pt, np.uint8)], wli)
        return float(pct[0]), float(raw[0])

    def supports_raw(self) -> bool:
        return True

    def last_stats(self) -> Dict[str, Any]:
        return dict(self._last_stats or {})

    def telemetry(self) -> Dict[str, Any]:
        out = dict(self._telemetry or {})
        out.update(self._last_stats or {})
        return out
