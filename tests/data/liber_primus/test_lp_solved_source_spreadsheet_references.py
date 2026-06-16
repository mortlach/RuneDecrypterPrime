from __future__ import annotations

import pytest

from rune_decrypter_prime.data import liber_primus as lp
from rune_decrypter_prime.utils.runeglish import Runeglish

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


def _reference_ct_idx_and_word_lengths(reference_text: str) -> tuple[list[int], list[int]]:
    ct_idx: list[int] = []
    word_lengths: list[int] = []
    current_word_length = 0
    for ch in reference_text:
        pos = Runeglish.rune2pos.get(ch)
        if pos is None:
            if current_word_length:
                word_lengths.append(current_word_length)
                current_word_length = 0
            continue
        ct_idx.append(pos)
        current_word_length += 1
    if current_word_length:
        word_lengths.append(current_word_length)
    return ct_idx, word_lengths


RUNE_PAGE_REFERENCES = {
    "warning": {
        "sheet": "A Warning",
        "expected_master_page_range": (0, 0),
        "reference_text": """ᚱ-ᛝᚱᚪᛗᚹ.ᛄᛁᚻᛖᛁᛡᛁ-ᛗᚫᚣᚹ-ᛠᚪᚫᚾ-/
ᚣᛖᛈ-ᛄᚫᚫᛞ.ᛁᛉᛞᛁᛋᛇ-ᛝᛚᚱᛇ-ᚦᚫᛡ/
-ᛞᛗᚫᛝ-ᛇᚫ-ᛄᛁ-ᛇᚪᛡᛁ.ᛇᛁᛈᛇ-ᚣᛁ-ᛞ/
ᛗᚫᛝᚻᛁᚳᛟᛁ.ᛠᛖᛗᚳ-ᚦᚫᛡᚪ-ᛇᚪᛡᚣ.ᛁᛉ/
ᛋᛁᚪᛖᛁᛗᛞᛁ-ᚦᚫᛡᚪ-ᚳᚠᚣ.ᚳᚫ-ᛗᚫᛇ-ᛁᚳᛖᛇ-ᚫ/
ᚪ-ᛞᛚᚱᚹᛁ-ᚣᛖᛈ-ᛄᚫᚫᛞ.ᚫᚪ-ᚣᛁ-ᚾᛁᛈᛈᚱᛟᛁ-/
ᛞᚫᛗᛇᚱᛖᛗᛁᚳ-ᛝᛖᚣᛖᛗ.ᛁᛖᚣᛁᚪ-ᚣᛁ-ᛝᚫ/
ᚪᚳᛈ-ᚫᚪ-ᚣᛁᛖᚪ-ᛗᛡᚾᛄᛁᚪᛈ.ᛠᚫᚪ-ᚱᚻᚻ-ᛖ/
ᛈ-ᛈᚱᛞᚪᛁᚳ./""",
    },
    "welcome_pilgrim": {
        "sheet": "Welcome",
        "expected_master_page_range": (1, 2),
        "reference_text": """ᚢᛠᛝᛋᛇᚠᚳ.ᚱᛇᚢᚷᛈᛠᛠ,-ᚠᚹᛉ/
ᛏᚳᛚᛠ,-ᚣᛗ-ᛠᛇ-ᛏᚳᚾᚫ-ᛝᛗᛡ/
ᛡᛗᛗᚹ-ᚫᛈᛞᛝᛡᚱ-ᚩᛠ-ᛡᛗᛁ-ᚠᚠ-/
ᛖᚢᛝ-ᛇᚢᚫ.ᚣᛈ-ᚱᚫ-ᛁᛈᚫ-ᚳᚫ-ᚫᚾᚹ-ᛒᛉᛗᛞ/
,ᚱᛡᛁ-ᚠᛈᚳ-ᛇᛇᚫᚳ-ᚱᚦᛈ-ᚠᛄᛗᚩ-ᛇᚳᚹᛡ-ᛒᚫᚹ-/
ᛒᛠᛚᛋ-ᚱᚣ-ᛄᚫ-ᚱ-ᛗᚳᚦᛇᚫᛏᚳᛈᚹ-ᛗᚷᛇ.ᚳ/
ᛝᛈᚢ-ᛇᚳ-ᚱᛖᚹ-ᛡᛈᛁ-ᛒᚣᛒᛉ-ᚠᛚᛁᚱ-ᚱᛗ-ᚳᚷ/
ᛒ-ᚣᚱ-ᚳᚠᚢ-ᚦᛈᛡᛄᚹᛏᚠᛠ-ᛄᚷᛒ-ᚫᚦᚠᚠᛠ/
ᛈᚦ,-ᛈᚠᚪᛉ-ᛄᛗᛖᛈᛝᛋᚩᛋᛗ,-ᚹᛇᛄᛚ-ᚹᛉᚢᚦ/
ᚫᚹᛗᚦ-ᛞᚣᛄᚳ-ᛋᛡᛉᚩᛝᚱᛗᛒᚹ,-ᚱᛗᛁ-ᛞᚣᛄ/
ᚳ-ᛉᚻᚢᚣᛈᛚ.ᛄᛝᚣᛗᚠᛄᛈᛇᚢᛡ,-ᚹᛇᛄ-ᛞ/
ᚹᛉᚢ-ᚪᛚᚪᛋᛗᛡᛇᛉ-ᚫᛗ-ᛡᛗᛁ-ᛈᚣ-ᚫᛗᚢᚠ/
%
.ᛗᚣ-ᚣᛇ-ᚫᛉᚱᛄᛋᛖ-ᛖᚹᚾ-ᛞᛄᚢᛋᛉᚣᛏ/
ᛖᛏᛗ-ᛇᚱᚣ-ᛞᛋ-ᚾᛖᚫᛞᛡ-ᛈᛒᚢᚾᛠᛝᛄᛡ/
ᚫ-ᛄᚷᛒ-ᛈᚦᛉ-ᛈᚾᚹᚹᛁᛚᛗᚫ.ᛚᛈᛒᚢᚩᛠᛡ-ᚱ/
ᛡᛠᚠ-ᚱᚱᛇᛄᛗ-ᚱᛗᛁ-ᛞᚣᛄ-ᚻᛚᚠᚢ-ᛄᚢᛡᛚᚦ/
ᛠ-ᛇᛄᚩᛇᚱᚱᛗ.ᚢᛗᛋᚳ-ᛠᛇ-ᛚᛁᚫᚫᚳᛚ,-ᚹᛁ-ᛚ/
ᛏ-ᛈᛖᚢᛈ-ᛠᛡᛈᚦᛏᛒ-ᛏᛗᛖ-ᚢᛚᚩᛚᛖ-ᛇᛄ/
ᛈ-ᚢᛠ-ᛚᚳᚷ-ᛠᚷᛋᛡᛏᛗ./
&
ᛒᛗᚱᚦᚠᛈ.ᚹᚱᛄ-ᚱᛉᚳ-ᛝ-ᛄᛠᛟ-ᛄᛖ/
ᚣᛗ-ᛞᚣᛄᚳᚫᛡᚢᚠ.ᛈᚠᚪ-ᚳᚳᛠ-ᚱ-/
ᚢᛄᚱ-ᚪᛗᛒᛈ-ᚷᛈᛒᚢᚾᛠᛝᚠ.ᚾᛉᛖ-/
ᚣᚷᛁᛠᛝᚢᛗᛏᚳᚷᛠᛠ-ᛄᚫ-ᛒᛈᚹᛞ.ᚠᚣ/
ᛉ-ᚫᚢᚠ-ᛇᛄᛈ-ᛉᛚᚦᛠᚪ-ᛚᚦ-ᚳᚣᚢᛡ./
ᚳᛖ-ᛚᚫᛇᛁᛉᚦᛋᚫᚻᚫ.ᚦᚣᚠᛚᚳᛖᚱ-ᛈᚠᚪᛉ-ᚱᛒᛖ-ᚫᚳᛒᚠ./""",
    },
}


