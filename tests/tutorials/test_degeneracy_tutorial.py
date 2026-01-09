from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, define_map
from rune_decrypter_prime.ciphers.generic_map_cipher import GenericMapCipher
from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.core.problem import ProblemSpec, ProblemInstance
from rune_decrypter_prime.core.types import Direction, Device
from rune_decrypter_prime.utils.runeglish import Runeglish

pytestmark = pytest.mark.tier_a


def test_degeneracy_pipeline_known_key_example():
    N = 29
    length = 20
    spec = define_map(
        N=N,
        function=lambda pt, k: (pt % 5 + k) % N,
        degeneracy="allow",
        resolver="expand_beam",
        per_pos_limit=29,
        resolver_limit=8193,
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
        name=spec.kind,
    )
    setattr(cfg, "spec", spec)
    cipher = GenericMapCipher(cfg)
    ciphertext = cipher.encrypt_single(plaintext=plaintext, key=key)

    cands, lens, invalid = cipher.candidates_for(ciphertext, key, limit=spec.per_pos_limit)
    assert not bool(np.asarray(invalid[0]).any())
    assert int(np.max(lens[0])) > 1

    solver = SolverSpec.beam(beam_width=1, test_key=key.tolist(), seed=7, progress_pct=1)
    sol = RunAPI.run(
        text=ciphertext,
        cipher=spec,
        key=KeySpec.repeat(len=length),
        solver=solver,
        device=Device.CPU,
        encoding_dir=Direction.LTR,
        wli_data=wli,
        telemetry_on=False,
    )

    sol_plaintext = getattr(sol, "plaintext", "")

    scoring_cfg = ScoringConfig(encoding_dir=Direction.LTR)
    cipher_cfg = CipherConfig(
        ciphertext=ciphertext,
        wli_data=wli,
        key_length=length,
        encoding_dir=Direction.LTR,
        device=Device.CPU,
        name=(spec.name or spec.kind),
    )
    setattr(cipher_cfg, "spec", spec)
    spec_problem = ProblemSpec(
        text="",
        text_encoding_direction=Direction.LTR,
        cipher_cfg=cipher_cfg,
        scorer_params=scoring_cfg,
        input_permutation=None,
    )
    instance = ProblemInstance.materialise(spec_problem)
    expected = instance.problem.resolve_plaintext(key)
    assert expected is not None
    expected_rune = Runeglish.to_rune(expected, wli)
    assert isinstance(sol_plaintext, str)
    assert sol_plaintext == expected_rune

    roundtrip = cipher.encrypt_single(plaintext=expected, key=key)
    assert np.array_equal(roundtrip, ciphertext)
