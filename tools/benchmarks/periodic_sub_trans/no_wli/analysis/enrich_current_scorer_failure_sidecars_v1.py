from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


RUN_LABEL = "current_scorer_failure_sidecars_v1"
RUN_ROOT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "current_scorer_failure_sidecars_v1"
)
REPEATED_NGRAM_N = 4


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

from rune_decrypter_prime.api import Direction  # noqa: E402
from rune_decrypter_prime.core.config.cipher import CipherConfig  # noqa: E402
from rune_decrypter_prime.core.config.scoring import ScoringConfig  # noqa: E402
from rune_decrypter_prime.core.engine.builders import build_scorer  # noqa: E402
from rune_decrypter_prime.core.types import Device  # noqa: E402
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_frontier_rows import (  # noqa: E402
    load_phasec_frontier_rows,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_truth_gap_dataset import (  # noqa: E402
    collect_phasec_truth_gap_rows,
)


RUN_ROOT = REPO_ROOT / RUN_ROOT_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


ROW_FIELDS = (
    "fixture_seed",
    "search_seed",
    "run_id",
    "bundle_path",
    "artifact_path",
    "winner_candidate_hash",
    "challenger_candidate_hash",
    "winner_truth_match",
    "challenger_truth_match",
    "truth_gap_challenger_minus_winner",
    "winner_current_score",
    "challenger_current_score",
    "score_gap_challenger_minus_winner",
    "winner_source",
    "winner_source_rank",
    "challenger_source",
    "challenger_source_rank",
    "winner_material_available",
    "challenger_material_available",
    "pair_material_available",
    "scorer_sidecar_available",
    "scorer_sidecar_missing_reason",
    "component_that_prefers_truth_better",
    "failure_subtype_after_sidecars",
    "winner_text_length",
    "challenger_text_length",
    "winner_char_lm_score",
    "challenger_char_lm_score",
    "winner_window_mean",
    "challenger_window_mean",
    "winner_window_worst",
    "challenger_window_worst",
    "winner_window_lower_quartile",
    "challenger_window_lower_quartile",
    "winner_window_variance",
    "challenger_window_variance",
    "winner_span_hamming_score",
    "challenger_span_hamming_score",
    "winner_word_ngram_judge_score",
    "challenger_word_ngram_judge_score",
    "winner_repeated_ngram_rate",
    "challenger_repeated_ngram_rate",
    "winner_unique_token_rate",
    "challenger_unique_token_rate",
    "winner_entropy_norm",
    "challenger_entropy_norm",
    "winner_low_diversity_penalty",
    "challenger_low_diversity_penalty",
    "winner_low_diversity_penalty_preferred",
    "challenger_low_diversity_penalty_preferred",
    "repeated_ngram_rate_prefers_truth_better",
    "low_diversity_penalty_prefers_truth_better",
)


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _display_path_text(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    if not text:
        return ""
    path = Path(text)
    if path.is_absolute():
        return _repo_rel(path)
    return text


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _finite_or_blank(value: Any) -> float | str:
    out = _safe_float(value)
    return float(out) if math.isfinite(out) else ""


def _resolve_repo_path(path_like: Any) -> str | None:
    if path_like is None:
        return None
    text = str(path_like)
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return str(path)


def token_diversity_metrics(tokens: Sequence[int], *, ngram_n: int = REPEATED_NGRAM_N) -> dict[str, Any]:
    vals = [int(v) for v in tokens]
    length = len(vals)
    if length <= 0:
        return {
            "text_length": 0,
            "repeated_ngram_rate": "",
            "unique_token_rate": "",
            "entropy_norm": "",
            "low_diversity_penalty": "",
        }
    counts = Counter(vals)
    probs = [float(count) / float(length) for count in counts.values()]
    entropy = -sum(p * math.log(p) for p in probs if p > 0.0)
    entropy_norm = entropy / math.log(max(2, len(counts)))
    unique_rate = float(len(counts) / length)
    n = int(max(1, int(ngram_n)))
    if length < n:
        repeated_rate: float | str = ""
    else:
        grams = [tuple(vals[idx : idx + n]) for idx in range(0, length - n + 1)]
        gram_counts = Counter(grams)
        repeated_positions = sum(count for count in gram_counts.values() if count > 1)
        repeated_rate = float(repeated_positions / max(1, len(grams)))
    low_diversity_penalty = float(1.0 - entropy_norm)
    return {
        "text_length": int(length),
        "repeated_ngram_rate": repeated_rate,
        "unique_token_rate": float(unique_rate),
        "entropy_norm": float(entropy_norm),
        "low_diversity_penalty": float(low_diversity_penalty),
    }


def _build_scorer_runtime(*, artifact: Mapping[str, Any], run_config: Mapping[str, Any]) -> Any:
    stage3_cfg = dict((run_config.get("stage3") or {}) if isinstance(run_config, Mapping) else {})
    scorer_cfg = dict((stage3_cfg.get("scorer") or {}) if isinstance(stage3_cfg, Mapping) else {})
    for path_key in (
        "model_root",
        "span_hamming_assets_dir",
        "span_hamming_wordlist_dir",
        "span_hamming_lm_assets_json",
        "word_ngram_judge_sqlite_path",
        "word_ngram_report_sqlite_path",
    ):
        if path_key in scorer_cfg:
            resolved = _resolve_repo_path(scorer_cfg.get(path_key))
            if resolved is not None:
                scorer_cfg[path_key] = resolved
    direction = Direction(str(artifact.get("direction", "ltr")))
    cfg_full = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        alphabet_size=int(artifact["alphabet_size"]),
        key_length=int(artifact["period"]) * int(artifact["alphabet_size"]) + int(artifact["columns"]),
        order=str(artifact["order"]),
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    return build_scorer(cfg_full, ScoringConfig(**scorer_cfg))


def _score_sidecar(*, scorer: Any, plaintext_idx: Sequence[int]) -> dict[str, Any]:
    pt = np.asarray([int(v) for v in plaintext_idx], dtype=np.uint8).reshape(-1)
    score = float(scorer.score(pt, None))
    stats = {}
    try:
        if hasattr(scorer, "last_stats") and callable(scorer.last_stats):
            stats = dict(scorer.last_stats())
    except Exception:
        stats = {}
    windows = dict(stats.get("windows", {}) or {}) if isinstance(stats.get("windows"), Mapping) else {}
    score_std = _safe_float(stats.get("score_std"))
    span_score = stats.get("span_hamming_combined_energy", stats.get("span_hamming_bonus", ""))
    word_score = stats.get("word_ngram_judge_report_xent", stats.get("word_ngram_judge_trust_score", ""))
    return {
        "char_lm_score": float(score),
        "window_mean": _finite_or_blank(stats.get("score_mean", score)),
        "window_worst": "",
        "window_lower_quartile": _finite_or_blank(windows.get("p10")),
        "window_variance": (float(score_std * score_std) if math.isfinite(score_std) else ""),
        "span_hamming_score": _finite_or_blank(span_score),
        "word_ngram_judge_score": _finite_or_blank(word_score),
    }


def _candidate_by_hash(rows: Sequence[Mapping[str, Any]], candidate_hash: str) -> dict[str, Any]:
    for row in rows:
        if str(row.get("candidate_hash", "") or "") == str(candidate_hash):
            return dict(row)
    return {}


def _load_artifact_case(source_row: Mapping[str, Any]) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    artifact_path = Path(str(source_row.get("artifact_path", "") or ""))
    if not artifact_path.is_absolute():
        artifact_path = (REPO_ROOT / artifact_path).resolve()
    run_dir = artifact_path.parents[1]
    run_config_path = run_dir / "run_config.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
    return artifact_path, run_config_path, dict(artifact), dict(run_config)


def _prefer_lower(value_a: Any, value_b: Any) -> str:
    a = _safe_float(value_a)
    b = _safe_float(value_b)
    if not math.isfinite(a) or not math.isfinite(b):
        return ""
    if a < b:
        return "winner"
    if b < a:
        return "challenger"
    return "tie"


def _prefer_higher(value_a: Any, value_b: Any) -> str:
    a = _safe_float(value_a)
    b = _safe_float(value_b)
    if not math.isfinite(a) or not math.isfinite(b):
        return ""
    if a > b:
        return "winner"
    if b > a:
        return "challenger"
    return "tie"


def _truth_better_side(row: Mapping[str, Any]) -> str:
    winner_truth = _safe_float(row.get("winner_truth_match"))
    challenger_truth = _safe_float(row.get("challenger_truth_match"))
    if not math.isfinite(winner_truth) or not math.isfinite(challenger_truth):
        return ""
    if winner_truth > challenger_truth:
        return "winner"
    if challenger_truth > winner_truth:
        return "challenger"
    return "tie"


def _classify_sidecar(row: Mapping[str, Any]) -> tuple[str, str]:
    truth_better = _truth_better_side(row)
    if not truth_better or truth_better == "tie":
        return "unknown_after_sidecars", ""
    preferences: list[str] = []
    char_pref = _prefer_higher(row.get("winner_char_lm_score"), row.get("challenger_char_lm_score"))
    if char_pref == truth_better:
        preferences.append("char_lm")
    span_pref = _prefer_higher(row.get("winner_span_hamming_score"), row.get("challenger_span_hamming_score"))
    if span_pref == truth_better:
        preferences.append("span_hamming")
    word_pref = _prefer_lower(row.get("winner_word_ngram_judge_score"), row.get("challenger_word_ngram_judge_score"))
    if word_pref == truth_better:
        preferences.append("word_ngram_judge")
    low_diversity_pref = _prefer_lower(
        row.get("winner_low_diversity_penalty"),
        row.get("challenger_low_diversity_penalty"),
    )
    repeated_ngram_pref = _prefer_lower(
        row.get("winner_repeated_ngram_rate"),
        row.get("challenger_repeated_ngram_rate"),
    )
    if repeated_ngram_pref == truth_better:
        preferences.append("repeated_ngram_rate")
    if low_diversity_pref == truth_better:
        preferences.append("low_diversity_penalty")
    if preferences:
        if char_pref and char_pref not in ("", "tie", truth_better):
            subtype = "local_ngram_overfit"
        elif "char_lm" in preferences:
            subtype = "component_weighting_failure"
        elif "span_hamming" in preferences or "word_ngram_judge" in preferences:
            subtype = "missing_span_or_word_signal"
        else:
            subtype = "motif_false_positive"
        return subtype, ";".join(preferences)
    return "unknown_after_sidecars", ""


def build_sidecar_row(source_row: Mapping[str, Any]) -> dict[str, Any]:
    artifact_path, _run_config_path, artifact, run_config = _load_artifact_case(source_row)
    frontier_rows = load_phasec_frontier_rows(artifact_path=artifact_path, artifact=artifact)
    winner_hash = str(source_row.get("winner_candidate_hash", "") or "")
    challenger_hash = str(source_row.get("challenger_candidate_hash", "") or "")
    winner = _candidate_by_hash(frontier_rows, winner_hash)
    challenger = _candidate_by_hash(frontier_rows, challenger_hash)
    winner_pt = [int(v) for v in list(winner.get("final_plaintext_idx", []) or [])]
    challenger_pt = [int(v) for v in list(challenger.get("final_plaintext_idx", []) or [])]
    winner_div = token_diversity_metrics(winner_pt)
    challenger_div = token_diversity_metrics(challenger_pt)
    row: dict[str, Any] = {
        "fixture_seed": _safe_int(source_row.get("key_seed", source_row.get("fixture_seed"))),
        "search_seed": _safe_int(source_row.get("search_seed"), 0),
        "run_id": str(winner.get("run_id", challenger.get("run_id", "")) or ""),
        "bundle_path": _display_path_text(source_row.get("run_dir", "")),
        "artifact_path": _display_path_text(source_row.get("artifact_path", "")),
        "winner_candidate_hash": winner_hash,
        "challenger_candidate_hash": challenger_hash,
        "winner_truth_match": _finite_or_blank(source_row.get("winner_truth_match")),
        "challenger_truth_match": _finite_or_blank(source_row.get("challenger_truth_match")),
        "truth_gap_challenger_minus_winner": _finite_or_blank(source_row.get("truth_gap_vs_winner")),
        "winner_current_score": _finite_or_blank(source_row.get("winner_score")),
        "challenger_current_score": _finite_or_blank(source_row.get("challenger_score")),
        "score_gap_challenger_minus_winner": _finite_or_blank(source_row.get("score_gap_vs_winner")),
        "winner_source": str(source_row.get("winner_source", winner.get("source", "")) or ""),
        "winner_source_rank": winner.get("source_rank", ""),
        "challenger_source": str(source_row.get("challenger_source", challenger.get("source", "")) or ""),
        "challenger_source_rank": challenger.get("source_rank", ""),
        "winner_material_available": int(bool(winner_pt)),
        "challenger_material_available": int(bool(challenger_pt)),
        "pair_material_available": int(bool(winner_pt) and bool(challenger_pt)),
        "scorer_sidecar_available": 0,
        "scorer_sidecar_missing_reason": "",
        "winner_text_length": winner_div["text_length"],
        "challenger_text_length": challenger_div["text_length"],
        "winner_repeated_ngram_rate": winner_div["repeated_ngram_rate"],
        "challenger_repeated_ngram_rate": challenger_div["repeated_ngram_rate"],
        "winner_unique_token_rate": winner_div["unique_token_rate"],
        "challenger_unique_token_rate": challenger_div["unique_token_rate"],
        "winner_entropy_norm": winner_div["entropy_norm"],
        "challenger_entropy_norm": challenger_div["entropy_norm"],
        "winner_low_diversity_penalty": winner_div["low_diversity_penalty"],
        "challenger_low_diversity_penalty": challenger_div["low_diversity_penalty"],
        "winner_low_diversity_penalty_preferred": int(
            _prefer_lower(winner_div["low_diversity_penalty"], challenger_div["low_diversity_penalty"]) == "winner"
        ),
        "challenger_low_diversity_penalty_preferred": int(
            _prefer_lower(winner_div["low_diversity_penalty"], challenger_div["low_diversity_penalty"]) == "challenger"
        ),
    }
    truth_better = _truth_better_side(row)
    row["repeated_ngram_rate_prefers_truth_better"] = int(
        bool(truth_better)
        and truth_better != "tie"
        and _prefer_lower(row["winner_repeated_ngram_rate"], row["challenger_repeated_ngram_rate"]) == truth_better
    )
    row["low_diversity_penalty_prefers_truth_better"] = int(
        bool(truth_better)
        and truth_better != "tie"
        and _prefer_lower(row["winner_low_diversity_penalty"], row["challenger_low_diversity_penalty"]) == truth_better
    )
    for prefix in ("winner", "challenger"):
        for suffix in (
            "char_lm_score",
            "window_mean",
            "window_worst",
            "window_lower_quartile",
            "window_variance",
            "span_hamming_score",
            "word_ngram_judge_score",
        ):
            row[f"{prefix}_{suffix}"] = ""
    if winner_pt and challenger_pt:
        try:
            scorer = _build_scorer_runtime(artifact=artifact, run_config=run_config)
            winner_score = _score_sidecar(scorer=scorer, plaintext_idx=winner_pt)
            challenger_score = _score_sidecar(scorer=scorer, plaintext_idx=challenger_pt)
            for key, value in winner_score.items():
                row[f"winner_{key}"] = value
            for key, value in challenger_score.items():
                row[f"challenger_{key}"] = value
            row["scorer_sidecar_available"] = 1
        except Exception as exc:  # report-only enrichment should stay extractable
            row["scorer_sidecar_missing_reason"] = type(exc).__name__ + ": " + str(exc)
    else:
        row["scorer_sidecar_missing_reason"] = "missing winner or challenger final_plaintext_idx"
    subtype, preferred = _classify_sidecar(row)
    row["failure_subtype_after_sidecars"] = subtype
    row["component_that_prefers_truth_better"] = preferred
    return {field: row.get(field, "") for field in ROW_FIELDS}


def build_sidecar_rows(source_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [build_sidecar_row(row) for row in source_rows]


def _count_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key, "") or "none")
        out[value] = int(out.get(value, 0) + 1)
    return dict(sorted(out.items()))


def _candidate_pair_key(row: Mapping[str, Any]) -> str:
    return "{winner}|{challenger}".format(
        winner=str(row.get("winner_candidate_hash", "") or ""),
        challenger=str(row.get("challenger_candidate_hash", "") or ""),
    )


def _fixture_search_key(row: Mapping[str, Any]) -> str:
    return "{fixture}|{search}".format(
        fixture=str(row.get("fixture_seed", "") or ""),
        search=str(row.get("search_seed", "") or ""),
    )


def _unique_by_candidate_pair(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = _candidate_pair_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(row))
    return out


def _counts_by_key(rows: Sequence[Mapping[str, Any]], key_fn) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        key = str(key_fn(row) or "none")
        out[key] = int(out.get(key, 0) + 1)
    return dict(sorted(out.items(), key=lambda item: (-item[1], item[0])))


def _dominant_count(counts: Mapping[str, int]) -> int:
    return int(max(counts.values()) if counts else 0)


def _preference_counts(
    rows: Sequence[Mapping[str, Any]],
    *,
    winner_key: str,
    challenger_key: str,
    lower_is_better: bool,
) -> dict[str, int]:
    counts = {"winner": 0, "challenger": 0, "tie": 0, "missing": 0, "truth_better": 0, "truth_worse": 0}
    for row in rows:
        if lower_is_better:
            preferred = _prefer_lower(row.get(winner_key), row.get(challenger_key))
        else:
            preferred = _prefer_higher(row.get(winner_key), row.get(challenger_key))
        if not preferred:
            counts["missing"] += 1
            continue
        counts[preferred] += 1
        truth_better = _truth_better_side(row)
        if truth_better and truth_better != "tie" and preferred != "tie":
            if preferred == truth_better:
                counts["truth_better"] += 1
            else:
                counts["truth_worse"] += 1
    return counts


def summarize_sidecar_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    row_list = [dict(row) for row in rows]
    enriched_rows = [row for row in row_list if int(row.get("scorer_sidecar_available", 0) or 0)]
    missing_rows = [row for row in row_list if not int(row.get("scorer_sidecar_available", 0) or 0)]
    unique_rows = _unique_by_candidate_pair(row_list)
    unique_enriched_rows = _unique_by_candidate_pair(enriched_rows)
    candidate_pair_counts = _counts_by_key(row_list, _candidate_pair_key)
    enriched_candidate_pair_counts = _counts_by_key(enriched_rows, _candidate_pair_key)
    fixture_search_counts = _counts_by_key(row_list, _fixture_search_key)
    dominant_pair_count = _dominant_count(candidate_pair_counts)
    dominant_enriched_pair_count = _dominant_count(enriched_candidate_pair_counts)
    winner_missing = [
        row
        for row in missing_rows
        if not int(row.get("winner_material_available", 0) or 0)
        and int(row.get("challenger_material_available", 0) or 0)
    ]
    challenger_missing = [
        row
        for row in missing_rows
        if int(row.get("winner_material_available", 0) or 0)
        and not int(row.get("challenger_material_available", 0) or 0)
    ]
    both_missing = [
        row
        for row in missing_rows
        if not int(row.get("winner_material_available", 0) or 0)
        and not int(row.get("challenger_material_available", 0) or 0)
    ]
    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "row_occurrence_count": len(row_list),
        "pair_count": len(row_list),
        "unique_candidate_pair_count": len(unique_rows),
        "unique_fixture_search_count": len(fixture_search_counts),
        "candidate_pair_counts": candidate_pair_counts,
        "fixture_search_counts": fixture_search_counts,
        "dominant_pair_count": dominant_pair_count,
        "dominant_pair_fraction": (
            None if not row_list else float(dominant_pair_count / len(row_list))
        ),
        "pair_material_available_count": sum(int(row.get("pair_material_available", 0) or 0) for row in row_list),
        "scorer_sidecar_available_count": len(enriched_rows),
        "scorer_sidecar_missing_count": len(missing_rows),
        "unique_enriched_candidate_pair_count": len(unique_enriched_rows),
        "enriched_candidate_pair_counts": enriched_candidate_pair_counts,
        "dominant_enriched_pair_count": dominant_enriched_pair_count,
        "dominant_enriched_pair_fraction": (
            None if not enriched_rows else float(dominant_enriched_pair_count / len(enriched_rows))
        ),
        "sidecar_missing_reason_counts": _count_by(missing_rows, "scorer_sidecar_missing_reason"),
        "missing_candidate_material_count": sum(
            1 for row in missing_rows if not int(row.get("pair_material_available", 0) or 0)
        ),
        "missing_winner_material_count": len(winner_missing),
        "missing_challenger_material_count": len(challenger_missing),
        "missing_both_material_count": len(both_missing),
        "failure_subtype_after_sidecars_counts": _count_by(row_list, "failure_subtype_after_sidecars"),
        "component_that_prefers_truth_better_counts": _count_by(row_list, "component_that_prefers_truth_better"),
        "char_lm_preference_counts": _preference_counts(
            row_list,
            winner_key="winner_char_lm_score",
            challenger_key="challenger_char_lm_score",
            lower_is_better=False,
        ),
        "char_lm_unique_pair_preference_counts": _preference_counts(
            unique_enriched_rows,
            winner_key="winner_char_lm_score",
            challenger_key="challenger_char_lm_score",
            lower_is_better=False,
        ),
        "span_hamming_preference_counts": _preference_counts(
            row_list,
            winner_key="winner_span_hamming_score",
            challenger_key="challenger_span_hamming_score",
            lower_is_better=False,
        ),
        "span_hamming_unique_pair_preference_counts": _preference_counts(
            unique_enriched_rows,
            winner_key="winner_span_hamming_score",
            challenger_key="challenger_span_hamming_score",
            lower_is_better=False,
        ),
        "word_ngram_judge_preference_counts": _preference_counts(
            row_list,
            winner_key="winner_word_ngram_judge_score",
            challenger_key="challenger_word_ngram_judge_score",
            lower_is_better=True,
        ),
        "word_ngram_judge_unique_pair_preference_counts": _preference_counts(
            unique_enriched_rows,
            winner_key="winner_word_ngram_judge_score",
            challenger_key="challenger_word_ngram_judge_score",
            lower_is_better=True,
        ),
        "repeated_ngram_rate_preference_counts": _preference_counts(
            row_list,
            winner_key="winner_repeated_ngram_rate",
            challenger_key="challenger_repeated_ngram_rate",
            lower_is_better=True,
        ),
        "repeated_ngram_rate_unique_pair_preference_counts": _preference_counts(
            unique_enriched_rows,
            winner_key="winner_repeated_ngram_rate",
            challenger_key="challenger_repeated_ngram_rate",
            lower_is_better=True,
        ),
        "low_diversity_penalty_preference_counts": _preference_counts(
            row_list,
            winner_key="winner_low_diversity_penalty",
            challenger_key="challenger_low_diversity_penalty",
            lower_is_better=True,
        ),
        "low_diversity_penalty_unique_pair_preference_counts": _preference_counts(
            unique_enriched_rows,
            winner_key="winner_low_diversity_penalty",
            challenger_key="challenger_low_diversity_penalty",
            lower_is_better=True,
        ),
        "repeated_ngram_rate_truth_better_row_count": sum(
            int(row.get("repeated_ngram_rate_prefers_truth_better", 0) or 0) for row in row_list
        ),
        "repeated_ngram_rate_truth_better_unique_pair_count": sum(
            int(row.get("repeated_ngram_rate_prefers_truth_better", 0) or 0) for row in unique_enriched_rows
        ),
        "low_diversity_penalty_truth_better_row_count": sum(
            int(row.get("low_diversity_penalty_prefers_truth_better", 0) or 0) for row in row_list
        ),
        "low_diversity_penalty_truth_better_unique_pair_count": sum(
            int(row.get("low_diversity_penalty_prefers_truth_better", 0) or 0) for row in unique_enriched_rows
        ),
        "rows_with_challenger_lower_diversity_penalty_count": sum(
            1 for row in row_list if int(row.get("challenger_low_diversity_penalty_preferred", 0) or 0)
        ),
        "rows_with_winner_lower_diversity_penalty_count": sum(
            1 for row in row_list if int(row.get("winner_low_diversity_penalty_preferred", 0) or 0)
        ),
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ROW_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in ROW_FIELDS})


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=True, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_readout(rows: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> str:
    lines = [
        "# Current Scorer Failure Sidecars v1",
        "",
        "## Summary",
        "",
        f"- row occurrences: `{summary['row_occurrence_count']}`",
        f"- unique winner/challenger candidate pairs: `{summary['unique_candidate_pair_count']}`",
        f"- enriched row occurrences with scorer sidecars: `{summary['scorer_sidecar_available_count']}`",
        f"- unique enriched winner/challenger candidate pairs: `{summary['unique_enriched_candidate_pair_count']}`",
        f"- dominant enriched candidate-pair row count: `{summary['dominant_enriched_pair_count']}`",
        f"- dominant enriched candidate-pair fraction: `{float(summary['dominant_enriched_pair_fraction'] or 0.0):.3f}`",
        f"- row occurrences missing scorer sidecars: `{summary['scorer_sidecar_missing_count']}`",
        "",
        "## Failure Subtypes After Sidecars",
        "",
    ]
    for key, value in dict(summary.get("failure_subtype_after_sidecars_counts", {})).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Candidate Pair Repetition", ""])
    for key, count in list(dict(summary.get("candidate_pair_counts", {})).items())[:10]:
        lines.append(f"- `{key}`: `{count}` row occurrences")
    lines.extend(["", "## Enriched Candidate Pair Repetition", ""])
    for key, count in list(dict(summary.get("enriched_candidate_pair_counts", {})).items())[:10]:
        lines.append(f"- `{key}`: `{count}` enriched row occurrences")
    lines.extend(["", "## Components Preferring Truth-Better Candidate", ""])
    for key, value in dict(summary.get("component_that_prefers_truth_better_counts", {})).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Component Preference Counts", ""])
    for name in (
        "char_lm_preference_counts",
        "span_hamming_preference_counts",
        "word_ngram_judge_preference_counts",
        "repeated_ngram_rate_preference_counts",
        "low_diversity_penalty_preference_counts",
        "char_lm_unique_pair_preference_counts",
        "span_hamming_unique_pair_preference_counts",
        "word_ngram_judge_unique_pair_preference_counts",
        "repeated_ngram_rate_unique_pair_preference_counts",
        "low_diversity_penalty_unique_pair_preference_counts",
    ):
        lines.append(f"- `{name}`: `{json.dumps(dict(summary.get(name, {})), ensure_ascii=True, sort_keys=True)}`")
    lines.extend(
        [
            "",
            "## Split Motif Diagnostics",
            "",
            f"- repeated 4-gram rate prefers truth-better row occurrences: `{summary['repeated_ngram_rate_truth_better_row_count']}`",
            f"- repeated 4-gram rate prefers truth-better unique enriched pairs: `{summary['repeated_ngram_rate_truth_better_unique_pair_count']}`",
            f"- low-diversity penalty prefers truth-better row occurrences: `{summary['low_diversity_penalty_truth_better_row_count']}`",
            f"- low-diversity penalty prefers truth-better unique enriched pairs: `{summary['low_diversity_penalty_truth_better_unique_pair_count']}`",
            "",
            "## Sidecar Missingness",
            "",
            f"- missing candidate material row occurrences: `{summary['missing_candidate_material_count']}`",
            f"- missing winner material only: `{summary['missing_winner_material_count']}`",
            f"- missing challenger material only: `{summary['missing_challenger_material_count']}`",
            f"- missing both materials: `{summary['missing_both_material_count']}`",
        ]
    )
    for key, value in dict(summary.get("sidecar_missing_reason_counts", {})).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is Stage 2b enrichment for the selected truth-gap slice, not a runtime scorer change.",
            "- Truth fields remain evaluation-only.",
            "- Missing sidecar values are left blank and missing reasons are recorded.",
            "- The useful signal in this packet is specifically repeated 4-gram rate, not generic diversity.",
            "- Stage 3 should stay on hold until this narrowed interpretation is reviewed.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_sidecar_outputs(
    *,
    rows: Sequence[Mapping[str, Any]],
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Any]:
    resolved_output = output_dir.resolve()
    try:
        resolved_output.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Output directory must stay under repo root: {output_dir}") from exc
    resolved_output.mkdir(parents=True, exist_ok=True)
    row_list = [dict(row) for row in rows]
    summary = summarize_sidecar_rows(row_list)
    summary["output_dir"] = _repo_rel(resolved_output)
    _write_csv(resolved_output / "current_scorer_failure_sidecar_rows.csv", row_list)
    _write_jsonl(resolved_output / "current_scorer_failure_sidecar_rows.jsonl", row_list)
    _write_json(resolved_output / "current_scorer_failure_sidecar_summary.json", summary)
    (resolved_output / "current_scorer_failure_sidecar_readout.md").write_text(
        build_readout(row_list, summary),
        encoding="utf-8",
    )
    return summary


def run_study() -> dict[str, Any]:
    started = time.perf_counter()
    source_rows = collect_phasec_truth_gap_rows(RUN_ROOT)
    rows = build_sidecar_rows(source_rows)
    summary = write_sidecar_outputs(rows=rows)
    summary["elapsed_seconds"] = float(time.perf_counter() - started)
    _write_json(OUTPUT_DIR / "current_scorer_failure_sidecar_summary.json", summary)
    print(
        "[current_scorer_failure_sidecars_v1] "
        f"rows={summary['row_occurrence_count']} "
        f"unique_pairs={summary['unique_candidate_pair_count']} "
        f"sidecar_rows={summary['scorer_sidecar_available_count']} "
        f"unique_enriched_pairs={summary['unique_enriched_candidate_pair_count']} "
        f"output_dir={summary['output_dir']}",
        flush=True,
    )
    return summary


def main() -> None:
    run_study()


if __name__ == "__main__":
    main()
