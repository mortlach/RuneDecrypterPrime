from __future__ import annotations

"""
Strict O4 FWD NOSE bridge damage-ladder canary v2.

IDE-friendly report-only runner. Edit CONFIG below and run from the IDE.

Purpose:
- consume the accepted O4 FWD NOSE runtime index;
- strict cut only, order 4 only, FWD only;
- run a small bounded overnight diagnostic over clean/damaged/null/control samples;
- save progress as it goes;
- resume safely after crash without wiping previous work;
- avoid repeated expensive scans for already committed samples;
- avoid duplicate hit rows by writing per-sample hit part files before summary commit.

Commit model:
- sample_o4_summary_rows.csv is the completed-sample commit log.
- A sample is complete iff it has a summary row.
- sample_rows.csv may contain attempted/incomplete samples and is not authoritative.
- hit rows are written to sample_o4_hit_parts/<safe_sample_id>.csv before summary commit.
- On restart, committed samples are skipped. Incomplete hit part files are removed/rebuilt.

This file must not write production scorer weights or candidate-ranking authority.
"""

import csv
import hashlib
import json
import os
import platform
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_strict_o4_fwd_bridge_reference_v1 import (  # noqa: E402
    RuntimeGroupRef,
    append_csv,
    hit_row,
    hamming_hits_for_group,
    load_runtime_npz,
    load_strict_o4_runtime_groups,
    summary_row,
    summarise_hits,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_target_actual_damage_models_v1 import (  # noqa: E402
    changed_fraction,
    empirical_probs,
    make_null_variant,
    make_target_damaged_variant,
    stable_int_seed,
)

# =============================================================================
# CONFIG: edit here, run from IDE
# =============================================================================

RUN_LABEL = "phaseB_strict_o4_fwd_nose_bridge_damage_ladder_canary_v2"
RUN_MODE = "overnight_5_clean_chunks"  # "smoke", "overnight_5_clean_chunks", "overnight_10_clean_chunks"
REPORT_ONLY = True
PRODUCTION_SCORER_CHANGE = False
REQUIRE_FWD_ONLY = True
ORDER = 4
CUT = "strict"
DIRECTION = "fwd"

# Resume hardening.
RESUME_MODE = True
FORCE_RESTART = False
CONTINUE_ON_SAMPLE_ERROR = False
WRITE_RUN_STATE_EVERY_SAMPLE = True
WRITE_HIT_PARTS = True

TOKENIZED_ROOT_REL = "../language_model_prime/lmprime_out/tokenized"
RUNTIME_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_lookup_index_v1/runtime_index_manifest.json"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_strict_o4_fwd_nose_bridge_damage_ladder_canary_v2"
)
BOOK_ORDER = "forward"
BOOK_SKIP = 0
EXCLUDE_BOOKS = ("1-0.txt", "10004.txt")
CHUNK_MAX_TOKENS = 500
GLOBAL_SEED = 20260507
DAMAGE_TOLERANCE = 0.01

# Strict O4 diagnostic lenses. Keep small and boring first.
MIN_PHRASE_TOKEN_LENGTH = 10
MAX_TOTAL_PHRASE_HD = 2
MAX_PHRASE_TOKEN_LENGTH: int | None = None

# Runtime guardrails. Smoke should finish on synthetic/tiny assets; overnight can
# increase these after smoke. Leave the full index unbounded only after canary
# evidence is good.
MODE_LIMITS: dict[str, dict[str, Any]] = {
    "smoke": {
        "num_clean_chunks": 1,
        "damage_levels": (0.30,),
        "damage_repeats_per_chunk": 1,
        "include_damage_models": ("independent_substitution", "burst_substitution"),
        "include_null_models": ("uniform_random", "block_shuffle_50"),
        "max_runtime_groups": 8,
        "max_phrase_rows_per_group": 2000,
        "write_hit_rows": True,
        "checkpoint_every_samples": 4,
        "checkpoint_every_seconds": 60.0,
    },
    "overnight_5_clean_chunks": {
        "num_clean_chunks": 5,
        "damage_levels": (0.20, 0.30, 0.40, 0.50, 0.60),
        "damage_repeats_per_chunk": 1,
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
        "max_runtime_groups": 250,
        "max_phrase_rows_per_group": 25000,
        "write_hit_rows": True,
        "checkpoint_every_samples": 10,
        "checkpoint_every_seconds": 300.0,
    },
    "overnight_10_clean_chunks": {
        "num_clean_chunks": 10,
        "damage_levels": (0.20, 0.30, 0.40, 0.50, 0.60),
        "damage_repeats_per_chunk": 1,
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
        "max_runtime_groups": 500,
        "max_phrase_rows_per_group": 50000,
        "write_hit_rows": False,
        "checkpoint_every_samples": 20,
        "checkpoint_every_seconds": 300.0,
    },
}

