# ============================================================
# rune_decrypter_prime/core/problem/spec.py
# Declarative problem specification (no side effects).
# ============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from rune_decrypter_prime.core.types import Direction, ensure_direction

@dataclass(slots=True)
class ProblemSpec:
    """
    Declarative description of a decryption run.
    This is intentionally *thin*: it carries only what's needed to
    materialise a runtime ProblemInstance without any global state.
    """
    # Ciphertext / pipeline orientation
    text: str
    text_encoding_direction: Direction = Direction.LTR

    # Config objects from the API layer (already normalised)
    cipher_cfg: Any = None           # e.g., CipherConfig
    scorer_params: Any = None        # score/runtime params (impl, dtype, etc.)

    # Optional fixed input permutation (indices over text), else identity.
    input_permutation: Optional[Sequence[int]] = None

    def __post_init__(self):
        # Enforce Enums in core
        self.text_encoding_direction = ensure_direction(self.text_encoding_direction)
