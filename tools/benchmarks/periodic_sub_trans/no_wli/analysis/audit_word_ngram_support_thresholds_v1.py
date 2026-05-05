from __future__ import annotations

"""
Report-only audit of word-ngram support and activation thresholds.

This recomputes word-ngram diagnostics for the saved historical candidate texts
and sweeps support formulas over the existing historical pair labels. It does
not change runtime scoring or solver selection.
"""

import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


RUN_LABEL = "word_ngram_support_thresholds_v1"

PAIR_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
UNIQUE_PARTIAL_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_partial_text_review_v1/unique_partial_text_rows.csv"
)
WORD_NGRAM_SQLITE_REL = (
    "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/"
    "20260308T024914Z__build_word_ngram_sqlite_asset_phase2_v1/"
    "word_ngrams_tokenized64_phase2_v1.sqlite"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "word_ngram_support_thresholds_v1"
)

WORD_NGRAM_ALPHA = 0.4
WORD_NGRAM_MISS_LOGP = -20.0
WORD_NGRAM_PREFIX_THRESHOLDS = (1, 10, 100)
ACTIVATION_THRESHOLDS = (1, 3, 6, 9, 12, 18, 24)
SPLIT_TOP_N = 30
PROGRESS_EVERY = 50


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

from rune_decrypter_prime.scoring.span_hamming.fast_backend import (  # noqa: E402
    FastSpanHammingBackend,
    fast_span_hamming_available,
)
from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig  # noqa: E402
from rune_decrypter_prime.scoring.word_ngrams import RuneTokenWordNgramJudgeRuntime  # noqa: E402


PAIR_ROWS = REPO_ROOT / PAIR_ROWS_REL
UNIQUE_PARTIAL_ROWS = REPO_ROOT / UNIQUE_PARTIAL_ROWS_REL
WORD_NGRAM_SQLITE = REPO_ROOT / WORD_NGRAM_SQLITE_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


CandidateRow = dict[str, Any]
PairRow = Mapping[str, str]
Formula = Callable[[Mapping[str, Any], int], float | None]


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(out):
        return float(default)
    return float(out)


def parse_numeric_tokens(token_sequence_text: str) -> list[int]:
    try:
        values = [int(part) for part in str(token_sequence_text).split()]
    except ValueError as exc:
        raise ValueError("token sequence must contain integers only") from exc
    if not values:
        raise ValueError("token sequence is empty")
    bad = [value for value in values if value < 0 or value > 28]
    if bad:
        raise ValueError("numeric rune/base-29 tokens must be in 0..28")
    return values


def _required_token_hashes(pair_rows: Sequence[PairRow]) -> set[str]:
    out: set[str] = set()
    for row in pair_rows:
        for key in ("winner_token_hash", "challenger_token_hash"):
            value = str(row.get(key, "") or "").strip()
            if value:
                out.add(value)
    return out


def load_required_token_rows(token_hashes: set[str]) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    with UNIQUE_PARTIAL_ROWS.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            token_hash = str(row.get("partial_text_hash", "") or "").strip()
            if token_hash in token_hashes:
                found[token_hash] = dict(row)
                if len(found) == len(token_hashes):
                    break
    return found


def word_ngram_support_score(row: Mapping[str, Any], formula_id: str) -> float:
    ge1 = _safe_float(row.get("prefix_total_ge_1_rate"))
    ge10 = _safe_float(row.get("prefix_total_ge_10_rate"))
    ge100 = _safe_float(row.get("prefix_total_ge_100_rate"))
    n_positions = max(0.0, _safe_float(row.get("word_ngram_n_positions")))
    if formula_id == "ge10_ge100":
        return float(0.5 * ge10 + 0.5 * ge100)
    if formula_id == "ge1_ge10_ge100":
        return float(0.2 * ge1 + 0.4 * ge10 + 0.4 * ge100)
    if formula_id == "ge10_only":
        return float(ge10)
    if formula_id == "ge100_only":
        return float(ge100)
    if formula_id == "positions_log_ge10_ge100":
        pos_weight = min(1.0, math.log1p(n_positions) / math.log1p(24.0))
        return float(pos_weight * (0.5 * ge10 + 0.5 * ge100))
    raise ValueError(f"unsupported support formula: {formula_id}")


