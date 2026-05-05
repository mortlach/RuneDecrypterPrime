from __future__ import annotations

"""
Report-only fixed-500 span-Hamming length/HD fingerprint canary.

No CLI arguments. Edit constants below. This scan scores each configured
500-token chunk separately for lengths 6..10 with max_hd = length - 3 and an
effectively uncapped candidate ceiling, then writes HD-bucket tallies as a
candidate fingerprint.
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

from rune_decrypter_prime.scoring.span_hamming.fast_backend import (  # noqa: E402
    FastSpanHammingBackend,
)
from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig  # noqa: E402
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (  # noqa: E402
    scan_span_hamming_500_normalized_canary_v1 as base,
)


RUN_LABEL = "span_hamming_500_length_hd_fingerprint_canary_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_length_hd_fingerprint_canary_v1"
)

TOKEN_HASH_LIMIT_FOR_CANARY = 80
PROGRESS_EVERY_SCORES = 50
LENGTHS = (6, 7, 8, 9, 10)
MAX_HD_BY_LENGTH = {length: length - 3 for length in LENGTHS}
MAX_CANDIDATES_PER_WINDOW = 100000

SPAN_CONFIG_SPECS = (
    dict(
        config_id="strict_selected_len6_10_hd_len_minus3_cap100000_norm500",
        dictionary_id="strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        require_selected=True,
    ),
)

CHUNK_KINDS = base.CHUNK_KINDS
REPO_ROOT = base.REPO_ROOT
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class FingerprintSpec:
    config_id: str
    dictionary_id: str
    wordlist_rel: str
    require_selected: bool


def _repo_rel(path: Path) -> str:
    return base._repo_rel(path)


def _specs() -> list[FingerprintSpec]:
    return [FingerprintSpec(**row) for row in SPAN_CONFIG_SPECS]


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


def _build_backend(spec: FingerprintSpec, length: int) -> FastSpanHammingBackend:
    cfg = SpanHammingConfig(
        len_min=length,
        len_max=length,
        max_hd=MAX_HD_BY_LENGTH[length],
        max_candidates_per_window=MAX_CANDIDATES_PER_WINDOW,
        debug_return_intervals=True,
    )
    return FastSpanHammingBackend(
        config=cfg,
        wordlist_dir=REPO_ROOT / spec.wordlist_rel,
        require_selected=spec.require_selected,
        return_raw_intervals=True,
    )


def _count_distances(intervals: Iterable[Mapping[str, Any]], *, length: int, max_hd: int) -> dict[int, int]:
    counts = {hd: 0 for hd in range(max_hd + 1)}
    for interval in intervals:
        if int(interval.get("length", 0)) != length:
            continue
        distance = int(interval.get("distance", max_hd + 1))
        if 0 <= distance <= max_hd:
            counts[distance] += 1
    return counts


def length_bucket_features(payload: Mapping[str, Any], *, length: int, token_length: int) -> dict[str, float]:
    max_hd = MAX_HD_BY_LENGTH[length]
    window_count = max(0, token_length - length + 1)
    denom = float(max(1, window_count))
    raw_counts = _count_distances(
        (dict(row) for row in payload.get("raw_intervals", [])),
        length=length,
        max_hd=max_hd,
    )
    selected_counts = _count_distances(
        (dict(row) for row in payload.get("selected_intervals", [])),
        length=length,
        max_hd=max_hd,
    )

    features: dict[str, float] = {
        f"len{length}_window_count": float(window_count),
        f"len{length}_max_hd": float(max_hd),
    }
    for prefix, counts in (("raw", raw_counts), ("selected", selected_counts)):
        total = int(sum(counts.values()))
        weighted_hd = int(sum(hd * count for hd, count in counts.items()))
        running = 0
        for hd in range(max_hd + 1):
            count = int(counts[hd])
            running += count
            features[f"{prefix}_len{length}_hd{hd}_count"] = float(count)
            features[f"{prefix}_len{length}_hd{hd}_count_norm"] = float(count) / denom
            features[f"{prefix}_len{length}_hd_le{hd}_count"] = float(running)
            features[f"{prefix}_len{length}_hd_le{hd}_count_norm"] = float(running) / denom
        features[f"{prefix}_len{length}_matched_window_count"] = float(total)
        features[f"{prefix}_len{length}_matched_window_count_norm"] = float(total) / denom
        features[f"{prefix}_len{length}_no_match_count"] = float(max(0, window_count - total))
        features[f"{prefix}_len{length}_no_match_count_norm"] = float(max(0, window_count - total)) / denom
        features[f"{prefix}_len{length}_mean_hd"] = float(weighted_hd) / float(max(1, total))
        features[f"{prefix}_len{length}_mean_error_rate"] = features[f"{prefix}_len{length}_mean_hd"] / float(length)

    n_considered = int(payload.get("n_candidates_considered", 0) or 0)
    n_pruned = int(payload.get("n_candidates_pruned_cap", 0) or 0)
    features[f"len{length}_candidate_cap_pruned_rate"] = float(n_pruned) / float(max(1, n_pruned + n_considered))
    features[f"len{length}_n_candidates_considered"] = float(n_considered)
    features[f"len{length}_n_candidates_pruned_cap"] = float(n_pruned)
    return features


def _aggregate_features(row: Mapping[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for prefix in ("raw", "selected"):
        exact = 0.0
        close = 0.0
        matched = 0.0
        weighted_error = 0.0
        window_total = 0.0
        for length in LENGTHS:
            windows = float(row.get(f"len{length}_window_count", 0.0) or 0.0)
            matched_count = float(row.get(f"{prefix}_len{length}_matched_window_count", 0.0) or 0.0)
            exact += float(row.get(f"{prefix}_len{length}_hd0_count", 0.0) or 0.0)
            close_hd = max(0, min(MAX_HD_BY_LENGTH[length], round(length * 0.20)))
            close += float(row.get(f"{prefix}_len{length}_hd_le{close_hd}_count", 0.0) or 0.0)
            matched += matched_count
            weighted_error += float(row.get(f"{prefix}_len{length}_mean_error_rate", 0.0) or 0.0) * matched_count
            window_total += windows
        out[f"{prefix}_fingerprint_exact_count_norm"] = exact / float(max(1.0, window_total))
        out[f"{prefix}_fingerprint_close20_count_norm"] = close / float(max(1.0, window_total))
        out[f"{prefix}_fingerprint_matched_count_norm"] = matched / float(max(1.0, window_total))
        out[f"{prefix}_fingerprint_mean_error_rate"] = weighted_error / float(max(1.0, matched))
    return out


def candidate_feature_names() -> list[str]:
    names: list[str] = []
    for length in LENGTHS:
        max_hd = MAX_HD_BY_LENGTH[length]
        names.extend([f"len{length}_window_count", f"len{length}_max_hd"])
        for prefix in ("raw", "selected"):
            for hd in range(max_hd + 1):
                names.extend(
                    [
                        f"{prefix}_len{length}_hd{hd}_count",
                        f"{prefix}_len{length}_hd{hd}_count_norm",
                        f"{prefix}_len{length}_hd_le{hd}_count",
                        f"{prefix}_len{length}_hd_le{hd}_count_norm",
                    ]
                )
            names.extend(
                [
                    f"{prefix}_len{length}_matched_window_count",
                    f"{prefix}_len{length}_matched_window_count_norm",
                    f"{prefix}_len{length}_no_match_count",
                    f"{prefix}_len{length}_no_match_count_norm",
                    f"{prefix}_len{length}_mean_hd",
                    f"{prefix}_len{length}_mean_error_rate",
                ]
            )
        names.extend(
            [
                f"len{length}_candidate_cap_pruned_rate",
                f"len{length}_n_candidates_considered",
                f"len{length}_n_candidates_pruned_cap",
            ]
        )
    names.extend(
        [
            "raw_fingerprint_exact_count_norm",
            "raw_fingerprint_close20_count_norm",
            "raw_fingerprint_matched_count_norm",
            "raw_fingerprint_mean_error_rate",
            "selected_fingerprint_exact_count_norm",
            "selected_fingerprint_close20_count_norm",
            "selected_fingerprint_matched_count_norm",
            "selected_fingerprint_mean_error_rate",
        ]
    )
    return names


def _candidate_fieldnames() -> list[str]:
    return [
        "run_label",
        "config_id",
        "dictionary_id",
        "wordlist_rel",
        "require_selected",
        "lengths",
        "max_hd_by_length_json",
        "max_candidates_per_window",
        "token_hash",
        "sample_id",
        "chunk_kind",
        "chunk_start",
        "chunk_end",
        "token_length",
        "score_elapsed_ms_total",
        *candidate_feature_names(),
    ]


def _candidate_row(
    *,
    spec: FingerprintSpec,
    sample: base.ChunkSample,
    features: Mapping[str, float],
    elapsed_ms_total: float,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "run_label": RUN_LABEL,
        "config_id": spec.config_id,
        "dictionary_id": spec.dictionary_id,
        "wordlist_rel": spec.wordlist_rel,
        "require_selected": int(spec.require_selected),
        "lengths": ",".join(str(length) for length in LENGTHS),
        "max_hd_by_length_json": json.dumps(MAX_HD_BY_LENGTH, sort_keys=True, separators=(",", ":")),
        "max_candidates_per_window": MAX_CANDIDATES_PER_WINDOW,
        "token_hash": sample.token_hash,
        "sample_id": sample.sample_id,
        "chunk_kind": sample.chunk_kind,
        "chunk_start": sample.start,
        "chunk_end": sample.end,
        "token_length": len(sample.tokens),
        "score_elapsed_ms_total": f"{elapsed_ms_total:.6f}",
    }
    row.update({key: f"{float(value):.12g}" for key, value in features.items()})
    return row


def _feature_direction(feature_name: str) -> str:
    if feature_name.endswith("_mean_hd") or feature_name.endswith("_mean_error_rate"):
        return "lower"
    if "no_match_count" in feature_name or "candidate_cap_pruned_rate" in feature_name:
        return "lower"
    return "higher"


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
    features = [
        name
        for name in candidate_feature_names()
        if name.endswith("_norm") or name.endswith("_mean_error_rate") or name.endswith("_candidate_cap_pruned_rate")
    ]
    config_ids = sorted({str(row["config_id"]) for row in candidate_rows})
    out: list[dict[str, Any]] = []
    for config_id in config_ids:
        for chunk_kind in CHUNK_KINDS:
            for feature_name in features:
                direction = _feature_direction(feature_name)
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
                }
                for pair in pair_rows:
                    winner_hash = str(pair.get("winner_token_hash", "")).strip()
                    challenger_hash = str(pair.get("challenger_token_hash", "")).strip()
                    winner = by_key.get((config_id, winner_hash, chunk_kind))
                    challenger = by_key.get((config_id, challenger_hash, chunk_kind))
                    if winner is None or challenger is None:
                        continue
                    current_correct = str(pair.get("current_score_correct", "")).strip() == "1"
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
                    else:
                        row["current_misranked_pair_count"] += 1
                        if pref == "truth_better":
                            row["rescues"] += 1
                row["net"] = int(row["rescues"]) - int(row["breaks"])
                out.append(row)
    out.sort(key=lambda item: (int(item["net"]), int(item["rescues"])), reverse=True)
    return out


def build_distribution_summary(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        name
        for name in candidate_feature_names()
        if name.endswith("_norm") or name.endswith("_mean_error_rate") or name.endswith("_candidate_cap_pruned_rate")
    ]
    out: list[dict[str, Any]] = []
    config_ids = sorted({str(row["config_id"]) for row in candidate_rows})
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


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    base._write_csv(path, rows, fieldnames)


def _append_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    return base._append_csv(path, rows, fieldnames)


def _write_run_state(path: Path, state: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(state), indent=2, sort_keys=True), encoding="utf-8")


def _build_readout(summary: Mapping[str, Any], best_rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Span-Hamming 500 Length/HD Fingerprint Canary v1",
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
            "- Canary subset only.",
            "- Fixed 500-token chunks only.",
            "- Each length is scored separately with max_hd = length - 3.",
            "- max_candidates_per_window is effectively uncapped at 100000; cap-prune columns should stay at zero.",
            "- Raw buckets are best-window intervals before overlap selection, not counts of every dictionary word at each HD.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_scan() -> dict[str, Any]:
    if not base.fast_span_hamming_available():
        raise RuntimeError("optional _span_hamming_fast extension is not built")

    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidate_path = OUTPUT_DIR / "span_hamming_500_length_hd_fingerprint_candidate_features.csv"
    pair_summary_path = OUTPUT_DIR / "span_hamming_500_length_hd_fingerprint_pair_summary.csv"
    distribution_path = OUTPUT_DIR / "span_hamming_500_length_hd_fingerprint_distribution_summary.csv"
    run_state_path = OUTPUT_DIR / "span_hamming_500_length_hd_fingerprint_run_state.json"
    for path in (candidate_path, pair_summary_path, distribution_path):
        if path.exists():
            path.unlink()

    pair_rows = base._read_pair_rows()
    required_hashes = base._required_token_hashes(pair_rows, TOKEN_HASH_LIMIT_FOR_CANARY)
    tokens_by_hash = base._read_token_rows(required_hashes)
    samples = base.build_chunk_samples(tokens_by_hash)
    specs = _specs()
    total_scores = len(specs) * len(samples) * len(LENGTHS)
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
            "lengths": list(LENGTHS),
            "max_hd_by_length": MAX_HD_BY_LENGTH,
            "max_candidates_per_window": MAX_CANDIDATES_PER_WINDOW,
            "total_scores": total_scores,
            "completed_scores": completed_scores,
        },
    )

    for spec in specs:
        backends = {length: _build_backend(spec, length) for length in LENGTHS}
        pending_rows: list[dict[str, Any]] = []
        for sample in samples:
            row_features: dict[str, float] = {}
            elapsed_total = 0.0
            for length, backend in backends.items():
                start_score = time.perf_counter()
                payload = backend.score_payload(sample.tokens)
                elapsed_ms = (time.perf_counter() - start_score) * 1000.0
                elapsed_total += elapsed_ms
                row_features.update(length_bucket_features(payload, length=length, token_length=len(sample.tokens)))
                completed_scores += 1
                if completed_scores == 1 or completed_scores % PROGRESS_EVERY_SCORES == 0 or completed_scores == total_scores:
                    elapsed = time.perf_counter() - started
                    rate = completed_scores / max(1e-9, elapsed)
                    eta = (total_scores - completed_scores) / max(1e-9, rate)
                    print(
                        f"[span_hamming_500_length_hd_fingerprint] progress {completed_scores}/{total_scores} "
                        f"elapsed={elapsed:.1f}s eta={eta:.1f}s last_config={spec.config_id} length={length}",
                        flush=True,
                    )
            row_features.update(_aggregate_features(row_features))
            row = _candidate_row(spec=spec, sample=sample, features=row_features, elapsed_ms_total=elapsed_total)
            pending_rows.append(row)
            candidate_rows.append(row)
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
                "lengths": list(LENGTHS),
                "max_hd_by_length": MAX_HD_BY_LENGTH,
                "max_candidates_per_window": MAX_CANDIDATES_PER_WINDOW,
                "total_scores": total_scores,
                "completed_scores": completed_scores,
                "last_completed_config_id": spec.config_id,
                "elapsed_seconds": time.perf_counter() - started,
            },
        )

    pair_summaries = build_pair_summaries(pair_rows=pair_rows, candidate_rows=candidate_rows)
    distributions = build_distribution_summary(candidate_rows)

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
    ]
    distribution_fields = ["config_id", "chunk_kind", "feature_name", "row_count", "mean", "median", "min", "p10", "p90", "max"]
    _write_csv(pair_summary_path, pair_summaries, summary_fields)
    _write_csv(distribution_path, distributions, distribution_fields)

    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "output_dir": _repo_rel(OUTPUT_DIR),
        "token_hash_limit_for_canary": TOKEN_HASH_LIMIT_FOR_CANARY,
        "token_hash_count": len(tokens_by_hash),
        "sample_count": len(samples),
        "config_count": len(specs),
        "lengths": list(LENGTHS),
        "max_hd_by_length": MAX_HD_BY_LENGTH,
        "max_candidates_per_window": MAX_CANDIDATES_PER_WINDOW,
        "total_scores": total_scores,
        "completed_scores": completed_scores,
        "candidate_row_count": len(candidate_rows),
        "pair_summary_row_count": len(pair_summaries),
        "distribution_summary_row_count": len(distributions),
        "elapsed_seconds": time.perf_counter() - started,
        "candidate_features_csv": _repo_rel(candidate_path),
        "pair_summary_csv": _repo_rel(pair_summary_path),
        "distribution_summary_csv": _repo_rel(distribution_path),
        "top_pair_rows": pair_summaries[:20],
        "caveats": [
            "report-only; no runtime solver behaviour changed",
            "canary subset only",
            "fixed 500-token chunks only",
            "raw buckets are best-window intervals, not every dictionary match",
            "cap-pruned columns must be checked before interpreting bucket distributions",
        ],
    }
    (OUTPUT_DIR / "span_hamming_500_length_hd_fingerprint_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_500_length_hd_fingerprint_readout.md").write_text(
        _build_readout(summary, pair_summaries),
        encoding="utf-8",
    )
    _write_run_state(run_state_path, summary)
    print(
        f"[span_hamming_500_length_hd_fingerprint] done rows={len(candidate_rows)} "
        f"elapsed={summary['elapsed_seconds']:.2f}s output={_repo_rel(OUTPUT_DIR)}",
        flush=True,
    )
    return summary


def main() -> None:
    run_scan()


if __name__ == "__main__":
    main()
