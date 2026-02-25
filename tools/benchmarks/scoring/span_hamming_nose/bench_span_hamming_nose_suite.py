from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
from array import array
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parents[4]
    _SRC = _ROOT / "src"
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    if _SRC.exists() and str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device, Direction, ScorerImpl
from rune_decrypter_prime.scoring.span_hamming import SpanHammingBackend, SpanHammingConfig
from tools.benchmarks.scoring.span_hamming_nose.schema import (
    DEFAULT_LENGTH_BUCKETS,
    NPZ_TOKEN_KEY,
    PlanRow,
    SUITE_VERSION,
    build_stride_plan,
    corpus_list_hash,
    discover_npz_paths,
    estimate_unigram_probs_by_direction,
    hash_object,
    load_corpus_records,
    read_plan_csv,
    stable_int,
    write_plan_csv,
)


# ---------------------------------------------------------------------------
# Config block (no CLI; edit constants here)
# ---------------------------------------------------------------------------
TOKENIZED_DIR = Path("assets_packed/tokenized_pg")
DIRECTIONS = ["ltr"]
USE_NOSE_ONLY = True

LENGTH_BUCKETS = list(DEFAULT_LENGTH_BUCKETS)

MIN_STRIDE = 200
STRIDE_FACTOR = 1.0
MAX_WINDOWS_PER_BOOK_BY_L = {
    20: 20,
    50: 20,
    100: 20,
    200: 15,
    300: 12,
    500: 10,
    600: 10,
    750: 8,
    1000: 6,
    1500: 4,
    2400: 2,
}
MAX_WINDOWS_FALLBACK = 50

GENERATORS = ["REAL", "RAND_UNIGRAM", "SHUFFLE_UNIGRAM"]
CORRUPT_PCTS: list[int] = []

ENABLE_CONVERGENCE = True
MEAN_TOL = 0.002
STD_TOL = 0.005
PATIENCE_BATCHES = 3
MAX_BATCHES = 10
BOOKS_PER_BATCH = 100

ENABLE_CHAR_BASELINES = True

GLOBAL_SEED = 12345
OUTPUT_ROOT = Path("output/tools/benchmarks/scoring/span_hamming_nose_suite")
RUN_DIR_OVERRIDE: str | None = None

SPAN_LEN_MIN = 3
SPAN_LEN_MAX = 14
SPAN_MAX_HD = 2
SPAN_MAX_CANDIDATES_PER_WINDOW = 256
SPAN_MAX_INTERVALS_PER_START = 4
SPAN_MIN_QUALITY_THRESHOLD = 1e-9

WRITE_SAMPLES_JSONL = False
CHECKPOINT_EVERY = 5000

# Crash-safe progress and multi-machine sharding.
RESUME_IF_RUN_DIR_EXISTS = True
SHARD_COUNT = 1
SHARD_INDEX = 0
SHARD_STRATEGY = "book_hash_mod"
COMPLETION_LOG_BASENAME = "completed_rows.csv"


@dataclass(frozen=True)
class SuiteRunConfig:
    tokenized_dir: Path
    directions: list[str]
    use_nose_only: bool
    length_buckets: list[int]
    min_stride: int
    stride_factor: float
    max_windows_per_book_by_l: dict[int, int]
    max_windows_fallback: int
    generators: list[str]
    corrupt_pcts: list[int]
    enable_convergence: bool
    mean_tol: float
    std_tol: float
    patience_batches: int
    max_batches: int
    books_per_batch: int | None
    enable_char_baselines: bool
    global_seed: int
    output_root: Path
    run_dir: Path | None
    span_len_min: int
    span_len_max: int
    span_max_hd: int
    span_max_candidates_per_window: int
    span_max_intervals_per_start: int
    span_min_quality_threshold: float
    write_samples_jsonl: bool
    checkpoint_every: int
    resume_if_run_dir_exists: bool
    shard_count: int
    shard_index: int
    shard_strategy: str
    completion_log_basename: str


def _build_run_config() -> SuiteRunConfig:
    return SuiteRunConfig(
        tokenized_dir=Path(TOKENIZED_DIR).expanduser().resolve(),
        directions=[str(x).strip().lower() for x in DIRECTIONS],
        use_nose_only=bool(USE_NOSE_ONLY),
        length_buckets=[int(x) for x in LENGTH_BUCKETS],
        min_stride=int(MIN_STRIDE),
        stride_factor=float(STRIDE_FACTOR),
        max_windows_per_book_by_l={int(k): int(v) for k, v in dict(MAX_WINDOWS_PER_BOOK_BY_L).items()},
        max_windows_fallback=int(MAX_WINDOWS_FALLBACK),
        generators=[str(x).strip().upper() for x in GENERATORS],
        corrupt_pcts=[int(x) for x in CORRUPT_PCTS],
        enable_convergence=bool(ENABLE_CONVERGENCE),
        mean_tol=float(MEAN_TOL),
        std_tol=float(STD_TOL),
        patience_batches=int(PATIENCE_BATCHES),
        max_batches=int(MAX_BATCHES),
        books_per_batch=(int(BOOKS_PER_BATCH) if BOOKS_PER_BATCH is not None else None),
        enable_char_baselines=bool(ENABLE_CHAR_BASELINES),
        global_seed=int(GLOBAL_SEED),
        output_root=Path(OUTPUT_ROOT).expanduser().resolve(),
        run_dir=(Path(RUN_DIR_OVERRIDE).expanduser().resolve() if RUN_DIR_OVERRIDE else None),
        span_len_min=int(SPAN_LEN_MIN),
        span_len_max=int(SPAN_LEN_MAX),
        span_max_hd=int(SPAN_MAX_HD),
        span_max_candidates_per_window=int(SPAN_MAX_CANDIDATES_PER_WINDOW),
        span_max_intervals_per_start=int(SPAN_MAX_INTERVALS_PER_START),
        span_min_quality_threshold=float(SPAN_MIN_QUALITY_THRESHOLD),
        write_samples_jsonl=bool(WRITE_SAMPLES_JSONL),
        checkpoint_every=int(CHECKPOINT_EVERY),
        resume_if_run_dir_exists=bool(RESUME_IF_RUN_DIR_EXISTS),
        shard_count=int(SHARD_COUNT),
        shard_index=int(SHARD_INDEX),
        shard_strategy=str(SHARD_STRATEGY).strip().lower(),
        completion_log_basename=str(COMPLETION_LOG_BASENAME),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _git_meta(repo_root: Path) -> dict[str, Any]:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            text=True,
        ).strip()
    except Exception:
        sha = "unknown"
    try:
        dirty_out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            text=True,
        )
        dirty = bool(dirty_out.strip())
    except Exception:
        dirty = False
    return {"git_sha": sha, "git_dirty": dirty}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False),
        encoding="utf-8",
    )