SAMPLE_FIELDS = [
    "sample_id", "config_hash", "source_kind", "model_name", "damage_level", "repeat_index", "seed", "book",
    "direction", "chunk_id", "token_count", "changed_fraction", "null_class",
]

SUMMARY_FIELDS = [
    "sample_id", "config_hash", "source_kind", "model_name", "damage_level", "repeat_index", "token_count",
    "changed_fraction", "groups_loaded", "phrase_rows_considered", "windows_considered",
    "verification_attempts", "hit_count", "exact_hit_count", "longest_exact_phrase_len",
    "longest_hit_phrase_len", "min_hd_at_len_ge_10", "min_hd_at_len_ge_12", "min_hd_at_len_ge_15",
    "selected_nonoverlap_exact_count", "selected_nonoverlap_exact_weight", "elapsed_seconds",
    "hit_part_path", "committed_utc",
]

HIT_FIELDS = [
    "sample_id", "config_hash", "source_kind", "model_name", "damage_level", "repeat_index", "candidate_start",
    "candidate_end", "phrase_id", "phrase_token_length", "word_token_lengths", "total_phrase_hd",
    "normalised_phrase_hd", "sum_count", "max_count", "sum_log_count", "max_log_count", "source_row_count",
]

PROGRESS_FIELDS = [
    "created_utc", "event", "config_hash", "samples_committed", "samples_skipped", "samples_failed",
    "total_samples_estimate", "elapsed_seconds", "last_sample_id", "groups_selected", "hit_rows_written",
]

FAILED_FIELDS = [
    "created_utc", "sample_id", "config_hash", "source_kind", "model_name", "damage_level", "repeat_index",
    "error_type", "error_message",
]

INCOMPLETE_FIELDS = [
    "created_utc", "sample_id", "config_hash", "reason", "action",
]


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
    source_kind: str
    model_name: str
    damage_level: str
    repeat_index: int
    seed: int
    clean_chunk: CleanChunk
    tokens: tuple[int, ...]
    changed_fraction: float
    null_class: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# Backwards-friendly alias for docs/tests that still mention write_json.
def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    write_json_atomic(path, payload)


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
            count += 1
    return count


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_csv_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            return [str(item) for item in next(reader)]
        except StopIteration:
            return []


def ensure_csv_ready(path: Path, fieldnames: Sequence[str], *, resume_mode: bool, force_restart: bool) -> None:
    if force_restart and path.exists():
        path.unlink()
    if path.exists() and resume_mode:
        header = read_csv_header(path)
        expected = list(fieldnames)
        if header != expected:
            raise ValueError(f"CSV header mismatch for {path}: expected={expected!r} actual={header!r}")
        return
    if not path.exists() or not resume_mode:
        write_csv(path, [], fieldnames)


def config_payload(
    *,
    runtime_manifest: Path,
    runtime_manifest_payload: Mapping[str, Any],
    limits: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "run_mode": RUN_MODE,
        "order": ORDER,
        "cut": CUT,
        "direction": DIRECTION,
        "runtime_manifest": repo_rel(runtime_manifest),
        "runtime_manifest_asset_id": runtime_manifest_payload.get("asset_id", ""),
        "runtime_manifest_sha256": hashlib.sha256(runtime_manifest.read_bytes()).hexdigest(),
        "runtime_groups_selected": int(limits["max_runtime_groups"]),
        "max_runtime_groups": int(limits["max_runtime_groups"]),
        "max_phrase_rows_per_group": int(limits["max_phrase_rows_per_group"]),
        "min_phrase_token_length": MIN_PHRASE_TOKEN_LENGTH,
        "max_phrase_token_length": MAX_PHRASE_TOKEN_LENGTH,
        "max_total_phrase_hd": MAX_TOTAL_PHRASE_HD,
        "damage_models": list(limits["include_damage_models"]),
        "damage_levels": [float(item) for item in limits["damage_levels"]],
        "null_models": list(limits["include_null_models"]),
        "num_clean_chunks": int(limits["num_clean_chunks"]),
        "damage_repeats_per_chunk": int(limits["damage_repeats_per_chunk"]),
        "book_order": BOOK_ORDER,
        "book_skip": BOOK_SKIP,
        "exclude_books": list(EXCLUDE_BOOKS),
        "chunk_max_tokens": CHUNK_MAX_TOKENS,
        "write_hit_rows": bool(limits["write_hit_rows"]),
        "write_hit_parts": WRITE_HIT_PARTS,
    }


