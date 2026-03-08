from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.scoring.span_hamming import SpanHammingBackend, SpanHammingConfig
from rune_decrypter_prime.scoring.word_ngrams import (
    RuneTokenWordNgramMemoryModel,
    RuneTokenWordNgramScorer,
    RuneTokenWordNgramSqlite,
    summarize_prefix_total_confidence,
    summarize_word_ngram_report_trust,
    word_ngram_report_is_active,
)
from tests.scoring.span_hamming.nowli_hard_cases import (
    auc_from_scores,
    exact_match_feasibility_metrics,
    extract_exact_match_tokens,
    load_nowli_hard_cases,
    segment_exact_match_tokens,
    word_token_sets_by_len,
)


OUTPUT_ROOT = REPO_ROOT / "output/tools/benchmarks/scoring/span_hamming_nose_word_ngram_sqlite_compare"
RUN_LABEL = "report_nowli_hard_cases_word_ngram_sqlite_compare_v1"
TOKENIZED_DIR = REPO_ROOT / "assets_packed/tokenized_pg"
SQLITE_ASSET_ROOT = REPO_ROOT / "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets"
SQLITE_ASSET_RUN_LABEL = "build_word_ngram_sqlite_asset_phase2_v1"
DATASETS = (
    REPO_ROOT / "tests/scoring/span_hamming/data/nowli_hard_cases_v1.json",
    REPO_ROOT / "tests/scoring/span_hamming/data/nowli_hard_cases_v2.json",
)

WORD_NGRAM_BOOK_LIMIT = 64
WORD_NGRAM_ORDERS = (3, 4, 5)
WORD_NGRAM_ALPHA = 0.4
WORD_NGRAM_MISS_LOGP = -20.0
WORD_NGRAM_MIN_POSITIONS = 12
WORD_NGRAM_PREFIX_TOTAL_THRESHOLDS = (1, 10, 100)
WORD_NGRAM_DIRECTION = "ltr"


def _utc_now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _select_word_ngram_books(root: Path, *, limit: int | None) -> list[Path]:
    paths = sorted(root.glob("*_fwd.npz"))
    ranked = sorted(
        paths,
        key=lambda p: (__import__("hashlib").sha1(p.name.encode("utf-8")).hexdigest(), p.name),
    )
    if limit is None or int(limit) <= 0:
        return ranked
    return ranked[: int(limit)]


def _latest_sqlite_asset() -> Path:
    candidates = sorted(SQLITE_ASSET_ROOT.glob(f"*__{SQLITE_ASSET_RUN_LABEL}"))
    if not candidates:
        raise FileNotFoundError(f"No sqlite asset runs found under: {SQLITE_ASSET_ROOT}")
    latest = candidates[-1]
    sqlite_files = sorted(latest.glob("*.sqlite"))
    if not sqlite_files:
        raise FileNotFoundError(f"No sqlite asset found under: {latest}")
    return sqlite_files[0]


def _score_segments(
    scorer: RuneTokenWordNgramScorer,
    token_segments: tuple[tuple[bytes, ...], ...],
) -> dict[str, object]:
    diag = scorer.score_segments_with_diagnostics(token_segments)
    score = diag.score
    conf = summarize_prefix_total_confidence(
        diag.prefix_totals_3,
        thresholds=WORD_NGRAM_PREFIX_TOTAL_THRESHOLDS,
    )
    report_active = word_ngram_report_is_active(
        n_positions=int(score.n_positions),
        min_positions=WORD_NGRAM_MIN_POSITIONS,
    )
    trust = summarize_word_ngram_report_trust(
        n_positions=int(score.n_positions),
        min_positions=WORD_NGRAM_MIN_POSITIONS,
        prefix_total_ge_10_rate=float(conf["prefix_total_ge_10_rate"]),
        prefix_total_ge_100_rate=float(conf["prefix_total_ge_100_rate"]),
    )
    return {
        "word3_xent": (None if int(score.n_positions) <= 0 else float(score.xent_3)),
        "word3_backoff_xent": (None if int(score.n_positions) <= 0 else float(score.xent_backoff_5_4_3)),
        "word3_positions": int(score.n_positions),
        "word3_miss_rate": (None if int(score.n_positions) <= 0 else float(score.miss_rate)),
        "word3_used5_rate": (None if int(score.n_positions) <= 0 else float(score.used5_rate)),
        "word3_used4_rate": (None if int(score.n_positions) <= 0 else float(score.used4_rate)),
        "word3_used3_rate": (None if int(score.n_positions) <= 0 else float(score.used3_rate)),
        "word3_prefix_total_mean": float(conf["prefix_total_mean"]),
        "word3_prefix_total_min": float(conf["prefix_total_min"]),
        "word3_prefix_total_ge_1_rate": float(conf["prefix_total_ge_1_rate"]),
        "word3_prefix_total_ge_10_rate": float(conf["prefix_total_ge_10_rate"]),
        "word3_prefix_total_ge_100_rate": float(conf["prefix_total_ge_100_rate"]),
        "word3_report_active": bool(report_active),
        "word3_report_xent": (
            None if (int(score.n_positions) <= 0 or not report_active) else float(score.xent_3)
        ),
        "word3_report_backoff_xent": (
            None if (int(score.n_positions) <= 0 or not report_active) else float(score.xent_backoff_5_4_3)
        ),
        "word3_report_trust_score": float(trust.trust_score),
        "word3_report_trust_tier": str(trust.trust_tier),
    }


