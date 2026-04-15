from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.scoring.hamming.backend import HammingBackend
from rune_decrypter_prime.scoring.hamming.loader import load_raw1grams_wordlists
from rune_decrypter_prime.scoring.span_hamming import SpanHammingBackend, SpanHammingConfig
from rune_decrypter_prime.data.cipher_tests import plaintext as plaintext_data
from tests.scoring.span_hamming.nowli_hard_cases import load_nowli_hard_cases_v1

POLICY_ASSET_ROOT = (
    REPO_ROOT
    / "planning_old/working/rdp_hamming_dictionary_policy_bundle_v2"
    / "rdp_hamming_dictionary_policy_bundle_v2/data/policy_assets"
)
OUTPUT_ROOT = REPO_ROOT / "output/tools/benchmarks/scoring/hamming_dictionary_policy_phase_c_v1"
DATASET_FP = REPO_ROOT / "tests/scoring/span_hamming/data/nowli_hard_cases_v1.json"

POLICIES_TO_COMPARE = ("normal", "strict", "broad")
COMPARE_BASELINE_POLICY = "normal"

PLAIN_SLICES = (
    ("plain_real_l200_a", 0, 200),
    ("plain_real_l200_b", 200, 200),
    ("plain_real_l400_a", 0, 400),
    ("plain_real_l400_b", 400, 400),
    ("plain_real_l800_a", 0, 800),
)
CORRUPT_PCTS = (0, 10, 30, 60, 100)
RANDOM_SEEDS = (0, 1, 2, 3, 4)

SPAN_CFG = SpanHammingConfig(
    len_min=3,
    len_max=14,
    max_hd=2,
    start_stride=1,
    max_windows_total=0,
    max_candidates_per_window=256,
    max_intervals_considered_per_start=4,
    min_quality_threshold=1e-9,
    debug_return_intervals=False,
)


@dataclass(frozen=True)
class SampleRow:
    domain: str
    policy: str
    sample_id: str
    family: str
    condition: str
    length: int
    category: str | None
    total_hd: float | None
    avg_hd_word: float | None
    n_words: float | None
    span_raw: float | None
    coverage: float | None
    quality: float | None
    n_intervals_selected: int | None
    elapsed_ms: float | None


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_policy_wordlists(policy_dir: Path) -> tuple[dict[int, list[list[int]]], dict[int, list[list[int]]] | None]:
    return load_raw1grams_wordlists(policy_dir, build_rtl=False, require_selected=True)


