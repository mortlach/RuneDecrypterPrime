from __future__ import annotations

"""
PhaseB Runeberg NOSE damaged-text span-Hamming ladder prototype v1.

IDE-friendly: edit the CONFIG block and run this file. No CLI arguments.

Purpose
-------
Use many tokenised Project Runeberg book chunks to test whether PhaseA14
strict/normal span-Hamming evidence survives across controlled damage and null
models. This is report-only. It does not change the production scorer.

Input
-----
Existing parser output files:

    TOKENIZED_ROOT/<book>_fwd.npz
    TOKENIZED_ROOT/<book>_rev.npz

Each .npz must contain:

    pt_nose_data   uint8 rune tokens, expected 0..28
    wli_nose_data  flattened uint8 word-location pairs, reshape(-1, 2)

Output
------
Writes streaming CSVs plus rolling timing/statistics to OUTPUT_DIR.

Notes
-----
This prototype deliberately uses NOSE only, source-word bounded chunks of up to
500 tokens, PhaseA14 selected dictionaries, and an explicitly named HD ladder
profile. Staged modes are FWD only unless their hardcoded mode settings say
otherwise.
"""

import csv
import gzip
import hashlib
import json
import math
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


# =============================================================================
# CONFIG: edit here, run from IDE
# =============================================================================

RUN_LABEL = "stage1_fwd_full_1k_pc_a"
RUN_MODE = "stage1_fwd_full_1k"  # "stage0_fwd_full_canary", "stage1_fwd_full_1k", "smoke", "timing_pilot", "medium_summary_50", "medium_summary_500", "medium_summary_1000", "pilot", "full".
BOOK_ORDER = "forward"  # "forward" or "reverse"; deterministic traversal of complete books.
BOOK_SKIP = 0
BOOK_LIST_FILE_REL = ""  # Optional repo-relative text file, one book name per line.
CHUNK_START_INDEX = 0
VERBOSE_ROLLING_SUMMARY_MODES = ("smoke",)
FORCE_VERBOSE_ROLLING_SUMMARY = False
WRITE_RAW_FEATURE_ROWS_MODES = ("smoke", "timing_pilot", "pilot")
WRITE_FEATURE_HISTOGRAMS_MODES = ("stage0_fwd_full_canary", "stage1_fwd_full_1k", "medium_summary_50", "medium_summary_500", "medium_summary_1000", "full")
WRITE_FEATURE_QUANTILES_MODES = ("stage0_fwd_full_canary", "stage1_fwd_full_1k", "medium_summary_50", "medium_summary_500", "medium_summary_1000", "full")
FEATURE_HISTOGRAMS_NAME = "feature_histograms.csv.gz"
FEATURE_QUANTILES_NAME = "feature_quantiles.csv.gz"
DAMAGED_VS_NULL_SUMMARY_NAME = "damaged_vs_null_summary.csv"
DAMAGED_VS_NULL_BY_VIEW_NAME = "damaged_vs_null_by_view.csv.gz"
CONVERGENCE_SUMMARY_NAME = "convergence_summary.csv"
DICTIONARY_HASH_MANIFEST_NAME = "dictionary_hash_manifest.csv"
EXCLUDE_BOOKS = (
    "1-0.txt",
    "10004.txt",
)

# These are deliberately relative to the detected repo root by default.
TOKENIZED_ROOT_REL = "../language_model_prime/lmprime_out/tokenized"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "stage1_fwd_full_1k_pc_a"
)

DIRECTIONS = ("fwd", "rev")
DIRECTIONS_BY_MODE = {
    "stage0_fwd_full_canary": ("fwd",),
    "stage1_fwd_full_1k": ("fwd",),
}
CHUNK_MAX_TOKENS = 500
CHUNK_SIZE = CHUNK_MAX_TOKENS  # Backward-compatible alias for tests/helpers.
GLOBAL_SEED = 20260507
DEFAULT_START_ASSUMPTION = "unknown_start"
SOURCE_START_ASSUMPTION = "assumed_word_start"
SCORE_REGIONS = ("full", "first_half", "second_half")
SCORE_REGIONS_BY_MODE = {
    "stage0_fwd_full_canary": ("full",),
    "stage1_fwd_full_1k": ("full",),
    "medium_summary_50": ("first_half", "second_half"),
    "medium_summary_500": ("first_half", "second_half"),
    "medium_summary_1000": ("first_half", "second_half"),
}
START_VIEW_SHIFTS_BY_MODE = {
    "stage0_fwd_full_canary": (0,),
    "stage1_fwd_full_1k": (0,),
    "smoke": (0, 3, 7, 11),
    "timing_pilot": (0, 3, 7, 11),
    "medium_summary_50": (0, 3, 7, 11),
    "medium_summary_500": (0, 3, 7, 11),
    "medium_summary_1000": (0, 3, 7, 11),
    "pilot": (0, 3, 7, 11),
    "full": (0,),
}
HISTOGRAM_BINS = (
    0.0,
    1e-6,
    1e-5,
    1e-4,
    5e-4,
    1e-3,
    2.5e-3,
    5e-3,
    1e-2,
    2.5e-2,
    5e-2,
    1e-1,
    2.5e-1,
    5e-1,
    1.0,
    2.0,
    5.0,
    math.inf,
)
QUANTILE_LEVELS = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)

# Named staged ladder. Do not change without changing LADDER_PROFILE.
LADDER_PROFILE = "v0_3_plus_long_relaxed_v2"
SPAN_LENGTHS = tuple(range(1, 15))
BASELINE_V0_3_MAX_HD_BY_LENGTH = {
    1: 0,
    2: 0,
    3: 1,
    4: 1,
    5: 1,
    6: 2,
    7: 2,
    8: 3,
    9: 3,
    10: 4,
    11: 4,
    12: 5,
    13: 5,
    14: 5,
}
MAX_HD_BY_LENGTH = {
    1: 0,
    2: 0,
    3: 1,
    4: 1,
    5: 1,
    6: 2,
    7: 3,
    8: 3,
    9: 4,
    10: 4,
    11: 5,
    12: 5,
    13: 6,
    14: 6,
}
BASELINE_V0_3_RUNG_COUNT = sum(max_hd + 1 for max_hd in BASELINE_V0_3_MAX_HD_BY_LENGTH.values())
TOTAL_LADDER_RUNG_COUNT = sum(max_hd + 1 for max_hd in MAX_HD_BY_LENGTH.values())
EXTRA_EXPERIMENTAL_RUNG_COUNT = TOTAL_LADDER_RUNG_COUNT - BASELINE_V0_3_RUNG_COUNT
CONVERGENCE_CHUNK_THRESHOLDS = (100, 250, 500, 1000)

# Fingerprint mode only: 0 means uncapped in the fast backend.
FINGERPRINT_MAX_CANDIDATES_PER_WINDOW = 0

# PhaseA14 selected dictionaries only.
DICTIONARY_SPECS = (
    {
        "dictionary_cut": "phaseA14_strict_selected",
        "dictionary_path": "assets/hamming_dictionary_policies_phaseA_v0_14/strict/hamming_raw_1g",
        "require_selected": True,
    },
    {
        "dictionary_cut": "phaseA14_normal_selected",
        "dictionary_path": "assets/hamming_dictionary_policies_phaseA_v0_14/normal/hamming_raw_1g",
        "require_selected": True,
    },
)

# Presets. Keep smoke small by default.
MODE_LIMITS = {
    "stage0_fwd_full_canary": {
        "num_clean_chunks": 25,
        "max_books": 510,
        "chunks_per_book_direction": 0,
        "damage_repeats_per_chunk": 1,
        "damage_levels": (0.20, 0.30, 0.40, 0.50, 0.60),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "checkpoint_every_samples": 100,
        "checkpoint_every_seconds": 300.0,
    },
    "stage1_fwd_full_1k": {
        "num_clean_chunks": 500,
        "max_books": 510,
        "chunks_per_book_direction": 0,
        "damage_repeats_per_chunk": 1,
        "damage_levels": (0.20, 0.30, 0.40, 0.50, 0.60),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "checkpoint_every_samples": 250,
        "checkpoint_every_seconds": 300.0,
    },
    "smoke": {
        "max_books": 2,
        "chunks_per_book_direction": 2,
        "damage_repeats_per_chunk": 1,
        "damage_levels": (0.30, 0.50),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "checkpoint_every_samples": 25,
        "checkpoint_every_seconds": 60.0,
    },
    "timing_pilot": {
        # 5 books * 2 directions * 2 chunks = about 20 clean chunks when every
        # selected book direction has enough source-word chunks.
        "num_clean_chunks": 20,
        "max_books": 5,
        "chunks_per_book_direction": 2,
        "damage_repeats_per_chunk": 1,
        "damage_levels": (0.20, 0.30, 0.40, 0.50, 0.60),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "checkpoint_every_samples": 25,
        "checkpoint_every_seconds": 60.0,
    },
    "medium_summary_50": {
        "num_clean_chunks": 50,
        "max_books": 25,
        "chunks_per_book_direction": 1,
        "damage_repeats_per_chunk": 1,
        "damage_levels": (0.20, 0.30, 0.40, 0.50, 0.60),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "checkpoint_every_samples": 50,
        "checkpoint_every_seconds": 300.0,
    },
    "medium_summary_500": {
        "num_clean_chunks": 500,
        "max_books": 250,
        "chunks_per_book_direction": 1,
        "damage_repeats_per_chunk": 1,
        "damage_levels": (0.20, 0.30, 0.40, 0.50, 0.60),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "checkpoint_every_samples": 100,
        "checkpoint_every_seconds": 300.0,
    },
    "medium_summary_1000": {
        "num_clean_chunks": 1000,
        "max_books": 500,
        "chunks_per_book_direction": 1,
        "damage_repeats_per_chunk": 1,
        "damage_levels": (0.20, 0.30, 0.40, 0.50, 0.60),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "checkpoint_every_samples": 100,
        "checkpoint_every_seconds": 300.0,
    },
    "pilot": {
        "max_books": 10,
        "chunks_per_book_direction": 10,
        "damage_repeats_per_chunk": 3,
        "damage_levels": (0.20, 0.30, 0.40, 0.50, 0.60),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "checkpoint_every_samples": 100,
        "checkpoint_every_seconds": 300.0,
    },
    "full": {
        "max_books": 100,
        "chunks_per_book_direction": 20,
        "damage_repeats_per_chunk": 5,
        "damage_levels": (0.10, 0.20, 0.30, 0.40, 0.50, 0.60),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "checkpoint_every_samples": 250,
        "checkpoint_every_seconds": 300.0,
    },
}

# Set true to run cheap internal determinism/range checks before the benchmark.
RUN_SELF_TESTS = True


# =============================================================================
# Repo/bootstrap and imports that depend on repo code
# =============================================================================


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    # Fallback for copied scripts run from a tools subfolder or IDE scratch area.
    cwd = Path.cwd().resolve()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root; expected parent containing src/ and tools/")


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.scoring.span_hamming.fast_backend import (  # noqa: E402
    FastSpanHammingBackend,
    fast_span_hamming_available,
)
from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig  # noqa: E402


# =============================================================================
# Small data types
# =============================================================================


@dataclass(frozen=True)
class TokenizedBookDirection:
    book: str
    direction: str
    path: Path
    tokens: np.ndarray
    wli: np.ndarray


@dataclass(frozen=True)
class CleanChunk:
    book: str
    direction: str
    chunk_index: int
    chunk_start: int
    chunk_end: int
    tokens: tuple[int, ...]
    wli: tuple[tuple[int, int], ...]
    source_start_assumption: str = SOURCE_START_ASSUMPTION
    corpus_chunk_index: int = 0

    @property
    def chunk_id(self) -> str:
        return f"{self.book}|{self.direction}|chunk{self.chunk_index:06d}|{self.chunk_start}_{self.chunk_end}"


@dataclass(frozen=True)
class Sample:
    sample_id: str
    source_kind: str  # clean | damaged | null
    damage_model: str
    damage_level: str
    null_model: str
    repeat_index: int
    seed: int
    clean_chunk: CleanChunk
    tokens: tuple[int, ...]


@dataclass(frozen=True)
class ScoreView:
    sample_id: str
    tokens: tuple[int, ...]
    start_assumption: str
    start_shift: int
    score_region: str


@dataclass(frozen=True)
class DictionarySpec:
    dictionary_cut: str
    dictionary_path: str
    require_selected: bool


@dataclass
class RunningStat:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0
    min_value: float = math.inf
    max_value: float = -math.inf

    def update(self, value: float) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta / float(self.count)
        delta2 = value - self.mean
        self.m2 += delta * delta2
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)

    @property
    def variance(self) -> float:
        if self.count < 2:
            return 0.0
        return self.m2 / float(self.count - 1)

    @property
    def stddev(self) -> float:
        return math.sqrt(max(0.0, self.variance))

    @property
    def stderr(self) -> float:
        if self.count < 1:
            return 0.0
        return self.stddev / math.sqrt(float(self.count))

    def row(self, extra: Mapping[str, Any]) -> dict[str, Any]:
        ci95 = 1.96 * self.stderr
        return {
            **dict(extra),
            "count": self.count,
            "mean": f"{self.mean:.12g}",
            "stddev": f"{self.stddev:.12g}",
            "stderr": f"{self.stderr:.12g}",
            "ci95_low": f"{self.mean - ci95:.12g}",
            "ci95_high": f"{self.mean + ci95:.12g}",
            "min": f"{self.min_value:.12g}" if self.count else "",
            "max": f"{self.max_value:.12g}" if self.count else "",
        }


