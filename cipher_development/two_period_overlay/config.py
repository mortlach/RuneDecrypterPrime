from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

PERIOD_A = 13
PERIOD_B = 17
TEXT_LENGTH = 308
ALPHABET_SIZE = 29
CRIB_WORD = "uncomfortable"
CRIB_START = 188
CRIB_RUNES = (1, 9, 5, 3, 19, 0, 3, 4, 16, 24, 17, 20, 18)
MASTER_SEED = 101
DECISION_SCORE = "wli_decision_score"
ARCHIVE_CAPACITY = 64
RUN_PROFILE = "canary"

# Explicit source paths for RUN_PROFILE = "baseline_import". Relative paths are
# resolved from the repository root and are never written to portable evidence.
BASELINE_RESULT_PATH = Path(
    "output/cipher_development_sources/two_period_overlay/latest_result.json"
)
BASELINE_RUNNER_PATH = Path(
    "output/cipher_development_sources/two_period_overlay/two_period_crib_solver_runner.py"
)


@dataclass(frozen=True, slots=True)
class RunBudget:
    coordinate_restarts: int
    coordinate_sweeps: int
    handoff_candidates: int
    minimum_comparisons: int
    sa_steps: int
    sa_cycles: int
    sa_t0: float = 0.005
    sa_tmin: float = 0.0001
    wallclock_limit_s: float = 300.0

    def __post_init__(self) -> None:
        for name in (
            "coordinate_restarts",
            "coordinate_sweeps",
            "handoff_candidates",
            "minimum_comparisons",
            "sa_steps",
            "sa_cycles",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a positive integer")
            if value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.minimum_comparisons > self.handoff_candidates:
            raise ValueError("minimum_comparisons must not exceed handoff_candidates")
        for name in ("sa_t0", "sa_tmin", "wallclock_limit_s"):
            value = getattr(self, name)
            if isinstance(value, bool):
                raise TypeError(f"{name} must be a positive finite number")
            number = float(value)
            if not math.isfinite(number) or number <= 0:
                raise ValueError(f"{name} must be a positive finite number")
            object.__setattr__(self, name, number)
        if self.sa_tmin > self.sa_t0:
            raise ValueError("sa_tmin must be no greater than sa_t0")


RUN_BUDGETS = {
    "canary": RunBudget(
        coordinate_restarts=4,
        coordinate_sweeps=2,
        handoff_candidates=2,
        minimum_comparisons=1,
        sa_steps=50,
        sa_cycles=1,
        wallclock_limit_s=300.0,
    ),
    "full": RunBudget(
        coordinate_restarts=64,
        coordinate_sweeps=20,
        handoff_candidates=8,
        minimum_comparisons=4,
        sa_steps=5_000,
        sa_cycles=2,
        wallclock_limit_s=28_800.0,
    ),
}

SCORING_CONTRACT = {
    "objective": "pct.logp.win10",
    "include_char": True,
    "use_word_breaks": True,
    "n_char": 4,
    "n_wli": 4,
    "char_weights": {3: 0.5, 4: 0.5},
    "wli_weights": {3: 0.5, 4: 0.5},
    "encoding_direction": "ltr",
    "hard_crib": True,
}


def budget_for(profile: str) -> RunBudget:
    try:
        return RUN_BUDGETS[profile]
    except KeyError as exc:
        allowed = sorted((*RUN_BUDGETS, "baseline_import"))
        raise ValueError(f"profile must be one of {allowed}") from exc
