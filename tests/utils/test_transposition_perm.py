from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.utils.transposition import TranspositionManager


pytestmark = pytest.mark.tier_a


def test_transposition_manager_rejects_duplicate_text_perm():
    perm = np.array([0, 0, 1], dtype=np.int64)
    with pytest.raises(ValueError, match="text_perm must be a permutation"):
        TranspositionManager(text_mode="perm", text_perm=perm)


def test_transposition_manager_rejects_out_of_range_key_perm():
    perm = np.array([0, 2, 3], dtype=np.int64)
    with pytest.raises(ValueError, match="key_perm must be a permutation"):
        TranspositionManager(key_mode="perm", key_perm=perm)