def _discover_policy_dirs(root: Path, policy_names: tuple[str, ...]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for name in policy_names:
        out[str(name)] = root / str(name) / "hamming_raw_1g"
    return out


def _slice_plaintext(start: int, length: int) -> tuple[list[int], list[list[int]]]:
    pt = list(plaintext_data.plaintext1[start : start + length])
    wli = [list(row) for row in plaintext_data.word_breaks1[start : start + length]]
    if len(pt) != int(length) or len(wli) != int(length):
        raise ValueError(f"Invalid plaintext slice start={start} length={length}")
    return pt, wli


def _corrupt_text(seq: Iterable[int], pct: int, seed: int) -> list[int]:
    values = [int(v) for v in seq]
    if pct <= 0:
        return list(values)
    rng = np.random.default_rng(int(seed))
    out = list(values)
    n_mut = int(round(len(out) * (int(pct) / 100.0)))
    if n_mut <= 0:
        return out
    indices = rng.choice(len(out), size=min(n_mut, len(out)), replace=False)
    for idx in np.asarray(indices, dtype=np.int64):
        old = int(out[int(idx)])
        new = int(rng.integers(0, 29))
        if new == old:
            new = int((old + 1) % 29)
        out[int(idx)] = new
    return out


def _random_text(length: int, seed: int) -> list[int]:
    rng = np.random.default_rng(int(seed))
    return [int(v) for v in rng.integers(0, 29, size=int(length), dtype=np.int64)]


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _policy_inventory_rows(policy_wordlists: dict[str, dict[int, list[list[int]]]]) -> list[dict]:
    rows: list[dict] = []
    for policy, words_by_len in sorted(policy_wordlists.items()):
        total = 0
        lengths = {}
        for length, words in sorted(words_by_len.items()):
            count = int(len(words))
            lengths[f"len_{int(length):02d}"] = count
            total += count
        row = {"policy": policy, "total_words": int(total)}
        row.update(lengths)
        rows.append(row)
    return rows


def _policy_inventory_deltas(policy_rows: list[dict], *, baseline: str) -> list[dict]:
    indexed = {str(row["policy"]): row for row in policy_rows}
    base = indexed.get(str(baseline))
    if base is None:
        return []
    out: list[dict] = []
    length_keys = sorted(key for key in base.keys() if key.startswith("len_"))
    for compare_policy, compare in sorted(indexed.items()):
        if compare_policy == baseline:
            continue
        row: dict[str, object] = {
            "baseline_policy": baseline,
            "compare_policy": compare_policy,
            "total_words_baseline": base.get("total_words"),
            "total_words_compare": compare.get("total_words"),
            "total_words_delta_compare_minus_baseline": int(compare.get("total_words", 0)) - int(base.get("total_words", 0)),
        }
        for key in length_keys:
            row[f"{key}_baseline"] = base.get(key, 0)
            row[f"{key}_compare"] = compare.get(key, 0)
            row[f"{key}_delta_compare_minus_baseline"] = int(compare.get(key, 0)) - int(base.get(key, 0))
        out.append(row)
    return out


def _summarize_plain(rows: list[SampleRow]) -> list[dict]:
    grouped: dict[tuple[str, str, str, int], list[SampleRow]] = defaultdict(list)
    for row in rows:
        if row.domain != "plain_hamming":
            continue
        grouped[(row.policy, row.family, row.condition, row.length)].append(row)
    out: list[dict] = []
    for (policy, family, condition, length), bucket in sorted(grouped.items()):
        total_hd = [float(r.total_hd) for r in bucket if r.total_hd is not None]
        avg_hd_word = [float(r.avg_hd_word) for r in bucket if r.avg_hd_word is not None]
        n_words = [float(r.n_words) for r in bucket if r.n_words is not None]
        elapsed_ms = [float(r.elapsed_ms) for r in bucket if r.elapsed_ms is not None]
        out.append(
            {
                "policy": policy,
                "family": family,
                "condition": condition,
                "length": int(length),
                "n_samples": len(bucket),
                "total_hd_mean": _mean(total_hd),
                "avg_hd_word_mean": _mean(avg_hd_word),
                "n_words_mean": _mean(n_words),
                "elapsed_ms_mean": _mean(elapsed_ms),
            }
        )
    return out


def _summarize_span(rows: list[SampleRow]) -> list[dict]:
    grouped: dict[tuple[str, str], list[SampleRow]] = defaultdict(list)
    for row in rows:
        if row.domain != "raw_span_hamming":
            continue
        grouped[(row.policy, str(row.category))].append(row)
    out: list[dict] = []
    for (policy, category), bucket in sorted(grouped.items()):
        span_raw = [float(r.span_raw) for r in bucket if r.span_raw is not None]
        coverage = [float(r.coverage) for r in bucket if r.coverage is not None]
        quality = [float(r.quality) for r in bucket if r.quality is not None]
        intervals = [float(r.n_intervals_selected) for r in bucket if r.n_intervals_selected is not None]
        elapsed_ms = [float(r.elapsed_ms) for r in bucket if r.elapsed_ms is not None]
        out.append(
            {
                "policy": policy,
                "category": category,
                "n_cases": len(bucket),
                "span_raw_mean": _mean(span_raw),
                "coverage_mean": _mean(coverage),
                "quality_mean": _mean(quality),
                "n_intervals_selected_mean": _mean(intervals),
                "elapsed_ms_mean": _mean(elapsed_ms),
            }
        )
    return out


def _case_policy_deltas(rows: list[SampleRow], *, baseline: str) -> list[dict]:
    grouped: dict[tuple[str, str], dict[str, SampleRow]] = defaultdict(dict)
    for row in rows:
        if row.domain != "raw_span_hamming":
            continue
        grouped[(row.sample_id, str(row.category))][row.policy] = row
    out: list[dict] = []
    for (sample_id, category), bucket in sorted(grouped.items()):
        base = bucket.get(str(baseline))
        if base is None:
            continue
        for compare_policy, compare in sorted(bucket.items()):
            if compare_policy == baseline:
                continue
            out.append(
                {
                    "sample_id": sample_id,
                    "category": category,
                    "baseline_policy": baseline,
                    "compare_policy": compare_policy,
                    "span_raw_baseline": base.span_raw,
                    "span_raw_compare": compare.span_raw,
                    "span_raw_delta_compare_minus_baseline": float((compare.span_raw or 0.0) - (base.span_raw or 0.0)),
                    "coverage_baseline": base.coverage,
                    "coverage_compare": compare.coverage,
                    "coverage_delta_compare_minus_baseline": float((compare.coverage or 0.0) - (base.coverage or 0.0)),
                    "quality_baseline": base.quality,
                    "quality_compare": compare.quality,
                    "quality_delta_compare_minus_baseline": float((compare.quality or 0.0) - (base.quality or 0.0)),
                    "elapsed_ms_baseline": base.elapsed_ms,
                    "elapsed_ms_compare": compare.elapsed_ms,
                    "elapsed_ms_delta_compare_minus_baseline": float(
                        (compare.elapsed_ms or 0.0) - (base.elapsed_ms or 0.0)
                    ),
                }
            )
    return out


def _plain_policy_deltas(summary_rows: list[dict], *, baseline: str) -> list[dict]:
    indexed: dict[tuple[str, int], dict[str, dict]] = defaultdict(dict)
    for row in summary_rows:
        indexed[(str(row["condition"]), int(row["length"]))][str(row["policy"])] = row
    out: list[dict] = []
    for (condition, length), bucket in sorted(indexed.items()):
        base = bucket.get(str(baseline))
        if base is None:
            continue
        for compare_policy, comp in sorted(bucket.items()):
            if compare_policy == baseline:
                continue
            out.append(
                {
                    "condition": condition,
                    "length": int(length),
                    "baseline_policy": baseline,
                    "compare_policy": compare_policy,
                    "avg_hd_word_mean_baseline": base.get("avg_hd_word_mean"),
                    "avg_hd_word_mean_compare": comp.get("avg_hd_word_mean"),
                    "avg_hd_word_delta_compare_minus_baseline": float(
                        float(comp.get("avg_hd_word_mean") or 0.0) - float(base.get("avg_hd_word_mean") or 0.0)
                    ),
                    "total_hd_mean_baseline": base.get("total_hd_mean"),
                    "total_hd_mean_compare": comp.get("total_hd_mean"),
                    "total_hd_delta_compare_minus_baseline": float(
                        float(comp.get("total_hd_mean") or 0.0) - float(base.get("total_hd_mean") or 0.0)
                    ),
                    "elapsed_ms_mean_baseline": base.get("elapsed_ms_mean"),
                    "elapsed_ms_mean_compare": comp.get("elapsed_ms_mean"),
                    "elapsed_ms_delta_compare_minus_baseline": float(
                        float(comp.get("elapsed_ms_mean") or 0.0) - float(base.get("elapsed_ms_mean") or 0.0)
                    ),
                }
            )
    return out


def _summarize_cost(rows: list[SampleRow]) -> list[dict]:
    grouped: dict[tuple[str, str], list[SampleRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.domain, row.policy)].append(row)
    out: list[dict] = []
    for (domain, policy), bucket in sorted(grouped.items()):
        elapsed_ms = [float(r.elapsed_ms) for r in bucket if r.elapsed_ms is not None]
        out.append(
            {
                "domain": domain,
                "policy": policy,
                "n_samples": len(bucket),
                "elapsed_ms_mean": _mean(elapsed_ms),
                "elapsed_ms_min": min(elapsed_ms) if elapsed_ms else None,
                "elapsed_ms_max": max(elapsed_ms) if elapsed_ms else None,
            }
        )
    return out


def _build_decision_summary(
    policy_inventory_deltas: list[dict],
    plain_deltas: list[dict],
    span_deltas: list[dict],
    cost_summary: list[dict],
) -> list[dict]:
    broad_inventory = next((row for row in policy_inventory_deltas if row.get("compare_policy") == "broad"), None)
    strict_inventory = next((row for row in policy_inventory_deltas if row.get("compare_policy") == "strict"), None)

    strict_plain_harsher = [
        float(row["avg_hd_word_delta_compare_minus_baseline"])
        for row in plain_deltas
        if row.get("compare_policy") == "strict"
    ]
    broad_plain_harsher = [
        abs(float(row["avg_hd_word_delta_compare_minus_baseline"]))
        for row in plain_deltas
        if row.get("compare_policy") == "broad"
    ]
    strict_false_high_span = [
        float(row["span_raw_delta_compare_minus_baseline"])
        for row in span_deltas
        if row.get("compare_policy") == "strict" and row.get("category") == "false_high_basin"
    ]
    strict_raw_span_cost = next(
        (
            row for row in cost_summary
            if row.get("domain") == "raw_span_hamming" and row.get("policy") == "strict"
        ),
        None,
    )
    normal_raw_span_cost = next(
        (
            row for row in cost_summary
            if row.get("domain") == "raw_span_hamming" and row.get("policy") == "normal"
        ),
        None,
    )

    return [
        {
            "decision": "broad_plumbing_status",
            "status": "keep",
            "evidence": "broad stays for plumbing completeness",
            "detail": (
                f"inventory_delta={int(broad_inventory['total_words_delta_compare_minus_baseline'])}"
                if broad_inventory is not None else "inventory_delta=unknown"
            ),
        },
        {
            "decision": "normal_baseline_status",
            "status": "keep",
            "evidence": "normal remains the baseline",
            "detail": (
                "broad close to normal and strict is materially more restrictive"
                if broad_inventory is not None and strict_inventory is not None else "comparison data incomplete"
            ),
        },
        {
            "decision": "strict_phase_d_status",
            "status": "defer",
            "evidence": "strict is interesting but not yet justified for calibrated rebuild",
            "detail": (
                f"false_high_span_raw_delta={strict_false_high_span[0]:.6f}; "
                f"raw_span_cost_ms_normal={float(normal_raw_span_cost['elapsed_ms_mean']):.3f}; "
                f"raw_span_cost_ms_strict={float(strict_raw_span_cost['elapsed_ms_mean']):.3f}"
                if strict_false_high_span and strict_raw_span_cost is not None and normal_raw_span_cost is not None
                else "evidence incomplete"
            ),
        },
        {
            "decision": "phase_d_trigger",
            "status": "future_only",
            "evidence": "only move to Phase D if a later dataset or campaign slice shows a much clearer strict quality advantage",
            "detail": (
                f"strict_plain_mean_delta={_mean(strict_plain_harsher)}; "
                f"broad_plain_abs_mean_delta={_mean(broad_plain_harsher)}"
            ),
        },
    ]


def _write_decision_note(path: Path, decision_rows: list[dict]) -> None:
    lines = [
        "# Phase C Decision Summary",
        "",
        "1. broad stays for plumbing completeness",
        "2. normal remains the baseline",
        "3. strict is interesting but not yet justified for calibrated rebuild",
        "4. only move to Phase D if a later dataset or campaign slice shows a much clearer strict quality advantage",
        "",
        "Evidence:",
    ]
    for row in decision_rows:
        lines.append(f"- {row['decision']}: {row['status']} | {row['detail']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    policy_dirs = _discover_policy_dirs(POLICY_ASSET_ROOT, POLICIES_TO_COMPARE)
    for name, policy_dir in policy_dirs.items():
        if not policy_dir.exists():
            raise FileNotFoundError(f"Missing policy asset dir for {name}: {policy_dir}")
    if not DATASET_FP.exists():
        raise FileNotFoundError(f"Missing hard-case dataset: {DATASET_FP}")

    run_id = f"{_timestamp()}__report_hamming_dictionary_policy_phase_c_v1"
    out_dir = OUTPUT_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[hamming_dictionary_policy_phase_c] loading policy backends...", flush=True)
    hamming_backends: dict[str, HammingBackend] = {}
    span_backends: dict[str, SpanHammingBackend] = {}
    policy_wordlists: dict[str, dict[int, list[list[int]]]] = {}
    for policy, policy_dir in policy_dirs.items():
        wl_ltr, _ = _load_policy_wordlists(policy_dir)
        policy_wordlists[policy] = wl_ltr
        hamming_backends[policy] = HammingBackend(wl_ltr, None)
        span_backends[policy] = SpanHammingBackend(config=SPAN_CFG, wordlist_dir=policy_dir, require_selected=True)

    rows: list[SampleRow] = []

    print("[hamming_dictionary_policy_phase_c] scoring plain hamming corpus slices...", flush=True)
    for sample_id, start, length in PLAIN_SLICES:
        pt, wli = _slice_plaintext(start, length)
        for policy, backend in hamming_backends.items():
            for pct in CORRUPT_PCTS:
                mutated = _corrupt_text(pt, pct, seed=(length * 1000 + pct))
                t0 = time.perf_counter()
                stats = backend.total_min_hd_stats(mutated, wli)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                rows.append(
                    SampleRow(
                        domain="plain_hamming",
                        policy=policy,
                        sample_id=sample_id,
                        family="corruption_curve",
                        condition=f"corrupt_{pct:03d}",
                        length=int(length),
                        category=None,
                        total_hd=float(stats["total_hd"]),
                        avg_hd_word=float(stats["avg_hd_word"]),
                        n_words=float(stats["n_words"]),
                        span_raw=None,
                        coverage=None,
                        quality=None,
                        n_intervals_selected=None,
                        elapsed_ms=float(elapsed_ms),
                    )
                )
            for seed in RANDOM_SEEDS:
                rnd = _random_text(length, seed=(length * 1000 + seed))
                t0 = time.perf_counter()
                stats = backend.total_min_hd_stats(rnd, wli)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                rows.append(
                    SampleRow(
                        domain="plain_hamming",
                        policy=policy,
                        sample_id=sample_id,
                        family="random_uniform",
                        condition=f"seed_{seed:02d}",
                        length=int(length),
                        category=None,
                        total_hd=float(stats["total_hd"]),
                        avg_hd_word=float(stats["avg_hd_word"]),
                        n_words=float(stats["n_words"]),
                        span_raw=None,
                        coverage=None,
                        quality=None,
                        n_intervals_selected=None,
                        elapsed_ms=float(elapsed_ms),
                    )
                )

    print("[hamming_dictionary_policy_phase_c] scoring raw span-hamming hard cases...", flush=True)
    dataset = load_nowli_hard_cases_v1(DATASET_FP)
    for case in dataset.cases:
        for policy, backend in span_backends.items():
            t0 = time.perf_counter()
            stats = backend.score(case.candidate_plaintext_idx)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            rows.append(
                SampleRow(
                    domain="raw_span_hamming",
                    policy=policy,
                    sample_id=case.case_id,
                    family="hard_case",
                    condition=case.status,
                    length=int(case.length),
                    category=case.category,
                    total_hd=None,
                    avg_hd_word=None,
                    n_words=None,
                    span_raw=float(stats.span_raw),
                    coverage=float(stats.coverage),
                    quality=float(stats.quality),
                    n_intervals_selected=int(stats.n_intervals_selected),
                    elapsed_ms=float(elapsed_ms),
                )
            )

    sample_rows = [row.__dict__ for row in rows]
    policy_inventory = _policy_inventory_rows(policy_wordlists)
    policy_inventory_deltas = _policy_inventory_deltas(policy_inventory, baseline=COMPARE_BASELINE_POLICY)
    plain_summary = _summarize_plain(rows)
    span_summary = _summarize_span(rows)
    delta_rows = _case_policy_deltas(rows, baseline=COMPARE_BASELINE_POLICY)
    plain_deltas = _plain_policy_deltas(plain_summary, baseline=COMPARE_BASELINE_POLICY)
    cost_summary = _summarize_cost(rows)
    decision_summary = _build_decision_summary(policy_inventory_deltas, plain_deltas, delta_rows, cost_summary)

    _write_csv(out_dir / "policy_inventory.csv", policy_inventory)
    _write_csv(out_dir / "policy_inventory_deltas.csv", policy_inventory_deltas)
    _write_csv(out_dir / "samples.csv", sample_rows)
    _write_csv(out_dir / "summary_plain_hamming.csv", plain_summary)
    _write_csv(out_dir / "summary_raw_span_hamming.csv", span_summary)
    _write_csv(out_dir / "summary_policy_costs.csv", cost_summary)
    _write_csv(out_dir / "decision_summary.csv", decision_summary)
    _write_csv(out_dir / "raw_span_case_deltas.csv", delta_rows)
    _write_csv(out_dir / "plain_hamming_policy_deltas.csv", plain_deltas)
    _write_decision_note(out_dir / "decision_summary.md", decision_summary)
    (out_dir / "run_config.json").write_text(
        json.dumps(
            {
                "dataset_fp": str(DATASET_FP),
                "policy_dirs": {k: str(v) for k, v in policy_dirs.items()},
                "policies_to_compare": list(POLICIES_TO_COMPARE),
                "compare_baseline_policy": COMPARE_BASELINE_POLICY,
                "plain_slices": list(PLAIN_SLICES),
                "corrupt_pcts": list(CORRUPT_PCTS),
                "random_seeds": list(RANDOM_SEEDS),
                "span_cfg": {
                    "len_min": SPAN_CFG.len_min,
                    "len_max": SPAN_CFG.len_max,
                    "max_hd": SPAN_CFG.max_hd,
                    "start_stride": SPAN_CFG.start_stride,
                    "max_candidates_per_window": SPAN_CFG.max_candidates_per_window,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[hamming_dictionary_policy_phase_c] wrote policy inventory: {out_dir / 'policy_inventory.csv'}", flush=True)
    print(f"[hamming_dictionary_policy_phase_c] wrote policy inventory deltas: {out_dir / 'policy_inventory_deltas.csv'}", flush=True)
    print(f"[hamming_dictionary_policy_phase_c] wrote samples: {out_dir / 'samples.csv'}", flush=True)
    print(f"[hamming_dictionary_policy_phase_c] wrote plain summary: {out_dir / 'summary_plain_hamming.csv'}", flush=True)
    print(f"[hamming_dictionary_policy_phase_c] wrote plain deltas: {out_dir / 'plain_hamming_policy_deltas.csv'}", flush=True)
    print(f"[hamming_dictionary_policy_phase_c] wrote span summary: {out_dir / 'summary_raw_span_hamming.csv'}", flush=True)
    print(f"[hamming_dictionary_policy_phase_c] wrote cost summary: {out_dir / 'summary_policy_costs.csv'}", flush=True)
    print(f"[hamming_dictionary_policy_phase_c] wrote decision summary: {out_dir / 'decision_summary.csv'}", flush=True)
    print(f"[hamming_dictionary_policy_phase_c] wrote case deltas: {out_dir / 'raw_span_case_deltas.csv'}", flush=True)


if __name__ == "__main__":
    main()
