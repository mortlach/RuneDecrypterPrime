from __future__ import annotations
import pytest
from rune_decrypter_prime.data.liber_primus.lp_registry import LPBuiltInPageScheme, LPPageRef, LPRegistry, LPRegistryLabel, LPResolutionContext, LPSectionOrdinal, build_nested_side_art_red_rune_partition, build_red_rune_17_partition, build_side_art_10_partition, resolve_page_ref, resolve_relative_index
pytestmark = pytest.mark.tier_a

def test_page_scheme_values_are_stable_strings() -> None:
    assert LPBuiltInPageScheme.TRANSCRIPT_PAGE_ID.value == 'transcript_page_id'
    assert LPBuiltInPageScheme.BOUND_BOOK_PAGE.value == 'bound_book_page'
    assert LPBuiltInPageScheme.CANON_UNSOLVED_PAGE.value == 'canon_unsolved_page'

def test_bound_book_and_canon_page_54_resolve_differently() -> None:
    context = LPResolutionContext(total_pages=74, canon_page_count=58)
    assert resolve_page_ref(LPPageRef.bound_book_page(54), context=context) == 53
    assert resolve_page_ref(LPPageRef.canon_page(54), context=context) == 70

def test_negative_relative_index_returns_last_item() -> None:
    assert resolve_relative_index(5, -1) == 4
    assert resolve_relative_index(5, 0) == 0
    assert resolve_relative_index(5, 3) == 3

def test_section_ordinal_renders_nested_labels() -> None:
    assert LPSectionOrdinal.of(8, 1).render() == '8-1'
    assert LPSectionOrdinal.of(1).render() == '1'

def test_nested_side_art_red_rune_partition_contains_expected_examples() -> None:
    nested = build_nested_side_art_red_rune_partition(side_art_entries=build_side_art_10_partition(), red_rune_entries=build_red_rune_17_partition())
    labels = {entry.ordinal.render(): entry.canon_page_range() for entry in nested}
    assert labels['1-1'] == (0, 2)
    assert labels['8-1'] == (40, 53)
    assert labels['8-2'] == (54, 55)
    assert labels['9-1'] == (56, 56)
    assert labels['10-1'] == (57, 57)

def test_registry_can_register_typed_page_alias() -> None:
    registry = LPRegistry()
    label = LPRegistryLabel(namespace='user', name='a_waning')
    target = LPPageRef.canon_page(0)
    registry.register_page_alias(label, target)
    assert registry.resolve_page_alias(label) == target
