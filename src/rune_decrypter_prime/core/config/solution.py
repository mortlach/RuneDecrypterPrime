# ============================================================
# rune_decrypter_prime/core/config.py
# Unified dataclasses for cipher/scorer/solver/run configs.
# ============================================================

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from rune_decrypter_prime.core.types import (
    Device,
    SolverName,
    ScorerImpl,
    Direction,
    ensure_device,
    ensure_direction,
    ensure_solver_name,
    ensure_scorer_impl,
)




@dataclass(slots=True)
class Solution:
    """Container for a solver’s best output.
    Required on construct: (key, plaintext, score).
    Engine populates the convenience + context fields before returning to API.
    """
    # Required
    key: Any
    plaintext: Any
    score: float

    # Optional context / flags
    has_wli: Optional[bool] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    # Convenience (safe views for tutorials/UIs)
    plaintext_str: str = ""                 # always a real str by the time API returns
    plaintext_idx: List[int] = field(default_factory=list)
    plaintext_rune: str = ""
    plaintext_rune_nospace: str = ""
    plaintext_latin: str = ""
    plaintext_latin_nospace: str = ""
    wli: Optional[Sequence[Sequence[int]]] = None
    ciphertext_idx: List[int] = field(default_factory=list)
    ciphertext_rune: str = ""
    ciphertext_rune_nospace: str = ""
    ciphertext_latin: str = ""
    ciphertext_latin_nospace: str = ""
    alphabet: str = "runic-29"
    alphabet_size: int = 29

    # -------- v1 standardised context (add-only, optional) --------
    device: Device = Device.CPU             # v1 surface
    cipher_name: str = ""
    solver_name: Optional[SolverName] = None
    scorer_impl: Optional[ScorerImpl] = None
    scorer_n_char: int = 0
    scorer_n_wli: int = 0
    direction: Direction = Direction.LTR
    pipeline: Dict[str, Any] = field(default_factory=lambda: {
        "text_encoding_direction": Direction.LTR,
        "input_permutation": {"kind": "none", "length": 0, "hash": ""},
    })

    # Optimisation sense
    maximize: bool = True

    # Progress summary
    step: int = 0
    evals: int = 0
    since_improve: int = 0
    tokens_processed: int = 0

    # Timings
    wall_time_s: float = 0.0
    decrypt_time_s: float = 0.0
    score_time_s: float = 0.0

    # Termination & extras. Public reports classify stop reasons through
    # rune_decrypter_prime.api.stop_reason_contract; keep the schema there.
    stop_reason: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Trigger enum normalisation for constructor arguments.
        self.device = self.device
        self.direction = self.direction
        if self.solver_name:
            self.solver_name = self.solver_name
        if self.scorer_impl:
            self.scorer_impl = self.scorer_impl

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "device" and value is not None:
            value = ensure_device(value)
        elif name == "direction" and value is not None:
            value = ensure_direction(value)
        elif name == "solver_name":
            if not value:
                value = None
            else:
                value = ensure_solver_name(value)
        elif name == "scorer_impl":
            if not value:
                value = None
            else:
                value = ensure_scorer_impl(value)
        object.__setattr__(self, name, value)
