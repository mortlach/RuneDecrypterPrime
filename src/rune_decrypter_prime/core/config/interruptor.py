# ============================================================
# rune_decrypter_prime/core/config/interruptor.py
# Interruptor configuration (positions only; symbols fixed from text).
# ============================================================
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional

from rune_decrypter_prime.core.types import InterruptorSearchStrategy, ensure_interruptor_search_strategy


_INT16_MIN = -(2 ** 15)
_INT16_MAX = (2 ** 15) - 1


def _coerce_indices(values: Iterable[Any], field: str) -> List[int]:
    if values is None:
        return []
    out: list[int] = []
    for i, raw in enumerate(values):
        if isinstance(raw, bool):
            raise TypeError(f"{field} indices cannot be bool (index {i})")
        try:
            val = int(raw)
        except Exception as exc:
            raise TypeError(f"{field} indices must be integers (index {i})") from exc
        if val < 0:
            raise ValueError(f"{field} indices must be >= 0 (index {i})")
        if val < _INT16_MIN or val > _INT16_MAX:
            raise ValueError(f"{field} indices must fit int16 range (index {i})")
        out.append(val)
    if len(set(out)) != len(out):
        raise ValueError(f"{field} indices must be unique")
    return sorted(out)


@dataclass(slots=True)
class InterruptorConfig:
    """
    Canonical interruptor configuration.

    Positions are absolute indices in the plaintext/ciphertext by default.
    Interruptor symbols are fixed from the text; only positions are configurable.
    """
    # primary mode
    mode: str = "disabled"  # "disabled" | "exact" | "pool"

    # exact positions (absolute indices)
    exact: Optional[List[int]] = None

    # pool search
    pool: Optional[List[int]] = None
    min_count: int = 0
    max_count: Optional[int] = None

    # index space (future extension)
    index_space: str = "absolute"  # "absolute" only for now

    # search strategy
    search_strategy: str = InterruptorSearchStrategy.AUTO.value  # "auto" | "bruteforce" | "keyops"
    bruteforce_max: int = 5000

    # reserved for future expansion (explicitly validated)
    score_mode: str = "full"  # "full" only for now
    value_mode: str = "fixed"  # "fixed" only for now

    def __post_init__(self) -> None:
        self.mode = str(self.mode or "disabled").strip().lower()
        if self.mode not in {"disabled", "exact", "pool"}:
            raise ValueError("interruptor mode must be 'disabled', 'exact', or 'pool'")

        self.index_space = str(self.index_space or "absolute").strip().lower()
        if self.index_space != "absolute":
            raise NotImplementedError("interruptor index_space currently supports only 'absolute'")

        self.search_strategy = ensure_interruptor_search_strategy(self.search_strategy).value

        self.bruteforce_max = int(self.bruteforce_max)
        if self.bruteforce_max < 0:
            raise ValueError("interruptor bruteforce_max must be >= 0")

        self.score_mode = str(self.score_mode or "full").strip().lower()
        if self.score_mode != "full":
            raise NotImplementedError("interruptor score_mode currently supports only 'full'")

        self.value_mode = str(self.value_mode or "fixed").strip().lower()
        if self.value_mode != "fixed":
            raise NotImplementedError("interruptor value_mode currently supports only 'fixed'")

        if self.exact is not None:
            self.exact = _coerce_indices(self.exact, "exact")
        if self.pool is not None:
            self.pool = _coerce_indices(self.pool, "pool")

        if self.mode == "disabled":
            if self.exact or self.pool:
                raise ValueError("interruptor mode='disabled' cannot define exact/pool indices")
            return

        if self.mode == "exact":
            if self.exact is None or len(self.exact) == 0:
                raise ValueError("interruptor mode='exact' requires a non-empty exact list")
            if self.pool is not None:
                raise ValueError("interruptor mode='exact' cannot define a pool")
            return

        # pool mode
        if self.pool is None or len(self.pool) == 0:
            raise ValueError("interruptor mode='pool' requires a non-empty pool")

        if self.max_count is None:
            self.max_count = int(len(self.pool))
        else:
            self.max_count = int(self.max_count)
        self.min_count = int(self.min_count or 0)

        if self.min_count < 0:
            raise ValueError("interruptor min_count must be >= 0")
        if self.max_count <= 0:
            raise ValueError("interruptor max_count must be > 0 when mode='pool'")
        if self.min_count > self.max_count:
            raise ValueError("interruptor min_count cannot exceed max_count")
        if self.max_count > len(self.pool):
            raise ValueError("interruptor max_count cannot exceed pool size")

    def asdict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["search_strategy"] = self.search_strategy
        return out


__all__ = ["InterruptorConfig"]
