from __future__ import annotations
import pytest
from rune_decrypter_prime.data.liber_primus.lp_adapter import payload_from_locator, payload_from_partition_entry
from rune_decrypter_prime.data.liber_primus.lp_main import extract_locator_ct_wli, extract_partition_entry_ct_wli, load_main_transcript
from rune_decrypter_prime.data.liber_primus.lp_registry import LPFragmentLocator, LPPageRef, build_red_rune_17_partition
from rune_decrypter_prime.data.liber_primus.lp_routes import LPLineReadMode, LPLineRuneSelector, LPSpiralDirection, LPSpiralRoute
pytestmark = pytest.mark.tier_a
LP_MAIN_TRANSCRIPT_SHA256 = '105f1c68cecde03df1e66982d3021ab31d7f49ee975ca109d1a1924cbcafc99c'

def test_payload_from_locator_matches_direct_ct_wli() -> None:
    doc = load_main_transcript(attach_catalogue=True)
    locator = LPFragmentLocator(page_ref=LPPageRef.canon_page(54))
    payload = payload_from_locator(doc, locator)
    ct_direct, wli_direct = extract_locator_ct_wli(doc, locator)
    assert payload.ct_idx == ct_direct
    assert payload.wli == wli_direct
    assert payload.metadata['route'] == 'none'
    assert payload.metadata['source_kind'] == 'liber_primus.locator'
    assert payload.metadata['asset_id'] == 'liber_primus.main_transcript'
    assert payload.metadata['asset_version'] == LP_MAIN_TRANSCRIPT_SHA256

def test_payload_from_partition_entry_matches_direct_ct_wli() -> None:
    doc = load_main_transcript(attach_catalogue=True)
    entry = build_red_rune_17_partition()[0]
    payload = payload_from_partition_entry(doc, entry)
    ct_direct, wli_direct = extract_partition_entry_ct_wli(doc, entry)
    assert payload.ct_idx == ct_direct
    assert payload.wli == wli_direct
    assert payload.metadata['partition_ordinal'] == '1'
    assert payload.metadata['source_kind'] == 'liber_primus.partition'
    assert payload.metadata['asset_id'] == 'liber_primus.main_transcript'
    assert payload.metadata['asset_version'] == LP_MAIN_TRANSCRIPT_SHA256

def test_payload_from_partition_entry_page_intersection_is_deterministic() -> None:
    doc = load_main_transcript(attach_catalogue=True)
    entry = build_red_rune_17_partition()[7]
    page_ref = LPPageRef.canon_page(20)
    payload_a = payload_from_partition_entry(doc, entry, intersect_page_ref=page_ref)
    payload_b = payload_from_partition_entry(doc, entry, intersect_page_ref=page_ref)
    assert payload_a.as_dict() == payload_b.as_dict()
    assert payload_a.metadata['intersect_page']['number'] == 20

def test_payload_from_locator_line_selector_route() -> None:
    doc = load_main_transcript(attach_catalogue=True)
    locator = LPFragmentLocator(page_ref=LPPageRef.canon_page(54), line=0, line_end=2)
    payload = payload_from_locator(doc, locator, line_mode=LPLineReadMode.BOUSTROPHEDON, selector=LPLineRuneSelector.FIRST_ONLY)
    assert payload.metadata['route'] == 'line:boustrophedon:first_only'
    assert len(payload.ct_idx) == len(payload.wli)

def test_payload_from_locator_spiral_route() -> None:
    doc = load_main_transcript(attach_catalogue=True)
    locator = LPFragmentLocator(page_ref=LPPageRef.canon_page(54), line=0, line_end=2)
    route = LPSpiralRoute(direction=LPSpiralDirection.CLOCKWISE)
    payload = payload_from_locator(doc, locator, spiral_route=route)
    assert payload.metadata['route'].startswith('spiral:clockwise:')
    assert len(payload.ct_idx) == len(payload.wli)
