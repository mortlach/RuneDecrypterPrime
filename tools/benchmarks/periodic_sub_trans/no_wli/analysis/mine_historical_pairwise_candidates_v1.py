from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


RUN_LABEL = "historical_pairwise_candidate_mining_v1"
TRUTH_GAP_THRESHOLD = 0.05
INPUT_OCCURRENCES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_partial_text_review_v1/partial_text_occurrences.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_pairwise_candidate_mining_v1"
)
REVIEW_PACK_DIR_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02"
)
REVIEW_PACK_ZIP_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02.zip"
)
PAIR_ROWS_FIELDS = (
    "pair_id",
    "artifact_path",
    "token_count",
    "fixture_seed",
    "search_seed",
    "text_a_hash",
    "text_b_hash",
    "candidate_a_hash",
    "candidate_b_hash",
    "truth_a",
    "truth_b",
    "stored_score_a",
    "stored_score_b",
    "truth_gap_abs",
    "stored_score_gap_abs",
    "truth_better_text_hash",
    "stored_score_better_text_hash",
    "stored_score_correct",
    "stored_score_misranked",
    "text_pair_key",
    "candidate_hash_pair_key",
    "repeated_3gram_a",
    "repeated_3gram_b",
    "repeated_4gram_a",
    "repeated_4gram_b",
    "repeated_5gram_a",
    "repeated_5gram_b",
    "repeated_6gram_a",
    "repeated_6gram_b",
)
UNIQUE_TEXT_PAIR_FIELDS = (
    "text_pair_key",
    "occurrence_count",
    "stored_score_correct",
    "stored_score_misranked",
    "artifact_count",
    "candidate_hash_pair_count",
    "fixture_search_count",
    "max_truth_gap_abs",
    "max_stored_score_gap_abs",
    "truth_better_text_hash",
    "truth_worse_text_hash",
    "repeated_3gram_truth_better",
    "repeated_3gram_truth_worse",
    "repeated_3gram_prefers_truth_better",
    "repeated_4gram_truth_better",
    "repeated_4gram_truth_worse",
    "repeated_4gram_prefers_truth_better",
    "repeated_5gram_truth_better",
    "repeated_5gram_truth_worse",
    "repeated_5gram_prefers_truth_better",
    "repeated_6gram_truth_better",
    "repeated_6gram_truth_worse",
    "repeated_6gram_prefers_truth_better",
    "example_artifacts",
    "example_candidate_hash_pairs",
)


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


REPO_ROOT = _find_repo_root()
INPUT_OCCURRENCES = REPO_ROOT / INPUT_OCCURRENCES_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL
REVIEW_PACK_DIR = REPO_ROOT / REVIEW_PACK_DIR_REL
REVIEW_PACK_ZIP = REPO_ROOT / REVIEW_PACK_ZIP_REL


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


