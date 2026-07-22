from __future__ import annotations

from dataclasses import dataclass
import math

ALPHABET_SIZE = 29
ORDER = "col_then_sub"
RAW_SCORE = "seed_raw_score"
WLI_SCORE = "wli_decision_score"
ARCHIVE_CAPACITY = 64
MASTER_SEED = 404
RUN_PROFILE = "canary"


@dataclass(frozen=True, slots=True)
class BenchmarkSpec:
    benchmark_id: str
    family: str
    period: int
    columns: int
    length: int
    text_offset_hint: int
    truth_key_seed: int

    def __post_init__(self) -> None:
        if not isinstance(self.benchmark_id, str) or not self.benchmark_id.strip():
            raise ValueError("benchmark_id must be a non-empty string")
        if self.family not in {"positive_control", "target"}:
            raise ValueError("family must be positive_control or target")
        for name in ("period", "columns", "length", "text_offset_hint", "truth_key_seed"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        if self.period <= 0 or self.columns <= 0 or self.length <= 0:
            raise ValueError("period, columns and length must be positive")
        if self.text_offset_hint < 0 or self.truth_key_seed < 0:
            raise ValueError("text_offset_hint and truth_key_seed must be non-negative")


@dataclass(frozen=True, slots=True)
class SeedPoolPlan:
    n_block_seeds: int
    n_tail_seeds: int
    n_starts: int
    refine_steps: int
    tail_move_prob: float
    temp_start: float
    temp_end: float

    def __post_init__(self) -> None:
        for name in ("n_block_seeds", "n_tail_seeds", "n_starts", "refine_steps"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a non-negative integer")
            if value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name in ("tail_move_prob", "temp_start", "temp_end"):
            value = getattr(self, name)
            if isinstance(value, bool):
                raise TypeError(f"{name} must be a finite number")
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"{name} must be a finite number")
            object.__setattr__(self, name, number)
        if not 0.0 <= self.tail_move_prob <= 1.0:
            raise ValueError("tail_move_prob must be between 0 and 1")
        if self.temp_start <= 0 or self.temp_end <= 0 or self.temp_end > self.temp_start:
            raise ValueError("temperatures must be positive with temp_end <= temp_start")


@dataclass(frozen=True, slots=True)
class RunBudget:
    candidate_pool_size: int
    handoff_candidates: int
    exploitation_replicates: int
    solver_restarts: int
    solver_steps: int
    solver_inner_batch: int
    minimum_policy_exclusive: int
    minimum_completed_target_cases: int
    minimum_completed_positive_controls: int
    wallclock_overrun_limit_s: float
    seed_plan: SeedPoolPlan

    def __post_init__(self) -> None:
        for name in (
            "candidate_pool_size",
            "handoff_candidates",
            "exploitation_replicates",
            "solver_restarts",
            "solver_steps",
            "solver_inner_batch",
            "minimum_policy_exclusive",
            "minimum_completed_target_cases",
            "minimum_completed_positive_controls",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a positive integer")
            if value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.candidate_pool_size > ARCHIVE_CAPACITY:
            raise ValueError("candidate_pool_size must not exceed archive capacity")
        if self.handoff_candidates > self.candidate_pool_size:
            raise ValueError("handoff_candidates must not exceed candidate_pool_size")
        if self.solver_restarts != 1:
            raise ValueError("WP4 requires one seeded solver restart per campaign replicate")
        if isinstance(self.wallclock_overrun_limit_s, bool):
            raise TypeError("wallclock_overrun_limit_s must be a positive finite number")
        limit = float(self.wallclock_overrun_limit_s)
        if not math.isfinite(limit) or limit <= 0:
            raise ValueError("wallclock_overrun_limit_s must be a positive finite number")
        object.__setattr__(self, "wallclock_overrun_limit_s", limit)
        if not isinstance(self.seed_plan, SeedPoolPlan):
            raise TypeError("seed_plan must be a SeedPoolPlan")


POSITIVE_CONTROL = BenchmarkSpec(
    benchmark_id="periodic_col_p7_c5_l400",
    family="positive_control",
    period=7,
    columns=5,
    length=400,
    text_offset_hint=0,
    truth_key_seed=111,
)
TARGET_CASE = BenchmarkSpec(
    benchmark_id="periodic_col_p13_c13_l300",
    family="target",
    period=13,
    columns=13,
    length=300,
    text_offset_hint=0,
    truth_key_seed=111,
)

CANARY_CASES = (POSITIVE_CONTROL, TARGET_CASE)
FULL_CASES = tuple(
    BenchmarkSpec(
        benchmark_id=(
            f"periodic_col_p{period}_c{columns}_l{length}_o{offset}_v{variant}"
        ),
        family=family,
        period=period,
        columns=columns,
        length=length,
        text_offset_hint=offset,
        truth_key_seed=seed,
    )
    for family, period, columns, length in (
        ("positive_control", 7, 5, 400),
        ("target", 13, 13, 300),
    )
    for offset in (0, 211)
    for variant, seed in enumerate((111, 222), start=1)
)


def _scoring_contract(*, objective: str, use_word_breaks: bool, avg_window_policy: str) -> dict:
    return {
        "model_root": None,
        "smoothing": "auto_gt",
        "alpha": 0.5,
        "oov_policy": "floor_min_seen",
        "objective": objective,
        "include_char": True,
        "use_word_breaks": use_word_breaks,
        "n_char": 4,
        "n_wli": 4,
        "win": 10,
        "stride": 1,
        "se_mode": "nose",
        "weights": [0.25, 0.75],
        "maximize": True,
        "char_weights": {3: 0.5, 4: 0.5},
        "wli_weights": {3: 0.5, 4: 0.5},
        "encoding_direction": "ltr",
        "avg_window_policy": avg_window_policy,
        "impl": "auto",
        "compute_dtype": "float32",
        "acc_dtype": "float64",
        "dtype": "float64",
        "ecdf_clamp_min": 1e-6,
        "ecdf_clamp_max": 1.0 - 1e-6,
        "diagnostics_enabled": False,
        "hard_crib": False,
        "hamming_enabled": False,
        "span_hamming_enabled": False,
        "word_ngram_judge_enabled": False,
    }


RAW_SCORING_CONTRACT = _scoring_contract(
    objective="avg.logp",
    use_word_breaks=False,
    avg_window_policy="full_text",
)
WLI_SCORING_CONTRACT = _scoring_contract(
    objective="pct.logp.win10",
    use_word_breaks=True,
    avg_window_policy="fixed_win",
)

KAEDING_SOLVER_CONTRACT = {
    "block_schedule": "round_robin",
    "slip_every": 50,
    "slip_blocks": 1,
    "col_every": 10,
    "col_batch": 64,
    "seed_selection_metric": "pct",
    "seed_restarts": 1,
    "slip_policy": "fixed",
    "stall_rounds": 50,
    "stall_slip_limit": 2,
    "slip_swaps": 20,
    "stall_stop_on_limit": False,
    "slip_follow_steps": 200,
    "use_raw_score": False,
    "raw_accept_min_delta": 1e-6,
    "pct_plateau_min_delta": 0.0,
    "delta_window": 200,
    "top_k": 0,
    "plateau_rounds": 360,
    "plateau_min_delta": 1e-6,
}

RUN_BUDGETS = {
    "canary": RunBudget(
        candidate_pool_size=16,
        handoff_candidates=2,
        exploitation_replicates=1,
        solver_restarts=1,
        solver_steps=24,
        solver_inner_batch=8,
        minimum_policy_exclusive=1,
        minimum_completed_target_cases=1,
        minimum_completed_positive_controls=1,
        wallclock_overrun_limit_s=900.0,
        seed_plan=SeedPoolPlan(
            n_block_seeds=3,
            n_tail_seeds=3,
            n_starts=16,
            refine_steps=20,
            tail_move_prob=0.45,
            temp_start=0.06,
            temp_end=0.008,
        ),
    ),
    "full": RunBudget(
        candidate_pool_size=64,
        handoff_candidates=8,
        exploitation_replicates=2,
        solver_restarts=1,
        solver_steps=300,
        solver_inner_batch=32,
        minimum_policy_exclusive=2,
        minimum_completed_target_cases=4,
        minimum_completed_positive_controls=2,
        wallclock_overrun_limit_s=28_800.0,
        seed_plan=SeedPoolPlan(
            n_block_seeds=6,
            n_tail_seeds=6,
            n_starts=64,
            refine_steps=600,
            tail_move_prob=0.45,
            temp_start=0.06,
            temp_end=0.008,
        ),
    ),
}


def cases_for(profile: str) -> tuple[BenchmarkSpec, ...]:
    if profile == "canary":
        return CANARY_CASES
    if profile == "full":
        return FULL_CASES
    raise ValueError("profile must be canary or full")


def budget_for(profile: str) -> RunBudget:
    try:
        return RUN_BUDGETS[profile]
    except KeyError as exc:
        raise ValueError("profile must be canary or full") from exc