def _json_array(values: Any) -> str:
    return json.dumps(values, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _append_csv_row(path: Path, header: list[str], row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        )
        handle.write("\n")


def _clear_outputs(paths: list[Path]) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


def _format_duration(seconds: float) -> str:
    sec = int(max(0.0, float(seconds)))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h}h{m:02d}m{s:02d}s"
    if m > 0:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def _completion_header() -> list[str]:
    return [
        "row_idx",
        "row_id",
        "direction",
        "length_bucket",
        "book_id",
        "start",
        "completed_at_utc",
    ]


def _append_completed_row(path: Path, plan: PlanRow) -> None:
    _append_csv_row(
        path,
        _completion_header(),
        {
            "row_idx": str(int(plan.row_idx)),
            "row_id": str(plan.row_id),
            "direction": str(plan.direction),
            "length_bucket": str(int(plan.length_bucket)),
            "book_id": str(plan.book_id),
            "start": str(int(plan.start)),
            "completed_at_utc": _utc_now(),
        },
    )


def _load_completed_row_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rid = str(row.get("row_id", "")).strip()
            if rid:
                out.add(rid)
    return out


def _to_float(value: Any, default: float = float("nan")) -> float:
    try:
        if value is None:
            return float(default)
        text = str(value).strip()
        if text == "":
            return float(default)
        return float(text)
    except Exception:
        return float(default)


def _get_or_create_group_bucket(
    group_values: dict[tuple[str, int, str], dict[str, array]],
    key: tuple[str, int, str],
) -> dict[str, array]:
    bucket = group_values.get(key)
    if bucket is None:
        bucket = {
            "span": array("f"),
            "char1": array("f"),
            "char2": array("f"),
            "char3": array("f"),
            "char4": array("f"),
        }
        group_values[key] = bucket
    return bucket


def _load_existing_samples_state(
    *,
    samples_csv_path: Path,
    completed_row_ids: set[str],
) -> tuple[
    dict[tuple[str, int, str], dict[str, array]],
    dict[tuple[str, int], list[float]],
    dict[str, set[str]],
]:
    group_values: dict[tuple[str, int, str], dict[str, array]] = {}
    real_scores_by_bucket: dict[tuple[str, int], list[float]] = {}
    partial_generators_by_row: dict[str, set[str]] = {}
    if not samples_csv_path.exists():
        return group_values, real_scores_by_bucket, partial_generators_by_row

    with samples_csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            direction = str(row.get("direction", "")).strip().lower()
            if not direction:
                continue
            length_bucket = int(row.get("length_bucket", 0))
            generator = str(row.get("generator", "")).strip().upper()
            row_id = str(row.get("row_id", "")).strip()

            gk = (direction, length_bucket, generator)
            vals = _get_or_create_group_bucket(group_values, gk)
            span_raw = _to_float(row.get("span_raw"))
            vals["span"].append(span_raw)
            vals["char1"].append(_to_float(row.get("char1_score")))
            vals["char2"].append(_to_float(row.get("char2_score")))
            vals["char3"].append(_to_float(row.get("char3_score")))
            vals["char4"].append(_to_float(row.get("char4_score")))

            if generator == "REAL":
                bk = (direction, length_bucket)
                real_scores_by_bucket.setdefault(bk, []).append(span_raw)

            if row_id and row_id not in completed_row_ids:
                partial_generators_by_row.setdefault(row_id, set()).add(generator)

    return group_values, real_scores_by_bucket, partial_generators_by_row


def _load_existing_convergence_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "direction": str(row.get("direction", "")).strip().lower(),
                    "length_bucket": int(row.get("length_bucket", 0)),
                    "batch_idx": int(row.get("batch_idx", 0)),
                    "books_in_batch": int(row.get("books_in_batch", 0)),
                    "planned_windows_batch": int(row.get("planned_windows_batch", 0)),
                    "real_windows_batch": int(row.get("real_windows_batch", 0)),
                    "real_windows_per_book_mean": _to_float(row.get("real_windows_per_book_mean")),
                    "real_windows_total": int(row.get("real_windows_total", 0)),
                    "mean_span_raw_real": _to_float(row.get("mean_span_raw_real")),
                    "std_span_raw_real": _to_float(row.get("std_span_raw_real")),
                    "delta_mean_rel": _to_float(row.get("delta_mean_rel")),
                    "delta_std_rel": _to_float(row.get("delta_std_rel")),
                    "stable": str(row.get("stable", "")).strip().lower() == "true",
                    "patience_count": int(row.get("patience_count", 0)),
                    "converged": str(row.get("converged", "")).strip().lower() == "true",
                }
            )
    return rows


