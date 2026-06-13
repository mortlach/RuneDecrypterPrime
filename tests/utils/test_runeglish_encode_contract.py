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

