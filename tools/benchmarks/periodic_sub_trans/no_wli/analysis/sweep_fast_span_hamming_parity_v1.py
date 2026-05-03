from __future__ import annotations

"""
Report-only S1f0b parity sweep for the optional fast span-Hamming backend.

No runtime solver behaviour changes. No CLI arguments. Edit constants below.
"""

import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence


RUN_LABEL = "fast_span_hamming_parity_sweep_v1"

UNIQUE_PARTIAL_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_partial_text_review_v1/unique_partial_text_rows.csv"
)
S1_PAIR_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fast_span_hamming_parity_sweep_v1"
)

# Canary passed; 0 means all S1 token hashes.
TOKEN_HASH_LIMIT_FOR_SWEEP = 0
PROGRESS_EVERY_ROWS = 25

SPAN_CONFIG_SPECS = (
    dict(
        config_id="raw_selected_len3_14_hd2_cap256__s1b_default",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel="assets/hamming_raw_1g",
    ),
    dict(
        config_id="raw_selected_len3_14_hd0_exact",
        len_min=3,
        len_max=14,
        max_hd=0,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel="assets/hamming_raw_1g",
    ),
    dict(
        config_id="raw_selected_len3_14_hd1",
        len_min=3,
        len_max=14,
        max_hd=1,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel="assets/hamming_raw_1g",
    ),
    dict(
        config_id="raw_selected_len4_14_hd1",
        len_min=4,
        len_max=14,
        max_hd=1,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel="assets/hamming_raw_1g",
    ),
    dict(
        config_id="raw_selected_len5_8_hd2_fixture_like",
        len_min=5,
        len_max=8,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel="assets/hamming_raw_1g",
    ),
    dict(
        config_id="raw_selected_len6_14_hd2_longer",
        len_min=6,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel="assets/hamming_raw_1g",
    ),
    dict(
        config_id="raw_selected_len3_14_hd2_cap512",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=512,
        require_selected=True,
        wordlist_rel="assets/hamming_raw_1g",
    ),
    dict(
        config_id="raw_selected_len3_14_hd2_cap1024",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=1024,
        require_selected=True,
        wordlist_rel="assets/hamming_raw_1g",
    ),
    dict(
        config_id="raw_all_len3_14_hd2_cap256",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=False,
        wordlist_rel="assets/hamming_raw_1g",
    ),
)


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.scoring.span_hamming.backend import SpanHammingBackend  # noqa: E402
from rune_decrypter_prime.scoring.span_hamming.fast_backend import (  # noqa: E402
    FastSpanHammingBackend,
    fast_span_hamming_available,
)
from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig, SpanHammingStats  # noqa: E402


UNIQUE_PARTIAL_ROWS = REPO_ROOT / UNIQUE_PARTIAL_ROWS_REL
S1_PAIR_ROWS = REPO_ROOT / S1_PAIR_ROWS_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class SpanSpec:
    config_id: str
    len_min: int
    len_max: int
    max_hd: int
    max_candidates_per_window: int
    require_selected: bool
    wordlist_rel: str


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_numeric_tokens(text: str) -> tuple[int, ...]:
    values = tuple(int(part) for part in str(text).split() if part.strip())
    for value in values:
        if value < 0 or value > 28:
            raise ValueError(f"numeric rune token out of range 0..28: {value}")
    return values


def _read_required_s1_token_hashes(limit: int) -> list[str]:
    required: list[str] = []
    seen: set[str] = set()
    with S1_PAIR_ROWS.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            for key in ("winner_token_hash", "challenger_token_hash"):
                token_hash = str(row.get(key, "")).strip()
                if token_hash and token_hash not in seen:
                    seen.add(token_hash)
                    required.append(token_hash)
                    if limit and len(required) >= limit:
                        return required
    return required


