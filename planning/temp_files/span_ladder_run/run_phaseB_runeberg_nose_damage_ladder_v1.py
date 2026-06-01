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
This prototype deliberately uses NOSE only, both fwd and rev, fixed 500-token
chunks, PhaseA14 selected dictionaries, and the full v0.3 enabled HD ladder.
"""

import csv
import hashlib
import json
import math
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


# =============================================================================
# CONFIG: edit here, run from IDE
# =============================================================================

RUN_LABEL = "phaseB_runeberg_nose_damage_ladder_v1"
RUN_MODE = "smoke"  # "smoke", "pilot", "full"; affects only preset limits below.

# These are deliberately relative to the detected repo root by default.
TOKENIZED_ROOT_REL = "lmprime_out/tokenized"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_runeberg_nose_damage_ladder_v1"
)

DIRECTIONS = ("fwd", "rev")
CHUNK_SIZE = 500
STRIDE = 500
GLOBAL_SEED = 20260507

# Full v0.3 enabled ladder. Do not narrow this to a winning length/HD.
SPAN_LENGTHS = tuple(range(1, 15))
MAX_HD_BY_LENGTH = {
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
    "smoke": {
        "max_books": 2,
        "chunks_per_book_direction": 2,
        "damage_repeats_per_chunk": 1,
        "damage_levels": (0.30, 0.50),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_25",
        ),
        "checkpoint_every_samples": 25,
        "checkpoint_every_seconds": 60.0,
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
        return path.as_posix()


def _safe_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _write_csv_header(path: Path, fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()


def _append_csv_rows(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
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
        raise KeyError(f"{path} missing required NOSE arrays: {missing}")

    tokens = np.asarray(data["pt_nose_data"], dtype=np.uint8)
    wli_flat = np.asarray(data["wli_nose_data"], dtype=np.uint8)
    if wli_flat.size % 2 != 0:
        raise ValueError(f"{path} wli_nose_data length is not even: {wli_flat.size}")
    wli = wli_flat.reshape(-1, 2)
    if tokens.shape[0] != wli.shape[0]:
        raise ValueError(f"{path} token/WLI length mismatch: {tokens.shape[0]} vs {wli.shape[0]}")
    if tokens.size and int(tokens.max()) > 28:
        raise ValueError(f"{path} contains NOSE token outside 0..28")
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


def select_books(rows: Sequence[tuple[str, str, Path]], *, max_books: int) -> list[str]:
    books = complete_books_from_rows(rows)
    if max_books and len(books) > max_books:
        rng = _rng("select_books", max_books, len(books))
        selected = sorted(rng.choice(np.asarray(books, dtype=object), size=max_books, replace=False).tolist())
        return [str(book) for book in selected]
    return books


def chunk_starts_for_length(token_count: int) -> list[int]:
    if token_count < CHUNK_SIZE:
        return []
    return list(range(0, token_count - CHUNK_SIZE + 1, STRIDE))


def select_chunk_starts(
    *,
    book: str,
    direction: str,
    token_count: int,
    chunks_per_book_direction: int,
) -> list[int]:
    starts = chunk_starts_for_length(token_count)
    if chunks_per_book_direction <= 0 or len(starts) <= chunks_per_book_direction:
        return starts
    rng = _rng("select_chunks", book, direction, token_count, chunks_per_book_direction)
    idxs = rng.choice(np.arange(len(starts)), size=chunks_per_book_direction, replace=False)
    return [starts[int(idx)] for idx in sorted(idxs.tolist())]


def build_clean_chunks(book_dir: TokenizedBookDirection, *, chunks_per_book_direction: int) -> list[CleanChunk]:
    starts = select_chunk_starts(
        book=book_dir.book,
        direction=book_dir.direction,
        token_count=int(book_dir.tokens.size),
        chunks_per_book_direction=chunks_per_book_direction,
    )
    chunks: list[CleanChunk] = []
    for idx, start in enumerate(starts):
        end = start + CHUNK_SIZE
        chunks.append(
            CleanChunk(
                book=book_dir.book,
                direction=book_dir.direction,
                chunk_index=idx,
                chunk_start=start,
                chunk_end=end,
                tokens=tuple(int(x) for x in book_dir.tokens[start:end]),
                wli=tuple((int(a), int(b)) for a, b in book_dir.wli[start:end]),
            )
        )
    return chunks


def _input_manifest_row(book_dir: TokenizedBookDirection, sampled_chunks: int) -> dict[str, Any]:
    return {
        "book": book_dir.book,
        "direction": book_dir.direction,
        "path": _repo_rel(book_dir.path),
        "token_count": int(book_dir.tokens.size),
        "available_chunks": len(chunk_starts_for_length(int(book_dir.tokens.size))),
        "sampled_chunks": sampled_chunks,
    }


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


# =============================================================================
# Span-Hamming fingerprint scoring
# =============================================================================


def build_backend(spec: DictionarySpec) -> FastSpanHammingBackend:
    cfg = SpanHammingConfig(
        len_min=min(SPAN_LENGTHS),
        len_max=max(SPAN_LENGTHS),
        max_hd=2,  # required by constructor; fingerprint mode bins independently.
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
    start = time.perf_counter()
    payload = backend.fingerprint_raw_hamming_counts(
        sample.tokens,
        include_offset_rows=False,
        include_match_dump=False,
        max_candidates_per_window=FINGERPRINT_MAX_CANDIDATES_PER_WINDOW,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    count_by_key: dict[tuple[int, int], int] = {}
    for row in payload.get("chunk_bins", []):
        length = int(row["length"])
        hd = int(row["hd"])
        count_by_key[(length, hd)] = int(row["raw_match_count"])

    rows: list[dict[str, Any]] = []
    for length in SPAN_LENGTHS:
        max_hd = MAX_HD_BY_LENGTH[length]
        windows = max(0, len(sample.tokens) - length + 1)
        denom = float(max(1, windows))
        running = 0
        n_considered = _payload_length_metric(payload, "n_candidates_considered_by_len", length)
        n_pruned = _payload_length_metric(payload, "n_candidates_pruned_cap_by_len", length)
        for hd in range(max_hd + 1):
            exact_count = int(count_by_key.get((length, hd), 0))
            running += exact_count
            rows.append(
                {
                    "run_label": RUN_LABEL,
                    "sample_id": sample.sample_id,
                    "book": sample.clean_chunk.book,
                    "direction": sample.clean_chunk.direction,
                    "chunk_id": sample.clean_chunk.chunk_id,
                    "chunk_index": sample.clean_chunk.chunk_index,
                    "chunk_start": sample.clean_chunk.chunk_start,
                    "chunk_end": sample.clean_chunk.chunk_end,
                    "source_kind": sample.source_kind,
                    "damage_model": sample.damage_model,
                    "damage_level": sample.damage_level,
                    "null_model": sample.null_model,
                    "repeat_index": sample.repeat_index,
                    "seed": sample.seed,
                    "dictionary_cut": spec.dictionary_cut,
                    "span_length": length,
                    "hd": hd,
                    "window_count": windows,
                    "exact_count": exact_count,
                    "exact_count_norm": f"{exact_count / denom:.12g}",
                    "hd_le_count": running,
                    "hd_le_count_norm": f"{running / denom:.12g}",
                    "n_candidates_considered": n_considered,
                    "n_candidates_pruned_cap": n_pruned,
                    "candidate_cap_pruned_rate": f"{n_pruned / float(max(1, n_considered + n_pruned)):.12g}",
                    "score_ms": f"{elapsed_ms:.6f}",
                    "backend_build_ms": "",
                    "fingerprint_scope": "raw_hamming_counts",
                    "fast_backend_hd_policy": str(payload.get("hd_max_policy", "length_minus_one")),
                    "enabled_ladder_only": 1,
                    "cap": int(payload.get("cap", FINGERPRINT_MAX_CANDIDATES_PER_WINDOW) or 0),
                    "is_uncapped": int(bool(payload.get("is_uncapped", FINGERPRINT_MAX_CANDIDATES_PER_WINDOW == 0))),
                }
            )
    return rows, elapsed_ms


# =============================================================================
# Output field names and rolling summary
# =============================================================================


SAMPLE_FIELDS = [
    "run_label",
    "sample_id",
    "book",
    "direction",
    "chunk_id",
    "source_kind",
    "damage_model",
    "damage_level",
    "null_model",
    "repeat_index",
    "seed",
    "token_count",
]

FEATURE_FIELDS = [
    "run_label",
    "sample_id",
    "book",
    "direction",
    "chunk_id",
    "chunk_index",
    "chunk_start",
    "chunk_end",
    "source_kind",
    "damage_model",
    "damage_level",
    "null_model",
    "repeat_index",
    "seed",
    "dictionary_cut",
    "span_length",
    "hd",
    "window_count",
    "exact_count",
    "exact_count_norm",
    "hd_le_count",
    "hd_le_count_norm",
    "n_candidates_considered",
    "n_candidates_pruned_cap",
    "candidate_cap_pruned_rate",
    "score_ms",
    "backend_build_ms",
    "fingerprint_scope",
    "fast_backend_hd_policy",
    "enabled_ladder_only",
    "cap",
    "is_uncapped",
]

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
    "dictionary_cut",
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


def _sample_row(sample: Sample) -> dict[str, Any]:
    return {
        "run_label": RUN_LABEL,
        "sample_id": sample.sample_id,
        "book": sample.clean_chunk.book,
        "direction": sample.clean_chunk.direction,
        "chunk_id": sample.clean_chunk.chunk_id,
        "source_kind": sample.source_kind,
        "damage_model": sample.damage_model,
        "damage_level": sample.damage_level,
        "null_model": sample.null_model,
        "repeat_index": sample.repeat_index,
        "seed": sample.seed,
        "token_count": len(sample.tokens),
    }


def _feature_stat_key(row: Mapping[str, Any], feature_name: str) -> tuple[Any, ...]:
    return (
        row["direction"],
        row["source_kind"],
        row["damage_model"],
        row["damage_level"],
        row["null_model"],
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
        "dictionary_cut": dictionary_cut,
        "span_length": span_length,
        "hd": hd,
        "feature_name": feature_name,
    }


def update_feature_stats(stats: dict[tuple[Any, ...], RunningStat], rows: Sequence[Mapping[str, Any]]) -> None:
    for row in rows:
        for feature_name in ("exact_count_norm", "hd_le_count_norm", "candidate_cap_pruned_rate"):
            value = float(row[feature_name])
            key = _feature_stat_key(row, feature_name)
            stats.setdefault(key, RunningStat()).update(value)


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
        "tokenized_root": _repo_rel(tokenized_root),
        "output_dir": _repo_rel(output_dir),
        "directions": list(DIRECTIONS),
        "chunk_size": CHUNK_SIZE,
        "stride": STRIDE,
        "global_seed": GLOBAL_SEED,
        "span_lengths": list(SPAN_LENGTHS),
        "max_hd_by_length": MAX_HD_BY_LENGTH,
        "fingerprint_max_candidates_per_window": FINGERPRINT_MAX_CANDIDATES_PER_WINDOW,
        "dictionary_specs": list(DICTIONARY_SPECS),
        "mode_limits": dict(_mode_limits()),
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


def run_once() -> dict[str, Any]:
    if RUN_SELF_TESTS:
        run_self_tests()
    if not fast_span_hamming_available():
        raise RuntimeError(
            "optional _span_hamming_fast extension is not built; "
            "build it before running this benchmark"
        )

    limits = _mode_limits()
    tokenized_root = REPO_ROOT / TOKENIZED_ROOT_REL
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    output_dir.mkdir(parents=True, exist_ok=True)

    if not tokenized_root.exists():
        raise FileNotFoundError(f"TOKENIZED_ROOT not found: {tokenized_root}")

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
            "repo_root": str(REPO_ROOT),
            "machine": _machine_payload(),
            "config": config,
        },
    )

    for path, fields in (
        (output_dir / "input_manifest.csv", INPUT_MANIFEST_FIELDS),
        (output_dir / "sample_rows.csv", SAMPLE_FIELDS),
        (output_dir / "feature_rows.csv", FEATURE_FIELDS),
        (output_dir / "timing_checkpoints.csv", TIMING_FIELDS),
        (output_dir / "rolling_feature_summary.csv", ROLLING_FIELDS),
        (output_dir / "final_feature_summary.csv", ROLLING_FIELDS),
    ):
        _write_csv_header(path, fields)

    discovered = discover_tokenized_files(tokenized_root)
    selected_books = set(select_books(discovered, max_books=int(limits["max_books"])))
    selected_rows = [row for row in discovered if row[0] in selected_books and row[1] in DIRECTIONS]
    if not selected_rows:
        raise RuntimeError(f"No tokenized fwd/rev files selected under {tokenized_root}")

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

    clean_chunks: list[CleanChunk] = []
    input_manifest_rows: list[dict[str, Any]] = []
    for book_dir in loaded:
        chunks = build_clean_chunks(book_dir, chunks_per_book_direction=int(limits["chunks_per_book_direction"]))
        clean_chunks.extend(chunks)
        input_manifest_rows.append(_input_manifest_row(book_dir, sampled_chunks=len(chunks)))
    _append_csv_rows(output_dir / "input_manifest.csv", input_manifest_rows, INPUT_MANIFEST_FIELDS)

    if not clean_chunks:
        raise RuntimeError("Selected tokenized books produced no 500-token NOSE chunks")

    estimated_total = estimate_total_samples(len(clean_chunks), limits)

    dictionary_specs = [DictionarySpec(**spec) for spec in DICTIONARY_SPECS]
    backends: dict[str, FastSpanHammingBackend] = {}
    backend_build_ms: dict[str, float] = {}
    for spec in dictionary_specs:
        t0 = time.perf_counter()
        backends[spec.dictionary_cut] = build_backend(spec)
        backend_build_ms[spec.dictionary_cut] = (time.perf_counter() - t0) * 1000.0

    feature_stats: dict[tuple[Any, ...], RunningStat] = {}
    recent_sample_ms: list[float] = []
    checkpoint_speeds: list[float] = []
    samples_done = 0
    feature_rows_done = 0
    checkpoint_index = 0
    last_checkpoint_at = time.perf_counter()
    books_seen: set[str] = set()
    directions_seen: set[str] = set()
    chunks_seen: set[str] = set()

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
        _append_csv_rows(
            output_dir / "rolling_feature_summary.csv",
            rolling_summary_rows(checkpoint_index=checkpoint_index, created_utc=created, stats=feature_stats),
            ROLLING_FIELDS,
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
                "updated_at_utc": created,
            },
        )
        last_checkpoint_at = now
        print(
            f"[{RUN_LABEL}] checkpoint {checkpoint_index}: samples={samples_done}/{estimated_total} "
            f"elapsed={elapsed:.1f}s median_eta={remain_med:.1f}s rows={feature_rows_done}",
            flush=True,
        )

    print(
        f"[{RUN_LABEL}] starting mode={RUN_MODE} books={len(selected_books)} clean_chunks={len(clean_chunks)} "
        f"estimated_samples={estimated_total}",
        flush=True,
    )

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
            _append_csv_rows(output_dir / "feature_rows.csv", all_feature_rows, FEATURE_FIELDS)
            update_feature_stats(feature_stats, all_feature_rows)

            samples_done += 1
            feature_rows_done += len(all_feature_rows)
            books_seen.add(clean_chunk.book)
            directions_seen.add(clean_chunk.direction)
            chunks_seen.add(clean_chunk.chunk_id)
            recent_sample_ms.append((time.perf_counter() - sample_t0) * 1000.0)
            if len(recent_sample_ms) > 200:
                recent_sample_ms = recent_sample_ms[-200:]
            write_checkpoint(force=False)

    write_checkpoint(force=True)
    final_created = _utc_now()
    final_rows = rolling_summary_rows(checkpoint_index=checkpoint_index, created_utc=final_created, stats=feature_stats)
    _append_csv_rows(output_dir / "final_feature_summary.csv", final_rows, ROLLING_FIELDS)

    elapsed_s = time.perf_counter() - started_wall
    summary = {
        "run_label": RUN_LABEL,
        "status": "complete",
        "started_at_utc": started_utc,
        "finished_at_utc": final_created,
        "elapsed_s": elapsed_s,
        "run_mode": RUN_MODE,
        "books_selected": len(selected_books),
        "clean_chunks": len(clean_chunks),
        "estimated_total_samples": estimated_total,
        "samples_done": samples_done,
        "feature_rows_done": feature_rows_done,
        "checkpoint_count": checkpoint_index,
        "dictionary_cuts": [spec.dictionary_cut for spec in dictionary_specs],
        "output_dir": _repo_rel(output_dir),
        "machine": _machine_payload(),
        "caveats": [
            "prototype report-only benchmark",
            "NOSE only; WISE deliberately excluded",
            "fwd and rev kept separate in rows and summaries",
            "uses fast raw fingerprint counts then filters to v0.3 enabled ladder",
            "does not alter production scorer weights",
        ],
        "files": {
            "config": _repo_rel(output_dir / "config.json"),
            "input_manifest": _repo_rel(output_dir / "input_manifest.csv"),
            "samples": _repo_rel(output_dir / "sample_rows.csv"),
            "features": _repo_rel(output_dir / "feature_rows.csv"),
            "timing_checkpoints": _repo_rel(output_dir / "timing_checkpoints.csv"),
            "rolling_feature_summary": _repo_rel(output_dir / "rolling_feature_summary.csv"),
            "final_feature_summary": _repo_rel(output_dir / "final_feature_summary.csv"),
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
            "repo_root": str(REPO_ROOT),
            "machine": _machine_payload(),
            "config": config,
            "summary": summary,
        },
    )

    readout = "\n".join(
        [
            f"# {RUN_LABEL}",
            "",
            "## Status",
            "",
            "- Report-only prototype; no production scorer change.",
            f"- mode: `{RUN_MODE}`",
            f"- samples: `{samples_done}`",
            f"- feature rows: `{feature_rows_done}`",
            f"- elapsed seconds: `{elapsed_s:.2f}`",
            f"- output: `{_repo_rel(output_dir)}`",
            "",
            "## Files",
            "",
            f"- `final_summary.json`",
            f"- `final_feature_summary.csv`",
            f"- `timing_checkpoints.csv`",
            f"- `rolling_feature_summary.csv`",
            f"- `feature_rows.csv`",
            "",
            "## Caveats",
            "",
            "- This is the first prototype layout, intended for smoke and timing pilot runs.",
            "- Feature summaries are descriptive; final damaged-vs-null comparison logic can be tightened after the smoke output shape is approved.",
        ]
    ) + "\n"
    (output_dir / "readout.md").write_text(readout, encoding="utf-8")

    print(
        f"[{RUN_LABEL}] complete samples={samples_done} rows={feature_rows_done} elapsed={elapsed_s:.2f}s",
        flush=True,
    )
    return summary


if __name__ == "__main__":
    run_once()
