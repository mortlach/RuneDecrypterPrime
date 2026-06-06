from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1 as lane2,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_lane2b_length_shape_stratified_diagnostic_evidence_v1 as lane2b,
)


def test_stratum_lengths_select_minimum_plus_two_and_plus_four() -> None:
    files = [{"phrase_token_length": length} for length in (7, 8, 9, 11, 13)]

    assert lane2b.stratum_lengths(files, 7) == (7, 9, 11)


def test_shape_rows_select_common_and_less_common() -> None:
    files = [
        {"phrase_token_length": 7, "phrase_count": 100, "path": "common", "word_token_lengths": "[1,6]"},
        {"phrase_token_length": 7, "phrase_count": 10, "path": "rare", "word_token_lengths": "[3,4]"},
        {"phrase_token_length": 9, "phrase_count": 1, "path": "other", "word_token_lengths": "[4,5]"},
    ]

    rows = lane2b.shape_rows_for_length(files, 7)

    assert [row["path"] for row in rows] == ["common", "rare"]


def test_stratified_selection_covers_multiple_lengths_and_shapes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(lane2, "REPO_ROOT", tmp_path)
    files = []
    for length in (7, 9, 11):
        for shape_index, shape in enumerate(((1, length - 1), (3, length - 3))):
            rel = f"runtime/len-{length}-shape-{shape_index}.npz"
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                path,
                rune_tokens=np.asarray([list(range(1, length + 1))], dtype=np.uint8),
                phrase_id=np.asarray([f"phrase-{length}-{shape_index}"], dtype=np.str_),
                word_token_lengths=np.asarray(shape, dtype=np.int16),
            )
            files.append(
                {
                    "path": rel,
                    "direction": "fwd",
                    "dictionary_cut": "normal",
                    "ngram_order": 2,
                    "phrase_token_length": length,
                    "word_token_lengths": json.dumps(list(shape)),
                    "phrase_count": 100 if shape_index == 0 else 10,
                }
            )
    spec = next(spec for spec in lane2.selected_profile_specs() if spec.profile_id == "BR_O2_soft")
    spec = spec.__class__(**{**spec.__dict__, "cuts": ("normal",)})

    entries, rows = lane2b.select_stratified_entries({"files": files}, (spec,))

    assert len(entries) == 6
    assert rows[0]["selection_status"] == "selected"
    assert json.loads(rows[0]["selected_distinct_phrase_lengths"]) == [7, 9, 11]
    assert len(json.loads(rows[0]["selected_word_length_shapes"])) == 6
