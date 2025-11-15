# ============================================================
# rune_decrypter_prime/core/runtime.py
# Canonical binding of cipher, scorer, ciphertext, and telemetry.
# ============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple, Any

from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.telemetry.bag import TelemetryBag
from rune_decrypter_prime.core.telemetry import _Timer
from rune_decrypter_prime.core.types import Device, ensure_device, KEY_DTYPE
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
class DecryptionProblem:
    """
    Canonical problem definition consumed by solver.
    Holds cipher, scorer, configs, ciphertext/WLI, and telemetry.
    """
    cipher: object
    scorer: object
    c_cfg: CipherConfig

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
        t.setdefault("lm_load_time_s", 0)

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
        self.wli_data = None if self.c_cfg.wli_data is None else list(map(tuple, self.c_cfg.wli_data))
        self.key_length = self.c_cfg.key_length

        self.ciphertext_len = (
            int(self.ciphertext.shape[-1]) if hasattr(self.ciphertext, "shape")
            else int(len(self.ciphertext or []))
        )

        # Construct KeyOps (and resolve fixed K)
        self.keyops = self._build_keyops_for_problem()
        self.key_dtype = getattr(self.keyops, "dtype", KEY_DTYPE)

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

        # --- construct ---
        hints = self._gather_keyops_hints()
        try:
            keyops = create_keyops(family, K=K, **hints)
        except TypeError:
            logger.info("problem: %s", "!!warning old keyops params!!")
            keyops = create_keyops(family, length=K, **hints)

        caps_len = int(getattr(getattr(keyops, "caps", None), "length", K))
        if caps_len != int(K):
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
        plains = self.cipher.decrypt(
            ciphertext=self.ciphertext,
            key=k_uint8,
            interrupt_idx=getattr(self.c_cfg, "interruptors_exact", None),
            interrupt_sym=None,
        )
        if hasattr(plains, "ndim") and plains.ndim >= 2:
            return [plains[i] for i in range(plains.shape[0])]
        return list(plains)

    def _score_batch_texts(self, plains_seq, wli):
        """
        Score a batch of plaintexts. Prefers scorer.batch_score, falls back to per-item.
        Returns float64 [B].
        """
        if wli is not None:
            if not (isinstance(wli, (list, tuple)) and all(
                isinstance(p, (list, tuple)) and len(p) == 2 and isinstance(p[0], int) and isinstance(p[1], int)
                for p in wli
            )):
                raise TypeError("WLI must be a list of (int,int) pairs or empty list")

        sc = self.scorer
        if hasattr(sc, "batch_score") and callable(sc.batch_score):
            try:
                return self.xp.asarray(sc.batch_score(plains_seq, wli), dtype=self.xp.float64).reshape(-1)
            except Exception:
                pass  # fall back to item-wise
        return self.xp.asarray(
            [
                float(sc.score_text(pt, wli) if hasattr(sc, "score_text") else sc.score(pt, wli))
                for pt in plains_seq
            ],
            dtype=self.xp.float64,
        )

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

        # Decrypt and score with timing
        t_dec, t_sc = _Timer(), _Timer()
        t_dec.start()
        plains_seq = self._decrypt_batch(k)
        self.telemetry.decrypt_time_s += t_dec.stop()

        t_sc.start()
        scores = self._score_batch_texts(plains_seq, self.wli_data)
        self.telemetry.score_time_s += t_sc.stop()

        # Counters
        if plains_seq and hasattr(plains_seq[0], "__len__"):
            N = int(len(plains_seq[0]))
        else:
            N = self.ciphertext_len
        self.telemetry.tokens_processed += B * N
        self.telemetry.evaluate_keys_calls += 1
        self.telemetry.candidates_evaluated += B

        return to_numpy(scores)

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

        return hints
