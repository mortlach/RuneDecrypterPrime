from __future__ import annotations
import rdp.api.normalize
import pytest
from rdp.data.runeglish import Runeglish
pytestmark = pytest.mark.tier_a

def test_encoding_direction():
    text = 'AB'
    ct, wli = rdp.api.normalize.normalize_ciphertext(text)
    ct_rtl, wli_rtl, _ = Runeglish.encode_english_to_runes(text, direction='rtl')
    assert ct.tolist() == ct_rtl
    assert wli == wli_rtl