def config_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_resume_config(output_dir: Path, current_hash: str) -> None:
    if FORCE_RESTART:
        return
    summary_path = output_dir / "sample_o4_summary_rows.csv"
    if summary_path.exists():
        for row in read_csv_rows(summary_path):
            existing = row.get("config_hash", "")
            if existing and existing != current_hash:
                raise RuntimeError(
                    "unsafe resume: existing summary rows use a different config_hash; "
                    "set FORCE_RESTART=True or use a fresh output directory"
                )
            if not existing and row.get("sample_id"):
                raise RuntimeError(
                    "unsafe resume: existing summary rows have no config_hash; "
                    "set FORCE_RESTART=True or use a fresh output directory"
                )
    manifest_path = output_dir / "run_manifest.json"
    if manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing_hash = existing_manifest.get("config_hash", "")
        if existing_hash and existing_hash != current_hash:
            raise RuntimeError(
                "unsafe resume: existing run_manifest config_hash differs from current config; "
                "set FORCE_RESTART=True or use a fresh output directory"
            )


def completed_sample_ids(summary_path: Path, current_config_hash: str | None = None) -> set[str]:
    return {
        row["sample_id"]
        for row in read_csv_rows(summary_path)
        if row.get("sample_id") and (current_config_hash is None or row.get("config_hash") == current_config_hash)
    }


def attempted_sample_ids(sample_path: Path, current_config_hash: str | None = None) -> set[str]:
    return {
        row["sample_id"]
        for row in read_csv_rows(sample_path)
        if row.get("sample_id") and (current_config_hash is None or row.get("config_hash") == current_config_hash)
    }


def safe_sample_file_id(sample_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.=-]+", "_", sample_id).strip("_")
    # Keep paths short on Windows while retaining enough readable context.
    digest = stable_int_seed("sample-file", sample_id)
    if len(safe) > 140:
        safe = safe[:140]
    return f"{safe}__{digest:016x}"


def sample_hit_part_path(output_dir: Path, sample_id: str) -> Path:
    return output_dir / "sample_o4_hit_parts" / f"{safe_sample_file_id(sample_id)}.csv"


def prepare_output_files(output_dir: Path, *, write_hit_rows: bool) -> None:
    if FORCE_RESTART and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_csv_ready(output_dir / "sample_rows.csv", SAMPLE_FIELDS, resume_mode=RESUME_MODE, force_restart=False)
    ensure_csv_ready(output_dir / "sample_o4_summary_rows.csv", SUMMARY_FIELDS, resume_mode=RESUME_MODE, force_restart=False)
    ensure_csv_ready(output_dir / "progress_rows.csv", PROGRESS_FIELDS, resume_mode=RESUME_MODE, force_restart=False)
    ensure_csv_ready(output_dir / "failed_sample_rows.csv", FAILED_FIELDS, resume_mode=RESUME_MODE, force_restart=False)
    ensure_csv_ready(output_dir / "incomplete_sample_rows.csv", INCOMPLETE_FIELDS, resume_mode=RESUME_MODE, force_restart=False)
    if write_hit_rows and WRITE_HIT_PARTS:
        (output_dir / "sample_o4_hit_parts").mkdir(parents=True, exist_ok=True)
    elif write_hit_rows:
        ensure_csv_ready(output_dir / "sample_o4_hit_rows.csv", HIT_FIELDS, resume_mode=RESUME_MODE, force_restart=False)


def remove_incomplete_hit_part(output_dir: Path, sample_id: str) -> None:
    part = sample_hit_part_path(output_dir, sample_id)
    if part.exists():
        part.unlink()


def write_progress(
    output_dir: Path,
    *,
    event: str,
    samples_committed: int,
    samples_skipped: int,
    samples_failed: int,
    total_samples_estimate: int,
    elapsed_seconds: float,
    last_sample_id: str,
    groups_selected: int,
    hit_rows_written: int,
    current_config_hash: str,
) -> None:
    append_csv(output_dir / "progress_rows.csv", [{
        "created_utc": utc_now(),
        "event": event,
        "config_hash": current_config_hash,
        "samples_committed": samples_committed,
        "samples_skipped": samples_skipped,
        "samples_failed": samples_failed,
        "total_samples_estimate": total_samples_estimate,
        "elapsed_seconds": f"{elapsed_seconds:.6f}",
        "last_sample_id": last_sample_id,
        "groups_selected": groups_selected,
        "hit_rows_written": hit_rows_written,
    }], PROGRESS_FIELDS)


