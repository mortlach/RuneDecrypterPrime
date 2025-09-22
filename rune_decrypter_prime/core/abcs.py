# ============================================================
# rune_decrypter_prime/core/abcs.py
# Abstract base contracts for cipher, scorer, and optimizer.
# ============================================================

from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np
from typing import Any

ArrayU8 = np.ndarray

class BaseCipher(ABC):
    """
    Abstract cipher contract.
    Optimizers interact with ciphers only through this interface.
    """

    def decrypt(self, **kwargs):  # type: ignore[no-untyped-def]
        """Pipeline mixins must provide this."""
        raise NotImplementedError("CipherPipelineMixin should provide decrypt()")

    @abstractmethod
    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        """Cipher must implement batch decryption core."""
        ...

class BaseScorer(ABC):
    """Abstract scoring contract."""

    @abstractmethod
    def score(self, plaintext: Any, wli: Any | None = None) -> float: ...

class BaseOptimizer(ABC):
    """Abstract optimizer contract."""

    @abstractmethod
    def search(self, problem: "DecryptionProblem") -> "Solution": ...

# TODO: Consider adding explicit Protocols for typing instead of bare ABCs.
