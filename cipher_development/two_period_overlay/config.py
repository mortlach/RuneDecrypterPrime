from __future__ import annotations

from dataclasses import dataclass
import math
import re

ALPHABET_SIZE = 29
TEXT_LENGTH = 308
CRIB_WORD = "uncomfortable"
CRIB_START = 188
CRIB_RUNES = (1, 9, 5, 3, 19, 0, 3, 4, 16, 24, 17, 20, 18)
MASTER_SEED = 101
DECISION_SCORE = "wli_decision_score"
ARCHIVE_CAPACITY = 64
RUN_EXPERIMENT = "benchmark_contract_canary"
RUN_PROFILE = "canary"
RUN_BENCHMARK_ID = "alice_308_p13_p17_d16"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@dataclass(frozen=True, slots=True)
class BenchmarkSpec:
    benchmark_id: str
    period_a: int
    period_b: int
    expected_free_dimension: int
    alphabet_size: int = ALPHABET_SIZE
    schedule: str = "overlay"
    text_length: int = TEXT_LENGTH
    crib_word: str = CRIB_WORD
    crib_start: int = CRIB_START
    gauge_stream: str = "B"
    gauge_index: int = 0
    gauge_value: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.benchmark_id, str) or not _ID_RE.fullmatch(self.benchmark_id):
            raise ValueError("benchmark_id must use lowercase letters, numbers, '_' or '-'")
        for name in (
            "period_a", "period_b", "alphabet_size", "text_length", "crib_start",
            "expected_free_dimension", "gauge_index", "gauge_value",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        if self.period_a <= 0 or self.period_b <= 0:
            raise ValueError("periods must be positive")
        if self.period_a == self.period_b:
            raise ValueError("periods must differ")
        if self.alphabet_size <= 1:
            raise ValueError("alphabet_size must be greater than one")
        if self.text_length <= 0:
            raise ValueError("text_length must be positive")
        if self.crib_start < 0 or self.crib_start + len(CRIB_RUNES) > self.text_length:
            raise ValueError("crib must fit within the benchmark text")
        if self.expected_free_dimension < 0 or self.expected_free_dimension > self.key_length:
            raise ValueError("expected_free_dimension is outside the key space")
        if self.schedule != "overlay":
            raise ValueError("the WP6 ladder supports only the full overlay schedule")
        if self.crib_word != CRIB_WORD:
            raise ValueError("the WP6 ladder uses the complete 'uncomfortable' crib")
        if (self.gauge_stream, self.gauge_index, self.gauge_value) != ("B", 0, 0):
            raise ValueError("the WP6 ladder fixes the gauge B[0] = 0")

    @property
    def key_length(self) -> int:
        return self.period_a + self.period_b

    @property
    def gauge_key_index(self) -> int:
        return self.period_a + self.gauge_index

    def to_json_dict(self) -> dict[str, int | str]:
        return {
            "benchmark_id": self.benchmark_id,
            "period_a": self.period_a,
            "period_b": self.period_b,
            "alphabet_size": self.alphabet_size,
            "schedule": self.schedule,
            "text_length": self.text_length,
            "crib_word": self.crib_word,
            "crib_start": self.crib_start,
            "gauge": f"{self.gauge_stream}[{self.gauge_index}]={self.gauge_value}",
            "expected_free_dimension": self.expected_free_dimension,
        }


BENCHMARK_LADDER = (
    BenchmarkSpec("alice_308_p05_p07_d00", 5, 7, 0),
    BenchmarkSpec("alice_308_p05_p13_d04", 5, 13, 4),
    BenchmarkSpec("alice_308_p09_p13_d08", 9, 13, 8),
    BenchmarkSpec("alice_308_p13_p17_d16", 13, 17, 16),
)
BENCHMARKS = {spec.benchmark_id: spec for spec in BENCHMARK_LADDER}
TARGET_BENCHMARK = BENCHMARKS[RUN_BENCHMARK_ID]

# Compatibility aliases for the current target-only search implementation. New
# benchmark-aware code should use BenchmarkSpec fields directly.
PERIOD_A = TARGET_BENCHMARK.period_a
PERIOD_B = TARGET_BENCHMARK.period_b


def benchmark_for(benchmark_id: str) -> BenchmarkSpec:
    try:
        return BENCHMARKS[benchmark_id]
    except KeyError as exc:
        raise ValueError(f"unknown two-period benchmark {benchmark_id!r}") from exc


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
            "coordinate_restarts", "coordinate_sweeps", "handoff_candidates",
            "minimum_comparisons", "sa_steps", "sa_cycles",
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
    "model_root": None,
    "smoothing": "auto_gt",
    "alpha": 0.5,
    "oov_policy": "floor_min_seen",
    "objective": "pct.logp.win10",
    "include_char": True,
    "use_word_breaks": True,
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
    "avg_window_policy": "fixed_win",
    "impl": "auto",
    "compute_dtype": "float32",
    "acc_dtype": "float64",
    "dtype": "float64",
    "ecdf_clamp_min": 1e-6,
    "ecdf_clamp_max": 1.0 - 1e-6,
    "diagnostics_enabled": False,
    "hard_crib": True,
    "hamming_enabled": False,
    "span_hamming_enabled": False,
    "word_ngram_judge_enabled": False,
}


def budget_for(profile: str) -> RunBudget:
    try:
        return RUN_BUDGETS[profile]
    except KeyError as exc:
        raise ValueError(f"profile must be one of {sorted(RUN_BUDGETS)}") from exc
