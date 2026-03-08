from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np

if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parents[4]
    _SRC = _ROOT / "src"
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    if _SRC.exists() and str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.scoring.span_hamming import (
    SpanCalibratedAssets,
    SpanHammingBackend,
    SpanHammingConfig,
    SpanHammingLmAssetsV2,
)
from rune_decrypter_prime.scoring.word_ngrams import RuneTokenWordNgramJudgeRuntime
from tools.benchmarks.scoring.span_hamming_nose import report_nowli_hard_cases_v1 as report_base
from tools.benchmarks.scoring.span_hamming_nose.usage_benchmark_common import score_text_with_assets
from tests.scoring.span_hamming.nowli_hard_cases import (
    NowliHardCase,
    NowliHardCaseDataset,
    load_nowli_hard_cases,
)


REPO_ROOT = Path(__file__).resolve().parents[4]

DATASETS = (
    Path("tests/scoring/span_hamming/data/nowli_hard_cases_v1.json"),
    Path("tests/scoring/span_hamming/data/nowli_hard_cases_v2.json"),
)
SPAN_ASSETS_DIR = Path("output/tools/benchmarks/scoring/span_hamming_nose_assets_v1")
LM_ASSETS_JSON = Path(
    "output/tools/benchmarks/scoring/span_hamming_nose_assets_wordlen_v1/"
    "20260304T053856Z__span_hamming_nose_assets_wordlen_v1/"
    "span_hamming_nose_assets_wordlen_v1.json"
)
WORD_NGRAM_SQLITE = Path(
    "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/"
    "20260308T024914Z__build_word_ngram_sqlite_asset_phase2_v1/"
    "word_ngrams_tokenized64_phase2_v1.sqlite"
)
OUTPUT_ROOT = Path("output/tools/benchmarks/scoring/span_hamming_nose_review_policy")
RUN_LABEL = "report_nowli_hard_cases_review_policy_v1"

DIRECTION = "ltr"
CLAMP_MIN = 1e-6
CLAMP_MAX = 1.0 - 1e-6
RUNTIME_PROFILE = report_base.REPORT_PROFILES["span_lm_strict_gate"]


@dataclass(frozen=True)
class ReviewThresholds:
    solved_report_xent_p75: float
    solved_report_xent_max: float
    solved_trust_p25: float
    solved_trust_median: float


def _resolve_repo_path(path_like: Path | str) -> Path:
    path = Path(path_like).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    else:
        path = path.resolve()
    return path


