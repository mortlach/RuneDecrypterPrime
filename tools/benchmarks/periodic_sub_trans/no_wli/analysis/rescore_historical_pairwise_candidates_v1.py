from __future__ import annotations

import csv
import json
import math
import shutil
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


RUN_LABEL = "historical_pairwise_rescore_v1"
TRUTH_GAP_THRESHOLD = 0.05
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_pairwise_rescore_v1"
)
REVIEW_PACK_DIR_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02"
)
REVIEW_PACK_ZIP_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02.zip"
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

from rune_decrypter_prime.api import Direction  # noqa: E402
from rune_decrypter_prime.core.config.cipher import CipherConfig  # noqa: E402
from rune_decrypter_prime.core.config.scoring import ScoringConfig  # noqa: E402
from rune_decrypter_prime.core.engine.builders import build_scorer  # noqa: E402
from rune_decrypter_prime.core.types import Device  # noqa: E402
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (  # noqa: E402
    mine_historical_pairwise_candidates_v1 as s0,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runtime_defaults import (  # noqa: E402
    DEFAULT_SCORER_FULL,
)


OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL
REVIEW_PACK_DIR = REPO_ROOT / REVIEW_PACK_DIR_REL
REVIEW_PACK_ZIP = REPO_ROOT / REVIEW_PACK_ZIP_REL

FROZEN_CURRENT_SCORER_CFG = dict(DEFAULT_SCORER_FULL)
FROZEN_CURRENT_SCORER_LABEL = "DEFAULT_SCORER_FULL_2026-05-02"

PAIR_FIELDS = (
    "pair_id",
    "artifact_path",
    "fixture_id",
    "fixture_seed",
    "search_seed",
    "token_length",
    "winner_candidate_hash",
    "challenger_candidate_hash",
    "winner_token_hash",
    "challenger_token_hash",
    "winner_truth_match",
    "challenger_truth_match",
    "truth_gap",
    "winner_stored_score",
    "challenger_stored_score",
    "stored_score_margin",
    "stored_score_correct",
    "winner_current_score",
    "challenger_current_score",
    "current_score_margin",
    "current_score_correct",
    "stored_current_agree",
    "winner_repeated_3gram_rate",
    "challenger_repeated_3gram_rate",
    "winner_repeated_4gram_rate",
    "challenger_repeated_4gram_rate",
    "winner_repeated_5gram_rate",
    "challenger_repeated_5gram_rate",
    "winner_repeated_6gram_rate",
    "challenger_repeated_6gram_rate",
    "current_feature_fields_present",
    "current_feature_fields_missing",
    "current_score_missing_reason",
)

FEATURE_SUMMARY_FIELDS = (
    "feature_name",
    "pair_group",
    "pair_count",
    "feature_prefers_truth_better_count",
    "feature_prefers_truth_better_fraction",
)

MISSINGNESS_FIELDS = (
    "missing_reason",
    "row_count",
    "unique_text_hash_count",
    "example_token_hashes",
)


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def _finite_or_blank(value: Any) -> float | str:
    out = _safe_float(value)
    return float(out) if math.isfinite(out) else ""


def _tokens(token_sequence_text: str) -> list[int]:
    vals = [int(part) for part in str(token_sequence_text).split()]
    if not vals or any(token < 0 or token > 28 for token in vals):
        raise ValueError("numeric rune/base-29 tokens must be in 0..28")
    return vals


def validate_numeric_tokens(token_sequence_text: str) -> bool:
    _ = _tokens(token_sequence_text)
    return True


def _artifact_metadata(artifact_path_text: str) -> dict[str, Any]:
    artifact_path = REPO_ROOT / artifact_path_text
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    return {
        "artifact_path": artifact_path_text,
        "fixture_id": str(artifact.get("instance_fixture_id", artifact.get("fixture_id", "")) or ""),
        "period": int(artifact.get("period", 0) or 0),
        "columns": int(artifact.get("columns", 0) or 0),
        "alphabet_size": int(artifact.get("alphabet_size", 29) or 29),
        "order": str(artifact.get("order", "sub_then_col") or "sub_then_col"),
        "direction": str(artifact.get("direction", "ltr") or "ltr"),
    }


def _scorer_key(meta: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(meta.get("direction", "ltr")),
        int(meta.get("period", 0) or 0),
        int(meta.get("columns", 0) or 0),
        int(meta.get("alphabet_size", 29) or 29),
        str(meta.get("order", "sub_then_col")),
    )


def _build_frozen_scorer(meta: Mapping[str, Any]) -> Any:
    direction = Direction(str(meta.get("direction", "ltr")))
    period = int(meta.get("period", 0) or 0)
    columns = int(meta.get("columns", 0) or 0)
    alphabet_size = int(meta.get("alphabet_size", 29) or 29)
    cfg_full = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=period,
        columns=columns,
        alphabet_size=alphabet_size,
        key_length=int(period * alphabet_size + columns),
        order=str(meta.get("order", "sub_then_col")),
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    scorer_cfg = dict(FROZEN_CURRENT_SCORER_CFG, encoding_dir=direction)
    return build_scorer(cfg_full, ScoringConfig(**scorer_cfg))


def _score_rows(deduped_rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    artifact_meta_cache: dict[str, dict[str, Any]] = {}
    scorer_cache: dict[tuple[Any, ...], Any] = {}
    grouped: dict[tuple[Any, int], list[Mapping[str, Any]]] = defaultdict(list)
    row_meta: dict[tuple[str, str], dict[str, Any]] = {}
    scored: dict[tuple[str, str], dict[str, Any]] = {}

    for row in deduped_rows:
        key = (str(row.get("artifact_path", "")), str(row.get("partial_text_hash", "")))
        artifact_path = str(row.get("artifact_path", ""))
        try:
            meta = artifact_meta_cache.get(artifact_path)
            if meta is None:
                meta = _artifact_metadata(artifact_path)
                artifact_meta_cache[artifact_path] = meta
            scorer_key = _scorer_key(meta)
            grouped[(scorer_key, int(row.get("token_count", 0) or 0))].append(row)
            row_meta[key] = meta
        except Exception as exc:
            scored[key] = {
                "current_score": "",
                "features_present": "",
                "features_missing": "current_score",
                "missing_reason": type(exc).__name__ + ": " + str(exc),
            }

    for (scorer_key, token_count), rows in sorted(grouped.items(), key=lambda item: str(item[0])):
        meta = {
            "direction": scorer_key[0],
            "period": scorer_key[1],
            "columns": scorer_key[2],
            "alphabet_size": scorer_key[3],
            "order": scorer_key[4],
        }
        try:
            scorer = scorer_cache.get(scorer_key)
            if scorer is None:
                scorer = _build_frozen_scorer(meta)
                scorer_cache[scorer_key] = scorer
            token_arrays = [np.asarray(_tokens(str(row.get("token_sequence_text", ""))), dtype=np.uint8) for row in rows]
            scores = scorer.batch_score(token_arrays, None)
            stats = {}
            try:
                stats = dict(scorer.last_stats()) if hasattr(scorer, "last_stats") else {}
            except Exception:
                stats = {}
            base_present = ["current_score"]
            if "score_mean" in stats:
                base_present.append("score_mean")
            if "stat.mean_per_ngram_penalized" in stats:
                base_present.append("stat.mean_per_ngram_penalized")
            for row, score in zip(rows, scores):
                key = (str(row.get("artifact_path", "")), str(row.get("partial_text_hash", "")))
                scored[key] = {
                    "current_score": float(score),
                    "features_present": ";".join(base_present),
                    "features_missing": "span_hamming;word_ngram_judge;window_worst;window_lower_quartile",
                    "missing_reason": "",
                }
        except Exception as exc:
            for row in rows:
                key = (str(row.get("artifact_path", "")), str(row.get("partial_text_hash", "")))
                scored[key] = {
                    "current_score": "",
                    "features_present": "",
                    "features_missing": "current_score",
                    "missing_reason": type(exc).__name__ + ": " + str(exc),
                }
        _ = token_count
    return scored


def _group_for_pairs(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, int], list[Mapping[str, Any]]]:
    groups: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("artifact_path", "")), int(row.get("token_count", 0) or 0))].append(row)
    return groups


