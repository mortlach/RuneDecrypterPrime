# ============================================================
# rune_decrypter_prime/core/telemetry.py
# Minimal, structured telemetry container for problem/optimisers.
# ============================================================
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Callable
import time

ProgressCallback = Callable[[Dict[str, Any]], None]


@dataclass(slots=True)
class Telemetry:
    """
    Lightweight telemetry container; typically attached to
    `Solution.meta['telemetry']`. Optimisers may store counters
    under the `solver` dict keyed by optimiser name.
    """
    device: str
    dtype: str
    batch_size: Optional[int] = None

    # Generic counters
    evaluate_keys_calls: int = 0
    candidates_evaluated: int = 0
    tokens_processed: int = 0

    # Timings (seconds)
    decrypt_time_s: float = 0.0
    score_time_s: float = 0.0
    wall_time_s: float = 0.0

    # Free-form optimiser bucket
    solver: Dict[str, Any] = field(default_factory=dict)

    # Optional event sink (e.g., progress callbacks)
    progress_callback: Optional[ProgressCallback] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a shallow dict representation (for JSONL logging, etc.)."""
        return asdict(self)


class _Timer:
    """Tiny helper for elapsed time measurements (perf counters)."""
    def __init__(self):
        self.t0: float = 0.0

    def start(self) -> None:
        self.t0 = time.perf_counter()

    def stop(self) -> float:
        return time.perf_counter() - self.t0
