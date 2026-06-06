from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.bridge import NgramProfileSpec
from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseEntry
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1 as lane2,
)


RUN_LABEL = "phaseB_ngram_hamming_lane2b_length_shape_stratified_diagnostic_evidence_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_lane2b_length_shape_stratified_diagnostic_evidence_v1"
)
SELECTION_STRATEGY = "length_shape_stratified"
ROWS_PER_SHAPE = 4
MINIMUM_DISTINCT_LENGTHS = 3


def stratum_lengths(files: Sequence[Mapping[str, Any]], minimum: int) -> tuple[int, ...]:
    available = sorted({int(row["phrase_token_length"]) for row in files})
    selected: list[int] = []
    for target in (minimum, minimum + 2, minimum + 4):
        candidate = next((length for length in available if length >= target and length not in selected), None)
        if candidate is not None:
            selected.append(candidate)
    return tuple(selected)


def shape_rows_for_length(files: Sequence[Mapping[str, Any]], length: int) -> tuple[Mapping[str, Any], ...]:
    matching = [row for row in files if int(row["phrase_token_length"]) == length]
    if not matching:
        return ()
    by_common = sorted(matching, key=lambda row: (-int(row.get("phrase_count", 0)), str(row.get("path", ""))))
    common = by_common[0]
    rare = sorted(matching, key=lambda row: (int(row.get("phrase_count", 0)), str(row.get("path", ""))))[0]
    return (common,) if common["path"] == rare["path"] else (common, rare)


def select_stratified_entries(
    manifest: Mapping[str, Any],
    specs: Sequence[NgramProfileSpec],
) -> tuple[tuple[PhraseEntry, ...], list[dict[str, Any]]]:
    files = list(manifest.get("files", []))
    selected_by_key: dict[tuple[int, str, str], PhraseEntry] = {}
    rows: list[dict[str, Any]] = []
    for spec in specs:
        for order in spec.orders:
            for cut in spec.cuts:
                eligible_files = [
                    row for row in files
                    if str(row.get("direction", "")) == spec.direction
                    and int(row.get("ngram_order", -1)) == order
                    and str(row.get("dictionary_cut", "")) == cut
                    and int(row.get("phrase_token_length", 0)) >= spec.min_phrase_token_length
                ]
                lengths = stratum_lengths(eligible_files, spec.min_phrase_token_length)
                bucket: list[PhraseEntry] = []
                selected_strata: list[dict[str, Any]] = []
                for length in lengths:
                    shape_files = shape_rows_for_length(eligible_files, length)
                    stratum_entries: list[PhraseEntry] = []
                    for file_row in shape_files:
                        stratum_entries.extend(lane2.read_runtime_file_entries(file_row, ROWS_PER_SHAPE))
                    bucket.extend(stratum_entries)
                    selected_strata.append(
                        {
                            "phrase_token_length": length,
                            "shape_count": len(shape_files),
                            "selected_entry_count": len(stratum_entries),
                            "word_length_shapes": [json.loads(str(row["word_token_lengths"])) for row in shape_files],
                        }
                    )
                for entry in bucket:
                    selected_by_key[(entry.ngram_order, entry.dictionary_cut, entry.phrase_id)] = entry
                selected_lengths = sorted({entry.phrase_token_length for entry in bucket})
                blocked_reason = ""
                if len(selected_lengths) < MINIMUM_DISTINCT_LENGTHS:
                    blocked_reason = "fewer than three distinct eligible phrase-length strata selected"
                elif max(selected_lengths, default=0) <= spec.min_phrase_token_length:
                    blocked_reason = "selection did not extend beyond profile minimum phrase length"
                status = "blocked" if blocked_reason else "selected"
                rows.append(
                    {
                        "profile_id": spec.profile_id,
                        "profile_origin": spec.profile_origin,
                        "canonical_profile_id": spec.canonical_profile_id,
                        "parameter_status": spec.parameter_status,
                        "score_authority": spec.score_authority,
                        "direction": spec.direction,
                        "cut": cut,
                        "ngram_order": order,
                        "selection_strategy": SELECTION_STRATEGY,
                        "min_phrase_token_length": spec.min_phrase_token_length,
                        "max_total_phrase_hd": spec.max_total_phrase_hd,
                        "max_word_hd": spec.max_word_hd,
                        "eligible_entry_count_seen": sum(max(1, int(row.get("phrase_count", 0))) for row in eligible_files),
                        "requested_entry_count": len(bucket),
                        "minimum_required_entry_count": MINIMUM_DISTINCT_LENGTHS,
                        "selected_entry_count": len(bucket),
                        "selected_phrase_token_length_min": min(selected_lengths) if selected_lengths else "",
                        "selected_phrase_token_length_max": max(selected_lengths) if selected_lengths else "",
                        "selected_distinct_phrase_lengths": json.dumps(selected_lengths, separators=(",", ":")),
                        "selected_word_length_shapes": json.dumps(
                            [list(shape) for shape in sorted({entry.word_lengths for entry in bucket})],
                            separators=(",", ":"),
                        ),
                        "selected_strata": json.dumps(selected_strata, separators=(",", ":")),
                        "selected_phrase_ids": json.dumps([entry.phrase_id for entry in bucket], separators=(",", ":")),
                        "selection_status": status,
                        "blocked_reason": blocked_reason,
                    }
                )
    return tuple(
        sorted(selected_by_key.values(), key=lambda entry: (entry.ngram_order, entry.dictionary_cut, entry.phrase_id))
    ), rows


def run_lane2b_length_shape_stratified_diagnostic_evidence() -> dict[str, Any]:
    specs = lane2.selected_profile_specs()
    manifest = lane2.validated_fast_runtime_manifest()
    entries, selection_rows = select_stratified_entries(manifest, specs)
    blocked = [row for row in selection_rows if row["selection_status"] == "blocked"]
    if blocked:
        raise RuntimeError(
            "Lane 2B stratified selection blocked: "
            + "; ".join(f"{row['profile_id']}/{row['ngram_order']}/{row['cut']}: {row['blocked_reason']}" for row in blocked)
        )
    lane2.RUN_LABEL = RUN_LABEL
    return lane2.run_lane2_gated_diagnostic_evidence(
        output_dir=lane2.REPO_ROOT / OUTPUT_DIR_REL,
        phrase_entries=entries,
        provided_selection_rows=selection_rows,
    )


def main() -> None:
    run_lane2b_length_shape_stratified_diagnostic_evidence()


if __name__ == "__main__":
    main()