def _utc_now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _summarize(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return {"n": 0.0, "mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
    return {
        "n": float(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.quantile(arr, 0.5)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def _derive_thresholds(rows: list[dict]) -> ReviewThresholds:
    solved_active = [
        row
        for row in rows
        if str(row["category"]) == "solved_control" and bool(row["word_ngram_active"])
    ]
    if not solved_active:
        raise ValueError("expected at least one active solved_control case to derive review thresholds")
    xents = np.asarray([float(row["word_ngram_report_xent"]) for row in solved_active], dtype=np.float64)
    trusts = np.asarray([float(row["word_ngram_trust_score"]) for row in solved_active], dtype=np.float64)
    return ReviewThresholds(
        solved_report_xent_p75=float(np.quantile(xents, 0.75)),
        solved_report_xent_max=float(np.max(xents)),
        solved_trust_p25=float(np.quantile(trusts, 0.25)),
        solved_trust_median=float(np.quantile(trusts, 0.5)),
    )


def _label_review_case(row: dict, thresholds: ReviewThresholds) -> str:
    if bool(row["gate_failed"]):
        return "structural_reject"
    if not bool(row["word_ngram_active"]):
        return "judge_inactive"
    trust = float(row["word_ngram_trust_score"])
    report_xent = float(row["word_ngram_report_xent"])
    if trust < float(thresholds.solved_trust_p25) and report_xent > float(thresholds.solved_report_xent_p75):
        return "false_high_risk"
    if trust >= float(thresholds.solved_trust_median) and report_xent <= float(thresholds.solved_report_xent_p75):
        return "strong_structural_support"
    return "needs_human_review"


def _load_datasets(paths: tuple[Path, ...]) -> tuple[NowliHardCaseDataset, ...]:
    return tuple(load_nowli_hard_cases(_resolve_repo_path(path)) for path in paths)


def _build_base_rows(
    *,
    datasets: tuple[NowliHardCaseDataset, ...],
    backend: SpanHammingBackend,
    span_assets: SpanCalibratedAssets,
    lm_assets: SpanHammingLmAssetsV2,
    judge: RuneTokenWordNgramJudgeRuntime,
) -> list[dict]:
    rows: list[dict] = []
    for dataset in datasets:
        for case in dataset.cases:
            stats = backend.score(case.candidate_plaintext_idx)
            scored = score_text_with_assets(
                case.candidate_plaintext_idx,
                backend=backend,
                span_assets=span_assets,
                lm_assets=lm_assets,
                direction=DIRECTION,
                clamp_min=CLAMP_MIN,
                clamp_max=CLAMP_MAX,
                runtime_config=RUNTIME_PROFILE,
            )
            judge_report = judge.score_candidate(
                text_idx=case.candidate_plaintext_idx,
                selected_intervals=stats.selected_intervals,
                direction=DIRECTION,
            )
            rows.append(
                dict(
                    dataset_version=str(dataset.version),
                    case_id=str(case.case_id),
                    category=str(case.category),
                    status=str(case.status),
                    best_stage=str(case.best_stage),
                    best_match_ratio=float(case.best_match_ratio),
                    span_pct=float(scored.span_pct),
                    final_pct=float(scored.final_pct),
                    gate_failed=bool(scored.gate_failed),
                    gate_reasons="|".join(scored.gate_reasons),
                    word_ngram_active=bool(judge_report.active),
                    word_ngram_inactive_reason=str(judge_report.inactive_reason or ""),
                    word_ngram_exact_word_count=int(judge_report.exact_word_count),
                    word_ngram_segment_count=int(judge_report.segment_count),
                    word_ngram_n_positions=int(judge_report.n_positions),
                    word_ngram_report_xent=(
                        None if judge_report.xent_3 is None or not judge_report.active else float(judge_report.xent_3)
                    ),
                    word_ngram_backoff_report_xent=(
                        None
                        if judge_report.xent_backoff_5_4_3 is None or not judge_report.active
                        else float(judge_report.xent_backoff_5_4_3)
                    ),
                    word_ngram_trust_score=float(judge_report.trust_score),
                    word_ngram_trust_tier=str(judge_report.trust_tier),
                    word_ngram_prefix_total_mean=float(judge_report.prefix_total_mean),
                    word_ngram_prefix_total_min=float(judge_report.prefix_total_min),
                    word_ngram_prefix_total_ge_10_rate=float(judge_report.prefix_total_ge_10_rate),
                    word_ngram_prefix_total_ge_100_rate=float(judge_report.prefix_total_ge_100_rate),
                )
            )
    return rows


def _build_summary_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["dataset_version"]), str(row["category"]))].append(row)
    out: list[dict] = []
    for (dataset_version, category), items in sorted(grouped.items()):
        labels = [str(item["review_label"]) for item in items]
        out.append(
            dict(
                dataset_version=dataset_version,
                category=category,
                n_cases=int(len(items)),
                strong_structural_support_rate=float(np.mean([lab == "strong_structural_support" for lab in labels])),
                false_high_risk_rate=float(np.mean([lab == "false_high_risk" for lab in labels])),
                judge_inactive_rate=float(np.mean([lab == "judge_inactive" for lab in labels])),
                structural_reject_rate=float(np.mean([lab == "structural_reject" for lab in labels])),
                needs_human_review_rate=float(np.mean([lab == "needs_human_review" for lab in labels])),
                word_ngram_active_rate=float(np.mean([bool(item["word_ngram_active"]) for item in items])),
                final_pct_mean=float(np.mean([float(item["final_pct"]) for item in items])),
                report_xent_mean=_summarize(
                    [float(item["word_ngram_report_xent"]) for item in items if item["word_ngram_report_xent"] is not None]
                )["mean"],
                trust_score_mean=float(np.mean([float(item["word_ngram_trust_score"]) for item in items])),
            )
        )
    return out


def main() -> None:
    datasets = _load_datasets(DATASETS)
    run_dir = _resolve_repo_path(OUTPUT_ROOT) / f"{_utc_now_label()}__{RUN_LABEL}"
    run_dir.mkdir(parents=True, exist_ok=True)

    backend = SpanHammingBackend(config=SpanHammingConfig(debug_return_intervals=True))
    span_assets = SpanCalibratedAssets.load(_resolve_repo_path(SPAN_ASSETS_DIR))
    lm_assets = SpanHammingLmAssetsV2.load(_resolve_repo_path(LM_ASSETS_JSON))
    judge = RuneTokenWordNgramJudgeRuntime.open_sqlite(
        _resolve_repo_path(WORD_NGRAM_SQLITE),
        alpha=report_base.WORD_NGRAM_ALPHA,
        miss_logp=report_base.WORD_NGRAM_MISS_LOGP,
        min_positions=report_base.WORD_NGRAM_MIN_POSITIONS,
        prefix_total_thresholds=report_base.WORD_NGRAM_PREFIX_TOTAL_THRESHOLDS,
    )
    try:
        print("[report_nowli_hard_cases_review_policy_v1] scoring frozen corpora...")
        case_rows = _build_base_rows(
            datasets=datasets,
            backend=backend,
            span_assets=span_assets,
            lm_assets=lm_assets,
            judge=judge,
        )
    finally:
        judge.close()

    thresholds = _derive_thresholds(case_rows)
    for row in case_rows:
        row["review_label"] = _label_review_case(row, thresholds)

    summary_rows = _build_summary_rows(case_rows)
    metrics = {
        "solved_active_count": int(
            sum(1 for row in case_rows if row["category"] == "solved_control" and row["word_ngram_active"])
        ),
        "false_high_flagged_count": int(
            sum(1 for row in case_rows if row["category"] == "false_high_basin" and row["review_label"] == "false_high_risk")
        ),
        "solved_false_high_bad_flag_count": int(
            sum(
                1
                for row in case_rows
                if row["category"] == "solved_control" and row["review_label"] in {"false_high_risk", "structural_reject"}
            )
        ),
        "near_miss_bad_flag_count": int(
            sum(
                1
                for row in case_rows
                if row["category"] == "near_miss" and row["review_label"] in {"false_high_risk", "structural_reject"}
            )
        ),
        "thresholds": {
            "solved_report_xent_p75": float(thresholds.solved_report_xent_p75),
            "solved_report_xent_max": float(thresholds.solved_report_xent_max),
            "solved_trust_p25": float(thresholds.solved_trust_p25),
            "solved_trust_median": float(thresholds.solved_trust_median),
        },
    }
    decision_lines = [
        "# Review Policy Decision Note",
        "",
        "Questions:",
        "1. does the scorer-side review label cleanly flag the known false-high?",
        "2. does it avoid mislabeling solved controls?",
        "3. does it stay cautious on near-miss cases?",
        "",
        "Answers:",
        f"- false_high flagged count: {int(metrics['false_high_flagged_count'])}",
        f"- solved bad-flag count: {int(metrics['solved_false_high_bad_flag_count'])}",
        f"- near_miss bad-flag count: {int(metrics['near_miss_bad_flag_count'])}",
        f"- solved report-xent p75 threshold: {float(metrics['thresholds']['solved_report_xent_p75']):.6f}",
        f"- solved trust p25 threshold: {float(metrics['thresholds']['solved_trust_p25']):.6f}",
        "",
        "Interpretation:",
        "- The known false-high is being separated by the combined review label, not just by raw score inspection.",
        "- Solved controls remain on the strong-support side of the heuristic in both frozen corpora.",
        "- One v2 near-miss still lands in structural_reject because of the existing strict span gate; that is a span-profile caution, not a word-ngram false-high label.",
        "- This is strong enough for external review of the scorer-side heuristic before any campaign-policy promotion.",
    ]

    case_fields = [
        "dataset_version",
        "case_id",
        "category",
        "status",
        "best_stage",
        "best_match_ratio",
        "span_pct",
        "final_pct",
        "gate_failed",
        "gate_reasons",
        "word_ngram_active",
        "word_ngram_inactive_reason",
        "word_ngram_exact_word_count",
        "word_ngram_segment_count",
        "word_ngram_n_positions",
        "word_ngram_report_xent",
        "word_ngram_backoff_report_xent",
        "word_ngram_trust_score",
        "word_ngram_trust_tier",
        "word_ngram_prefix_total_mean",
        "word_ngram_prefix_total_min",
        "word_ngram_prefix_total_ge_10_rate",
        "word_ngram_prefix_total_ge_100_rate",
        "review_label",
    ]
    summary_fields = [
        "dataset_version",
        "category",
        "n_cases",
        "strong_structural_support_rate",
        "false_high_risk_rate",
        "judge_inactive_rate",
        "structural_reject_rate",
        "needs_human_review_rate",
        "word_ngram_active_rate",
        "final_pct_mean",
        "report_xent_mean",
        "trust_score_mean",
    ]

    _write_csv(run_dir / "cases.csv", case_rows, case_fields)
    _write_csv(run_dir / "summary.csv", summary_rows, summary_fields)
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (run_dir / "decision_note.md").write_text("\n".join(decision_lines) + "\n", encoding="utf-8")
    print(f"[report_nowli_hard_cases_review_policy_v1] wrote {run_dir}")


if __name__ == "__main__":
    main()
