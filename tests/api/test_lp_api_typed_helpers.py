from __future__ import annotations

import pytest

from rune_decrypter_prime.api import (
    load_lp_payload_from_locator,
    load_lp_payload_from_partition_entry,
)
from rune_decrypter_prime.data.liber_primus import (
    LPFragmentLocator,
    LPPageRef,
    build_red_rune_17_partition,
)


pytestmark = pytest.mark.tier_a


def test_api_locator_payload_helper_returns_solver_payload() -> None:
    locator = LPFragmentLocator(page_ref=LPPageRef.canon_page(54), line=0, line_end=1)
    payload = load_lp_payload_from_locator(locator)
    assert len(payload.ct_idx) == len(payload.wli)
    assert payload.metadata["source"] == "locator"


def test_api_partition_payload_helper_returns_solver_payload() -> None:
    entry = build_red_rune_17_partition()[0]
    payload = load_lp_payload_from_partition_entry(entry)
    assert len(payload.ct_idx) == len(payload.wli)
    assert payload.metadata["source"] == "partition"