def _book_shard_index(*, book_id: str, shard_count: int, global_seed: int) -> int:
    if shard_count <= 1:
        return 0
    return int(stable_int("book_shard", book_id, int(global_seed)) % int(shard_count))


def _write_book_manifest(
    *,
    path: Path,
    records: list[Any],
    shard_book_ids: set[str],
) -> None:
    header = ["book_id", "path", "direction", "n_tokens", "in_shard"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for rec in records:
            writer.writerow(
                {
                    "book_id": str(rec.book_id),
                    "path": str(rec.path),
                    "direction": str(rec.direction),
                    "n_tokens": str(int(rec.tokens.size)),
                    "in_shard": "1" if str(rec.book_id) in shard_book_ids else "0",
                }
            )


def _sample_header() -> list[str]:
    return [
        "sample_id",
        "row_id",
        "direction",
        "length_bucket",
        "generator",
        "book_id",
        "book_path",
        "start",
        "text_length",
        "stride",
        "batch_index",
        "seed_local",
        "span_raw",
        "coverage",
        "quality",
        "n_chars",
        "chars_covered",
        "n_intervals_selected",
        "length_bins",
        "span_raw_by_len",
        "coverage_by_len",
        "quality_by_len",
        "selected_intervals_by_len",
        "chars_covered_by_len",
        "n_windows_total",
        "n_windows_scored",
        "n_candidates_considered",
        "n_candidates_pruned_cap",
        "char1_score",
        "char2_score",
        "char3_score",
        "char4_score",
    ]


def _summary_header() -> list[str]:
    header = [
        "direction",
        "length_bucket",
        "generator",
        "n",
        "span_raw_mean",
        "span_raw_median",
        "span_raw_std",
        "span_raw_p10",
        "span_raw_p50",
        "span_raw_p90",
        "span_raw_p99",
    ]
    for n in (1, 2, 3, 4):
        header.extend(
            [
                f"char{n}_mean",
                f"char{n}_median",
                f"char{n}_std",
            ]
        )
    for n in (1, 2, 3, 4):
        header.append(f"spearman_real_char{n}")
    for n in (1, 2, 3, 4):
        header.append(f"spearman_shuffle_char{n}")
    return header


def _convergence_header() -> list[str]:
    return [
        "direction",
        "length_bucket",
        "batch_idx",
        "books_in_batch",
        "planned_windows_batch",
        "real_windows_batch",
        "real_windows_per_book_mean",
        "real_windows_total",
        "mean_span_raw_real",
        "std_span_raw_real",
        "delta_mean_rel",
        "delta_std_rel",
        "stable",
        "patience_count",
        "converged",
    ]


def _sample_to_csv_row(sample_row: dict[str, Any]) -> dict[str, str]:
    json_fields = {
        "length_bins",
        "span_raw_by_len",
        "coverage_by_len",
        "quality_by_len",
        "selected_intervals_by_len",
        "chars_covered_by_len",
    }
    out: dict[str, str] = {}
    for key in _sample_header():
        value = sample_row.get(key)
        if key in json_fields:
            out[key] = _json_array(value)
        elif isinstance(value, float):
            out[key] = f"{value:.12g}"
        else:
            out[key] = str(value)
    return out


def _rankdata_average_ties(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.zeros_like(sorted_values, dtype=np.float64)
    idx = 0
    n = sorted_values.size
    while idx < n:
        j = idx + 1
        while j < n and sorted_values[j] == sorted_values[idx]:
            j += 1
        avg_rank = 0.5 * (idx + j - 1) + 1.0
        ranks[idx:j] = avg_rank
        idx = j
    out = np.zeros_like(ranks)
    out[order] = ranks
    return out


def _spearman_corr(x: Sequence[float], y: Sequence[float]) -> float:
    xa = np.asarray(x, dtype=np.float64)
    ya = np.asarray(y, dtype=np.float64)
    if xa.size != ya.size or xa.size < 2:
        return float("nan")
    if not np.isfinite(xa).all() or not np.isfinite(ya).all():
        return float("nan")
    rx = _rankdata_average_ties(xa)
    ry = _rankdata_average_ties(ya)
    sx = float(np.std(rx))
    sy = float(np.std(ry))
    if sx <= 0.0 or sy <= 0.0:
        return float("nan")
    cov = float(np.mean((rx - float(np.mean(rx))) * (ry - float(np.mean(ry)))))
    return cov / (sx * sy)


def _build_char_baseline_scorers(
    *,
    enabled: bool,
    directions: list[str],
) -> dict[tuple[str, int], Any]:
    if not enabled:
        return {}
    scorers: dict[tuple[str, int], Any] = {}
    for direction in directions:
        direction_norm = str(direction).lower()
        direction_enum = Direction.RTL if direction_norm == "rtl" else Direction.LTR
        cipher_cfg = CipherConfig(
            ciphertext=[0],
            wli_data=[],
            key_length=None,
            device=Device.CPU,
            encoding_dir=direction_enum,
        )
        for n in (1, 2, 3, 4):
            score_cfg = ScoringConfig(
                objective="avg.logp.win20",
                avg_window_policy="full_text",
                include_char=True,
                use_word_breaks=False,
                n_char=n,
                n_wli=0,
                char_weights={n: 1.0},
                wli_weights={},
                impl=ScorerImpl.NUMPY,
                encoding_dir=direction_enum,
            )
            scorers[(direction_norm, n)] = build_scorer(cipher_cfg, score_cfg)
    return scorers


def _generator_sample(
    base_tokens: np.ndarray,
    *,
    generator: str,
    rng: np.random.Generator,
    unigram_probs: np.ndarray,
    corrupt_pcts: Sequence[int],
) -> np.ndarray:
    gen = generator.upper()
    if gen == "REAL":
        return base_tokens.astype(np.uint8, copy=True)
    if gen == "SHUFFLE_UNIGRAM":
        out = base_tokens.astype(np.uint8, copy=True)
        rng.shuffle(out)
        return out
    if gen == "RAND_UNIGRAM":
        values = rng.choice(29, size=base_tokens.size, replace=True, p=unigram_probs)
        return values.astype(np.uint8, copy=False)
    if gen.startswith("CORRUPT_"):
        out = base_tokens.astype(np.uint8, copy=True)
        pct = int(gen.split("_", 1)[1])
        if pct not in set(int(x) for x in corrupt_pcts):
            raise ValueError(f"CORRUPT percent not in configured set: {pct}")
        k = int(round((pct / 100.0) * float(out.size)))
        k = max(1, min(int(out.size), k))
        idx = rng.choice(int(out.size), size=k, replace=False)
        repl = rng.choice(29, size=k, replace=True, p=unigram_probs)
        out[idx] = repl.astype(np.uint8, copy=False)
        return out
    raise ValueError(f"Unsupported generator: {generator}")


def score_window_sample(
    *,
    plan: PlanRow,
    base_tokens: np.ndarray,
    generator: str,
    global_seed: int,
    batch_index: int,
    span_backend: SpanHammingBackend,
    unigram_probs: np.ndarray,
    corrupt_pcts: Sequence[int],
    enable_char_baselines: bool,
    char_baseline_scorers: dict[tuple[str, int], Any],
) -> dict[str, Any]:
    seed_local = int(stable_int(global_seed, plan.row_id, generator) & 0x7FFFFFFF)
    rng = np.random.default_rng(seed_local)
    sample_tokens = _generator_sample(
        base_tokens=base_tokens,
        generator=generator,
        rng=rng,
        unigram_probs=unigram_probs,
        corrupt_pcts=corrupt_pcts,
    )
    stats = span_backend.score(sample_tokens)

    char_scores: dict[int, float] = {1: float("nan"), 2: float("nan"), 3: float("nan"), 4: float("nan")}
    if enable_char_baselines:
        for n in (1, 2, 3, 4):
            scorer = char_baseline_scorers[(plan.direction, n)]
            char_scores[n] = float(scorer.score(sample_tokens, None))

    sample_id = hash_object(
        {
            "row_id": plan.row_id,
            "generator": str(generator).upper(),
            "seed_local": seed_local,
        }
    )
    return {
        "sample_id": sample_id,
        "row_id": plan.row_id,
        "direction": plan.direction,
        "length_bucket": int(plan.length_bucket),
        "generator": str(generator).upper(),
        "book_id": plan.book_id,
        "book_path": plan.book_path,
        "start": int(plan.start),
        "text_length": int(plan.text_length),
        "stride": int(plan.stride),
        "batch_index": int(batch_index),
        "seed_local": seed_local,
        "span_raw": float(stats.span_raw),
        "coverage": float(stats.coverage),
        "quality": float(stats.quality),
        "n_chars": int(stats.n_chars),
        "chars_covered": int(stats.chars_covered),
        "n_intervals_selected": int(stats.n_intervals_selected),
        "length_bins": list(map(int, stats.length_bins)),
        "span_raw_by_len": list(map(float, stats.span_raw_by_len)),
        "coverage_by_len": list(map(float, stats.coverage_by_len)),
        "quality_by_len": list(map(float, stats.quality_by_len)),
        "selected_intervals_by_len": list(map(int, stats.selected_intervals_by_len)),
        "chars_covered_by_len": list(map(int, stats.chars_covered_by_len)),
        "n_windows_total": int(stats.n_windows_total),
        "n_windows_scored": int(stats.n_windows_scored),
        "n_candidates_considered": int(stats.n_candidates_considered),
        "n_candidates_pruned_cap": int(stats.n_candidates_pruned_cap),
        "char1_score": float(char_scores[1]),
        "char2_score": float(char_scores[2]),
        "char3_score": float(char_scores[3]),
        "char4_score": float(char_scores[4]),
    }


def _bucket_book_batches(
    *,
    plan_rows: list[PlanRow],
    books_per_batch: int | None,
    max_batches: int,
) -> list[list[str]]:
    books = sorted({row.book_id for row in plan_rows})
    if not books:
        return []
    batch_size = len(books) if not books_per_batch or books_per_batch <= 0 else int(books_per_batch)
    batches = [books[i : i + batch_size] for i in range(0, len(books), batch_size)]
    if max_batches > 0:
        batches = batches[: int(max_batches)]
    return batches


def _arr_to_np(values: array) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)


def _write_summary_csv(path: Path, group_values: dict[tuple[str, int, str], dict[str, array]]) -> None:
    by_bucket: dict[tuple[str, int], dict[str, dict[str, array]]] = {}
    for (direction, length_bucket, generator), vals in group_values.items():
        by_bucket.setdefault((direction, length_bucket), {})[generator] = vals

    corr_by_bucket: dict[tuple[str, int], dict[str, float]] = {}
    for key, by_gen in by_bucket.items():
        corr: dict[str, float] = {}
        real = by_gen.get("REAL")
        shuf = by_gen.get("SHUFFLE_UNIGRAM")
        for n in (1, 2, 3, 4):
            if real is None:
                corr[f"real_char{n}"] = float("nan")
            else:
                corr[f"real_char{n}"] = _spearman_corr(
                    _arr_to_np(real["span"]),
                    _arr_to_np(real[f"char{n}"]),
                )
            if shuf is None:
                corr[f"shuffle_char{n}"] = float("nan")
            else:
                corr[f"shuffle_char{n}"] = _spearman_corr(
                    _arr_to_np(shuf["span"]),
                    _arr_to_np(shuf[f"char{n}"]),
                )
        corr_by_bucket[key] = corr

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_summary_header())
        writer.writeheader()
        for (direction, length_bucket, generator) in sorted(group_values.keys()):
            values = group_values[(direction, length_bucket, generator)]
            span = _arr_to_np(values["span"])
            out: dict[str, str] = {
                "direction": direction,
                "length_bucket": str(length_bucket),
                "generator": generator,
                "n": str(int(span.size)),
                "span_raw_mean": f"{float(np.mean(span)):.12g}",
                "span_raw_median": f"{float(np.median(span)):.12g}",
                "span_raw_std": f"{float(np.std(span)):.12g}",
                "span_raw_p10": f"{float(np.quantile(span, 0.10)):.12g}",
                "span_raw_p50": f"{float(np.quantile(span, 0.50)):.12g}",
                "span_raw_p90": f"{float(np.quantile(span, 0.90)):.12g}",
                "span_raw_p99": f"{float(np.quantile(span, 0.99)):.12g}",
            }
            for n in (1, 2, 3, 4):
                vals = _arr_to_np(values[f"char{n}"])
                out[f"char{n}_mean"] = f"{float(np.mean(vals)):.12g}"
                out[f"char{n}_median"] = f"{float(np.median(vals)):.12g}"
                out[f"char{n}_std"] = f"{float(np.std(vals)):.12g}"
            corr = corr_by_bucket[(direction, length_bucket)]
            for n in (1, 2, 3, 4):
                v = corr.get(f"real_char{n}", float("nan"))
                out[f"spearman_real_char{n}"] = "" if not np.isfinite(v) else f"{float(v):.12g}"
            for n in (1, 2, 3, 4):
                v = corr.get(f"shuffle_char{n}", float("nan"))
                out[f"spearman_shuffle_char{n}"] = "" if not np.isfinite(v) else f"{float(v):.12g}"
            writer.writerow(out)