def _as_int_text(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return ""


def _token_values(token_sequence_text: str) -> list[int]:
    tokens = [int(part) for part in token_sequence_text.split()]
    if not tokens or any(token < 0 or token > 28 for token in tokens):
        raise ValueError("token_sequence_text must contain numeric base-29 values")
    return tokens


def repeated_ngram_rate(token_sequence_text: str, ngram_size: int) -> float:
    tokens = _token_values(token_sequence_text)
    if len(tokens) < ngram_size:
        return 0.0
    windows = [tuple(tokens[idx : idx + ngram_size]) for idx in range(len(tokens) - ngram_size + 1)]
    counts = Counter(windows)
    repeated_positions = sum(count for count in counts.values() if count > 1)
    return repeated_positions / len(windows)


def _pair_key(left: str, right: str) -> str:
    return "||".join(sorted((left, right)))


def _pair_id(*parts: Any) -> str:
    payload = "||".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def _row_has_pairwise_inputs(row: Mapping[str, str]) -> bool:
    return bool(
        row.get("artifact_path")
        and row.get("candidate_hash")
        and row.get("partial_text_hash")
        and row.get("token_sequence_text")
        and row.get("score")
        and row.get("match_ratio")
    )


def load_labelled_artifact_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with INPUT_OCCURRENCES.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if not _row_has_pairwise_inputs(row):
                continue
            score = _safe_float(row.get("score"))
            truth_match = _safe_float(row.get("match_ratio"))
            if not math.isfinite(score) or not math.isfinite(truth_match):
                continue
            try:
                _token_values(str(row.get("token_sequence_text", "")))
            except ValueError:
                continue
            rows.append(
                {
                    "artifact_path": str(row.get("artifact_path", "")),
                    "data_file": str(row.get("data_file", "")),
                    "token_count": int(row.get("token_count", 0) or 0),
                    "token_sequence_text": str(row.get("token_sequence_text", "")),
                    "partial_text_hash": str(row.get("partial_text_hash", "")),
                    "candidate_hash": str(row.get("candidate_hash", "")),
                    "score": score,
                    "truth_match": truth_match,
                    "fixture_seed": _as_int_text(row.get("fixture_seed")),
                    "search_seed": _as_int_text(row.get("search_seed")),
                    "source": str(row.get("source", "")),
                    "field_name": str(row.get("field_name", "")),
                }
            )
    return rows


def dedupe_artifact_candidate_text(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for row in rows:
        key = (
            str(row.get("artifact_path", "")),
            str(row.get("candidate_hash", "")),
            str(row.get("partial_text_hash", "")),
        )
        old = deduped.get(key)
        if old is None or (
            _safe_float(row.get("truth_match")),
            _safe_float(row.get("score")),
        ) > (
            _safe_float(old.get("truth_match")),
            _safe_float(old.get("score")),
        ):
            deduped[key] = row
    return [dict(row) for row in deduped.values()]


def _candidate_pair_rows(rows: Sequence[Mapping[str, Any]]) -> Iterable[dict[str, Any]]:
    groups: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("artifact_path", "")), int(row.get("token_count", 0) or 0))].append(row)

    for (artifact_path, token_count), group_rows in sorted(groups.items()):
        if len(group_rows) < 2:
            continue
        ordered = sorted(
            group_rows,
            key=lambda row: (
                str(row.get("candidate_hash", "")),
                str(row.get("partial_text_hash", "")),
            ),
        )
        for left, right in combinations(ordered, 2):
            truth_left = _safe_float(left.get("truth_match"))
            truth_right = _safe_float(right.get("truth_match"))
            truth_gap_abs = abs(truth_left - truth_right)
            if truth_gap_abs < TRUTH_GAP_THRESHOLD:
                continue

            score_left = _safe_float(left.get("score"))
            score_right = _safe_float(right.get("score"))
            if score_left == score_right:
                continue

            truth_better = left if truth_left > truth_right else right
            score_better = left if score_left > score_right else right
            stored_score_correct = (
                str(truth_better.get("partial_text_hash")) == str(score_better.get("partial_text_hash"))
            )

            repeated: dict[str, float] = {}
            for ngram_size in (3, 4, 5, 6):
                repeated[f"repeated_{ngram_size}gram_a"] = repeated_ngram_rate(
                    str(left.get("token_sequence_text", "")),
                    ngram_size,
                )
                repeated[f"repeated_{ngram_size}gram_b"] = repeated_ngram_rate(
                    str(right.get("token_sequence_text", "")),
                    ngram_size,
                )

            yield {
                "pair_id": _pair_id(
                    artifact_path,
                    left.get("candidate_hash"),
                    left.get("partial_text_hash"),
                    right.get("candidate_hash"),
                    right.get("partial_text_hash"),
                ),
                "artifact_path": artifact_path,
                "token_count": token_count,
                "fixture_seed": str(left.get("fixture_seed") or right.get("fixture_seed") or ""),
                "search_seed": str(left.get("search_seed") or right.get("search_seed") or ""),
                "text_a_hash": str(left.get("partial_text_hash", "")),
                "text_b_hash": str(right.get("partial_text_hash", "")),
                "candidate_a_hash": str(left.get("candidate_hash", "")),
                "candidate_b_hash": str(right.get("candidate_hash", "")),
                "truth_a": truth_left,
                "truth_b": truth_right,
                "stored_score_a": score_left,
                "stored_score_b": score_right,
                "truth_gap_abs": truth_gap_abs,
                "stored_score_gap_abs": abs(score_left - score_right),
                "truth_better_text_hash": str(truth_better.get("partial_text_hash", "")),
                "stored_score_better_text_hash": str(score_better.get("partial_text_hash", "")),
                "stored_score_correct": int(stored_score_correct),
                "stored_score_misranked": int(not stored_score_correct),
                "text_pair_key": _pair_key(
                    str(left.get("partial_text_hash", "")),
                    str(right.get("partial_text_hash", "")),
                ),
                "candidate_hash_pair_key": _pair_key(
                    str(left.get("candidate_hash", "")),
                    str(right.get("candidate_hash", "")),
                ),
                **repeated,
            }


def build_pair_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{field: row.get(field, "") for field in PAIR_ROWS_FIELDS} for row in _candidate_pair_rows(rows)]


