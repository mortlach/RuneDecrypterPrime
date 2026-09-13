from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class LmLoadStatus:
    kind: Literal["ecdf_load", "joint_table_load", "cache_hit", "missing_asset"]
    asset_type: str
    asset_id: str
    path: str
    status: str
    cached: bool = False


LmLoadReporter = Callable[[LmLoadStatus], None]


__all__ = ["LmLoadReporter", "LmLoadStatus"]
