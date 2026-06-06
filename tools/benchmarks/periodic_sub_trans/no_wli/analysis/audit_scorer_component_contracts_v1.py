from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


RUN_LABEL = "scorer_component_contract_audit_v1"
BENCHMARK_MIN_TOKEN_LENGTH = 500
S1_PAIR_ROWS_REL = (
    "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/source/historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
S1B_CANDIDATE_FEATURES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_component_feature_audit_v1/scorer_component_feature_audit_candidate_features.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_component_contract_audit_v1"
)
WORD_NGRAM_SQLITE_REL = (
    "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/"
    "20260308T024914Z__build_word_ngram_sqlite_asset_phase2_v1/"
    "word_ngrams_tokenized64_phase2_v1.sqlite"
)
WORD_NGRAM_RUN_CONFIG_REL = (
    "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/"
    "20260308T024914Z__build_word_ngram_sqlite_asset_phase2_v1/"
    "run_config.json"
)
HAMMING_WORDLIST_DIR_REL = "assets/hamming_raw_1g"
WORD_NGRAM_ALPHA = 0.4
WORD_NGRAM_MISS_LOGP = -20.0
WORD_NGRAM_MIN_POSITIONS = 12
WORD_NGRAM_PREFIX_THRESHOLDS = (1, 10, 100)
WORD_NGRAM_DIRECTION_POLICY = "artifact_direction_required_ltr_for_s1d"
SPAN_DIRECTION_POLICY = "direction_insensitive_numeric_span_scan"
FEATURE_CACHE_KEY_POLICY = "token_hash_only_validated_against_artifact_context"


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

from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig  # noqa: E402


S1_PAIR_ROWS = REPO_ROOT / S1_PAIR_ROWS_REL
S1B_CANDIDATE_FEATURES = REPO_ROOT / S1B_CANDIDATE_FEATURES_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL
WORD_NGRAM_SQLITE = REPO_ROOT / WORD_NGRAM_SQLITE_REL
WORD_NGRAM_RUN_CONFIG = REPO_ROOT / WORD_NGRAM_RUN_CONFIG_REL
HAMMING_WORDLIST_DIR = REPO_ROOT / HAMMING_WORDLIST_DIR_REL


PAIR_CONTEXT_FIELDS = (
    "pair_id",
    "artifact_path",
    "fixture_id",
    "fixture_seed",
    "search_seed",
    "token_length",
    "direction",
    "period",
    "columns",
    "alphabet_size",
    "order",
    "winner_token_hash",
    "challenger_token_hash",
    "current_score_correct",
    "below_min_token_length",
)

ACTIVE_STATE_FIELDS = (
    "pair_id",
    "winner_token_hash",
    "challenger_token_hash",
    "winner_word_ngram_active",
    "challenger_word_ngram_active",
    "winner_word_ngram_available",
    "challenger_word_ngram_available",
    "word_active_pair_state",
    "pair_group",
    "word_trust_prefers_truth_better_active_pair",
    "word_xent_prefers_truth_better_both_active",
    "word_backoff_xent_prefers_truth_better_both_active",
    "word_miss_rate_prefers_truth_better_both_active",
)

CACHE_CONTEXT_FIELDS = (
    "token_hash",
    "context_count",
    "contexts",
    "cache_safe_for_token_hash_only",
)


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out


def _artifact_context(artifact_path_text: str) -> dict[str, Any]:
    artifact_path = REPO_ROOT / str(artifact_path_text)
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception:
        artifact = {}
    return {
        "direction": str(artifact.get("direction", "") or ""),
        "period": str(artifact.get("period", "") or ""),
        "columns": str(artifact.get("columns", "") or ""),
        "alphabet_size": str(artifact.get("alphabet_size", "") or ""),
        "order": str(artifact.get("order", "") or ""),
    }


