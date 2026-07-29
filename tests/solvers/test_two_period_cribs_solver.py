from __future__ import annotations

import hashlib

import numpy as np
import pytest

from rune_decrypter_prime.api.two_period_cribs import normalize_two_period_cribs_request
from rune_decrypter_prime.api.specs import SolverSpec
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.solvers.two_period_cribs import (
    CribConstraintSpace,
    TwoPeriodBranch,
    _deduplicated_union,
    _run_refinement_stage,
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
    assert {
        profile: profile_contract_hash(profile) for profile in ("S2", "B1", "F1")
    } == {
        "S2": "cfd406a753ef41ec8d217fafe0fb9a75ee902f4d07a135f14c754dc361ef9e51",
        "B1": "025e8c6825f4597b540c05982f6c8be9d2b59f02cc3856cbe9a838fd90611613",
        "F1": "56773006f1d252022952b026212e8df8bd991d6bcd268bf22f3a90405bb88fd8",
    }


@pytest.mark.parametrize(
    "spans, expected_dimension",
    [
        ((("uncomfortable", 188),), 30),
        ((("uncomfortable", 188), ("dormouse", 81)), 22),
        ((("uncomfortable", 188), ("dormouse", 206)), 22),
        ((("uncomfortable", 188), ("dormouse", 81), ("dormouse", 206)), 14),
    ],
)
def test_p13_p31_accepted_affine_dimensions(spans, expected_dimension):
    from rune_decrypter_prime.solvers.two_period_cribs import CribSpan
    from rune_decrypter_prime.utils.runeglish import Runeglish

    plaintext = np.arange(308, dtype=np.uint16) % 29
    key_a = np.asarray([(5 * index + 3) % 29 for index in range(13)], dtype=np.uint8)
    key_b = np.asarray(
        [0, *((7 * index + 11) % 29 for index in range(1, 31))],
        dtype=np.uint8,
    )
    crib_spans = []
    for word, start in spans:
        runes, _, _ = Runeglish.encode_english_to_runes(word, direction="ltr")
        plaintext[start:start + len(runes)] = runes
        crib_spans.append(CribSpan(word, tuple(runes), start))
    ciphertext = _ciphertext(plaintext, key_a, key_b)
    space = derive_constraint_space(
        ciphertext, crib_spans, period_a=13, period_b=31, modulus=29
    )
    assert space.dimension == expected_dimension


def test_explicit_candidate_position_must_be_complete_wli_span():
    from rune_decrypter_prime.api.normalize import normalize_ciphertext

    ciphertext, wli = normalize_ciphertext("dormouse")
    request = normalize_two_period_cribs_request(
        SolverSpec.two_period_cribs(
            candidate_words=("dormouse",),
            candidate_positions={"dormouse": (1,)},
            starts=1,
        )
    )
    with pytest.raises(ValueError, match=r"dormouse.*position 1.*complete WLI span"):
        build_branches(
            ciphertext,
            wli,
            request,
            period_a=5,
            period_b=7,
            modulus=29,
            direction=Direction.LTR,
        )


def test_missing_automatic_position_is_retained_as_rejection_evidence():
    from rune_decrypter_prime.api.normalize import normalize_ciphertext

    ciphertext, wli = normalize_ciphertext("dormouse")
    request = normalize_two_period_cribs_request(
        SolverSpec.two_period_cribs(
            candidate_words=("dormouse", "uncomfortable"), starts=1
        )
    )
    branches, rejected = build_branches(
        ciphertext,
        wli,
        request,
        period_a=5,
        period_b=7,
        modulus=29,
        direction=Direction.LTR,
    )
    assert branches
    assert {
        "word": "uncomfortable",
        "start": None,
        "reason": "no complete WLI span of rune length 13",
    } in rejected


def test_all_missing_automatic_positions_raise_with_rejection_reason():
    from rune_decrypter_prime.api.normalize import normalize_ciphertext

    ciphertext, wli = normalize_ciphertext("dormouse")
    request = normalize_two_period_cribs_request(
        SolverSpec.two_period_cribs(candidate_words=("uncomfortable",), starts=1)
    )
    with pytest.raises(
        ValueError, match=r"no compatible.*uncomfortable.*no complete WLI span"
    ):
        build_branches(
            ciphertext,
            wli,
            request,
            period_a=5,
            period_b=7,
            modulus=29,
            direction=Direction.LTR,
        )


def test_branch_identity_varies_with_periods_and_modulus():
    from rune_decrypter_prime.solvers.two_period_cribs import _branch_id

    spaces = (
        CribConstraintSpace(29, 5, 7, (0,) * 12, ((),) * 12, ()),
        CribConstraintSpace(29, 4, 8, (0,) * 12, ((),) * 12, ()),
        CribConstraintSpace(31, 5, 7, (0,) * 12, ((),) * 12, ()),
    )
    identities = {_branch_id((), None, space) for space in spaces}
    assert len(identities) == 3


def test_rune_equivalent_candidate_hypotheses_deduplicate():
    from rune_decrypter_prime.api.normalize import normalize_ciphertext

    ciphertext, wli = normalize_ciphertext("dormouse")
    request = normalize_two_period_cribs_request(
        SolverSpec.two_period_cribs(
            candidate_words=("dormouse", "dormovse"),
            candidate_positions={"dormouse": (0,), "dormovse": (0,)},
            starts=1,
        )
    )
    branches, rejected = build_branches(
        ciphertext,
        wli,
        request,
        period_a=5,
        period_b=7,
        modulus=29,
        direction=Direction.LTR,
    )
    assert len(branches) == 1
    assert rejected == ()


def test_f1_judge_searches_complete_union_and_new_terminal_can_win():
    space = CribConstraintSpace(
        modulus=29,
        period_a=1,
        period_b=1,
        particular=(0, 0),
        basis=((1,), (0,)),
        free_columns=(0,),
    )
    branch = TwoPeriodBranch("branch", (), None, space)

    def record(value):
        key = expand_reduced_key(np.asarray([value], dtype=np.uint8), space)
        candidate_id = "candidate_" + str(value)
        return candidate_id, {
            "candidate_id": candidate_id,
            "branch_id": branch.branch_id,
            "variables": [value],
            "key": key.astype(int).tolist(),
        }

    scout = dict([record(0)])
    bridge = dict([record(1)])
    judge_inputs = _deduplicated_union(scout, bridge)
    assert tuple(judge_inputs) == ("candidate_0", "candidate_1")

    def evaluate(values):
        return -np.abs(values[:, 0].astype(float) - 5.0)

    judge, evaluations, _elapsed = _run_refinement_stage(
        stage_id="F1",
        score_field="judge_score",
        evaluate=evaluate,
        branch=branch,
        inputs=judge_inputs,
        sweeps=3,
        root_seed=2026,
        modulus=29,
    )
    final_union = _deduplicated_union(scout, bridge, judge)
    judge_key = expand_reduced_key(np.asarray([5], dtype=np.uint8), space)
    judge_id = "tpc_" + hashlib.sha256(bytes(judge_key)).hexdigest()[:20]
    assert judge_id in judge
    assert set(scout) | set(bridge) | set(judge) == set(final_union)
    assert max(final_union, key=lambda item: evaluate(
        np.asarray([final_union[item]["variables"]], dtype=np.uint8)
    )[0]) == judge_id
    assert evaluations >= len(judge_inputs)