def write_run_state(
    output_dir: Path,
    *,
    status: str,
    samples_committed: int,
    samples_skipped: int,
    samples_failed: int,
    total_samples_estimate: int,
    last_sample_id: str,
    elapsed_seconds: float,
    groups_selected: int,
    hit_rows_written: int,
    current_config_hash: str,
) -> None:
    write_json_atomic(output_dir / "run_state.json", {
        "run_label": RUN_LABEL,
        "run_mode": RUN_MODE,
        "status": status,
        "updated_utc": utc_now(),
        "config_hash": current_config_hash,
        "resume_mode": RESUME_MODE,
        "force_restart": FORCE_RESTART,
        "samples_committed_this_process": samples_committed,
        "samples_skipped_this_process": samples_skipped,
        "samples_failed_this_process": samples_failed,
        "total_samples_estimate": total_samples_estimate,
        "last_sample_id": last_sample_id,
        "elapsed_seconds": elapsed_seconds,
        "groups_selected": groups_selected,
        "hit_rows_written_this_process": hit_rows_written,
        "commit_marker": "sample_o4_summary_rows.csv",
    })


def tokenized_book_path(tokenized_root: Path, book: str, direction: str) -> Path:
    return tokenized_root / f"{book}_{direction}.npz"


def discover_fwd_books(tokenized_root: Path) -> list[str]:
    books = sorted(path.name[: -len("_fwd.npz")] for path in tokenized_root.glob("*_fwd.npz"))
    books = [book for book in books if book not in set(EXCLUDE_BOOKS)]
    if BOOK_ORDER == "reverse":
        books = list(reversed(books))
    elif BOOK_ORDER != "forward":
        raise ValueError(f"unknown BOOK_ORDER={BOOK_ORDER!r}")
    if BOOK_SKIP:
        books = books[int(BOOK_SKIP):]
    return books


