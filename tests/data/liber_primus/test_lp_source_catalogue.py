from __future__ import annotations

import pytest

from rune_decrypter_prime.data import liber_primus as lp

pytestmark = pytest.mark.tier_a


_METHOD_WORDS = {
    "cipher",
    "divinity",
    "emirp",
    "fibbo",
    "fibonacci",
    "firfumferenfe",
    "gematria",
    "interrupter",
    "interruptors",
    "key",
    "prime",
    "primes",
    "recipe",
    "shift",
    "stream",
    "vigenere",
}


def _label_parts(label: str) -> set[str]:
    return {part for part in label.replace("-", "_").split(".") for part in part.split("_") if part}


def test_solved_lp_source_labels_are_text_identity_only() -> None:
    labels = lp.list_source_labels()

    assert "red_rune.welcome_pilgrim" in labels
    assert "red_rune.an_end" in labels
    assert "red_rune.parable" in labels
    assert all(label.startswith("red_rune.") for label in labels)

    for label in lp.list_source_labels(include_aliases=True):
        assert not (_label_parts(label) & _METHOD_WORDS), label


def test_resolve_source_label_exposes_spreadsheet_and_candidate_metadata() -> None:
    entry = lp.resolve_source_label("red_rune.welcome_pilgrim")

    assert entry.source_label == "red_rune.welcome_pilgrim"
    assert entry.display_name == "Welcome Pilgrim"
    assert entry.spreadsheet_sheet == "Welcome"
    assert entry.source_status == lp.SOURCE_STATUS_SOLVED_TEXT_AVAILABLE
    assert entry.boundary_status == lp.BOUNDARY_NEEDS_VERIFICATION
    assert entry.candidate_red_rune_sections == (3,)
    assert entry.candidate_canon_page_range == (3, 6)
    assert entry.locator is None


def test_source_aliases_resolve_to_canonical_text_label() -> None:
    entry = lp.resolve_source_label("solved.welcome_pilgrim")

    assert entry.source_label == "red_rune.welcome_pilgrim"


def test_unknown_source_label_fails_clearly() -> None:
    with pytest.raises(KeyError, match="unknown LP source label"):
        lp.resolve_source_label("red_rune.not_a_real_source")


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


def test_payload_from_unverified_source_label_fails_before_using_candidate_bounds() -> None:
    with pytest.raises(ValueError, match="no verified master transcript locator"):
        lp.payload_from_label("red_rune.welcome_pilgrim")
