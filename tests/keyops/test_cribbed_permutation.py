from __future__ import annotations

import numpy as np

from rune_decrypter_prime.keyops.cribbed_permutation import CribbedPermutationKeyOps


def test_normalize_respects_multi_option_constraints():
    keyops = CribbedPermutationKeyOps(
        K=8,
        crib_multi=[
            {"ct": 1, "pt_codes": [4, 5]},
            {"ct": 6, "pt_codes": [2]},
        ],
    )
    perm = np.arange(8, dtype=np.int64)
    perm[1] = 0
    perm[6] = 7
    repaired = keyops.normalize(perm)
    assert repaired[6] == 2
    assert repaired[1] in {4, 5}
    assert sorted(repaired.tolist()) == list(range(8))


def test_multi_option_weights_prefer_highest_when_rng_missing():
    keyops = CribbedPermutationKeyOps(
        K=6,
        crib_multi=[
            {"ct": 2, "pt_codes": [3, 4], "weights": [0.1, 2.5]},
        ],
    )
    perm = np.array([0, 1, 5, 2, 3, 4], dtype=np.int64)
    repaired = keyops.normalize(perm)
    assert repaired[2] == 4  # weight 2.5 should be preferred deterministically