def _build_calibration(group_values: dict[tuple[str, int, str], dict[str, array]]) -> dict[str, Any]:
    grouped: dict[tuple[str, int], dict[str, dict[str, array]]] = {}
    for (direction, length_bucket, generator), values in group_values.items():
        grouped.setdefault((direction, length_bucket), {})[generator] = values
    rows_out: list[dict[str, Any]] = []
    for (direction, length_bucket) in sorted(grouped.keys()):
        by_gen = grouped[(direction, length_bucket)]
        real_vals = by_gen.get("REAL")
        rand_vals = by_gen.get("RAND_UNIGRAM")
        real = _arr_to_np(real_vals["span"]) if real_vals is not None else np.asarray([], dtype=np.float64)
        rand = _arr_to_np(rand_vals["span"]) if rand_vals is not None else np.asarray([], dtype=np.float64)
        real_ref = float(np.median(real)) if real.size else 0.0
        rand_ref = float(np.median(rand)) if rand.size else 0.0
        denom = float(real_ref - rand_ref)
        rows_out.append(
            {
                "direction": direction,
                "length_bucket": int(length_bucket),
                "real_ref": real_ref,
                "rand_ref": rand_ref,
                "denom": denom,
                "n_real": int(real.size),
                "n_rand": int(rand.size),
                "span_norm_valid": bool(denom > 0.0),
            }
        )
    return {
        "normalization": "span_norm = clamp((span_raw - rand_ref) / denom, 0, 1) when denom > 0",
        "calibrations": rows_out,
    }