def _read_token_rows(limit: int) -> dict[str, tuple[int, ...]]:
    required = _read_required_s1_token_hashes(limit)
    required_set = set(required)
    loaded: dict[str, tuple[int, ...]] = {}
    with UNIQUE_PARTIAL_ROWS.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            token_hash = str(row.get("partial_text_hash", "")).strip()
            token_text = str(row.get("token_sequence_text", "")).strip()
            if not token_hash or token_hash not in required_set or not token_text:
                continue
            loaded[token_hash] = _parse_numeric_tokens(token_text)
            if len(loaded) >= len(required):
                break
    missing = [token_hash for token_hash in required if token_hash not in loaded]
    if missing:
        raise RuntimeError(f"missing S1 token hashes in unique partial rows: {len(missing)}")
    return {token_hash: loaded[token_hash] for token_hash in required}


def _span_config(spec: SpanSpec) -> SpanHammingConfig:
    return SpanHammingConfig(
        len_min=spec.len_min,
        len_max=spec.len_max,
        max_hd=spec.max_hd,
        max_candidates_per_window=spec.max_candidates_per_window,
        debug_return_intervals=True,
    )


def _build_backends(spec: SpanSpec) -> tuple[SpanHammingBackend | None, FastSpanHammingBackend | None, str]:
    wordlist_dir = REPO_ROOT / spec.wordlist_rel
    if not wordlist_dir.exists():
        return None, None, f"missing_wordlist_dir:{spec.wordlist_rel}"
    cfg = _span_config(spec)
    return (
        SpanHammingBackend(config=cfg, wordlist_dir=wordlist_dir, require_selected=spec.require_selected),
        FastSpanHammingBackend(config=cfg, wordlist_dir=wordlist_dir, require_selected=spec.require_selected),
        "",
    )


def _stats_compare(left: SpanHammingStats, right: SpanHammingStats) -> list[str]:
    mismatches: list[str] = []
    fields = (
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
        "selected_intervals",
    )
    for field in fields:
        left_value = getattr(left, field)
        right_value = getattr(right, field)
        if isinstance(left_value, float):
            if abs(float(left_value) - float(right_value)) > 1e-12:
                mismatches.append(field)
        elif isinstance(left_value, tuple) and left_value and isinstance(left_value[0], float):
            if len(left_value) != len(right_value):
                mismatches.append(field)
            elif any(abs(float(a) - float(b)) > 1e-12 for a, b in zip(left_value, right_value)):
                mismatches.append(field)
        elif left_value != right_value:
            mismatches.append(field)
    return mismatches


def _time_score(backend: Any, tokens: Sequence[int]) -> tuple[SpanHammingStats, float]:
    start = time.perf_counter()
    stats = backend.score(tokens)
    return stats, (time.perf_counter() - start) * 1000.0


