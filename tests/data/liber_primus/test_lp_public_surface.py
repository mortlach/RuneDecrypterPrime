from __future__ import annotations
import pytest
import rdp.data.liber_primus as lp
pytestmark = pytest.mark.tier_a

def test_liber_primus_public_surface_exports_typed_core() -> None:
    assert lp.LPBuiltInPageScheme.CANON_UNSOLVED_PAGE.value == 'canon_unsolved_page'
    assert lp.LPLineReadMode.BOUSTROPHEDON.value == 'boustrophedon'
    assert callable(lp.payload_from_locator)
    assert callable(lp.payload_from_partition_entry)
    assert callable(lp.parse_page_token)
