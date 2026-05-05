from __future__ import annotations

"""
Report-only fixed-500 len-8 Hamming-distance bucket diagnostic.

No CLI arguments. Edit constants below or use the full wrapper. This keeps the
test shape fixed across texts: each available candidate contributes prefix,
middle, and suffix 500-token chunks, scored with len_min=len_max=8 and max_hd=4.
"""

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence


def _bootstrap_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            src_dir = parent / "src"
            if src_dir.exists() and str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))
            return parent
    raise RuntimeError("Could not locate repo root from script path")


_BOOTSTRAPPED_REPO_ROOT = _bootstrap_repo_root()

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    scan_span_hamming_500_normalized_canary_v1 as base,
)


RUN_LABEL = "span_hamming_500_len8_hd_buckets_canary_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_len8_hd_buckets_canary_v1"
)

TOKEN_HASH_LIMIT_FOR_CANARY = 80
PROGRESS_EVERY_SAMPLES = 50

LEN8 = 8
MAX_HD = 4
MAX_CANDIDATES_PER_WINDOW = 256
CHUNK_KINDS = base.CHUNK_KINDS

SPAN_CONFIG_SPECS = (
    dict(
        config_id="raw_selected_len8_hd4_cap256_norm500",
        dictionary_id="raw_selected",
        wordlist_rel="assets/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        config_id="strict_selected_len8_hd4_cap256_norm500",
        dictionary_id="strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        config_id="research_selected_len8_hd4_cap256_norm500",
        dictionary_id="research_selected",
        wordlist_rel="assets/hamming_dictionary_policies/research/hamming_raw_1g",
        require_selected=True,
    ),
)

BUCKET_FIELD_ROOTS = [
    *(f"raw_len8_hd{hd}_count" for hd in range(MAX_HD + 1)),
    *(f"selected_len8_hd{hd}_count" for hd in range(MAX_HD + 1)),
    *(f"raw_len8_hd_le{hd}_count" for hd in range(MAX_HD + 1)),
    *(f"selected_len8_hd_le{hd}_count" for hd in range(MAX_HD + 1)),
    "raw_len8_hd3_4_count",
    "selected_len8_hd3_4_count",
]
BUCKET_FEATURES = [*BUCKET_FIELD_ROOTS, *(f"{name}_norm" for name in BUCKET_FIELD_ROOTS)]
PAIR_FEATURES = [
    *(dict(feature_name=name, feature_direction=direction) for name in BUCKET_FEATURES for direction in ("higher", "lower")),
    dict(feature_name="candidate_cap_pruned_rate", feature_direction="lower"),
]

REPO_ROOT = base.REPO_ROOT
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class Len8Spec:
    config_id: str
    dictionary_id: str
    wordlist_rel: str
    require_selected: bool


def _repo_rel(path: Path) -> str:
    return base._repo_rel(path)


def _as_span_spec(spec: Len8Spec) -> base.SpanSpec:
    return base.SpanSpec(
        config_id=spec.config_id,
        dictionary_id=spec.dictionary_id,
        wordlist_rel=spec.wordlist_rel,
        require_selected=spec.require_selected,
        len_min=LEN8,
        len_max=LEN8,
        max_hd=MAX_HD,
        max_candidates_per_window=MAX_CANDIDATES_PER_WINDOW,
    )


def _specs() -> list[Len8Spec]:
    return [Len8Spec(**row) for row in SPAN_CONFIG_SPECS]


def _safe_float(value: object) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return float(ordered[idx])


def _count_distances(intervals: Iterable[Mapping[str, Any]]) -> dict[int, int]:
    counts = {hd: 0 for hd in range(MAX_HD + 1)}
    for interval in intervals:
        if int(interval.get("length", 0)) != LEN8:
            continue
        distance = int(interval.get("distance", MAX_HD + 1))
        if 0 <= distance <= MAX_HD:
            counts[distance] += 1
    return counts