def build_unique_text_pair_rows(pair_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in pair_rows:
        groups[str(row.get("text_pair_key", ""))].append(row)

    out: list[dict[str, Any]] = []
    for text_pair_key, rows in groups.items():
        first = rows[0]
        correctness_values = {int(row.get("stored_score_correct", 0) or 0) for row in rows}
        stored_score_correct = 1 if correctness_values == {1} else 0
        stored_score_misranked = 1 if correctness_values == {0} else 0
        truth_better = str(first.get("truth_better_text_hash", ""))
        text_hashes = text_pair_key.split("||")
        truth_worse = next((text_hash for text_hash in text_hashes if text_hash != truth_better), "")
        if not truth_worse and len(text_hashes) == 2:
            truth_worse = text_hashes[1]

        def rate_for(hash_value: str, ngram_size: int) -> float:
            if hash_value == str(first.get("text_a_hash", "")):
                return _safe_float(first.get(f"repeated_{ngram_size}gram_a"))
            return _safe_float(first.get(f"repeated_{ngram_size}gram_b"))

        row = {
            "text_pair_key": text_pair_key,
            "occurrence_count": len(rows),
            "stored_score_correct": stored_score_correct,
            "stored_score_misranked": stored_score_misranked,
            "artifact_count": len({str(item.get("artifact_path", "")) for item in rows}),
            "candidate_hash_pair_count": len({str(item.get("candidate_hash_pair_key", "")) for item in rows}),
            "fixture_search_count": len(
                {
                    (str(item.get("fixture_seed", "")), str(item.get("search_seed", "")))
                    for item in rows
                }
            ),
            "max_truth_gap_abs": max(_safe_float(item.get("truth_gap_abs")) for item in rows),
            "max_stored_score_gap_abs": max(_safe_float(item.get("stored_score_gap_abs")) for item in rows),
            "truth_better_text_hash": truth_better,
            "truth_worse_text_hash": truth_worse,
            "example_artifacts": ";".join(sorted({str(item.get("artifact_path", "")) for item in rows})[:5]),
            "example_candidate_hash_pairs": ";".join(
                sorted({str(item.get("candidate_hash_pair_key", "")) for item in rows})[:5]
            ),
        }
        for ngram_size in (3, 4, 5, 6):
            better_rate = rate_for(truth_better, ngram_size)
            worse_rate = rate_for(truth_worse, ngram_size)
            row[f"repeated_{ngram_size}gram_truth_better"] = better_rate
            row[f"repeated_{ngram_size}gram_truth_worse"] = worse_rate
            row[f"repeated_{ngram_size}gram_prefers_truth_better"] = int(better_rate < worse_rate)
        out.append({field: row.get(field, "") for field in UNIQUE_TEXT_PAIR_FIELDS})

    out.sort(
        key=lambda row: (
            int(row.get("stored_score_misranked", 0) or 0),
            int(row.get("occurrence_count", 0) or 0),
            _safe_float(row.get("max_truth_gap_abs")),
        ),
        reverse=True,
    )
    return out


def _count_unique(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return len({str(row.get(key, "") or "") for row in rows if str(row.get(key, "") or "")})


def _dominant_fraction(counter: Counter[str]) -> float:
    total = sum(counter.values())
    if not total:
        return 0.0
    return max(counter.values()) / total


def _repetition_summary(unique_rows: Sequence[Mapping[str, Any]], *, status_key: str) -> dict[str, Any]:
    rows = [row for row in unique_rows if int(row.get(status_key, 0) or 0) == 1]
    out: dict[str, Any] = {"unique_pair_count": len(rows)}
    for ngram_size in (3, 4, 5, 6):
        field = f"repeated_{ngram_size}gram_prefers_truth_better"
        count = sum(int(row.get(field, 0) or 0) for row in rows)
        out[f"repeated_{ngram_size}gram_prefers_truth_better_count"] = count
        out[f"repeated_{ngram_size}gram_prefers_truth_better_fraction"] = count / len(rows) if rows else 0.0
    return out


def build_summary(
    *,
    labelled_rows: Sequence[Mapping[str, Any]],
    deduped_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    unique_text_pair_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    score_correct_rows = [row for row in pair_rows if int(row.get("stored_score_correct", 0) or 0) == 1]
    misranked_rows = [row for row in pair_rows if int(row.get("stored_score_misranked", 0) or 0) == 1]
    dominant_misranked_text = Counter(str(row.get("text_pair_key", "")) for row in misranked_rows)
    dominant_misranked_hash = Counter(str(row.get("candidate_hash_pair_key", "")) for row in misranked_rows)
    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "input_occurrences": INPUT_OCCURRENCES_REL,
        "truth_gap_threshold": TRUTH_GAP_THRESHOLD,
        "candidate_partial_occurrence_count": 69112,
        "labelled_artifact_row_count": len(labelled_rows),
        "deduped_artifact_candidate_text_count": len(deduped_rows),
        "same_artifact_same_length_truth_gap_pair_count": len(pair_rows),
        "score_tie_removed_pair_count": len(pair_rows),
        "stored_score_correct_count": len(score_correct_rows),
        "stored_score_misranked_count": len(misranked_rows),
        "stored_score_pairwise_accuracy": len(score_correct_rows) / len(pair_rows) if pair_rows else 0.0,
        "unique_numeric_text_pair_count": len(unique_text_pair_rows),
        "unique_numeric_text_pair_score_correct_count": sum(
            int(row.get("stored_score_correct", 0) or 0) for row in unique_text_pair_rows
        ),
        "unique_numeric_text_pair_misranked_count": sum(
            int(row.get("stored_score_misranked", 0) or 0) for row in unique_text_pair_rows
        ),
        "unique_candidate_hash_pair_count": _count_unique(pair_rows, "candidate_hash_pair_key"),
        "artifact_count": _count_unique(pair_rows, "artifact_path"),
        "fixture_search_cell_count": len(
            {
                (str(row.get("fixture_seed", "")), str(row.get("search_seed", "")))
                for row in pair_rows
            }
        ),
        "dominant_misranked_text_pair_fraction": _dominant_fraction(dominant_misranked_text),
        "dominant_misranked_candidate_hash_pair_fraction": _dominant_fraction(dominant_misranked_hash),
        "unique_misranked_repetition_summary": _repetition_summary(
            unique_text_pair_rows,
            status_key="stored_score_misranked",
        ),
        "unique_score_correct_repetition_summary": _repetition_summary(
            unique_text_pair_rows,
            status_key="stored_score_correct",
        ),
        "important_caveat": (
            "Scores are stored historical scores from prior artifacts, not a frozen recomputation "
            "through one current scorer version."
        ),
        "representation_rule": (
            "Pairing uses numeric rune/base-29 token sequences only through partial_text_hash and "
            "token_sequence_text. No English rendering is used."
        ),
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=True, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_readout(summary: Mapping[str, Any]) -> str:
    mis = dict(summary.get("unique_misranked_repetition_summary", {}))
    ok = dict(summary.get("unique_score_correct_repetition_summary", {}))
    lines = [
        "# Historical Pairwise Candidate Mining v1",
        "",
        "## Purpose",
        "",
        "Mine the historical numeric partial-text inventory for same-artifact candidate pairs.",
        "This is a report-only bridge between the historical review pack and future current-scorer rescoring.",
        "",
        "## Dataset Definition",
        "",
        "- `artifact_path` present.",
        "- `candidate_hash` present.",
        "- numeric rune/base-29 `token_sequence_text` present.",
        "- stored historical score present.",
        "- stored truth/match ratio present.",
        "- dedupe by artifact, candidate hash, and numeric partial-text hash.",
        f"- pair only same artifact and same token length with truth gap >= `{TRUTH_GAP_THRESHOLD}`.",
        "- remove stored-score ties.",
        "",
        "## Counts",
        "",
        f"- labelled artifact rows: `{summary['labelled_artifact_row_count']}`",
        f"- after artifact/candidate/text dedupe: `{summary['deduped_artifact_candidate_text_count']}`",
        f"- same-artifact same-length pairs after score ties: `{summary['score_tie_removed_pair_count']}`",
        f"- stored-score correct rows: `{summary['stored_score_correct_count']}`",
        f"- stored-score misranked rows: `{summary['stored_score_misranked_count']}`",
        f"- unique numeric text pairs: `{summary['unique_numeric_text_pair_count']}`",
        f"- unique candidate-hash pairs: `{summary['unique_candidate_hash_pair_count']}`",
        f"- artifacts represented: `{summary['artifact_count']}`",
        f"- fixture/search cells represented: `{summary['fixture_search_cell_count']}`",
        f"- dominant misranked text-pair fraction: `{summary['dominant_misranked_text_pair_fraction']:.4f}`",
        f"- dominant misranked candidate-hash-pair fraction: `{summary['dominant_misranked_candidate_hash_pair_fraction']:.4f}`",
        "",
        "## Repetition Signal, Unique Numeric Text Pairs",
        "",
        "Misranked pairs:",
    ]
    for ngram_size in (3, 4, 5, 6):
        count = mis.get(f"repeated_{ngram_size}gram_prefers_truth_better_count", 0)
        frac = mis.get(f"repeated_{ngram_size}gram_prefers_truth_better_fraction", 0.0)
        lines.append(f"- lower repeated {ngram_size}-gram rate favoured truth-better: `{count}/{mis.get('unique_pair_count', 0)}` = `{frac:.3f}`")
    lines.append("")
    lines.append("Score-correct controls:")
    for ngram_size in (3, 4, 5, 6):
        count = ok.get(f"repeated_{ngram_size}gram_prefers_truth_better_count", 0)
        frac = ok.get(f"repeated_{ngram_size}gram_prefers_truth_better_fraction", 0.0)
        lines.append(f"- lower repeated {ngram_size}-gram rate favoured truth-better: `{count}/{ok.get('unique_pair_count', 0)}` = `{frac:.3f}`")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The wider historical dataset supports repetition/motif structure as an enriched failure diagnostic, not as a standalone scorer.",
            "The useful motif length varies, so a future scorer probe should compare a small family of repetition and bad-window diagnostics.",
            "",
            "## Caveats",
            "",
            "- These are stored historical scores, not one frozen current-scorer recomputation.",
            "- This is not global current scorer accuracy.",
            "- Truth/match fields are evaluation-only and must not become runtime features.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs() -> dict[str, Any]:
    labelled_rows = load_labelled_artifact_rows()
    deduped_rows = dedupe_artifact_candidate_text(labelled_rows)
    pair_rows = build_pair_rows(deduped_rows)
    unique_text_pair_rows = build_unique_text_pair_rows(pair_rows)
    summary = build_summary(
        labelled_rows=labelled_rows,
        deduped_rows=deduped_rows,
        pair_rows=pair_rows,
        unique_text_pair_rows=unique_text_pair_rows,
    )
    summary["output_dir"] = OUTPUT_DIR_REL
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(OUTPUT_DIR / "historical_pairwise_candidate_rows.csv", pair_rows, PAIR_ROWS_FIELDS)
    _write_jsonl(OUTPUT_DIR / "historical_pairwise_candidate_rows.jsonl", pair_rows)
    _write_csv(OUTPUT_DIR / "historical_pairwise_unique_text_pair_rows.csv", unique_text_pair_rows, UNIQUE_TEXT_PAIR_FIELDS)
    _write_jsonl(OUTPUT_DIR / "historical_pairwise_unique_text_pair_rows.jsonl", unique_text_pair_rows)
    _write_json(OUTPUT_DIR / "historical_pairwise_candidate_summary.json", summary)
    (OUTPUT_DIR / "historical_pairwise_candidate_readout.md").write_text(
        build_readout(summary),
        encoding="utf-8",
    )
    print(
        "[historical_pairwise_candidate_mining_v1] "
        f"labelled_rows={summary['labelled_artifact_row_count']} "
        f"deduped={summary['deduped_artifact_candidate_text_count']} "
        f"pairs={summary['score_tie_removed_pair_count']} "
        f"unique_text_pairs={summary['unique_numeric_text_pair_count']} "
        f"output_dir={summary['output_dir']}",
        flush=True,
    )
    return summary


def update_review_pack() -> None:
    if not REVIEW_PACK_DIR.exists():
        return
    dst = REVIEW_PACK_DIR / "historical_pairwise_candidate_mining"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(OUTPUT_DIR, dst)

    source_dst = REVIEW_PACK_DIR / "source_scripts"
    source_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).resolve(), source_dst / Path(__file__).name)

    test_src = REPO_ROOT / "tests/tools/test_no_wli_historical_pairwise_candidate_mining_v1.py"
    if test_src.exists():
        tests_dst = REVIEW_PACK_DIR / "tests"
        tests_dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_src, tests_dst / test_src.name)

    if REVIEW_PACK_ZIP.exists():
        REVIEW_PACK_ZIP.unlink()
    shutil.make_archive(str(REVIEW_PACK_ZIP.with_suffix("")), "zip", REVIEW_PACK_DIR)
    print(
        "[historical_pairwise_candidate_mining_v1] "
        f"updated_pack={_repo_rel(REVIEW_PACK_DIR)} zip={_repo_rel(REVIEW_PACK_ZIP)}",
        flush=True,
    )


def main() -> None:
    write_outputs()
    update_review_pack()


if __name__ == "__main__":
    main()