def build_pair_context_rows(pair_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    context_cache: dict[str, dict[str, Any]] = {}
    out: list[dict[str, Any]] = []
    for row in pair_rows:
        artifact_path = str(row.get("artifact_path", "") or "")
        context = context_cache.get(artifact_path)
        if context is None:
            context = _artifact_context(artifact_path)
            context_cache[artifact_path] = context
        token_length = _safe_int(row.get("token_length"))
        out.append(
            {
                "pair_id": row.get("pair_id", ""),
                "artifact_path": artifact_path,
                "fixture_id": row.get("fixture_id", ""),
                "fixture_seed": row.get("fixture_seed", ""),
                "search_seed": row.get("search_seed", ""),
                "token_length": token_length,
                "direction": context.get("direction", ""),
                "period": context.get("period", ""),
                "columns": context.get("columns", ""),
                "alphabet_size": context.get("alphabet_size", ""),
                "order": context.get("order", ""),
                "winner_token_hash": row.get("winner_token_hash", ""),
                "challenger_token_hash": row.get("challenger_token_hash", ""),
                "current_score_correct": row.get("current_score_correct", ""),
                "below_min_token_length": int(token_length < BENCHMARK_MIN_TOKEN_LENGTH),
            }
        )
    return out


def _candidate_by_hash(candidate_rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(row.get("token_hash", "") or ""): row for row in candidate_rows}


def _word_active_state(winner_active: int, challenger_active: int) -> str:
    if winner_active and challenger_active:
        return "both_active"
    if winner_active and not challenger_active:
        return "winner_only_active"
    if challenger_active and not winner_active:
        return "challenger_only_active"
    return "neither_active"


def _lower_prefers_winner(winner_value: Any, challenger_value: Any) -> int | str:
    winner = _safe_float(winner_value)
    challenger = _safe_float(challenger_value)
    if winner is None or challenger is None or winner == challenger:
        return ""
    return int(winner < challenger)


def _higher_prefers_winner(winner_value: Any, challenger_value: Any) -> int | str:
    winner = _safe_float(winner_value)
    challenger = _safe_float(challenger_value)
    if winner is None or challenger is None or winner == challenger:
        return ""
    return int(winner > challenger)


def build_active_state_rows(
    *,
    pair_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates = _candidate_by_hash(candidate_rows)
    out: list[dict[str, Any]] = []
    for row in pair_rows:
        winner = dict(candidates.get(str(row.get("winner_token_hash", "") or ""), {}))
        challenger = dict(candidates.get(str(row.get("challenger_token_hash", "") or ""), {}))
        winner_active = _safe_int(winner.get("word_ngram_active"))
        challenger_active = _safe_int(challenger.get("word_ngram_active"))
        state = _word_active_state(winner_active, challenger_active)
        pair_group = (
            "current_score_correct"
            if _safe_int(row.get("current_score_correct")) == 1
            else "current_score_misranked"
        )
        trust_pref = ""
        xent_pref = ""
        backoff_pref = ""
        miss_pref = ""
        if winner_active or challenger_active:
            trust_pref = _higher_prefers_winner(
                winner.get("word_ngram_trust_score"),
                challenger.get("word_ngram_trust_score"),
            )
        if winner_active and challenger_active:
            xent_pref = _lower_prefers_winner(winner.get("word_ngram_xent"), challenger.get("word_ngram_xent"))
            backoff_pref = _lower_prefers_winner(
                winner.get("word_ngram_backoff_xent"),
                challenger.get("word_ngram_backoff_xent"),
            )
            miss_pref = _lower_prefers_winner(
                winner.get("word_ngram_miss_rate"),
                challenger.get("word_ngram_miss_rate"),
            )
        out.append(
            {
                "pair_id": row.get("pair_id", ""),
                "winner_token_hash": row.get("winner_token_hash", ""),
                "challenger_token_hash": row.get("challenger_token_hash", ""),
                "winner_word_ngram_active": winner_active,
                "challenger_word_ngram_active": challenger_active,
                "winner_word_ngram_available": _safe_int(winner.get("word_ngram_available")),
                "challenger_word_ngram_available": _safe_int(challenger.get("word_ngram_available")),
                "word_active_pair_state": state,
                "pair_group": pair_group,
                "word_trust_prefers_truth_better_active_pair": trust_pref,
                "word_xent_prefers_truth_better_both_active": xent_pref,
                "word_backoff_xent_prefers_truth_better_both_active": backoff_pref,
                "word_miss_rate_prefers_truth_better_both_active": miss_pref,
            }
        )
    return out


def build_cache_context_rows(pair_context_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    contexts_by_token: dict[str, set[str]] = defaultdict(set)
    for row in pair_context_rows:
        context = "|".join(
            str(row.get(key, "") or "")
            for key in ("direction", "period", "columns", "alphabet_size", "order")
        )
        for side in ("winner_token_hash", "challenger_token_hash"):
            token_hash = str(row.get(side, "") or "")
            if token_hash:
                contexts_by_token[token_hash].add(context)
    out = []
    for token_hash, contexts in sorted(contexts_by_token.items()):
        out.append(
            {
                "token_hash": token_hash,
                "context_count": len(contexts),
                "contexts": ";".join(sorted(contexts)),
                "cache_safe_for_token_hash_only": int(len(contexts) == 1),
            }
        )
    return out


def _count_values(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key, "") or "") for row in rows).items()))