def bucket_features(payload: Mapping[str, Any], token_length: int) -> dict[str, float]:
    raw_counts = _count_distances(dict(row) for row in payload.get("raw_intervals", []))
    selected_counts = _count_distances(dict(row) for row in payload.get("selected_intervals", []))
    window_count = max(1, token_length - LEN8 + 1)

    features: dict[str, float] = {}
    for prefix, counts in (("raw", raw_counts), ("selected", selected_counts)):
        running = 0
        for hd in range(MAX_HD + 1):
            count = int(counts[hd])
            features[f"{prefix}_len8_hd{hd}_count"] = float(count)
            features[f"{prefix}_len8_hd{hd}_count_norm"] = float(count) / float(window_count)
            running += count
            features[f"{prefix}_len8_hd_le{hd}_count"] = float(running)
            features[f"{prefix}_len8_hd_le{hd}_count_norm"] = float(running) / float(window_count)
        noisy = int(counts[3] + counts[4])
        features[f"{prefix}_len8_hd3_4_count"] = float(noisy)
        features[f"{prefix}_len8_hd3_4_count_norm"] = float(noisy) / float(window_count)

    n_considered = int(payload.get("n_candidates_considered", 0) or 0)
    n_pruned = int(payload.get("n_candidates_pruned_cap", 0) or 0)
    features["candidate_cap_pruned_rate"] = float(n_pruned) / float(max(1, n_pruned + n_considered))
    return features


def _candidate_row(
    *,
    spec: Len8Spec,
    sample: base.ChunkSample,
    payload: Mapping[str, Any],
    elapsed_ms: float,
    build_ms: float,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "run_label": RUN_LABEL,
        "config_id": spec.config_id,
        "dictionary_id": spec.dictionary_id,
        "wordlist_rel": spec.wordlist_rel,
        "require_selected": int(spec.require_selected),
        "len_min": LEN8,
        "len_max": LEN8,
        "max_hd": MAX_HD,
        "max_candidates_per_window": MAX_CANDIDATES_PER_WINDOW,
        "token_hash": sample.token_hash,
        "sample_id": sample.sample_id,
        "chunk_kind": sample.chunk_kind,
        "chunk_start": sample.start,
        "chunk_end": sample.end,
        "token_length": len(sample.tokens),
        "len8_window_count": max(0, len(sample.tokens) - LEN8 + 1),
        "span_raw_current": float(payload["span_raw"]),
        "span_coverage_current": float(payload["coverage"]),
        "span_quality_current": float(payload["quality"]),
        "selected_interval_count": int(payload["n_intervals_selected"]),
        "raw_interval_count": len(list(payload.get("raw_intervals", []))),
        "n_windows_total": int(payload["n_windows_total"]),
        "n_windows_scored": int(payload["n_windows_scored"]),
        "n_candidates_considered": int(payload.get("n_candidates_considered", 0) or 0),
        "n_candidates_pruned_cap": int(payload.get("n_candidates_pruned_cap", 0) or 0),
        "score_elapsed_ms": f"{elapsed_ms:.6f}",
        "backend_build_ms": f"{build_ms:.6f}",
    }
    row.update({key: f"{value:.12g}" for key, value in bucket_features(payload, len(sample.tokens)).items()})
    return row


def _candidate_fieldnames() -> list[str]:
    return [
        "run_label",
        "config_id",
        "dictionary_id",
        "wordlist_rel",
        "require_selected",
        "len_min",
        "len_max",
        "max_hd",
        "max_candidates_per_window",
        "token_hash",
        "sample_id",
        "chunk_kind",
        "chunk_start",
        "chunk_end",
        "token_length",
        "len8_window_count",
        "span_raw_current",
        "span_coverage_current",
        "span_quality_current",
        "selected_interval_count",
        "raw_interval_count",
        "n_windows_total",
        "n_windows_scored",
        "n_candidates_considered",
        "n_candidates_pruned_cap",
        "score_elapsed_ms",
        "backend_build_ms",
        *BUCKET_FEATURES,
        "candidate_cap_pruned_rate",
    ]


def _feature_preference(direction: str, winner_value: object, challenger_value: object) -> str:
    winner = _safe_float(winner_value)
    challenger = _safe_float(challenger_value)
    if winner is None or challenger is None:
        return "no_decision"
    if abs(winner - challenger) <= 1e-12:
        return "tie"
    if direction == "higher":
        return "truth_better" if winner > challenger else "truth_worse"
    if direction == "lower":
        return "truth_better" if winner < challenger else "truth_worse"
    raise ValueError(f"unknown direction: {direction}")


