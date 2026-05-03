from __future__ import annotations

"""
Report-only pattern inspection for the fixed-500 normalized span scan.

This is deliberately small and comparative: it samples both rescues and breaks
for a few high-signal feature rows, then replays the 500-token chunks to
summarize interval shapes and repetition patterns.
"""

import csv
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


RUN_LABEL = "span_hamming_500_pattern_examples_v1"

PAIR_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
UNIQUE_PARTIAL_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_partial_text_review_v1/unique_partial_text_rows.csv"
)
CANDIDATE_FEATURES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_normalized_full_v1/span_hamming_500_normalized_candidate_features.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_pattern_examples_v1"
)

EXAMPLES_PER_BUCKET = 5
TEXT_PREVIEW_TOKENS = 90

TARGETS = (
    dict(
        target_id="strict_middle_short_fuzzy_noise",
        config_id="strict_selected_len3_14_hd2_cap256_norm500",
        chunk_kind="middle",
        feature_name="short_fuzzy_noise_len_le_4_norm",
        direction="lower",
    ),
    dict(
        target_id="strict_middle_err20_len_ge_5",
        config_id="strict_selected_len3_14_hd2_cap256_norm500",
        chunk_kind="middle",
        feature_name="err20_len_ge_5_norm",
        direction="higher",
    ),
    dict(
        target_id="research_suffix_short_fuzzy_noise",
        config_id="research_selected_len3_14_hd2_cap256_norm500",
        chunk_kind="suffix",
        feature_name="short_fuzzy_noise_len_le_4_norm",
        direction="lower",
    ),
)


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root from script path")


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.scoring.span_hamming.fast_backend import FastSpanHammingBackend  # noqa: E402
from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig  # noqa: E402
from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402


PAIR_ROWS = REPO_ROOT / PAIR_ROWS_REL
UNIQUE_PARTIAL_ROWS = REPO_ROOT / UNIQUE_PARTIAL_ROWS_REL
CANDIDATE_FEATURES = REPO_ROOT / CANDIDATE_FEATURES_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class Target:
    target_id: str
    config_id: str
    chunk_kind: str
    feature_name: str
    direction: str


@dataclass(frozen=True)
class SpanSpec:
    config_id: str
    dictionary_id: str
    wordlist_rel: str
    require_selected: bool
    len_min: int
    len_max: int
    max_hd: int
    max_candidates_per_window: int


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _parse_numeric_tokens(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in str(text).split() if part.strip())


def _safe_float(value: object) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def _read_token_rows(token_hashes: set[str]) -> dict[str, tuple[int, ...]]:
    loaded: dict[str, tuple[int, ...]] = {}
    with UNIQUE_PARTIAL_ROWS.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            token_hash = str(row.get("partial_text_hash", "")).strip()
            if token_hash not in token_hashes:
                continue
            loaded[token_hash] = _parse_numeric_tokens(str(row.get("token_sequence_text", "")))
            if len(loaded) >= len(token_hashes):
                break
    return loaded


def _feature_preference(direction: str, winner_value: float, challenger_value: float) -> str:
    if abs(winner_value - challenger_value) <= 1e-12:
        return "tie"
    if direction == "higher":
        return "truth_better" if winner_value > challenger_value else "truth_worse"
    if direction == "lower":
        return "truth_better" if winner_value < challenger_value else "truth_worse"
    raise ValueError(f"unknown direction: {direction}")


