# ============================================================
# rune_decrypter_prime/core/config/cipher.py
# ============================================================
from __future__ import annotations
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Literal

from rune_decrypter_prime.core.types import (
    Device,
    Direction,
    ensure_device,
    ensure_direction,
)

# ---------------- CipherConfig ------------------------------------------------
@dataclass
class CipherConfig:
    """Cipher-specific configuration (ciphertext, WLI, keys, device, etc.)."""
    ciphertext: Sequence[int]
    wli_data: Sequence[Sequence[int]]
    key_length: Optional[int]
    plaintext_english26: Optional[str] = None
    plaintext: Optional[Sequence[int]] = None
    initial_text_permutation_indices: Optional[Sequence[int]] = None
    device: Optional[Device] = Device.CPU
    encoding_dir: Optional[Direction] = Direction.LTR
    interruptors: Optional[List[int]] = None
    initial_keys: Optional[List[Sequence[int]]] = None
    test_key: Optional[Sequence[int]] = None
    interruptors_exact: Optional[List[int]] = None
    interruptors_pool: Optional[List[int]] = None
    interruptors_max: Optional[int] = None
    transposition_search_modes: Optional[List[str]] = None
    # meh
    name: str = "vigenere"
    def __post_init__(self) -> None:
        if self.device is not None:
            self.device = ensure_device(self.device)
        if self.encoding_dir is not None:
            self.encoding_dir = ensure_direction(self.encoding_dir)

        if self.wli_data is not None:
            try:
                import numpy as _np  # local import to avoid core-level import debt
                arr = self.wli_data
                # Coerce to list-of-tuples
                if isinstance(arr, _np.ndarray):
                    if arr.ndim == 1:
                        # Tests sometimes pass 1D starts; map to (start, start)
                        arr = _np.stack([arr, arr], axis=1)
                    if arr.shape[1] != 2:
                        raise ValueError("wli_data ndarray must have shape (N,2)")
                    pairs = [(int(a), int(b)) for a, b in arr.tolist()]
                else:
                    pairs = []
                    for pair in arr:
                        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                            raise ValueError("wli_data items must be (start, end) pairs per docs")
                        a, b = int(pair[0]), int(pair[1])
                        if a < 0 or b < 0 or a > b:
                            raise ValueError("wli_data pairs must be non-negative with start <= end")
                        pairs.append((a, b))
                self.wli_data = pairs
            except Exception as exc:
                raise ValueError("wli_data must be a sequence of two-integer tuples as documented") from exc

    def asdict(self) -> Dict[str, Any]:
        out = asdict(self)
        if isinstance(self.device, Device):
            out["device"] = self.device.value
        if isinstance(self.encoding_dir, Direction):
            out["encoding_dir"] = self.encoding_dir.value
        return out
