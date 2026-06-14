from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np

from rune_decrypter_prime.core.types import Device, Direction, SolverName, ensure_device, ensure_direction, ensure_solver_name


@dataclass
class Solution:
    key: Union[Sequence[int], np.ndarray, None] = None
    plaintext: Union[str, Sequence[int], np.ndarray, None] = None
    score: float = float("-inf")
    meta: Dict[str, Any] = field(default_factory=dict)

    # Canonical config-ish metadata
    device: Device = Device.CPU
    direction: Direction = Direction.FWD
    solver_name: Optional[SolverName] = None

    # Common decoded forms
    plaintext_idx: List[int] = field(default_factory=list)
    plaintext_str: str = ""

    # Progress summary
    step: int = 0
    evals: int = 0
    since_improve: int = 0
    tokens_processed: int = 0

    # Timings
    wall_time_s: float = 0.0
    decrypt_time_s: float = 0.0
    score_time_s: float = 0.0

    # Termination & extras.  Public reports classify these through
    # rune_decrypter_prime.api.stop_reason_contract rather than relying on this
    # comment as the source of truth.
    stop_reason: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Trigger enum normalisation for constructor arguments.
        self.device = ensure_device(self.device)
        self.direction = ensure_direction(self.direction)
        if self.solver_name:
            self.solver_name = ensure_solver_name(self.solver_name)

        # Normalise key to plain list if ndarray-like.
        if isinstance(self.key, np.ndarray):
            self.key = self.key.reshape(-1).astype(int).tolist()
        elif self.key is not None:
            self.key = [int(x) for x in self.key]

        # Normalise plaintext convenience forms.
        if isinstance(self.plaintext, str):
            self.plaintext_str = self.plaintext
        elif isinstance(self.plaintext, np.ndarray):
            flat = self.plaintext.reshape(-1).astype(int).tolist()
            self.plaintext_idx = flat
            if not self.plaintext_str:
                self.plaintext_str = "".join(map(str, flat))
        elif self.plaintext is not None:
            try:
                flat = [int(x) for x in self.plaintext]
                self.plaintext_idx = flat
                if not self.plaintext_str:
                    self.plaintext_str = "".join(map(str, flat))
            except Exception:
                # Keep arbitrary plaintext payloads as repr text only.
                if not self.plaintext_str:
                    self.plaintext_str = str(self.plaintext)

        if self.meta is None:
            self.meta = {}
        if self.extras is None:
            self.extras = {}