def _target_pairs(
    *,
    target: Target,
    pair_rows: Sequence[Mapping[str, str]],
    feature_by_key: Mapping[tuple[str, str, str], Mapping[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rescue_rows: list[dict[str, Any]] = []
    break_rows: list[dict[str, Any]] = []
    for pair in pair_rows:
        winner_hash = str(pair.get("winner_token_hash", "")).strip()
        challenger_hash = str(pair.get("challenger_token_hash", "")).strip()
        winner = feature_by_key.get((target.config_id, winner_hash, target.chunk_kind))
        challenger = feature_by_key.get((target.config_id, challenger_hash, target.chunk_kind))
        if winner is None or challenger is None:
            continue
        winner_value = _safe_float(winner.get(target.feature_name))
        challenger_value = _safe_float(challenger.get(target.feature_name))
        if winner_value is None or challenger_value is None:
            continue
        preference = _feature_preference(target.direction, winner_value, challenger_value)
        if preference == "tie":
            continue
        current_correct = str(pair.get("current_score_correct", "")).strip() == "1"
        margin = abs(winner_value - challenger_value)
        row = {
            "pair_id": str(pair.get("pair_id", "")),
            "winner_token_hash": winner_hash,
            "challenger_token_hash": challenger_hash,
            "winner_truth_match": pair.get("winner_truth_match", ""),
            "challenger_truth_match": pair.get("challenger_truth_match", ""),
            "winner_current_score": pair.get("winner_current_score", ""),
            "challenger_current_score": pair.get("challenger_current_score", ""),
            "current_score_correct": int(current_correct),
            "winner_feature": winner_value,
            "challenger_feature": challenger_value,
            "feature_margin_abs": margin,
            "feature_preference": preference,
        }
        if not current_correct and preference == "truth_better":
            rescue_rows.append(row)
        elif current_correct and preference == "truth_worse":
            break_rows.append(row)
    rescue_rows.sort(key=lambda item: float(item["feature_margin_abs"]), reverse=True)
    break_rows.sort(key=lambda item: float(item["feature_margin_abs"]), reverse=True)
    return rescue_rows[:EXAMPLES_PER_BUCKET], break_rows[:EXAMPLES_PER_BUCKET]


def _spec_from_candidate_row(row: Mapping[str, str]) -> SpanSpec:
    return SpanSpec(
        config_id=str(row["config_id"]),
        dictionary_id=str(row["dictionary_id"]),
        wordlist_rel=str(row["wordlist_rel"]),
        require_selected=str(row["require_selected"]).strip() == "1",
        len_min=int(row["len_min"]),
        len_max=int(row["len_max"]),
        max_hd=int(row["max_hd"]),
        max_candidates_per_window=int(row["max_candidates_per_window"]),
    )


def _backend_for_spec(spec: SpanSpec) -> FastSpanHammingBackend:
    return FastSpanHammingBackend(
        config=SpanHammingConfig(
            len_min=spec.len_min,
            len_max=spec.len_max,
            max_hd=spec.max_hd,
            max_candidates_per_window=spec.max_candidates_per_window,
            debug_return_intervals=True,
        ),
        wordlist_dir=REPO_ROOT / spec.wordlist_rel,
        require_selected=spec.require_selected,
        return_raw_intervals=True,
    )


def _chunk_bounds(candidate_feature_row: Mapping[str, str]) -> tuple[int, int]:
    return int(candidate_feature_row["chunk_start"]), int(candidate_feature_row["chunk_end"])


def _ngram_repeat_rate(tokens: Sequence[int], n: int) -> float:
    if len(tokens) < n:
        return 0.0
    grams = [tuple(tokens[i:i + n]) for i in range(0, len(tokens) - n + 1)]
    counts = Counter(grams)
    repeated = sum(count for count in counts.values() if count > 1)
    return float(repeated) / float(max(1, len(grams)))


def _interval_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    intervals = [dict(row) for row in payload.get("selected_intervals", [])]
    by_len_dist = Counter((int(row["length"]), int(row["distance"])) for row in intervals)
    short_fuzzy = sum(1 for row in intervals if int(row["length"]) <= 4 and int(row["distance"]) > 0)
    exact_ge5 = sum(1 for row in intervals if int(row["length"]) >= 5 and int(row["distance"]) == 0)
    err20_ge5 = sum(
        1
        for row in intervals
        if int(row["length"]) >= 5 and float(row["distance"]) / float(row["length"]) <= 0.20
    )
    err15_ge8 = sum(
        1
        for row in intervals
        if int(row["length"]) >= 8 and float(row["distance"]) / float(row["length"]) <= 0.15
    )
    top = sorted(by_len_dist.items(), key=lambda item: (-item[1], item[0]))[:8]
    return {
        "selected_intervals": len(intervals),
        "short_fuzzy_intervals": short_fuzzy,
        "exact_ge5_intervals": exact_ge5,
        "err20_ge5_intervals": err20_ge5,
        "err15_ge8_intervals": err15_ge8,
        "len_dist_counts": ";".join(f"{length}:{distance}={count}" for (length, distance), count in top),
        "span_raw": float(payload.get("span_raw", 0.0) or 0.0),
        "coverage": float(payload.get("coverage", 0.0) or 0.0),
        "quality": float(payload.get("quality", 0.0) or 0.0),
    }


def _render_preview(tokens: Sequence[int]) -> tuple[str, str]:
    preview_tokens = tuple(tokens[:TEXT_PREVIEW_TOKENS])
    numeric = " ".join(str(value) for value in preview_tokens)
    runes = Runeglish.pos_to_rune(preview_tokens)
    return numeric, runes


def _inspect_side(
    *,
    side: str,
    token_hash: str,
    target: Target,
    feature_by_key: Mapping[tuple[str, str, str], Mapping[str, str]],
    tokens_by_hash: Mapping[str, Sequence[int]],
    backend: FastSpanHammingBackend,
) -> dict[str, Any]:
    candidate_row = feature_by_key[(target.config_id, token_hash, target.chunk_kind)]
    start, end = _chunk_bounds(candidate_row)
    tokens = tuple(int(v) for v in tokens_by_hash[token_hash][start:end])
    payload = backend.score_payload(tokens)
    summary = _interval_summary(payload)
    numeric_preview, rune_preview = _render_preview(tokens)
    out = {
        "side": side,
        "token_hash": token_hash,
        "chunk_start": start,
        "chunk_end": end,
        "target_feature_value": candidate_row.get(target.feature_name, ""),
        "repeat_3_rate": f"{_ngram_repeat_rate(tokens, 3):.12g}",
        "repeat_4_rate": f"{_ngram_repeat_rate(tokens, 4):.12g}",
        "repeat_5_rate": f"{_ngram_repeat_rate(tokens, 5):.12g}",
        "numeric_preview": numeric_preview,
        "rune_preview": rune_preview,
    }
    out.update(summary)
    return out


def _build_readout(summary: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Span-Hamming 500 Pattern Examples v1",
        "",
        "## Purpose",
        "",
        "Small paired inspection of fixed-500 span-Hamming feature behaviour.",
        "",
        "## Status",
        "",
        f"- example pair buckets: `{summary['example_pair_bucket_count']}`",
        f"- side rows: `{summary['side_row_count']}`",
        f"- output CSV: `{summary['examples_csv']}`",
        "",
        "## Notes",
        "",
        "- This is intuition-building only, not a promotion gate.",
        "- Each target includes rescue and break examples to reduce overfitting.",
        "- Text previews are numeric/rune token previews from the scored 500-token band.",
        "",
        "## First Examples",
        "",
    ]
    for row in rows[:12]:
        lines.append(
            f"- `{row['target_id']}` `{row['example_kind']}` pair `{row['pair_id']}` "
            f"{row['side']}: selected=`{row['selected_intervals']}`, short_fuzzy=`{row['short_fuzzy_intervals']}`, "
            f"err20_ge5=`{row['err20_ge5_intervals']}`, repeats3=`{row['repeat_3_rate']}`"
        )
    return "\n".join(lines) + "\n"


def run_inspection() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pair_rows = _read_csv(PAIR_ROWS)
    candidate_rows = _read_csv(CANDIDATE_FEATURES)
    feature_by_key = {
        (str(row["config_id"]), str(row["token_hash"]), str(row["chunk_kind"])): row
        for row in candidate_rows
    }
    spec_by_config: dict[str, SpanSpec] = {}
    for row in candidate_rows:
        config_id = str(row["config_id"])
        if config_id not in spec_by_config:
            spec_by_config[config_id] = _spec_from_candidate_row(row)

    targets = [Target(**row) for row in TARGETS]
    selected_pairs: list[tuple[Target, str, dict[str, Any]]] = []
    required_hashes: set[str] = set()
    for target in targets:
        rescues, breaks = _target_pairs(target=target, pair_rows=pair_rows, feature_by_key=feature_by_key)
        for example_kind, rows in (("rescue", rescues), ("break", breaks)):
            for row in rows:
                selected_pairs.append((target, example_kind, row))
                required_hashes.add(str(row["winner_token_hash"]))
                required_hashes.add(str(row["challenger_token_hash"]))

    tokens_by_hash = _read_token_rows(required_hashes)
    backend_by_config = {
        target.config_id: _backend_for_spec(spec_by_config[target.config_id])
        for target in targets
    }

    side_rows: list[dict[str, Any]] = []
    for target, example_kind, pair in selected_pairs:
        backend = backend_by_config[target.config_id]
        common = {
            "run_label": RUN_LABEL,
            "target_id": target.target_id,
            "config_id": target.config_id,
            "chunk_kind": target.chunk_kind,
            "feature_name": target.feature_name,
            "feature_direction": target.direction,
            "example_kind": example_kind,
            "pair_id": pair["pair_id"],
            "winner_truth_match": pair["winner_truth_match"],
            "challenger_truth_match": pair["challenger_truth_match"],
            "winner_current_score": pair["winner_current_score"],
            "challenger_current_score": pair["challenger_current_score"],
            "winner_feature": pair["winner_feature"],
            "challenger_feature": pair["challenger_feature"],
            "feature_margin_abs": pair["feature_margin_abs"],
        }
        for side, key in (("winner", "winner_token_hash"), ("challenger", "challenger_token_hash")):
            token_hash = str(pair[key])
            if token_hash not in tokens_by_hash:
                continue
            side_row = _inspect_side(
                side=side,
                token_hash=token_hash,
                target=target,
                feature_by_key=feature_by_key,
                tokens_by_hash=tokens_by_hash,
                backend=backend,
            )
            merged = dict(common)
            merged.update(side_row)
            side_rows.append(merged)

    examples_csv = OUTPUT_DIR / "span_hamming_500_pattern_examples.csv"
    fieldnames = [
        "run_label",
        "target_id",
        "config_id",
        "chunk_kind",
        "feature_name",
        "feature_direction",
        "example_kind",
        "pair_id",
        "side",
        "token_hash",
        "winner_truth_match",
        "challenger_truth_match",
        "winner_current_score",
        "challenger_current_score",
        "winner_feature",
        "challenger_feature",
        "feature_margin_abs",
        "target_feature_value",
        "chunk_start",
        "chunk_end",
        "selected_intervals",
        "short_fuzzy_intervals",
        "exact_ge5_intervals",
        "err20_ge5_intervals",
        "err15_ge8_intervals",
        "len_dist_counts",
        "span_raw",
        "coverage",
        "quality",
        "repeat_3_rate",
        "repeat_4_rate",
        "repeat_5_rate",
        "numeric_preview",
        "rune_preview",
    ]
    _write_csv(examples_csv, side_rows, fieldnames)
    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": _repo_rel(OUTPUT_DIR),
        "targets": [target.__dict__ for target in targets],
        "example_pair_bucket_count": len(selected_pairs),
        "side_row_count": len(side_rows),
        "examples_csv": _repo_rel(examples_csv),
        "source_candidate_features": _repo_rel(CANDIDATE_FEATURES),
        "caveats": [
            "intuition-building only",
            "samples only a few rescue/break examples per target",
            "uses fixed 500-token chunks from completed normalized full scan",
        ],
    }
    summary_path = OUTPUT_DIR / "span_hamming_500_pattern_examples_summary.json"
    readout_path = OUTPUT_DIR / "span_hamming_500_pattern_examples_readout.md"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    readout_path.write_text(_build_readout(summary, side_rows), encoding="utf-8")
    print(
        f"[span_hamming_500_pattern_examples] done pairs={len(selected_pairs)} "
        f"side_rows={len(side_rows)} output={_repo_rel(OUTPUT_DIR)}",
        flush=True,
    )
    return summary


def main() -> None:
    run_inspection()


if __name__ == "__main__":
    main()