def _truth_better_pair(left: Mapping[str, Any], right: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if _safe_float(left.get("truth_match")) >= _safe_float(right.get("truth_match")):
        return left, right
    return right, left


def _score_correct(*, winner_score: Any, challenger_score: Any) -> int | str:
    winner = _safe_float(winner_score)
    challenger = _safe_float(challenger_score)
    if not math.isfinite(winner) or not math.isfinite(challenger):
        return ""
    if winner == challenger:
        return ""
    return int(winner > challenger)


def _pair_rows(deduped_rows: Sequence[Mapping[str, Any]], rescored: Mapping[tuple[str, str], Mapping[str, Any]]) -> list[dict[str, Any]]:
    artifact_meta_cache: dict[str, dict[str, Any]] = {}
    out: list[dict[str, Any]] = []
    for (artifact_path, token_count), rows in sorted(_group_for_pairs(deduped_rows).items()):
        if len(rows) < 2:
            continue
        ordered = sorted(rows, key=lambda row: (str(row.get("candidate_hash", "")), str(row.get("partial_text_hash", ""))))
        for left, right in combinations(ordered, 2):
            truth_gap = abs(_safe_float(left.get("truth_match")) - _safe_float(right.get("truth_match")))
            if truth_gap < TRUTH_GAP_THRESHOLD:
                continue
            if _safe_float(left.get("score")) == _safe_float(right.get("score")):
                continue
            winner, challenger = _truth_better_pair(left, right)
            winner_key = (str(winner.get("artifact_path", "")), str(winner.get("partial_text_hash", "")))
            challenger_key = (str(challenger.get("artifact_path", "")), str(challenger.get("partial_text_hash", "")))
            winner_current = rescored.get(winner_key, {})
            challenger_current = rescored.get(challenger_key, {})
            stored_correct = _score_correct(
                winner_score=winner.get("score"),
                challenger_score=challenger.get("score"),
            )
            current_correct = _score_correct(
                winner_score=winner_current.get("current_score"),
                challenger_score=challenger_current.get("current_score"),
            )
            meta = artifact_meta_cache.get(artifact_path)
            if meta is None:
                try:
                    meta = _artifact_metadata(artifact_path)
                except Exception:
                    meta = {}
                artifact_meta_cache[artifact_path] = meta
            missing_reason = ";".join(
                sorted(
                    {
                        str(winner_current.get("missing_reason", "") or ""),
                        str(challenger_current.get("missing_reason", "") or ""),
                    }
                    - {""}
                )
            )
            fields_present = ";".join(
                sorted(
                    {
                        part
                        for value in (
                            str(winner_current.get("features_present", "") or ""),
                            str(challenger_current.get("features_present", "") or ""),
                        )
                        for part in value.split(";")
                        if part
                    }
                )
            )
            fields_missing = ";".join(
                sorted(
                    {
                        part
                        for value in (
                            str(winner_current.get("features_missing", "") or ""),
                            str(challenger_current.get("features_missing", "") or ""),
                        )
                        for part in value.split(";")
                        if part
                    }
                )
            )
            repeated = {}
            for ngram_size in (3, 4, 5, 6):
                repeated[f"winner_repeated_{ngram_size}gram_rate"] = s0.repeated_ngram_rate(
                    str(winner.get("token_sequence_text", "")),
                    ngram_size,
                )
                repeated[f"challenger_repeated_{ngram_size}gram_rate"] = s0.repeated_ngram_rate(
                    str(challenger.get("token_sequence_text", "")),
                    ngram_size,
                )
            out.append(
                {
                    "pair_id": s0._pair_id(  # stable report-only id
                        artifact_path,
                        winner.get("candidate_hash"),
                        winner.get("partial_text_hash"),
                        challenger.get("candidate_hash"),
                        challenger.get("partial_text_hash"),
                    ),
                    "artifact_path": artifact_path,
                    "fixture_id": str(meta.get("fixture_id", "")),
                    "fixture_seed": str(winner.get("fixture_seed", "") or challenger.get("fixture_seed", "")),
                    "search_seed": str(winner.get("search_seed", "") or challenger.get("search_seed", "")),
                    "token_length": int(token_count),
                    "winner_candidate_hash": str(winner.get("candidate_hash", "")),
                    "challenger_candidate_hash": str(challenger.get("candidate_hash", "")),
                    "winner_token_hash": str(winner.get("partial_text_hash", "")),
                    "challenger_token_hash": str(challenger.get("partial_text_hash", "")),
                    "winner_truth_match": float(_safe_float(winner.get("truth_match"))),
                    "challenger_truth_match": float(_safe_float(challenger.get("truth_match"))),
                    "truth_gap": float(truth_gap),
                    "winner_stored_score": float(_safe_float(winner.get("score"))),
                    "challenger_stored_score": float(_safe_float(challenger.get("score"))),
                    "stored_score_margin": float(_safe_float(winner.get("score")) - _safe_float(challenger.get("score"))),
                    "stored_score_correct": stored_correct,
                    "winner_current_score": _finite_or_blank(winner_current.get("current_score")),
                    "challenger_current_score": _finite_or_blank(challenger_current.get("current_score")),
                    "current_score_margin": (
                        _finite_or_blank(
                            _safe_float(winner_current.get("current_score"))
                            - _safe_float(challenger_current.get("current_score"))
                        )
                    ),
                    "current_score_correct": current_correct,
                    "stored_current_agree": (
                        int(stored_correct == current_correct)
                        if stored_correct in (0, 1) and current_correct in (0, 1)
                        else ""
                    ),
                    **repeated,
                    "current_feature_fields_present": fields_present,
                    "current_feature_fields_missing": fields_missing,
                    "current_score_missing_reason": missing_reason,
                }
            )
    return [{field: row.get(field, "") for field in PAIR_FIELDS} for row in out]


def _count_unique(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return len({str(row.get(key, "") or "") for row in rows if str(row.get(key, "") or "")})


def _text_pair_key(row: Mapping[str, Any]) -> str:
    return s0._pair_key(str(row.get("winner_token_hash", "")), str(row.get("challenger_token_hash", "")))


def _candidate_pair_key(row: Mapping[str, Any]) -> str:
    return s0._pair_key(str(row.get("winner_candidate_hash", "")), str(row.get("challenger_candidate_hash", "")))


def _dominant_fraction(values: Sequence[str]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    return (max(counts.values()) / total) if total else 0.0


def _feature_prefers_truth_better(row: Mapping[str, Any], feature_prefix: str) -> bool:
    winner = _safe_float(row.get(f"winner_{feature_prefix}"))
    challenger = _safe_float(row.get(f"challenger_{feature_prefix}"))
    return math.isfinite(winner) and math.isfinite(challenger) and winner < challenger


def _feature_summary_rows(pair_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups = {
        "all": list(pair_rows),
        "stored_misranked": [row for row in pair_rows if int(row.get("stored_score_correct", 0) or 0) == 0],
        "stored_correct": [row for row in pair_rows if int(row.get("stored_score_correct", 0) or 0) == 1],
        "current_misranked": [row for row in pair_rows if int(row.get("current_score_correct", 0) or 0) == 0],
        "current_correct": [row for row in pair_rows if int(row.get("current_score_correct", 0) or 0) == 1],
    }
    out: list[dict[str, Any]] = []
    for group_name, rows in groups.items():
        unique: dict[str, Mapping[str, Any]] = {}
        for row in rows:
            unique.setdefault(_text_pair_key(row), row)
        unique_rows = list(unique.values())
        for ngram_size in (3, 4, 5, 6):
            feature = f"repeated_{ngram_size}gram_rate"
            count = sum(int(_feature_prefers_truth_better(row, feature)) for row in unique_rows)
            out.append(
                {
                    "feature_name": feature,
                    "pair_group": group_name,
                    "pair_count": len(unique_rows),
                    "feature_prefers_truth_better_count": count,
                    "feature_prefers_truth_better_fraction": count / len(unique_rows) if unique_rows else 0.0,
                }
            )
    return out


def _missingness_rows(pair_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in pair_rows:
        reason = str(row.get("current_score_missing_reason", "") or "none")
        grouped[reason].append(row)
    out = []
    for reason, rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        hashes = sorted(
            {
                str(row.get("winner_token_hash", ""))
                for row in rows
            }
            | {
                str(row.get("challenger_token_hash", ""))
                for row in rows
            }
        )
        out.append(
            {
                "missing_reason": reason,
                "row_count": len(rows),
                "unique_text_hash_count": len([h for h in hashes if h]),
                "example_token_hashes": ";".join(hashes[:10]),
            }
        )
    return out


def build_summary(pair_rows: Sequence[Mapping[str, Any]], *, elapsed_seconds: float) -> dict[str, Any]:
    valid_current = [row for row in pair_rows if row.get("current_score_correct") in (0, 1)]
    stored_correct = [row for row in pair_rows if int(row.get("stored_score_correct", 0) or 0) == 1]
    current_correct = [row for row in valid_current if int(row.get("current_score_correct", 0) or 0) == 1]
    stored_misranked = [row for row in pair_rows if int(row.get("stored_score_correct", 0) or 0) == 0]
    current_misranked = [row for row in valid_current if int(row.get("current_score_correct", 0) or 0) == 0]
    stored_current_agree = [row for row in valid_current if int(row.get("stored_current_agree", 0) or 0) == 1]
    text_pair_keys = [_text_pair_key(row) for row in pair_rows]
    candidate_pair_keys = [_candidate_pair_key(row) for row in pair_rows]
    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "elapsed_seconds": float(elapsed_seconds),
        "frozen_current_scorer_label": FROZEN_CURRENT_SCORER_LABEL,
        "frozen_current_scorer_cfg": dict(FROZEN_CURRENT_SCORER_CFG),
        "truth_gap_threshold": TRUTH_GAP_THRESHOLD,
        "pair_count": len(pair_rows),
        "current_score_available_pair_count": len(valid_current),
        "current_score_missing_pair_count": len(pair_rows) - len(valid_current),
        "stored_score_correct_count": len(stored_correct),
        "stored_score_misranked_count": len(stored_misranked),
        "stored_score_pairwise_accuracy": len(stored_correct) / len(pair_rows) if pair_rows else 0.0,
        "current_score_correct_count": len(current_correct),
        "current_score_misranked_count": len(current_misranked),
        "current_score_pairwise_accuracy": len(current_correct) / len(valid_current) if valid_current else 0.0,
        "stored_current_agree_count": len(stored_current_agree),
        "stored_current_agree_fraction": len(stored_current_agree) / len(valid_current) if valid_current else 0.0,
        "unique_numeric_text_pair_count": len(set(text_pair_keys)),
        "unique_candidate_hash_pair_count": len(set(candidate_pair_keys)),
        "artifact_count": _count_unique(pair_rows, "artifact_path"),
        "fixture_search_cell_count": len(
            {
                (str(row.get("fixture_seed", "")), str(row.get("search_seed", "")))
                for row in pair_rows
            }
        ),
        "dominant_text_pair_fraction": _dominant_fraction(text_pair_keys),
        "dominant_candidate_hash_pair_fraction": _dominant_fraction(candidate_pair_keys),
        "output_dir": OUTPUT_DIR_REL,
        "representation_rule": "Numeric rune/base-29 token sequences only; values 0..28.",
        "truth_is_evaluation_only": True,
        "runtime_behavior_changed": False,
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
    return "\n".join(
        [
            "# Historical Pairwise Rescore v1",
            "",
            "## Purpose",
            "",
            "Re-score S0 historical numeric rune/base-29 candidate pairs through one frozen current scorer stack.",
            "",
            "## Frozen Scorer",
            "",
            f"- label: `{summary['frozen_current_scorer_label']}`",
            f"- config: `{json.dumps(summary['frozen_current_scorer_cfg'], sort_keys=True)}`",
            "",
            "## Counts",
            "",
            f"- pair count: `{summary['pair_count']}`",
            f"- current-score available pairs: `{summary['current_score_available_pair_count']}`",
            f"- current-score missing pairs: `{summary['current_score_missing_pair_count']}`",
            f"- stored-score correct: `{summary['stored_score_correct_count']}`",
            f"- stored-score misranked: `{summary['stored_score_misranked_count']}`",
            f"- stored-score pairwise accuracy: `{summary['stored_score_pairwise_accuracy']:.4f}`",
            f"- current-score correct: `{summary['current_score_correct_count']}`",
            f"- current-score misranked: `{summary['current_score_misranked_count']}`",
            f"- current-score pairwise accuracy: `{summary['current_score_pairwise_accuracy']:.4f}`",
            f"- stored/current agreement: `{summary['stored_current_agree_count']}` / `{summary['current_score_available_pair_count']}` = `{summary['stored_current_agree_fraction']:.4f}`",
            f"- unique numeric text pairs: `{summary['unique_numeric_text_pair_count']}`",
            f"- unique candidate-hash pairs: `{summary['unique_candidate_hash_pair_count']}`",
            f"- artifacts represented: `{summary['artifact_count']}`",
            f"- fixture/search cells represented: `{summary['fixture_search_cell_count']}`",
            f"- dominant text-pair fraction: `{summary['dominant_text_pair_fraction']:.4f}`",
            f"- dominant candidate-hash-pair fraction: `{summary['dominant_candidate_hash_pair_fraction']:.4f}`",
            "",
            "## Caveats",
            "",
            "- Report-only. Runtime behavior was not changed.",
            "- Truth/match fields are evaluation labels only.",
            "- `winner` means truth-better candidate, not scorer-selected candidate.",
            "- This does not design a new scorer.",
        ]
    ).rstrip() + "\n"


def write_outputs() -> dict[str, Any]:
    started = time.perf_counter()
    labelled = s0.load_labelled_artifact_rows()
    deduped = s0.dedupe_artifact_candidate_text(labelled)
    rescored = _score_rows(deduped)
    pair_rows = _pair_rows(deduped, rescored)
    feature_rows = _feature_summary_rows(pair_rows)
    missingness_rows = _missingness_rows(pair_rows)
    summary = build_summary(pair_rows, elapsed_seconds=time.perf_counter() - started)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(OUTPUT_DIR / "historical_pairwise_rescore_pairs.csv", pair_rows, PAIR_FIELDS)
    _write_csv(OUTPUT_DIR / "historical_pairwise_rescore_feature_summary.csv", feature_rows, FEATURE_SUMMARY_FIELDS)
    _write_csv(OUTPUT_DIR / "historical_pairwise_rescore_missingness.csv", missingness_rows, MISSINGNESS_FIELDS)
    _write_json(OUTPUT_DIR / "historical_pairwise_rescore_summary.json", summary)
    (OUTPUT_DIR / "historical_pairwise_rescore_readout.md").write_text(
        build_readout(summary),
        encoding="utf-8",
    )
    print(
        "[historical_pairwise_rescore_v1] "
        f"pairs={summary['pair_count']} "
        f"current_available={summary['current_score_available_pair_count']} "
        f"current_correct={summary['current_score_correct_count']} "
        f"current_misranked={summary['current_score_misranked_count']} "
        f"output_dir={summary['output_dir']}",
        flush=True,
    )
    return summary


def update_review_pack() -> None:
    if not REVIEW_PACK_DIR.exists():
        return
    dst = REVIEW_PACK_DIR / "historical_pairwise_rescore"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(OUTPUT_DIR, dst)
    source_dst = REVIEW_PACK_DIR / "source_scripts"
    source_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).resolve(), source_dst / Path(__file__).name)
    test_src = REPO_ROOT / "tests/tools/test_no_wli_historical_pairwise_rescore_v1.py"
    if test_src.exists():
        tests_dst = REVIEW_PACK_DIR / "tests"
        tests_dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_src, tests_dst / test_src.name)
    if REVIEW_PACK_ZIP.exists():
        REVIEW_PACK_ZIP.unlink()
    shutil.make_archive(str(REVIEW_PACK_ZIP.with_suffix("")), "zip", REVIEW_PACK_DIR)
    print(
        "[historical_pairwise_rescore_v1] "
        f"updated_pack={_repo_rel(REVIEW_PACK_DIR)} zip={_repo_rel(REVIEW_PACK_ZIP)}",
        flush=True,
    )


def main() -> None:
    write_outputs()
    update_review_pack()


if __name__ == "__main__":
    main()
