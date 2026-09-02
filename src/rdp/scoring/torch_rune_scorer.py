# # ============================================================
# # rdp/scoring/torch_rune_scorer.py
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
# rdp/scoring/torch_rune_scorer.py
# ============================================================
from __future__ import annotations
from typing import Iterable, Sequence, List, Dict, Any, Tuple
import numpy as np
import time
import torch

from rdp.scoring.unified_tables import (
    TablesProvider,
    RuntimeTablesProvider,
)
from rdp.scoring.language_model.language_model_prime_runtime import ECDFCache
from rdp.scoring.stat_transform import apply_stat_transform
from rdp.backends.xp import select_backend
from rdp.scoring.base_scorer import BaseScorer
from rdp.scoring.objective_normalize import (
    normalize_objective_input as _normalize_objective,
)
from rdp.scoring.windowing import START_TAG, END_TAG
from rdp.telemetry.scoring import stash as _tstash  # canonical helper  ✔
from rdp.core.types import (
    SeMode,
    AvgWindowPolicy,
    ensure_direction,
    ensure_avg_window_policy,
)
from rdp.core.config.cipher import CipherConfig
from rdp.scoring.word_ngrams import RuneTokenWordNgramJudgeRuntime
from rdp.core.config.scoring import (
    ScoringConfig,
    HammingTextDirectionMode,
    SpanHammingBucketPolicy,
    SpanHammingCombineMode,
    SpanHammingGateFailurePolicy,
    SpanHammingLanguageModelProfileSource,
    SpanHammingMode,
    ensure_hamming_text_direction_mode,
    ensure_span_hamming_bucket_policy,
    ensure_span_hamming_combine_mode,
    ensure_span_hamming_gate_failure_policy,
    ensure_span_hamming_language_model_profile_source,
    ensure_span_hamming_mode,
)


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

    def __init__(
        self,
        cfg_cipher: CipherConfig,
        scorer_cfg: ScoringConfig,
        tables: TablesProvider | None = None,
    ) -> None:
        if not isinstance(cfg_cipher, CipherConfig):
            raise TypeError("cfg_cipher must be CipherConfig")
        if not isinstance(scorer_cfg, ScoringConfig):
            raise TypeError("scorer_cfg must be ScoringConfig")
        # device
        device_req = str(cfg_cipher.device or "auto")
        dev_name, _xp = select_backend(device_req)
        self.device = torch.device("cuda" if dev_name == "cuda" else "cpu")

        # core flags / numbers
        self.include_char = scorer_cfg.character_lane_enabled
        self.use_wli = scorer_cfg.word_length_lane_enabled
        self.n_char = scorer_cfg.character_ngram_order
        self.n_wli = scorer_cfg.word_length_ngram_order
        self.win = scorer_cfg.window_size
        self.stride = scorer_cfg.stride

        def _dtype_str(value: Any, default: str) -> str:
            if value is None:
                return default
            if hasattr(value, "value"):
                return str(getattr(value, "value")).lower()
            return str(value).lower()

        compute_dt = _dtype_str(scorer_cfg.compute_dtype, "float32")
        acc_dt = _dtype_str(scorer_cfg.accumulator_dtype, "float64")
        out_dt = acc_dt
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
        self.direction = ensure_direction(cfg_cipher.encoding_dir)
        self.se_mode = SeMode.NOSE
        if self.se_mode is SeMode.WISE:
            raise ValueError("WISE mode is not supported yet; use NOSE.")

        self.weights = scorer_cfg.base_lane_weights or (0.5, 0.5)
        self.char_weights = scorer_cfg.character_order_weights
        self.wli_weights = scorer_cfg.word_length_order_weights
        self._effective_model_weights = scorer_cfg.effective_lm_model_weights
        self._weight_contract = scorer_cfg.weight_contract()

        # objective intake supports ObjectiveSpec | dict | str | None
        from rdp.core.types import ObjectiveFamily, Stat, ObjectiveSpec
        obj = _normalize_objective(
            scorer_cfg.objective,
            default_win=int(self.win),
        )
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
            scorer_cfg.average_window_policy.value.replace("window", "win")
        )

        # ECDF config
        self._ecdf_clamp_min = float(scorer_cfg.ecdf_clamp_minimum)
        self._ecdf_clamp_max = float(scorer_cfg.ecdf_clamp_maximum)
        if not (0.0 < self._ecdf_clamp_min < 1.0 and 0.0 < self._ecdf_clamp_max < 1.0):
            raise ValueError("ecdf_clamp_min/max must be in (0,1) for ENERGY-safe scoring")
        if self._ecdf_clamp_min >= self._ecdf_clamp_max:
            raise ValueError("ecdf_clamp_min must be < ecdf_clamp_max")
        self._diagnostics_enabled = scorer_cfg.diagnostics_enabled

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
            "lm_weights": self._weight_contract,
        }
        self._last_stats: Dict[str, Any] = {}

        # Optional Hamming backend (shared C++ module)
        self._hamming_backend = None
        raw_hw = scorer_cfg.hamming_weight
        hw_max_default = float(scorer_cfg.hamming_maximum_weight or 0.0)
        if raw_hw is None:
            if scorer_cfg.hamming_enabled:
                self._hamming_weight = hw_max_default
            else:
                self._hamming_weight = 0.0
        else:
            self._hamming_weight = float(raw_hw)
        self._hamming_weight_max: float = float(scorer_cfg.hamming_maximum_weight)
        self._hamming_ramp_start: float = float(
            scorer_cfg.hamming_ramp_start_fraction or 0.0
        )
        self._hamming_ramp_end: float = float(
            scorer_cfg.hamming_ramp_end_fraction or 1.0
        )
        self._hamming_max_hd: int = int(scorer_cfg.hamming_maximum_distance)
        self._hamming_direction_mode: HammingTextDirectionMode = (
            ensure_hamming_text_direction_mode(scorer_cfg.hamming_text_direction_mode)
        )
        self._hamming_enabled: bool = bool(
            scorer_cfg.hamming_enabled or self._hamming_weight != 0.0
        )
        self._hamming_dictionary_policy = scorer_cfg.hamming_dictionary_policy
        self._hamming_dictionary_policy_root = scorer_cfg.hamming_dictionary_root
        self._hamming_wordlist_dir_resolved = None
        self._hamming_length_weights = None
        try:
            lw = scorer_cfg.hamming_length_weights
            if lw:
                self._hamming_length_weights = {int(k): float(v) for k, v in dict(lw).items()}
        except Exception:
            self._hamming_length_weights = None

        if self._hamming_enabled:
            try:
                from rdp.scoring.hamming.dictionary_assets import choose_hamming_dictionary_wordlist_dir
                from rdp.scoring.hamming.loader import load_raw1grams_wordlists
                from rdp.scoring.hamming.backend import HammingBackend

                wl_dir = choose_hamming_dictionary_wordlist_dir(
                    explicit_wordlist_dir=scorer_cfg.hamming_wordlist_directory,
                    policy=self._hamming_dictionary_policy,
                    policy_root=self._hamming_dictionary_policy_root,
                )
                self._hamming_wordlist_dir_resolved = wl_dir
                build_rtl = scorer_cfg.hamming_build_right_to_left
                wl_ltr, wl_rtl = load_raw1grams_wordlists(wl_dir, build_rtl=build_rtl)
                self._hamming_backend = HammingBackend(
                    wl_ltr,
                    wl_rtl if build_rtl else None,
                    max_hd=self._hamming_max_hd,
                    length_weights=self._hamming_length_weights,
                )
            except Exception:
                self._hamming_backend = None
        self._telemetry["hamming_dictionary_policy"] = (
            str(getattr(self._hamming_dictionary_policy, "value", self._hamming_dictionary_policy))
            if self._hamming_dictionary_policy is not None
            else None
        )
        self._telemetry["hamming_wordlist_dir"] = (
            str(self._hamming_wordlist_dir_resolved) if self._hamming_wordlist_dir_resolved is not None else None
        )

        # Optional span-hamming backend (pure Python dictionary span matcher)
        self._span_hamming_backend = None
        self._span_hamming_assets = None
        self._span_hamming_mode: SpanHammingMode = ensure_span_hamming_mode(
            scorer_cfg.span_hamming_mode
        )
        self._span_hamming_weight = float(scorer_cfg.span_hamming_weight or 0.0)
        legacy_enabled = bool(
            scorer_cfg.span_hamming_enabled or self._span_hamming_weight != 0.0
        )
        if self._span_hamming_mode is SpanHammingMode.OFF and legacy_enabled:
            self._span_hamming_mode = SpanHammingMode.RAW_BONUS
        self._span_hamming_assets_dir = scorer_cfg.span_hamming_assets_directory
        self._span_hamming_assets_dictionary_policy = (
            scorer_cfg.span_hamming_assets_dictionary_policy
        )
        self._span_hamming_allow_dictionary_policy_mismatch = bool(
            scorer_cfg.span_hamming_allow_dictionary_mismatch
        )
        self._span_hamming_wordlist_dir_resolved = None
        self._span_hamming_dictionary_policy = None
        self._span_hamming_dictionary_policy_match = None
        self._span_hamming_dictionary_policy_note = None
        self._span_hamming_bucket_policy: SpanHammingBucketPolicy = (
            ensure_span_hamming_bucket_policy(scorer_cfg.span_hamming_bucket_policy)
        )
        self._span_hamming_ecdf_clamp_min = scorer_cfg.span_hamming_ecdf_clamp_minimum
        self._span_hamming_ecdf_clamp_max = scorer_cfg.span_hamming_ecdf_clamp_maximum
        if self._span_hamming_ecdf_clamp_min is None:
            self._span_hamming_ecdf_clamp_min = float(self._ecdf_clamp_min)
        else:
            self._span_hamming_ecdf_clamp_min = float(self._span_hamming_ecdf_clamp_min)
        if self._span_hamming_ecdf_clamp_max is None:
            self._span_hamming_ecdf_clamp_max = float(self._ecdf_clamp_max)
        else:
            self._span_hamming_ecdf_clamp_max = float(self._span_hamming_ecdf_clamp_max)
        self._span_hamming_coverage_min = float(
            scorer_cfg.span_hamming_minimum_coverage or 0.0
        )
        self._span_hamming_quality_min = float(
            scorer_cfg.span_hamming_minimum_gate_quality or 0.0
        )
        self._span_hamming_span_pct_min = (
            scorer_cfg.span_hamming_minimum_span_percentile
        )
        if self._span_hamming_span_pct_min is not None:
            self._span_hamming_span_pct_min = float(self._span_hamming_span_pct_min)
        self._span_hamming_char_pct_min = (
            scorer_cfg.span_hamming_minimum_character_percentile
        )
        if self._span_hamming_char_pct_min is not None:
            self._span_hamming_char_pct_min = float(self._span_hamming_char_pct_min)
        self._span_hamming_combine_mode: SpanHammingCombineMode = (
            ensure_span_hamming_combine_mode(scorer_cfg.span_hamming_combine_mode)
        )
        self._span_hamming_weight_span = float(
            scorer_cfg.span_hamming_span_weight or 0.0
        )
        self._span_hamming_weight_char = float(
            scorer_cfg.span_hamming_character_weight or 0.0
        )
        self._span_hamming_use_char_channel = False
        self._span_hamming_gate_fail_policy: SpanHammingGateFailurePolicy = (
            ensure_span_hamming_gate_failure_policy(
                scorer_cfg.span_hamming_gate_failure_policy
            )
        )
        self._span_hamming_gate_score_floor = scorer_cfg.span_hamming_gate_score_floor
        if self._span_hamming_gate_score_floor is not None:
            self._span_hamming_gate_score_floor = float(self._span_hamming_gate_score_floor)
        self._span_hamming_lm_assets = None
        self._span_hamming_lm_assets_json = (
            scorer_cfg.span_hamming_language_model_assets
        )
        self._span_hamming_lm_profile_source: SpanHammingLanguageModelProfileSource = (
            ensure_span_hamming_language_model_profile_source(
                scorer_cfg.span_hamming_language_model_profile_source
            )
        )
        self._span_hamming_lm_tail_start_index = int(
            scorer_cfg.span_hamming_language_model_tail_start or 0
        )
        self._span_hamming_lm_weight = float(
            scorer_cfg.span_hamming_language_model_weight or 0.0
        )
        self._word_ngram_judge_enabled = scorer_cfg.word_ngram_judge_enabled
        self._word_ngram_judge_sqlite_path = scorer_cfg.word_ngram_judge_database
        self._word_ngram_judge_alpha = float(scorer_cfg.word_ngram_judge_alpha or 0.4)
        self._word_ngram_judge_miss_logp = float(
            scorer_cfg.word_ngram_judge_missing_log_probability or -20.0
        )
        self._word_ngram_judge_min_positions = int(
            scorer_cfg.word_ngram_judge_minimum_positions or 0
        )
        self._word_ngram_judge_prefix_total_thresholds = tuple(
            int(v) for v in scorer_cfg.word_ngram_judge_prefix_thresholds
        )
        self._word_ngram_judge = None
        self._word_ngram_judge_forced_debug_intervals = False
        if self._word_ngram_judge_enabled:
            self._word_ngram_judge = RuneTokenWordNgramJudgeRuntime.open_sqlite(
                self._word_ngram_judge_sqlite_path,
                alpha=float(self._word_ngram_judge_alpha),
                miss_logp=float(self._word_ngram_judge_miss_logp),
                min_positions=int(self._word_ngram_judge_min_positions),
                prefix_total_thresholds=self._word_ngram_judge_prefix_total_thresholds,
            )
        if not (
            0.0
            < self._span_hamming_ecdf_clamp_min
            < self._span_hamming_ecdf_clamp_max
            < 1.0
        ):
            raise ValueError(
                "span_hamming_ecdf_clamp_min/max must satisfy 0 < min < max < 1"
            )
        if (
            self._span_hamming_bucket_policy
            is not SpanHammingBucketPolicy.NEAREST_SMALLER_ON_TIE
        ):
            raise ValueError(
                "span_hamming_bucket_policy currently only supports "
                "'nearest_smaller_on_tie'"
            )
        self._span_hamming_enabled = self._span_hamming_mode is not SpanHammingMode.OFF
        if self._span_hamming_enabled:
            try:
                from rdp.core.hamming_dictionary_policy import ensure_hamming_dictionary_policy
                from rdp.scoring.hamming.dictionary_assets import choose_hamming_dictionary_wordlist_dir
                from rdp.scoring.span_hamming import (
                    SpanCalibratedAssets,
                    SpanHammingBackend,
                    SpanHammingConfig,
                    SpanHammingLmAssetsV2,
                )

                debug_return_intervals = scorer_cfg.span_hamming_return_debug_intervals
                if self._word_ngram_judge is not None and not debug_return_intervals:
                    debug_return_intervals = True
                    self._word_ngram_judge_forced_debug_intervals = True

                span_cfg = SpanHammingConfig(
                    len_min=scorer_cfg.span_hamming_minimum_length,
                    len_max=scorer_cfg.span_hamming_maximum_length,
                    max_hd=scorer_cfg.span_hamming_maximum_distance,
                    start_stride=scorer_cfg.span_hamming_start_stride,
                    max_windows_total=scorer_cfg.span_hamming_maximum_windows,
                    max_candidates_per_window=(
                        scorer_cfg.span_hamming_maximum_candidates_per_window
                    ),
                    max_intervals_considered_per_start=(
                        scorer_cfg.span_hamming_maximum_intervals_per_start
                    ),
                    min_quality_threshold=scorer_cfg.span_hamming_minimum_quality,
                    debug_return_intervals=debug_return_intervals,
                )
                explicit_span_wl_dir = scorer_cfg.span_hamming_wordlist_directory
                wl_dir = choose_hamming_dictionary_wordlist_dir(
                    explicit_wordlist_dir=explicit_span_wl_dir,
                    policy=self._hamming_dictionary_policy,
                    policy_root=self._hamming_dictionary_policy_root,
                )
                self._span_hamming_wordlist_dir_resolved = wl_dir
                if explicit_span_wl_dir is None and self._hamming_dictionary_policy is not None:
                    self._span_hamming_dictionary_policy = str(
                        getattr(self._hamming_dictionary_policy, "value", self._hamming_dictionary_policy)
                    )
                elif explicit_span_wl_dir is not None:
                    self._span_hamming_dictionary_policy_note = (
                        "explicit_span_hamming_wordlist_dir"
                    )
                require_selected = scorer_cfg.span_hamming_require_selection
                self._span_hamming_backend = SpanHammingBackend(
                    config=span_cfg,
                    wordlist_dir=wl_dir,
                    require_selected=require_selected,
                )
                if self._span_hamming_mode is SpanHammingMode.CALIBRATED:
                    from rdp.core.types import ObjectiveFamily
                    fam = getattr(self.objective, "family", None)
                    if fam not in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
                        raise ValueError(
                            "span_hamming_mode='calibrated' only supports ObjectiveFamily.PCT or ENERGY"
                        )
                    if self._span_hamming_assets_dir is None:
                        raise ValueError(
                            "span_hamming_assets_dir is required when span_hamming_mode='calibrated'"
                        )
                    self._span_hamming_assets = SpanCalibratedAssets.load(self._span_hamming_assets_dir)
                    assets_policy = self._span_hamming_assets_dictionary_policy
                    if assets_policy is None:
                        assets_policy = getattr(self._span_hamming_assets, "dictionary_policy", None)
                    if assets_policy is not None:
                        assets_policy = ensure_hamming_dictionary_policy(assets_policy).value
                    self._span_hamming_assets_dictionary_policy = assets_policy
                    active_policy = self._span_hamming_dictionary_policy
                    if active_policy is None:
                        if self._span_hamming_allow_dictionary_policy_mismatch:
                            self._span_hamming_dictionary_policy_match = None
                            self._span_hamming_dictionary_policy_note = "custom_wordlist_dir_unverified_allowed"
                        else:
                            raise ValueError(
                                "calibrated span-hamming with explicit span_hamming_wordlist_dir requires "
                                "span_hamming_allow_dictionary_policy_mismatch=True"
                            )
                    elif assets_policy is None:
                        if str(active_policy) == "normal":
                            self._span_hamming_dictionary_policy_match = True
                            self._span_hamming_dictionary_policy_note = "legacy_assets_assumed_normal"
                        elif self._span_hamming_allow_dictionary_policy_mismatch:
                            self._span_hamming_dictionary_policy_match = None
                            self._span_hamming_dictionary_policy_note = (
                                "assets_policy_unspecified_nondefault_dictionary_allowed"
                            )
                        else:
                            raise ValueError(
                                "calibrated span-hamming with non-default dictionary policy requires "
                                "span_hamming_assets_dictionary_policy metadata or explicit override"
                            )
                    elif str(active_policy) == str(assets_policy):
                        self._span_hamming_dictionary_policy_match = True
                        self._span_hamming_dictionary_policy_note = "policy_match"
                    elif self._span_hamming_allow_dictionary_policy_mismatch:
                        self._span_hamming_dictionary_policy_match = False
                        self._span_hamming_dictionary_policy_note = "policy_mismatch_allowed"
                    else:
                        raise ValueError(
                            "calibrated span-hamming dictionary policy mismatch: "
                            f"active={active_policy} assets={assets_policy}"
                        )
                    if self._span_hamming_lm_assets_json is not None:
                        self._span_hamming_lm_assets = SpanHammingLmAssetsV2.load(self._span_hamming_lm_assets_json)
                        if self._span_hamming_lm_tail_start_index >= int(self._span_hamming_lm_assets.profile_vector_length):
                            raise ValueError(
                                "span_hamming_lm_tail_start_index must be < profile_vector_length in LM assets"
                            )
                    self._span_hamming_use_char_channel = bool(
                        self._span_hamming_weight_char > 0.0
                        or self._span_hamming_char_pct_min is not None
                    )
                    if self._span_hamming_use_char_channel and not self._calibrated_char_pct_available():
                        raise ValueError(
                            "calibrated span char channel requires char4-only base scorer "
                            "(include_char=True, use_word_breaks=False, char_weights={4:1.0})"
                        )
                    if self._span_hamming_weight_span < 0.0 or self._span_hamming_weight_char < 0.0:
                        raise ValueError("span_hamming_weight_span/char must be >= 0")
                    if self._span_hamming_combine_mode is SpanHammingCombineMode.WEIGHTED_SUM:
                        w_span = float(self._span_hamming_weight_span)
                        w_char = float(self._span_hamming_weight_char if self._span_hamming_use_char_channel else 0.0)
                        if (w_span + w_char) <= 0.0:
                            raise ValueError(
                                "weighted_sum combine requires positive total weight "
                                "(span_hamming_weight_span + span_hamming_weight_char)"
                            )
                    if self._span_hamming_gate_score_floor is None:
                        if fam is ObjectiveFamily.ENERGY:
                            self._span_hamming_gate_score_floor = float(
                                -np.log1p(-self._span_hamming_ecdf_clamp_min)
                            )
                        else:
                            self._span_hamming_gate_score_floor = float(self._span_hamming_ecdf_clamp_min)
            except Exception:
                if self._span_hamming_mode is SpanHammingMode.CALIBRATED:
                    raise
                self._span_hamming_backend = None
        self._telemetry["span_hamming_enabled"] = bool(
            self._span_hamming_backend is not None and (
                (self._span_hamming_mode is SpanHammingMode.RAW_BONUS and self._span_hamming_weight != 0.0)
                or self._span_hamming_mode is SpanHammingMode.CALIBRATED
            )
        )
        self._telemetry["span_hamming_wordlist_dir"] = (
            str(self._span_hamming_wordlist_dir_resolved)
            if self._span_hamming_wordlist_dir_resolved is not None
            else None
        )
        self._telemetry["span_hamming_dictionary_policy"] = self._span_hamming_dictionary_policy
        self._telemetry["span_hamming_mode"] = self._span_hamming_mode.value
        self._telemetry["span_hamming_assets_dir"] = (
            str(self._span_hamming_assets_dir) if self._span_hamming_assets_dir is not None else None
        )
        self._telemetry["span_hamming_assets_dictionary_policy"] = self._span_hamming_assets_dictionary_policy
        self._telemetry["span_hamming_dictionary_policy_match"] = self._span_hamming_dictionary_policy_match
        self._telemetry["span_hamming_dictionary_policy_note"] = self._span_hamming_dictionary_policy_note
        self._telemetry["span_hamming_weight"] = float(self._span_hamming_weight)
        self._telemetry["word_ngram_judge_enabled"] = bool(self._word_ngram_judge is not None)
        self._telemetry["word_ngram_judge_sqlite_path"] = (
            str(self._word_ngram_judge_sqlite_path) if self._word_ngram_judge_sqlite_path is not None else None
        )
        self._telemetry["word_ngram_judge_min_positions"] = int(self._word_ngram_judge_min_positions)
        self._telemetry["word_ngram_judge_prefix_total_thresholds"] = tuple(self._word_ngram_judge_prefix_total_thresholds)
        self._telemetry["word_ngram_judge_forced_debug_intervals"] = bool(self._word_ngram_judge_forced_debug_intervals)
        self._telemetry["span_hamming_combine_mode"] = self._span_hamming_combine_mode.value
        self._telemetry["span_hamming_weight_span"] = float(self._span_hamming_weight_span)
        self._telemetry["span_hamming_weight_char"] = float(self._span_hamming_weight_char)
        self._telemetry["span_hamming_use_char_channel"] = bool(self._span_hamming_use_char_channel)
        self._telemetry["span_hamming_ecdf_clamp_min"] = float(self._span_hamming_ecdf_clamp_min)
        self._telemetry["span_hamming_ecdf_clamp_max"] = float(self._span_hamming_ecdf_clamp_max)
        self._telemetry["span_hamming_bucket_policy"] = self._span_hamming_bucket_policy.value
        self._telemetry["span_hamming_eval_total"] = 0
        self._telemetry["span_hamming_eval_active"] = 0
        self._telemetry["span_hamming_eval_skipped_char_gate"] = 0
        self._telemetry["span_hamming_eval_seconds_total"] = 0.0
        self._telemetry["span_hamming_eval_active_seconds_total"] = 0.0

        # tables provider + caches
        self._prov: TablesProvider | None = (
            tables if (tables is not None and hasattr(tables, "get_joint_table")) else None
        )
        self._tables: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self._loaded_device: torch.device | None = None
        self._ecdf_root = scorer_cfg.language_model_root
        self._ecdf_prefer_float32 = self._acc_dtype != "float64"
        self._lm_load_reporter = getattr(scorer_cfg, "_lm_load_reporter", None)
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
                load_reporter=self._lm_load_reporter,
            )
        return self._ecdf

    def _score_word_ngram_signal(self, *, pt_values: Sequence[int], span_stats: Any) -> dict[str, Any]:
        judge = getattr(self, "_word_ngram_judge", None)
        if judge is None:
            return {
                "word_ngram_judge_available": False,
                "word_ngram_judge_active": False,
                "word_ngram_judge_inactive_reason": "disabled",
            }
        intervals = tuple(getattr(span_stats, "selected_intervals", ()) or ())
        if not intervals:
            return {
                "word_ngram_judge_available": True,
                "word_ngram_judge_active": False,
                "word_ngram_judge_inactive_reason": "no_selected_intervals",
                "word_ngram_judge_exact_word_count": 0,
                "word_ngram_judge_segment_count": 0,
                "word_ngram_judge_n_positions": 0,
                "word_ngram_judge_trust_score": 0.0,
                "word_ngram_judge_trust_tier": "inactive",
            }
        report = judge.score_candidate(
            text_idx=pt_values,
            selected_intervals=intervals,
            direction=self.direction,
        )
        return {
            "word_ngram_judge_available": bool(report.available),
            "word_ngram_judge_active": bool(report.active),
            "word_ngram_judge_inactive_reason": report.inactive_reason,
            "word_ngram_judge_exact_word_count": int(report.exact_word_count),
            "word_ngram_judge_segment_count": int(report.segment_count),
            "word_ngram_judge_xent_3": report.xent_3,
            "word_ngram_judge_backoff_xent": report.xent_backoff_5_4_3,
            "word_ngram_judge_n_positions": int(report.n_positions),
            "word_ngram_judge_miss_rate": report.miss_rate,
            "word_ngram_judge_used5_rate": report.used5_rate,
            "word_ngram_judge_used4_rate": report.used4_rate,
            "word_ngram_judge_used3_rate": report.used3_rate,
            "word_ngram_judge_prefix_total_mean": float(report.prefix_total_mean),
            "word_ngram_judge_prefix_total_min": float(report.prefix_total_min),
            "word_ngram_judge_prefix_total_ge_1_rate": float(report.prefix_total_ge_1_rate),
            "word_ngram_judge_prefix_total_ge_10_rate": float(report.prefix_total_ge_10_rate),
            "word_ngram_judge_prefix_total_ge_100_rate": float(report.prefix_total_ge_100_rate),
            "word_ngram_judge_trust_score": float(report.trust_score),
            "word_ngram_judge_trust_tier": str(report.trust_tier),
            "word_ngram_judge_report_xent": (
                None if not report.active else report.xent_3
            ),
            "word_ngram_judge_report_backoff_xent": (
                None if not report.active else report.xent_backoff_5_4_3
            ),
        }

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
        return [
            (channel, int(n), float(weight))
            for channel, n, weight in self._effective_model_weights(
                use_word_lengths=use_wli_now
            )
        ]

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
        from rdp.core.types import ObjectiveFamily, Stat

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
                            mode=self._hamming_direction_mode.value,
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
                        mode=self._hamming_direction_mode.value,
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
        from rdp.core.types import Stat

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
                        mode=self._hamming_direction_mode.value,
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
        from rdp.core.types import Stat

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
                        mode=self._hamming_direction_mode.value,
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

    def _calibrated_char_pct_available(self) -> bool:
        if self.use_wli:
            return False
        try:
            models = self._active_models(False)
        except Exception:
            return False
        if len(models) != 1:
            return False
        ch, n, w = models[0]
        return (ch == "char") and (int(n) == 4) and (abs(float(w) - 1.0) <= 1e-9)

    def _score_base_channel_pct_batch(
        self,
        pt_b: np.ndarray,
        wli_b: np.ndarray | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        from rdp.core.types import ObjectiveFamily

        prev_mode = self._span_hamming_mode
        prev_enabled = self._span_hamming_enabled
        self._span_hamming_mode = SpanHammingMode.OFF
        self._span_hamming_enabled = False
        try:
            base_scores = np.asarray(self._score_batch_impl(pt_b, wli_b), dtype=self._score_dtype)
        finally:
            self._span_hamming_mode = prev_mode
            self._span_hamming_enabled = prev_enabled
        fam = getattr(self.objective, "family", None)
        if fam is ObjectiveFamily.ENERGY:
            base_pct = -np.expm1(-base_scores)
        else:
            base_pct = base_scores.copy()
        base_pct = np.asarray(
            np.clip(base_pct, self._ecdf_clamp_min, self._ecdf_clamp_max),
            dtype=self._score_dtype,
        )
        return base_pct, base_scores

    def _score_span_hamming_calibrated_batch(
        self,
        pt_b: np.ndarray,
        wli_b: np.ndarray | None,
    ) -> np.ndarray:
        from rdp.core.types import ObjectiveFamily

        backend = self._span_hamming_backend
        assets = self._span_hamming_assets
        lm_assets = getattr(self, "_span_hamming_lm_assets", None)
        lm_profile_source = getattr(
            self,
            "_span_hamming_lm_profile_source",
            SpanHammingLanguageModelProfileSource.RAW_SPAN_BY_LENGTH,
        ).value
        lm_tail_start_index = int(getattr(self, "_span_hamming_lm_tail_start_index", 0) or 0)
        lm_weight = float(getattr(self, "_span_hamming_lm_weight", 0.0) or 0.0)
        if backend is None or assets is None:
            raise ValueError("Calibrated span mode requires loaded span backend and assets")
        fam = getattr(self.objective, "family", None)
        if fam not in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY):
            raise ValueError("span_hamming_mode='calibrated' only supports ObjectiveFamily.PCT or ENERGY")
        if pt_b.ndim != 2:
            raise ValueError("pt_b must be rank-2 [B,L] in calibrated span mode")

        score_dtype = self._score_dtype
        B = int(pt_b.shape[0])
        span_raw = np.zeros((B,), dtype=score_dtype)
        span_cov = np.zeros((B,), dtype=score_dtype)
        span_q = np.zeros((B,), dtype=score_dtype)
        span_x = np.zeros((B,), dtype=score_dtype)
        span_pct = np.zeros((B,), dtype=score_dtype)
        span_energy = np.zeros((B,), dtype=score_dtype)
        span_bucket = np.full((B,), -1, dtype=np.int32)
        span_bucket_dir: list[str] = [""] * B
        lm_profile_margin_raw = np.full((B,), np.nan, dtype=score_dtype)
        lm_profile_pct_noise = np.full((B,), np.nan, dtype=score_dtype)
        lm_profile_pct_real = np.full((B,), np.nan, dtype=score_dtype)
        lm_profile_energy = np.zeros((B,), dtype=score_dtype)
        lm_mean_bin_index = np.full((B,), np.nan, dtype=score_dtype)
        lm_mean_bin_length = np.full((B,), np.nan, dtype=score_dtype)
        lm_tail_mass = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_available = np.zeros((B,), dtype=np.bool_)
        word_ngram_active = np.zeros((B,), dtype=np.bool_)
        word_ngram_exact_word_count = np.zeros((B,), dtype=np.int32)
        word_ngram_segment_count = np.zeros((B,), dtype=np.int32)
        word_ngram_n_positions = np.zeros((B,), dtype=np.int32)
        word_ngram_xent = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_backoff_xent = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_report_xent = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_report_backoff_xent = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_miss_rate = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_used5_rate = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_used4_rate = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_used3_rate = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_prefix_total_mean = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_prefix_total_min = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_prefix_total_ge_1_rate = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_prefix_total_ge_10_rate = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_prefix_total_ge_100_rate = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_trust_score = np.full((B,), np.nan, dtype=score_dtype)
        word_ngram_trust_tier: list[str | None] = [None] * B
        word_ngram_inactive_reason: list[str | None] = [None] * B
        char_pct: np.ndarray | None = None
        char_score: np.ndarray | None = None
        if self._span_hamming_use_char_channel:
            char_pct, char_score = self._score_base_channel_pct_batch(pt_b, wli_b)

        skip_span_by_char = np.zeros((B,), dtype=np.bool_)
        if lm_assets is None and char_pct is not None and self._span_hamming_char_pct_min is not None:
            skip_span_by_char = np.asarray(
                char_pct < float(self._span_hamming_char_pct_min),
                dtype=np.bool_,
            )
        eval_total = int(B)
        eval_skipped_char_gate = int(np.count_nonzero(skip_span_by_char))
        eval_active = int(max(0, eval_total - eval_skipped_char_gate))
        prev_total = int(self._telemetry.get("span_hamming_eval_total", 0) or 0)
        prev_active = int(self._telemetry.get("span_hamming_eval_active", 0) or 0)
        prev_skipped = int(self._telemetry.get("span_hamming_eval_skipped_char_gate", 0) or 0)
        self._telemetry["span_hamming_eval_total"] = int(prev_total + eval_total)
        self._telemetry["span_hamming_eval_active"] = int(prev_active + eval_active)
        self._telemetry["span_hamming_eval_skipped_char_gate"] = int(prev_skipped + eval_skipped_char_gate)

        def _bump_span_seconds(delta_s: float) -> None:
            dt = max(0.0, float(delta_s))
            if dt <= 0.0:
                return
            prev_seconds_total = float(self._telemetry.get("span_hamming_eval_seconds_total", 0.0) or 0.0)
            prev_seconds_active = float(self._telemetry.get("span_hamming_eval_active_seconds_total", 0.0) or 0.0)
            self._telemetry["span_hamming_eval_seconds_total"] = float(max(0.0, prev_seconds_total + dt))
            self._telemetry["span_hamming_eval_active_seconds_total"] = float(max(0.0, prev_seconds_active + dt))

        for i in range(B):
            if bool(skip_span_by_char[i]):
                span_bucket_dir[i] = str(self.direction.value)
                continue
            t_span = float(time.perf_counter())
            try:
                stats = backend.score(pt_b[i].tolist())
                span_raw_i = float(stats.span_raw)
                span_cov_i = float(stats.coverage)
                span_q_i = float(stats.quality)
            except Exception as exc:
                _bump_span_seconds(float(time.perf_counter() - t_span))
                raise ValueError(f"Span backend failed in calibrated mode: {exc}") from exc
            _bump_span_seconds(float(time.perf_counter() - t_span))
            selected_bucket = assets.select_bucket(
                direction=str(self.direction.value),
                text_length=int(pt_b.shape[1]),
            )
            bucket = assets.score_span_raw_in_bucket(
                direction=str(self.direction.value),
                length_bucket=int(selected_bucket),
                span_raw=span_raw_i,
                clamp_min=float(self._span_hamming_ecdf_clamp_min),
                clamp_max=float(self._span_hamming_ecdf_clamp_max),
            )
            span_raw[i] = score_dtype(span_raw_i)
            span_cov[i] = score_dtype(span_cov_i)
            span_q[i] = score_dtype(span_q_i)
            span_x[i] = score_dtype(float(bucket.x_span))
            span_pct[i] = score_dtype(float(bucket.span_pct))
            span_energy[i] = score_dtype(float(bucket.span_energy))
            span_bucket[i] = int(bucket.length_bucket)
            span_bucket_dir[i] = str(bucket.direction)
            word_ngram_i = self._score_word_ngram_signal(
                pt_values=pt_b[i].tolist(),
                span_stats=stats,
            )
            word_ngram_available[i] = bool(word_ngram_i.get("word_ngram_judge_available", False))
            word_ngram_active[i] = bool(word_ngram_i.get("word_ngram_judge_active", False))
            word_ngram_exact_word_count[i] = int(word_ngram_i.get("word_ngram_judge_exact_word_count", 0) or 0)
            word_ngram_segment_count[i] = int(word_ngram_i.get("word_ngram_judge_segment_count", 0) or 0)
            word_ngram_n_positions[i] = int(word_ngram_i.get("word_ngram_judge_n_positions", 0) or 0)
            for arr, key in (
                (word_ngram_xent, "word_ngram_judge_xent_3"),
                (word_ngram_backoff_xent, "word_ngram_judge_backoff_xent"),
                (word_ngram_report_xent, "word_ngram_judge_report_xent"),
                (word_ngram_report_backoff_xent, "word_ngram_judge_report_backoff_xent"),
                (word_ngram_miss_rate, "word_ngram_judge_miss_rate"),
                (word_ngram_used5_rate, "word_ngram_judge_used5_rate"),
                (word_ngram_used4_rate, "word_ngram_judge_used4_rate"),
                (word_ngram_used3_rate, "word_ngram_judge_used3_rate"),
                (word_ngram_prefix_total_mean, "word_ngram_judge_prefix_total_mean"),
                (word_ngram_prefix_total_min, "word_ngram_judge_prefix_total_min"),
                (word_ngram_prefix_total_ge_1_rate, "word_ngram_judge_prefix_total_ge_1_rate"),
                (word_ngram_prefix_total_ge_10_rate, "word_ngram_judge_prefix_total_ge_10_rate"),
                (word_ngram_prefix_total_ge_100_rate, "word_ngram_judge_prefix_total_ge_100_rate"),
                (word_ngram_trust_score, "word_ngram_judge_trust_score"),
            ):
                value = word_ngram_i.get(key)
                if value is not None:
                    arr[i] = score_dtype(float(value))
            word_ngram_trust_tier[i] = word_ngram_i.get("word_ngram_judge_trust_tier")
            word_ngram_inactive_reason[i] = word_ngram_i.get("word_ngram_judge_inactive_reason")
            if lm_assets is not None:
                lm_scored = lm_assets.score_profile_margin_l1_in_bucket(
                    stats=stats,
                    direction=str(self.direction.value),
                    length_bucket=int(selected_bucket),
                    clamp_min=float(self._span_hamming_ecdf_clamp_min),
                    clamp_max=float(self._span_hamming_ecdf_clamp_max),
                    profile_source=lm_profile_source,
                    tail_start_index=lm_tail_start_index,
                )
                lm_profile_margin_raw[i] = score_dtype(float(lm_scored.profile_margin_l1_raw))
                lm_profile_pct_noise[i] = score_dtype(float(lm_scored.profile_margin_l1_pct_noise))
                lm_profile_pct_real[i] = score_dtype(
                    float("nan") if lm_scored.profile_margin_l1_pct_real is None else float(lm_scored.profile_margin_l1_pct_real)
                )
                lm_profile_energy[i] = score_dtype(float(lm_scored.profile_margin_l1_energy))
                lm_mean_bin_index[i] = score_dtype(float(lm_scored.mean_bin_index_raw))
                lm_mean_bin_length[i] = score_dtype(float(lm_scored.mean_bin_length_raw))
                lm_tail_mass[i] = score_dtype(float(lm_scored.tail_mass_raw))

        if char_pct is None:
            combined_pct = span_pct.copy()
        elif self._span_hamming_combine_mode is SpanHammingCombineMode.MINIMUM:
            combined_pct = np.minimum(span_pct, char_pct)
        else:
            w_span = float(self._span_hamming_weight_span)
            w_char = float(self._span_hamming_weight_char)
            w_total = float(w_span + w_char)
            if w_total <= 0.0:
                raise ValueError(
                    "weighted_sum combine requires positive total weight "
                    "(span_hamming_weight_span + span_hamming_weight_char)"
                )
            combined_pct = ((w_span * span_pct) + (w_char * char_pct)) / w_total
        combined_pct = np.asarray(
            np.clip(combined_pct, self._span_hamming_ecdf_clamp_min, self._span_hamming_ecdf_clamp_max),
            dtype=score_dtype,
        )
        combined_energy = np.asarray(-np.log1p(-combined_pct), dtype=score_dtype)

        gate_failed = np.zeros((B,), dtype=np.bool_)
        gate_reasons_batch: list[list[str]] = [[] for _ in range(B)]
        for i in range(B):
            if bool(skip_span_by_char[i]):
                gate_failed[i] = True
                gate_reasons_batch[i].append("char_pct_below_min")
                continue
            if float(span_cov[i]) < float(self._span_hamming_coverage_min):
                gate_failed[i] = True
                gate_reasons_batch[i].append("coverage_below_min")
            if float(span_q[i]) < float(self._span_hamming_quality_min):
                gate_failed[i] = True
                gate_reasons_batch[i].append("quality_below_min")
            if self._span_hamming_span_pct_min is not None and float(span_pct[i]) < float(self._span_hamming_span_pct_min):
                gate_failed[i] = True
                gate_reasons_batch[i].append("span_pct_below_min")
            if (
                char_pct is not None
                and self._span_hamming_char_pct_min is not None
                and float(char_pct[i]) < float(self._span_hamming_char_pct_min)
            ):
                gate_failed[i] = True
                gate_reasons_batch[i].append("char_pct_below_min")

        span_energy_base = combined_energy.copy()
        lm_enabled_batch = np.full((B,), bool(lm_assets is not None), dtype=np.bool_)
        lm_applied_to_score = np.logical_and(lm_enabled_batch, np.logical_not(gate_failed))
        span_energy_total = span_energy_base.copy()
        if bool(lm_applied_to_score.any()):
            span_energy_total[lm_applied_to_score] = np.asarray(
                span_energy_base[lm_applied_to_score]
                + float(lm_weight) * lm_profile_energy[lm_applied_to_score],
                dtype=score_dtype,
            )
        span_pct_total = np.asarray(1.0 - np.exp(-span_energy_total), dtype=score_dtype)
        span_pct_total = np.asarray(
            np.clip(span_pct_total, self._span_hamming_ecdf_clamp_min, self._span_hamming_ecdf_clamp_max),
            dtype=score_dtype,
        )

        if fam is ObjectiveFamily.ENERGY:
            score_vec = span_energy_total.copy()
        else:
            score_vec = span_pct_total.copy()
        gate_policy = self._span_hamming_gate_fail_policy.value
        if bool(gate_failed.any()):
            score_vec = score_vec.copy()
            if gate_policy == "character_only" and char_score is not None:
                score_vec[gate_failed] = np.asarray(char_score, dtype=score_dtype)[
                    gate_failed
                ]
            else:
                score_vec[gate_failed] = score_dtype(float(self._span_hamming_gate_score_floor))

        if B == 1:
            i = 0
            objective = {
                "score_mean": float(score_vec[i]),
                "score_std": 0.0,
                "n_windows": 1,
                "span_raw": float(span_raw[i]),
                "span_coverage": float(span_cov[i]),
                "span_quality": float(span_q[i]),
                "span_x": float(span_x[i]),
                "span_pct": float(span_pct[i]),
                "span_energy": float(span_energy[i]),
                "char_pct": (None if char_pct is None else float(char_pct[i])),
                "char_score": (None if char_score is None else float(char_score[i])),
                "combine_mode": self._span_hamming_combine_mode.value,
                "combined_pct": float(combined_pct[i]),
                "combined_energy": float(combined_energy[i]),
                "span_energy_base": float(span_energy_base[i]),
                "span_energy_total": float(span_energy_total[i]),
                "span_pct_total": float(span_pct_total[i]),
                "span_bucket_length": int(span_bucket[i]),
                "span_bucket_direction": str(span_bucket_dir[i]),
                "gate_failed": bool(gate_failed[i]),
                "gate_reasons": list(gate_reasons_batch[i]),
                "gate_fail_policy": gate_policy,
                "span_lm_enabled": bool(lm_enabled_batch[i]),
                "span_lm_applied_to_score": bool(lm_applied_to_score[i]),
                "word_ngram_judge_active": bool(word_ngram_active[i]),
                "word_ngram_judge_report_xent": (
                    None if np.isnan(word_ngram_report_xent[i]) else float(word_ngram_report_xent[i])
                ),
                "word_ngram_judge_trust_tier": word_ngram_trust_tier[i],
            }
            self._last_stats = {
                "n_windows": 1,
                "score_mean": float(score_vec[i]),
                "score_std": 0.0,
                "stat.name": "x_span",
                "stat.variant": "span_full_text",
                "stat.mean_per_ngram_penalized": float(span_raw[i]),
                "span_hamming_mode": "calibrated",
                "span_hamming_combine_mode": self._span_hamming_combine_mode.value,
                "span_hamming_weight_span": float(self._span_hamming_weight_span),
                "span_hamming_weight_char": float(self._span_hamming_weight_char),
                "span_hamming_use_char_channel": bool(self._span_hamming_use_char_channel),
                "span_hamming_raw": float(span_raw[i]),
                "span_hamming_coverage": float(span_cov[i]),
                "span_hamming_quality": float(span_q[i]),
                "span_hamming_x": float(span_x[i]),
                "span_hamming_pct": float(span_pct[i]),
                "span_hamming_energy": float(span_energy[i]),
                "span_hamming_char_pct": (None if char_pct is None else float(char_pct[i])),
                "span_hamming_char_score": (None if char_score is None else float(char_score[i])),
                "span_hamming_combined_pct": float(combined_pct[i]),
                "span_hamming_combined_energy": float(combined_energy[i]),
                "span_energy_base": float(span_energy_base[i]),
                "span_energy_total": float(span_energy_total[i]),
                "span_pct_total": float(span_pct_total[i]),
                "span_hamming_bucket_length": int(span_bucket[i]),
                "span_hamming_bucket_direction": str(span_bucket_dir[i]),
                "span_hamming_gate_failed": bool(gate_failed[i]),
                "span_hamming_gate_reasons": list(gate_reasons_batch[i]),
                "span_hamming_gate_score_floor": float(self._span_hamming_gate_score_floor),
                "span_hamming_span_skipped": bool(skip_span_by_char[i]),
                "span_hamming_gate_fail_policy": gate_policy,
                "span_lm_enabled": bool(lm_enabled_batch[i]),
                "span_lm_applied_to_score": bool(lm_applied_to_score[i]),
                "span_lm_profile_source": (
                    None if lm_assets is None else str(lm_profile_source)
                ),
                "span_lm_tail_start_index": (
                    None if lm_assets is None else int(lm_tail_start_index)
                ),
                "span_lm_tail_start_index_used_for_score": False,
                "span_lm_weight": float(lm_weight),
                "span_lm_length_bucket": (None if lm_assets is None else int(span_bucket[i])),
                "span_lm_profile_margin_l1_raw": (
                    None if lm_assets is None else float(lm_profile_margin_raw[i])
                ),
                "span_lm_profile_margin_l1_pct_noise": (
                    None if lm_assets is None else float(lm_profile_pct_noise[i])
                ),
                "span_lm_profile_margin_l1_pct_real": (
                    None if lm_assets is None else float(lm_profile_pct_real[i])
                ),
                "span_lm_profile_energy": (
                    None if lm_assets is None else float(lm_profile_energy[i])
                ),
                "span_lm_mean_bin_index_raw": (
                    None if lm_assets is None else float(lm_mean_bin_index[i])
                ),
                "span_lm_mean_bin_length_raw": (
                    None if lm_assets is None else float(lm_mean_bin_length[i])
                ),
                "span_lm_tail_mass_raw": (
                    None if lm_assets is None else float(lm_tail_mass[i])
                ),
                "word_ngram_judge_available": bool(word_ngram_available[i]),
                "word_ngram_judge_active": bool(word_ngram_active[i]),
                "word_ngram_judge_inactive_reason": word_ngram_inactive_reason[i],
                "word_ngram_judge_exact_word_count": int(word_ngram_exact_word_count[i]),
                "word_ngram_judge_segment_count": int(word_ngram_segment_count[i]),
                "word_ngram_judge_xent_3": (
                    None if np.isnan(word_ngram_xent[i]) else float(word_ngram_xent[i])
                ),
                "word_ngram_judge_backoff_xent": (
                    None if np.isnan(word_ngram_backoff_xent[i]) else float(word_ngram_backoff_xent[i])
                ),
                "word_ngram_judge_n_positions": int(word_ngram_n_positions[i]),
                "word_ngram_judge_miss_rate": (
                    None if np.isnan(word_ngram_miss_rate[i]) else float(word_ngram_miss_rate[i])
                ),
                "word_ngram_judge_used5_rate": (
                    None if np.isnan(word_ngram_used5_rate[i]) else float(word_ngram_used5_rate[i])
                ),
                "word_ngram_judge_used4_rate": (
                    None if np.isnan(word_ngram_used4_rate[i]) else float(word_ngram_used4_rate[i])
                ),
                "word_ngram_judge_used3_rate": (
                    None if np.isnan(word_ngram_used3_rate[i]) else float(word_ngram_used3_rate[i])
                ),
                "word_ngram_judge_prefix_total_mean": (
                    None if np.isnan(word_ngram_prefix_total_mean[i]) else float(word_ngram_prefix_total_mean[i])
                ),
                "word_ngram_judge_prefix_total_min": (
                    None if np.isnan(word_ngram_prefix_total_min[i]) else float(word_ngram_prefix_total_min[i])
                ),
                "word_ngram_judge_prefix_total_ge_1_rate": (
                    None if np.isnan(word_ngram_prefix_total_ge_1_rate[i]) else float(word_ngram_prefix_total_ge_1_rate[i])
                ),
                "word_ngram_judge_prefix_total_ge_10_rate": (
                    None if np.isnan(word_ngram_prefix_total_ge_10_rate[i]) else float(word_ngram_prefix_total_ge_10_rate[i])
                ),
                "word_ngram_judge_prefix_total_ge_100_rate": (
                    None if np.isnan(word_ngram_prefix_total_ge_100_rate[i]) else float(word_ngram_prefix_total_ge_100_rate[i])
                ),
                "word_ngram_judge_trust_score": (
                    None if np.isnan(word_ngram_trust_score[i]) else float(word_ngram_trust_score[i])
                ),
                "word_ngram_judge_trust_tier": word_ngram_trust_tier[i],
                "word_ngram_judge_report_xent": (
                    None if np.isnan(word_ngram_report_xent[i]) else float(word_ngram_report_xent[i])
                ),
                "word_ngram_judge_report_backoff_xent": (
                    None if np.isnan(word_ngram_report_backoff_xent[i]) else float(word_ngram_report_backoff_xent[i])
                ),
                "span_hamming_eval_total_batch": int(eval_total),
                "span_hamming_eval_active_batch": int(eval_active),
                "span_hamming_eval_skipped_char_gate_batch": int(eval_skipped_char_gate),
                "objective_stats": objective,
            }
        else:
            self._last_stats = {
                "n_windows": 1,
                "score_mean_batch": score_vec.astype(score_dtype, copy=False).tolist(),
                "score_std_batch": [0.0] * B,
                "span_hamming_mode": "calibrated",
                "span_hamming_combine_mode": self._span_hamming_combine_mode.value,
                "span_hamming_weight_span": float(self._span_hamming_weight_span),
                "span_hamming_weight_char": float(self._span_hamming_weight_char),
                "span_hamming_use_char_channel": bool(self._span_hamming_use_char_channel),
                "span_hamming_raw_batch": span_raw.astype(score_dtype, copy=False).tolist(),
                "span_hamming_coverage_batch": span_cov.astype(score_dtype, copy=False).tolist(),
                "span_hamming_quality_batch": span_q.astype(score_dtype, copy=False).tolist(),
                "span_hamming_x_batch": span_x.astype(score_dtype, copy=False).tolist(),
                "span_hamming_pct_batch": span_pct.astype(score_dtype, copy=False).tolist(),
                "span_hamming_energy_batch": span_energy.astype(score_dtype, copy=False).tolist(),
                "span_hamming_char_pct_batch": (
                    None if char_pct is None else np.asarray(char_pct, dtype=score_dtype).tolist()
                ),
                "span_hamming_char_score_batch": (
                    None if char_score is None else np.asarray(char_score, dtype=score_dtype).tolist()
                ),
                "span_hamming_combined_pct_batch": combined_pct.astype(score_dtype, copy=False).tolist(),
                "span_hamming_combined_energy_batch": combined_energy.astype(score_dtype, copy=False).tolist(),
                "span_energy_base_batch": span_energy_base.astype(score_dtype, copy=False).tolist(),
                "span_energy_total_batch": span_energy_total.astype(score_dtype, copy=False).tolist(),
                "span_pct_total_batch": span_pct_total.astype(score_dtype, copy=False).tolist(),
                "span_hamming_bucket_length_batch": span_bucket.astype(np.int32, copy=False).tolist(),
                "span_hamming_bucket_direction_batch": list(span_bucket_dir),
                "span_hamming_gate_failed_batch": gate_failed.astype(np.bool_, copy=False).tolist(),
                "span_hamming_gate_reasons_batch": gate_reasons_batch,
                "span_hamming_gate_score_floor": float(self._span_hamming_gate_score_floor),
                "span_hamming_span_skipped_batch": skip_span_by_char.astype(np.bool_, copy=False).tolist(),
                "span_hamming_gate_fail_policy": gate_policy,
                "span_lm_enabled_batch": lm_enabled_batch.astype(np.bool_, copy=False).tolist(),
                "span_lm_applied_to_score_batch": lm_applied_to_score.astype(np.bool_, copy=False).tolist(),
                "span_lm_profile_margin_l1_raw_batch": (
                    None if lm_assets is None else lm_profile_margin_raw.astype(score_dtype, copy=False).tolist()
                ),
                "span_lm_profile_margin_l1_pct_noise_batch": (
                    None if lm_assets is None else lm_profile_pct_noise.astype(score_dtype, copy=False).tolist()
                ),
                "span_lm_profile_margin_l1_pct_real_batch": (
                    None if lm_assets is None else lm_profile_pct_real.astype(score_dtype, copy=False).tolist()
                ),
                "span_lm_profile_energy_batch": (
                    None if lm_assets is None else lm_profile_energy.astype(score_dtype, copy=False).tolist()
                ),
                "span_lm_mean_bin_index_raw_batch": (
                    None if lm_assets is None else lm_mean_bin_index.astype(score_dtype, copy=False).tolist()
                ),
                "span_lm_mean_bin_length_raw_batch": (
                    None if lm_assets is None else lm_mean_bin_length.astype(score_dtype, copy=False).tolist()
                ),
                "span_lm_tail_mass_raw_batch": (
                    None if lm_assets is None else lm_tail_mass.astype(score_dtype, copy=False).tolist()
                ),
                "word_ngram_judge_available_batch": word_ngram_available.astype(np.bool_, copy=False).tolist(),
                "word_ngram_judge_active_batch": word_ngram_active.astype(np.bool_, copy=False).tolist(),
                "word_ngram_judge_inactive_reason_batch": list(word_ngram_inactive_reason),
                "word_ngram_judge_exact_word_count_batch": word_ngram_exact_word_count.astype(np.int32, copy=False).tolist(),
                "word_ngram_judge_segment_count_batch": word_ngram_segment_count.astype(np.int32, copy=False).tolist(),
                "word_ngram_judge_xent_3_batch": word_ngram_xent.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_backoff_xent_batch": word_ngram_backoff_xent.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_n_positions_batch": word_ngram_n_positions.astype(np.int32, copy=False).tolist(),
                "word_ngram_judge_miss_rate_batch": word_ngram_miss_rate.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_used5_rate_batch": word_ngram_used5_rate.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_used4_rate_batch": word_ngram_used4_rate.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_used3_rate_batch": word_ngram_used3_rate.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_prefix_total_mean_batch": word_ngram_prefix_total_mean.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_prefix_total_min_batch": word_ngram_prefix_total_min.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_prefix_total_ge_1_rate_batch": word_ngram_prefix_total_ge_1_rate.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_prefix_total_ge_10_rate_batch": word_ngram_prefix_total_ge_10_rate.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_prefix_total_ge_100_rate_batch": word_ngram_prefix_total_ge_100_rate.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_trust_score_batch": word_ngram_trust_score.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_trust_tier_batch": list(word_ngram_trust_tier),
                "word_ngram_judge_report_xent_batch": word_ngram_report_xent.astype(score_dtype, copy=False).tolist(),
                "word_ngram_judge_report_backoff_xent_batch": word_ngram_report_backoff_xent.astype(score_dtype, copy=False).tolist(),
                "span_hamming_eval_total_batch": int(eval_total),
                "span_hamming_eval_active_batch": int(eval_active),
                "span_hamming_eval_skipped_char_gate_batch": int(eval_skipped_char_gate),
            }

        _tstash(self._telemetry, **self._last_stats)
        try:
            self._last_raw_batch = span_raw.astype(score_dtype, copy=False)
            self._last_raw_std_batch = np.zeros_like(span_raw, dtype=score_dtype)
        except Exception:
            pass
        return score_vec.astype(score_dtype, copy=False)

    def _apply_span_hamming_bonus_batch(self, scores: np.ndarray, pt_b: np.ndarray) -> np.ndarray:
        if getattr(self, "_span_hamming_mode", SpanHammingMode.OFF) is not SpanHammingMode.RAW_BONUS:
            return scores
        backend = self._span_hamming_backend
        weight = float(self._span_hamming_weight)
        if backend is None or weight == 0.0:
            return scores
        if pt_b.ndim != 2 or scores.ndim != 1:
            return scores
        B = int(pt_b.shape[0])
        if B == 0:
            return scores

        prev_total = int(self._telemetry.get("span_hamming_eval_total", 0) or 0)
        prev_active = int(self._telemetry.get("span_hamming_eval_active", 0) or 0)
        self._telemetry["span_hamming_eval_total"] = int(prev_total + B)
        self._telemetry["span_hamming_eval_active"] = int(prev_active + B)

        span_raw = np.zeros((B,), dtype=self._score_dtype)
        span_cov = np.zeros((B,), dtype=self._score_dtype)
        span_q = np.zeros((B,), dtype=self._score_dtype)
        word_ngram_available = np.zeros((B,), dtype=np.bool_)
        word_ngram_active = np.zeros((B,), dtype=np.bool_)
        word_ngram_n_positions = np.zeros((B,), dtype=np.int32)
        word_ngram_xent = np.full((B,), np.nan, dtype=self._score_dtype)
        word_ngram_report_xent = np.full((B,), np.nan, dtype=self._score_dtype)
        word_ngram_trust_score = np.full((B,), np.nan, dtype=self._score_dtype)
        word_ngram_inactive_reason: list[str | None] = [None] * B
        word_ngram_trust_tier: list[str | None] = [None] * B
        span_seconds_total = 0.0
        for i in range(B):
            t_span = float(time.perf_counter())
            try:
                stats = backend.score(pt_b[i].tolist())
                span_raw[i] = float(stats.span_raw)
                span_cov[i] = float(stats.coverage)
                span_q[i] = float(stats.quality)
                word_ngram_i = self._score_word_ngram_signal(
                    pt_values=pt_b[i].tolist(),
                    span_stats=stats,
                )
                word_ngram_available[i] = bool(word_ngram_i.get("word_ngram_judge_available", False))
                word_ngram_active[i] = bool(word_ngram_i.get("word_ngram_judge_active", False))
                word_ngram_n_positions[i] = int(word_ngram_i.get("word_ngram_judge_n_positions", 0) or 0)
                if word_ngram_i.get("word_ngram_judge_xent_3") is not None:
                    word_ngram_xent[i] = float(word_ngram_i["word_ngram_judge_xent_3"])
                if word_ngram_i.get("word_ngram_judge_report_xent") is not None:
                    word_ngram_report_xent[i] = float(word_ngram_i["word_ngram_judge_report_xent"])
                if word_ngram_i.get("word_ngram_judge_trust_score") is not None:
                    word_ngram_trust_score[i] = float(word_ngram_i["word_ngram_judge_trust_score"])
                word_ngram_inactive_reason[i] = word_ngram_i.get("word_ngram_judge_inactive_reason")
                word_ngram_trust_tier[i] = word_ngram_i.get("word_ngram_judge_trust_tier")
            except Exception:
                span_raw[i] = 0.0
                span_cov[i] = 0.0
                span_q[i] = 0.0
            span_seconds_total += max(0.0, float(time.perf_counter() - t_span))

        prev_seconds_total = float(self._telemetry.get("span_hamming_eval_seconds_total", 0.0) or 0.0)
        prev_seconds_active = float(self._telemetry.get("span_hamming_eval_active_seconds_total", 0.0) or 0.0)
        self._telemetry["span_hamming_eval_seconds_total"] = float(max(0.0, prev_seconds_total + span_seconds_total))
        self._telemetry["span_hamming_eval_active_seconds_total"] = float(max(0.0, prev_seconds_active + span_seconds_total))

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
            stats["word_ngram_judge_available_batch"] = word_ngram_available.astype(np.bool_, copy=False).tolist()
            stats["word_ngram_judge_active_batch"] = word_ngram_active.astype(np.bool_, copy=False).tolist()
            stats["word_ngram_judge_inactive_reason_batch"] = list(word_ngram_inactive_reason)
            stats["word_ngram_judge_n_positions_batch"] = word_ngram_n_positions.astype(np.int32, copy=False).tolist()
            stats["word_ngram_judge_xent_3_batch"] = word_ngram_xent.astype(self._score_dtype, copy=False).tolist()
            stats["word_ngram_judge_report_xent_batch"] = word_ngram_report_xent.astype(self._score_dtype, copy=False).tolist()
            stats["word_ngram_judge_trust_score_batch"] = word_ngram_trust_score.astype(self._score_dtype, copy=False).tolist()
            stats["word_ngram_judge_trust_tier_batch"] = list(word_ngram_trust_tier)
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
                stats["word_ngram_judge_available"] = bool(word_ngram_available[0])
                stats["word_ngram_judge_active"] = bool(word_ngram_active[0])
                stats["word_ngram_judge_inactive_reason"] = word_ngram_inactive_reason[0]
                stats["word_ngram_judge_n_positions"] = int(word_ngram_n_positions[0])
                stats["word_ngram_judge_xent_3"] = None if np.isnan(word_ngram_xent[0]) else float(word_ngram_xent[0])
                stats["word_ngram_judge_report_xent"] = None if np.isnan(word_ngram_report_xent[0]) else float(word_ngram_report_xent[0])
                stats["word_ngram_judge_trust_score"] = None if np.isnan(word_ngram_trust_score[0]) else float(word_ngram_trust_score[0])
                stats["word_ngram_judge_trust_tier"] = word_ngram_trust_tier[0]
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
                word_ngram_judge_available_batch=word_ngram_available.astype(np.bool_, copy=False).tolist(),
                word_ngram_judge_active_batch=word_ngram_active.astype(np.bool_, copy=False).tolist(),
                word_ngram_judge_inactive_reason_batch=list(word_ngram_inactive_reason),
                word_ngram_judge_n_positions_batch=word_ngram_n_positions.astype(np.int32, copy=False).tolist(),
                word_ngram_judge_xent_3_batch=word_ngram_xent.astype(self._score_dtype, copy=False).tolist(),
                word_ngram_judge_report_xent_batch=word_ngram_report_xent.astype(self._score_dtype, copy=False).tolist(),
                word_ngram_judge_trust_score_batch=word_ngram_trust_score.astype(self._score_dtype, copy=False).tolist(),
                word_ngram_judge_trust_tier_batch=list(word_ngram_trust_tier),
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
            from rdp.scoring.hamming.anneal import compute_hamming_weight
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
        from rdp.core.types import ObjectiveFamily, Stat
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

        if getattr(self, "_span_hamming_mode", SpanHammingMode.OFF) is SpanHammingMode.CALIBRATED:
            scores = self._score_span_hamming_calibrated_batch(pt_b, wli_b)
        else:
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
