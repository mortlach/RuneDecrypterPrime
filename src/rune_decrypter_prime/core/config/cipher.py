# ============================================================
# rune_decrypter_prime/core/config/cipher.py
# ============================================================
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Literal

from rune_decrypter_prime.core.config.interruptor import InterruptorConfig
from rune_decrypter_prime.core.types import (
    Device,
    Direction,
    ensure_device,
    ensure_direction,
    ensure_keyops_family,
    KeyOpsFamily,
)

# ---------------- CipherConfig ------------------------------------------------
@dataclass
class CipherConfig:
    """Cipher-specific configuration (ciphertext, WLI, keys, device, etc.)."""
    ciphertext: Sequence[int]
    wli_data: Sequence[Sequence[int]]
    key_length: Optional[int]
    keyops_family: Optional[KeyOpsFamily | str] = None
    keyops_hints: Optional[Dict[str, Any]] = None
    # Optional cipher-family specification object for typed plugin contracts.
    # This is not a general config escape hatch: runtime code may use it only
    # when a cipher plugin defines and documents a concrete spec object.
    spec: Optional[Any] = None
    alphabet_size: Optional[int] = None
    period: Optional[int] = None
    columns: Optional[int] = None
    order: Optional[str] = None
    plaintext_english26: Optional[str] = None
    plaintext: Optional[Sequence[int]] = None
    initial_text_permutation_indices: Optional[Sequence[int]] = None
    device: Optional[Device] = Device.CPU
    encoding_dir: Optional[Direction] = Direction.LTR
    interruptors: Optional[List[int]] = None
    interruptors_cfg: Optional[InterruptorConfig | Dict[str, Any]] = None
    initial_keys: Optional[List[Sequence[int]]] = None
    test_key: Optional[Sequence[int]] = None
    interruptors_exact: Optional[List[int]] = None
    interruptors_pool: Optional[List[int]] = None
    interruptors_max: Optional[int] = None
    transposition_search_modes: Optional[List[str]] = None
    name: str = "vigenere"
    def __post_init__(self) -> None:
        if self.device is not None:
            self.device = ensure_device(self.device)
        if self.encoding_dir is not None:
            self.encoding_dir = ensure_direction(self.encoding_dir)
        if self.keyops_family is not None:
            self.keyops_family = ensure_keyops_family(self.keyops_family)

        if self.wli_data is not None:
            try:
                import numpy as _np  # local import to avoid core-level import debt
                arr = self.wli_data
                # Allow empty list/array to mean "no WLI"
                if isinstance(arr, _np.ndarray):
                    if arr.size == 0:
                        self.wli_data = []
                        arr = None
                    else:
                        if arr.ndim != 2 or arr.shape[1] != 2:
                            raise ValueError("wli_data ndarray must have shape (N,2)")
                        pairs = [[int(a), int(b)] for a, b in arr.tolist()]
                        self._validate_wli_pairs(pairs)
                        self.wli_data = pairs
                        arr = None
                if arr is not None:
                    pairs = list(arr)
                    if len(pairs) == 0:
                        self.wli_data = []
                    else:
                        out: list[list[int]] = []
                        for i, pair in enumerate(pairs):
                            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                                raise ValueError("wli_data items must be (pos_in_word, word_len) pairs")
                            out.append([int(pair[0]), int(pair[1])])
                        self._validate_wli_pairs(out)
                        self.wli_data = out
            except Exception as exc:
                raise ValueError("wli_data must be a sequence of two-integer tuples as documented") from exc

        self._normalize_interruptors_cfg()

    def _validate_wli_pairs(self, pairs: list[list[int]]) -> None:
        # Empty list means "no WLI"; caller must handle WLI requirement.
        if not pairs:
            return
        ct_len = len(self.ciphertext) if self.ciphertext is not None else None
        if ct_len is not None and len(pairs) != int(ct_len):
            raise ValueError("wli_data length must match ciphertext length")
        expected_pos = 0
        current_len = None
        for i, (pos, ln) in enumerate(pairs):
            if pos < 0 or ln <= 0:
                raise ValueError("wli_data entries must be non-negative; word_len must be > 0")
            if pos >= ln:
                raise ValueError("wli_data pos_in_word must be < word_len")
            if pos > 63 or ln > 63:
                raise ValueError("wli_data entries must be <= 63 to match LMPrime WLI encoding")
            if expected_pos == 0:
                current_len = ln
            if ln != current_len:
                raise ValueError("wli_data word_len must remain constant within a word")
            if pos != expected_pos:
                raise ValueError("wli_data pos_in_word sequence must be contiguous within each word")
            expected_pos += 1
            if expected_pos == current_len:
                expected_pos = 0
                current_len = None
        if expected_pos != 0:
            raise ValueError("wli_data word_len exceeds available positions")

    def _normalize_interruptors_cfg(self) -> None:
        cfg_raw = getattr(self, "interruptors_cfg", None)
        has_legacy = any(
            x is not None for x in (
                self.interruptors_exact,
                self.interruptors,
                self.interruptors_pool,
                self.interruptors_max,
            )
        )

        if cfg_raw is not None:
            if has_legacy:
                raise ValueError("interruptors_cfg cannot be combined with legacy interruptor fields")
            if isinstance(cfg_raw, dict):
                cfg = InterruptorConfig(**cfg_raw)
            elif isinstance(cfg_raw, InterruptorConfig):
                cfg = cfg_raw
            else:
                raise TypeError("interruptors_cfg must be InterruptorConfig or dict")
            self.interruptors_cfg = cfg
        else:
            cfg = None
            if self.interruptors_exact is not None:
                cfg = InterruptorConfig(mode="exact", exact=self.interruptors_exact)
            elif self.interruptors is not None:
                cfg = InterruptorConfig(mode="exact", exact=self.interruptors)
            elif self.interruptors_pool is not None or self.interruptors_max is not None:
                pool = list(self.interruptors_pool or [])
                if not pool:
                    raise ValueError("interruptors_pool is required when interruptors_max is set")
                if self.interruptors_max is None:
                    min_count = 0
                    max_count = len(pool)
                else:
                    min_count = int(self.interruptors_max)
                    max_count = int(self.interruptors_max)
                cfg = InterruptorConfig(
                    mode="pool",
                    pool=pool,
                    min_count=min_count,
                    max_count=max_count,
                )
            self.interruptors_cfg = cfg