def _candidate_features(
    *,
    token_hash: str,
    token_row: Mapping[str, str],
    backend: FastSpanHammingBackend,
    runtime: RuneTokenWordNgramJudgeRuntime,
) -> CandidateRow:
    base: CandidateRow = {
        "token_hash": str(token_hash),
        "numeric_valid": 0,
        "numeric_missing_reason": "",
        "token_length": "",
        "span_selected_interval_count": "",
        "word_ngram_available": 0,
        "word_ngram_active_minpos1": 0,
        "word_ngram_missing_reason_minpos1": "",
        "word_ngram_token_count": "",
        "word_ngram_segment_count": "",
        "word_ngram_n_positions": "",
        "word_ngram_xent": "",
        "word_ngram_backoff_xent": "",
        "word_ngram_miss_rate": "",
        "word_ngram_backoff_used_rate": "",
        "prefix_total_mean": "",
        "prefix_total_min": "",
        "prefix_total_ge_1_rate": "",
        "prefix_total_ge_10_rate": "",
        "prefix_total_ge_100_rate": "",
    }
    try:
        tokens = parse_numeric_tokens(str(token_row.get("token_sequence_text", "")))
        stats = backend.score(tokens)
        selected_intervals = tuple(stats.selected_intervals)
        report = runtime.score_candidate(
            text_idx=tokens,
            selected_intervals=selected_intervals,
            direction="ltr",
        )
        used_rates = [
            report.used5_rate,
            report.used4_rate,
            report.used3_rate,
        ]
        backoff_used_rate = (
            ""
            if any(value is None for value in used_rates)
            else float(sum(float(value) for value in used_rates if value is not None))
        )
        base.update(
            numeric_valid=1,
            token_length=int(len(tokens)),
            span_selected_interval_count=int(len(selected_intervals)),
            word_ngram_available=int(1 if bool(report.available) else 0),
            word_ngram_active_minpos1=int(1 if bool(report.active) else 0),
            word_ngram_missing_reason_minpos1=str(report.inactive_reason or ""),
            word_ngram_token_count=int(report.exact_word_count),
            word_ngram_segment_count=int(report.segment_count),
            word_ngram_n_positions=int(report.n_positions),
            word_ngram_xent=("" if report.xent_3 is None else float(report.xent_3)),
            word_ngram_backoff_xent=(
                "" if report.xent_backoff_5_4_3 is None else float(report.xent_backoff_5_4_3)
            ),
            word_ngram_miss_rate=("" if report.miss_rate is None else float(report.miss_rate)),
            word_ngram_backoff_used_rate=backoff_used_rate,
            prefix_total_mean=float(report.prefix_total_mean),
            prefix_total_min=float(report.prefix_total_min),
            prefix_total_ge_1_rate=float(report.prefix_total_ge_1_rate),
            prefix_total_ge_10_rate=float(report.prefix_total_ge_10_rate),
            prefix_total_ge_100_rate=float(report.prefix_total_ge_100_rate),
        )
    except Exception as exc:
        base["numeric_missing_reason"] = type(exc).__name__ + ": " + str(exc)
    return base


def _feature_formulas() -> list[tuple[str, str, Formula]]:
    formulas: list[tuple[str, str, Formula]] = []
    support_ids = (
        "ge10_ge100",
        "ge1_ge10_ge100",
        "ge10_only",
        "ge100_only",
        "positions_log_ge10_ge100",
    )
    for support_id in support_ids:
        formulas.append(
            (
                f"support_{support_id}",
                "higher",
                lambda row, threshold, support_id=support_id: (
                    word_ngram_support_score(row, support_id)
                    if int(_safe_float(row.get("word_ngram_n_positions"))) >= int(threshold)
                    else 0.0
                ),
            )
        )
    formulas.extend(
        [
            (
                "active_indicator",
                "higher",
                lambda row, threshold: (
                    1.0
                    if int(_safe_float(row.get("word_ngram_n_positions"))) >= int(threshold)
                    else 0.0
                ),
            ),
            (
                "n_positions",
                "higher",
                lambda row, threshold: (
                    _safe_float(row.get("word_ngram_n_positions"))
                    if int(_safe_float(row.get("word_ngram_n_positions"))) >= int(threshold)
                    else 0.0
                ),
            ),
            (
                "xent_active_only",
                "lower",
                lambda row, threshold: (
                    _safe_float(row.get("word_ngram_xent"))
                    if int(_safe_float(row.get("word_ngram_n_positions"))) >= int(threshold)
                    else None
                ),
            ),
            (
                "miss_rate_active_only",
                "lower",
                lambda row, threshold: (
                    _safe_float(row.get("word_ngram_miss_rate"))
                    if int(_safe_float(row.get("word_ngram_n_positions"))) >= int(threshold)
                    else None
                ),
            ),
        ]
    )
    return formulas


