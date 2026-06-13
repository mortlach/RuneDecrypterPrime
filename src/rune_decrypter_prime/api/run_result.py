from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rune_decrypter_prime.api.solver_report import SolverReport


@dataclass(frozen=True, slots=True)
class RunResult:
    solution: Any
    solver_report: SolverReport

    def __post_init__(self) -> None:
        if not isinstance(self.solver_report, SolverReport):
            raise TypeError("solver_report must be a SolverReport")


__all__ = ["RunResult"]