def build_pair_summaries(
    *,
    pair_rows: Sequence[Mapping[str, str]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_key = {
        (str(row["config_id"]), str(row["token_hash"]), str(row["chunk_kind"])): row
        for row in candidate_rows
    }
    config_ids = sorted({str(row["config_id"]) for row in candidate_rows})
    out: list[dict[str, Any]] = []
    for config_id in config_ids:
        for chunk_kind in CHUNK_KINDS:
            for feature in PAIR_FEATURES:
                feature_name = str(feature["feature_name"])
                direction = str(feature["feature_direction"])
                row = {
                    "config_id": config_id,
                    "chunk_kind": chunk_kind,
                    "feature_name": feature_name,
                    "feature_direction": direction,
                    "pair_count": 0,
                    "available_pair_count": 0,
                    "no_decision": 0,
                    "truth_better": 0,
                    "truth_worse": 0,
                    "tie": 0,
                    "rescues": 0,
                    "breaks": 0,
                    "current_misranked_pair_count": 0,
                    "current_correct_control_pair_count": 0,
                    "unique_misranked_rescue_pair_count": 0,
                    "unique_control_break_pair_count": 0,
                }
                rescue_pairs: set[str] = set()
                break_pairs: set[str] = set()
                for pair in pair_rows:
                    winner_hash = str(pair.get("winner_token_hash", "")).strip()
                    challenger_hash = str(pair.get("challenger_token_hash", "")).strip()
                    winner = by_key.get((config_id, winner_hash, chunk_kind))
                    challenger = by_key.get((config_id, challenger_hash, chunk_kind))
                    if winner is None or challenger is None:
                        continue
                    current_correct = str(pair.get("current_score_correct", "")).strip() == "1"
                    pair_id = str(pair.get("pair_id", f"{winner_hash}|{challenger_hash}"))
                    pref = _feature_preference(direction, winner.get(feature_name), challenger.get(feature_name))
                    row["pair_count"] += 1
                    if pref == "no_decision":
                        row["no_decision"] += 1
                        continue
                    row["available_pair_count"] += 1
                    row[pref] += 1
                    if current_correct:
                        row["current_correct_control_pair_count"] += 1
                        if pref == "truth_worse":
                            row["breaks"] += 1
                            break_pairs.add(pair_id)
                    else:
                        row["current_misranked_pair_count"] += 1
                        if pref == "truth_better":
                            row["rescues"] += 1
                            rescue_pairs.add(pair_id)
                row["net"] = int(row["rescues"]) - int(row["breaks"])
                row["unique_misranked_rescue_pair_count"] = len(rescue_pairs)
                row["unique_control_break_pair_count"] = len(break_pairs)
                out.append(row)
    out.sort(key=lambda item: (int(item["net"]), int(item["rescues"])), reverse=True)
    return out


def build_distribution_summary(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    config_ids = sorted({str(row["config_id"]) for row in candidate_rows})
    fields = [*BUCKET_FEATURES, "candidate_cap_pruned_rate"]
    for config_id in config_ids:
        for chunk_kind in CHUNK_KINDS:
            rows = [row for row in candidate_rows if str(row["config_id"]) == config_id and str(row["chunk_kind"]) == chunk_kind]
            for field in fields:
                values = [_safe_float(row.get(field)) for row in rows]
                nums = [float(value) for value in values if value is not None]
                if not nums:
                    continue
                out.append(
                    {
                        "config_id": config_id,
                        "chunk_kind": chunk_kind,
                        "feature_name": field,
                        "row_count": len(nums),
                        "mean": f"{mean(nums):.12g}",
                        "median": f"{median(nums):.12g}",
                        "min": f"{min(nums):.12g}",
                        "p10": f"{_percentile(nums, 0.10):.12g}",
                        "p90": f"{_percentile(nums, 0.90):.12g}",
                        "max": f"{max(nums):.12g}",
                    }
                )
    return out


def _timing_summary(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[float]] = {}
    for row in candidate_rows:
        value = _safe_float(row.get("score_elapsed_ms"))
        if value is None:
            continue
        key = (str(row["config_id"]), str(row["chunk_kind"]))
        grouped.setdefault(key, []).append(value)
    out = []
    for (config_id, chunk_kind), values in sorted(grouped.items()):
        out.append(
            {
                "config_id": config_id,
                "chunk_kind": chunk_kind,
                "row_count": len(values),
                "mean_ms": f"{mean(values):.6f}",
                "median_ms": f"{median(values):.6f}",
                "max_ms": f"{max(values):.6f}",
            }
        )
    return out


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    base._write_csv(path, rows, fieldnames)


def _append_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    return base._append_csv(path, rows, fieldnames)


def _write_run_state(path: Path, state: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(state), indent=2, sort_keys=True), encoding="utf-8")


def _build_readout(summary: Mapping[str, Any], best_rows: Sequence[Mapping[str, Any]]) -> str:
    coverage_note = "Canary subset only." if int(summary["token_hash_limit_for_canary"]) else "Full configured token-hash set."
    lines = [
        "# Span-Hamming 500 Len8 HD Buckets v1",
        "",
        "## Status",
        "",
        "- Report-only; no runtime behaviour changed.",
        f"- candidate rows: `{summary['candidate_row_count']}`",
        f"- pair summary rows: `{summary['pair_summary_row_count']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.2f}`",
        "",
        "## Best Pair Rows",
        "",
        "| config | chunk | feature | direction | rescues | breaks | net |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for row in best_rows[:15]:
        lines.append(
            f"| {row['config_id']} | {row['chunk_kind']} | {row['feature_name']} | "
            f"{row['feature_direction']} | {row['rescues']} | {row['breaks']} | {row['net']} |"
        )
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            f"- {coverage_note}",
            "- Fixed 500-token chunks only.",
            "- len_min=len_max=8, max_hd=4, max_candidates_per_window fixed for this run.",
            "- Raw bucket counts are pre-overlap-selection best-window intervals; selected bucket counts are after non-overlap selection.",
            "- Higher/lower directions are both evaluated for bucket features because high-distance buckets may be noise.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_scan() -> dict[str, Any]:
    if not base.fast_span_hamming_available():
        raise RuntimeError("optional _span_hamming_fast extension is not built")

    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidate_path = OUTPUT_DIR / "span_hamming_500_len8_hd_bucket_candidate_features.csv"
    pair_summary_path = OUTPUT_DIR / "span_hamming_500_len8_hd_bucket_pair_summary.csv"
    distribution_path = OUTPUT_DIR / "span_hamming_500_len8_hd_bucket_distribution_summary.csv"
    timing_path = OUTPUT_DIR / "span_hamming_500_len8_hd_bucket_timing_summary.csv"
    run_state_path = OUTPUT_DIR / "span_hamming_500_len8_hd_bucket_run_state.json"

    for path in (candidate_path, pair_summary_path, distribution_path, timing_path):
        if path.exists():
            path.unlink()

    pair_rows = base._read_pair_rows()
    required_hashes = base._required_token_hashes(pair_rows, TOKEN_HASH_LIMIT_FOR_CANARY)
    tokens_by_hash = base._read_token_rows(required_hashes)
    samples = base.build_chunk_samples(tokens_by_hash)
    specs = _specs()
    total_scores = len(specs) * len(samples)
    completed_scores = 0
    candidate_rows: list[dict[str, Any]] = []

    _write_run_state(
        run_state_path,
        {
            "run_label": RUN_LABEL,
            "status": "running",
            "output_dir": _repo_rel(OUTPUT_DIR),
            "token_hash_limit_for_canary": TOKEN_HASH_LIMIT_FOR_CANARY,
            "token_hash_count": len(tokens_by_hash),
            "sample_count": len(samples),
            "config_count": len(specs),
            "total_scores": total_scores,
            "completed_scores": completed_scores,
        },
    )

    for spec in specs:
        backend, missing_reason, build_ms = base._build_fast_backend(_as_span_spec(spec))
        if backend is None:
            print(f"[span_hamming_500_len8_hd_buckets] skip {spec.config_id}: {missing_reason}", flush=True)
            continue
        pending_rows: list[dict[str, Any]] = []
        for sample in samples:
            payload, elapsed_ms = base._score_payload(backend, sample.tokens)
            row = _candidate_row(
                spec=spec,
                sample=sample,
                payload=payload,
                elapsed_ms=elapsed_ms,
                build_ms=build_ms,
            )
            pending_rows.append(row)
            candidate_rows.append(row)
            completed_scores += 1
            if completed_scores == 1 or completed_scores % PROGRESS_EVERY_SAMPLES == 0 or completed_scores == total_scores:
                elapsed = time.perf_counter() - started
                rate = completed_scores / max(1e-9, elapsed)
                eta = (total_scores - completed_scores) / max(1e-9, rate)
                print(
                    f"[span_hamming_500_len8_hd_buckets] progress {completed_scores}/{total_scores} "
                    f"elapsed={elapsed:.1f}s eta={eta:.1f}s last_config={spec.config_id}",
                    flush=True,
                )
        _append_csv(candidate_path, pending_rows, _candidate_fieldnames())
        _write_run_state(
            run_state_path,
            {
                "run_label": RUN_LABEL,
                "status": "running",
                "output_dir": _repo_rel(OUTPUT_DIR),
                "token_hash_limit_for_canary": TOKEN_HASH_LIMIT_FOR_CANARY,
                "token_hash_count": len(tokens_by_hash),
                "sample_count": len(samples),
                "config_count": len(specs),
                "total_scores": total_scores,
                "completed_scores": completed_scores,
                "last_completed_config_id": spec.config_id,
                "elapsed_seconds": time.perf_counter() - started,
            },
        )

    pair_summaries = build_pair_summaries(pair_rows=pair_rows, candidate_rows=candidate_rows)
    distributions = build_distribution_summary(candidate_rows)
    timing_rows = _timing_summary(candidate_rows)

    summary_fields = [
        "config_id",
        "chunk_kind",
        "feature_name",
        "feature_direction",
        "pair_count",
        "available_pair_count",
        "no_decision",
        "truth_better",
        "truth_worse",
        "tie",
        "rescues",
        "breaks",
        "net",
        "current_misranked_pair_count",
        "current_correct_control_pair_count",
        "unique_misranked_rescue_pair_count",
        "unique_control_break_pair_count",
    ]
    distribution_fields = ["config_id", "chunk_kind", "feature_name", "row_count", "mean", "median", "min", "p10", "p90", "max"]
    timing_fields = ["config_id", "chunk_kind", "row_count", "mean_ms", "median_ms", "max_ms"]

    _write_csv(pair_summary_path, pair_summaries, summary_fields)
    _write_csv(distribution_path, distributions, distribution_fields)
    _write_csv(timing_path, timing_rows, timing_fields)

    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "output_dir": _repo_rel(OUTPUT_DIR),
        "token_hash_limit_for_canary": TOKEN_HASH_LIMIT_FOR_CANARY,
        "token_hash_count": len(tokens_by_hash),
        "sample_count": len(samples),
        "config_count": len(specs),
        "total_scores": total_scores,
        "completed_scores": completed_scores,
        "candidate_row_count": len(candidate_rows),
        "pair_summary_row_count": len(pair_summaries),
        "distribution_summary_row_count": len(distributions),
        "elapsed_seconds": time.perf_counter() - started,
        "candidate_features_csv": _repo_rel(candidate_path),
        "pair_summary_csv": _repo_rel(pair_summary_path),
        "distribution_summary_csv": _repo_rel(distribution_path),
        "timing_summary_csv": _repo_rel(timing_path),
        "top_pair_rows": pair_summaries[:20],
        "caveats": [
            "report-only; no runtime solver behaviour changed",
            "fixed 500-token chunks only",
            "len_min=len_max=8, max_hd=4, max_candidates_per_window fixed",
            "candidate cap pressure should be checked before interpreting high-HD buckets",
        ],
    }
    (OUTPUT_DIR / "span_hamming_500_len8_hd_bucket_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_500_len8_hd_bucket_readout.md").write_text(
        _build_readout(summary, pair_summaries),
        encoding="utf-8",
    )
    _write_run_state(run_state_path, summary)
    print(
        f"[span_hamming_500_len8_hd_buckets] done rows={len(candidate_rows)} "
        f"elapsed={summary['elapsed_seconds']:.2f}s output={_repo_rel(OUTPUT_DIR)}",
        flush=True,
    )
    return summary


def main() -> None:
    run_scan()


if __name__ == "__main__":
    main()
