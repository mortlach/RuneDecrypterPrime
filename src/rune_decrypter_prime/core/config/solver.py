# ============================================================
# rune_decrypter_prime/core/config.py
# Unified dataclasses for cipher/scorer/solver/run configs.
# ============================================================

from __future__ import annotations
from typing import Any, Dict

from rune_decrypter_prime.core.types import (
    SolverName,
    parse_optimizer_kind,
)


class SolverConfig:
    """
    Backward/forward compatible solver config.
    Canonical: SolverConfig(name=OptimizerKind.BEAM, params={...})
    Legacy:    SolverConfig(name="beam", params={...})
    """

    def __init__(
        self,
        name: SolverName | str = SolverName.BEAM,
        params: dict | None = None,
        *,
        seed: int | None = None,
        **legacy_kwargs,
    ):
        self.kind: SolverName = parse_optimizer_kind(name)
        self.params = dict(params) if params is not None else {}

        # Allow callers to pass `seed` either explicitly or via legacy kwargs
        legacy_seed = legacy_kwargs.pop("seed", None)
        if seed is None and legacy_seed is not None:
            seed = legacy_seed
        self.seed: int | None = None if seed is None else int(seed)

        for k, v in legacy_kwargs.items():
            self.params[k] = v

    # preserve old .name for callers; returns canonical string
    @property
    def name(self) -> str:
        return self.kind.value

    def __repr__(self) -> str:
        return f"SolverConfig(name={self.kind!s}, params={self.params!r})"

    def asdict(self) -> Dict[str, Any]:
        return {
            "name": self.kind.value,
            "params": dict(self.params),
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, d: dict | None):
        if d is None:
            return cls()
        d = dict(d)
        name = d.pop("name", SolverName.BEAM)
        seed = d.pop("seed", None)
        p = d.pop("params", None)
        if p is None:
            return cls(name=name, seed=seed, **d)
        params = dict(p)
        params.update(d)
        return cls(name=name, params=params, seed=seed)
