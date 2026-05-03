from __future__ import annotations

"""
Report-only S1f0 parity and timing probe for the optional fast span-Hamming backend.

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


RUN_LABEL = "span_hamming_fast_backend_probe_v1"

UNIQUE_PARTIAL_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_partial_text_review_v1/unique_partial_text_rows.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_fast_backend_probe_v1"
)

# Keep this small. This is a parity/speed probe, not the full S1f calibration.
TOKEN_HASH_LIMIT_FOR_PROBE = 20

SPAN_PROBE_CONFIGS = (
    {
        "config_id": "raw_selected_len3_14_hd2_cap256__s1b_default",
        "len_min": 3,
        "len_max": 14,
        "max_hd": 2,
        "max_candidates_per_window": 256,
        "require_selected": True,
        "wordlist_rel": "assets/hamming_raw_1g",
    },
    {
        "config_id": "raw_selected_len3_14_hd0_exact",
        "len_min": 3,
        "len_max": 14,
        "max_hd": 0,
        "max_candidates_per_window": 256,
        "require_selected": True,
        "wordlist_rel": "assets/hamming_raw_1g",
    },
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
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class ProbeConfig:
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


def _read_token_rows(limit: int) -> dict[str, tuple[int, ...]]:
    rows: dict[str, tuple[int, ...]] = {}
    with UNIQUE_PARTIAL_ROWS.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            token_hash = str(row.get("partial_text_hash", "")).strip()
            token_text = str(row.get("token_sequence_text", "")).strip()
            if not token_hash or not token_text:
                continue
            rows[token_hash] = _parse_numeric_tokens(token_text)
            if limit and len(rows) >= limit:
                break
    return rows


def _span_config(spec: ProbeConfig) -> SpanHammingConfig:
    return SpanHammingConfig(
        len_min=spec.len_min,
        len_max=spec.len_max,
        max_hd=spec.max_hd,
        max_candidates_per_window=spec.max_candidates_per_window,
        debug_return_intervals=True,
    )


def _stats_compare(left: SpanHammingStats, right: SpanHammingStats) -> list[str]:
    mismatches: list[str] = []
    scalar_fields = (
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
    for field in scalar_fields:
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


def _build_backend_pair(spec: ProbeConfig) -> tuple[SpanHammingBackend, FastSpanHammingBackend]:
    cfg = _span_config(spec)
    wordlist_dir = REPO_ROOT / spec.wordlist_rel
    return (
        SpanHammingBackend(
            config=cfg,
            wordlist_dir=wordlist_dir,
            require_selected=spec.require_selected,
        ),
        FastSpanHammingBackend(
            config=cfg,
            wordlist_dir=wordlist_dir,
            require_selected=spec.require_selected,
        ),
    )


def _time_score(backend: Any, tokens: Sequence[int]) -> tuple[SpanHammingStats, float]:
    start = time.perf_counter()
    stats = backend.score(tokens)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return stats, elapsed_ms


def _write_csv(path: Path, rows: list[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _build_readout(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Span-Hamming Fast Backend Probe v1",
        "",
        "## Purpose",
        "",
        "Report-only parity and timing probe for the optional C++ span-Hamming backend.",
        "",
        "## Result",
        "",
        f"- token hashes tested: {summary['token_hash_count']}",
        f"- config count: {summary['config_count']}",
        f"- parity failed rows: {summary['parity_failed_row_count']}",
        f"- mean speedup: {summary['mean_speedup_ratio']:.3f}x",
        f"- median speedup: {summary['median_speedup_ratio']:.3f}x",
        "",
        "## Caveats",
        "",
        "- This does not change runtime solver behaviour.",
        "- Python SpanHammingBackend remains the reference implementation.",
        "- This probe uses numeric rune/base-29 token sequences only.",
        "- This is not the full S1f calibration run.",
    ]
    return "\n".join(lines) + "\n"


def run_probe() -> dict[str, Any]:
    if not fast_span_hamming_available():
        raise RuntimeError("optional _span_hamming_fast extension is not built")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    token_rows = _read_token_rows(TOKEN_HASH_LIMIT_FOR_PROBE)
    specs = [ProbeConfig(**spec) for spec in SPAN_PROBE_CONFIGS]
    result_rows: list[dict[str, Any]] = []

    for spec_idx, spec in enumerate(specs, start=1):
        py_backend, fast_backend = _build_backend_pair(spec)
        for token_idx, (token_hash, tokens) in enumerate(token_rows.items(), start=1):
            py_stats, py_ms = _time_score(py_backend, tokens)
            fast_stats, fast_ms = _time_score(fast_backend, tokens)
            mismatches = _stats_compare(py_stats, fast_stats)
            speedup = py_ms / fast_ms if fast_ms > 0.0 else 0.0
            result_rows.append(
                {
                    "config_id": spec.config_id,
                    "token_hash": token_hash,
                    "token_length": len(tokens),
                    "python_ms": f"{py_ms:.6f}",
                    "fast_ms": f"{fast_ms:.6f}",
                    "speedup_ratio": f"{speedup:.6f}",
                    "parity_ok": 1 if not mismatches else 0,
                    "mismatch_fields": ";".join(mismatches),
                    "span_raw": f"{py_stats.span_raw:.12g}",
                    "coverage": f"{py_stats.coverage:.12g}",
                    "quality": f"{py_stats.quality:.12g}",
                    "n_intervals_selected": py_stats.n_intervals_selected,
                    "n_candidates_pruned_cap": py_stats.n_candidates_pruned_cap,
                    "spec_index": spec_idx,
                    "token_index": token_idx,
                }
            )

    speedups = [float(row["speedup_ratio"]) for row in result_rows if int(row["parity_ok"]) == 1]
    parity_failed = [row for row in result_rows if int(row["parity_ok"]) != 1]
    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_unique_partial_rows": _repo_rel(UNIQUE_PARTIAL_ROWS),
        "output_dir": _repo_rel(OUTPUT_DIR),
        "token_hash_limit_for_probe": TOKEN_HASH_LIMIT_FOR_PROBE,
        "token_hash_count": len(token_rows),
        "config_count": len(specs),
        "result_row_count": len(result_rows),
        "parity_failed_row_count": len(parity_failed),
        "mean_speedup_ratio": mean(speedups) if speedups else 0.0,
        "median_speedup_ratio": median(speedups) if speedups else 0.0,
        "max_speedup_ratio": max(speedups) if speedups else 0.0,
        "min_speedup_ratio": min(speedups) if speedups else 0.0,
        "configs": [asdict(spec) for spec in specs],
    }

    _write_csv(
        OUTPUT_DIR / "span_hamming_fast_backend_probe_rows.csv",
        result_rows,
        (
            "config_id",
            "token_hash",
            "token_length",
            "python_ms",
            "fast_ms",
            "speedup_ratio",
            "parity_ok",
            "mismatch_fields",
            "span_raw",
            "coverage",
            "quality",
            "n_intervals_selected",
            "n_candidates_pruned_cap",
            "spec_index",
            "token_index",
        ),
    )
    (OUTPUT_DIR / "span_hamming_fast_backend_probe_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_fast_backend_probe_readout.md").write_text(
        _build_readout(summary),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    summary = run_probe()
    print(
        "[span_hamming_fast_probe] done "
        f"rows={summary['result_row_count']} "
        f"parity_failed={summary['parity_failed_row_count']} "
        f"mean_speedup={summary['mean_speedup_ratio']:.3f}x "
        f"output={summary['output_dir']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
