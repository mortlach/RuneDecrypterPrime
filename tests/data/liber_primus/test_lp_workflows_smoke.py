from __future__ import annotations

import pytest

from rune_decrypter_prime.data import liber_primus as lp


pytestmark = pytest.mark.tier_a


def test_workflow_canon_page_payload_smoke() -> None:
    doc = lp.load_master_transcript(attach_catalogue=True)
    locator = lp.LPFragmentLocator(page_ref=lp.LPPageRef.canon_page(54))
    payload = lp.payload_from_locator(doc, locator)
    assert len(payload.ct_idx) == len(payload.wli)


def test_workflow_named_alias_payload_smoke() -> None:
    doc = lp.load_master_transcript(attach_catalogue=True)
    registry = lp.LPRegistry()
    label = lp.LPRegistryLabel(namespace="solved", name="example_page")
    registry.register_page_alias(label, lp.LPPageRef.canon_page(54))
    locator = lp.LPFragmentLocator(page_ref=registry.resolve_page_alias(label))
    payload = lp.payload_from_locator(doc, locator)
    assert len(payload.ct_idx) > 0


def test_workflow_partition_intersection_smoke() -> None:
    doc = lp.load_master_transcript(attach_catalogue=True)
    entry = lp.build_red_rune_17_partition()[14]
    payload = lp.payload_from_partition_entry(
        doc,
        entry,
        intersect_page_ref=lp.LPPageRef.canon_page(54),
    )
    assert len(payload.ct_idx) == len(payload.wli)


def test_workflow_route_variants_smoke() -> None:
    doc = lp.load_master_transcript(attach_catalogue=True)
    locator = lp.LPFragmentLocator(page_ref=lp.LPPageRef.canon_page(54), line=0, line_end=4)
    ltr = lp.payload_from_locator(doc, locator, line_mode=lp.LPLineReadMode.LEFT_TO_RIGHT)
    rtl = lp.payload_from_locator(doc, locator, line_mode=lp.LPLineReadMode.RIGHT_TO_LEFT)
    bou = lp.payload_from_locator(doc, locator, line_mode=lp.LPLineReadMode.BOUSTROPHEDON)
    spi = lp.payload_from_locator(doc, locator, spiral_route=lp.LPSpiralRoute())
    assert len(ltr.ct_idx) > 0
    assert len(rtl.ct_idx) > 0
    assert len(bou.ct_idx) > 0
    assert len(spi.ct_idx) > 0

