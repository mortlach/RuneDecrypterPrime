from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.generic_map_cipher import GenericMapCipher
from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.core.problem import ProblemSpec, ProblemInstance
from rdp.core.types import Direction, Device

pytestmark = pytest.mark.tier_a

def test_degeneracy_pipeline_known_key_example():
    N = 29
    length = 20
    spec = api.experimental.define_cipher_map(
        lambda pt, k: (pt % 5 + k) % N,
        alphabet_size=N,
        degeneracy=api.experimental.DegeneracyPolicy.ALLOW,
        resolver=api.experimental.ResolverMode.EXPAND_BEAM,
        per_position_limit=29,
        resolver_limit=32,
    )
    plaintext = np.array(
        [4, 20, 1, 3, 14, 25, 6, 8, 9, 10, 12, 17, 18, 2, 5, 7, 11, 13, 15, 19],
        dtype=np.uint8,
    )
    key = np.array(
        [7, 0, 18, 5, 12, 9, 0, 21, 3, 14, 6, 11, 22, 4, 19, 2, 8, 13, 25, 1],
        dtype=np.uint8,
    )
    wli = [[0, 1] for _ in range(length)]
    cfg = CipherConfig(
        ciphertext=np.zeros(length, dtype=np.uint8),
        wli_data=wli,
        key_length=length,
        encoding_dir=Direction.LTR,
        device=Device.CPU,
        name="generic_map",
    )
    setattr(cfg, "spec", spec)
    cipher = GenericMapCipher(cfg)
    ciphertext = cipher.encrypt_single(plaintext=plaintext, key=key)
    cands, lens, invalid = cipher.candidates_for(
        ciphertext, key, limit=spec.parameters["per_position_limit"]
    )
    assert not bool(np.asarray(invalid[0]).any())
    assert int(np.max(lens[0])) > 1
    solver = api.SolverSpec.beam_search(width=1, seed=7, rounds=0)
    sol = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(
                indices=tuple(int(value) for value in ciphertext), word_lengths=wli
            ),
            cipher=spec,
            key_space=api.KeySpec.repeating(length=length),
            solver=solver,
            scoring=api.ScoringConfig(),
            initial_keys=(tuple(int(value) for value in key),),
            telemetry_enabled=False,
            text_direction=api.TextDirection.LEFT_TO_RIGHT,
            compute_device=api.ComputeDevice.CPU,
        )
    )
    sol_plaintext = sol.plaintext
    scoring_cfg = api.ScoringConfig()
    cipher_cfg = CipherConfig(
        ciphertext=ciphertext,
        wli_data=wli,
        key_length=length,
        spec=spec,
        key_space=api.KeySpec.repeating(length=length),
        encoding_dir=Direction.LTR,
        device=Device.CPU,
        name="generic_map",
    )
    spec_problem = ProblemSpec(
        text="",
        text_encoding_direction=Direction.LTR,
        cipher_cfg=cipher_cfg,
        scorer_params=scoring_cfg,
        input_permutation=None,
    )
    instance = ProblemInstance.materialise(spec_problem)
    assert sol.key is not None
    expected = instance.problem.resolve_plaintext(sol.key)
    assert expected is not None
    assert sol_plaintext == tuple(int(value) for value in expected)
    roundtrip = cipher.encrypt_single(plaintext=expected, key=sol.key)
    assert np.array_equal(roundtrip, ciphertext)