def load_tokenized_nose(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(path, allow_pickle=False)
    missing = [name for name in ("pt_nose_data", "wli_nose_data") if name not in data.files]
    if missing:
        raise KeyError(f"tokenized file missing {missing}: {path}")
    tokens = np.asarray(data["pt_nose_data"], dtype=np.uint8)
    wli_flat = np.asarray(data["wli_nose_data"], dtype=np.uint8)
    if wli_flat.size % 2:
        raise ValueError(f"wli length not even: {path}")
    wli = wli_flat.reshape(-1, 2)
    if tokens.shape[0] != wli.shape[0]:
        raise ValueError(f"token/WLI length mismatch: {path}")
    return tokens, wli


def source_word_chunks_for_wli(wli: Sequence[Sequence[int]], *, max_tokens: int = CHUNK_MAX_TOKENS) -> list[tuple[int, int]]:
    arr = np.asarray(wli, dtype=np.int64)
    starts = np.flatnonzero((arr[:, 0] == 0) & (arr[:, 1] > 0)).astype(np.int64).tolist()
    chunks: list[tuple[int, int]] = []
    idx = 0
    n = int(arr.shape[0])
    while idx < len(starts):
        start = int(starts[idx])
        end = start
        cursor = idx
        while cursor < len(starts):
            word_start = int(starts[cursor])
            if word_start != end:
                break
            word_len = int(arr[word_start, 1])
            next_end = word_start + word_len
            if next_end > n or next_end - start > max_tokens:
                break
            end = next_end
            cursor += 1
        if end > start:
            chunks.append((start, end))
            while idx < len(starts) and starts[idx] < end:
                idx += 1
        else:
            idx += 1
    return chunks


def load_clean_chunks(tokenized_root: Path, *, limit: int) -> list[CleanChunk]:
    chunks: list[CleanChunk] = []
    for book in discover_fwd_books(tokenized_root):
        path = tokenized_book_path(tokenized_root, book, DIRECTION)
        tokens, wli = load_tokenized_nose(path)
        for chunk_index, (start, end) in enumerate(source_word_chunks_for_wli(wli)):
            chunks.append(
                CleanChunk(
                    book=book,
                    direction=DIRECTION,
                    chunk_index=chunk_index,
                    chunk_start=start,
                    chunk_end=end,
                    tokens=tuple(int(x) for x in tokens[start:end]),
                    wli=tuple((int(a), int(b)) for a, b in wli[start:end]),
                )
            )
            if len(chunks) >= limit:
                return chunks
    return chunks


def null_class(model_name: str) -> str:
    if model_name.startswith("block_shuffle_"):
        return "hard_local_order_control"
    return "ordinary_null"


def iter_samples(clean_chunk: CleanChunk, *, limits: Mapping[str, Any], global_probs: np.ndarray, book_probs: np.ndarray) -> Iterable[Sample]:
    clean = Sample(
        sample_id=f"{clean_chunk.chunk_id}|clean|none||r0",
        source_kind="clean",
        model_name="none",
        damage_level="",
        repeat_index=0,
        seed=stable_int_seed(GLOBAL_SEED, clean_chunk.chunk_id, "clean"),
        clean_chunk=clean_chunk,
        tokens=clean_chunk.tokens,
        changed_fraction=0.0,
        null_class="not_null",
    )
    yield clean
    for repeat in range(int(limits["damage_repeats_per_chunk"])):
        for level in limits["damage_levels"]:
            level_text = f"{float(level):.2f}"
            for model in limits["include_damage_models"]:
                seed = stable_int_seed(GLOBAL_SEED, clean_chunk.chunk_id, model, level_text, repeat)
                tokens = make_target_damaged_variant(
                    clean_chunk.tokens,
                    model_name=str(model),
                    target_fraction=float(level),
                    seed=seed,
                    wli=clean_chunk.wli,
                    global_probs=global_probs,
                    book_probs=book_probs,
                    tolerance=DAMAGE_TOLERANCE,
                )
                yield Sample(
                    sample_id=f"{clean_chunk.chunk_id}|damaged|{model}|{level_text}|r{repeat}",
                    source_kind="damaged",
                    model_name=str(model),
                    damage_level=level_text,
                    repeat_index=repeat,
                    seed=seed,
                    clean_chunk=clean_chunk,
                    tokens=tokens,
                    changed_fraction=changed_fraction(clean_chunk.tokens, tokens),
                    null_class="not_null",
                )
        for model in limits["include_null_models"]:
            seed = stable_int_seed(GLOBAL_SEED, clean_chunk.chunk_id, model, repeat)
            tokens = make_null_variant(clean_chunk.tokens, model_name=str(model), seed=seed, global_probs=global_probs)
            yield Sample(
                sample_id=f"{clean_chunk.chunk_id}|null|{model}||r{repeat}",
                source_kind="null_control",
                model_name=str(model),
                damage_level="",
                repeat_index=repeat,
                seed=seed,
                clean_chunk=clean_chunk,
                tokens=tokens,
                changed_fraction=changed_fraction(clean_chunk.tokens, tokens),
                null_class=null_class(str(model)),
            )


def sample_row(sample: Sample, current_config_hash: str) -> dict[str, Any]:
    return {
        "sample_id": sample.sample_id,
        "config_hash": current_config_hash,
        "source_kind": sample.source_kind,
        "model_name": sample.model_name,
        "damage_level": sample.damage_level,
        "repeat_index": sample.repeat_index,
        "seed": sample.seed,
        "book": sample.clean_chunk.book,
        "direction": sample.clean_chunk.direction,
        "chunk_id": sample.clean_chunk.chunk_id,
        "token_count": len(sample.tokens),
        "changed_fraction": f"{sample.changed_fraction:.12g}",
        "null_class": sample.null_class,
    }


def run_once() -> dict[str, Any]:
    if not REPORT_ONLY or PRODUCTION_SCORER_CHANGE:
        raise RuntimeError("strict O4 bridge canary must remain report-only")
    if (ORDER, CUT, DIRECTION) != (4, "strict", "fwd"):
        raise RuntimeError("strict O4 bridge canary is locked to order=4 cut=strict direction=fwd")
    limits = MODE_LIMITS[RUN_MODE]
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    tokenized_root = (REPO_ROOT / TOKENIZED_ROOT_REL).resolve()
    runtime_manifest = REPO_ROOT / RUNTIME_MANIFEST_REL
    runtime_manifest_payload = json.loads(runtime_manifest.read_text(encoding="utf-8"))
    write_hit_rows = bool(limits["write_hit_rows"])
    effective_config = config_payload(
        runtime_manifest=runtime_manifest,
        runtime_manifest_payload=runtime_manifest_payload,
        limits=limits,
    )
    current_config_hash = config_hash(effective_config)

    if output_dir.exists():
        validate_resume_config(output_dir, current_config_hash)
    prepare_output_files(output_dir, write_hit_rows=write_hit_rows)
    committed_at_start = completed_sample_ids(output_dir / "sample_o4_summary_rows.csv", current_config_hash)
    attempted_ids = attempted_sample_ids(output_dir / "sample_rows.csv", current_config_hash)

    groups = load_strict_o4_runtime_groups(
        runtime_manifest,
        min_phrase_token_length=MIN_PHRASE_TOKEN_LENGTH,
        max_phrase_token_length=MAX_PHRASE_TOKEN_LENGTH,
        max_groups=int(limits["max_runtime_groups"]),
    )
    clean_chunks = load_clean_chunks(tokenized_root, limit=int(limits["num_clean_chunks"]))
    if not clean_chunks:
        raise RuntimeError("no clean FWD chunks loaded")
    if any(chunk.direction != "fwd" for chunk in clean_chunks):
        raise RuntimeError("non-FWD clean chunk selected")
    global_probs = empirical_probs([token for chunk in clean_chunks for token in chunk.tokens])

    started = time.perf_counter()
    manifest = {
        "run_label": RUN_LABEL,
        "run_mode": RUN_MODE,
        "created_utc": utc_now(),
        "config_hash": current_config_hash,
        "effective_config": effective_config,
        "report_only": REPORT_ONLY,
        "production_scorer_change": PRODUCTION_SCORER_CHANGE,
        "direction": DIRECTION,
        "order": ORDER,
        "cut": CUT,
        "resume_mode": RESUME_MODE,
        "force_restart": FORCE_RESTART,
        "commit_marker": "sample_o4_summary_rows.csv",
        "hit_row_storage": "per_sample_part_files" if write_hit_rows and WRITE_HIT_PARTS else "single_csv_or_disabled",
        "runtime_manifest": repo_rel(runtime_manifest),
        "output_dir": repo_rel(output_dir),
        "min_phrase_token_length": MIN_PHRASE_TOKEN_LENGTH,
        "max_total_phrase_hd": MAX_TOTAL_PHRASE_HD,
        "max_runtime_groups": int(limits["max_runtime_groups"]),
        "max_phrase_rows_per_group": int(limits["max_phrase_rows_per_group"]),
        "clean_chunks": len(clean_chunks),
        "runtime_groups_selected": len(groups),
        "completed_samples_at_start": len(committed_at_start),
        "limits": dict(limits),
        "machine": {"python": sys.version.split()[0], "platform": platform.platform(), "cpu_logical": os.cpu_count()},
    }
    write_json_atomic(output_dir / "run_manifest.json", manifest)

    total_samples_estimate = len(clean_chunks) * (
        1
        + len(tuple(limits["damage_levels"])) * len(tuple(limits["include_damage_models"])) * int(limits["damage_repeats_per_chunk"])
        + len(tuple(limits["include_null_models"])) * int(limits["damage_repeats_per_chunk"])
    )

    loaded_payloads: list[tuple[RuntimeGroupRef, Mapping[str, np.ndarray]]] = []
    for group in groups:
        loaded_payloads.append(
            (
                group,
                load_runtime_npz(REPO_ROOT, group, max_phrase_rows=int(limits["max_phrase_rows_per_group"])),
            )
        )

    samples_committed = 0
    samples_skipped = 0
    samples_failed = 0
    hit_rows_written = 0
    last_sample_id = ""
    last_checkpoint_at = time.perf_counter()
    completed = set(committed_at_start)

    write_progress(
        output_dir,
        event="start_or_resume",
        samples_committed=samples_committed,
        samples_skipped=samples_skipped,
        samples_failed=samples_failed,
        total_samples_estimate=total_samples_estimate,
        elapsed_seconds=0.0,
        last_sample_id="",
        groups_selected=len(groups),
        hit_rows_written=hit_rows_written,
        current_config_hash=current_config_hash,
    )

    for chunk in clean_chunks:
        book_probs = empirical_probs(chunk.tokens)
        for sample in iter_samples(chunk, limits=limits, global_probs=global_probs, book_probs=book_probs):
            last_sample_id = sample.sample_id
            if sample.sample_id in completed:
                samples_skipped += 1
                continue
            remove_incomplete_hit_part(output_dir, sample.sample_id)
            if sample.sample_id not in attempted_ids:
                append_csv(output_dir / "sample_rows.csv", [sample_row(sample, current_config_hash)], SAMPLE_FIELDS)
                attempted_ids.add(sample.sample_id)
            if WRITE_RUN_STATE_EVERY_SAMPLE:
                write_run_state(
                    output_dir,
                    status="running_sample",
                    samples_committed=samples_committed,
                    samples_skipped=samples_skipped,
                    samples_failed=samples_failed,
                    total_samples_estimate=total_samples_estimate,
                    last_sample_id=sample.sample_id,
                    elapsed_seconds=time.perf_counter() - started,
                    groups_selected=len(groups),
                    hit_rows_written=hit_rows_written,
                    current_config_hash=current_config_hash,
                )
            try:
                sample_started = time.perf_counter()
                hits = []
                phrase_rows_considered = 0
                windows_considered = 0
                attempts = 0
                for group, payload in loaded_payloads:
                    group_hits, phrase_count, windows, group_attempts = hamming_hits_for_group(
                        sample_id=sample.sample_id,
                        source_kind=sample.source_kind,
                        model_name=sample.model_name,
                        damage_level=sample.damage_level,
                        repeat_index=sample.repeat_index,
                        tokens=sample.tokens,
                        group=group,
                        payload=payload,
                        max_total_phrase_hd=MAX_TOTAL_PHRASE_HD,
                    )
                    hits.extend(group_hits)
                    phrase_rows_considered += phrase_count
                    windows_considered += windows
                    attempts += group_attempts
                summary = summarise_hits(
                    sample_id=sample.sample_id,
                    source_kind=sample.source_kind,
                    model_name=sample.model_name,
                    damage_level=sample.damage_level,
                    repeat_index=sample.repeat_index,
                    token_count=len(sample.tokens),
                    changed_fraction=sample.changed_fraction,
                    groups_loaded=len(loaded_payloads),
                    phrase_rows_considered=phrase_rows_considered,
                    windows_considered=windows_considered,
                    verification_attempts=attempts,
                    hits=hits,
                    elapsed_seconds=time.perf_counter() - sample_started,
                )
                hit_part_rel = ""
                if write_hit_rows:
                    hit_rows = [hit_row(hit) for hit in hits]
                    hit_rows = [{**row, "config_hash": current_config_hash} for row in hit_rows]
                    if WRITE_HIT_PARTS:
                        part_path = sample_hit_part_path(output_dir, sample.sample_id)
                        # Rewrite the part from scratch. If crash happens before summary commit,
                        # restart deletes and rebuilds this part.
                        written = write_csv(part_path, hit_rows, HIT_FIELDS)
                        hit_part_rel = repo_rel(part_path)
                    else:
                        written = append_csv(output_dir / "sample_o4_hit_rows.csv", hit_rows, HIT_FIELDS)
                    hit_rows_written += written
                row = summary_row(summary)
                row["config_hash"] = current_config_hash
                row["hit_part_path"] = hit_part_rel
                row["committed_utc"] = utc_now()
                # Commit marker: once this row exists, this sample is considered done.
                append_csv(output_dir / "sample_o4_summary_rows.csv", [row], SUMMARY_FIELDS)
                completed.add(sample.sample_id)
                samples_committed += 1
            except Exception as exc:
                samples_failed += 1
                remove_incomplete_hit_part(output_dir, sample.sample_id)
                append_csv(output_dir / "failed_sample_rows.csv", [{
                    "created_utc": utc_now(),
                    "sample_id": sample.sample_id,
                    "config_hash": current_config_hash,
                    "source_kind": sample.source_kind,
                    "model_name": sample.model_name,
                    "damage_level": sample.damage_level,
                    "repeat_index": sample.repeat_index,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }], FAILED_FIELDS)
                write_run_state(
                    output_dir,
                    status="failed_sample",
                    samples_committed=samples_committed,
                    samples_skipped=samples_skipped,
                    samples_failed=samples_failed,
                    total_samples_estimate=total_samples_estimate,
                    last_sample_id=sample.sample_id,
                    elapsed_seconds=time.perf_counter() - started,
                    groups_selected=len(groups),
                    hit_rows_written=hit_rows_written,
                    current_config_hash=current_config_hash,
                )
                if not CONTINUE_ON_SAMPLE_ERROR:
                    raise
            elapsed = time.perf_counter() - started
            now = time.perf_counter()
            sample_checkpoint = samples_committed > 0 and samples_committed % int(limits["checkpoint_every_samples"]) == 0
            time_checkpoint = (now - last_checkpoint_at) >= float(limits["checkpoint_every_seconds"])
            if sample_checkpoint or time_checkpoint:
                write_progress(
                    output_dir,
                    event="checkpoint",
                    samples_committed=samples_committed,
                    samples_skipped=samples_skipped,
                    samples_failed=samples_failed,
                    total_samples_estimate=total_samples_estimate,
                    elapsed_seconds=elapsed,
                    last_sample_id=sample.sample_id,
                    groups_selected=len(groups),
                    hit_rows_written=hit_rows_written,
                    current_config_hash=current_config_hash,
                )
                last_checkpoint_at = now
                write_run_state(
                    output_dir,
                    status="running",
                    samples_committed=samples_committed,
                    samples_skipped=samples_skipped,
                    samples_failed=samples_failed,
                    total_samples_estimate=total_samples_estimate,
                    last_sample_id=sample.sample_id,
                    elapsed_seconds=elapsed,
                    groups_selected=len(groups),
                    hit_rows_written=hit_rows_written,
                    current_config_hash=current_config_hash,
                )

    elapsed = time.perf_counter() - started
    # Capture sample_rows-only attempts that were not committed. This usually means
    # an interrupted prior process or a newly failed sample.
    final_completed = completed_sample_ids(output_dir / "sample_o4_summary_rows.csv", current_config_hash)
    final_attempted = attempted_sample_ids(output_dir / "sample_rows.csv", current_config_hash)
    incomplete = sorted(final_attempted - final_completed)
    for sample_id in incomplete:
        append_csv(output_dir / "incomplete_sample_rows.csv", [{
            "created_utc": utc_now(),
            "sample_id": sample_id,
            "config_hash": current_config_hash,
            "reason": "attempted_without_summary_commit",
            "action": "will_retry_on_next_resume",
        }], INCOMPLETE_FIELDS)

    final = {
        **manifest,
        "status": "complete" if samples_failed == 0 else "complete_with_sample_failures",
        "finished_utc": utc_now(),
        "elapsed_seconds": elapsed,
        "config_hash": current_config_hash,
        "effective_config": effective_config,
        "samples_committed_this_process": samples_committed,
        "samples_skipped_this_process": samples_skipped,
        "samples_failed_this_process": samples_failed,
        "completed_samples_total": len(final_completed),
        "incomplete_samples_total": len(incomplete),
        "total_samples_estimate": total_samples_estimate,
        "hit_rows_written_this_process": hit_rows_written,
        "files": {
            "sample_rows": repo_rel(output_dir / "sample_rows.csv"),
            "sample_o4_summary_rows": repo_rel(output_dir / "sample_o4_summary_rows.csv"),
            "sample_o4_hit_parts_dir": repo_rel(output_dir / "sample_o4_hit_parts") if write_hit_rows and WRITE_HIT_PARTS else "",
            "sample_o4_hit_rows": repo_rel(output_dir / "sample_o4_hit_rows.csv") if write_hit_rows and not WRITE_HIT_PARTS else "",
            "progress_rows": repo_rel(output_dir / "progress_rows.csv"),
            "failed_sample_rows": repo_rel(output_dir / "failed_sample_rows.csv"),
            "incomplete_sample_rows": repo_rel(output_dir / "incomplete_sample_rows.csv"),
            "run_state": repo_rel(output_dir / "run_state.json"),
        },
    }
    write_json_atomic(output_dir / "final_summary.json", final)
    write_run_state(
        output_dir,
        status=str(final["status"]),
        samples_committed=samples_committed,
        samples_skipped=samples_skipped,
        samples_failed=samples_failed,
        total_samples_estimate=total_samples_estimate,
        last_sample_id=last_sample_id,
        elapsed_seconds=elapsed,
        groups_selected=len(groups),
        hit_rows_written=hit_rows_written,
        current_config_hash=current_config_hash,
    )
    write_progress(
        output_dir,
        event="complete",
        samples_committed=samples_committed,
        samples_skipped=samples_skipped,
        samples_failed=samples_failed,
        total_samples_estimate=total_samples_estimate,
        elapsed_seconds=elapsed,
        last_sample_id=last_sample_id,
        groups_selected=len(groups),
        hit_rows_written=hit_rows_written,
        current_config_hash=current_config_hash,
    )
    (output_dir / "readout.md").write_text(
        "\n".join([
            f"# {RUN_LABEL}",
            "",
            "Report-only strict O4 FWD bridge canary with resume hardening.",
            f"- status: `{final['status']}`",
            f"- run_mode: `{RUN_MODE}`",
            f"- completed_samples_total: `{len(final_completed)}`",
            f"- samples_committed_this_process: `{samples_committed}`",
            f"- samples_skipped_this_process: `{samples_skipped}`",
            f"- samples_failed_this_process: `{samples_failed}`",
            f"- incomplete_samples_total: `{len(incomplete)}`",
            f"- runtime groups selected: `{len(groups)}`",
            f"- hit rows written this process: `{hit_rows_written}`",
            f"- elapsed_seconds: `{elapsed:.2f}`",
            "- commit marker: `sample_o4_summary_rows.csv`",
            "- production scorer change: `false`",
            "",
        ]) + "\n",
        encoding="utf-8",
    )
    return final


if __name__ == "__main__":
    print(json.dumps(run_once(), indent=2, sort_keys=True))
