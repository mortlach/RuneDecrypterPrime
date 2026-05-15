from __future__ import annotations

import csv
import gzip
import json
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402


RUN_LABEL = "phaseB_span_hamming_candidate_manual_inspection_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / RUN_LABEL
REVIEW_PACK_DIR = (
    REPO_ROOT
    / "planning/projects/no_wli/40_review_summaries"
    / "phaseB_span_hamming_candidate_manual_inspection_v1_review_pack_2026-05-13"
)
REVIEW_PACK_ZIP = REVIEW_PACK_DIR.with_suffix(".zip")

HARD_PAIR_DIR = (
    REPO_ROOT
    / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1"
)
HISTORICAL_PACK = (
    REPO_ROOT
    / "planning/projects/no_wli/40_review_summaries/no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02"
)
UNIQUE_TEXT_ROWS_PATH = HISTORICAL_PACK / "historical_partial_texts/unique_partial_text_rows.csv"
HISTORICAL_PAIR_ROWS_PATH = HISTORICAL_PACK / "historical_pairwise_rescore/historical_pairwise_rescore_pairs.csv"

SNIPPET_TOKENS = 250
TOP_N = 50
PANELS = ("A_core_medium_local", "B_longer_span", "D_strict_precision")
MANUAL_FLAG_FIELDS = (
    "looks_like_local_words",
    "looks_like_order_scrambled",
    "looks_like_repetition",
    "looks_like_short_word_overmatch",
    "looks_like_periodic_or_lane_artifact",
    "looks_like_partial_plaintext",
    "label_maybe_wrong",
    "manual_comment",
)


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def ensure_under_repo(path: Path) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(REPO_ROOT):
        raise ValueError(f"path escapes repo root: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: list[str]) -> None:
    ensure_under_repo(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_jsonl_gz(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    ensure_under_repo(path)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_tokens(text: str) -> list[int]:
    return [int(part) for part in text.split() if part.strip()]


def latin_from_tokens(tokens: list[int]) -> str:
    return "".join(str(Runeglish.pos_to_latin(int(token))) for token in tokens)


def token_snippet(tokens: list[int], section: str) -> str:
    if not tokens:
        return ""
    if section == "start":
        subset = tokens[:SNIPPET_TOKENS]
    elif section == "end":
        subset = tokens[-SNIPPET_TOKENS:]
    else:
        start = max(0, (len(tokens) - SNIPPET_TOKENS) // 2)
        subset = tokens[start : start + SNIPPET_TOKENS]
    return " ".join(str(int(token)) for token in subset)


def latin_snippet(tokens: list[int], section: str) -> str:
    return latin_from_tokens(parse_tokens(token_snippet(tokens, section)))


def parse_panel_score_text(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in str(text).split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        out[key] = as_float(value)
    return out


def candidate_hash_from_id(candidate_id: str) -> str:
    prefix = "hist_text_"
    return candidate_id[len(prefix) :] if candidate_id.startswith(prefix) else candidate_id


def load_token_map(needed_hashes: set[str]) -> tuple[dict[str, list[int]], list[str]]:
    found: dict[str, list[int]] = {}
    if not UNIQUE_TEXT_ROWS_PATH.exists():
        return found, [rel(UNIQUE_TEXT_ROWS_PATH)]
    with UNIQUE_TEXT_ROWS_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            token_hash = row["partial_text_hash"]
            if token_hash not in needed_hashes:
                continue
            found[token_hash] = parse_tokens(row["token_sequence_text"])
            if len(found) == len(needed_hashes):
                break
    missing = sorted(needed_hashes - set(found))
    return found, missing


def rank_map(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    ranked = sorted(rows, key=lambda row: as_float(row.get(field)), reverse=True)
    return {str(row["candidate_id"]): idx + 1 for idx, row in enumerate(ranked)}


def best_panel_features(panel_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    best: dict[tuple[str, str], dict[str, str]] = {}
    for row in panel_rows:
        key = (row["candidate_id"], row["panel_id"])
        if key not in best or as_float(row["panel_mean_signed_effect"]) > as_float(best[key]["panel_mean_signed_effect"]):
            best[key] = row
    return best


def build_candidate_rows(
    *,
    candidate_manifest: list[dict[str, str]],
    candidate_level: list[dict[str, str]],
    panel_summary: list[dict[str, str]],
    token_map: Mapping[str, list[int]],
) -> list[dict[str, Any]]:
    by_candidate: dict[str, dict[str, Any]] = {}
    for row in candidate_manifest:
        cid = row["candidate_id"]
        by_candidate[cid] = dict(row)
        by_candidate[cid].update({"panelA_score": "", "panelB_score": "", "panelD_score": "", "chunk_count": ""})

    for row in candidate_level:
        cid = row["candidate_id"]
        if cid not in by_candidate:
            continue
        panel = row["panel_id"]
        if panel == "A_core_medium_local":
            by_candidate[cid]["panelA_score"] = row["mean_chunk_score"]
            by_candidate[cid]["chunk_count"] = row["chunk_count"]
        elif panel == "B_longer_span":
            by_candidate[cid]["panelB_score"] = row["mean_chunk_score"]
        elif panel == "D_strict_precision":
            by_candidate[cid]["panelD_score"] = row["mean_chunk_score"]

    rows = list(by_candidate.values())
    panel_a_ranks = rank_map(rows, "panelA_score")
    panel_b_ranks = rank_map(rows, "panelB_score")
    panel_d_ranks = rank_map(rows, "panelD_score")
    feature_lookup = best_panel_features(panel_summary)

    out: list[dict[str, Any]] = []
    for row in rows:
        cid = row["candidate_id"]
        token_hash = row.get("token_hash") or candidate_hash_from_id(cid)
        tokens = list(token_map.get(token_hash, []))
        panel_a_features = feature_lookup.get((cid, "A_core_medium_local"), {})
        snippet_start = token_snippet(tokens, "start")
        snippet_middle = token_snippet(tokens, "middle")
        snippet_end = token_snippet(tokens, "end")
        latin_start = latin_snippet(tokens, "start")
        latin_middle = latin_snippet(tokens, "middle")
        latin_end = latin_snippet(tokens, "end")
        out_row = {
            "candidate_id": cid,
            "label": row.get("label", ""),
            "label_confidence": row.get("label_confidence", ""),
            "source_run_id": row.get("source_run_id", ""),
            "source_file": row.get("source_file", ""),
            "candidate_rank": row.get("candidate_rank", ""),
            "current_score": row.get("current_score", ""),
            "current_score_name": row.get("current_score_name", ""),
            "truth_match_ratio": row.get("truth_match_ratio", ""),
            "panelA_score": row.get("panelA_score", ""),
            "panelB_score": row.get("panelB_score", ""),
            "panelD_score": row.get("panelD_score", ""),
            "panelA_rank": panel_a_ranks.get(cid, ""),
            "panelB_rank": panel_b_ranks.get(cid, ""),
            "panelD_rank": panel_d_ranks.get(cid, ""),
            "token_count": row.get("token_count", len(tokens)),
            "chunk_count": row.get("chunk_count", ""),
            "candidate_text_or_rune_string": f"{latin_start} ... {latin_middle} ... {latin_end}" if tokens else "",
            "latin_snippet_start": latin_start,
            "latin_snippet_middle": latin_middle,
            "latin_snippet_end": latin_end,
            "token_snippet_start": snippet_start,
            "token_snippet_middle": snippet_middle,
            "token_snippet_end": snippet_end,
            "top_supporting_span_hamming_features": panel_a_features.get("panel_top_supporting_features", ""),
            "top_warning_features": panel_a_features.get("panel_top_warning_features", ""),
            "notes": row.get("notes", ""),
            "token_hash": token_hash,
            "text_resolved": "true" if tokens else "false",
        }
        for field in MANUAL_FLAG_FIELDS:
            out_row[field] = ""
        out.append(out_row)
    return out


def load_historical_pair_metadata() -> dict[str, dict[str, str]]:
    if not HISTORICAL_PAIR_ROWS_PATH.exists():
        return {}
    return {row["pair_id"]: row for row in read_csv_rows(HISTORICAL_PAIR_ROWS_PATH)}


def panel_preferred(a_id: str, b_id: str, scores: Mapping[str, Mapping[str, float]], panel: str) -> str:
    a = scores.get(a_id, {}).get(panel, 0.0)
    b = scores.get(b_id, {}).get(panel, 0.0)
    if a > b:
        return a_id
    if b > a:
        return b_id
    return "tie"


def build_pair_rows(
    *,
    pairwise_rows: list[dict[str, str]],
    candidate_rows_by_id: Mapping[str, Mapping[str, Any]],
    historical_pair_metadata: Mapping[str, Mapping[str, str]],
) -> list[dict[str, Any]]:
    scores: dict[str, dict[str, float]] = {}
    for cid, row in candidate_rows_by_id.items():
        scores[cid] = {
            "A_core_medium_local": as_float(row.get("panelA_score")),
            "B_longer_span": as_float(row.get("panelB_score")),
            "D_strict_precision": as_float(row.get("panelD_score")),
        }

    out: list[dict[str, Any]] = []
    for row in pairwise_rows:
        a_id = row["candidate_a_id"]
        b_id = row["candidate_b_id"]
        a = candidate_rows_by_id.get(a_id, {})
        b = candidate_rows_by_id.get(b_id, {})
        panel_a_gap = scores.get(a_id, {}).get("A_core_medium_local", 0.0) - scores.get(b_id, {}).get("A_core_medium_local", 0.0)
        panel_b_gap = scores.get(a_id, {}).get("B_longer_span", 0.0) - scores.get(b_id, {}).get("B_longer_span", 0.0)
        panel_d_gap = scores.get(a_id, {}).get("D_strict_precision", 0.0) - scores.get(b_id, {}).get("D_strict_precision", 0.0)
        hist = historical_pair_metadata.get(row["pair_id"], {})
        out_row = {
            "pair_id": row["pair_id"],
            "candidate_a_id": a_id,
            "candidate_b_id": b_id,
            "truth_better_candidate_id": a_id,
            "truth_worse_candidate_id": b_id,
            "current_scorer_preferred": row.get("current_scorer_preferred", ""),
            "panelA_preferred": panel_preferred(a_id, b_id, scores, "A_core_medium_local"),
            "panelB_preferred": panel_preferred(a_id, b_id, scores, "B_longer_span"),
            "panelD_preferred": panel_preferred(a_id, b_id, scores, "D_strict_precision"),
            "panelA_gap": f"{panel_a_gap:.12g}",
            "panelB_gap": f"{panel_b_gap:.12g}",
            "panelD_gap": f"{panel_d_gap:.12g}",
            "current_score_gap": row.get("current_score_margin", ""),
            "current_scorer_correct": row.get("current_scorer_correct", ""),
            "panelA_correct": "true" if panel_a_gap > 0 else ("false" if panel_a_gap < 0 else "tie"),
            "panelA_rescue": row.get("span_hamming_rescues_current_misrank", ""),
            "panelA_break": row.get("span_hamming_breaks_current_correct", ""),
            "truth_better_text_snippet": a.get("latin_snippet_start", ""),
            "truth_worse_text_snippet": b.get("latin_snippet_start", ""),
            "truth_better_token_snippet": a.get("token_snippet_start", ""),
            "truth_worse_token_snippet": b.get("token_snippet_start", ""),
            "truth_better_truth_match_ratio": row.get("winner_truth_match", a.get("truth_match_ratio", "")),
            "truth_worse_truth_match_ratio": row.get("challenger_truth_match", b.get("truth_match_ratio", "")),
            "truth_better_panelA": f"{scores.get(a_id, {}).get('A_core_medium_local', 0.0):.12g}",
            "truth_worse_panelA": f"{scores.get(b_id, {}).get('A_core_medium_local', 0.0):.12g}",
            "truth_better_current_score": row.get("winner_current_score", a.get("current_score", "")),
            "truth_worse_current_score": row.get("challenger_current_score", b.get("current_score", "")),
            "truth_better_repeated_3gram_rate": hist.get("winner_repeated_3gram_rate", ""),
            "truth_worse_repeated_3gram_rate": hist.get("challenger_repeated_3gram_rate", ""),
            "truth_better_repeated_4gram_rate": hist.get("winner_repeated_4gram_rate", ""),
            "truth_worse_repeated_4gram_rate": hist.get("challenger_repeated_4gram_rate", ""),
            "manual_review_notes": "",
        }
        for field in MANUAL_FLAG_FIELDS:
            out_row[field] = ""
        out.append(out_row)
    return out


def subset_rows(candidate_rows: list[dict[str, Any]], pair_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    bad_labels = {"known_bad", "likely_bad"}
    good_labels = {"known_good", "likely_good"}
    return {
        "top_panelA_false_positives.csv": sorted(
            [row for row in candidate_rows if row["label"] in bad_labels],
            key=lambda row: as_float(row["panelA_score"]),
            reverse=True,
        )[:TOP_N],
        "top_panelA_true_positives.csv": sorted(
            [row for row in candidate_rows if row["label"] in good_labels],
            key=lambda row: as_float(row["panelA_score"]),
            reverse=True,
        )[:TOP_N],
        "high_current_score_bad_candidates.csv": sorted(
            [row for row in candidate_rows if row["label"] in bad_labels],
            key=lambda row: as_float(row["current_score"]),
            reverse=True,
        )[:TOP_N],
        "panelA_rescues.csv": sorted(
            [row for row in pair_rows if row["panelA_rescue"] == "true"],
            key=lambda row: as_float(row["panelA_gap"]),
            reverse=True,
        )[:TOP_N],
        "panelA_breaks.csv": sorted(
            [row for row in pair_rows if row["panelA_break"] == "true"],
            key=lambda row: as_float(row["panelA_gap"]),
        )[:TOP_N],
    }


def write_markdown_reviews(candidate_rows: list[dict[str, Any]], pair_rows: list[dict[str, Any]]) -> None:
    false_pos = sorted(
        [row for row in candidate_rows if row["label"] in {"known_bad", "likely_bad"}],
        key=lambda row: as_float(row["panelA_score"]),
        reverse=True,
    )[:20]
    rescues = sorted(
        [row for row in pair_rows if row["panelA_rescue"] == "true"],
        key=lambda row: as_float(row["panelA_gap"]),
        reverse=True,
    )[:20]
    breaks = sorted(
        [row for row in pair_rows if row["panelA_break"] == "true"],
        key=lambda row: as_float(row["panelA_gap"]),
    )[:20]

    candidate_lines = ["# Candidate Manual Inspection Highlights", ""]
    for row in false_pos:
        candidate_lines.extend(
            [
                f"## {row['candidate_id']}",
                "",
                f"- label: {row['label']}",
                f"- Panel A: {row['panelA_score']}",
                f"- truth: {row['truth_match_ratio']}",
                f"- current score: {row['current_score']}",
                "",
                row["latin_snippet_start"],
                "",
            ]
        )
    (OUTPUT_DIR / "candidate_manual_inspection.md").write_text("\n".join(candidate_lines), encoding="utf-8")

    pair_lines = ["# Pair Manual Inspection Highlights", ""]
    for title, rows in (("Rescues", rescues), ("Breaks", breaks)):
        pair_lines.extend([f"## {title}", ""])
        for row in rows:
            pair_lines.extend(
                [
                    f"### {row['pair_id']}",
                    "",
                    f"- Panel A gap: {row['panelA_gap']}",
                    f"- current correct: {row['current_scorer_correct']}",
                    f"- rescue: {row['panelA_rescue']}",
                    f"- break: {row['panelA_break']}",
                    "",
                    "Truth better:",
                    row["truth_better_text_snippet"],
                    "",
                    "Truth worse:",
                    row["truth_worse_text_snippet"],
                    "",
                ]
            )
    (OUTPUT_DIR / "pair_manual_inspection.md").write_text("\n".join(pair_lines), encoding="utf-8")


def write_readout(
    *,
    candidate_rows: list[dict[str, Any]],
    pair_rows: list[dict[str, Any]],
    subsets: Mapping[str, list[dict[str, Any]]],
    missing: list[str],
) -> None:
    label_counts = Counter(str(row.get("label", "")) for row in candidate_rows)
    readable_candidates = sum(1 for row in candidate_rows if row.get("text_resolved") == "true")
    resolved_pairs = sum(1 for row in pair_rows if row.get("truth_better_text_snippet") and row.get("truth_worse_text_snippet"))
    false_pos = subsets["top_panelA_false_positives.csv"][:10]
    rescues = subsets["panelA_rescues.csv"][:10]
    breaks = subsets["panelA_breaks.csv"][:10]

    repeated_breaks = [as_float(row.get("truth_worse_repeated_3gram_rate")) - as_float(row.get("truth_better_repeated_3gram_rate")) for row in pair_rows if row.get("panelA_break") == "true"]
    repeated_rescues = [as_float(row.get("truth_worse_repeated_3gram_rate")) - as_float(row.get("truth_better_repeated_3gram_rate")) for row in pair_rows if row.get("panelA_rescue") == "true"]

    lines = [
        "# PhaseB Span-Hamming Candidate Manual Inspection v1",
        "",
        f"Created UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Scope",
        "",
        f"- Candidates with readable text/token snippets: {readable_candidates} / {len(candidate_rows)}",
        f"- Pairs with both candidate texts resolved: {resolved_pairs} / {len(pair_rows)}",
        f"- Label counts: {dict(sorted(label_counts.items()))}",
        f"- Snippet size: {SNIPPET_TOKENS} tokens from start, middle, and end",
        "- Full token and latin renderings are in `candidate_full_texts.jsonl.gz`.",
        "- No scoring weights, scorer defaults, ranking policy, calibration outputs, or Stage 4 run were changed.",
        "",
        "## Highest Panel A Known/Likely Bad Candidates",
        "",
    ]
    for row in false_pos:
        lines.append(
            f"- {row['candidate_id']}: label={row['label']} PanelA={row['panelA_score']} truth={row['truth_match_ratio']} current={row['current_score']}"
        )
    lines.extend(["", "## Largest Panel A Rescues", ""])
    for row in rescues:
        lines.append(
            f"- {row['pair_id']}: gap={row['panelA_gap']} truth_better={row['truth_better_truth_match_ratio']} truth_worse={row['truth_worse_truth_match_ratio']}"
        )
    lines.extend(["", "## Largest Panel A Breaks", ""])
    for row in breaks:
        lines.append(
            f"- {row['pair_id']}: gap={row['panelA_gap']} truth_better={row['truth_better_truth_match_ratio']} truth_worse={row['truth_worse_truth_match_ratio']}"
        )
    lines.extend(["", "## Automatic Pattern Clues", ""])
    if repeated_breaks:
        lines.append(
            f"- Breaks mean truth-worse minus truth-better repeated-3gram rate: {statistics.fmean(repeated_breaks):.6g}"
        )
    if repeated_rescues:
        lines.append(
            f"- Rescues mean truth-worse minus truth-better repeated-3gram rate: {statistics.fmean(repeated_rescues):.6g}"
        )
    lines.append("- Manual annotation columns are blank for human review.")
    lines.extend(["", "## Missing Or Incomplete Sources", ""])
    if missing:
        for item in missing:
            lines.append(f"- {item}")
    else:
        lines.append("- none observed")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- candidate_manual_inspection.csv",
            "- pair_manual_inspection.csv",
            "- top_panelA_false_positives.csv",
            "- top_panelA_true_positives.csv",
            "- panelA_rescues.csv",
            "- panelA_breaks.csv",
            "- high_current_score_bad_candidates.csv",
            "- candidate_full_texts.jsonl.gz",
        ]
    )
    (OUTPUT_DIR / "readout.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_review_pack() -> None:
    if REVIEW_PACK_DIR.exists():
        shutil.rmtree(REVIEW_PACK_DIR)
    REVIEW_PACK_DIR.mkdir(parents=True, exist_ok=True)
    for name in (
        "config.json",
        "input_manifest.json",
        "readout.md",
        "candidate_manual_inspection.csv",
        "pair_manual_inspection.csv",
        "top_panelA_false_positives.csv",
        "top_panelA_true_positives.csv",
        "panelA_rescues.csv",
        "panelA_breaks.csv",
        "high_current_score_bad_candidates.csv",
        "candidate_manual_inspection.md",
        "pair_manual_inspection.md",
        "candidate_full_texts.jsonl.gz",
    ):
        shutil.copy2(OUTPUT_DIR / name, REVIEW_PACK_DIR / name)
    if REVIEW_PACK_ZIP.exists():
        REVIEW_PACK_ZIP.unlink()
    shutil.make_archive(str(REVIEW_PACK_DIR), "zip", REVIEW_PACK_DIR)


def main() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    required_paths = {
        "candidate_manifest_resolved": HARD_PAIR_DIR / "candidate_manifest_resolved.csv",
        "candidate_level_summary": HARD_PAIR_DIR / "candidate_level_summary.csv",
        "candidate_panel_summary": HARD_PAIR_DIR / "candidate_panel_summary.csv",
        "pairwise_road_test_summary": HARD_PAIR_DIR / "pairwise_road_test_summary.csv",
        "hard_pair_manifest": HARD_PAIR_DIR / "hard_pair_manifest.csv",
        "bad_candidate_separation_summary": HARD_PAIR_DIR / "bad_candidate_separation_summary.csv",
        "unique_partial_text_rows": UNIQUE_TEXT_ROWS_PATH,
        "historical_pair_rows": HISTORICAL_PAIR_ROWS_PATH,
    }
    missing_sources = [f"{name}: {rel(path)}" for name, path in required_paths.items() if not path.exists()]
    if missing_sources:
        write_json(OUTPUT_DIR / "input_manifest.json", {"missing_sources": missing_sources})
        raise FileNotFoundError(f"missing required sources: {missing_sources}")

    candidate_manifest = read_csv_rows(required_paths["candidate_manifest_resolved"])
    candidate_level = read_csv_rows(required_paths["candidate_level_summary"])
    candidate_panel = read_csv_rows(required_paths["candidate_panel_summary"])
    pairwise_rows = read_csv_rows(required_paths["pairwise_road_test_summary"])
    historical_pair_metadata = load_historical_pair_metadata()

    needed_hashes = {str(row.get("token_hash") or candidate_hash_from_id(row["candidate_id"])) for row in candidate_manifest}
    token_map, missing_hashes = load_token_map(needed_hashes)
    missing_notes = [f"missing token hash in unique_partial_text_rows.csv: {token_hash}" for token_hash in missing_hashes]

    config = {
        "run_label": RUN_LABEL,
        "report_only": True,
        "snippet_tokens": SNIPPET_TOKENS,
        "top_n": TOP_N,
        "manual_flag_fields": MANUAL_FLAG_FIELDS,
        "hard_pair_output_dir": rel(HARD_PAIR_DIR),
        "unique_text_rows": rel(UNIQUE_TEXT_ROWS_PATH),
        "full_texts_file": "candidate_full_texts.jsonl.gz",
        "scorer_policy": "inspection/report only; no production weights/defaults/ranking/calibration changes",
    }
    write_json(OUTPUT_DIR / "config.json", config)
    write_json(
        OUTPUT_DIR / "input_manifest.json",
        {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "inputs": {name: {"path": rel(path), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0} for name, path in required_paths.items()},
            "candidate_rows_loaded": len(candidate_manifest),
            "pair_rows_loaded": len(pairwise_rows),
            "needed_token_hashes": len(needed_hashes),
            "resolved_token_hashes": len(token_map),
            "missing_sources": missing_sources,
            "missing_token_hashes": missing_hashes,
        },
    )

    candidate_rows = build_candidate_rows(
        candidate_manifest=candidate_manifest,
        candidate_level=candidate_level,
        panel_summary=candidate_panel,
        token_map=token_map,
    )
    candidate_by_id = {row["candidate_id"]: row for row in candidate_rows}
    pair_rows = build_pair_rows(
        pairwise_rows=pairwise_rows,
        candidate_rows_by_id=candidate_by_id,
        historical_pair_metadata=historical_pair_metadata,
    )

    candidate_fields = [
        "candidate_id",
        "label",
        "label_confidence",
        "source_run_id",
        "source_file",
        "candidate_rank",
        "current_score",
        "current_score_name",
        "truth_match_ratio",
        "panelA_score",
        "panelB_score",
        "panelD_score",
        "panelA_rank",
        "panelB_rank",
        "panelD_rank",
        "token_count",
        "chunk_count",
        "candidate_text_or_rune_string",
        "latin_snippet_start",
        "latin_snippet_middle",
        "latin_snippet_end",
        "token_snippet_start",
        "token_snippet_middle",
        "token_snippet_end",
        "top_supporting_span_hamming_features",
        "top_warning_features",
        "notes",
        "token_hash",
        "text_resolved",
        *MANUAL_FLAG_FIELDS,
    ]
    pair_fields = [
        "pair_id",
        "candidate_a_id",
        "candidate_b_id",
        "truth_better_candidate_id",
        "truth_worse_candidate_id",
        "current_scorer_preferred",
        "panelA_preferred",
        "panelB_preferred",
        "panelD_preferred",
        "panelA_gap",
        "panelB_gap",
        "panelD_gap",
        "current_score_gap",
        "current_scorer_correct",
        "panelA_correct",
        "panelA_rescue",
        "panelA_break",
        "truth_better_text_snippet",
        "truth_worse_text_snippet",
        "truth_better_token_snippet",
        "truth_worse_token_snippet",
        "truth_better_truth_match_ratio",
        "truth_worse_truth_match_ratio",
        "truth_better_panelA",
        "truth_worse_panelA",
        "truth_better_current_score",
        "truth_worse_current_score",
        "truth_better_repeated_3gram_rate",
        "truth_worse_repeated_3gram_rate",
        "truth_better_repeated_4gram_rate",
        "truth_worse_repeated_4gram_rate",
        "manual_review_notes",
        *MANUAL_FLAG_FIELDS,
    ]
    write_csv(OUTPUT_DIR / "candidate_manual_inspection.csv", candidate_rows, candidate_fields)
    write_csv(OUTPUT_DIR / "pair_manual_inspection.csv", pair_rows, pair_fields)

    full_text_rows = []
    for row in candidate_rows:
        token_hash = row["token_hash"]
        tokens = token_map.get(token_hash, [])
        full_text_rows.append(
            {
                "candidate_id": row["candidate_id"],
                "token_hash": token_hash,
                "label": row["label"],
                "truth_match_ratio": row["truth_match_ratio"],
                "panelA_score": row["panelA_score"],
                "current_score": row["current_score"],
                "token_count": len(tokens),
                "token_sequence_text": " ".join(str(int(token)) for token in tokens),
                "latin_render": latin_from_tokens(tokens),
            }
        )
    write_jsonl_gz(OUTPUT_DIR / "candidate_full_texts.jsonl.gz", full_text_rows)

    subsets = subset_rows(candidate_rows, pair_rows)
    for name, rows in subsets.items():
        fields = pair_fields if name in {"panelA_rescues.csv", "panelA_breaks.csv"} else candidate_fields
        write_csv(OUTPUT_DIR / name, rows, fields)

    write_markdown_reviews(candidate_rows, pair_rows)
    write_readout(candidate_rows=candidate_rows, pair_rows=pair_rows, subsets=subsets, missing=missing_notes)
    copy_review_pack()

    print(f"[{RUN_LABEL}] complete candidates={len(candidate_rows)} pairs={len(pair_rows)} resolved_texts={len(token_map)}")
    print(f"[{RUN_LABEL}] output_dir={rel(OUTPUT_DIR)}")
    print(f"[{RUN_LABEL}] review_pack={rel(REVIEW_PACK_ZIP)}")


if __name__ == "__main__":
    main()