def _write_convergence_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_convergence_header())
        writer.writeheader()
        for row in rows:
            out: dict[str, str] = {}
            for key in _convergence_header():
                value = row.get(key)
                if isinstance(value, float):
                    out[key] = f"{value:.12g}"
                else:
                    out[key] = str(value)
            writer.writerow(out)


def _run_checkpoint(
    *,
    summary_csv_path: Path,
    calibration_json_path: Path,
    convergence_csv_path: Path,
    group_values: dict[tuple[str, int, str], dict[str, array]],
    convergence_rows: list[dict[str, Any]],
) -> None:
    _write_summary_csv(summary_csv_path, group_values)
    _write_json(calibration_json_path, _build_calibration(group_values))
    _write_convergence_csv(convergence_csv_path, convergence_rows)


def run_suite(cfg: SuiteRunConfig) -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    npz_paths = discover_npz_paths(tokenized_dir=cfg.tokenized_dir, directions=cfg.directions)
    records = load_corpus_records(
        npz_paths,
        min_length=min(cfg.length_buckets),
        directions=cfg.directions,
    )
    if not records:
        raise ValueError("No records loaded for requested directions/lengths")
    record_map = {str(rec.path): rec for rec in records}
    unigram_by_direction = estimate_unigram_probs_by_direction(records)

    span_cfg = SpanHammingConfig(
        len_min=int(cfg.span_len_min),
        len_max=int(cfg.span_len_max),
        max_hd=int(cfg.span_max_hd),
        max_candidates_per_window=int(cfg.span_max_candidates_per_window),
        max_intervals_considered_per_start=int(cfg.span_max_intervals_per_start),
        min_quality_threshold=float(cfg.span_min_quality_threshold),
        debug_return_intervals=False,
    )
    span_backend = SpanHammingBackend(config=span_cfg)
    char_scorers = _build_char_baseline_scorers(
        enabled=cfg.enable_char_baselines,
        directions=cfg.directions,
    )

    plan_rows_all = build_stride_plan(
        records=records,
        directions=cfg.directions,
        length_buckets=cfg.length_buckets,
        global_seed=cfg.global_seed,
        min_stride=cfg.min_stride,
        stride_factor=cfg.stride_factor,
        max_windows_per_book_by_l=cfg.max_windows_per_book_by_l,
        fallback_max_windows=cfg.max_windows_fallback,
    )
    if int(cfg.shard_count) < 1:
        raise ValueError("SHARD_COUNT must be >= 1")
    if int(cfg.shard_index) < 0 or int(cfg.shard_index) >= int(cfg.shard_count):
        raise ValueError("SHARD_INDEX must satisfy 0 <= SHARD_INDEX < SHARD_COUNT")
    if cfg.shard_strategy not in {"book_hash_mod"}:
        raise ValueError("SHARD_STRATEGY must be 'book_hash_mod'")
    if int(cfg.shard_count) == 1:
        plan_rows = list(plan_rows_all)
    else:
        plan_rows = [
            row
            for row in plan_rows_all
            if _book_shard_index(
                book_id=str(row.book_id),
                shard_count=int(cfg.shard_count),
                global_seed=int(cfg.global_seed),
            )
            == int(cfg.shard_index)
        ]

    if cfg.run_dir is not None:
        run_dir = cfg.run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        shard_suffix = (
            f"__shard{int(cfg.shard_index)}of{int(cfg.shard_count)}"
            if int(cfg.shard_count) > 1
            else ""
        )
        run_dir = cfg.output_root / f"{_utc_now()}__span_hamming_nose_suite{shard_suffix}"
        run_dir.mkdir(parents=True, exist_ok=True)

    plan_csv = run_dir / "plan.csv"
    samples_csv = run_dir / "samples.csv"
    samples_jsonl = run_dir / "samples.jsonl"
    completed_rows_csv = run_dir / cfg.completion_log_basename
    book_manifest_csv = run_dir / "book_manifest.csv"
    summary_csv = run_dir / "summary.csv"
    calibration_json = run_dir / "calibration.json"
    convergence_csv = run_dir / "convergence.csv"
    run_config_json = run_dir / "run_config.json"
    resume_mode = bool(
        cfg.resume_if_run_dir_exists
        and cfg.run_dir is not None
        and (samples_csv.exists() or completed_rows_csv.exists() or run_config_json.exists())
    )

    if resume_mode:
        if plan_csv.exists():
            existing_plan = read_plan_csv(plan_csv)
            existing_ids = [row.row_id for row in existing_plan]
            expected_ids = [row.row_id for row in plan_rows]
            if existing_ids != expected_ids:
                raise ValueError(
                    "Resume plan mismatch: existing plan.csv does not match current resolved plan"
                )
        else:
            write_plan_csv(plan_csv, plan_rows)
    else:
        _clear_outputs(
            [
                plan_csv,
                samples_csv,
                samples_jsonl,
                completed_rows_csv,
                book_manifest_csv,
                summary_csv,
                calibration_json,
                convergence_csv,
                run_config_json,
            ]
        )
        write_plan_csv(plan_csv, plan_rows)

    git_meta = _git_meta(repo_root)
    shard_book_ids = sorted({row.book_id for row in plan_rows})
    shard_book_id_set = set(shard_book_ids)
    if (not resume_mode) or (not book_manifest_csv.exists()):
        _write_book_manifest(
            path=book_manifest_csv,
            records=records,
            shard_book_ids=shard_book_id_set,
        )
    run_config = {
        "suite_version": SUITE_VERSION,
        "token_key": NPZ_TOKEN_KEY,
        "git_sha": git_meta["git_sha"],
        "git_dirty": git_meta["git_dirty"],
        "global_seed": int(cfg.global_seed),
        "tokenized_dir": str(cfg.tokenized_dir),
        "directions": list(cfg.directions),
        "use_nose_only": bool(cfg.use_nose_only),
        "length_buckets": [int(x) for x in cfg.length_buckets],
        "min_stride": int(cfg.min_stride),
        "stride_factor": float(cfg.stride_factor),
        "max_windows_per_book_by_l": {str(k): int(v) for k, v in cfg.max_windows_per_book_by_l.items()},
        "max_windows_fallback": int(cfg.max_windows_fallback),
        "generators": list(cfg.generators),
        "corrupt_pcts": [int(x) for x in cfg.corrupt_pcts],
        "enable_convergence": bool(cfg.enable_convergence),
        "mean_tol": float(cfg.mean_tol),
        "std_tol": float(cfg.std_tol),
        "patience_batches": int(cfg.patience_batches),
        "max_batches": int(cfg.max_batches),
        "books_per_batch": (int(cfg.books_per_batch) if cfg.books_per_batch else None),
        "enable_char_baselines": bool(cfg.enable_char_baselines),
        "span_config": {
            "len_min": int(cfg.span_len_min),
            "len_max": int(cfg.span_len_max),
            "max_hd": int(cfg.span_max_hd),
            "max_candidates_per_window": int(cfg.span_max_candidates_per_window),
            "max_intervals_considered_per_start": int(cfg.span_max_intervals_per_start),
            "min_quality_threshold": float(cfg.span_min_quality_threshold),
        },
        "resolved_books": [
            {
                "book_id": rec.book_id,
                "path": str(rec.path),
                "direction": rec.direction,
                "n_tokens": int(rec.tokens.size),
            }
            for rec in records
        ],
        "resolved_book_count": int(len(records)),
        "shard_books": [
            {
                "book_id": rec.book_id,
                "path": str(rec.path),
                "direction": rec.direction,
                "n_tokens": int(rec.tokens.size),
            }
            for rec in records
            if rec.book_id in shard_book_id_set
        ],
        "corpus_list_hash": corpus_list_hash(records),
        "plan_rows_all": int(len(plan_rows_all)),
        "plan_rows_shard": int(len(plan_rows)),
        "shard_count": int(cfg.shard_count),
        "shard_index": int(cfg.shard_index),
        "shard_strategy": str(cfg.shard_strategy),
        "shard_book_count": int(len(shard_book_ids)),
        "resume_mode": bool(resume_mode),
        "completion_log": str(completed_rows_csv.name),
        "book_manifest": str(book_manifest_csv.name),
        "run_dir": str(run_dir),
        "started_at_utc": _utc_now(),
    }
    _write_json(run_config_json, run_config)

    by_bucket_book: dict[tuple[str, int], dict[str, list[PlanRow]]] = {}
    for row in plan_rows:
        bucket_key = (row.direction, int(row.length_bucket))
        by_bucket_book.setdefault(bucket_key, {}).setdefault(row.book_id, []).append(row)

    for bucket in by_bucket_book.values():
        for rows in bucket.values():
            rows.sort(key=lambda r: r.start)

    generators = [str(x).upper() for x in cfg.generators]
    if "REAL" not in generators:
        raise ValueError("GENERATORS must include REAL")

    completed_row_ids = _load_completed_row_ids(completed_rows_csv) if resume_mode else set()
    if resume_mode:
        group_values, existing_real_by_bucket, partial_generators_by_row = _load_existing_samples_state(
            samples_csv_path=samples_csv,
            completed_row_ids=completed_row_ids,
        )
        convergence_rows = _load_existing_convergence_rows(convergence_csv)
    else:
        group_values = {}
        existing_real_by_bucket = {}
        partial_generators_by_row = {}
        convergence_rows = []

    processed_real = int(sum(len(vals) for vals in existing_real_by_bucket.values()))
    run_started = time.perf_counter()
    total_real_rows_shard = int(len(plan_rows))
    total_buckets = int(len(by_bucket_book))
    for bucket_idx, bucket_key in enumerate(sorted(by_bucket_book.keys()), start=1):
        direction, length_bucket = bucket_key
        bucket_books_all = by_bucket_book[bucket_key]
        bucket_books: dict[str, list[PlanRow]] = {}
        for book_id, rows in bucket_books_all.items():
            pending = [row for row in rows if row.row_id not in completed_row_ids]
            if pending:
                bucket_books[book_id] = pending
        if not bucket_books:
            print(
                f"[span_hamming_nose] bucket skip {bucket_idx}/{total_buckets} "
                f"direction={direction} length={length_bucket} reason=already_completed",
                flush=True,
            )
            continue

        flat_rows = [row for book_id in sorted(bucket_books.keys()) for row in bucket_books[book_id]]
        print(
            f"[span_hamming_nose] bucket start {bucket_idx}/{total_buckets} "
            f"direction={direction} length={length_bucket} "
            f"pending_rows={len(flat_rows)} pending_books={len(bucket_books)}",
            flush=True,
        )
        book_batches = _bucket_book_batches(
            plan_rows=flat_rows,
            books_per_batch=cfg.books_per_batch,
            max_batches=cfg.max_batches,
        )
        if not book_batches:
            continue

        real_scores: list[float] = list(existing_real_by_bucket.get(bucket_key, []))
        prev_mean: float | None = None
        prev_std: float | None = None
        patience = 0
        converged = False
        batch_start_idx = 1
        for prior in reversed(convergence_rows):
            if (
                str(prior.get("direction", "")).strip().lower() == direction
                and int(prior.get("length_bucket", -1)) == int(length_bucket)
            ):
                prev_mean = _to_float(prior.get("mean_span_raw_real"))
                prev_std = _to_float(prior.get("std_span_raw_real"))
                patience = int(prior.get("patience_count", 0))
                converged = bool(prior.get("converged", False))
                batch_start_idx = int(prior.get("batch_idx", 0)) + 1
                break

        total_batches = int(len(book_batches) + batch_start_idx - 1)
        for batch_idx, book_ids in enumerate(book_batches, start=batch_start_idx):
            if cfg.enable_convergence and converged:
                break
            batch_started = time.perf_counter()
            planned_windows_batch = int(sum(len(bucket_books[book_id]) for book_id in book_ids))
            batch_real = 0
            for book_id in book_ids:
                for plan in bucket_books[book_id]:
                    rec = record_map.get(plan.book_path)
                    if rec is None:
                        raise FileNotFoundError(f"Missing book referenced by plan: {plan.book_path}")
                    base_tokens = rec.tokens[plan.start : plan.start + plan.text_length]
                    if int(base_tokens.size) < int(plan.text_length):
                        continue
                    existing_generators = set(partial_generators_by_row.get(plan.row_id, set()))
                    seen_generators = set(existing_generators)
                    for generator in generators:
                        if generator in existing_generators:
                            continue
                        row = score_window_sample(
                            plan=plan,
                            base_tokens=base_tokens,
                            generator=generator,
                            global_seed=cfg.global_seed,
                            batch_index=batch_idx,
                            span_backend=span_backend,
                            unigram_probs=unigram_by_direction[direction],
                            corrupt_pcts=cfg.corrupt_pcts,
                            enable_char_baselines=cfg.enable_char_baselines,
                            char_baseline_scorers=char_scorers,
                        )
                        _append_csv_row(samples_csv, _sample_header(), _sample_to_csv_row(row))
                        if cfg.write_samples_jsonl:
                            _append_jsonl(samples_jsonl, row)
                        gk = (row["direction"], int(row["length_bucket"]), str(row["generator"]).upper())
                        bucket_vals = _get_or_create_group_bucket(group_values, gk)
                        bucket_vals["span"].append(float(row["span_raw"]))
                        bucket_vals["char1"].append(float(row["char1_score"]))
                        bucket_vals["char2"].append(float(row["char2_score"]))
                        bucket_vals["char3"].append(float(row["char3_score"]))
                        bucket_vals["char4"].append(float(row["char4_score"]))
                        seen_generators.add(str(row["generator"]).upper())
                        if row["generator"] == "REAL":
                            real_scores.append(float(row["span_raw"]))
                            batch_real += 1
                            processed_real += 1
                    if all(gen in seen_generators for gen in generators):
                        _append_completed_row(completed_rows_csv, plan)
                        completed_row_ids.add(plan.row_id)
                        partial_generators_by_row.pop(plan.row_id, None)
                    else:
                        partial_generators_by_row[plan.row_id] = seen_generators

            mean_now = float(np.mean(real_scores)) if real_scores else float("nan")
            std_now = float(np.std(real_scores)) if real_scores else float("nan")
            if prev_mean is None or not np.isfinite(prev_mean):
                delta_mean = float("inf")
            else:
                delta_mean = abs(mean_now - prev_mean) / max(abs(prev_mean), 1e-12)
            if prev_std is None or not np.isfinite(prev_std):
                delta_std = float("inf")
            else:
                delta_std = abs(std_now - prev_std) / max(abs(prev_std), 1e-12)

            stable = bool(np.isfinite(delta_mean) and np.isfinite(delta_std) and delta_mean < cfg.mean_tol and delta_std < cfg.std_tol)
            if stable:
                patience += 1
            else:
                patience = 0
            converged = bool(cfg.enable_convergence and patience >= int(cfg.patience_batches))

            convergence_rows.append(
                {
                    "direction": direction,
                    "length_bucket": int(length_bucket),
                    "batch_idx": int(batch_idx),
                    "books_in_batch": int(len(book_ids)),
                    "planned_windows_batch": int(planned_windows_batch),
                    "real_windows_batch": int(batch_real),
                    "real_windows_per_book_mean": (
                        float(batch_real) / float(len(book_ids)) if book_ids else float("nan")
                    ),
                    "real_windows_total": int(len(real_scores)),
                    "mean_span_raw_real": mean_now,
                    "std_span_raw_real": std_now,
                    "delta_mean_rel": delta_mean,
                    "delta_std_rel": delta_std,
                    "stable": bool(stable),
                    "patience_count": int(patience),
                    "converged": bool(converged),
                }
            )
            done_real_rows = int(len(completed_row_ids))
            elapsed = time.perf_counter() - run_started
            pct = (
                100.0 * float(done_real_rows) / float(total_real_rows_shard)
                if total_real_rows_shard > 0
                else 0.0
            )
            print(
                f"[span_hamming_nose] batch {batch_idx}/{total_batches} "
                f"direction={direction} length={length_bucket} "
                f"planned_windows={planned_windows_batch} real_batch={batch_real} "
                f"real_total={len(real_scores)} stable={stable} patience={patience} "
                f"progress={done_real_rows}/{total_real_rows_shard} ({pct:.1f}%) "
                f"batch_time={_format_duration(time.perf_counter() - batch_started)} "
                f"elapsed={_format_duration(elapsed)}",
                flush=True,
            )
            prev_mean = mean_now
            prev_std = std_now

            if int(cfg.checkpoint_every) > 0 and (processed_real % int(cfg.checkpoint_every) == 0):
                _run_checkpoint(
                    summary_csv_path=summary_csv,
                    calibration_json_path=calibration_json,
                    convergence_csv_path=convergence_csv,
                    group_values=group_values,
                    convergence_rows=convergence_rows,
                )
                elapsed = time.perf_counter() - run_started
                rate = (
                    float(len(completed_row_ids)) / max(1e-9, elapsed)
                    if elapsed > 0.0
                    else 0.0
                )
                print(
                    f"[span_hamming_nose] checkpoint "
                    f"completed_rows={len(completed_row_ids)} rate_rows_per_sec={rate:.3f} "
                    f"elapsed={_format_duration(elapsed)}",
                    flush=True,
                )

        print(
            f"[span_hamming_nose] bucket done direction={direction} length={length_bucket} "
            f"real_windows={len(real_scores)} converged={converged}",
            flush=True,
        )

    _run_checkpoint(
        summary_csv_path=summary_csv,
        calibration_json_path=calibration_json,
        convergence_csv_path=convergence_csv,
        group_values=group_values,
        convergence_rows=convergence_rows,
    )
    return run_dir


def main() -> int:
    cfg = _build_run_config()
    print(
        "[span_hamming_nose] setup: "
        f"tokenized_dir={cfg.tokenized_dir} directions={cfg.directions} "
        f"length_buckets={cfg.length_buckets} generators={cfg.generators} "
        f"convergence={cfg.enable_convergence} "
        f"shard={cfg.shard_index}/{cfg.shard_count} strategy={cfg.shard_strategy} "
        f"jsonl={cfg.write_samples_jsonl} resume={cfg.resume_if_run_dir_exists}",
        flush=True,
    )
    run_dir = run_suite(cfg)
    print(f"[span_hamming_nose] run_dir={run_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
