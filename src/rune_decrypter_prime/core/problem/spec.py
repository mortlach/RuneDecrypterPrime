# ============================================================
# rune_decrypter_prime/core/problem/spec.py
# Declarative problem specification (no side effects).
# ============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence

from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.cipher import expected_concrete_key_length
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rdp.core.types import Direction, ensure_direction


@dataclass(slots=True)
class ProblemSpec:
    """
    Declarative description of a decryption run.

    Core receives canonical config objects only. Dicts and config-like
    objects must be normalised before this boundary.
    """
    # Ciphertext / pipeline orientation
    text: str

    # Config objects from the API layer (already normalised)
    cipher_cfg: CipherConfig
    scorer_params: ScoringConfig

    text_encoding_direction: Direction = Direction.LTR

    # Optional fixed input permutation (indices over text), else identity.
    input_permutation: Optional[Sequence[int]] = None

    def __post_init__(self) -> None:
        # Enforce Enums and canonical config objects in core.
        self.text_encoding_direction = ensure_direction(self.text_encoding_direction)
        if not isinstance(self.cipher_cfg, CipherConfig):
            raise TypeError(f"cipher_cfg must be CipherConfig, got {type(self.cipher_cfg).__name__}")
        if not isinstance(self.scorer_params, ScoringConfig):
            raise TypeError(f"scorer_params must be ScoringConfig, got {type(self.scorer_params).__name__}")
        if self.cipher_cfg.spec is not None or self.cipher_cfg.key_space is not None:
            if self.cipher_cfg.spec is None or self.cipher_cfg.key_space is None:
                raise ValueError("typed cipher and key-space ownership must be recorded together")
            expected = expected_concrete_key_length(
                self.cipher_cfg.spec,
                self.cipher_cfg.key_space,
            )
            if self.cipher_cfg.key_length != expected:
                raise ValueError("materialized key length does not match the typed binding")
