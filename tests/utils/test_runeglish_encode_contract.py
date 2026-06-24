import numpy as np

from rune_decrypter_prime.utils.runeglish import Runeglish


def test_encode_english_to_runes_return_order_and_shapes():
    # Contract: encode_english_to_runes returns (pt_idx, wli, rune_str)
    # This test exists because a prior benchmark/test bug accidentally unpacked
    # (pt_idx, wli, rune_str) as (_, pt_idx, _), scoring WLI as plaintext.
    pt_idx, wli, rune_str = Runeglish.encode_english_to_runes("HELLO WORLD", direction="ltr")

    assert isinstance(pt_idx, list)
    assert isinstance(wli, list)
    assert isinstance(rune_str, str)

    assert len(pt_idx) > 0
    assert len(wli) == len(pt_idx)

    arr = np.asarray(pt_idx, dtype=np.int64)
    assert arr.ndim == 1
    assert arr.min() >= 0
    assert arr.max() <= 28

    # Basic WLI shape check: list of [pos, len] pairs
    assert all(isinstance(p, list) and len(p) == 2 for p in wli)
    assert all(isinstance(p[0], int) and isinstance(p[1], int) for p in wli)


def test_rtl_latin_rendering_inverts_reversed_multigraph_tokenisation():
    text = "READ EARTH AETHER THE WHITE RABBIT"
    pt_idx, wli, rune_str = Runeglish.encode_english_to_runes(text, direction="rtl")

    assert "ᚱᚫᛞ" in rune_str
    assert Runeglish.to_rune_latin(pt_idx, wli) != text
    assert Runeglish.to_rune_latin(pt_idx, wli, direction="rtl") == text


def test_ltr_latin_rendering_keeps_left_to_right_multigraphs():
    text = "READ RAED EARTH AETHER"
    pt_idx, wli, _rune_str = Runeglish.encode_english_to_runes(text, direction="ltr")

    assert Runeglish.to_rune_latin(pt_idx, wli, direction="ltr") == text


def test_rtl_latin_rendering_requires_wli_for_wordwise_inverse():
    pt_idx, _wli, _rune_str = Runeglish.encode_english_to_runes("READ", direction="rtl")

    assert Runeglish.to_rune_latin(pt_idx, None, direction="rtl") == "RAED"


def test_latin_rendering_uses_canonical_alphabet_normalisation():
    pt_idx, wli, _rune_str = Runeglish.encode_english_to_runes("LOOKED", direction="rtl")

    assert Runeglish.to_rune_latin(pt_idx, wli, direction="rtl") == "LOOCED"

