from __future__ import annotations
import rdp.api.normalize
import pytest
from rune_decrypter_prime.utils.runeglish import Runeglish
pytestmark = pytest.mark.tier_a

def test_wli_parity():
    text = 'AB CD'
    ct, wli = rdp.api.normalize.normalize_ciphertext(text)
    ct_ref, wli_ref, _ = Runeglish.encode_english_to_runes(text, direction='ltr')
    assert ct.tolist() == ct_ref
    assert wli == wli_ref
