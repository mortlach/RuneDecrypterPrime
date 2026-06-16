from __future__ import annotations

import pytest

from rune_decrypter_prime.data import liber_primus as lp

pytestmark = pytest.mark.tier_a


EXPECTED_SOLVED_SOURCE_RANGES = {
    "warning": ("red_rune.warning", (0, 0)),
    "welcome_pilgrim": ("red_rune.welcome_pilgrim", (1, 2)),
    "some_wisdom": ("red_rune.some_wisdom", (3, 3)),
    "koan_a_man": ("red_rune.koan_a_man", (4, 7)),
    "loss_of_divinity": ("red_rune.loss_of_divinity", (8, 11)),
    "koan_during_lesson": ("red_rune.koan_during_lesson", (12, 13)),
    "instruction": ("red_rune.instruction", (14, 14)),
    "an_end": ("red_rune.an_end", (71, 71)),
    "parable": ("red_rune.parable", (72, 72)),
}

ALIAS_GROUPS = {
    "warning": ("warning", "red_rune.warning", "solved.warning"),
    "welcome_pilgrim": ("welcome_pilgrim", "red_rune.welcome_pilgrim", "solved.welcome_pilgrim"),
    "some_wisdom": ("some_wisdom", "red_rune.some_wisdom", "solved.some_wisdom"),
    "koan_a_man": ("koan_a_man", "red_rune.koan_a_man", "solved.koan_a_man"),
    "loss_of_divinity": ("loss_of_divinity", "red_rune.loss_of_divinity", "solved.loss_of_divinity"),
    "koan_during_lesson": (
        "koan_during_lesson",
        "red_rune.koan_during_lesson",
        "solved.koan_during_lesson",
    ),
    "instruction": ("instruction", "red_rune.instruction", "solved.instruction"),
    "an_end": ("an_end", "red_rune.an_end", "solved.an_end", "p56", "56.jpg", "canon.56"),
    "parable": ("parable", "red_rune.parable", "solved.parable", "p57", "57.jpg", "canon.57"),
}


def test_solved_lp_source_labels_are_listed() -> None:
    labels = set(lp.list_source_labels())
    aliases = set(lp.list_source_labels(include_aliases=True))

    for simple_label, (canonical_label, _) in EXPECTED_SOLVED_SOURCE_RANGES.items():
        assert canonical_label in labels
        assert simple_label in aliases

    for aliases_for_page in ALIAS_GROUPS.values():
        for alias in aliases_for_page:
            assert alias in aliases


def test_resolve_source_label_exposes_spreadsheet_and_master_page_metadata() -> None:
    entry = lp.resolve_source_label("welcome_pilgrim")

    assert entry.source_label == "red_rune.welcome_pilgrim"
    assert entry.display_name == "Welcome Pilgrim"
    assert entry.spreadsheet_sheet == "Welcome"
    assert entry.source_status == lp.SOURCE_STATUS_SOLVED_TEXT_AVAILABLE
    assert entry.boundary_status == lp.BOUNDARY_MASTER_PAGE_RANGE
    assert entry.red_rune_sections == (3,)
    assert entry.master_page_range == (1, 2)
    assert entry.locator is None


@pytest.mark.parametrize("simple_label,expected", sorted(EXPECTED_SOLVED_SOURCE_RANGES.items()))
def test_source_aliases_resolve_to_canonical_text_label(simple_label: str, expected: tuple[str, tuple[int, int]]) -> None:
    canonical_label, expected_master_range = expected
    entry = lp.resolve_source_label(simple_label)

    assert entry.source_label == canonical_label
    assert entry.master_page_range == expected_master_range


@pytest.mark.parametrize("simple_label,aliases", sorted(ALIAS_GROUPS.items()))
def test_alias_flavours_return_same_payload(simple_label: str, aliases: tuple[str, ...]) -> None:
    canonical_label, expected_master_range = EXPECTED_SOLVED_SOURCE_RANGES[simple_label]
    baseline = lp.payload_from_label(simple_label)

    for alias in aliases:
        payload = lp.payload_from_label(alias)
        assert payload.metadata["source_label"] == canonical_label
        assert (payload.metadata["master_page_start"], payload.metadata["master_page_end"]) == expected_master_range
        assert payload.ct_idx == baseline.ct_idx
        assert payload.wli == baseline.wli


def test_unknown_source_label_fails_clearly() -> None:
    with pytest.raises(KeyError, match="unknown LP source label"):
        lp.resolve_source_label("not_a_real_source")


def test_solve_recipes_are_separate_from_source_labels() -> None:
    recipe = lp.resolve_solve_recipe_label("recipe.welcome_pilgrim.vigenere_interruptors")

    assert recipe.source_label == "red_rune.welcome_pilgrim"
    assert recipe.cipher_family == "vigenere_with_interruptors"
    assert recipe.target_kind == "real_solve"
    assert recipe.priority == "P0"
    assert recipe.reference_key_or_shift == "DIVINITY"
    assert recipe.source_label in lp.list_source_labels()


def test_every_recipe_targets_a_known_source_label() -> None:
    sources = set(lp.list_source_labels())

    for recipe_label in lp.list_solve_recipe_labels():
        recipe = lp.resolve_solve_recipe_label(recipe_label)
        assert recipe.source_label in sources


@pytest.mark.parametrize("simple_label,expected", sorted(EXPECTED_SOLVED_SOURCE_RANGES.items()))
def test_payload_from_label_returns_real_master_transcript_payload(simple_label: str, expected: tuple[str, tuple[int, int]]) -> None:
    canonical_label, expected_master_range = expected

    payload = lp.payload_from_label(simple_label)

    assert payload.ct_idx
    assert payload.wli
    assert len(payload.ct_idx) == len(payload.wli)
    assert payload.metadata["source_kind"] == "liber_primus.label"
    assert payload.metadata["source_label"] == canonical_label
    assert payload.metadata["requested_label"] == simple_label
    assert payload.metadata["boundary_status"] == lp.BOUNDARY_MASTER_PAGE_RANGE
    assert (payload.metadata["master_page_start"], payload.metadata["master_page_end"]) == expected_master_range
    assert payload.metadata["bound_book_start"] == expected_master_range[0] + 1
    assert payload.metadata["bound_book_end"] == expected_master_range[1] + 1
    assert payload.metadata["line"] is None
    assert payload.metadata["line_end"] is None
    assert payload.metadata["boundary_granularity"] == "full_master_pages"
