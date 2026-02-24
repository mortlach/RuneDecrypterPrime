# ============================================================
# rune_decrypter_prime/core/runtime.py
# Canonical binding of cipher, scorer, ciphertext, and telemetry.
# ============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple, Any

from rune_decrypter_prime.core.config import CipherConfig, InterruptorConfig
from rune_decrypter_prime.core.config.hard_crib import HardCribConfig, normalize_hard_crib_config
from rune_decrypter_prime.telemetry.bag import TelemetryBag
from rune_decrypter_prime.core.telemetry import _Timer
from rune_decrypter_prime.core.types import (
    Device,
    InterruptorSearchStrategy,
    ObjectiveFamily,
    ensure_device,
    ensure_interruptor_search_strategy,
    KEY_DTYPE,
)
from rune_decrypter_prime.telemetry.pipeline import device_request_str
from rune_decrypter_prime.keyops.registry import create as create_keyops
from rune_decrypter_prime.io.logging_adapter import module_logger
from rune_decrypter_prime.backends.xp import select_backend
from rune_decrypter_prime.backends.xp import to_numpy
from rune_decrypter_prime.telemetry.schema import (
    to_canonical_device_str,
    to_canonical_impl_str,  # kept available for callers; unused here
)

logger = module_logger(__name__)


@dataclass(slots=True)
class _CompiledHardCrib:
    fixed_chars: dict[int, frozenset[int]]
    per_word_allowed: dict[int, frozenset[tuple[int, ...]]]
    global_allowed_by_len: dict[int, frozenset[tuple[int, ...]]]
    word_spans: tuple[tuple[int, int], ...]

    @property
    def has_word_rules(self) -> bool:
        return bool(self.per_word_allowed) or bool(self.global_allowed_by_len)