def _metric_row(dataset_version: str, model_kind: str, case_rows: list[dict]) -> dict:
    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in case_rows:
        by_category[str(row["category"])].append(row)

    solved_word3 = [float(r["word3_xent"]) for r in by_category.get("solved_control", []) if r.get("word3_xent") is not None]
    false_word3 = [float(r["word3_xent"]) for r in by_category.get("false_high_basin", []) if r.get("word3_xent") is not None]
    solved_report = [float(r["word3_report_xent"]) for r in by_category.get("solved_control", []) if r.get("word3_report_xent") is not None]
    false_report = [float(r["word3_report_xent"]) for r in by_category.get("false_high_basin", []) if r.get("word3_report_xent") is not None]

    return {
        "dataset_version": dataset_version,
        "model_kind": model_kind,
        "solved_vs_false_high_word3_xent_auc": (
            auc_from_scores([-x for x in solved_word3], [-x for x in false_word3])
            if solved_word3 and false_word3 else float("nan")
        ),
        "solved_vs_false_high_word3_report_xent_auc": (
            auc_from_scores([-x for x in solved_report], [-x for x in false_report])
            if solved_report and false_report else float("nan")
        ),
        "near_miss_word3_report_active_rate": float(
            sum(float(bool(r["word3_report_active"])) for r in by_category.get("near_miss", []))
            / max(1, len(by_category.get("near_miss", [])))
        ),
        "false_high_word3_report_active_rate": float(
            sum(float(bool(r["word3_report_active"])) for r in by_category.get("false_high_basin", []))
            / max(1, len(by_category.get("false_high_basin", [])))
        ),
        "solved_word3_report_active_rate": float(
            sum(float(bool(r["word3_report_active"])) for r in by_category.get("solved_control", []))
            / max(1, len(by_category.get("solved_control", [])))
        ),
        "solved_word3_report_trust_mean": float(
            sum(float(r["word3_report_trust_score"]) for r in by_category.get("solved_control", []))
            / max(1, len(by_category.get("solved_control", [])))
        ),
        "false_high_word3_report_trust_mean": float(
            sum(float(r["word3_report_trust_score"]) for r in by_category.get("false_high_basin", []))
            / max(1, len(by_category.get("false_high_basin", [])))
        ),
    }