@dataclass
class HistogramStat:
    bins: list[int]
    count: int = 0

    @classmethod
    def create(cls) -> "HistogramStat":
        return cls(bins=[0 for _ in HISTOGRAM_BINS])

    def update(self, value: float) -> None:
        self.count += 1
        for idx, upper in enumerate(HISTOGRAM_BINS):
            if value <= upper:
                self.bins[idx] += 1
                return
        self.bins[-1] += 1

    def quantile_upper_bound(self, q: float) -> float:
        if self.count <= 0:
            return 0.0
        target = max(1, int(math.ceil(float(q) * self.count)))
        running = 0
        for idx, bin_count in enumerate(self.bins):
            running += bin_count
            if running >= target:
                return float(HISTOGRAM_BINS[idx])
        return float(HISTOGRAM_BINS[-1])


# =============================================================================
# Generic helpers
# =============================================================================


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_int_seed(*parts: object) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little", signed=False) & 0x7FFF_FFFF_FFFF_FFFF


def _rng(*parts: object) -> np.random.Generator:
    return np.random.default_rng(_stable_int_seed(GLOBAL_SEED, *parts))


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return os.path.relpath(path.resolve(), REPO_ROOT.resolve()).replace(os.sep, "/")


def _resolve_from_repo_root(path_text: str) -> Path:
    return (REPO_ROOT / path_text).resolve()


def _require_output_under_repo(path: Path) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Output path must stay under repo root: {_repo_rel(resolved)}") from exc


