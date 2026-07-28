from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api.two_period_cribs import normalize_two_period_cribs_request
from rune_decrypter_prime.api.specs import SolverSpec
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.solvers.two_period_cribs import (
    build_branches,
    coordinate_search,
    derive_child_seed,
    derive_constraint_space,
    expand_reduced_key,
    profile_contract_hash,
)

pytestmark = pytest.mark.tier_a


def _ciphertext(plaintext, key_a, key_b, modulus=29):
    return np.asarray(
        [
            (value + key_a[index % len(key_a)] + key_b[index % len(key_b)]) % modulus
            for index, value in enumerate(plaintext)
        ],
        dtype=np.uint8,
    )


def test_constraint_space_contains_canonical_known_key():
    key_a = np.asarray([3, 8, 13, 18, 23], dtype=np.uint8)
    key_b = np.asarray([0, 7, 14, 21, 28, 6, 13], dtype=np.uint8)
    plain = np.arange(40, dtype=np.uint8) % 29
    ct = _ciphertext(plain, key_a, key_b)
    from rune_decrypter_prime.solvers.two_period_cribs import CribSpan
    span = CribSpan("fixture", tuple(int(x) for x in plain[4:20]), 4)
    space = derive_constraint_space(ct, (span,), period_a=5, period_b=7, modulus=29)
    variables = np.asarray([np.concatenate((key_a, key_b))[i] for i in space.free_columns])
    assert np.array_equal(expand_reduced_key(variables, space), np.concatenate((key_a, key_b)))
    assert expand_reduced_key(variables, space)[5] == 0


def test_contradictory_overlapping_crib_rejects():
    from rune_decrypter_prime.solvers.two_period_cribs import CribSpan
    ct = np.zeros(20, dtype=np.uint8)
    spans = (CribSpan("a", (0,), 0), CribSpan("b", (1,), 0))
    try:
        derive_constraint_space(ct, spans, period_a=5, period_b=7, modulus=29)
    except ValueError as exc:
        assert "contradictory" in str(exc)
    else:
        raise AssertionError("contradictory overlap was accepted")


def test_branch_order_and_child_seeds_are_input_order_independent():
    text = "dormouse pilgrimage"
    from rune_decrypter_prime.api.normalize import normalize_ciphertext
    ct, wli = normalize_ciphertext(text)
    first = normalize_two_period_cribs_request(
        SolverSpec.two_period_cribs(candidate_words=("dormouse", "pilgrimage"), starts=1, seed=9)
    )
    second = normalize_two_period_cribs_request(
        SolverSpec.two_period_cribs(candidate_words=("pilgrimage", "dormouse"), starts=1, seed=9)
    )
    one, _ = build_branches(
        ct, wli, first, period_a=5, period_b=7, modulus=29, direction=Direction.LTR
    )
    two, _ = build_branches(
        ct, wli, second, period_a=5, period_b=7, modulus=29, direction=Direction.LTR
    )
    assert [branch.branch_id for branch in one] == [branch.branch_id for branch in two]
    assert [derive_child_seed(9, branch.branch_id, "S2", 0) for branch in one] == [
        derive_child_seed(9, branch.branch_id, "S2", 0) for branch in two
    ]


def test_coordinate_search_is_deterministic_and_accounts_evaluations():
    target = np.asarray([2, 4, 6], dtype=np.uint8)

    def evaluate(values):
        return -np.count_nonzero(values != target[None, :], axis=1).astype(float)

    result1 = coordinate_search(evaluate, np.random.default_rng(11), np.zeros(3, dtype=np.uint8), 2)
    np.random.seed(999)
    result2 = coordinate_search(evaluate, np.random.default_rng(11), np.zeros(3, dtype=np.uint8), 2)
    assert np.array_equal(result1[0], target)
    assert np.array_equal(result1[0], result2[0])
    assert result1[1:] == result2[1:]
    assert result1[2] == 1 + 2 * 3 * 29


def test_profile_hashes_are_stable_and_distinct():
    hashes = [profile_contract_hash(profile) for profile in ("S2", "B1", "F1")]
    assert hashes == [profile_contract_hash(profile) for profile in ("S2", "B1", "F1")]
    assert len(set(hashes)) == 3