def _write_csv(path: Path, rows: list[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _build_readout(summary: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Fast Span-Hamming Parity Sweep v1",
            "",
            "## Purpose",
            "",
            "Check optional C++ fast span-Hamming parity against Python SpanHammingBackend on S1 numeric tokens.",
            "",
            "## Result",
            "",
            f"- token hashes: {summary['token_hash_count']}",
            f"- config count: {summary['config_count']}",
            f"- result rows: {summary['result_row_count']}",
            f"- skipped config count: {summary['skipped_config_count']}",
            f"- parity failed rows: {summary['parity_failed_row_count']}",
            f"- mean speedup: {summary['mean_speedup_ratio']:.3f}x",
            f"- median speedup: {summary['median_speedup_ratio']:.3f}x",
            "",
            "## Caveats",
            "",
            "- Report-only only; no runtime solver behaviour changed.",
            "- Python SpanHammingBackend remains the reference.",
            "- Numeric rune/base-29 token sequences only.",
        ]
    ) + "\n"


def run_sweep() -> dict[str, Any]:
    if not fast_span_hamming_available():
        raise RuntimeError("optional _span_hamming_fast extension is not built")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tokens_by_hash = _read_token_rows(TOKEN_HASH_LIMIT_FOR_SWEEP)
    specs = [SpanSpec(**row) for row in SPAN_CONFIG_SPECS]
    total_work = len(tokens_by_hash) * len(specs)
    completed = 0
    start_time = time.perf_counter()
    result_rows: list[dict[str, Any]] = []
    skipped_configs: list[dict[str, Any]] = []

    print(
        f"[fast_span_hamming_parity] start token_hashes={len(tokens_by_hash)} "
        f"configs={len(specs)} total_rows={total_work}",
        flush=True,
    )

    for spec in specs:
        py_backend, fast_backend, skip_reason = _build_backends(spec)
        if skip_reason:
            skipped_configs.append({"config_id": spec.config_id, "skip_reason": skip_reason})
            completed += len(tokens_by_hash)
            continue
        assert py_backend is not None
        assert fast_backend is not None

        for token_hash, tokens in tokens_by_hash.items():
            py_stats, py_ms = _time_score(py_backend, tokens)
            fast_stats, fast_ms = _time_score(fast_backend, tokens)
            mismatches = _stats_compare(py_stats, fast_stats)
            speedup = py_ms / fast_ms if fast_ms > 0 else 0.0
            completed += 1
            result_rows.append(
                {
                    "config_id": spec.config_id,
                    "token_hash": token_hash,
                    "token_length": len(tokens),
                    "parity_ok": 1 if not mismatches else 0,
                    "mismatch_fields": ";".join(mismatches),
                    "python_ms": f"{py_ms:.6f}",
                    "fast_ms": f"{fast_ms:.6f}",
                    "speedup_ratio": f"{speedup:.6f}",
                    "n_candidates_considered": py_stats.n_candidates_considered,
                    "n_candidates_pruned_cap": py_stats.n_candidates_pruned_cap,
                    "n_intervals_selected": py_stats.n_intervals_selected,
                }
            )

            if completed == 1 or completed % PROGRESS_EVERY_ROWS == 0 or completed == total_work:
                elapsed = time.perf_counter() - start_time
                rate = completed / elapsed if elapsed > 0 else 0.0
                remaining = max(0, total_work - completed)
                eta = remaining / rate if rate > 0 else 0.0
                print(
                    f"[fast_span_hamming_parity] progress {completed}/{total_work} "
                    f"elapsed={elapsed/60.0:.1f}m eta={eta/60.0:.1f}m "
                    f"last_config={spec.config_id}",
                    flush=True,
                )

    speedups = [float(row["speedup_ratio"]) for row in result_rows if int(row["parity_ok"]) == 1]
    parity_failed = [row for row in result_rows if int(row["parity_ok"]) != 1]
    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_s1_pair_rows": _repo_rel(S1_PAIR_ROWS),
        "input_unique_partial_rows": _repo_rel(UNIQUE_PARTIAL_ROWS),
        "output_dir": _repo_rel(OUTPUT_DIR),
        "token_hash_limit_for_sweep": TOKEN_HASH_LIMIT_FOR_SWEEP,
        "token_hash_count": len(tokens_by_hash),
        "config_count": len(specs),
        "skipped_config_count": len(skipped_configs),
        "result_row_count": len(result_rows),
        "parity_failed_row_count": len(parity_failed),
        "mean_speedup_ratio": mean(speedups) if speedups else 0.0,
        "median_speedup_ratio": median(speedups) if speedups else 0.0,
        "min_speedup_ratio": min(speedups) if speedups else 0.0,
        "max_speedup_ratio": max(speedups) if speedups else 0.0,
        "elapsed_seconds": time.perf_counter() - start_time,
        "configs": [asdict(spec) for spec in specs],
        "skipped_configs": skipped_configs,
    }

    _write_csv(
        OUTPUT_DIR / "fast_span_hamming_parity_sweep_rows.csv",
        result_rows,
        (
            "config_id",
            "token_hash",
            "token_length",
            "parity_ok",
            "mismatch_fields",
            "python_ms",
            "fast_ms",
            "speedup_ratio",
            "n_candidates_considered",
            "n_candidates_pruned_cap",
            "n_intervals_selected",
        ),
    )
    _write_csv(
        OUTPUT_DIR / "fast_span_hamming_parity_sweep_skipped_configs.csv",
        skipped_configs,
        ("config_id", "skip_reason"),
    )
    (OUTPUT_DIR / "fast_span_hamming_parity_sweep_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "fast_span_hamming_parity_sweep_readout.md").write_text(
        _build_readout(summary),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    summary = run_sweep()
    print(
        "[fast_span_hamming_parity] done "
        f"rows={summary['result_row_count']} "
        f"failed={summary['parity_failed_row_count']} "
        f"mean_speedup={summary['mean_speedup_ratio']:.3f}x "
        f"output={summary['output_dir']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