def _compare_rows(case_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in case_rows:
        grouped[(str(row["dataset_version"]), str(row["case_id"]))][str(row["model_kind"])] = row
    out: list[dict] = []
    for (dataset_version, case_id), bucket in sorted(grouped.items()):
        mem = bucket.get("in_memory")
        sql = bucket.get("sqlite")
        if mem is None or sql is None:
            continue
        out.append(
            {
                "dataset_version": dataset_version,
                "case_id": case_id,
                "category": mem["category"],
                "word3_positions_in_memory": mem["word3_positions"],
                "word3_positions_sqlite": sql["word3_positions"],
                "word3_positions_delta_sqlite_minus_in_memory": int(sql["word3_positions"]) - int(mem["word3_positions"]),
                "word3_xent_in_memory": mem["word3_xent"],
                "word3_xent_sqlite": sql["word3_xent"],
                "word3_xent_delta_sqlite_minus_in_memory": (
                    None if mem["word3_xent"] is None or sql["word3_xent"] is None
                    else float(sql["word3_xent"]) - float(mem["word3_xent"])
                ),
                "word3_report_active_in_memory": mem["word3_report_active"],
                "word3_report_active_sqlite": sql["word3_report_active"],
                "word3_report_xent_in_memory": mem["word3_report_xent"],
                "word3_report_xent_sqlite": sql["word3_report_xent"],
                "word3_report_xent_delta_sqlite_minus_in_memory": (
                    None if mem["word3_report_xent"] is None or sql["word3_report_xent"] is None
                    else float(sql["word3_report_xent"]) - float(mem["word3_report_xent"])
                ),
                "word3_report_trust_score_in_memory": mem["word3_report_trust_score"],
                "word3_report_trust_score_sqlite": sql["word3_report_trust_score"],
                "word3_report_trust_score_delta_sqlite_minus_in_memory": float(sql["word3_report_trust_score"]) - float(mem["word3_report_trust_score"]),
            }
        )
    return out


def _decision_note(metric_rows: list[dict], compare_rows: list[dict]) -> str:
    def _get(dataset: str, model: str) -> dict | None:
        return next((row for row in metric_rows if row["dataset_version"] == dataset and row["model_kind"] == model), None)

    v1_mem = _get("v1", "in_memory")
    v1_sql = _get("v1", "sqlite")
    v2_mem = _get("v2", "in_memory")
    v2_sql = _get("v2", "sqlite")
    active_flip_count = sum(
        1 for row in compare_rows
        if bool(row["word3_report_active_in_memory"]) != bool(row["word3_report_active_sqlite"])
    )
    lines = [
        "# Phase 2 Decision Note",
        "",
        "Questions:",
        "1. did SQLite reproduce the useful direction?",
        "2. did any important ranking flip?",
        "3. did coverage gating remain safe?",
        "4. did interpretability get worse?",
        "5. is Phase 3 justified or still deferred?",
        "",
        "Answers:",
        f"- v1 solved_vs_false_high report AUC: in_memory={v1_mem['solved_vs_false_high_word3_report_xent_auc'] if v1_mem else 'n/a'} sqlite={v1_sql['solved_vs_false_high_word3_report_xent_auc'] if v1_sql else 'n/a'}",
        f"- v2 solved_vs_false_high report AUC: in_memory={v2_mem['solved_vs_false_high_word3_report_xent_auc'] if v2_mem else 'n/a'} sqlite={v2_sql['solved_vs_false_high_word3_report_xent_auc'] if v2_sql else 'n/a'}",
        f"- report-active flips between backends: {active_flip_count}",
        "- Phase 3 stays deferred unless SQLite preserves the useful direction cleanly and the broader frozen corpus still argues for more support rather than a different signal family.",
        "",
        "Interpretation:",
        "- SQLite should be considered credible only if it preserves the same solved-vs-false-high direction without making coverage gating noisier.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    run_dir = OUTPUT_ROOT / f"{_utc_now_label()}__{RUN_LABEL}"
    run_dir.mkdir(parents=True, exist_ok=True)

    sqlite_fp = _latest_sqlite_asset()
    print(f"[report_nowli_hard_cases_word_ngram_sqlite_compare_v1] sqlite_asset={sqlite_fp}", flush=True)

    books = _select_word_ngram_books(TOKENIZED_DIR, limit=WORD_NGRAM_BOOK_LIMIT)
    memory_model = RuneTokenWordNgramMemoryModel.from_tokenized_npz_paths(
        books,
        pt_key="pt_nose_data",
        wli_key="wli_nose_data",
        orders=WORD_NGRAM_ORDERS,
    )
    memory_scorer = RuneTokenWordNgramScorer(
        memory_model,
        alpha=WORD_NGRAM_ALPHA,
        miss_logp=WORD_NGRAM_MISS_LOGP,
    )

    backend = SpanHammingBackend(config=SpanHammingConfig(debug_return_intervals=True))
    word_sets = word_token_sets_by_len(getattr(backend, "_words_by_len", {}))

    case_rows: list[dict] = []
    metric_rows: list[dict] = []

    with RuneTokenWordNgramSqlite.open(sqlite_fp) as sqlite_model:
        sqlite_book_names = json.loads(sqlite_model.meta("book_names_json", "[]") or "[]")
        if sqlite_book_names != [p.name for p in books]:
            raise ValueError("SQLite asset book set does not match current in-memory baseline selection")
        sqlite_scorer = RuneTokenWordNgramScorer(
            sqlite_model,
            alpha=WORD_NGRAM_ALPHA,
            miss_logp=WORD_NGRAM_MISS_LOGP,
        )

        for dataset_fp in DATASETS:
            dataset = load_nowli_hard_cases(dataset_fp)
            dataset_version = str(dataset.version)
            case_cache: dict[str, dict[str, object]] = {}
            for case in dataset.cases:
                stats = backend.score(case.candidate_plaintext_idx)
                exact = exact_match_feasibility_metrics(
                    case.candidate_plaintext_idx,
                    stats.selected_intervals,
                    word_sets_by_len=word_sets,
                )
                exact_tokens = extract_exact_match_tokens(case.candidate_plaintext_idx, stats.selected_intervals)
                exact_segments = segment_exact_match_tokens(exact_tokens)
                token_segments = tuple(tuple(tok.token for tok in seg) for seg in exact_segments)
                case_cache[case.case_id] = {
                    "category": case.category,
                    "status": case.status,
                    "best_match_ratio": case.best_match_ratio,
                    "exact_word_count": int(exact["exact_word_count"]),
                    "total_trigram_positions": int(exact["total_trigram_positions"]),
                    "token_segments": token_segments,
                }

            for model_kind, scorer in (("in_memory", memory_scorer), ("sqlite", sqlite_scorer)):
                model_case_rows: list[dict] = []
                for case in dataset.cases:
                    cached = case_cache[case.case_id]
                    scored = _score_segments(scorer, cached["token_segments"])  # type: ignore[arg-type]
                    row = {
                        "dataset_version": dataset_version,
                        "model_kind": model_kind,
                        "case_id": case.case_id,
                        "category": cached["category"],
                        "status": cached["status"],
                        "best_match_ratio": cached["best_match_ratio"],
                        "exact_word_count": cached["exact_word_count"],
                        "total_trigram_positions": cached["total_trigram_positions"],
                    }
                    row.update(scored)
                    case_rows.append(row)
                    model_case_rows.append(row)
                metric_rows.append(_metric_row(dataset_version, model_kind, model_case_rows))

    compare_rows = _compare_rows(case_rows)
    _write_csv(run_dir / "cases.csv", case_rows)
    _write_csv(run_dir / "metrics.csv", metric_rows)
    _write_csv(run_dir / "case_deltas.csv", compare_rows)
    (run_dir / "metrics.json").write_text(json.dumps(metric_rows, indent=2), encoding="utf-8")
    (run_dir / "decision_note.md").write_text(_decision_note(metric_rows, compare_rows), encoding="utf-8")
    (run_dir / "run_config.json").write_text(
        json.dumps(
            {
                "datasets": [str(p) for p in DATASETS],
                "tokenized_dir": str(TOKENIZED_DIR),
                "book_limit": int(WORD_NGRAM_BOOK_LIMIT),
                "orders": [int(v) for v in WORD_NGRAM_ORDERS],
                "alpha": float(WORD_NGRAM_ALPHA),
                "miss_logp": float(WORD_NGRAM_MISS_LOGP),
                "min_positions": int(WORD_NGRAM_MIN_POSITIONS),
                "sqlite_asset": str(sqlite_fp),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[report_nowli_hard_cases_word_ngram_sqlite_compare_v1] wrote cases: {run_dir / 'cases.csv'}", flush=True)
    print(f"[report_nowli_hard_cases_word_ngram_sqlite_compare_v1] wrote metrics: {run_dir / 'metrics.csv'}", flush=True)
    print(f"[report_nowli_hard_cases_word_ngram_sqlite_compare_v1] wrote case deltas: {run_dir / 'case_deltas.csv'}", flush=True)


if __name__ == "__main__":
    main()