def _preference(*, winner: float, challenger: float, direction: str) -> str:
    if abs(float(winner) - float(challenger)) <= 1e-12:
        return "tie"
    if direction == "higher":
        return "truth_better" if winner > challenger else "truth_worse"
    if direction == "lower":
        return "truth_better" if winner < challenger else "truth_worse"
    raise ValueError(f"unsupported direction: {direction}")


def evaluate_feature(
    *,
    pair_rows: Sequence[PairRow],
    candidate_by_hash: Mapping[str, Mapping[str, Any]],
    feature_name: str,
    direction: str,
    threshold: int,
    formula: Formula,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "feature_name": feature_name,
        "direction": direction,
        "min_positions": int(threshold),
        "pair_count": 0,
        "available_pair_count": 0,
        "missing_pair_count": 0,
        "truth_better": 0,
        "truth_worse": 0,
        "tie": 0,
        "rescues": 0,
        "breaks": 0,
        "current_misranked_pair_count": 0,
        "current_correct_control_pair_count": 0,
    }
    for pair in pair_rows:
        winner_hash = str(pair.get("winner_token_hash", "") or "").strip()
        challenger_hash = str(pair.get("challenger_token_hash", "") or "").strip()
        winner_row = candidate_by_hash.get(winner_hash)
        challenger_row = candidate_by_hash.get(challenger_hash)
        if winner_row is None or challenger_row is None:
            row["missing_pair_count"] += 1
            continue
        winner_value = formula(winner_row, int(threshold))
        challenger_value = formula(challenger_row, int(threshold))
        if winner_value is None or challenger_value is None:
            row["missing_pair_count"] += 1
            continue
        row["pair_count"] += 1
        pref = _preference(
            winner=float(winner_value),
            challenger=float(challenger_value),
            direction=str(direction),
        )
        if pref == "tie":
            row["tie"] += 1
        else:
            row["available_pair_count"] += 1
            row[pref] += 1
        current_correct = str(pair.get("current_score_correct", "")).strip() == "1"
        if current_correct:
            row["current_correct_control_pair_count"] += 1
            if pref == "truth_worse":
                row["breaks"] += 1
        else:
            row["current_misranked_pair_count"] += 1
            if pref == "truth_better":
                row["rescues"] += 1
    row["net"] = int(row["rescues"]) - int(row["breaks"])
    return row


def _split_predicates() -> list[tuple[str, Callable[[PairRow], bool]]]:
    return [
        ("fixture_seed_even", lambda p: int(str(p.get("fixture_seed") or "0") or 0) % 2 == 0),
        ("fixture_seed_odd", lambda p: int(str(p.get("fixture_seed") or "0") or 0) % 2 == 1),
        ("fixture_family_seed_7000s", lambda p: str(p.get("fixture_seed") or "").startswith("7")),
        ("fixture_family_seed_x11", lambda p: str(p.get("fixture_seed") or "").endswith("11")),
        ("current_score_margin_abs_lt_0p01", lambda p: abs(_safe_float(p.get("current_score_margin"))) < 0.01),
        ("current_score_margin_abs_ge_0p01", lambda p: abs(_safe_float(p.get("current_score_margin"))) >= 0.01),
    ]


