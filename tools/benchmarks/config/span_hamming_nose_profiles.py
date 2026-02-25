from __future__ import annotations

"""Typed profiles for the span-hamming NOSE benchmark suite."""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from tools.benchmarks.scoring.span_hamming_nose.schema import (
    DEFAULT_GENERATORS,
    DEFAULT_LENGTH_BUCKETS,
)


@dataclass(frozen=True)
class SpanHammingNoseProfile:
    """Benchmark-facing profile for span-hamming NOSE runs."""

    profile_id: str
    description: str
    corpus_paths: Tuple[str, ...]
    corpus_glob: Optional[str]
    output_root: str
    global_seed: int
    directions: Tuple[str, ...]
    length_buckets: Tuple[int, ...]
    generators: Tuple[str, ...]
    samples_per_bucket: int
    len_min: int
    len_max: int
    max_hd: int
    max_candidates_per_window: int
    max_intervals_considered_per_start: int
    min_quality_threshold: float
    checkpoint_every: int
    max_rows: Optional[int]
    include_baselines: bool
    baseline_objectives: Tuple[str, ...]


_PROFILES: Dict[str, SpanHammingNoseProfile] = {}


def _build_profiles() -> Dict[str, SpanHammingNoseProfile]:
    profiles: Dict[str, SpanHammingNoseProfile] = {}

    profiles["span_hamming_nose_v1"] = SpanHammingNoseProfile(
        profile_id="span_hamming_nose_v1",
        description=(
            "Default full NOSE sweep for span_hamming using deterministic plan/checkpoint flow."
        ),
        corpus_paths=(),
        corpus_glob="assets_packed/tokenized_pg/*_fwd.npz",
        output_root="output/tools/benchmarks/scoring/span_hamming_nose_suite",
        global_seed=12345,
        directions=("ltr",),
        length_buckets=tuple(int(x) for x in DEFAULT_LENGTH_BUCKETS),
        generators=tuple(str(x).upper() for x in DEFAULT_GENERATORS),
        samples_per_bucket=300,
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        max_intervals_considered_per_start=4,
        min_quality_threshold=1e-9,
        checkpoint_every=200,
        max_rows=None,
        include_baselines=False,
        baseline_objectives=("avg.logp.win20",),
    )

    profiles["span_hamming_nose_smoke_v1"] = SpanHammingNoseProfile(
        profile_id="span_hamming_nose_smoke_v1",
        description="Small deterministic smoke profile for fast local checks.",
        corpus_paths=(),
        corpus_glob="assets_packed/tokenized_pg/*_fwd.npz",
        output_root="output/tools/benchmarks/scoring/span_hamming_nose_suite",
        global_seed=12345,
        directions=("ltr",),
        length_buckets=(20, 50),
        generators=("REAL", "RAND_UNIGRAM"),
        samples_per_bucket=8,
        len_min=3,
        len_max=8,
        max_hd=2,
        max_candidates_per_window=128,
        max_intervals_considered_per_start=3,
        min_quality_threshold=1e-9,
        checkpoint_every=20,
        max_rows=None,
        include_baselines=False,
        baseline_objectives=("avg.logp.win20",),
    )
    return profiles


def get_span_hamming_nose_profile(profile_id: str) -> SpanHammingNoseProfile:
    """Return an immutable profile by id."""

    if not _PROFILES:
        _PROFILES.update(_build_profiles())
    pid = str(profile_id).strip()
    profile = _PROFILES.get(pid)
    if profile is None:
        known = ", ".join(sorted(_PROFILES.keys()))
        raise ValueError(f"Unknown span_hamming NOSE profile_id={pid!r}. Known: {known}")
    return profile
