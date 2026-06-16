from __future__ import annotations

import pytest

from rune_decrypter_prime.data import liber_primus as lp

pytestmark = pytest.mark.tier_a


def _word_lengths_from_wli(wli: list[list[int]] | tuple[tuple[int, int], ...]) -> list[int]:
    lengths: list[int] = []
    cursor = 0
    while cursor < len(wli):
        pos, word_len = wli[cursor]
        if pos != 0:
            raise AssertionError(f"word at offset {cursor} does not start at WLI position 0")
        for expected_pos in range(word_len):
            actual_pos, actual_len = wli[cursor + expected_pos]
            assert actual_pos == expected_pos
            assert actual_len == word_len
        lengths.append(word_len)
        cursor += word_len
    return lengths


SPREADSHEET_REFERENCES = {
    "red_rune.an_end": {
        "sheet": "p56 An End",
        "expected_ct_idx": [
            25, 11, 22, 15, 4, 19, 26, 20, 3, 8, 3, 25, 5, 2, 6, 7, 7, 20, 25, 14,
            3, 24, 13, 19, 23, 23, 1, 6, 7, 20, 23, 9, 26, 11, 5, 0, 27, 25, 16,
            13, 12, 24, 2, 5, 25, 5, 23, 0, 9, 27, 18, 0, 9, 5, 21, 4, 0, 25, 10,
            4, 23, 18, 15, 26, 11, 28, 1, 21, 7, 14, 3, 19, 28, 7, 0, 4, 6, 27,
            21, 4, 17, 25, 9, 1, 15,
        ],
        "expected_word_lengths": [
            2, 3, 5, 2, 4, 3, 4, 6, 1, 4, 3, 6, 2, 2, 2, 2, 4, 2, 5, 7, 2, 4, 3,
            3, 4,
        ],
        "expected_canon_range": (56, 56),
    },
    "red_rune.parable": {
        "sheet": "p57 Parable",
        "expected_ct_idx": [
            13, 24, 4, 24, 17, 20, 18, 20, 10, 5, 18, 2, 18, 10, 9, 15, 16, 24, 4,
            16, 1, 9, 9, 18, 20, 21, 16, 3, 2, 18, 15, 1, 4, 0, 24, 5, 18, 7, 18,
            19, 1, 15, 16, 15, 8, 18, 23, 3, 1, 4, 3, 7, 9, 5, 10, 4, 5, 1, 19,
            0, 18, 4, 18, 9, 5, 18, 15, 0, 10, 9, 23, 2, 18, 23, 10, 1, 10, 9,
            10, 16, 26, 7, 10, 2, 10, 9, 24, 9, 23, 18, 19, 18, 4, 6, 18,
        ],
        "expected_word_lengths": [
            7, 4, 2, 6, 7, 2, 2, 7, 2, 4, 4, 3, 3, 14, 4, 2, 8, 5, 3, 6,
        ],
        "expected_canon_range": (57, 57),
    },
}


@pytest.mark.parametrize("source_label", sorted(SPREADSHEET_REFERENCES))
def test_solved_lp_label_payload_matches_hardcoded_spreadsheet_reference(source_label: str) -> None:
    reference = SPREADSHEET_REFERENCES[source_label]

    payload = lp.payload_from_label(source_label)

    assert payload.metadata["source_label"] == source_label
    assert payload.metadata["spreadsheet_sheet"] == reference["sheet"]
    assert tuple(payload.ct_idx) == tuple(reference["expected_ct_idx"])
    assert _word_lengths_from_wli(payload.wli) == reference["expected_word_lengths"]
    assert sum(reference["expected_word_lengths"]) == len(reference["expected_ct_idx"])
    assert (payload.metadata["canon_start"], payload.metadata["canon_end"]) == reference[
        "expected_canon_range"
    ]
    assert payload.metadata["boundary_granularity"] == "full_canon_pages"
