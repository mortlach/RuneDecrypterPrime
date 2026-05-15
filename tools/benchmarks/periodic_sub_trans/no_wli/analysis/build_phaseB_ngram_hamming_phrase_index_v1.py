from __future__ import annotations

import csv
import gzip
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.reference import (  # noqa: E402
    PhraseEntry,
    PhraseProfile,
    phrase_entry_from_asset_row,
)


RUN_LABEL = "phaseB_ngram_hamming_phrase_index_v1"
ASSET_ROOT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_index_v1/20260514T044954Z__phaseB_filtered_ngram_index_v1"
OUTPUT_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_phrase_index_v1"
DIRECTIONS = ("fwd", "rev")
DICTIONARY_CUTS = ("normal", "strict")
ORDERS = (2, 3, 4, 5)
ASSET_MODE = "sample"
SAMPLE_LINE_LIMIT_PER_ORDER = 25000
FULL_ASSET_AVAILABLE = False
PROFILES = (
    PhraseProfile("P0_exact_short", "fwd", (2, 3, 4), ("normal", "strict"), 5, 0, 0),
    PhraseProfile("P1_word_analogue_len7_hd2", "fwd", (2, 3, 4), ("normal", "strict"), 7, 2, 2),
    PhraseProfile("P2_conservative_len8_hd2", "fwd", (2, 3, 4), ("normal", "strict"), 8, 2, 1),
    PhraseProfile("P3_longer_phrase_len10_hd3", "fwd", (3, 4), ("normal", "strict"), 10, 3, 2),
    PhraseProfile("P4_strict_long_len10_hd2", "fwd", (3, 4), ("strict",), 10, 2, 1),
    PhraseProfile("P5_order5_diagnostic_len12_hd3", "fwd", (5,), ("normal", "strict"), 12, 3, 2),
)


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def asset_path(dictionary_cut: str, direction: str, order: int) -> Path:
    return REPO_ROOT / ASSET_ROOT_REL / f"{dictionary_cut}_{direction}" / f"ngram{order}.csv.gz"


def phrase_identity(entry: PhraseEntry) -> tuple[str, str, int, tuple[tuple[int, ...], ...]]:
    return (entry.direction, entry.dictionary_cut, entry.ngram_order, entry.word_token_ids)


def phrase_id_for_identity(identity: tuple[str, str, int, tuple[tuple[int, ...], ...]]) -> str:
    direction, dictionary_cut, order, word_token_ids = identity
    payload = json.dumps(word_token_ids, separators=(",", ":"))
    return f"{direction}|{dictionary_cut}|{order}|{payload}"


