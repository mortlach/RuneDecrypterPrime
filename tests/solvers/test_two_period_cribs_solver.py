from __future__ import annotations
from tutorials.v1.data.two_period_cribs_demo import encrypt_interruptor_fixture
import rdp.api.normalize
import rdp.api.two_period_cribs
from rdp import api
import hashlib
import numpy as np
import pytest
from rune_decrypter_prime.core.types import Device, Direction
from rune_decrypter_prime.solvers.two_period_cribs import (
    CribConstraintSpace,
    TwoPeriodBranch,
    _candidate_id,
    _deduplicated_union,
    _run_refinement_stage,
    build_branches,
    coordinate_search,
    derive_child_seed,
    derive_constraint_space,
    expand_reduced_key,
    profile_contract_hash,
    _resolve_interruptor_hypotheses,
    run_two_period_stages,
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

    span = CribSpan("fixture", tuple((int(x) for x in plain[4:20])), 4)
    space = derive_constraint_space(ct, (span,), period_a=5, period_b=7, modulus=29)
    variables = np.asarray(
        [np.concatenate((key_a, key_b))[i] for i in space.free_columns]
    )
    assert np.array_equal(
        expand_reduced_key(variables, space), np.concatenate((key_a, key_b))
    )
    assert expand_reduced_key(variables, space)[5] == 0


def test_constraint_space_uses_core_positions_after_structural_interruptors():
    from rune_decrypter_prime.solvers.two_period_cribs import CribSpan
    from rune_decrypter_prime.utils.runeglish import Runeglish

    plain, _wli, _runes = Runeglish.encode_english_to_runes(
        "uncomfortable", direction="ltr"
    )
    plaintext = np.asarray(plain, dtype=np.uint8)
    key_a = np.asarray([3, 8, 13, 18, 23], dtype=np.uint8)
    key_b = np.asarray([0, 7, 14, 21, 28, 6, 13], dtype=np.uint8)
    known_key = np.concatenate((key_a, key_b))
    interruptors = (2, 7)
    cipher, _key = (
        api.CipherSpec.two_period_vigenere(
            first_period=5, second_period=7, alphabet_size=29
        ),
        api.KeySpec.repeating(length=5 + 7),
    )
    ciphertext = encrypt_interruptor_fixture(
        plaintext,
        cipher=cipher,
        key=tuple((int(_concrete_key_value) for _concrete_key_value in known_key)),
        interruptor_positions=np.asarray(interruptors, dtype=np.intp),
    )
    span = CribSpan("uncomfortable", tuple((int(x) for x in plaintext)), 0)
    space = derive_constraint_space(
        ciphertext,
        (span,),
        period_a=5,
        period_b=7,
        modulus=29,
        interruptors=interruptors,
    )
    variables = np.asarray([known_key[i] for i in space.free_columns], dtype=np.uint8)
    assert np.array_equal(expand_reduced_key(variables, space), known_key)
    assert all(
        (int(ciphertext[index]) == int(plaintext[index]) for index in interruptors)
    )


def test_crib_must_match_unchanged_interruptor_symbol():
    from rune_decrypter_prime.solvers.two_period_cribs import CribSpan

    ciphertext = np.asarray([4, 9, 5, 7], dtype=np.uint8)
    span = CribSpan("fixture", (4, 9, 6, 7), 0)
    with pytest.raises(ValueError, match="contradicts interruptor at position 2"):
        derive_constraint_space(
            ciphertext, (span,), period_a=2, period_b=3, modulus=29, interruptors=(2,)
        )


def test_interruptor_pool_hypotheses_are_stable_and_count_bounded():
    cfg = api.InterruptorConfig.search(
        [8, 3, 5],
        minimum_count=2,
        maximum_count=2,
        strategy=api.advanced.InterruptorSearchStrategy.AUTO,
        maximum_combinations=3,
    )
    assert _resolve_interruptor_hypotheses(cfg, 20) == ((3, 5), (3, 8), (5, 8))


def test_interruptor_pool_range_enumerates_each_allowed_count_stably():
    cfg = api.InterruptorConfig.search(
        [4, 1, 7],
        minimum_count=1,
        maximum_count=2,
        strategy=api.advanced.InterruptorSearchStrategy.AUTO,
        maximum_combinations=6,
    )
    assert _resolve_interruptor_hypotheses(cfg, 20) == (
        (1,),
        (4,),
        (7,),
        (1, 4),
        (1, 7),
        (4, 7),
    )


def test_interruptor_pool_explicit_bruteforce_can_opt_in_above_auto_cap():
    cfg = api.InterruptorConfig.search(
        [1, 2, 3, 4],
        minimum_count=2,
        maximum_count=2,
        strategy=api.advanced.InterruptorSearchStrategy.BRUTE_FORCE,
        maximum_combinations=1,
    )
    assert _resolve_interruptor_hypotheses(cfg, 20) == (
        (1, 2),
        (1, 3),
        (1, 4),
        (2, 3),
        (2, 4),
        (3, 4),
    )


def test_interruptor_pool_auto_refuses_implicit_keyops_fallback():
    cfg = api.InterruptorConfig.search(
        [1, 2, 3, 4],
        minimum_count=2,
        maximum_count=2,
        strategy=api.advanced.InterruptorSearchStrategy.AUTO,
        maximum_combinations=5,
    )
    with pytest.raises(ValueError, match="exceeds bruteforce_max"):
        _resolve_interruptor_hypotheses(cfg, 20)


def test_interruptor_pool_keyops_is_explicitly_unsupported_for_constraint_route():
    cfg = api.InterruptorConfig.search(
        [1, 2, 3],
        minimum_count=1,
        maximum_count=1,
        strategy=api.advanced.InterruptorSearchStrategy.KEY_OPERATIONS,
        maximum_combinations=5000,
    )
    with pytest.raises(ValueError, match="structural.*keyops.*unsupported"):
        _resolve_interruptor_hypotheses(cfg, 20)


def test_staged_pool_search_keeps_structural_candidates_distinct_and_uses_winning_interruptors(
    monkeypatch,
):
    from rune_decrypter_prime.solvers import two_period_cribs as staged

    plaintext, wli = rdp.api.normalize.normalize_ciphertext("uncomfortable dormouse")
    known_key = np.asarray([3, 8, 13, 18, 23, 0, 7, 14, 21, 28, 6, 13], dtype=np.uint8)
    true_interruptors = (14,)
    cipher, key = (
        api.CipherSpec.two_period_vigenere(
            first_period=5, second_period=7, alphabet_size=29
        ),
        api.KeySpec.repeating(length=5 + 7),
    )
    cipher_obj = cipher
    ciphertext = encrypt_interruptor_fixture(
        plaintext,
        cipher=cipher_obj,
        key=tuple((int(_concrete_key_value) for _concrete_key_value in known_key)),
        interruptor_positions=np.asarray(true_interruptors, dtype=np.intp),
    )
    request = rdp.api.two_period_cribs.normalize_two_period_cribs_request(
        api.SolverSpec.two_period_cribs(
            fixed_cribs=(("uncomfortable", 0),), starts=1, seed=9
        )
    )

    class FakeProblem:
        def __init__(self, *, cipher, scorer, c_cfg, s_cfg, enable_telemetry):
            self.cipher = cipher
            self.scorer = scorer
            self.c_cfg = c_cfg

        def _interruptors(self):
            cfg = self.c_cfg.interruptors_cfg
            return None if cfg is None else cfg.parameters.get("positions")

        def _plain(self, key_values):
            return np.asarray(
                self.cipher.decrypt_single(
                    ciphertext=self.c_cfg.ciphertext,
                    key=np.asarray(key_values, dtype=np.uint8),
                    interrupt_idx=self._interruptors(),
                ),
                dtype=np.uint8,
            )

        def evaluate_keys(self, keys):
            batch = np.asarray(keys, dtype=np.uint8)
            if batch.ndim == 1:
                batch = batch[None, :]
            return np.asarray(
                [np.mean(self._plain(row) == plaintext) for row in batch],
                dtype=np.float64,
            )

        def resolve_plaintext(self, key_values):
            return self._plain(key_values)

    monkeypatch.setattr(staged, "DecryptionProblem", FakeProblem)
    monkeypatch.setattr(staged, "build_scorer", lambda *_args, **_kwargs: object())
    result = run_two_period_stages(
        ciphertext=np.asarray(ciphertext, dtype=np.uint8),
        wli=wli,
        cipher=cipher,
        key=key,
        request=request,
        device=Device.CPU,
        direction=Direction.LTR,
        telemetry_on=False,
        interruptors=api.InterruptorConfig.search(
            [15, 14],
            minimum_count=1,
            maximum_count=1,
            strategy=api.advanced.InterruptorSearchStrategy.AUTO,
            maximum_combinations=2,
        ),
    )
    details = result.meta["two_period_solve"]
    assert result.key == known_key.astype(int).tolist()
    assert (
        result.plaintext_idx
        == np.asarray(plaintext, dtype=np.uint8).astype(int).tolist()
    )
    assert details["interruptors"]["hypothesis_count"] == 2
    assert details["interruptors"]["winning_positions"] == [14]
    assert details["interruptors"]["winning_count"] == 1
    assert details["branch_count"] == 2
    assert details["final_union_count"] == 2


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
    ct, wli = rdp.api.normalize.normalize_ciphertext(text)
    first = rdp.api.two_period_cribs.normalize_two_period_cribs_request(
        api.SolverSpec.two_period_cribs(
            candidate_words=("dormouse", "pilgrimage"), starts=1, seed=9
        )
    )
    second = rdp.api.two_period_cribs.normalize_two_period_cribs_request(
        api.SolverSpec.two_period_cribs(
            candidate_words=("pilgrimage", "dormouse"), starts=1, seed=9
        )
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

    result1 = coordinate_search(
        evaluate, np.random.default_rng(11), np.zeros(3, dtype=np.uint8), 2
    )
    np.random.seed(999)
    result2 = coordinate_search(
        evaluate, np.random.default_rng(11), np.zeros(3, dtype=np.uint8), 2
    )
    assert np.array_equal(result1[0], target)
    assert np.array_equal(result1[0], result2[0])
    assert result1[1:] == result2[1:]
    assert result1[2] == 1 + 2 * 3 * 29


def test_profile_hashes_are_stable_and_distinct():
    assert {
        profile: profile_contract_hash(profile) for profile in ("S2", "B1", "F1")
    } == {
        "S2": "264ce44b7f0338fe345f69f6dbba05fedd562e215c6ff819232a9c7aa1c64661",
        "B1": "65696e93fd2d3c5bc57aae2725bd61ab280d2f26e893ad53ec145895b5706b02",
        "F1": "00b48410ea166bc75d23a0d65713e81dade7c4ee9a834ff4e55869ed08ab30c3",
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
        [0, *((7 * index + 11) % 29 for index in range(1, 31))], dtype=np.uint8
    )
    crib_spans = []
    for word, start in spans:
        runes, _, _ = Runeglish.encode_english_to_runes(word, direction="ltr")
        plaintext[start : start + len(runes)] = runes
        crib_spans.append(CribSpan(word, tuple(runes), start))
    ciphertext = _ciphertext(plaintext, key_a, key_b)
    space = derive_constraint_space(
        ciphertext, crib_spans, period_a=13, period_b=31, modulus=29
    )
    assert space.dimension == expected_dimension


def test_explicit_candidate_position_must_be_complete_wli_span():
    ciphertext, wli = rdp.api.normalize.normalize_ciphertext("dormouse")
    request = rdp.api.two_period_cribs.normalize_two_period_cribs_request(
        api.SolverSpec.two_period_cribs(
            candidate_words=("dormouse",),
            candidate_positions={"dormouse": (1,)},
            starts=1,
        )
    )
    with pytest.raises(ValueError, match="dormouse.*position 1.*complete WLI span"):
        build_branches(
            ciphertext,
            wli,
            request,
            period_a=5,
            period_b=7,
            modulus=29,
            direction=Direction.LTR,
        )


def test_staged_route_rejects_mixed_canonical_and_legacy_interruptor_inputs():
    ciphertext, wli = rdp.api.normalize.normalize_ciphertext("a")
    cipher, key = (
        api.CipherSpec.two_period_vigenere(
            first_period=5, second_period=7, alphabet_size=29
        ),
        api.KeySpec.repeating(length=5 + 7),
    )
    request = rdp.api.two_period_cribs.normalize_two_period_cribs_request(
        api.SolverSpec.two_period_cribs(fixed_cribs=(("a", 0),), starts=1)
    )
    with pytest.raises(ValueError, match="cannot be combined"):
        run_two_period_stages(
            ciphertext=np.asarray(ciphertext, dtype=np.uint8),
            wli=wli,
            cipher=cipher,
            key=key,
            request=request,
            device=Device.CPU,
            direction=Direction.LTR,
            telemetry_on=False,
            interruptors=api.InterruptorConfig.exact([0]),
            interruptors_exact=[0],
        )


def test_pool_mode_does_not_mask_invalid_explicit_candidate_position_as_structural_rejection():
    ciphertext, wli = rdp.api.normalize.normalize_ciphertext("dormouse")
    cipher, key = (
        api.CipherSpec.two_period_vigenere(
            first_period=5, second_period=7, alphabet_size=29
        ),
        api.KeySpec.repeating(length=5 + 7),
    )
    request = rdp.api.two_period_cribs.normalize_two_period_cribs_request(
        api.SolverSpec.two_period_cribs(
            candidate_words=("dormouse",),
            candidate_positions={"dormouse": (1,)},
            starts=1,
        )
    )
    with pytest.raises(ValueError, match="dormouse.*position 1.*complete WLI span"):
        run_two_period_stages(
            ciphertext=np.asarray(ciphertext, dtype=np.uint8),
            wli=wli,
            cipher=cipher,
            key=key,
            request=request,
            device=Device.CPU,
            direction=Direction.LTR,
            telemetry_on=False,
            interruptors=api.InterruptorConfig.search(
                [0, 2],
                minimum_count=1,
                maximum_count=1,
                strategy=api.advanced.InterruptorSearchStrategy.AUTO,
                maximum_combinations=5000,
            ),
        )


def test_missing_automatic_position_is_retained_as_rejection_evidence():
    ciphertext, wli = rdp.api.normalize.normalize_ciphertext("dormouse")
    request = rdp.api.two_period_cribs.normalize_two_period_cribs_request(
        api.SolverSpec.two_period_cribs(
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
    ciphertext, wli = rdp.api.normalize.normalize_ciphertext("dormouse")
    request = rdp.api.two_period_cribs.normalize_two_period_cribs_request(
        api.SolverSpec.two_period_cribs(candidate_words=("uncomfortable",), starts=1)
    )
    with pytest.raises(
        ValueError, match="no compatible.*uncomfortable.*no complete WLI span"
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


def test_candidate_identity_preserves_legacy_key_only_hash_without_interruptors():
    key = np.asarray([3, 8, 13, 0, 7], dtype=np.uint8)
    expected = "tpc_" + hashlib.sha256(bytes(key)).hexdigest()[:20]
    assert _candidate_id(key) == expected


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
    ciphertext, wli = rdp.api.normalize.normalize_ciphertext("dormouse")
    request = rdp.api.two_period_cribs.normalize_two_period_cribs_request(
        api.SolverSpec.two_period_cribs(
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
        return (
            candidate_id,
            {
                "candidate_id": candidate_id,
                "branch_id": branch.branch_id,
                "variables": [value],
                "key": key.astype(int).tolist(),
            },
        )

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
    assert (
        max(
            final_union,
            key=lambda item: evaluate(
                np.asarray([final_union[item]["variables"]], dtype=np.uint8)
            )[0],
        )
        == judge_id
    )
    assert evaluations >= len(judge_inputs)