def _safe_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _write_csv_header(path: Path, fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()


def _append_csv_rows(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, "at", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        for row in rows:
            writer.writerow(dict(row))
            count += 1
    return count


def _write_csv_rows(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
            count += 1
    return count


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return float(ordered[idx])


def _mode_limits() -> Mapping[str, Any]:
    if RUN_MODE not in MODE_LIMITS:
        raise ValueError(f"Unknown RUN_MODE={RUN_MODE!r}; expected one of {sorted(MODE_LIMITS)}")
    return MODE_LIMITS[RUN_MODE]


def score_regions_for_mode(run_mode: str) -> tuple[str, ...]:
    return tuple(SCORE_REGIONS_BY_MODE.get(run_mode, SCORE_REGIONS))


def active_hd_by_length() -> dict[int, list[int]]:
    return {length: list(range(MAX_HD_BY_LENGTH[length] + 1)) for length in SPAN_LENGTHS}


def ladder_profile_payload() -> dict[str, Any]:
    return {
        "ladder_profile": LADDER_PROFILE,
        "active_span_lengths": list(SPAN_LENGTHS),
        "active_hd_by_length": active_hd_by_length(),
        "baseline_v0_3_max_hd_by_length": dict(BASELINE_V0_3_MAX_HD_BY_LENGTH),
        "baseline_v0_3_rung_count": BASELINE_V0_3_RUNG_COUNT,
        "extra_experimental_rung_count": EXTRA_EXPERIMENTAL_RUNG_COUNT,
        "total_rung_count": TOTAL_LADDER_RUNG_COUNT,
    }


def write_raw_feature_rows_enabled(run_mode: str = RUN_MODE) -> bool:
    return run_mode in WRITE_RAW_FEATURE_ROWS_MODES


def write_feature_histograms_enabled(run_mode: str = RUN_MODE) -> bool:
    return run_mode in WRITE_FEATURE_HISTOGRAMS_MODES


def write_feature_quantiles_enabled(run_mode: str = RUN_MODE) -> bool:
    return run_mode in WRITE_FEATURE_QUANTILES_MODES


def num_clean_chunks_for_limits(
    limits: Mapping[str, Any],
    actual_clean_chunks: int | None = None,
    *,
    run_mode: str = RUN_MODE,
) -> int:
    configured = int(limits.get("num_clean_chunks", 0) or 0)
    if configured > 0:
        return configured if actual_clean_chunks is None else min(configured, int(actual_clean_chunks))
    if actual_clean_chunks is not None:
        return int(actual_clean_chunks)
    return nominal_clean_chunk_count_for_limits(limits, run_mode=run_mode)


# =============================================================================
# Input loading and chunking
# =============================================================================


def _book_name_from_tokenized(path: Path, direction: str) -> str:
    suffix = f"_{direction}.npz"
    name = path.name
    if not name.endswith(suffix):
        raise ValueError(f"tokenized file does not end with {suffix!r}: {path.name}")
    return name[: -len(suffix)]


def discover_tokenized_files(tokenized_root: Path) -> list[tuple[str, str, Path]]:
    rows: list[tuple[str, str, Path]] = []
    for direction in DIRECTIONS:
        for path in sorted(tokenized_root.glob(f"*_{direction}.npz")):
            rows.append((_book_name_from_tokenized(path, direction), direction, path))
    rows.sort(key=lambda row: (row[0], row[1]))
    return rows


def load_tokenized_nose(book: str, direction: str, path: Path) -> TokenizedBookDirection:
    data = np.load(path, allow_pickle=False)
    missing = [key for key in ("pt_nose_data", "wli_nose_data") if key not in data.files]
    if missing:
        raise KeyError(f"{_repo_rel(path)} missing required NOSE arrays: {missing}")

    tokens = np.asarray(data["pt_nose_data"], dtype=np.uint8)
    wli_flat = np.asarray(data["wli_nose_data"], dtype=np.uint8)
    if wli_flat.size % 2 != 0:
        raise ValueError(f"{_repo_rel(path)} wli_nose_data length is not even: {wli_flat.size}")
    wli = wli_flat.reshape(-1, 2)
    if tokens.shape[0] != wli.shape[0]:
        raise ValueError(f"{_repo_rel(path)} token/WLI length mismatch: {tokens.shape[0]} vs {wli.shape[0]}")
    if tokens.size and int(tokens.max()) > 28:
        raise ValueError(f"{_repo_rel(path)} contains NOSE token outside 0..28")
    return TokenizedBookDirection(book=book, direction=direction, path=path, tokens=tokens, wli=wli)


def complete_books_from_rows(rows: Sequence[tuple[str, str, Path]]) -> list[str]:
    """Return books that have every required direction file.

    The benchmark contract is fwd+rev, so a book missing either direction is
    excluded rather than silently becoming a one-direction sample.
    """
    by_book: dict[str, set[str]] = {}
    for book, direction, _path in rows:
        by_book.setdefault(book, set()).add(direction)
    required = set(DIRECTIONS)
    return sorted(book for book, seen in by_book.items() if required.issubset(seen))


def directions_for_mode(run_mode: str = RUN_MODE) -> tuple[str, ...]:
    return tuple(DIRECTIONS_BY_MODE.get(run_mode, DIRECTIONS))


def _read_book_list_file(path: Path) -> list[str]:
    books: list[str] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line in seen:
            duplicates.append(line)
        seen.add(line)
        books.append(line)
    if duplicates:
        raise ValueError(f"BOOK_LIST_FILE has duplicate books: {sorted(set(duplicates))}")
    if not books:
        raise ValueError(f"BOOK_LIST_FILE contains no book names: {_repo_rel(path)}")
    return books


def select_books_from_book_list_file(
    rows: Sequence[tuple[str, str, Path]],
    *,
    book_list_file: Path,
) -> list[str]:
    listed_books = _read_book_list_file(book_list_file)
    excluded_books = [book for book in listed_books if book in set(EXCLUDE_BOOKS)]
    if excluded_books:
        raise ValueError(
            f"BOOK_LIST_FILE preflight failed for {_repo_rel(book_list_file)}: "
            f"excluded books={excluded_books}"
        )
    by_book: dict[str, set[str]] = {}
    for book, direction, _path in rows:
        by_book.setdefault(book, set()).add(direction)
    missing: list[str] = []
    incomplete: list[str] = []
    required = set(DIRECTIONS)
    for book in listed_books:
        seen = by_book.get(book)
        if seen is None:
            missing.append(book)
        elif not required.issubset(seen):
            incomplete.append(f"{book}:missing={','.join(sorted(required - seen))}")
    if missing or incomplete:
        parts = []
        if missing:
            parts.append(f"missing books={missing}")
        if incomplete:
            parts.append(f"incomplete books={incomplete}")
        raise ValueError(f"BOOK_LIST_FILE preflight failed for {_repo_rel(book_list_file)}: {'; '.join(parts)}")
    return listed_books


def select_books(rows: Sequence[tuple[str, str, Path]], *, max_books: int) -> list[str]:
    if BOOK_LIST_FILE_REL:
        return select_books_from_book_list_file(rows, book_list_file=_resolve_from_repo_root(BOOK_LIST_FILE_REL))
    excluded = set(EXCLUDE_BOOKS)
    books = [book for book in complete_books_from_rows(rows) if book not in excluded]
    if BOOK_ORDER == "forward":
        ordered = books
    elif BOOK_ORDER == "reverse":
        ordered = list(reversed(books))
    else:
        raise ValueError(f"Unknown BOOK_ORDER={BOOK_ORDER!r}; expected 'forward' or 'reverse'")
    if BOOK_SKIP:
        ordered = ordered[int(BOOK_SKIP):]
    if max_books and len(ordered) > max_books:
        return ordered[:max_books]
    return ordered


def word_start_indices(wli: Sequence[Sequence[int]]) -> list[int]:
    return [idx for idx, pair in enumerate(wli) if int(pair[0]) == 0 and int(pair[1]) > 0]


def source_word_chunks_for_wli(
    wli: Sequence[Sequence[int]],
    *,
    max_tokens: int = CHUNK_MAX_TOKENS,
    limit: int = 0,
) -> list[tuple[int, int]]:
    """Build non-overlapping chunks that start and end on source word boundaries."""
    wli_array = np.asarray(wli, dtype=np.int64)
    if wli_array.ndim != 2 or wli_array.shape[1] != 2:
        raise ValueError(f"unexpected WLI shape {wli_array.shape}")
    positions = wli_array[:, 0]
    lengths = wli_array[:, 1]
    starts = np.flatnonzero((positions == 0) & (lengths > 0)).astype(np.int64).tolist()
    if not starts:
        return []
    n = int(wli_array.shape[0])
    chunks: list[tuple[int, int]] = []
    start_idx = 0
    while start_idx < len(starts):
        start = starts[start_idx]
        best_end = start
        cursor_idx = start_idx
        while cursor_idx < len(starts):
            cursor = starts[cursor_idx]
            if cursor != best_end:
                break
            length = int(lengths[cursor])
            if length <= 0:
                break
            end = cursor + length
            if end > n or (end - start) > max_tokens:
                break
            best_end = end
            cursor_idx += 1
        if best_end > start:
            chunks.append((start, best_end))
            if limit > 0 and len(chunks) >= limit:
                break
            while start_idx < len(starts) and starts[start_idx] < best_end:
                start_idx += 1
        else:
            start_idx += 1
    return chunks


def select_chunk_starts(
    *,
    book: str,
    direction: str,
    token_count: int,
    chunks_per_book_direction: int,
) -> list[int]:
    starts = list(range(token_count))
    if chunks_per_book_direction <= 0 or len(starts) <= chunks_per_book_direction:
        return starts
    return starts[:chunks_per_book_direction]


def build_clean_chunks(book_dir: TokenizedBookDirection, *, chunks_per_book_direction: int) -> list[CleanChunk]:
    spans = source_word_chunks_for_wli(
        book_dir.wli,
        max_tokens=CHUNK_MAX_TOKENS,
        limit=max(0, int(chunks_per_book_direction)),
    )
    chunks: list[CleanChunk] = []
    for idx, (start, end) in enumerate(spans):
        chunks.append(
            CleanChunk(
                book=book_dir.book,
                direction=book_dir.direction,
                chunk_index=idx,
                corpus_chunk_index=0,
                chunk_start=start,
                chunk_end=end,
                tokens=tuple(int(x) for x in book_dir.tokens[start:end]),
                wli=tuple((int(a), int(b)) for a, b in book_dir.wli[start:end]),
                source_start_assumption=SOURCE_START_ASSUMPTION,
            )
        )
    return chunks


def _input_manifest_row(book_dir: TokenizedBookDirection, sampled_chunks: int) -> dict[str, Any]:
    return {
        "book": book_dir.book,
        "direction": book_dir.direction,
        "path": _repo_rel(book_dir.path),
        "token_count": int(book_dir.tokens.size),
        "available_chunks": len(source_word_chunks_for_wli(book_dir.wli)),
        "sampled_chunks": sampled_chunks,
    }


def input_manifest_rows_for_used_chunks(
    loaded: Sequence[TokenizedBookDirection],
    clean_chunks: Sequence[CleanChunk],
) -> list[dict[str, Any]]:
    sampled_by_key: dict[tuple[str, str], int] = {}
    for chunk in clean_chunks:
        key = (chunk.book, chunk.direction)
        sampled_by_key[key] = sampled_by_key.get(key, 0) + 1
    rows: list[dict[str, Any]] = []
    for book_dir in loaded:
        sampled = sampled_by_key.get((book_dir.book, book_dir.direction), 0)
        if sampled > 0:
            rows.append(_input_manifest_row(book_dir, sampled_chunks=sampled))
    return rows


# =============================================================================
# Damage/null generation
# =============================================================================


def _empirical_probs(tokens: Sequence[int]) -> np.ndarray:
    counts = np.bincount(np.asarray(tokens, dtype=np.int64), minlength=29).astype(np.float64)
    total = float(counts.sum())
    if total <= 0.0:
        return np.ones(29, dtype=np.float64) / 29.0
    return counts / total


def _replace_positions_uniform(tokens: np.ndarray, positions: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = tokens.copy()
    if positions.size == 0:
        return out
    original = out[positions].astype(np.int16)
    repl = rng.integers(0, 28, size=positions.size, dtype=np.int16)
    repl = repl + (repl >= original)
    out[positions] = repl.astype(np.uint8)
    return out


def _replace_positions_from_probs(
    tokens: np.ndarray,
    positions: np.ndarray,
    rng: np.random.Generator,
    probs: np.ndarray,
) -> np.ndarray:
    out = tokens.copy()
    if positions.size == 0:
        return out
    repl = rng.choice(np.arange(29, dtype=np.uint8), size=positions.size, replace=True, p=probs)
    # Ensure actual substitution. Re-draw only same-as-original positions.
    same = repl == out[positions]
    guard = 0
    while bool(np.any(same)):
        repl[same] = rng.choice(np.arange(29, dtype=np.uint8), size=int(np.sum(same)), replace=True, p=probs)
        same = repl == out[positions]
        guard += 1
        if guard > 20:
            # Degenerate distribution, fall back to uniform-different for stubborn positions.
            stubborn = positions[same]
            tmp = _replace_positions_uniform(out, stubborn, rng)
            out[stubborn] = tmp[stubborn]
            same = np.zeros_like(same, dtype=bool)
    out[positions] = repl.astype(np.uint8)
    return out


def _positions_by_probability(n: int, p: float, rng: np.random.Generator) -> np.ndarray:
    mask = rng.random(n) < float(p)
    return np.flatnonzero(mask).astype(np.int64)


def _complete_word_intervals(wli: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    arr = np.asarray(wli, dtype=np.int64)
    out: list[tuple[int, int]] = []
    n = int(arr.shape[0])
    i = 0
    while i < n:
        pos = int(arr[i, 0])
        length = int(arr[i, 1])
        if pos == 0 and length > 0 and i + length <= n:
            expected = np.arange(length, dtype=np.int64)
            observed_pos = arr[i:i + length, 0]
            observed_len = arr[i:i + length, 1]
            if np.array_equal(observed_pos, expected) and bool(np.all(observed_len == length)):
                out.append((i, i + length))
                i += length
                continue
        i += 1
    return out


def damage_independent(tokens: Sequence[int], *, p: float, seed: int) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    positions = _positions_by_probability(int(arr.size), p, rng)
    out = _replace_positions_uniform(arr, positions, rng)
    return tuple(int(x) for x in out)


def damage_frequency_matched(tokens: Sequence[int], *, p: float, seed: int, probs: np.ndarray) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    positions = _positions_by_probability(int(arr.size), p, rng)
    out = _replace_positions_from_probs(arr, positions, rng, probs)
    return tuple(int(x) for x in out)


def damage_word_local(tokens: Sequence[int], wli: Sequence[tuple[int, int]], *, p: float, seed: int) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    intervals = _complete_word_intervals(wli)
    positions: list[int] = []
    # Keep this tied to p but explicitly word-local: choose words with p, then corrupt inside with p.
    for start, end in intervals:
        if rng.random() >= p:
            continue
        inner = np.arange(start, end, dtype=np.int64)
        inner_mask = rng.random(inner.size) < p
        positions.extend(int(x) for x in inner[inner_mask])
    out = _replace_positions_uniform(arr, np.asarray(sorted(set(positions)), dtype=np.int64), rng)
    return tuple(int(x) for x in out)


def damage_burst(tokens: Sequence[int], *, p: float, seed: int) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    n = int(arr.size)
    target = max(1, int(round(float(p) * n)))
    chosen: set[int] = set()
    attempts = 0
    while len(chosen) < target and attempts < 10_000:
        attempts += 1
        length = int(rng.integers(5, 21)) if rng.random() < 0.7 else int(rng.integers(25, 81))
        start = int(rng.integers(0, max(1, n)))
        for pos in range(start, min(n, start + length)):
            chosen.add(pos)
            if len(chosen) >= target:
                break
    out = _replace_positions_uniform(arr, np.asarray(sorted(chosen), dtype=np.int64), rng)
    return tuple(int(x) for x in out)


def damage_lane_period(tokens: Sequence[int], *, p: float, seed: int) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    n = int(arr.size)
    period = int(rng.choice(np.asarray([5, 7, 13, 19, 29], dtype=np.int64)))
    lane_count = int(rng.integers(1, min(3, period) + 1))
    lanes = set(int(x) for x in rng.choice(np.arange(period), size=lane_count, replace=False).tolist())
    positions = np.asarray([idx for idx in range(n) if (idx % period) in lanes], dtype=np.int64)
    if positions.size:
        positions = positions[rng.random(positions.size) < float(p)]
    out = _replace_positions_uniform(arr, positions, rng)
    return tuple(int(x) for x in out)


def null_uniform(tokens: Sequence[int], *, seed: int) -> tuple[int, ...]:
    rng = np.random.default_rng(seed)
    return tuple(int(x) for x in rng.integers(0, 29, size=len(tokens), dtype=np.uint8))


def null_frequency(tokens: Sequence[int], *, seed: int, probs: np.ndarray) -> tuple[int, ...]:
    rng = np.random.default_rng(seed)
    return tuple(int(x) for x in rng.choice(np.arange(29, dtype=np.uint8), size=len(tokens), replace=True, p=probs))


def null_within_chunk_shuffle(tokens: Sequence[int], *, seed: int) -> tuple[int, ...]:
    rng = np.random.default_rng(seed)
    arr = np.asarray(tokens, dtype=np.uint8).copy()
    rng.shuffle(arr)
    return tuple(int(x) for x in arr)


def null_block_shuffle(tokens: Sequence[int], *, seed: int, block_size: int) -> tuple[int, ...]:
    rng = np.random.default_rng(seed)
    arr = np.asarray(tokens, dtype=np.uint8)
    blocks = [arr[i:i + block_size].copy() for i in range(0, int(arr.size), block_size)]
    order = np.arange(len(blocks))
    rng.shuffle(order)
    out = np.concatenate([blocks[int(idx)] for idx in order])
    return tuple(int(x) for x in out[: len(tokens)])


def make_sample(
    *,
    clean_chunk: CleanChunk,
    source_kind: str,
    damage_model: str,
    damage_level: str,
    null_model: str,
    repeat_index: int,
    global_probs: np.ndarray,
    book_probs: np.ndarray,
) -> Sample:
    sample_id_base = f"{clean_chunk.chunk_id}|{source_kind}|{damage_model}|{damage_level}|{null_model}|r{repeat_index}"
    seed = _stable_int_seed(GLOBAL_SEED, sample_id_base)
    p = float(damage_level) if damage_level else 0.0

    if source_kind == "clean":
        tokens = clean_chunk.tokens
    elif source_kind == "damaged":
        if damage_model == "independent_substitution":
            tokens = damage_independent(clean_chunk.tokens, p=p, seed=seed)
        elif damage_model == "frequency_matched_global":
            tokens = damage_frequency_matched(clean_chunk.tokens, p=p, seed=seed, probs=global_probs)
        elif damage_model == "frequency_matched_book":
            tokens = damage_frequency_matched(clean_chunk.tokens, p=p, seed=seed, probs=book_probs)
        elif damage_model == "word_local_substitution":
            tokens = damage_word_local(clean_chunk.tokens, clean_chunk.wli, p=p, seed=seed)
        elif damage_model == "burst_substitution":
            tokens = damage_burst(clean_chunk.tokens, p=p, seed=seed)
        elif damage_model == "lane_period_substitution":
            tokens = damage_lane_period(clean_chunk.tokens, p=p, seed=seed)
        else:
            raise ValueError(f"Unknown damage_model: {damage_model}")
    elif source_kind == "null":
        if null_model == "uniform_random":
            tokens = null_uniform(clean_chunk.tokens, seed=seed)
        elif null_model == "global_frequency_random":
            tokens = null_frequency(clean_chunk.tokens, seed=seed, probs=global_probs)
        elif null_model == "within_chunk_shuffle":
            tokens = null_within_chunk_shuffle(clean_chunk.tokens, seed=seed)
        elif null_model.startswith("block_shuffle_"):
            block_size = int(null_model.rsplit("_", 1)[1])
            tokens = null_block_shuffle(clean_chunk.tokens, seed=seed, block_size=block_size)
        else:
            raise ValueError(f"Unknown null_model: {null_model}")
    else:
        raise ValueError(f"Unknown source_kind: {source_kind}")

    if len(tokens) != len(clean_chunk.tokens):
        raise AssertionError("damage/null function changed token length")
    if tokens and (min(tokens) < 0 or max(tokens) > 28):
        raise AssertionError("damage/null function produced token outside 0..28")

    return Sample(
        sample_id=sample_id_base,
        source_kind=source_kind,
        damage_model=damage_model,
        damage_level=damage_level,
        null_model=null_model,
        repeat_index=repeat_index,
        seed=seed,
        clean_chunk=clean_chunk,
        tokens=tuple(int(x) for x in tokens),
    )


def iter_samples_for_chunk(
    clean_chunk: CleanChunk,
    *,
    global_probs: np.ndarray,
    book_probs: np.ndarray,
    limits: Mapping[str, Any],
) -> Iterable[Sample]:
    yield make_sample(
        clean_chunk=clean_chunk,
        source_kind="clean",
        damage_model="none",
        damage_level="",
        null_model="",
        repeat_index=0,
        global_probs=global_probs,
        book_probs=book_probs,
    )

    for repeat in range(int(limits["damage_repeats_per_chunk"])):
        for level in limits["damage_levels"]:
            level_text = f"{float(level):.2f}"
            for model in limits["include_damage_models"]:
                yield make_sample(
                    clean_chunk=clean_chunk,
                    source_kind="damaged",
                    damage_model=str(model),
                    damage_level=level_text,
                    null_model="",
                    repeat_index=repeat,
                    global_probs=global_probs,
                    book_probs=book_probs,
                )
        for null_model in limits["include_null_models"]:
            yield make_sample(
                clean_chunk=clean_chunk,
                source_kind="null",
                damage_model="",
                damage_level="",
                null_model=str(null_model),
                repeat_index=repeat,
                global_probs=global_probs,
                book_probs=book_probs,
            )


def start_view_shifts_for_mode(run_mode: str) -> tuple[int, ...]:
    return tuple(int(value) for value in START_VIEW_SHIFTS_BY_MODE.get(run_mode, (0,)))


def iter_score_views_for_sample(sample: Sample, *, run_mode: str = RUN_MODE) -> Iterable[ScoreView]:
    for shift in start_view_shifts_for_mode(run_mode):
        if shift >= len(sample.tokens):
            continue
        shifted = tuple(sample.tokens[shift:])
        start_assumption = sample.clean_chunk.source_start_assumption if shift == 0 else DEFAULT_START_ASSUMPTION
        view_id = "base" if shift == 0 else f"shift_{shift}"
        regions = {
            "full": shifted,
            "first_half": shifted[: len(shifted) // 2],
            "second_half": shifted[len(shifted) // 2 :],
        }
        for region in score_regions_for_mode(run_mode):
            tokens = tuple(int(x) for x in regions[region])
            if tokens:
                yield ScoreView(
                    sample_id=f"{sample.sample_id}|{view_id}|{region}",
                    tokens=tokens,
                    start_assumption=start_assumption,
                    start_shift=shift,
                    score_region=region,
                )


# =============================================================================
# Span-Hamming fingerprint scoring
# =============================================================================


def build_backend(spec: DictionarySpec) -> FastSpanHammingBackend:
    cfg = SpanHammingConfig(
        len_min=min(SPAN_LENGTHS),
        len_max=max(SPAN_LENGTHS),
        max_hd=max(MAX_HD_BY_LENGTH.values()),
        max_candidates_per_window=1024,
        debug_return_intervals=False,
    )
    return FastSpanHammingBackend(
        config=cfg,
        wordlist_dir=REPO_ROOT / spec.dictionary_path,
        require_selected=spec.require_selected,
        return_raw_intervals=False,
    )


def _payload_length_metric(payload: Mapping[str, Any], metric_name: str, length: int) -> int:
    length_bins = [int(value) for value in payload.get("length_bins", [])]
    values = list(payload.get(metric_name, []))
    if length not in length_bins:
        return 0
    idx = length_bins.index(length)
    if idx >= len(values):
        return 0
    return int(values[idx])


def fingerprint_rows_for_sample(
    *,
    sample: Sample,
    spec: DictionarySpec,
    backend: FastSpanHammingBackend,
) -> tuple[list[dict[str, Any]], float]:
    rows: list[dict[str, Any]] = []
    elapsed_ms_total = 0.0
    for view in iter_score_views_for_sample(sample):
        start = time.perf_counter()
        payload = backend.fingerprint_raw_hamming_counts(
            view.tokens,
            include_offset_rows=True,
            include_match_dump=False,
            max_candidates_per_window=FINGERPRINT_MAX_CANDIDATES_PER_WINDOW,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        elapsed_ms_total += elapsed_ms

        count_by_key: dict[tuple[int, int], int] = {}
        matched_offsets_by_key: dict[tuple[int, int], set[int]] = {}
        for row in payload.get("chunk_bins", []):
            length = int(row["length"])
            hd = int(row["hd"])
            count_by_key[(length, hd)] = int(row["raw_match_count"])
        for row in payload.get("offset_bins", []):
            raw_count = int(row["raw_match_count"])
            if raw_count <= 0:
                continue
            key = (int(row["length"]), int(row["hd"]))
            offset = row.get("offset", row.get("start"))
            if offset is None:
                raise KeyError("offset_bins row missing offset/start")
            matched_offsets_by_key.setdefault(key, set()).add(int(offset))

        for length in SPAN_LENGTHS:
            max_hd = MAX_HD_BY_LENGTH[length]
            windows = max(0, len(view.tokens) - length + 1)
            denom = float(max(1, windows))
            running = 0
            matched_offsets: set[int] = set()
            n_considered = _payload_length_metric(payload, "n_candidates_considered_by_len", length)
            n_pruned = _payload_length_metric(payload, "n_candidates_pruned_cap_by_len", length)
            for hd in range(max_hd + 1):
                exact_count = int(count_by_key.get((length, hd), 0))
                running += exact_count
                matched_offsets.update(matched_offsets_by_key.get((length, hd), set()))
                matched_window_count = len(matched_offsets)
                rows.append(
                    {
                        "run_label": RUN_LABEL,
                        "sample_id": sample.sample_id,
                        "score_view_id": view.sample_id,
                        "book": sample.clean_chunk.book,
                        "direction": sample.clean_chunk.direction,
                        "chunk_id": sample.clean_chunk.chunk_id,
                        "chunk_index": sample.clean_chunk.chunk_index,
                        "corpus_chunk_index": sample.clean_chunk.corpus_chunk_index,
                        "chunk_start": sample.clean_chunk.chunk_start,
                        "chunk_end": sample.clean_chunk.chunk_end,
                        "source_kind": sample.source_kind,
                        "damage_model": sample.damage_model,
                        "damage_level": sample.damage_level,
                        "null_model": sample.null_model,
                        "repeat_index": sample.repeat_index,
                        "seed": sample.seed,
                        "start_assumption": view.start_assumption,
                        "start_shift": view.start_shift,
                        "score_region": view.score_region,
                        "score_token_count": len(view.tokens),
                        "dictionary_cut": spec.dictionary_cut,
                        "span_length": length,
                        "hd": hd,
                        "window_count": windows,
                        "exact_count": exact_count,
                        "hd_le_count": running,
                        "matched_window_count": matched_window_count,
                        "no_match_count": max(0, windows - matched_window_count),
                        "exact_count_norm": f"{exact_count / denom:.12g}",
                        "hd_le_count_norm": f"{running / denom:.12g}",
                        "n_candidates_considered": n_considered,
                        "n_candidates_pruned_cap": n_pruned,
                        "candidate_cap_pruned_rate": f"{n_pruned / float(max(1, n_considered + n_pruned)):.12g}",
                        "score_ms": f"{elapsed_ms:.6f}",
                        "backend_build_ms": "",
                        "fingerprint_scope": "raw_hamming_counts",
                        "fast_backend_hd_policy": str(payload.get("hd_max_policy", "length_minus_one")),
                        "enabled_ladder_only": 1,
                        "ladder_profile": LADDER_PROFILE,
                        "cap": int(payload.get("cap", FINGERPRINT_MAX_CANDIDATES_PER_WINDOW) or 0),
                        "is_uncapped": int(bool(payload.get("is_uncapped", FINGERPRINT_MAX_CANDIDATES_PER_WINDOW == 0))),
                    }
                )
    return rows, elapsed_ms_total


# =============================================================================
# Output field names and rolling summary
# =============================================================================


SAMPLE_FIELDS = [
    "run_label",
    "sample_id",
    "book",
    "direction",
    "chunk_id",
    "corpus_chunk_index",
    "chunk_start_index_config",
    "source_kind",
    "damage_model",
    "damage_level",
    "null_model",
    "repeat_index",
    "seed",
    "token_count",
    "changed_positions",
    "changed_fraction",
    "same_positions",
    "same_fraction",
    "source_start_assumption",
]

FEATURE_FIELDS = [
    "run_label",
    "sample_id",
    "score_view_id",
    "book",
    "direction",
    "chunk_id",
    "chunk_index",
    "corpus_chunk_index",
    "chunk_start",
    "chunk_end",
    "source_kind",
    "damage_model",
    "damage_level",
    "null_model",
    "repeat_index",
    "seed",
    "start_assumption",
    "start_shift",
    "score_region",
    "score_token_count",
    "dictionary_cut",
    "ladder_profile",
    "span_length",
    "hd",
    "window_count",
    "exact_count",
    "hd_le_count",
    "matched_window_count",
    "no_match_count",
    "exact_count_norm",
    "hd_le_count_norm",
    "n_candidates_considered",
    "n_candidates_pruned_cap",
    "candidate_cap_pruned_rate",
    "score_ms",
    "backend_build_ms",
    "fingerprint_scope",
    "fast_backend_hd_policy",
    "enabled_ladder_only",
    "ladder_profile",
    "cap",
    "is_uncapped",
]

FINAL_FEATURE_NAMES = (
    "candidate_cap_pruned_rate",
    "exact_count",
    "hd_le_count",
    "matched_window_count",
    "no_match_count",
    "window_count",
    "exact_count_norm",
    "hd_le_count_norm",
)

DISTRIBUTION_FEATURE_NAMES = (
    "candidate_cap_pruned_rate",
    "exact_count_norm",
    "hd_le_count_norm",
)

INPUT_MANIFEST_FIELDS = [
    "book",
    "direction",
    "path",
    "token_count",
    "available_chunks",
    "sampled_chunks",
]

TIMING_FIELDS = [
    "checkpoint_index",
    "created_utc",
    "elapsed_s",
    "samples_done",
    "feature_rows_done",
    "chunks_done",
    "books_seen",
    "directions_seen",
    "mean_sample_score_ms_recent",
    "p95_sample_score_ms_recent",
    "samples_per_second",
    "feature_rows_per_second",
    "estimated_total_samples",
    "estimated_remaining_s_fast",
    "estimated_remaining_s_median",
    "estimated_remaining_s_slow",
]

ROLLING_FIELDS = [
    "checkpoint_index",
    "created_utc",
    "direction",
    "source_kind",
    "damage_model",
    "damage_level",
    "null_model",
    "start_assumption",
    "start_shift",
    "score_region",
    "dictionary_cut",
    "ladder_profile",
    "span_length",
    "hd",
    "feature_name",
    "count",
    "mean",
    "stddev",
    "stderr",
    "ci95_low",
    "ci95_high",
    "min",
    "max",
]

ROLLING_COMPACT_FIELDS = [
    "checkpoint_index",
    "created_utc",
    "rolling_summary_mode",
    "elapsed_s",
    "samples_done",
    "feature_rows_done",
    "chunks_done",
    "books_seen",
    "directions_seen",
    "feature_stat_group_count",
    "mean_sample_score_ms_recent",
    "p95_sample_score_ms_recent",
    "samples_per_second",
    "feature_rows_per_second",
    "estimated_total_samples",
    "estimated_remaining_s_fast",
    "estimated_remaining_s_median",
    "estimated_remaining_s_slow",
]

FEATURE_HISTOGRAM_FIELDS = [
    "direction",
    "source_kind",
    "damage_model",
    "damage_level",
    "null_model",
    "start_assumption",
    "start_shift",
    "score_region",
    "dictionary_cut",
    "ladder_profile",
    "span_length",
    "hd",
    "feature_name",
    "bin_upper",
    "count",
]

FEATURE_QUANTILE_FIELDS = [
    "direction",
    "source_kind",
    "damage_model",
    "damage_level",
    "null_model",
    "start_assumption",
    "start_shift",
    "score_region",
    "dictionary_cut",
    "ladder_profile",
    "span_length",
    "hd",
    "feature_name",
    "quantile",
    "value_upper_bound",
]

DAMAGED_VS_NULL_FIELDS = [
    "damage_model",
    "damage_level",
    "null_model",
    "dictionary_cut",
    "ladder_profile",
    "span_length",
    "hd",
    "feature_name",
    "damaged_count",
    "damaged_mean",
    "damaged_stddev",
    "null_count",
    "null_mean",
    "null_stddev",
    "mean_diff",
    "cohen_d",
]

DAMAGED_VS_NULL_BY_VIEW_FIELDS = [
    "direction",
    "start_shift",
    "score_region",
    *DAMAGED_VS_NULL_FIELDS,
]

CONVERGENCE_FIELDS = [
    "checkpoint_index",
    "created_utc",
    "threshold_chunks",
    "actual_chunks_seen",
    "direction",
    "score_region",
    "start_shift",
    "dictionary_cut",
    "ladder_profile",
    "span_length",
    "hd",
    "feature_name",
    "damage_model",
    "damage_level",
    "null_model",
    "n_chunks",
    "n_samples",
    "damaged_mean",
    "null_mean",
    "effect",
    "ci95_low",
    "ci95_high",
    "relative_change_from_previous_checkpoint",
    "sign_stability",
    "provisional_status",
]

DICTIONARY_HASH_FIELDS = [
    "dictionary_cut",
    "dictionary_path",
    "file_name",
    "span_length",
    "sha256",
    "file_bytes",
]


def verbose_rolling_summary_enabled(run_mode: str = RUN_MODE) -> bool:
    return bool(FORCE_VERBOSE_ROLLING_SUMMARY or run_mode in VERBOSE_ROLLING_SUMMARY_MODES)


def sample_change_metrics(sample: Sample) -> dict[str, Any]:
    clean = sample.clean_chunk.tokens
    tokens = sample.tokens
    compare_len = min(len(clean), len(tokens))
    same = sum(1 for idx in range(compare_len) if int(clean[idx]) == int(tokens[idx]))
    denominator = max(len(clean), len(tokens))
    changed = denominator - same
    if denominator <= 0:
        return {
            "changed_positions": 0,
            "changed_fraction": "0",
            "same_positions": 0,
            "same_fraction": "0",
        }
    return {
        "changed_positions": changed,
        "changed_fraction": f"{changed / float(denominator):.12g}",
        "same_positions": same,
        "same_fraction": f"{same / float(denominator):.12g}",
    }


def _sample_row(sample: Sample) -> dict[str, Any]:
    change_metrics = sample_change_metrics(sample)
    return {
        "run_label": RUN_LABEL,
        "sample_id": sample.sample_id,
        "book": sample.clean_chunk.book,
        "direction": sample.clean_chunk.direction,
        "chunk_id": sample.clean_chunk.chunk_id,
        "corpus_chunk_index": sample.clean_chunk.corpus_chunk_index,
        "chunk_start_index_config": CHUNK_START_INDEX,
        "source_kind": sample.source_kind,
        "damage_model": sample.damage_model,
        "damage_level": sample.damage_level,
        "null_model": sample.null_model,
        "repeat_index": sample.repeat_index,
        "seed": sample.seed,
        "token_count": len(sample.tokens),
        **change_metrics,
        "source_start_assumption": sample.clean_chunk.source_start_assumption,
    }


def _feature_stat_key(row: Mapping[str, Any], feature_name: str) -> tuple[Any, ...]:
    return (
        row["direction"],
        row["source_kind"],
        row["damage_model"],
        row["damage_level"],
        row["null_model"],
        row["start_assumption"],
        int(row["start_shift"]),
        row["score_region"],
        row["dictionary_cut"],
        int(row["span_length"]),
        int(row["hd"]),
        feature_name,
    )


def _feature_stat_key_to_extra(key: tuple[Any, ...]) -> dict[str, Any]:
    (
        direction,
        source_kind,
        damage_model,
        damage_level,
        null_model,
        start_assumption,
        start_shift,
        score_region,
        dictionary_cut,
        span_length,
        hd,
        feature_name,
    ) = key
    return {
        "direction": direction,
        "source_kind": source_kind,
        "damage_model": damage_model,
        "damage_level": damage_level,
        "null_model": null_model,
        "start_assumption": start_assumption,
        "start_shift": start_shift,
        "score_region": score_region,
        "dictionary_cut": dictionary_cut,
        "ladder_profile": LADDER_PROFILE,
        "span_length": span_length,
        "hd": hd,
        "feature_name": feature_name,
    }


def update_feature_stats(stats: dict[tuple[Any, ...], RunningStat], rows: Sequence[Mapping[str, Any]]) -> None:
    for row in rows:
        for feature_name in FINAL_FEATURE_NAMES:
            value = float(row[feature_name])
            key = _feature_stat_key(row, feature_name)
            stats.setdefault(key, RunningStat()).update(value)


def update_feature_histograms(stats: dict[tuple[Any, ...], HistogramStat], rows: Sequence[Mapping[str, Any]]) -> None:
    for row in rows:
        for feature_name in DISTRIBUTION_FEATURE_NAMES:
            value = float(row[feature_name])
            key = _feature_stat_key(row, feature_name)
            stats.setdefault(key, HistogramStat.create()).update(value)


def rolling_summary_rows(
    *,
    checkpoint_index: int,
    created_utc: str,
    stats: Mapping[tuple[Any, ...], RunningStat],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, stat in sorted(stats.items(), key=lambda item: tuple(str(x) for x in item[0])):
        rows.append(
            stat.row(
                {
                    "checkpoint_index": checkpoint_index,
                    "created_utc": created_utc,
                    **_feature_stat_key_to_extra(key),
                }
            )
        )
    return rows


def feature_histogram_rows(stats: Mapping[tuple[Any, ...], HistogramStat]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, stat in sorted(stats.items(), key=lambda item: tuple(str(x) for x in item[0])):
        extra = _feature_stat_key_to_extra(key)
        for idx, bin_count in enumerate(stat.bins):
            rows.append(
                {
                    **extra,
                    "bin_upper": f"{HISTOGRAM_BINS[idx]:.12g}",
                    "count": int(bin_count),
                }
            )
    return rows


def feature_quantile_rows(stats: Mapping[tuple[Any, ...], HistogramStat]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, stat in sorted(stats.items(), key=lambda item: tuple(str(x) for x in item[0])):
        extra = _feature_stat_key_to_extra(key)
        for q in QUANTILE_LEVELS:
            rows.append(
                {
                    **extra,
                    "quantile": f"{q:.2f}",
                    "value_upper_bound": f"{stat.quantile_upper_bound(q):.12g}",
                }
            )
    return rows


@dataclass
class StatAggregate:
    count: int = 0
    sum_value: float = 0.0
    sum_square: float = 0.0

    def add(self, stat: RunningStat) -> None:
        if stat.count <= 0:
            return
        self.count += stat.count
        self.sum_value += stat.mean * float(stat.count)
        self.sum_square += stat.m2 + float(stat.count) * stat.mean * stat.mean

    @property
    def mean(self) -> float:
        return self.sum_value / float(self.count) if self.count else 0.0

    @property
    def stddev(self) -> float:
        if self.count < 2:
            return 0.0
        variance = (self.sum_square - float(self.count) * self.mean * self.mean) / float(self.count - 1)
        return math.sqrt(max(0.0, variance))


def _pooled_cohen_d(left: StatAggregate, right: StatAggregate) -> float:
    if left.count <= 0 or right.count <= 0:
        return 0.0
    denom_n = left.count + right.count - 2
    if denom_n <= 0:
        return 0.0
    pooled_var = (
        float(left.count - 1) * left.stddev * left.stddev
        + float(right.count - 1) * right.stddev * right.stddev
    ) / float(denom_n)
    pooled = math.sqrt(max(0.0, pooled_var))
    if pooled <= 1e-12:
        return 0.0
    return (left.mean - right.mean) / pooled


def damaged_vs_null_summary_rows(
    stats: Mapping[tuple[Any, ...], RunningStat],
    *,
    include_view: bool = False,
) -> list[dict[str, Any]]:
    damaged: dict[tuple[Any, ...], StatAggregate] = {}
    nulls: dict[tuple[Any, ...], StatAggregate] = {}
    damage_groups: set[tuple[str, str]] = set()
    null_models: set[str] = set()

    for key, stat in stats.items():
        extra = _feature_stat_key_to_extra(key)
        view_key = (
            extra["direction"],
            int(extra["start_shift"]),
            extra["score_region"],
        )
        family_key = (
            extra["dictionary_cut"],
            int(extra["span_length"]),
            int(extra["hd"]),
            extra["feature_name"],
        )
        group_key = (*view_key, *family_key) if include_view else family_key
        source_kind = str(extra["source_kind"])
        if source_kind == "damaged":
            damage_model = str(extra["damage_model"])
            damage_level = str(extra["damage_level"])
            damage_groups.add((damage_model, damage_level))
            damaged_key = (damage_model, damage_level, *group_key)
            damaged.setdefault(damaged_key, StatAggregate()).add(stat)
        elif source_kind == "null":
            null_model = str(extra["null_model"])
            null_models.add(null_model)
            null_key = (null_model, *group_key)
            nulls.setdefault(null_key, StatAggregate()).add(stat)

    rows: list[dict[str, Any]] = []
    family_keys = sorted(
        {
            key[2:]
            for key in damaged
        }
        | {
            key[1:]
            for key in nulls
        },
        key=lambda item: tuple(str(x) for x in item),
    )
    for damage_model, damage_level in sorted(damage_groups):
        for null_model in sorted(null_models):
            for family_key in family_keys:
                dstat = damaged.get((damage_model, damage_level, *family_key), StatAggregate())
                nstat = nulls.get((null_model, *family_key), StatAggregate())
                if include_view:
                    direction, start_shift, score_region, dictionary_cut, span_length, hd, feature_name = family_key
                    view_extra = {
                        "direction": direction,
                        "start_shift": start_shift,
                        "score_region": score_region,
                    }
                else:
                    dictionary_cut, span_length, hd, feature_name = family_key
                    view_extra = {}
                rows.append(
                    {
                        **view_extra,
                        "damage_model": damage_model,
                        "damage_level": damage_level,
                        "null_model": null_model,
                        "dictionary_cut": dictionary_cut,
                        "ladder_profile": LADDER_PROFILE,
                        "span_length": span_length,
                        "hd": hd,
                        "feature_name": feature_name,
                        "damaged_count": dstat.count,
                        "damaged_mean": f"{dstat.mean:.12g}",
                        "damaged_stddev": f"{dstat.stddev:.12g}",
                        "null_count": nstat.count,
                        "null_mean": f"{nstat.mean:.12g}",
                        "null_stddev": f"{nstat.stddev:.12g}",
                        "mean_diff": f"{dstat.mean - nstat.mean:.12g}",
                        "cohen_d": f"{_pooled_cohen_d(dstat, nstat):.12g}",
                    }
                )
    return rows


def top_damaged_vs_null_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int = 12,
    feature_names: Sequence[str] | None = None,
) -> list[Mapping[str, Any]]:
    allowed = set(feature_names) if feature_names is not None else None
    filtered = [row for row in rows if allowed is None or str(row["feature_name"]) in allowed]
    return sorted(filtered, key=lambda row: abs(float(row["cohen_d"])), reverse=True)[:limit]


def dictionary_hash_manifest_rows(dictionary_specs: Sequence[DictionarySpec]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in dictionary_specs:
        dictionary_dir = REPO_ROOT / spec.dictionary_path
        for length in SPAN_LENGTHS:
            path = dictionary_dir / f"raw1grams_{length:02d}.csv"
            if not path.exists():
                raise FileNotFoundError(f"Dictionary file missing: {_repo_rel(path)}")
            rows.append(
                {
                    "dictionary_cut": spec.dictionary_cut,
                    "dictionary_path": spec.dictionary_path,
                    "file_name": path.name,
                    "span_length": length,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "file_bytes": path.stat().st_size,
                }
            )
    return rows


def _mean_diff_ci95(damaged_stddev: float, damaged_count: int, null_stddev: float, null_count: int) -> float:
    damaged_var = (damaged_stddev * damaged_stddev) / float(max(1, damaged_count))
    null_var = (null_stddev * null_stddev) / float(max(1, null_count))
    return 1.96 * math.sqrt(max(0.0, damaged_var + null_var))


def _relative_effect_change(previous: float | None, current: float) -> str:
    if previous is None:
        return ""
    if abs(previous) <= 1e-12:
        return "" if abs(current) <= 1e-12 else "inf"
    return f"{(current - previous) / abs(previous):.12g}"


def _effect_sign(value: float) -> int:
    if value > 1e-12:
        return 1
    if value < -1e-12:
        return -1
    return 0


def _provisional_status(effect: float, sign_stability: str) -> str:
    abs_effect = abs(effect)
    if abs_effect < 0.05:
        return "converged_noisy"
    if abs_effect >= 0.20 and sign_stability in {"same", "initial"}:
        return "converged_positive"
    if sign_stability == "changed":
        return "needs_more_data"
    return "active"


def convergence_summary_rows(
    *,
    checkpoint_index: int,
    created_utc: str,
    threshold_chunks: int,
    actual_chunks_seen: int,
    stats: Mapping[tuple[Any, ...], RunningStat],
    previous_effects: Mapping[tuple[Any, ...], float],
) -> tuple[list[dict[str, Any]], dict[tuple[Any, ...], float]]:
    current_effects: dict[tuple[Any, ...], float] = {}
    rows: list[dict[str, Any]] = []
    for row in damaged_vs_null_summary_rows(stats, include_view=True):
        effect = float(row["cohen_d"])
        mean_diff = float(row["mean_diff"])
        damaged_count = int(row["damaged_count"])
        null_count = int(row["null_count"])
        ci = _mean_diff_ci95(
            float(row["damaged_stddev"]),
            damaged_count,
            float(row["null_stddev"]),
            null_count,
        )
        key = (
            row["direction"],
            row["score_region"],
            int(row["start_shift"]),
            row["dictionary_cut"],
            row["ladder_profile"],
            int(row["span_length"]),
            int(row["hd"]),
            row["feature_name"],
            row["damage_model"],
            row["damage_level"],
            row["null_model"],
        )
        previous = previous_effects.get(key)
        if previous is None:
            sign_stability = "initial"
        elif _effect_sign(previous) == _effect_sign(effect):
            sign_stability = "same"
        else:
            sign_stability = "changed"
        current_effects[key] = effect
        rows.append(
            {
                "checkpoint_index": checkpoint_index,
                "created_utc": created_utc,
                "threshold_chunks": threshold_chunks,
                "actual_chunks_seen": actual_chunks_seen,
                "direction": row["direction"],
                "score_region": row["score_region"],
                "start_shift": row["start_shift"],
                "dictionary_cut": row["dictionary_cut"],
                "ladder_profile": row["ladder_profile"],
                "span_length": row["span_length"],
                "hd": row["hd"],
                "feature_name": row["feature_name"],
                "damage_model": row["damage_model"],
                "damage_level": row["damage_level"],
                "null_model": row["null_model"],
                "n_chunks": actual_chunks_seen,
                "n_samples": damaged_count + null_count,
                "damaged_mean": row["damaged_mean"],
                "null_mean": row["null_mean"],
                "effect": f"{effect:.12g}",
                "ci95_low": f"{mean_diff - ci:.12g}",
                "ci95_high": f"{mean_diff + ci:.12g}",
                "relative_change_from_previous_checkpoint": _relative_effect_change(previous, effect),
                "sign_stability": sign_stability,
                "provisional_status": _provisional_status(effect, sign_stability),
            }
        )
    return rows, current_effects


def _estimate_remaining(samples_done: int, estimated_total_samples: int, speeds: Sequence[float]) -> tuple[float, float, float]:
    remaining = max(0, estimated_total_samples - samples_done)
    good_speeds = [s for s in speeds if s > 0.0]
    if not good_speeds:
        return 0.0, 0.0, 0.0
    fast = max(good_speeds)
    median_speed = sorted(good_speeds)[len(good_speeds) // 2]
    slow = min(good_speeds)
    return remaining / fast, remaining / median_speed, remaining / slow


# =============================================================================
# Self tests
# =============================================================================


def run_self_tests() -> None:
    tokens = tuple(range(29)) * 18
    tokens = tokens[:CHUNK_SIZE]
    wli = tuple((i % 5, 5) for i in range(CHUNK_SIZE))
    global_probs = np.ones(29, dtype=np.float64) / 29.0
    book_probs = _empirical_probs(tokens)
    dummy = CleanChunk(
        book="self_test",
        direction="fwd",
        chunk_index=0,
        chunk_start=0,
        chunk_end=len(tokens),
        tokens=tokens,
        wli=wli,
    )
    for model in (
        "independent_substitution",
        "frequency_matched_global",
        "frequency_matched_book",
        "word_local_substitution",
        "burst_substitution",
        "lane_period_substitution",
    ):
        a = make_sample(
            clean_chunk=dummy,
            source_kind="damaged",
            damage_model=model,
            damage_level="0.40",
            null_model="",
            repeat_index=0,
            global_probs=global_probs,
            book_probs=book_probs,
        )
        b = make_sample(
            clean_chunk=dummy,
            source_kind="damaged",
            damage_model=model,
            damage_level="0.40",
            null_model="",
            repeat_index=0,
            global_probs=global_probs,
            book_probs=book_probs,
        )
        assert a.tokens == b.tokens, model
        assert len(a.tokens) == len(tokens), model
        assert min(a.tokens) >= 0 and max(a.tokens) <= 28, model
    for model in (
        "uniform_random",
        "global_frequency_random",
        "within_chunk_shuffle",
        "block_shuffle_25",
    ):
        a = make_sample(
            clean_chunk=dummy,
            source_kind="null",
            damage_model="",
            damage_level="",
            null_model=model,
            repeat_index=0,
            global_probs=global_probs,
            book_probs=book_probs,
        )
        b = make_sample(
            clean_chunk=dummy,
            source_kind="null",
            damage_model="",
            damage_level="",
            null_model=model,
            repeat_index=0,
            global_probs=global_probs,
            book_probs=book_probs,
        )
        assert a.tokens == b.tokens, model
        assert len(a.tokens) == len(tokens), model
        assert min(a.tokens) >= 0 and max(a.tokens) <= 28, model
    print("[self_tests] passed", flush=True)


# =============================================================================
# Main run
# =============================================================================


def _config_payload(tokenized_root: Path, output_dir: Path) -> dict[str, Any]:
    return {
        "run_label": RUN_LABEL,
        "run_mode": RUN_MODE,
        "book_order": BOOK_ORDER,
        "book_skip": BOOK_SKIP,
        "book_list_file": BOOK_LIST_FILE_REL,
        "chunk_start_index": CHUNK_START_INDEX,
        "exclude_books": list(EXCLUDE_BOOKS),
        "tokenized_root": _repo_rel(tokenized_root),
        "output_dir": _repo_rel(output_dir),
        "directions": list(directions_for_mode(RUN_MODE)),
        "all_available_directions": list(DIRECTIONS),
        "chunk_max_tokens": CHUNK_MAX_TOKENS,
        "num_clean_chunks_configured": int(_mode_limits().get("num_clean_chunks", 0) or 0),
        "num_clean_chunks_this_run_configured": int(_mode_limits().get("num_clean_chunks", 0) or 0),
        "global_seed": GLOBAL_SEED,
        "default_start_assumption": DEFAULT_START_ASSUMPTION,
        "source_start_assumption": SOURCE_START_ASSUMPTION,
        "score_regions": list(score_regions_for_mode(RUN_MODE)),
        "all_available_score_regions": list(SCORE_REGIONS),
        "start_view_shifts": list(start_view_shifts_for_mode(RUN_MODE)),
        **ladder_profile_payload(),
        "span_lengths": list(SPAN_LENGTHS),
        "max_hd_by_length": MAX_HD_BY_LENGTH,
        "fingerprint_max_candidates_per_window": FINGERPRINT_MAX_CANDIDATES_PER_WINDOW,
        "dictionary_specs": list(DICTIONARY_SPECS),
        "mode_limits": dict(_mode_limits()),
        "verbose_rolling_summary_enabled": verbose_rolling_summary_enabled(RUN_MODE),
        "write_raw_feature_rows": write_raw_feature_rows_enabled(RUN_MODE),
        "write_feature_histograms": write_feature_histograms_enabled(RUN_MODE),
        "write_feature_quantiles": write_feature_quantiles_enabled(RUN_MODE),
        "force_verbose_rolling_summary": FORCE_VERBOSE_ROLLING_SUMMARY,
        "verbose_rolling_summary_modes": list(VERBOSE_ROLLING_SUMMARY_MODES),
        "report_only": True,
        "nose_only": True,
        "runtime_solver_change": False,
    }


def _machine_payload() -> dict[str, Any]:
    try:
        affinity = len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
    except Exception:
        affinity = None
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_logical": os.cpu_count(),
        "cpu_affinity": affinity,
    }


def estimate_total_samples(clean_chunk_count: int, limits: Mapping[str, Any]) -> int:
    damaged_per_chunk = (
        int(limits["damage_repeats_per_chunk"])
        * len(tuple(limits["damage_levels"]))
        * len(tuple(limits["include_damage_models"]))
    )
    null_per_chunk = int(limits["damage_repeats_per_chunk"]) * len(tuple(limits["include_null_models"]))
    clean_per_chunk = 1
    return clean_chunk_count * (clean_per_chunk + damaged_per_chunk + null_per_chunk)


def ladder_row_count_per_dictionary() -> int:
    return sum(MAX_HD_BY_LENGTH[length] + 1 for length in SPAN_LENGTHS)


def score_views_per_sample_for_mode(run_mode: str) -> int:
    return len(start_view_shifts_for_mode(run_mode)) * len(score_regions_for_mode(run_mode))


def estimate_feature_rows(clean_chunk_count: int, limits: Mapping[str, Any], *, run_mode: str = RUN_MODE) -> int:
    return (
        estimate_total_samples(clean_chunk_count, limits)
        * score_views_per_sample_for_mode(run_mode)
        * len(DICTIONARY_SPECS)
        * ladder_row_count_per_dictionary()
    )


def estimate_output_shape(
    *,
    selected_books: int,
    clean_chunk_count: int,
    limits: Mapping[str, Any],
    run_mode: str = RUN_MODE,
) -> dict[str, Any]:
    samples = estimate_total_samples(clean_chunk_count, limits)
    score_views = score_views_per_sample_for_mode(run_mode)
    return {
        "selected_books": selected_books,
        "num_clean_chunks": clean_chunk_count,
        "num_clean_chunks_this_run": clean_chunk_count,
        "chunks": clean_chunk_count,
        "chunk_max_tokens": CHUNK_MAX_TOKENS,
        "samples": samples,
        "regions": list(score_regions_for_mode(run_mode)),
        "start_view_shifts": list(start_view_shifts_for_mode(run_mode)),
        "score_views_per_sample": score_views,
        "dictionary_cuts": len(DICTIONARY_SPECS),
        "ladder_rows_per_dictionary": ladder_row_count_per_dictionary(),
        "total_feature_rows": estimate_feature_rows(clean_chunk_count, limits, run_mode=run_mode),
    }


def nominal_clean_chunk_count_for_limits(limits: Mapping[str, Any], *, run_mode: str = RUN_MODE) -> int:
    configured = int(limits.get("num_clean_chunks", 0) or 0)
    if configured > 0:
        return configured
    return int(limits["max_books"]) * len(directions_for_mode(run_mode)) * int(limits["chunks_per_book_direction"])


def _file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def _projected_run_estimates(
    *,
    output_dir: Path,
    elapsed_s: float,
    samples_done: int,
    feature_rows_done: int,
    checkpoint_count: int,
) -> dict[str, Any]:
    feature_bytes = _file_size(output_dir / "feature_rows.csv")
    rolling_bytes = _file_size(output_dir / "rolling_feature_summary.csv")
    timing_bytes = _file_size(output_dir / "timing_checkpoints.csv")
    final_feature_summary_bytes = _file_size(output_dir / "final_feature_summary.csv")
    histogram_bytes = _file_size(output_dir / FEATURE_HISTOGRAMS_NAME)
    quantile_bytes = _file_size(output_dir / FEATURE_QUANTILES_NAME)
    damaged_vs_null_bytes = _file_size(output_dir / DAMAGED_VS_NULL_SUMMARY_NAME)
    damaged_vs_null_by_view_bytes = _file_size(output_dir / DAMAGED_VS_NULL_BY_VIEW_NAME)
    feature_bytes_per_row = feature_bytes / float(max(1, feature_rows_done))
    rolling_bytes_per_checkpoint = rolling_bytes / float(max(1, checkpoint_count))
    compact_bytes_per_checkpoint = timing_bytes / float(max(1, checkpoint_count))
    samples_per_second = samples_done / max(1e-9, elapsed_s)

    full_limits = MODE_LIMITS["full"]
    full_chunks = nominal_clean_chunk_count_for_limits(full_limits)
    full_shape = estimate_output_shape(
        selected_books=int(full_limits["max_books"]),
        clean_chunk_count=full_chunks,
        limits=full_limits,
        run_mode="full",
    )
    full_samples = int(full_shape["samples"])
    full_feature_rows = int(full_shape["total_feature_rows"])
    full_checkpoints = max(1, math.ceil(full_samples / int(full_limits["checkpoint_every_samples"])) + 1)
    mode_projections: dict[str, dict[str, Any]] = {}
    samples_per_second = samples_done / max(1e-9, elapsed_s)
    feature_rows_per_second = feature_rows_done / max(1e-9, elapsed_s)
    for mode_name in ("stage0_fwd_full_canary", "stage1_fwd_full_1k", "medium_summary_500", "medium_summary_1000", "full"):
        mode_limits = MODE_LIMITS[mode_name]
        mode_chunks = num_clean_chunks_for_limits(mode_limits)
        mode_shape = estimate_output_shape(
            selected_books=int(mode_limits["max_books"]),
            clean_chunk_count=mode_chunks,
            limits=mode_limits,
            run_mode=mode_name,
        )
        mode_samples = int(mode_shape["samples"])
        mode_feature_rows = int(mode_shape["total_feature_rows"])
        mode_projections[mode_name] = {
            "num_clean_chunks": mode_chunks,
            "samples": mode_samples,
            "feature_row_equivalents": mode_feature_rows,
            "runtime_s_by_sample_throughput": mode_samples / max(1e-9, samples_per_second),
            "runtime_s_by_feature_row_throughput": mode_feature_rows / max(1e-9, feature_rows_per_second),
        }

    return {
        "observed_feature_rows_csv_bytes": feature_bytes,
        "observed_rolling_feature_summary_csv_bytes": rolling_bytes,
        "observed_timing_checkpoints_csv_bytes": timing_bytes,
        "observed_final_feature_summary_csv_bytes": final_feature_summary_bytes,
        "observed_feature_histograms_csv_bytes": histogram_bytes,
        "observed_feature_quantiles_csv_bytes": quantile_bytes,
        "observed_damaged_vs_null_summary_csv_bytes": damaged_vs_null_bytes,
        "observed_damaged_vs_null_by_view_csv_gz_bytes": damaged_vs_null_by_view_bytes,
        "feature_row_bytes_per_row": feature_bytes_per_row,
        "rolling_bytes_per_checkpoint_observed": rolling_bytes_per_checkpoint,
        "compact_rolling_bytes_per_checkpoint_estimate": compact_bytes_per_checkpoint,
        "observed_samples_per_second": samples_per_second,
        "observed_feature_rows_per_second": feature_rows_done / max(1e-9, elapsed_s),
        "nominal_full_num_clean_chunks": full_chunks,
        "nominal_full_samples": full_samples,
        "nominal_full_feature_rows": full_feature_rows,
        "nominal_full_feature_rows_csv_bytes_projected": full_feature_rows * feature_bytes_per_row,
        "nominal_full_compact_rolling_summary_csv_bytes_projected": full_checkpoints * compact_bytes_per_checkpoint,
        "nominal_full_runtime_s_projected": full_samples / max(1e-9, samples_per_second),
        "nominal_full_checkpoints_projected": full_checkpoints,
        "mode_runtime_projections": mode_projections,
    }


def run_once() -> dict[str, Any]:
    if RUN_SELF_TESTS:
        run_self_tests()
    if not fast_span_hamming_available():
        raise RuntimeError(
            "optional _span_hamming_fast extension is not built; "
            "build it before running this benchmark"
        )

    limits = _mode_limits()
    tokenized_root = _resolve_from_repo_root(TOKENIZED_ROOT_REL)
    output_dir = _resolve_from_repo_root(OUTPUT_DIR_REL)
    _require_output_under_repo(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale_name in (
        "run_state.json",
        "final_summary.json",
        "readout.md",
        "feature_rows.csv",
        "feature_histograms.csv",
        FEATURE_HISTOGRAMS_NAME,
        "feature_quantiles.csv",
        FEATURE_QUANTILES_NAME,
        DAMAGED_VS_NULL_SUMMARY_NAME,
        DAMAGED_VS_NULL_BY_VIEW_NAME,
        CONVERGENCE_SUMMARY_NAME,
        DICTIONARY_HASH_MANIFEST_NAME,
    ):
        stale_path = output_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()

    if not tokenized_root.exists():
        raise FileNotFoundError(f"TOKENIZED_ROOT not found: {_repo_rel(tokenized_root)}")

    started_wall = time.perf_counter()
    started_utc = _utc_now()

    config = _config_payload(tokenized_root, output_dir)
    _safe_json_write(output_dir / "config.json", config)
    _safe_json_write(
        output_dir / "run_manifest.json",
        {
            "run_label": RUN_LABEL,
            "status": "running",
            "started_at_utc": started_utc,
            "repo_root": ".",
            "machine": _machine_payload(),
            "config": config,
        },
    )
    _safe_json_write(
        output_dir / "run_state.json",
        {
            "run_label": RUN_LABEL,
            "status": "starting",
            "checkpoint_index": 0,
            "samples_done": 0,
            "estimated_total_samples": 0,
            "elapsed_s": 0.0,
            "estimated_remaining_s_median": 0.0,
            "feature_rows_done": 0,
            "chunk_start_index": CHUNK_START_INDEX,
            "num_clean_chunks_this_run_configured": int(limits.get("num_clean_chunks", 0) or 0),
            "updated_at_utc": started_utc,
        },
    )

    for path, fields in (
        (output_dir / "input_manifest.csv", INPUT_MANIFEST_FIELDS),
        (output_dir / "sample_rows.csv", SAMPLE_FIELDS),
        (output_dir / "timing_checkpoints.csv", TIMING_FIELDS),
        (output_dir / "final_feature_summary.csv", ROLLING_FIELDS),
        (output_dir / CONVERGENCE_SUMMARY_NAME, CONVERGENCE_FIELDS),
    ):
        _write_csv_header(path, fields)
    if write_raw_feature_rows_enabled(RUN_MODE):
        _write_csv_header(output_dir / "feature_rows.csv", FEATURE_FIELDS)
    rolling_fields = ROLLING_FIELDS if verbose_rolling_summary_enabled(RUN_MODE) else ROLLING_COMPACT_FIELDS
    _write_csv_header(output_dir / "rolling_feature_summary.csv", rolling_fields)

    discovered = discover_tokenized_files(tokenized_root)
    selected_books = select_books(discovered, max_books=int(limits["max_books"]))
    rows_by_book_direction = {(book, direction): path for book, direction, path in discovered}
    active_directions = directions_for_mode(RUN_MODE)
    selected_rows = [
        (book, direction, rows_by_book_direction[(book, direction)])
        for book in selected_books
        for direction in active_directions
        if (book, direction) in rows_by_book_direction
    ]
    if not selected_rows:
        raise RuntimeError(f"No tokenized fwd/rev files selected under {_repo_rel(tokenized_root)}")

    # Load selected book/directions once. This keeps smoke/pilot simple and lets
    # us compute a global empirical rune distribution for frequency nulls.
    loaded: list[TokenizedBookDirection] = []
    for book, direction, path in selected_rows:
        loaded.append(load_tokenized_nose(book, direction, path))

    non_empty_token_arrays = [row.tokens for row in loaded if row.tokens.size]
    if not non_empty_token_arrays:
        raise RuntimeError("Selected tokenized files contained no NOSE tokens")
    global_token_pool = np.concatenate(non_empty_token_arrays)
    global_probs = _empirical_probs(global_token_pool)
    book_probs_by_key = {(row.book, row.direction): _empirical_probs(row.tokens) for row in loaded}

    num_clean_chunks_target = int(limits.get("num_clean_chunks", 0) or 0)
    chunk_start_index = max(0, int(CHUNK_START_INDEX))
    chunk_stop_index = chunk_start_index + num_clean_chunks_target if num_clean_chunks_target > 0 else None
    clean_chunks: list[CleanChunk] = []
    corpus_chunk_index = 0
    stop_reached = False
    for book_dir in loaded:
        chunks = build_clean_chunks(book_dir, chunks_per_book_direction=int(limits["chunks_per_book_direction"]))
        for chunk in chunks:
            if corpus_chunk_index >= chunk_start_index and (
                chunk_stop_index is None or corpus_chunk_index < chunk_stop_index
            ):
                clean_chunks.append(replace(chunk, corpus_chunk_index=corpus_chunk_index))
            corpus_chunk_index += 1
            if chunk_stop_index is not None and corpus_chunk_index >= chunk_stop_index:
                stop_reached = True
                break
        if stop_reached:
            break
    input_manifest_rows = input_manifest_rows_for_used_chunks(loaded, clean_chunks)
    _append_csv_rows(output_dir / "input_manifest.csv", input_manifest_rows, INPUT_MANIFEST_FIELDS)

    if not clean_chunks:
        raise RuntimeError("Selected tokenized books produced no source-word-bounded NOSE chunks")

    estimated_total = estimate_total_samples(len(clean_chunks), limits)
    output_shape = estimate_output_shape(
        selected_books=len(selected_books),
        clean_chunk_count=len(clean_chunks),
        limits=limits,
        run_mode=RUN_MODE,
    )

    first_chunk_id = clean_chunks[0].chunk_id if clean_chunks else ""
    last_chunk_id = clean_chunks[-1].chunk_id if clean_chunks else ""
    next_chunk_start_index = chunk_start_index + len(clean_chunks)

    dictionary_specs = [DictionarySpec(**spec) for spec in DICTIONARY_SPECS]
    _write_csv_rows(
        output_dir / DICTIONARY_HASH_MANIFEST_NAME,
        dictionary_hash_manifest_rows(dictionary_specs),
        DICTIONARY_HASH_FIELDS,
    )
    backends: dict[str, FastSpanHammingBackend] = {}
    backend_build_ms: dict[str, float] = {}
    for spec in dictionary_specs:
        print(f"[{RUN_LABEL}] building backend dictionary_cut={spec.dictionary_cut}", flush=True)
        t0 = time.perf_counter()
        backends[spec.dictionary_cut] = build_backend(spec)
        backend_build_ms[spec.dictionary_cut] = (time.perf_counter() - t0) * 1000.0
        print(
            f"[{RUN_LABEL}] backend ready dictionary_cut={spec.dictionary_cut} "
            f"elapsed_ms={backend_build_ms[spec.dictionary_cut]:.1f}",
            flush=True,
        )

    feature_stats: dict[tuple[Any, ...], RunningStat] = {}
    feature_histograms: dict[tuple[Any, ...], HistogramStat] = {}
    recent_sample_ms: list[float] = []
    checkpoint_speeds: list[float] = []
    samples_done = 0
    feature_rows_done = 0
    checkpoint_index = 0
    last_checkpoint_at = time.perf_counter()
    books_seen: set[str] = set()
    directions_seen: set[str] = set()
    chunks_seen: set[str] = set()
    convergence_previous_effects: dict[tuple[Any, ...], float] = {}
    convergence_written_thresholds: set[int] = set()

    def write_checkpoint(force: bool = False) -> None:
        nonlocal checkpoint_index, last_checkpoint_at
        now = time.perf_counter()
        if not force:
            if samples_done == 0:
                return
            sample_gap_ok = samples_done % int(limits["checkpoint_every_samples"]) == 0
            time_gap_ok = (now - last_checkpoint_at) >= float(limits["checkpoint_every_seconds"])
            if not sample_gap_ok and not time_gap_ok:
                return
        checkpoint_index += 1
        created = _utc_now()
        elapsed = now - started_wall
        speed = samples_done / max(1e-9, elapsed)
        checkpoint_speeds.append(speed)
        remain_fast, remain_med, remain_slow = _estimate_remaining(samples_done, estimated_total, checkpoint_speeds)
        timing_row = {
            "checkpoint_index": checkpoint_index,
            "created_utc": created,
            "elapsed_s": f"{elapsed:.6f}",
            "samples_done": samples_done,
            "feature_rows_done": feature_rows_done,
            "chunks_done": len(chunks_seen),
            "books_seen": len(books_seen),
            "directions_seen": len(directions_seen),
            "mean_sample_score_ms_recent": f"{mean(recent_sample_ms):.6f}" if recent_sample_ms else "",
            "p95_sample_score_ms_recent": f"{_percentile(recent_sample_ms, 0.95):.6f}" if recent_sample_ms else "",
            "samples_per_second": f"{speed:.12g}",
            "feature_rows_per_second": f"{feature_rows_done / max(1e-9, elapsed):.12g}",
            "estimated_total_samples": estimated_total,
            "estimated_remaining_s_fast": f"{remain_fast:.6f}",
            "estimated_remaining_s_median": f"{remain_med:.6f}",
            "estimated_remaining_s_slow": f"{remain_slow:.6f}",
        }
        _append_csv_rows(output_dir / "timing_checkpoints.csv", [timing_row], TIMING_FIELDS)
        if verbose_rolling_summary_enabled(RUN_MODE):
            _append_csv_rows(
                output_dir / "rolling_feature_summary.csv",
                rolling_summary_rows(checkpoint_index=checkpoint_index, created_utc=created, stats=feature_stats),
                ROLLING_FIELDS,
            )
        else:
            _append_csv_rows(
                output_dir / "rolling_feature_summary.csv",
                [
                    {
                        **timing_row,
                        "rolling_summary_mode": "compact_checkpoint",
                        "feature_stat_group_count": len(feature_stats),
                    }
                ],
                ROLLING_COMPACT_FIELDS,
            )
        _safe_json_write(
            output_dir / "run_state.json",
            {
                "run_label": RUN_LABEL,
                "status": "running",
                "checkpoint_index": checkpoint_index,
                "samples_done": samples_done,
                "estimated_total_samples": estimated_total,
                "elapsed_s": elapsed,
                "estimated_remaining_s_median": remain_med,
                "feature_rows_done": feature_rows_done,
                "chunk_start_index": chunk_start_index,
                "num_clean_chunks_this_run": len(clean_chunks),
                "actual_chunks_used": len(chunks_seen),
                "first_chunk_id": first_chunk_id,
                "last_chunk_id": last_chunk_id,
                "next_chunk_start_index": next_chunk_start_index,
                "updated_at_utc": created,
            },
        )
        last_checkpoint_at = now
        print(
            f"[{RUN_LABEL}] checkpoint {checkpoint_index}: samples={samples_done}/{estimated_total} "
            f"elapsed={elapsed:.1f}s median_eta={remain_med:.1f}s rows={feature_rows_done}",
            flush=True,
        )

    def write_convergence_checkpoint(threshold_chunks: int) -> None:
        nonlocal convergence_previous_effects
        if threshold_chunks in convergence_written_thresholds:
            return
        created = _utc_now()
        rows, convergence_previous_effects = convergence_summary_rows(
            checkpoint_index=checkpoint_index,
            created_utc=created,
            threshold_chunks=threshold_chunks,
            actual_chunks_seen=len(chunks_seen),
            stats=feature_stats,
            previous_effects=convergence_previous_effects,
        )
        _append_csv_rows(output_dir / CONVERGENCE_SUMMARY_NAME, rows, CONVERGENCE_FIELDS)
        convergence_written_thresholds.add(threshold_chunks)
        print(
            f"[{RUN_LABEL}] convergence threshold={threshold_chunks} "
            f"chunks_seen={len(chunks_seen)} rows={len(rows)}",
            flush=True,
        )

    print(
        f"[{RUN_LABEL}] starting mode={RUN_MODE} books={len(selected_books)} "
        f"CHUNK_MAX_TOKENS={CHUNK_MAX_TOKENS} NUM_CLEAN_CHUNKS_THIS_RUN={len(clean_chunks)} "
        f"estimated_samples={estimated_total} estimated_feature_rows={output_shape['total_feature_rows']}",
        flush=True,
    )
    print(f"[{RUN_LABEL}] output_shape={json.dumps(output_shape, sort_keys=True)}", flush=True)

    for clean_chunk in clean_chunks:
        book_probs = book_probs_by_key[(clean_chunk.book, clean_chunk.direction)]
        for sample in iter_samples_for_chunk(clean_chunk, global_probs=global_probs, book_probs=book_probs, limits=limits):
            sample_t0 = time.perf_counter()
            _append_csv_rows(output_dir / "sample_rows.csv", [_sample_row(sample)], SAMPLE_FIELDS)
            all_feature_rows: list[dict[str, Any]] = []
            score_ms_total = 0.0
            for spec in dictionary_specs:
                rows, score_ms = fingerprint_rows_for_sample(
                    sample=sample,
                    spec=spec,
                    backend=backends[spec.dictionary_cut],
                )
                # Include backend build time only in first score row for visibility.
                if rows:
                    rows[0]["backend_build_ms"] = f"{backend_build_ms[spec.dictionary_cut]:.6f}"
                all_feature_rows.extend(rows)
                score_ms_total += score_ms
            if write_raw_feature_rows_enabled(RUN_MODE):
                _append_csv_rows(output_dir / "feature_rows.csv", all_feature_rows, FEATURE_FIELDS)
            update_feature_stats(feature_stats, all_feature_rows)
            if write_feature_histograms_enabled(RUN_MODE) or write_feature_quantiles_enabled(RUN_MODE):
                update_feature_histograms(feature_histograms, all_feature_rows)

            samples_done += 1
            feature_rows_done += len(all_feature_rows)
            books_seen.add(clean_chunk.book)
            directions_seen.add(clean_chunk.direction)
            chunks_seen.add(clean_chunk.chunk_id)
            recent_sample_ms.append((time.perf_counter() - sample_t0) * 1000.0)
            if len(recent_sample_ms) > 200:
                recent_sample_ms = recent_sample_ms[-200:]
            write_checkpoint(force=False)
        for threshold in CONVERGENCE_CHUNK_THRESHOLDS:
            if len(chunks_seen) >= threshold:
                write_convergence_checkpoint(threshold)

    write_checkpoint(force=True)
    if len(chunks_seen) and len(chunks_seen) not in convergence_written_thresholds:
        write_convergence_checkpoint(len(chunks_seen))
    final_created = _utc_now()
    final_rows = rolling_summary_rows(checkpoint_index=checkpoint_index, created_utc=final_created, stats=feature_stats)
    _append_csv_rows(output_dir / "final_feature_summary.csv", final_rows, ROLLING_FIELDS)
    if write_feature_histograms_enabled(RUN_MODE):
        _write_csv_rows(output_dir / FEATURE_HISTOGRAMS_NAME, feature_histogram_rows(feature_histograms), FEATURE_HISTOGRAM_FIELDS)
    if write_feature_quantiles_enabled(RUN_MODE):
        _write_csv_rows(output_dir / FEATURE_QUANTILES_NAME, feature_quantile_rows(feature_histograms), FEATURE_QUANTILE_FIELDS)
    damaged_null_rows = damaged_vs_null_summary_rows(feature_stats)
    _write_csv_header(output_dir / DAMAGED_VS_NULL_SUMMARY_NAME, DAMAGED_VS_NULL_FIELDS)
    _append_csv_rows(output_dir / DAMAGED_VS_NULL_SUMMARY_NAME, damaged_null_rows, DAMAGED_VS_NULL_FIELDS)
    damaged_null_by_view_rows = damaged_vs_null_summary_rows(feature_stats, include_view=True)
    _write_csv_rows(output_dir / DAMAGED_VS_NULL_BY_VIEW_NAME, damaged_null_by_view_rows, DAMAGED_VS_NULL_BY_VIEW_FIELDS)
    top_damaged_null_norm = top_damaged_vs_null_rows(
        damaged_null_rows,
        feature_names=("exact_count_norm", "hd_le_count_norm"),
    )
    top_damaged_null_raw = top_damaged_vs_null_rows(
        damaged_null_rows,
        feature_names=("exact_count", "hd_le_count", "matched_window_count", "no_match_count", "window_count"),
    )

    elapsed_s = time.perf_counter() - started_wall
    actual_books_used = len({chunk.book for chunk in clean_chunks})
    actual_book_directions_used = len({(chunk.book, chunk.direction) for chunk in clean_chunks})
    output_estimates = _projected_run_estimates(
        output_dir=output_dir,
        elapsed_s=elapsed_s,
        samples_done=samples_done,
        feature_rows_done=feature_rows_done,
        checkpoint_count=checkpoint_index,
    )
    summary = {
        "run_label": RUN_LABEL,
        "status": "complete",
        "started_at_utc": started_utc,
        "finished_at_utc": final_created,
        "elapsed_s": elapsed_s,
        "run_mode": RUN_MODE,
        "book_order": BOOK_ORDER,
        "book_list_file": BOOK_LIST_FILE_REL,
        "directions": list(active_directions),
        "books_selected": len(selected_books),
        "actual_books_used": actual_books_used,
        "actual_book_directions_used": actual_book_directions_used,
        "actual_chunks_used": len(clean_chunks),
        "clean_chunks": len(clean_chunks),
        "chunk_start_index": chunk_start_index,
        "CHUNK_START_INDEX": chunk_start_index,
        "NUM_CLEAN_CHUNKS_THIS_RUN": len(clean_chunks),
        "num_clean_chunks_this_run_configured": int(limits.get("num_clean_chunks", 0) or 0),
        "first_chunk_id": first_chunk_id,
        "last_chunk_id": last_chunk_id,
        "next_chunk_start_index": next_chunk_start_index,
        "estimated_total_samples": estimated_total,
        "estimated_output_shape": output_shape,
        "samples_done": samples_done,
        "feature_rows_done": feature_rows_done,
        "checkpoint_count": checkpoint_index,
        "chunk_max_tokens": CHUNK_MAX_TOKENS,
        "num_clean_chunks": len(clean_chunks),
        "num_clean_chunks_this_run": len(clean_chunks),
        "rolling_summary_mode": (
            "verbose_cumulative_grouped" if verbose_rolling_summary_enabled(RUN_MODE) else "compact_checkpoint"
        ),
        "write_raw_feature_rows": write_raw_feature_rows_enabled(RUN_MODE),
        "write_feature_histograms": write_feature_histograms_enabled(RUN_MODE),
        "write_feature_quantiles": write_feature_quantiles_enabled(RUN_MODE),
        **ladder_profile_payload(),
        "output_estimates": output_estimates,
        "dictionary_cuts": [spec.dictionary_cut for spec in dictionary_specs],
        "output_dir": _repo_rel(output_dir),
        "machine": _machine_payload(),
        "caveats": [
            "prototype report-only benchmark",
            "NOSE only; WISE deliberately excluded",
            "staged modes are FWD-only unless their hardcoded mode settings say otherwise",
            "feature extraction receives token streams only and scans all offsets",
            f"uses fast raw fingerprint counts then filters to ladder profile {LADDER_PROFILE}",
            "does not alter production scorer weights",
        ],
        "files": {
            "config": _repo_rel(output_dir / "config.json"),
            "input_manifest": _repo_rel(output_dir / "input_manifest.csv"),
            "samples": _repo_rel(output_dir / "sample_rows.csv"),
            "features": _repo_rel(output_dir / "feature_rows.csv") if write_raw_feature_rows_enabled(RUN_MODE) else "",
            "timing_checkpoints": _repo_rel(output_dir / "timing_checkpoints.csv"),
            "rolling_feature_summary": _repo_rel(output_dir / "rolling_feature_summary.csv"),
            "final_feature_summary": _repo_rel(output_dir / "final_feature_summary.csv"),
            "feature_histograms": _repo_rel(output_dir / FEATURE_HISTOGRAMS_NAME) if write_feature_histograms_enabled(RUN_MODE) else "",
            "feature_quantiles": _repo_rel(output_dir / FEATURE_QUANTILES_NAME) if write_feature_quantiles_enabled(RUN_MODE) else "",
            "damaged_vs_null_summary": _repo_rel(output_dir / DAMAGED_VS_NULL_SUMMARY_NAME),
            "damaged_vs_null_by_view": _repo_rel(output_dir / DAMAGED_VS_NULL_BY_VIEW_NAME),
            "convergence_summary": _repo_rel(output_dir / CONVERGENCE_SUMMARY_NAME),
            "dictionary_hash_manifest": _repo_rel(output_dir / DICTIONARY_HASH_MANIFEST_NAME),
        },
    }
    _safe_json_write(output_dir / "final_summary.json", summary)
    _safe_json_write(
        output_dir / "run_manifest.json",
        {
            "run_label": RUN_LABEL,
            "status": "complete",
            "started_at_utc": started_utc,
            "finished_at_utc": final_created,
            "repo_root": ".",
            "machine": _machine_payload(),
            "config": config,
            "summary": summary,
        },
    )

    def _fmt_gib(value: float) -> str:
        return f"{value / (1024.0 ** 3):.2f} GiB"

    def _fmt_hours(value: float) -> str:
        return f"{value / 3600.0:.2f} h"

    readout = "\n".join(
        [
            f"# {RUN_LABEL}",
            "",
            "## Status",
            "",
            "- Report-only prototype; no production scorer change.",
            f"- mode: `{RUN_MODE}`",
            f"- directions: `{', '.join(active_directions)}`",
            f"- CHUNK_MAX_TOKENS: `{CHUNK_MAX_TOKENS}`",
            f"- CHUNK_START_INDEX: `{chunk_start_index}`",
            f"- NUM_CLEAN_CHUNKS_THIS_RUN: `{len(clean_chunks)}`",
            f"- next_chunk_start_index: `{next_chunk_start_index}`",
            f"- first chunk: `{first_chunk_id}`",
            f"- last chunk: `{last_chunk_id}`",
            f"- BOOK_LIST_FILE_REL: `{BOOK_LIST_FILE_REL}`",
            f"- actual books used: `{actual_books_used}`",
            f"- actual book/directions used: `{actual_book_directions_used}`",
            f"- LADDER_PROFILE: `{LADDER_PROFILE}`",
            f"- baseline v0.3 rungs: `{BASELINE_V0_3_RUNG_COUNT}`",
            f"- extra experimental rungs: `{EXTRA_EXPERIMENTAL_RUNG_COUNT}`",
            f"- total ladder rungs: `{TOTAL_LADDER_RUNG_COUNT}`",
            f"- active HD by length: `{json.dumps(active_hd_by_length(), sort_keys=True)}`",
            f"- samples: `{samples_done}`",
            f"- feature rows: `{feature_rows_done}`",
            f"- elapsed seconds: `{elapsed_s:.2f}`",
            f"- output: `{_repo_rel(output_dir)}`",
            f"- rolling summary mode: `{summary['rolling_summary_mode']}`",
            f"- raw feature_rows.csv written: `{write_raw_feature_rows_enabled(RUN_MODE)}`",
            f"- histograms/quantiles written: `{write_feature_histograms_enabled(RUN_MODE)}` / `{write_feature_quantiles_enabled(RUN_MODE)}`",
            f"- final feature names: `{', '.join(FINAL_FEATURE_NAMES)}`",
            "",
            "## Output Estimates",
            "",
            f"- observed feature row bytes/row: `{output_estimates['feature_row_bytes_per_row']:.2f}`",
            f"- observed feature_rows.csv size: `{_fmt_gib(output_estimates['observed_feature_rows_csv_bytes'])}`",
            f"- observed rolling_feature_summary.csv size: `{_fmt_gib(output_estimates['observed_rolling_feature_summary_csv_bytes'])}`",
            f"- observed final_feature_summary.csv size: `{_fmt_gib(output_estimates['observed_final_feature_summary_csv_bytes'])}`",
            f"- observed feature_histograms.csv size: `{_fmt_gib(output_estimates['observed_feature_histograms_csv_bytes'])}`",
            f"- observed feature_quantiles.csv size: `{_fmt_gib(output_estimates['observed_feature_quantiles_csv_bytes'])}`",
            f"- observed damaged_vs_null_summary.csv size: `{_fmt_gib(output_estimates['observed_damaged_vs_null_summary_csv_bytes'])}`",
            f"- observed damaged_vs_null_by_view.csv.gz size: `{_fmt_gib(output_estimates['observed_damaged_vs_null_by_view_csv_gz_bytes'])}`",
            f"- projected nominal full feature_rows.csv size: `{_fmt_gib(output_estimates['nominal_full_feature_rows_csv_bytes_projected'])}`",
            f"- projected nominal full compact rolling summary size: `{_fmt_gib(output_estimates['nominal_full_compact_rolling_summary_csv_bytes_projected'])}`",
            f"- projected nominal full runtime: `{_fmt_hours(output_estimates['nominal_full_runtime_s_projected'])}`",
            f"- nominal full samples/feature rows: `{output_estimates['nominal_full_samples']}` / `{output_estimates['nominal_full_feature_rows']}`",
            *[
                (
                    f"- projected `{mode_name}` runtime: sample-throughput "
                    f"`{_fmt_hours(values['runtime_s_by_sample_throughput'])}`, "
                    f"feature-row-throughput `{_fmt_hours(values['runtime_s_by_feature_row_throughput'])}` "
                    f"for `{values['num_clean_chunks']}` clean chunks"
                )
                for mode_name, values in output_estimates["mode_runtime_projections"].items()
            ],
            "",
            "## Damaged Vs Null",
            "",
            f"- grouped summary: `{DAMAGED_VS_NULL_SUMMARY_NAME}`",
            f"- by-view summary: `{DAMAGED_VS_NULL_BY_VIEW_NAME}`",
            "- top normalised separated rows:",
            *[
                (
                    f"  - `{row['damage_model']}` level `{row['damage_level']}` vs `{row['null_model']}` "
                    f"`{row['dictionary_cut']}` len `{row['span_length']}` HD `{row['hd']}` "
                    f"`{row['feature_name']}`: d=`{float(row['cohen_d']):.3f}`, diff=`{float(row['mean_diff']):.6g}`"
                )
                for row in top_damaged_null_norm
            ],
            "- top raw-count diagnostics:",
            *[
                (
                    f"  - `{row['damage_model']}` level `{row['damage_level']}` vs `{row['null_model']}` "
                    f"`{row['dictionary_cut']}` len `{row['span_length']}` HD `{row['hd']}` "
                    f"`{row['feature_name']}`: d=`{float(row['cohen_d']):.3f}`, diff=`{float(row['mean_diff']):.6g}`"
                )
                for row in top_damaged_null_raw
            ],
            "",
            "## Files",
            "",
            f"- `final_summary.json`",
            f"- `final_feature_summary.csv`",
            f"- `timing_checkpoints.csv`",
            f"- `rolling_feature_summary.csv`",
            f"- `feature_rows.csv`" if write_raw_feature_rows_enabled(RUN_MODE) else "- `feature_rows.csv` omitted by run mode",
            f"- `{FEATURE_HISTOGRAMS_NAME}`" if write_feature_histograms_enabled(RUN_MODE) else f"- `{FEATURE_HISTOGRAMS_NAME}` omitted by run mode",
            f"- `{FEATURE_QUANTILES_NAME}`" if write_feature_quantiles_enabled(RUN_MODE) else f"- `{FEATURE_QUANTILES_NAME}` omitted by run mode",
            f"- `{DAMAGED_VS_NULL_SUMMARY_NAME}`",
            f"- `{DAMAGED_VS_NULL_BY_VIEW_NAME}`",
            f"- `{CONVERGENCE_SUMMARY_NAME}`",
            f"- `{DICTIONARY_HASH_MANIFEST_NAME}`",
            "",
            "## Caveats",
            "",
            "- Convergence status is descriptive/report-only; it does not change the run while executing.",
            "- Quantiles are derived from histogram bins and should be recomputed from merged histograms for combined staged reports.",
        ]
    ) + "\n"
    (output_dir / "readout.md").write_text(readout, encoding="utf-8")
    _safe_json_write(
        output_dir / "run_state.json",
        {
            "run_label": RUN_LABEL,
            "status": "complete",
            "samples_done": samples_done,
            "estimated_total_samples": estimated_total,
            "feature_rows_done": feature_rows_done,
            "checkpoint_index": checkpoint_index,
            "elapsed_s": elapsed_s,
            "estimated_remaining_s_median": 0.0,
            "chunk_start_index": chunk_start_index,
            "num_clean_chunks_this_run": len(clean_chunks),
            "actual_chunks_used": len(clean_chunks),
            "first_chunk_id": first_chunk_id,
            "last_chunk_id": last_chunk_id,
            "next_chunk_start_index": next_chunk_start_index,
            "updated_at_utc": _utc_now(),
        },
    )

    print(
        f"[{RUN_LABEL}] complete samples={samples_done} rows={feature_rows_done} elapsed={elapsed_s:.2f}s",
        flush=True,
    )
    return summary


if __name__ == "__main__":
    run_once()
