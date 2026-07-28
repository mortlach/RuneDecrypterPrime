from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any

ALPHABET_SIZE = 29
TEXT_LENGTH = 308
CRIB_WORD = "uncomfortable"
CRIB_START = 188
CRIB_RUNES = (1, 9, 5, 3, 19, 0, 3, 4, 16, 24, 17, 20, 18)
DORMOUSE_WORD = "dormouse"
DORMOUSE_RUNES = (23, 3, 4, 19, 3, 1, 15, 18)
MASTER_SEED = 101
DECISION_SCORE = "wli_decision_score"
ARCHIVE_CAPACITY = 64
RUN_EXPERIMENT = "archive_handoff"
RUN_PROFILE = "canary"
RUN_BENCHMARK_ID = "alice_308_p13_p17_d16"
REQUIRED_REPLAY_BINDING_ARTIFACTS = (
    "artifacts/archive_handoff_binding.json",
    "artifacts/control_start_binding.json",
)
REQUIRED_REPLAY_REPEAT_COUNT = 2
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@dataclass(frozen=True, slots=True)
class CribSpec:
    """One complete plaintext span deliberately exposed to an experiment."""

    label: str
    word: str
    start: int
    runes: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not _ID_RE.fullmatch(self.label):
            raise ValueError("crib label must use lowercase letters, numbers, '_' or '-'")
        if not isinstance(self.word, str) or not self.word.strip():
            raise ValueError("crib word must be a non-empty string")
        if isinstance(self.start, bool) or not isinstance(self.start, int) or self.start < 0:
            raise ValueError("crib start must be a non-negative integer")
        try:
            runes = tuple(int(value) for value in self.runes)
        except (TypeError, ValueError) as exc:
            raise TypeError("crib runes must be an integer sequence") from exc
        if not runes:
            raise ValueError("crib runes must not be empty")
        if any(value < 0 or value >= ALPHABET_SIZE for value in runes):
            raise ValueError("crib runes must be valid modulo-29 symbols")
        object.__setattr__(self, "word", self.word.strip().lower())
        object.__setattr__(self, "runes", runes)

    @property
    def stop(self) -> int:
        return self.start + len(self.runes)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "word": self.word,
            "start": self.start,
            "rune_length": len(self.runes),
            "runes": list(self.runes),
        }


PRIMARY_CRIB = CribSpec("uncomfortable_188", CRIB_WORD, CRIB_START, CRIB_RUNES)
EXTRA_CRIB_206 = CribSpec("dormouse_206", DORMOUSE_WORD, 206, DORMOUSE_RUNES)
EXTRA_CRIB_081 = CribSpec("dormouse_081", DORMOUSE_WORD, 81, DORMOUSE_RUNES)


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
    additional_cribs: tuple[CribSpec, ...] = ()
    additional_cribs_are_exact: bool = True

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

        if not isinstance(self.additional_cribs_are_exact, bool):
            raise TypeError("additional_cribs_are_exact must be a boolean")

        cribs = tuple(self.additional_cribs)
        if any(not isinstance(item, CribSpec) for item in cribs):
            raise TypeError("additional_cribs must contain CribSpec values")
        occupied = set(range(PRIMARY_CRIB.start, PRIMARY_CRIB.stop))
        for crib in cribs:
            if crib.stop > self.text_length:
                raise ValueError(f"additional crib {crib.label!r} does not fit the text")
            positions = set(range(crib.start, crib.stop))
            if occupied & positions:
                raise ValueError("complete crib spans must not overlap")
            occupied.update(positions)
        object.__setattr__(self, "additional_cribs", cribs)

    @property
    def key_length(self) -> int:
        return self.period_a + self.period_b

    @property
    def gauge_key_index(self) -> int:
        return self.period_a + self.gauge_index

    @property
    def crib_specs(self) -> tuple[CribSpec, ...]:
        return (PRIMARY_CRIB, *self.additional_cribs)

    def to_json_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
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
        # Keep old replay contexts byte-for-byte compatible at the contract level.
        if self.additional_cribs:
            payload["additional_cribs"] = [
                crib.to_json_dict() for crib in self.additional_cribs
            ]
        if not self.additional_cribs_are_exact:
            payload["additional_cribs_are_exact"] = False
        return payload


BENCHMARK_LADDER = (
    BenchmarkSpec("alice_308_p05_p07_d00", 5, 7, 0),
    BenchmarkSpec("alice_308_p05_p13_d04", 5, 13, 4),
    BenchmarkSpec("alice_308_p09_p13_d08", 9, 13, 8),
    BenchmarkSpec("alice_308_p13_p17_d16", 13, 17, 16),
)
EXACT_EXTRA_CRIB_BENCHMARKS = (
    BenchmarkSpec(
        "alice_308_p13_p17_crib188x13_plus206x8_d08",
        13,
        17,
        8,
        additional_cribs=(EXTRA_CRIB_206,),
    ),
    BenchmarkSpec(
        "alice_308_p13_p17_crib188x13_plus081x8_d08",
        13,
        17,
        8,
        additional_cribs=(EXTRA_CRIB_081,),
    ),
)

# WP6 Pack 06 controlled period-13 / period-31 benchmark ladder.  The first
# three entries exist to lock the independently derived rank changes; the final
# entry is the frozen d14 scientific target.
P13_P31_BENCHMARKS = (
    BenchmarkSpec(
        "alice_308_p13_p31_crib188x13_d30",
        13,
        31,
        30,
    ),
    BenchmarkSpec(
        "alice_308_p13_p31_crib188x13_plus081x8_d22",
        13,
        31,
        22,
        additional_cribs=(EXTRA_CRIB_081,),
    ),
    BenchmarkSpec(
        "alice_308_p13_p31_crib188x13_plus206x8_d22",
        13,
        31,
        22,
        additional_cribs=(EXTRA_CRIB_206,),
    ),
    BenchmarkSpec(
        "alice_308_p13_p31_crib188x13_plus081x8_plus206x8_d14",
        13,
        31,
        14,
        additional_cribs=(EXTRA_CRIB_081, EXTRA_CRIB_206),
    ),
)
P13_P31_PRIMARY_BENCHMARK = P13_P31_BENCHMARKS[0]
P13_P31_DORMOUSE_081_BENCHMARK = P13_P31_BENCHMARKS[1]
P13_P31_DORMOUSE_206_BENCHMARK = P13_P31_BENCHMARKS[2]
P13_P31_TARGET_BENCHMARK = P13_P31_BENCHMARKS[3]

BENCHMARKS = {
    spec.benchmark_id: spec
    for spec in (
        *BENCHMARK_LADDER,
        *EXACT_EXTRA_CRIB_BENCHMARKS,
        *P13_P31_BENCHMARKS,
    )
}
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