@dataclass(slots=True)
class DecryptionProblem:
    """
    Canonical problem definition consumed by solver.
    Holds cipher, scorer, configs, ciphertext/WLI, and telemetry.
    """
    cipher: object
    scorer: object
    c_cfg: CipherConfig
    s_cfg: Any = None

    # ---- fields initialised in __post_init__ ----
    keyops: Any = field(init=False, repr=False)
    K: int = field(init=False, default=0)
    ciphertext_len: int = field(init=False, default=0)
    xp: Any = field(default=None, repr=False)
    key_dtype: Any = field(init=False, repr=False, default=KEY_DTYPE)

    telemetry: TelemetryBag = field(default_factory=TelemetryBag)

    enable_telemetry: bool = True
    ciphertext: Optional[Any] = None          # xp.ndarray[uint8]
    wli_data: Optional[Sequence[Tuple[int, int]]] = None
    key_length: Optional[int] = None
    _hard_crib_cfg: Optional[HardCribConfig] = field(init=False, default=None, repr=False)
    _hard_crib_compiled: Optional[_CompiledHardCrib] = field(init=False, default=None, repr=False)

    # =========================================================
    # Lifecycle
    # =========================================================
    def __post_init__(self):
        # Ensure TelemetryBag
        if not isinstance(self.telemetry, TelemetryBag):
            self.telemetry = TelemetryBag(dict(self.telemetry) if isinstance(self.telemetry, dict) else {})

        t = self.telemetry  # shorthand

        # Seed canonical telemetry keys (harmless if later overwritten by engine/scorer)
        dev_kind = ensure_device(getattr(self.c_cfg, "device", Device.CPU))
        t.setdefault("device", to_canonical_device_str(dev_kind))
        try:
            enc_dir = getattr(self.c_cfg, "encoding_dir", None)
            if enc_dir is not None and hasattr(enc_dir, "value"):
                t.setdefault("direction", enc_dir.value)
        except Exception:
            pass

        # Timers/counters
        t.setdefault("decrypt_time_s", 0.0)
        t.setdefault("score_time_s", 0.0)
        t.setdefault("eval_keys", 0)
        t.setdefault("eval_batches", 0)
        t.setdefault("tokens_processed", 0)
        t.setdefault("evaluate_keys_calls", 0)
        t.setdefault("candidates_evaluated", 0)
        t.setdefault("score_batch_calls", 0)
        t.setdefault("score_batch_with_raw_calls", 0)
        t.setdefault("score_batch_fallback_scalar", 0)
        t.setdefault("score_batch_with_raw_fallback_scalar", 0)
        t.setdefault("lm_load_time_s", 0)
        t.setdefault("crib_enabled", False)
        t.setdefault("crib_mode", None)
        t.setdefault("crib_pass_total", 0)
        t.setdefault("crib_reject_total", 0)
        t.setdefault("crib_reject_fixed_char", 0)
        t.setdefault("crib_reject_word_index", 0)
        t.setdefault("crib_reject_global_len", 0)
        t.setdefault("crib_all_rejected_batches", 0)

        # Normalise config
        if isinstance(self.c_cfg, dict):
            self.c_cfg = CipherConfig(**self.c_cfg)
        if not isinstance(self.c_cfg, CipherConfig):
            raise TypeError(f"c_cfg must be CipherConfig, got {type(self.c_cfg)}")

        # Backend handle
        if self.xp is None:
            req = device_request_str(dev_kind)  # "cpu" or "cuda"
            _, self.xp = select_backend(req)

        # Bind ciphertext / WLI / key_length
        self.ciphertext = self.xp.asarray(self.c_cfg.ciphertext, dtype=self.xp.uint8)
        raw_wli = getattr(self.c_cfg, "wli_data", None)
        if raw_wli is None or (hasattr(raw_wli, "__len__") and len(raw_wli) == 0):
            self.wli_data = None
        else:
            self.wli_data = [[int(p[0]), int(p[1])] for p in raw_wli]
        self.key_length = self.c_cfg.key_length

        self.ciphertext_len = (
            int(self.ciphertext.shape[-1]) if hasattr(self.ciphertext, "shape")
            else int(len(self.ciphertext or []))
        )

        # Construct KeyOps (and resolve fixed K)
        self.keyops = self._build_keyops_for_problem()
        self.key_dtype = getattr(self.keyops, "dtype", KEY_DTYPE)
        self._hard_crib_cfg = self._resolve_hard_crib_cfg()
        self._hard_crib_compiled = self._compile_hard_crib(self._hard_crib_cfg)
        self.telemetry["crib_enabled"] = bool(self._hard_crib_compiled is not None)
        self.telemetry["crib_mode"] = (
            self._hard_crib_cfg.mode.value if isinstance(self._hard_crib_cfg, HardCribConfig) else None
        )

    # =========================================================
    # KeyOps construction (single source of truth for K)
    # =========================================================
    def _build_keyops_for_problem(self):
        """
        Decide KeyOps family and fixed key length K, then construct the KeyOps.
        Priority for K:
          1) cipher.key_length
          2) self.key_length (CipherConfig/UI)
          3) len(self.c_cfg.test_key) if provided
        """
        # --- resolve K ---
        K = None
        if hasattr(self.cipher, "key_length"):
            kl = self.cipher.key_length
            K = int(kl() if callable(kl) else kl) if kl is not None else None
        if K is None and self.key_length is not None:
            K = int(self.key_length)
        test_key = getattr(self.c_cfg, "test_key", None)
        if K is None and test_key is not None:
            K = int(len(test_key))
        if K is None or K <= 0:
            raise ValueError("Fixed key length required (cipher.key_length / config.key_length / test_key)")

        # --- resolve family ---
        family = getattr(self.cipher, "keyops_family", None) or getattr(self.c_cfg, "keyops_family", None)
        if not family:
            family = "vector" if getattr(self.cipher, "is_vector_key", False) else "perm"
        core_family = family

        if self._interruptors_search_enabled():
            family = "composite"

        # --- construct ---
        hints = self._gather_keyops_hints()
        if str(family).lower() == "composite":
            hints.setdefault("core_family", core_family)
        try:
            keyops = create_keyops(family, K=K, **hints)
        except TypeError:
            logger.info("problem: %s", "!!warning old keyops params!!")
            keyops = create_keyops(family, length=K, **hints)

        caps_len = int(getattr(getattr(keyops, "caps", None), "length", K))
        if caps_len != int(K):
            traits = getattr(getattr(keyops, "caps", None), "traits", {}) or {}
            core_len = traits.get("core_length")
            if core_len is None or int(core_len) != int(K):
                raise ValueError(f"KeyOps length mismatch: caps.length={caps_len} != resolved K={K}")
        return keyops

    # =========================================================
    # Core evaluation (decrypt + score) used by all solvers
    # =========================================================
    def _decrypt_batch(self, k_uint8: Any):
        """
        Decrypt a batch of keys -> list of plaintexts (length B).
        Always returns a Python list for scorer compatibility.
        """
        core_keys, key_interrupts = self._split_key_batch(k_uint8)
        if key_interrupts is None:
            interrupt_idx = self._normalize_interrupt_idx(self._resolve_interrupt_idx())
            plains = self.cipher.decrypt(
                ciphertext=self.ciphertext,
                key=core_keys,
                interrupt_idx=interrupt_idx,
                interrupt_sym=None,
            )
            if hasattr(plains, "ndim") and plains.ndim >= 2:
                return [plains[i] for i in range(plains.shape[0])]
            return list(plains)

        core = to_numpy(core_keys).astype(self.key_dtype, copy=False)
        intr = to_numpy(key_interrupts).astype("intp", copy=False)
        if core.ndim == 1:
            core = core[None, :]
        if intr.ndim == 1:
            intr = intr[None, :]

        out = []
        for i in range(core.shape[0]):
            idx = self._normalize_interrupt_idx(intr[i])
            pt = self.cipher.decrypt(
                ciphertext=self.ciphertext,
                key=core[i],
                interrupt_idx=idx,
                interrupt_sym=None,
            )
            if hasattr(pt, "ndim") and pt.ndim >= 2:
                pt = pt[0]
            out.append(pt)
        return out

    def _interruptor_cfg(self) -> Optional[InterruptorConfig]:
        cfg = getattr(self.c_cfg, "interruptors_cfg", None)
        return cfg if isinstance(cfg, InterruptorConfig) else None

    def _normalize_interrupt_idx(self, idx):
        if idx is None:
            return None
        arr = to_numpy(idx).astype("intp", copy=False).reshape(-1)
        if arr.size == 0:
            return None
        arr = arr[arr >= 0]
        if arr.size == 0:
            return None
        return arr

    def _resolve_interrupt_idx(self):
        """Resolve canonical interruptor positions with exact taking precedence."""
        cfg = self._interruptor_cfg()
        if cfg is not None:
            if cfg.mode == "exact":
                return cfg.exact
            return None

        exact = getattr(self.c_cfg, "interruptors_exact", None)
        if exact is not None:
            return exact
        legacy = getattr(self.c_cfg, "interruptors", None)
        if legacy is not None:
            return legacy
        return None

    def _interruptors_search_enabled(self) -> bool:
        cfg = self._interruptor_cfg()
        if cfg is not None:
            if cfg.mode != "pool":
                return False
            try:
                return int(cfg.max_count or 0) > 0 and len(cfg.pool or []) > 0
            except Exception:
                return False

        if getattr(self.c_cfg, "interruptors_exact", None) is not None:
            return False
        pool = getattr(self.c_cfg, "interruptors_pool", None)
        max_n = getattr(self.c_cfg, "interruptors_max", None)
        if pool is None or max_n is None:
            return False
        try:
            return int(max_n) > 0 and len(pool) > 0
        except Exception:
            return False

    @staticmethod
    def _seq_len(seq) -> int:
        if hasattr(seq, "shape") and getattr(seq, "shape", None):
            return int(seq.shape[-1])
        return int(len(seq))

    @staticmethod
    def _iter_plaintexts(plains_seq):
        if plains_seq is None:
            return []
        if hasattr(plains_seq, "ndim") and int(getattr(plains_seq, "ndim", 0)) == 1:
            return [plains_seq]
        return plains_seq

    def _validate_wli_alignment(self, plains_seq, wli) -> None:
        if wli is None:
            return
        if not (isinstance(wli, (list, tuple)) and all(
            isinstance(p, (list, tuple)) and len(p) == 2 and isinstance(p[0], int) and isinstance(p[1], int)
            for p in wli
        )):
            raise TypeError("WLI must be a list of (int,int) pairs or empty list")
        wli_len = int(len(wli))
        for i, pt in enumerate(self._iter_plaintexts(plains_seq)):
            try:
                pt_len = self._seq_len(pt)
            except Exception as exc:
                raise ValueError("Unable to determine plaintext length for WLI alignment check") from exc
            if pt_len != wli_len:
                raise ValueError(
                    f"WLI length {wli_len} does not match plaintext length {pt_len} at batch index {i}. "
                    "This indicates scoring text length drift (e.g., interruptor stripping/compaction)."
                )

    def _split_key_batch(self, keys: Any):
        keys_np = to_numpy(keys)
        split = getattr(self.keyops, "split_key", None)
        if callable(split):
            return split(keys_np)
        return keys_np, None

    def _resolve_hard_crib_cfg(self) -> Optional[HardCribConfig]:
        raw = None
        s_cfg = getattr(self, "s_cfg", None)
        if s_cfg is not None:
            if isinstance(s_cfg, dict):
                raw = s_cfg.get("hard_crib")
            else:
                raw = getattr(s_cfg, "hard_crib", None)
        return normalize_hard_crib_config(raw)

    @staticmethod
    def _word_spans_from_wli(wli: Sequence[Tuple[int, int]]) -> tuple[tuple[int, int], ...]:
        if not wli:
            return tuple()
        spans: list[tuple[int, int]] = []
        i = 0
        n = int(len(wli))
        while i < n:
            pos0, ln0 = int(wli[i][0]), int(wli[i][1])
            if pos0 != 0:
                raise ValueError("WLI must start each word with pos_in_word=0")
            if ln0 <= 0:
                raise ValueError("WLI word_len must be > 0")
            end = i + ln0
            if end > n:
                raise ValueError("WLI word_len exceeds available positions")
            for off in range(ln0):
                p, ln = int(wli[i + off][0]), int(wli[i + off][1])
                if p != off or ln != ln0:
                    raise ValueError("WLI does not form contiguous [pos,len] sequences per word")
            spans.append((i, end))
            i = end
        return tuple(spans)

    def _compile_hard_crib(self, cfg: Optional[HardCribConfig]) -> Optional[_CompiledHardCrib]:
        if cfg is None or (not bool(cfg.enabled)) or (not bool(cfg.has_any_rules)):
            return None

        fixed_chars: dict[int, frozenset[int]] = {}
        for pos, allowed in (cfg.fixed_chars or {}).items():
            p = int(pos)
            if p < 0 or p >= int(self.ciphertext_len):
                raise ValueError(f"hard_crib.fixed_chars position {p} out of range for text length {self.ciphertext_len}")
            fixed_chars[p] = frozenset(int(v) for v in allowed)

        has_word_rules = bool(cfg.has_word_rules)
        if has_word_rules and self.wli_data is None:
            if bool(cfg.require_wli_for_word_rules):
                raise ValueError("hard_crib word rules require WLI data, but WLI is missing for this run")
            has_word_rules = False

        word_spans: tuple[tuple[int, int], ...] = tuple()
        per_word_allowed: dict[int, frozenset[tuple[int, ...]]] = {}
        global_allowed_by_len: dict[int, frozenset[tuple[int, ...]]] = {}

        if has_word_rules:
            word_spans = self._word_spans_from_wli(self.wli_data)  # type: ignore[arg-type]
            n_words = int(len(word_spans))

            for word_idx, allowed_words in (cfg.per_word_allowed or {}).items():
                idx = int(word_idx)
                if idx < 0 or idx >= n_words:
                    raise ValueError(f"hard_crib.per_word_allowed index {idx} out of range for {n_words} words")
                start, end = word_spans[idx]
                expected_len = int(end - start)
                cooked: set[tuple[int, ...]] = set()
                for word in allowed_words:
                    tup = tuple(int(v) for v in word)
                    if len(tup) != expected_len:
                        raise ValueError(
                            f"hard_crib.per_word_allowed[{idx}] contains length {len(tup)}; expected {expected_len}"
                        )
                    cooked.add(tup)
                if not cooked:
                    raise ValueError(f"hard_crib.per_word_allowed[{idx}] cannot be empty")
                per_word_allowed[idx] = frozenset(cooked)

            for word_len, allowed_words in (cfg.global_allowed_by_len or {}).items():
                L = int(word_len)
                if L <= 0:
                    raise ValueError("hard_crib.global_allowed_by_len keys must be >= 1")
                cooked: set[tuple[int, ...]] = set()
                for word in allowed_words:
                    tup = tuple(int(v) for v in word)
                    if len(tup) != L:
                        raise ValueError(
                            f"hard_crib.global_allowed_by_len[{L}] contains length {len(tup)}; expected {L}"
                        )
                    cooked.add(tup)
                if not cooked:
                    raise ValueError(f"hard_crib.global_allowed_by_len[{L}] cannot be empty")
                global_allowed_by_len[L] = frozenset(cooked)

        return _CompiledHardCrib(
            fixed_chars=fixed_chars,
            per_word_allowed=per_word_allowed,
            global_allowed_by_len=global_allowed_by_len,
            word_spans=word_spans,
        )

    def _crib_filter_mask(self, plains_seq) -> tuple[list[bool], int, int, int] | None:
        compiled = self._hard_crib_compiled
        if compiled is None:
            return None

        plains = list(self._iter_plaintexts(plains_seq))
        n = int(len(plains))
        mask = [True] * n
        rej_fixed = 0
        rej_word = 0
        rej_global = 0

        for i, pt in enumerate(plains):
            pt_arr = to_numpy(pt).astype("int64", copy=False).reshape(-1)

            failed = False
            for pos, allowed in compiled.fixed_chars.items():
                if pos >= pt_arr.size or int(pt_arr[pos]) not in allowed:
                    failed = True
                    rej_fixed += 1
                    break
            if failed:
                mask[i] = False
                continue

            if compiled.per_word_allowed:
                for word_idx, allowed_words in compiled.per_word_allowed.items():
                    start, end = compiled.word_spans[word_idx]
                    word = tuple(int(v) for v in pt_arr[start:end].tolist())
                    if word not in allowed_words:
                        failed = True
                        rej_word += 1
                        break
            if failed:
                mask[i] = False
                continue

            if compiled.global_allowed_by_len:
                for start, end in compiled.word_spans:
                    L = int(end - start)
                    allowed_words = compiled.global_allowed_by_len.get(L)
                    if not allowed_words:
                        continue
                    word = tuple(int(v) for v in pt_arr[start:end].tolist())
                    if word not in allowed_words:
                        failed = True
                        rej_global += 1
                        break
            if failed:
                mask[i] = False

        pass_count = sum(1 for ok in mask if ok)
        reject_count = int(n - pass_count)
        t = self.telemetry
        t["crib_pass_total"] = int(t.get("crib_pass_total", 0)) + pass_count
        t["crib_reject_total"] = int(t.get("crib_reject_total", 0)) + reject_count
        t["crib_reject_fixed_char"] = int(t.get("crib_reject_fixed_char", 0)) + int(rej_fixed)
        t["crib_reject_word_index"] = int(t.get("crib_reject_word_index", 0)) + int(rej_word)
        t["crib_reject_global_len"] = int(t.get("crib_reject_global_len", 0)) + int(rej_global)
        if reject_count == n and n > 0:
            t["crib_all_rejected_batches"] = int(t.get("crib_all_rejected_batches", 0)) + 1

        return mask, rej_fixed, rej_word, rej_global

    def _score_batch_texts_core(self, plains_seq, wli):
        sc = self.scorer
        if hasattr(sc, "batch_score") and callable(sc.batch_score):
            self.telemetry["score_batch_calls"] = int(self.telemetry.get("score_batch_calls", 0)) + 1
            try:
                return self.xp.asarray(sc.batch_score(plains_seq, wli), dtype=self.xp.float64).reshape(-1)
            except Exception:
                self.telemetry["score_batch_fallback_scalar"] = int(
                    self.telemetry.get("score_batch_fallback_scalar", 0)
                ) + 1
                pass  # fall back to item-wise
        return self.xp.asarray(
            [
                float(sc.score_text(pt, wli) if hasattr(sc, "score_text") else sc.score(pt, wli))
                for pt in plains_seq
            ],
            dtype=self.xp.float64,
        )

    def _score_batch_texts(self, plains_seq, wli):
        """
        Score a batch of plaintexts. Prefers scorer.batch_score, falls back to per-item.
        Returns float64 [B].
        """
        plains = list(self._iter_plaintexts(plains_seq))
        self._validate_wli_alignment(plains, wli)

        filt = self._crib_filter_mask(plains)
        if filt is None:
            return self._score_batch_texts_core(plains, wli)

        mask, _, _, _ = filt
        if all(mask):
            return self._score_batch_texts_core(plains, wli)

        out = self.xp.full((len(plains),), float("-inf"), dtype=self.xp.float64)
        keep = [i for i, ok in enumerate(mask) if ok]
        if not keep:
            return out

        kept_plain = [plains[int(i)] for i in keep]
        kept_scores = self._score_batch_texts_core(kept_plain, wli)
        for j, idx in enumerate(keep):
            out[idx] = kept_scores[j]
        return out

    def _score_batch_texts_with_raw_core(self, plains_seq, wli, *, require_raw: bool = False):
        sc = self.scorer
        if require_raw:
            supports_raw = False
            if hasattr(sc, "supports_raw") and callable(sc.supports_raw):
                try:
                    supports_raw = bool(sc.supports_raw())
                except Exception:
                    supports_raw = False
            if not supports_raw:
                raise ValueError("Raw scoring requested but scorer does not support raw outputs.")
        if hasattr(sc, "batch_score_with_raw") and callable(sc.batch_score_with_raw):
            self.telemetry["score_batch_with_raw_calls"] = int(
                self.telemetry.get("score_batch_with_raw_calls", 0)
            ) + 1
            try:
                pct, raw = sc.batch_score_with_raw(plains_seq, wli)
                return (
                    self.xp.asarray(pct, dtype=self.xp.float64).reshape(-1),
                    self.xp.asarray(raw, dtype=self.xp.float64).reshape(-1),
                )
            except Exception:
                self.telemetry["score_batch_with_raw_fallback_scalar"] = int(
                    self.telemetry.get("score_batch_with_raw_fallback_scalar", 0)
                ) + 1
                pass

        scores_pct = []
        scores_raw = []
        for pt in plains_seq:
            if hasattr(sc, "score_with_raw") and callable(sc.score_with_raw):
                pct, raw = sc.score_with_raw(pt, wli)
            else:
                pct = float(sc.score_text(pt, wli) if hasattr(sc, "score_text") else sc.score(pt, wli))
                raw = pct
                if require_raw:
                    raise ValueError("Raw scoring requested but scorer returned pct fallback.")
            scores_pct.append(float(pct))
            scores_raw.append(float(raw))
        return (
            self.xp.asarray(scores_pct, dtype=self.xp.float64),
            self.xp.asarray(scores_raw, dtype=self.xp.float64),
        )

    def _score_batch_texts_with_raw(self, plains_seq, wli, *, require_raw: bool = False):
        """
        Score a batch of plaintexts and return (primary_scores, raw_scores).
        Raw scores fall back to primary if the scorer doesn't expose raw.
        """
        plains = list(self._iter_plaintexts(plains_seq))
        self._validate_wli_alignment(plains, wli)

        filt = self._crib_filter_mask(plains)
        if filt is None:
            return self._score_batch_texts_with_raw_core(plains, wli, require_raw=require_raw)

        mask, _, _, _ = filt
        if all(mask):
            return self._score_batch_texts_with_raw_core(plains, wli, require_raw=require_raw)

        out_pct = self.xp.full((len(plains),), float("-inf"), dtype=self.xp.float64)
        out_raw = self.xp.full((len(plains),), float("-inf"), dtype=self.xp.float64)
        keep = [i for i, ok in enumerate(mask) if ok]
        if not keep:
            return out_pct, out_raw

        kept_plain = [plains[int(i)] for i in keep]
        kept_pct, kept_raw = self._score_batch_texts_with_raw_core(kept_plain, wli, require_raw=require_raw)
        for j, idx in enumerate(keep):
            out_pct[idx] = kept_pct[j]
            out_raw[idx] = kept_raw[j]
        return out_pct, out_raw

    def _ensure_key_batch_2d(self, keys: Any):
        """Normalise keys to contiguous KEY_DTYPE with shape [B, K] using the active xp backend."""
        target_dtype = getattr(self, "key_dtype", KEY_DTYPE)
        k = self.xp.asarray(keys, dtype=target_dtype)
        if getattr(k, "ndim", 1) == 1:
            k = k[None, :]
        # contiguity across numpy/torch/cupy
        need_copy = False
        flags = getattr(k, "flags", None)
        if flags is not None and hasattr(flags, "c_contiguous"):
            need_copy = not bool(flags.c_contiguous)
        elif hasattr(k, "is_contiguous"):
            try:
                need_copy = not bool(k.is_contiguous())
            except Exception:
                need_copy = False
        if need_copy:
            if hasattr(k, "contiguous") and callable(getattr(k, "contiguous")):
                try:
                    k = k.contiguous()
                except Exception:
                    k = self.xp.asarray(k, dtype=target_dtype)
            else:
                k = self.xp.asarray(k, dtype=target_dtype)
        return k

    def evaluate_keys(self, keys: Any, *, batch_hint: bool = True) -> Any:
        """
        Evaluate candidate keys against this problem’s ciphertext.
        Returns xp.ndarray[float64] of shape [B].
        """
        if self.ciphertext is None:
            raise ValueError("DecryptionProblem has no ciphertext bound")

        k = self._ensure_key_batch_2d(keys)
        B, K = int(k.shape[0]), int(k.shape[1])

        if getattr(self, "keyops", None) is not None and getattr(self.keyops, "caps", None):
            expK = int(self.keyops.caps.length)
            if K != expK:
                raise ValueError(f"Key length mismatch: got {K}, expected {expK}")

        # Telemetry device/dtype initialisation (once)
        if getattr(self.telemetry, "device", "unknown") == "unknown" or getattr(self.telemetry, "dtype", "unknown") == "unknown":
            dev_kind = ensure_device(getattr(self.c_cfg, "device", Device.CPU))
            dtype = getattr(self.scorer, "dtype", None) or "float32"
            self.telemetry.device = to_canonical_device_str(dev_kind)
            self.telemetry.dtype = str(dtype)

        deg_cfg = self._degeneracy_cfg()

        # Decrypt and score with timing
        t_dec, t_sc = _Timer(), _Timer()
        if deg_cfg is not None:
            t_dec.start()
            plains_seq, scores, cand_count, sc_time = self._evaluate_keys_with_degeneracy(k, deg_cfg)
            self.telemetry.decrypt_time_s += t_dec.stop()
            self.telemetry.score_time_s += float(sc_time)
        else:
            t_dec.start()
            plains_seq = self._decrypt_batch(k)
            self.telemetry.decrypt_time_s += t_dec.stop()

            t_sc.start()
            scores = self._score_batch_texts(plains_seq, self.wli_data)
            self.telemetry.score_time_s += t_sc.stop()
            cand_count = int(B)

        # Counters
        if plains_seq and hasattr(plains_seq[0], "__len__"):
            N = int(len(plains_seq[0]))
        else:
            N = self.ciphertext_len
        self.telemetry.eval_batches += 1
        self.telemetry.eval_keys += int(B)
        self.telemetry.tokens_processed += int(cand_count) * N
        self.telemetry.evaluate_keys_calls += 1
        self.telemetry.candidates_evaluated += int(cand_count)

        return to_numpy(scores)

    def evaluate_keys_with_raw(self, keys: Any, *, batch_hint: bool = True, require_raw: bool = False):
        """
        Evaluate candidate keys and return (primary_scores, raw_scores).
        Raw scores fall back to primary if the scorer doesn't expose raw.
        """
        if self.ciphertext is None:
            raise ValueError("DecryptionProblem has no ciphertext bound")

        k = self._ensure_key_batch_2d(keys)
        B, K = int(k.shape[0]), int(k.shape[1])

        if getattr(self, "keyops", None) is not None and getattr(self.keyops, "caps", None):
            expK = int(self.keyops.caps.length)
            if K != expK:
                raise ValueError(f"Key length mismatch: got {K}, expected {expK}")

        # Telemetry device/dtype initialisation (once)
        if getattr(self.telemetry, "device", "unknown") == "unknown" or getattr(self.telemetry, "dtype", "unknown") == "unknown":
            dev_kind = ensure_device(getattr(self.c_cfg, "device", Device.CPU))
            dtype = getattr(self.scorer, "dtype", None) or "float32"
            self.telemetry.device = to_canonical_device_str(dev_kind)
            self.telemetry.dtype = str(dtype)

        deg_cfg = self._degeneracy_cfg()

        # Decrypt and score with timing
        t_dec, t_sc = _Timer(), _Timer()
        if deg_cfg is not None:
            obj = getattr(self.scorer, "objective", None)
            use_raw_primary = bool(require_raw)
            if obj is not None and getattr(obj, "family", None) is ObjectiveFamily.AVG:
                use_raw_primary = True
                require_raw = True
            t_dec.start()
            plains_seq, scores_pct, scores_raw, cand_count, sc_time = self._evaluate_keys_with_degeneracy_raw(
                k,
                deg_cfg,
                use_raw_primary=use_raw_primary,
                require_raw=require_raw,
            )
            self.telemetry.decrypt_time_s += t_dec.stop()
            self.telemetry.score_time_s += float(sc_time)
        else:
            t_dec.start()
            plains_seq = self._decrypt_batch(k)
            self.telemetry.decrypt_time_s += t_dec.stop()

            t_sc.start()
            scores_pct, scores_raw = self._score_batch_texts_with_raw(plains_seq, self.wli_data, require_raw=require_raw)
            self.telemetry.score_time_s += t_sc.stop()
            cand_count = int(B)

        # Counters
        if plains_seq and hasattr(plains_seq[0], "__len__"):
            N = int(len(plains_seq[0]))
        else:
            N = self.ciphertext_len
        self.telemetry.eval_batches += 1
        self.telemetry.eval_keys += int(B)
        self.telemetry.tokens_processed += int(cand_count) * N
        self.telemetry.evaluate_keys_calls += 1
        self.telemetry.candidates_evaluated += int(cand_count)

        return to_numpy(scores_pct), to_numpy(scores_raw)

    def _evaluate_keys_with_degeneracy_raw(
        self,
        keys: Any,
        cfg: dict,
        *,
        use_raw_primary: bool,
        require_raw: bool,
    ):
        """Degeneracy-aware evaluation that returns (pct_scores, raw_scores)."""
        resolver = cfg.get("resolver", "first")
        per_pos_limit = int(cfg.get("per_pos_limit", 1) or 0)
        resolver_limit = int(cfg.get("resolver_limit", 1) or 1)

        keys_np = to_numpy(keys)
        if keys_np.ndim == 1:
            keys_np = keys_np[None, :]
        core_keys, key_interrupts = self._split_key_batch(keys_np)

        if key_interrupts is None:
            ct_tr, keys_tr, info, L_full = self._prepare_candidate_inputs(core_keys)
            cands, lens, invalid = self.cipher.candidates_for(ct_tr, keys_tr, limit=per_pos_limit)
            B = int(keys_tr.shape[0])
        else:
            keys_tr = None
            cands = lens = invalid = None
            info = None
            L_full = int(self.ciphertext_len)
            B = int(core_keys.shape[0])

        scores_pct_out = self.xp.full((B,), float("-inf"), dtype=self.xp.float64)
        scores_raw_out = self.xp.full((B,), float("-inf"), dtype=self.xp.float64)
        plains_out = [None] * B
        total_scored = 0
        score_time = 0.0

        for b in range(B):
            if key_interrupts is None:
                if invalid is not None and bool(to_numpy(invalid[b]).any()):
                    continue
                cands_b = cands[b]
                lens_b = lens[b]
                info_b = info
                L_full_b = L_full
                key_core = core_keys[b]
            else:
                ct_tr, keys_tr_b, info_b, L_full_b = self._prepare_candidate_inputs(
                    core_keys[b:b + 1],
                    interrupt_idx=key_interrupts[b],
                )
                cands_b, lens_b, invalid_b = self.cipher.candidates_for(
                    ct_tr,
                    keys_tr_b,
                    limit=per_pos_limit,
                )
                if invalid_b is not None and bool(to_numpy(invalid_b[0]).any()):
                    continue
                key_core = core_keys[b]

            if resolver != "expand_beam":
                if key_interrupts is None:
                    pt = self._decrypt_batch(key_core)
                    pt_arr = to_numpy(pt[0] if isinstance(pt, list) else pt)
                else:
                    idx = self._normalize_interrupt_idx(key_interrupts[b])
                    pt = self.cipher.decrypt(
                        ciphertext=self.ciphertext,
                        key=key_core,
                        interrupt_idx=idx,
                        interrupt_sym=None,
                    )
                    pt_arr = to_numpy(pt)
                pt_arr = pt_arr.astype("uint8", copy=False).reshape(-1)
                plains_out[b] = pt_arr
                t_sc = _Timer()
                t_sc.start()
                pct_arr, raw_arr = self._score_batch_texts_with_raw([pt_arr], self.wli_data, require_raw=require_raw)
                score_time += t_sc.stop()
                scores_pct_out[b] = float(pct_arr[0])
                scores_raw_out[b] = float(raw_arr[0])
                total_scored += 1
                continue

            pt_best, pct_best, raw_best, scored, sc_time = self._resolve_candidates_for_key_with_raw(
                cands_b[0] if key_interrupts is not None else cands_b,
                lens_b[0] if key_interrupts is not None else lens_b,
                info_b,
                L_full=L_full_b,
                resolver_limit=resolver_limit,
                use_raw_primary=use_raw_primary,
                require_raw=require_raw,
            )
            if pt_best is not None:
                plains_out[b] = pt_best
                scores_pct_out[b] = float(pct_best)
                scores_raw_out[b] = float(raw_best)
                total_scored += int(scored)
                score_time += float(sc_time)

        return plains_out, scores_pct_out, scores_raw_out, total_scored, score_time

    def _degeneracy_cfg(self) -> Optional[dict]:
        """Return degeneracy config if enabled and supported by the cipher."""
        spec = getattr(self.c_cfg, "spec", None)
        if spec is None:
            return None
        deg = str(getattr(spec, "degeneracy", "forbid") or "forbid").strip().lower()
        if deg != "allow":
            return None
        if not callable(getattr(self.cipher, "candidates_for", None)):
            return None

        resolver = str(getattr(spec, "resolver", "first") or "first").strip().lower()
        per_pos_limit = int(getattr(spec, "per_pos_limit", 1) or 0)
        resolver_limit = int(getattr(spec, "resolver_limit", 8193) or 0)
        if resolver_limit <= 0:
            resolver_limit = 1

        A = getattr(self.cipher, "A", None)
        if A is None:
            A = getattr(self.cipher, "N", None)
        if per_pos_limit <= 0:
            per_pos_limit = int(A) if A is not None else 0
        if A is not None and per_pos_limit > int(A):
            per_pos_limit = int(A)

        return {
            "resolver": resolver,
            "per_pos_limit": per_pos_limit,
            "resolver_limit": resolver_limit,
        }

    def _evaluate_keys_with_degeneracy(self, keys: Any, cfg: dict):
        """Evaluate keys with degeneracy-aware candidate expansion."""
        resolver = cfg.get("resolver", "first")
        per_pos_limit = int(cfg.get("per_pos_limit", 1) or 0)
        resolver_limit = int(cfg.get("resolver_limit", 1) or 1)

        keys_np = to_numpy(keys)
        if keys_np.ndim == 1:
            keys_np = keys_np[None, :]
        core_keys, key_interrupts = self._split_key_batch(keys_np)

        if key_interrupts is None:
            ct_tr, keys_tr, info, L_full = self._prepare_candidate_inputs(core_keys)
            cands, lens, invalid = self.cipher.candidates_for(ct_tr, keys_tr, limit=per_pos_limit)
            B = int(keys_tr.shape[0])
        else:
            keys_tr = None
            cands = lens = invalid = None
            info = None
            L_full = int(self.ciphertext_len)
            B = int(core_keys.shape[0])

        scores_out = self.xp.full((B,), float("-inf"), dtype=self.xp.float64)
        plains_out = [None] * B
        total_scored = 0
        score_time = 0.0

        for b in range(B):
            if key_interrupts is None:
                if invalid is not None and bool(to_numpy(invalid[b]).any()):
                    continue
                cands_b = cands[b]
                lens_b = lens[b]
                info_b = info
                L_full_b = L_full
                key_core = core_keys[b]
            else:
                ct_tr, keys_tr_b, info_b, L_full_b = self._prepare_candidate_inputs(
                    core_keys[b:b + 1],
                    interrupt_idx=key_interrupts[b],
                )
                cands_b, lens_b, invalid_b = self.cipher.candidates_for(
                    ct_tr,
                    keys_tr_b,
                    limit=per_pos_limit,
                )
                if invalid_b is not None and bool(to_numpy(invalid_b[0]).any()):
                    continue
                key_core = core_keys[b]

            if resolver != "expand_beam":
                # "first" resolver: decrypt normally but reject invalid keys
                if key_interrupts is None:
                    pt = self._decrypt_batch(key_core)
                    pt_arr = to_numpy(pt[0] if isinstance(pt, list) else pt)
                else:
                    idx = self._normalize_interrupt_idx(key_interrupts[b])
                    pt = self.cipher.decrypt(
                        ciphertext=self.ciphertext,
                        key=key_core,
                        interrupt_idx=idx,
                        interrupt_sym=None,
                    )
                    pt_arr = to_numpy(pt)
                pt_arr = pt_arr.astype("uint8", copy=False).reshape(-1)
                plains_out[b] = pt_arr
                t_sc = _Timer()
                t_sc.start()
                sc = float(self._score_batch_texts([pt_arr], self.wli_data)[0])
                score_time += t_sc.stop()
                scores_out[b] = sc
                total_scored += 1
                continue

            pt_best, sc_best, scored, sc_time = self._resolve_candidates_for_key(
                cands_b[0] if key_interrupts is not None else cands_b,
                lens_b[0] if key_interrupts is not None else lens_b,
                info_b,
                L_full=L_full_b,
                resolver_limit=resolver_limit,
            )
            if pt_best is not None:
                plains_out[b] = pt_best
                scores_out[b] = sc_best
                total_scored += int(scored)
                score_time += float(sc_time)

        return plains_out, scores_out, total_scored, score_time

    def _prepare_candidate_inputs(self, keys_np: np.ndarray, *, interrupt_idx: Optional[Any] = None):
        """Prepare core/transposed ciphertext + keys for candidates_for()."""
        cipher = self.cipher
        ct_arr = to_numpy(self.ciphertext).reshape(-1)

        if hasattr(cipher, "_intr_mgr") and hasattr(cipher, "_trans_mgr"):
            if hasattr(cipher, "_as_u8"):
                try:
                    ct_idx = cipher._as_u8(ct_arr, "ciphertext")
                except TypeError:
                    ct_idx = cipher._as_u8(ct_arr)
            else:
                ct_idx = to_numpy(ct_arr).astype("uint8", copy=False)
            ct_full = ct_idx
            if hasattr(cipher, "_apply_full_text_perm"):
                ct_idx = cipher._apply_full_text_perm(ct_idx)
            if interrupt_idx is None:
                interrupt_idx = self._resolve_interrupt_idx()
            interrupt_idx = self._normalize_interrupt_idx(interrupt_idx)
            if interrupt_idx is not None and hasattr(cipher, "_as_intp"):
                try:
                    idx = cipher._as_intp(interrupt_idx, "interrupt_idx")
                except TypeError:
                    idx = cipher._as_intp(interrupt_idx)
            elif interrupt_idx is not None:
                idx = to_numpy(interrupt_idx).astype("intp", copy=False)
            else:
                idx = None

            if idx is not None and hasattr(cipher, "_validate_interrupt_idx"):
                cipher._validate_interrupt_idx(idx, int(ct_full.size))
                if hasattr(cipher, "_map_interrupt_idx_for_perm"):
                    idx = cipher._map_interrupt_idx_for_perm(idx, int(ct_full.size))

            if idx is not None:
                ct_core, info = cipher._intr_mgr.remove_from(ct_idx, possible_idx=idx)
            else:
                ct_core, info = cipher._intr_mgr.remove_from(ct_idx, possible_idx=None)

            ct_tr = cipher._trans_mgr.apply_text(ct_core)
            if hasattr(cipher, "_as_key_dtype"):
                try:
                    key_arr = cipher._as_key_dtype(keys_np, "key")
                except TypeError:
                    key_arr = cipher._as_key_dtype(keys_np)
            else:
                key_arr = to_numpy(keys_np).astype(self.key_dtype, copy=False)
            if getattr(cipher, "mod_keys", True):
                if hasattr(cipher, "_validate_key_range"):
                    cipher._validate_key_range(key_arr)
                A = getattr(cipher, "A", None)
                if A is not None:
                    key_arr = key_arr % int(A)
            if key_arr.ndim == 1:
                key_arr = key_arr[None, :]
            keys_tr = cipher._trans_mgr.apply_key(key_arr)
            return ct_tr, keys_tr, info, int(ct_full.size)

        # Fallback: assume candidates_for consumes full ciphertext/key space
        key_arr = to_numpy(keys_np).astype(self.key_dtype, copy=False)
        if key_arr.ndim == 1:
            key_arr = key_arr[None, :]
        ct_arr_u8 = to_numpy(ct_arr).astype("uint8", copy=False)
        return ct_arr_u8, key_arr, None, int(ct_arr_u8.size)

    @staticmethod
    def _enumerate_candidates(cands_row: np.ndarray, lens_row: np.ndarray, limit: int) -> np.ndarray:
        """Enumerate candidate plaintexts in core/transposed space with a hard cap."""
        lens_np = to_numpy(lens_row).reshape(-1)
        if limit <= 0:
            return to_numpy([]).astype("uint8").reshape(0, int(lens_np.size))

        lengths = [int(x) for x in lens_np]
        if not lengths:
            return to_numpy([]).astype("uint8").reshape(0, 0)
        if any(L <= 0 for L in lengths):
            return to_numpy([]).astype("uint8").reshape(0, len(lengths))

        total = 1
        for L in lengths:
            total *= L
            if total > limit:
                total = limit + 1
                break
        out_n = min(limit, total) if total != (limit + 1) else limit
        L = len(lengths)
        out = to_numpy([[0] * L for _ in range(out_n)]).astype("uint8", copy=False)

        idx = [0] * L
        for n in range(out_n):
            for i in range(L):
                out[n, i] = cands_row[i, idx[i]]
            # increment mixed-radix counter
            for pos in range(L - 1, -1, -1):
                idx[pos] += 1
                if idx[pos] < lengths[pos]:
                    break
                idx[pos] = 0
        return out

    def _reassemble_plaintexts(self, plains_tr: np.ndarray, info, L_full: int) -> list[np.ndarray]:
        """Undo text transposition and reinsert interruptors for candidate batches."""
        cipher = self.cipher
        if not hasattr(cipher, "_trans_mgr"):
            return [to_numpy(row).astype("uint8", copy=False).reshape(-1) for row in plains_tr]

        out = []
        for row in plains_tr:
            cand_core = cipher._trans_mgr.undo_text(to_numpy(row).astype("uint8", copy=False))
            if info is not None and hasattr(cipher, "_intr_mgr"):
                cand_full = cipher._intr_mgr.insert_into(cand_core, info)
            else:
                cand_full = cand_core
            if hasattr(cipher, "_undo_full_text_perm"):
                cand_full = cipher._undo_full_text_perm(cand_full)
            cand_full = to_numpy(cand_full).astype("uint8", copy=False).reshape(-1)
            if L_full and cand_full.size != int(L_full):
                raise ValueError(f"reassembled plaintext has length {cand_full.size}, expected {L_full}")
            out.append(cand_full)
        return out

    def _resolve_candidates_for_key(
        self,
        cands_row: np.ndarray,
        lens_row: np.ndarray,
        info,
        *,
        L_full: int,
        resolver_limit: int,
    ):
        """Return (best_plaintext, best_score, scored_count, score_time) for one key."""
        seqs_tr = self._enumerate_candidates(cands_row, lens_row, resolver_limit)
        if seqs_tr.size == 0:
            return None, float("-inf"), 0, 0.0
        plains_full = self._reassemble_plaintexts(seqs_tr, info, L_full)
        t_sc = _Timer()
        t_sc.start()
        scores = self._score_batch_texts(plains_full, self.wli_data)
        sc_time = t_sc.stop()
        scores_np = to_numpy(scores)
        if scores_np.size == 0:
            return None, float("-inf"), 0, sc_time
        best_idx = int(scores_np.argmax())
        best_plain = to_numpy(plains_full[best_idx]).astype("uint8", copy=False).reshape(-1)
        return best_plain, float(scores_np[best_idx]), int(len(plains_full)), sc_time

    def _resolve_candidates_for_key_with_raw(
        self,
        cands_row: np.ndarray,
        lens_row: np.ndarray,
        info,
        *,
        L_full: int,
        resolver_limit: int,
        use_raw_primary: bool,
        require_raw: bool,
    ):
        """Return (best_plaintext, best_pct, best_raw, scored_count, score_time)."""
        seqs_tr = self._enumerate_candidates(cands_row, lens_row, resolver_limit)
        if seqs_tr.size == 0:
            return None, float("-inf"), float("-inf"), 0, 0.0
        plains_full = self._reassemble_plaintexts(seqs_tr, info, L_full)
        t_sc = _Timer()
        t_sc.start()
        scores_pct, scores_raw = self._score_batch_texts_with_raw(
            plains_full,
            self.wli_data,
            require_raw=require_raw,
        )
        sc_time = t_sc.stop()
        pct_np = to_numpy(scores_pct)
        raw_np = to_numpy(scores_raw)
        if pct_np.size == 0:
            return None, float("-inf"), float("-inf"), 0, sc_time
        primary = raw_np if use_raw_primary else pct_np
        best_idx = int(primary.argmax())
        best_plain = to_numpy(plains_full[best_idx]).astype("uint8", copy=False).reshape(-1)
        return best_plain, float(pct_np[best_idx]), float(raw_np[best_idx]), int(len(plains_full)), sc_time

    def resolve_plaintext(self, key: Any) -> Optional[np.ndarray]:
        """Resolve a key to a plaintext, honoring degeneracy settings if enabled."""
        cfg = self._degeneracy_cfg()
        key_np = to_numpy(key).astype(self.key_dtype, copy=False).reshape(1, -1)
        key_core, key_interrupts = self._split_key_batch(key_np)
        interrupt_idx = self._resolve_interrupt_idx() if key_interrupts is None else key_interrupts[0]
        interrupt_idx = self._normalize_interrupt_idx(interrupt_idx)
        if cfg is None:
            pt = self.cipher.decrypt(
                ciphertext=self.ciphertext,
                key=key_core[0] if hasattr(key_core, "ndim") and key_core.ndim == 2 else key_core,
                interrupt_idx=interrupt_idx,
                interrupt_sym=None,
            )
            pt_arr = to_numpy(pt).astype("uint8", copy=False)
            if pt_arr.ndim >= 2:
                pt_arr = pt_arr[0]
            return pt_arr.reshape(-1)

        keys_np = to_numpy(key_core).astype(self.key_dtype, copy=False).reshape(1, -1)
        ct_tr, keys_tr, info, L_full = self._prepare_candidate_inputs(keys_np, interrupt_idx=interrupt_idx)
        cands, lens, invalid = self.cipher.candidates_for(ct_tr, keys_tr, limit=cfg["per_pos_limit"])
        if invalid is not None and bool(to_numpy(invalid[0]).any()):
            return None

        resolver = cfg.get("resolver", "first")
        if resolver != "expand_beam":
            pt = self.cipher.decrypt(
                ciphertext=self.ciphertext,
                key=key_core[0] if hasattr(key_core, "ndim") and key_core.ndim == 2 else key_core,
                interrupt_idx=interrupt_idx,
                interrupt_sym=None,
            )
            pt_arr = to_numpy(pt).astype("uint8", copy=False)
            if pt_arr.ndim >= 2:
                pt_arr = pt_arr[0]
            return pt_arr.reshape(-1)

        pt_best, _score, _count, _sc_time = self._resolve_candidates_for_key(
            cands[0],
            lens[0],
            info,
            L_full=L_full,
            resolver_limit=int(cfg.get("resolver_limit", 1) or 1),
        )
        return pt_best

    def _gather_keyops_hints(self) -> dict:
        """Collect generic hints for KeyOps constructors without branching on family."""
        hints = {}
        for name in ("alphabet_size", "A", "N", "mod", "modulus"):
            v = getattr(self.cipher, name, None)
            if v is None:
                v = getattr(self.c_cfg, name, None)
            if v is not None:
                try:
                    hints["A"] = int(v)
                    break
                except Exception:
                    pass

        extra = getattr(self.cipher, "keyops_hints", None)
        if isinstance(extra, dict):
            hints.update(extra)
        extra2 = getattr(self.c_cfg, "keyops_hints", None)
        if isinstance(extra2, dict):
            hints.update(extra2)

        pb = getattr(self.cipher, "prefers_batch", None)
        if isinstance(pb, bool):
            hints["prefers_batch"] = pb

        cfg = self._interruptor_cfg()
        if cfg is not None and cfg.mode == "pool":
            hints["interruptors_pool"] = list(cfg.pool or [])
            hints["interruptors_min"] = int(cfg.min_count or 0)
            if cfg.max_count is not None:
                hints["interruptors_max"] = int(cfg.max_count)
            hints["interruptors_sentinel"] = -1
            try:
                strategy = ensure_interruptor_search_strategy(cfg.search_strategy)
            except Exception:
                strategy = InterruptorSearchStrategy.AUTO
            hints["interruptors_search_strategy"] = strategy.value
            hints["interruptors_bruteforce_max"] = int(cfg.bruteforce_max or 0)
        else:
            pool = getattr(self.c_cfg, "interruptors_pool", None)
            if pool is not None:
                hints["interruptors_pool"] = list(pool)
            max_n = getattr(self.c_cfg, "interruptors_max", None)
            if max_n is not None:
                hints["interruptors_max"] = int(max_n)

        return hints
