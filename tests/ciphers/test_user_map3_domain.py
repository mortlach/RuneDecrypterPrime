from __future__ import annotations

import pytest
from rdp import api

pytestmark = pytest.mark.tier_a


def test_three_input_custom_maps_are_not_in_the_v1_experimental_surface() -> None:
    assert not hasattr(api.experimental, "define_cipher_map3")
    with pytest.raises(api.advanced.UnknownComponentError, match="unsupported cipher"):
        api.CipherSpec.from_name("user_map3")