def quantile(values: list[int], fraction: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    pos = (len(ordered) - 1) * fraction
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return float(ordered[low])
    weight = pos - low
    return float(ordered[low] * (1.0 - weight) + ordered[high] * weight)


def entry_to_json(entry: PhraseEntry, *, duplicate_row_count: int, source_asset_ids: list[str], top_latin_examples: list[str]) -> dict[str, Any]:
    return {
        "phrase_id": entry.phrase_id,
        "direction": entry.direction,
        "dictionary_cut": entry.dictionary_cut,
        "ngram_order": entry.ngram_order,
        "word_token_ids": entry.word_token_ids,
        "rune_token_ids": entry.rune_token_ids,
        "word_lengths": entry.word_lengths,
        "phrase_token_length": entry.phrase_token_length,
        "count": entry.count,
        "sum_count": entry.count,
        "max_count": entry.count,
        "log_count": entry.log_count,
        "max_log_count": entry.log_count,
        "phrase_count": entry.phrase_count,
        "top_latin_ngram": entry.top_latin_ngram,
        "duplicate_row_count": duplicate_row_count,
        "source_asset_ids": source_asset_ids,
        "latin_examples": top_latin_examples,
    }


def load_and_collapse_assets() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    collapsed: dict[tuple[str, str, int, tuple[tuple[int, ...], ...]], dict[str, Any]] = {}
    summaries: list[dict[str, Any]] = []
    for dictionary_cut in DICTIONARY_CUTS:
        for direction in DIRECTIONS:
            for order in ORDERS:
                path = asset_path(dictionary_cut, direction, order)
                raw_rows = 0
                invalid_rows = 0
                if not path.exists():
                    summaries.append(
                        {
                            "asset_path": repo_rel(path),
                            "exists": False,
                            "dictionary_cut": dictionary_cut,
                            "direction": direction,
                            "ngram_order": order,
                            "raw_rows": 0,
                            "valid_rows": 0,
                            "invalid_rows": 0,
                            "unique_phrase_entries": 0,
                        }
                    )
                    continue
                before = len(collapsed)
                with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
                    reader = csv.DictReader(handle)
                    for row in reader:
                        raw_rows += 1
                        try:
                            entry = phrase_entry_from_asset_row(row)
                        except Exception:
                            invalid_rows += 1
                            continue
                        identity = phrase_identity(entry)
                        phrase_id = phrase_id_for_identity(identity)
                        source_asset_id = f"{dictionary_cut}_{direction}/ngram{order}.csv.gz"
                        current = collapsed.get(identity)
                        examples = []
                        try:
                            examples = json.loads(row.get("latin_examples", "[]"))
                        except json.JSONDecodeError:
                            examples = []
                        if current is None:
                            collapsed[identity] = {
                                "entry": PhraseEntry(
                                    phrase_id=phrase_id,
                                    direction=entry.direction,
                                    dictionary_cut=entry.dictionary_cut,
                                    ngram_order=entry.ngram_order,
                                    word_token_ids=entry.word_token_ids,
                                    rune_token_ids=entry.rune_token_ids,
                                    count=entry.count,
                                    log_count=entry.log_count,
                                    phrase_count=entry.phrase_count,
                                    top_latin_ngram=entry.top_latin_ngram,
                                ),
                                "duplicate_row_count": 0,
                                "source_asset_ids": {source_asset_id},
                                "latin_examples": list(examples[:5]),
                                "max_count": entry.count,
                            }
                        else:
                            current["duplicate_row_count"] += 1
                            current["source_asset_ids"].add(source_asset_id)
                            current["max_count"] = max(float(current["max_count"]), entry.count)
                            existing_examples = current["latin_examples"]
                            for example in examples:
                                if example not in existing_examples and len(existing_examples) < 5:
                                    existing_examples.append(example)
                            existing = current["entry"]
                            summed_count = existing.count + entry.count
                            if entry.log_count > existing.log_count:
                                top_entry = entry
                            else:
                                top_entry = existing
                            current["entry"] = PhraseEntry(
                                phrase_id=phrase_id,
                                direction=existing.direction,
                                dictionary_cut=existing.dictionary_cut,
                                ngram_order=existing.ngram_order,
                                word_token_ids=existing.word_token_ids,
                                rune_token_ids=existing.rune_token_ids,
                                count=summed_count,
                                log_count=max(existing.log_count, entry.log_count),
                                phrase_count=existing.phrase_count + entry.phrase_count,
                                top_latin_ngram=top_entry.top_latin_ngram,
                            )
                summaries.append(
                    {
                        "asset_path": repo_rel(path),
                        "exists": True,
                        "dictionary_cut": dictionary_cut,
                        "direction": direction,
                        "ngram_order": order,
                        "raw_rows": raw_rows,
                        "valid_rows": raw_rows - invalid_rows,
                        "invalid_rows": invalid_rows,
                        "unique_phrase_entries": len(collapsed) - before,
                    }
                )

    rows: list[dict[str, Any]] = []
    for current in collapsed.values():
        row = entry_to_json(
            current["entry"],
            duplicate_row_count=int(current["duplicate_row_count"]),
            source_asset_ids=sorted(current["source_asset_ids"]),
            top_latin_examples=list(current["latin_examples"]),
        )
        row["max_count"] = float(current["max_count"])
        rows.append(row)
    rows.sort(key=lambda row: (row["direction"], row["dictionary_cut"], row["ngram_order"], row["phrase_id"]))
    return rows, summaries


def build_profile_eligibility_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary_rows: list[dict[str, Any]] = []
    for profile in PROFILES:
        for direction in DIRECTIONS:
            for dictionary_cut in DICTIONARY_CUTS:
                for order in ORDERS:
                    lengths = [
                        int(row["phrase_token_length"])
                        for row in rows
                        if row["direction"] == direction
                        and direction == profile.direction
                        and row["dictionary_cut"] == dictionary_cut
                        and int(row["ngram_order"]) == order
                        and order in profile.orders
                        and dictionary_cut in profile.dictionary_cuts
                        and int(row["phrase_token_length"]) >= profile.min_phrase_token_length
                    ]
                    summary_rows.append(
                        {
                            "profile_id": profile.profile_id,
                            "direction": direction,
                            "dictionary_cut": dictionary_cut,
                            "ngram_order": order,
                            "asset_mode": ASSET_MODE,
                            "eligible_phrase_entries": len(lengths),
                            "min_profile_phrase_token_length": profile.min_phrase_token_length,
                            "max_total_phrase_hd": profile.max_total_phrase_hd,
                            "max_word_hd": profile.max_word_hd,
                            "min_phrase_token_length": min(lengths) if lengths else 0,
                            "max_phrase_token_length": max(lengths) if lengths else 0,
                            "q05_phrase_token_length": quantile(lengths, 0.05),
                            "q50_phrase_token_length": quantile(lengths, 0.50),
                            "q95_phrase_token_length": quantile(lengths, 0.95),
                            "mean_phrase_token_length": (sum(lengths) / len(lengths) if lengths else 0.0),
                        }
                    )
    return summary_rows


def write_outputs(rows: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> dict[str, Any]:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    phrase_index_path = output_dir / "phrase_index.jsonl.gz"
    ensure_under_repo(phrase_index_path)
    with gzip.open(phrase_index_path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    summary_path = output_dir / "phrase_index_asset_summary.csv"
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "asset_path",
            "exists",
            "dictionary_cut",
            "direction",
            "ngram_order",
            "raw_rows",
            "valid_rows",
            "invalid_rows",
            "unique_phrase_entries",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summaries)

    profile_summary_rows = build_profile_eligibility_summary(rows)
    profile_summary_path = output_dir / "phrase_profile_eligibility_summary.csv"
    with profile_summary_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "profile_id",
            "direction",
            "dictionary_cut",
            "ngram_order",
            "asset_mode",
            "eligible_phrase_entries",
            "min_profile_phrase_token_length",
            "max_total_phrase_hd",
            "max_word_hd",
            "min_phrase_token_length",
            "max_phrase_token_length",
            "q05_phrase_token_length",
            "q50_phrase_token_length",
            "q95_phrase_token_length",
            "mean_phrase_token_length",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(profile_summary_rows)

    core_fwd_invalid_row_count = sum(
        int(row["invalid_rows"])
        for row in summaries
        if row["direction"] == "fwd" and int(row["ngram_order"]) in (2, 3, 4)
    )
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if rows and core_fwd_invalid_row_count == 0 else "blocked",
        "blocked_reason": "" if rows and core_fwd_invalid_row_count == 0 else "invalid core FWD asset rows or empty phrase index",
        "asset_root": ASSET_ROOT_REL,
        "asset_mode": ASSET_MODE,
        "sample_line_limit_per_order": SAMPLE_LINE_LIMIT_PER_ORDER,
        "full_asset_available": FULL_ASSET_AVAILABLE,
        "phrase_identity_key": ["direction", "dictionary_cut", "ngram_order", "canonical_word_token_ids"],
        "phrase_index_path": repo_rel(phrase_index_path),
        "asset_summary_path": repo_rel(summary_path),
        "profile_eligibility_summary_path": repo_rel(profile_summary_path),
        "phrase_entry_count": len(rows),
        "core_fwd_invalid_row_count": core_fwd_invalid_row_count,
        "invalid_rows_block_core_fwd": True,
        "asset_summaries": summaries,
        "profile_eligibility_summary": profile_summary_rows,
    }
    (output_dir / "phrase_index_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    readout = [
        "# PhaseB N-Gram Hamming Phrase Index v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- phrase entries: `{manifest['phrase_entry_count']}`",
        f"- phrase identity: `{', '.join(manifest['phrase_identity_key'])}`",
        f"- asset mode: `{ASSET_MODE}`",
        "",
        "## Files",
        "",
        "- `phrase_index.jsonl.gz`",
        "- `phrase_index_manifest.json`",
        "- `phrase_index_asset_summary.csv`",
        "- `phrase_profile_eligibility_summary.csv`",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")
    return manifest


def build_phrase_index() -> dict[str, Any]:
    rows, summaries = load_and_collapse_assets()
    return write_outputs(rows, summaries)


def main() -> None:
    manifest = build_phrase_index()
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] phrase_entries={manifest['phrase_entry_count']}")


if __name__ == "__main__":
    main()