def _split_rows(
    *,
    pair_rows: Sequence[PairRow],
    candidate_by_hash: Mapping[str, Mapping[str, Any]],
    summary_rows: Sequence[Mapping[str, Any]],
    formulas_by_name: Mapping[str, tuple[str, Formula]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    top = sorted(
        summary_rows,
        key=lambda item: (int(item.get("net", 0)), int(item.get("rescues", 0))),
        reverse=True,
    )[:SPLIT_TOP_N]
    for summary in top:
        feature_name = str(summary["feature_name"])
        direction, formula = formulas_by_name[feature_name]
        threshold = int(summary["min_positions"])
        for split_name, predicate in _split_predicates():
            rows = [row for row in pair_rows if predicate(row)]
            split = evaluate_feature(
                pair_rows=rows,
                candidate_by_hash=candidate_by_hash,
                feature_name=feature_name,
                direction=direction,
                threshold=threshold,
                formula=formula,
            )
            split["split_name"] = split_name
            split["parent_net"] = int(summary["net"])
            out.append(split)
    return out


def _active_counts(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    total = len(candidate_rows)
    for threshold in ACTIVATION_THRESHOLDS:
        active = sum(
            1
            for row in candidate_rows
            if int(_safe_float(row.get("word_ngram_n_positions"))) >= int(threshold)
        )
        out.append(
            {
                "min_positions": int(threshold),
                "active_candidates": int(active),
                "candidate_count": int(total),
                "active_rate": float(active / max(1, total)),
            }
        )
    return out


def _build_readout(
    *,
    summary: Mapping[str, Any],
    active_rows: Sequence[Mapping[str, Any]],
    feature_rows: Sequence[Mapping[str, Any]],
    split_rows: Sequence[Mapping[str, Any]],
) -> str:
    lines = [
        "# Word-Ngram Support Thresholds v1",
        "",
        "## Status",
        "",
        "- Report-only; no runtime behaviour changed.",
        f"- candidate rows: `{summary['candidate_row_count']}`",
        f"- pair rows: `{summary['pair_row_count']}`",
        f"- feature summary rows: `{summary['feature_summary_row_count']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.2f}`",
        "",
        "## Activation Counts",
        "",
        "| min positions | active candidates | active rate |",
        "|---:|---:|---:|",
    ]
    for row in active_rows:
        lines.append(
            f"| {row['min_positions']} | {row['active_candidates']}/{row['candidate_count']} | "
            f"{float(row['active_rate']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Top Direct Features",
            "",
            "| feature | min positions | direction | rescues | breaks | net |",
            "|---|---:|---|---:|---:|---:|",
        ]
    )
    for row in feature_rows[:15]:
        lines.append(
            f"| {row['feature_name']} | {row['min_positions']} | {row['direction']} | "
            f"{row['rescues']} | {row['breaks']} | {row['net']} |"
        )
    if feature_rows:
        top = feature_rows[0]
        top_splits = [
            row
            for row in split_rows
            if row["feature_name"] == top["feature_name"]
            and int(row["min_positions"]) == int(top["min_positions"])
        ]
        lines.extend(
            [
                "",
                "## Top Row Splits",
                "",
                "| split | rescues | breaks | net |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in top_splits:
            lines.append(
                f"| {row['split_name']} | {row['rescues']} | {row['breaks']} | {row['net']} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Support/trust features are the useful family in this audit.",
            "- Raw xent/miss-rate rows are only evaluated when both sides meet the activation threshold.",
            "- This is still direct pairwise evidence; joint use with span-Hamming needs separate validation.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_audit() -> dict[str, Any]:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not WORD_NGRAM_SQLITE.exists():
        raise FileNotFoundError("missing word-ngram sqlite: " + _repo_rel(WORD_NGRAM_SQLITE))
    if not fast_span_hamming_available():
        raise RuntimeError("FastSpanHammingBackend is required for this audit")

    pair_rows = _read_csv(PAIR_ROWS)
    token_hashes = sorted(_required_token_hashes(pair_rows))
    token_rows = load_required_token_rows(set(token_hashes))
    missing_hashes = sorted(set(token_hashes) - set(token_rows))

    backend = FastSpanHammingBackend(
        config=SpanHammingConfig(debug_return_intervals=True),
        return_raw_intervals=False,
    )
    runtime = RuneTokenWordNgramJudgeRuntime.open_sqlite(
        WORD_NGRAM_SQLITE,
        alpha=WORD_NGRAM_ALPHA,
        miss_logp=WORD_NGRAM_MISS_LOGP,
        min_positions=1,
        prefix_total_thresholds=WORD_NGRAM_PREFIX_THRESHOLDS,
    )
    try:
        candidate_rows: list[CandidateRow] = []
        total = len(token_hashes)
        for index, token_hash in enumerate(token_hashes, start=1):
            if index == 1 or index % PROGRESS_EVERY == 0 or index == total:
                elapsed = time.perf_counter() - started
                rate = index / elapsed if elapsed > 0.0 else 0.0
                eta = (total - index) / rate if rate > 0.0 else 0.0
                print(
                    f"[{RUN_LABEL}] progress {index}/{total} "
                    f"elapsed={elapsed:.1f}s eta={eta:.1f}s",
                    flush=True,
                )
            candidate_rows.append(
                _candidate_features(
                    token_hash=token_hash,
                    token_row=token_rows.get(token_hash, {}),
                    backend=backend,
                    runtime=runtime,
                )
            )
    finally:
        runtime.close()

    candidate_by_hash = {str(row["token_hash"]): row for row in candidate_rows}
    formula_specs = _feature_formulas()
    formulas_by_name = {
        name: (direction, formula)
        for name, direction, formula in formula_specs
    }
    feature_summary_rows: list[dict[str, Any]] = []
    for threshold in ACTIVATION_THRESHOLDS:
        for feature_name, direction, formula in formula_specs:
            feature_summary_rows.append(
                evaluate_feature(
                    pair_rows=pair_rows,
                    candidate_by_hash=candidate_by_hash,
                    feature_name=feature_name,
                    direction=direction,
                    threshold=int(threshold),
                    formula=formula,
                )
            )
    feature_summary_rows.sort(
        key=lambda row: (int(row["net"]), int(row["rescues"]), -int(row["breaks"])),
        reverse=True,
    )
    split_rows = _split_rows(
        pair_rows=pair_rows,
        candidate_by_hash=candidate_by_hash,
        summary_rows=feature_summary_rows,
        formulas_by_name=formulas_by_name,
    )
    split_rows.sort(
        key=lambda row: (
            str(row["feature_name"]),
            int(row["min_positions"]),
            str(row["split_name"]),
        )
    )
    active_rows = _active_counts(candidate_rows)

    candidate_fields = [
        "token_hash",
        "numeric_valid",
        "numeric_missing_reason",
        "token_length",
        "span_selected_interval_count",
        "word_ngram_available",
        "word_ngram_active_minpos1",
        "word_ngram_missing_reason_minpos1",
        "word_ngram_token_count",
        "word_ngram_segment_count",
        "word_ngram_n_positions",
        "word_ngram_xent",
        "word_ngram_backoff_xent",
        "word_ngram_miss_rate",
        "word_ngram_backoff_used_rate",
        "prefix_total_mean",
        "prefix_total_min",
        "prefix_total_ge_1_rate",
        "prefix_total_ge_10_rate",
        "prefix_total_ge_100_rate",
    ]
    summary_fields = [
        "feature_name",
        "direction",
        "min_positions",
        "pair_count",
        "available_pair_count",
        "missing_pair_count",
        "truth_better",
        "truth_worse",
        "tie",
        "rescues",
        "breaks",
        "net",
        "current_misranked_pair_count",
        "current_correct_control_pair_count",
    ]
    split_fields = ["split_name", "parent_net", *summary_fields]

    candidate_csv = OUTPUT_DIR / "word_ngram_support_candidate_features.csv"
    active_csv = OUTPUT_DIR / "word_ngram_support_activation_counts.csv"
    feature_csv = OUTPUT_DIR / "word_ngram_support_feature_summary.csv"
    split_csv = OUTPUT_DIR / "word_ngram_support_split_validation.csv"
    _write_csv(candidate_csv, candidate_rows, candidate_fields)
    _write_csv(active_csv, active_rows, ["min_positions", "active_candidates", "candidate_count", "active_rate"])
    _write_csv(feature_csv, feature_summary_rows, summary_fields)
    _write_csv(split_csv, split_rows, split_fields)

    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_behavior_changed": False,
        "pair_rows": _repo_rel(PAIR_ROWS),
        "unique_partial_rows": _repo_rel(UNIQUE_PARTIAL_ROWS),
        "word_ngram_sqlite": _repo_rel(WORD_NGRAM_SQLITE),
        "output_dir": _repo_rel(OUTPUT_DIR),
        "pair_row_count": len(pair_rows),
        "required_token_hash_count": len(token_hashes),
        "candidate_row_count": len(candidate_rows),
        "missing_token_hash_count": len(missing_hashes),
        "missing_token_hashes": missing_hashes,
        "activation_thresholds": list(ACTIVATION_THRESHOLDS),
        "feature_summary_row_count": len(feature_summary_rows),
        "split_validation_row_count": len(split_rows),
        "elapsed_seconds": time.perf_counter() - started,
        "candidate_features_csv": _repo_rel(candidate_csv),
        "activation_counts_csv": _repo_rel(active_csv),
        "feature_summary_csv": _repo_rel(feature_csv),
        "split_validation_csv": _repo_rel(split_csv),
        "top_net_rows": feature_summary_rows[:20],
    }
    (OUTPUT_DIR / "word_ngram_support_summary.json").write_text(
        json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "word_ngram_support_readout.md").write_text(
        _build_readout(
            summary=summary,
            active_rows=active_rows,
            feature_rows=feature_summary_rows,
            split_rows=split_rows,
        ),
        encoding="utf-8",
    )
    print(
        f"[{RUN_LABEL}] done rows={len(candidate_rows)} "
        f"elapsed={summary['elapsed_seconds']:.1f}s output={_repo_rel(OUTPUT_DIR)}",
        flush=True,
    )
    return summary


def main() -> None:
    run_audit()


if __name__ == "__main__":
    main()