def _asset_snapshot() -> dict[str, Any]:
    word_run_config = {}
    if WORD_NGRAM_RUN_CONFIG.exists():
        try:
            raw_config = json.loads(WORD_NGRAM_RUN_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            raw_config = {}
        word_run_config = {
            "book_limit": raw_config.get("book_limit", ""),
            "orders": raw_config.get("orders", []),
            "book_count": len(raw_config.get("book_names", []) or []),
            "sqlite_path_recorded_as": (
                "absolute_path_redacted"
                if Path(str(raw_config.get("sqlite_path", ""))).is_absolute()
                else str(raw_config.get("sqlite_path", "") or "")
            ),
            "tokenized_dir_recorded_as": (
                "absolute_path_redacted"
                if Path(str(raw_config.get("tokenized_dir", ""))).is_absolute()
                else str(raw_config.get("tokenized_dir", "") or "")
            ),
        }
    hamming_files = sorted(HAMMING_WORDLIST_DIR.glob("raw1grams_*.csv")) if HAMMING_WORDLIST_DIR.exists() else []
    return {
        "span_hamming_wordlist_dir": _repo_rel(HAMMING_WORDLIST_DIR),
        "span_hamming_wordlist_file_count": len(hamming_files),
        "span_hamming_wordlist_total_bytes": sum(int(fp.stat().st_size) for fp in hamming_files),
        "word_ngram_sqlite_path": _repo_rel(WORD_NGRAM_SQLITE),
        "word_ngram_sqlite_exists": WORD_NGRAM_SQLITE.exists(),
        "word_ngram_sqlite_bytes": int(WORD_NGRAM_SQLITE.stat().st_size) if WORD_NGRAM_SQLITE.exists() else 0,
        "word_ngram_run_config_path": _repo_rel(WORD_NGRAM_RUN_CONFIG),
        "word_ngram_run_config_exists": WORD_NGRAM_RUN_CONFIG.exists(),
        "word_ngram_run_config": word_run_config,
    }


def _active_state_summary(active_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "word_active_pair_state_counts": _count_values(active_rows, "word_active_pair_state"),
    }
    for state in ("both_active", "winner_only_active", "challenger_only_active", "neither_active"):
        rows = [row for row in active_rows if str(row.get("word_active_pair_state", "")) == state]
        out[f"{state}_current_misranked_count"] = sum(
            1 for row in rows if str(row.get("pair_group", "")) == "current_score_misranked"
        )
        out[f"{state}_current_correct_control_count"] = sum(
            1 for row in rows if str(row.get("pair_group", "")) == "current_score_correct"
        )
    out["word_trust_active_pair_rescue_count"] = sum(
        1
        for row in active_rows
        if str(row.get("pair_group", "")) == "current_score_misranked"
        and row.get("word_trust_prefers_truth_better_active_pair") == 1
    )
    out["word_trust_active_pair_break_count"] = sum(
        1
        for row in active_rows
        if str(row.get("pair_group", "")) == "current_score_correct"
        and row.get("word_trust_prefers_truth_better_active_pair") == 0
    )
    out["word_xent_both_active_rescue_count"] = sum(
        1
        for row in active_rows
        if str(row.get("pair_group", "")) == "current_score_misranked"
        and row.get("word_xent_prefers_truth_better_both_active") == 1
    )
    out["word_xent_both_active_break_count"] = sum(
        1
        for row in active_rows
        if str(row.get("pair_group", "")) == "current_score_correct"
        and row.get("word_xent_prefers_truth_better_both_active") == 0
    )
    return out


def build_summary(
    *,
    pair_context_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    active_rows: Sequence[Mapping[str, Any]],
    cache_context_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    length_values = [_safe_int(row.get("token_length")) for row in pair_context_rows]
    below_min_pairs = [row for row in pair_context_rows if _safe_int(row.get("below_min_token_length")) == 1]
    below_min_candidates = [
        row for row in candidate_rows if _safe_int(row.get("token_length")) < BENCHMARK_MIN_TOKEN_LENGTH
    ]
    cache_unsafe = [row for row in cache_context_rows if _safe_int(row.get("cache_safe_for_token_hash_only")) == 0]
    direction_counts = _count_values(pair_context_rows, "direction")
    all_ltr = set(direction_counts) == {"ltr"}
    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "runtime_behavior_changed": False,
        "truth_is_evaluation_only": True,
        "input_pair_rows": S1_PAIR_ROWS_REL,
        "input_candidate_features": S1B_CANDIDATE_FEATURES_REL,
        "output_dir": OUTPUT_DIR_REL,
        "benchmark_min_token_length": BENCHMARK_MIN_TOKEN_LENGTH,
        "pair_count": len(pair_context_rows),
        "candidate_count": len(candidate_rows),
        "token_length_min": min(length_values) if length_values else 0,
        "token_length_max": max(length_values) if length_values else 0,
        "token_length_counts": dict(sorted(Counter(length_values).items())),
        "below_min_token_length_pair_count": len(below_min_pairs),
        "below_min_token_length_candidate_count": len(below_min_candidates),
        "direction_counts": direction_counts,
        "period_counts": _count_values(pair_context_rows, "period"),
        "columns_counts": _count_values(pair_context_rows, "columns"),
        "alphabet_size_counts": _count_values(pair_context_rows, "alphabet_size"),
        "order_counts": _count_values(pair_context_rows, "order"),
        "all_pairs_ltr": all_ltr,
        "hard_coded_ltr_word_call_safe_for_s1": all_ltr,
        "feature_cache_key_policy": FEATURE_CACHE_KEY_POLICY,
        "token_hash_only_cache_unsafe_token_count": len(cache_unsafe),
        "token_hash_only_cache_safe_for_s1": len(cache_unsafe) == 0,
        "span_hamming_direction_policy": SPAN_DIRECTION_POLICY,
        "span_hamming_config": asdict(SpanHammingConfig(debug_return_intervals=True)),
        "span_hamming_score_direction": "higher_is_better_for_span_raw_coverage_quality",
        "word_ngram_config": {
            "sqlite_path": _repo_rel(WORD_NGRAM_SQLITE),
            "alpha": WORD_NGRAM_ALPHA,
            "miss_logp": WORD_NGRAM_MISS_LOGP,
            "min_positions": WORD_NGRAM_MIN_POSITIONS,
            "prefix_total_thresholds": list(WORD_NGRAM_PREFIX_THRESHOLDS),
            "direction_policy": WORD_NGRAM_DIRECTION_POLICY,
            "inactive_policy_for_stage2": "inactive_must_be_no_decision_for_xent_backoff_miss_features",
            "trust_score_policy": "trust_score_may_be_positive_confidence_only; inactive is zero confidence",
        },
        "asset_snapshot": _asset_snapshot(),
        **_active_state_summary(active_rows),
        "stage2_go": False,
        "stage2_hold_reason": (
            "S1d is a contract audit only. Stage 2 may start after review confirms the "
            "explicit active/inactive and direction/cache policies."
        ),
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_readout(summary: Mapping[str, Any]) -> str:
    state_counts = dict(summary.get("word_active_pair_state_counts", {}))
    lines = [
        "# Scorer Component Contract Audit v1",
        "",
        "## Purpose",
        "",
        "Verify scorer/report component contracts before Stage 2 gate simulation.",
        "This is report-only and does not change runtime behavior.",
        "",
        "## Length Policy",
        "",
        f"- benchmark minimum token length: `{summary['benchmark_min_token_length']}`",
        f"- token length min/max: `{summary['token_length_min']}` / `{summary['token_length_max']}`",
        f"- below-min pair count: `{summary['below_min_token_length_pair_count']}`",
        f"- below-min candidate count: `{summary['below_min_token_length_candidate_count']}`",
        "",
        "## Artifact Context",
        "",
        f"- direction counts: `{json.dumps(summary['direction_counts'], sort_keys=True)}`",
        f"- period counts: `{json.dumps(summary['period_counts'], sort_keys=True)}`",
        f"- columns counts: `{json.dumps(summary['columns_counts'], sort_keys=True)}`",
        f"- order counts: `{json.dumps(summary['order_counts'], sort_keys=True)}`",
        f"- hard-coded LTR word call safe for S1: `{summary['hard_coded_ltr_word_call_safe_for_s1']}`",
        "",
        "## Cache Key Policy",
        "",
        f"- token-hash-only cache unsafe token count: `{summary['token_hash_only_cache_unsafe_token_count']}`",
        f"- token-hash-only cache safe for S1: `{summary['token_hash_only_cache_safe_for_s1']}`",
        "",
        "## Span-Hamming Contract",
        "",
        f"- config: `{json.dumps(summary['span_hamming_config'], sort_keys=True)}`",
        f"- score direction: `{summary['span_hamming_score_direction']}`",
        "",
        "## Word-Ngram Contract",
        "",
        f"- config: `{json.dumps(summary['word_ngram_config'], sort_keys=True)}`",
        f"- active pair states: `{json.dumps(state_counts, sort_keys=True)}`",
        f"- word trust active-pair rescues: `{summary['word_trust_active_pair_rescue_count']}`",
        f"- word trust active-pair breaks: `{summary['word_trust_active_pair_break_count']}`",
        f"- word xent both-active rescues: `{summary['word_xent_both_active_rescue_count']}`",
        f"- word xent both-active breaks: `{summary['word_xent_both_active_break_count']}`",
        "",
        "## Stage 2 Status",
        "",
        f"- stage2_go: `{summary['stage2_go']}`",
        f"- hold reason: {summary['stage2_hold_reason']}",
    ]
    return "\n".join(lines) + "\n"


def write_outputs() -> dict[str, Any]:
    print(f"[{RUN_LABEL}] loading S1/S1b inputs")
    pair_rows = _load_csv(S1_PAIR_ROWS)
    candidate_rows = _load_csv(S1B_CANDIDATE_FEATURES)
    pair_context_rows = build_pair_context_rows(pair_rows)
    active_rows = build_active_state_rows(pair_rows=pair_rows, candidate_rows=candidate_rows)
    cache_context_rows = build_cache_context_rows(pair_context_rows)
    summary = build_summary(
        pair_context_rows=pair_context_rows,
        candidate_rows=candidate_rows,
        active_rows=active_rows,
        cache_context_rows=cache_context_rows,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(OUTPUT_DIR / "scorer_component_contract_audit_pair_context.csv", pair_context_rows, PAIR_CONTEXT_FIELDS)
    _write_csv(OUTPUT_DIR / "scorer_component_contract_audit_active_state.csv", active_rows, ACTIVE_STATE_FIELDS)
    _write_csv(OUTPUT_DIR / "scorer_component_contract_audit_cache_context.csv", cache_context_rows, CACHE_CONTEXT_FIELDS)
    _write_json(OUTPUT_DIR / "scorer_component_contract_audit_config_snapshot.json", {
        "span_hamming_config": summary["span_hamming_config"],
        "word_ngram_config": summary["word_ngram_config"],
        "asset_snapshot": summary["asset_snapshot"],
    })
    _write_json(OUTPUT_DIR / "scorer_component_contract_audit_summary.json", summary)
    (OUTPUT_DIR / "scorer_component_contract_audit_readout.md").write_text(build_readout(summary), encoding="utf-8")
    print(
        f"[{RUN_LABEL}] done pairs={summary['pair_count']} candidates={summary['candidate_count']} "
        f"stage2_go={summary['stage2_go']} output_dir={summary['output_dir']}"
    )
    return summary


def main() -> None:
    write_outputs()


if __name__ == "__main__":
    main()