SPREADSHEET_NUMERIC_REFERENCES = {
    "instruction": {
        "sheet": "An Instruction",
        "expected_ct_idx": [
            24, 9, 10, 9, 15, 16, 4, 1, 5, 16, 27, 9, 5, 7, 18, 15, 16, 27, 9,
            24, 20, 20, 2, 21, 15, 23, 10, 15, 5, 3, 1, 18, 4, 16, 4, 1, 2, 10,
            9, 15, 10, 23, 18, 26, 3, 1, 4, 15, 18, 20, 0, 0, 3, 20, 20, 3, 7,
            26, 3, 1, 4, 16, 4, 1, 2, 10, 19, 13, 3, 15, 18, 9, 3, 2, 21, 3,
            9, 3, 2, 18, 4, 15, 5, 9, 3, 7, 2, 10, 15,
        ],
        "expected_word_lengths": [
            2, 10, 7, 3, 3, 8, 4, 6, 8, 6, 4, 4, 6, 4, 2, 5, 4, 3,
        ],
        "expected_master_page_range": (54, 55),
    },
    "an_end": {
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
        "expected_master_page_range": (56, 56),
    },
    "parable": {
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
        "expected_master_page_range": (57, 57),
    },
}


@pytest.mark.parametrize("source_label", sorted(RUNE_PAGE_REFERENCES))
def test_solved_lp_label_payload_matches_hardcoded_page_reference(source_label: str) -> None:
    reference = RUNE_PAGE_REFERENCES[source_label]
    expected_ct_idx, expected_word_lengths = _reference_ct_idx_and_word_lengths(reference["reference_text"])

    payload = lp.payload_from_label(source_label)

    assert payload.metadata["requested_label"] == source_label
    assert payload.metadata["spreadsheet_sheet"] == reference["sheet"]
    assert tuple(payload.ct_idx) == tuple(expected_ct_idx)
    assert _word_lengths_from_wli(payload.wli) == expected_word_lengths
    assert sum(expected_word_lengths) == len(expected_ct_idx)
    assert (payload.metadata["master_page_start"], payload.metadata["master_page_end"]) == reference[
        "expected_master_page_range"
    ]
    assert payload.metadata["boundary_granularity"] == "full_master_pages"


@pytest.mark.parametrize("source_label", sorted(SPREADSHEET_NUMERIC_REFERENCES))
def test_solved_lp_label_payload_matches_hardcoded_numeric_reference(source_label: str) -> None:
    reference = SPREADSHEET_NUMERIC_REFERENCES[source_label]

    payload = lp.payload_from_label(source_label)

    assert payload.metadata["requested_label"] == source_label
    assert payload.metadata["spreadsheet_sheet"] == reference["sheet"]
    assert tuple(payload.ct_idx) == tuple(reference["expected_ct_idx"])
    assert _word_lengths_from_wli(payload.wli) == reference["expected_word_lengths"]
    assert sum(reference["expected_word_lengths"]) == len(reference["expected_ct_idx"])
    assert (payload.metadata["master_page_start"], payload.metadata["master_page_end"]) == reference[
        "expected_master_page_range"
    ]
    assert payload.metadata["bound_book_start"] >= 1
    assert payload.metadata["bound_book_end"] >= payload.metadata["bound_book_start"]
    assert payload.metadata["boundary_granularity"] == "full_master_pages"
