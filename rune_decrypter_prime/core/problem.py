# ============================================================
# rune_decrypter_prime/core/problem.py
# Canonical binding of cipher, scorer, ciphertext, and telemetry.
# ============================================================

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Sequence
import numpy as np

from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.core.telemetry import Telemetry, _Timer
from rune_decrypter_prime.core.transpositions import _apply_transposition_batch

ArrayU8 = np.ndarray

@dataclass(slots=True)
class DecryptionProblem:
    """
    Canonical problem definition consumed by optimizers.
    Holds cipher, scorer, configs, ciphertext/WLI, and telemetry.
    """
    cipher: object
    scorer: object
    c_cfg: CipherConfig
    telemetry: Telemetry = field(default_factory=lambda: Telemetry(device="unknown", dtype="unknown"))
    enable_telemetry: bool = True
    ciphertext: Optional[ArrayU8] = None
    wli_data: Optional[ArrayU8] = None
    key_length: Optional[int] = None

    def __post_init__(self):
        if isinstance(self.c_cfg, CipherConfig):
            self.ciphertext = np.asarray(self.c_cfg.ciphertext, dtype=np.uint8)
            self.wli_data = None if self.c_cfg.wli_data is None else np.asarray(self.c_cfg.wli_data, dtype=np.int32)
            self.key_length = self.c_cfg.key_length
        if self.enable_telemetry and self.telemetry is None:
            self.telemetry = Telemetry(device="unknown", dtype="unknown")

    def evaluate_keys(self, keys: ArrayU8, *, batch_hint: bool = True) -> np.ndarray:
        """
        Score one or more candidate keys against the problem’s ciphertext.
        Updates telemetry with timings, counts, and device/dtype info.
        """
        if self.ciphertext is None:
            raise ValueError("DecryptionProblem has no ciphertext bound")

        k = np.asarray(keys, dtype=np.uint8)
        if k.ndim == 1:
            k = k[None, :]
        B = int(k.shape[0])

        if self.telemetry.device == "unknown" or self.telemetry.dtype == "unknown":
            dev = getattr(self.c_cfg, "device", None) or getattr(self.cipher, "device", None) or "cpu"
            dtype = getattr(self.scorer, "dtype", None) or "float32"
            self.telemetry.device = str(dev); self.telemetry.dtype = str(dtype)

        t_dec, t_sc = _Timer(), _Timer()

        # decrypt
        t_dec.start()
        if getattr(self.c_cfg, "_transpose", None):
            plains = _apply_transposition_batch(self.c_cfg, k)
        else:
            plains = self.cipher.decrypt(
                ciphertext=self.ciphertext,
                key=k,
                interrupt_idx=getattr(self.c_cfg, "interruptors_exact", None),
                interrupt_sym=None,
            )
        self.telemetry.decrypt_time += t_dec.stop()

        # score
        t_sc.start()
        N = int(plains.shape[1]) if getattr(plains, "ndim", 1) >= 2 else int(len(plains))
        if hasattr(self.scorer, "batch_score") and callable(self.scorer.batch_score):
            try:
                pts_seq = [plains[i] for i in range(plains.shape[0])]
                scores = self.scorer.batch_score(pts_seq, self.wli_data)
                scores = np.asarray(scores, dtype=np.float32).reshape(-1)
            except Exception:
                scores = np.array([float(self.scorer.score(plains[i], self.wli_data)) for i in range(plains.shape[0])],
                                  dtype=np.float32)
        else:
            scores = np.array([float(self.scorer.score(plains[i], self.wli_data)) for i in range(plains.shape[0])],
                              dtype=np.float32)

        self.telemetry.tokens_processed += B * N
        self.telemetry.score_time += t_sc.stop()
        self.telemetry.evaluate_keys_calls += 1
        self.telemetry.candidates_evaluated += B

        return scores

# TODO: unify evaluate_keys paths (batch vs per-item) for readability.
