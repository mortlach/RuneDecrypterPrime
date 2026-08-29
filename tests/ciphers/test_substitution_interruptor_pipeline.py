from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.substitution_cipher import SubstitutionCipher
from rune_decrypter_prime.core.config import (
    CipherConfig,
)
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.types import Direction
pytestmark = pytest.mark.tier_a

def _cipher(alphabet_size: int=5) -> SubstitutionCipher:
    cfg = CipherConfig(name='substitution', ciphertext=[1, 2, 3], wli_data=[], key_length=alphabet_size, alphabet_size=alphabet_size, encoding_dir=Direction.LTR, device='cpu')
    return SubstitutionCipher(cfg)

def test_direct_decrypt_uses_shared_exact_interruptor_pipeline():
    cipher = _cipher()
    inverse = np.asarray([4, 0, 1, 2, 3], dtype=np.uint8)
    actual = cipher.decrypt(ciphertext=np.asarray([1, 2, 3], dtype=np.uint8), key=inverse, interrupt_idx=np.asarray([1], dtype=np.intp))
    np.testing.assert_array_equal(actual, np.asarray([0, 2, 2], dtype=np.uint8))

def test_direct_encrypt_uses_shared_exact_interruptor_pipeline():
    cipher = _cipher()
    forward = np.asarray([1, 2, 3, 4, 0], dtype=np.uint8)
    actual = cipher.encrypt(plaintext=np.asarray([0, 1, 2], dtype=np.uint8), key=forward, interrupt_idx=np.asarray([1], dtype=np.intp))
    np.testing.assert_array_equal(actual, np.asarray([1, 1, 3], dtype=np.uint8))

def test_non_structural_orientation_and_batch_behaviour_are_preserved():
    cipher = _cipher()
    forward = np.asarray([1, 2, 3, 4, 0], dtype=np.uint8)
    inverse = np.asarray([4, 0, 1, 2, 3], dtype=np.uint8)
    identity = np.arange(5, dtype=np.uint8)
    ciphertext = np.asarray([1, 2, 3], dtype=np.uint8)
    np.testing.assert_array_equal(cipher.decrypt(ciphertext=ciphertext, key=inverse), np.asarray([0, 1, 2], dtype=np.uint8))
    np.testing.assert_array_equal(cipher.decrypt(ciphertext=ciphertext, key=forward, key_is_fwd=True), np.asarray([0, 1, 2], dtype=np.uint8))
    np.testing.assert_array_equal(cipher.encrypt(plaintext=np.asarray([0, 1, 2], dtype=np.uint8), key=forward), np.asarray([1, 2, 3], dtype=np.uint8))
    np.testing.assert_array_equal(cipher.decrypt(ciphertext=ciphertext, key=np.stack([inverse, identity])), np.asarray([[0, 1, 2], [1, 2, 3]], dtype=np.uint8))

def test_runapi_substitution_exact_interruptor_regression():
    inverse_shift = np.r_[28, np.arange(28)].astype(int).tolist()
    solution = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(
                indices=[1, 2, 3], word_lengths=[[i, 3] for i in range(3)]
            ),
            cipher=api.CipherSpec.substitution(alphabet_size=29),
            key_space=api.KeySpec.permutation(length=29),
            solver=api.SolverSpec.beam_search(width=1, seed=1, rounds=0),
            scoring=api.ScoringConfig(),
            initial_keys=(tuple(inverse_shift),),
            telemetry_enabled=False,
            interruptors=api.InterruptorConfig.exact([1]),
        )
    )
    assert solution.plaintext is not None
    assert len(solution.plaintext) == 3
    assert solution.plaintext[1] == 2

class _TransparentScorer:

    def __init__(self) -> None:
        self.plaintexts: list[list[int]] = []

    def batch_score(self, plaintexts, wli=None):
        expected = np.asarray([0, 2, 2], dtype=np.uint8)
        self.plaintexts = [np.asarray(pt, dtype=np.uint8).astype(int).tolist() for pt in plaintexts]
        return -np.asarray([np.count_nonzero(np.asarray(pt, dtype=np.uint8) != expected) for pt in plaintexts], dtype=np.float64)

def test_candidate_evaluation_scores_corrected_plaintext_transparently():
    inverse_shift = np.r_[28, np.arange(28)].astype(np.uint8)
    cfg = CipherConfig(name='substitution', ciphertext=[1, 2, 3], wli_data=[], key_length=29, alphabet_size=29, encoding_dir=Direction.LTR, device='cpu', interruptors_cfg=api.InterruptorConfig.exact([1]))
    scorer = _TransparentScorer()
    problem = DecryptionProblem(cipher=SubstitutionCipher(cfg), scorer=scorer, c_cfg=cfg, s_cfg=api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=False, backend=api.advanced.ScorerBackend.NUMPY))
    scores = problem.evaluate_keys(inverse_shift[None, :])
    assert scorer.plaintexts == [[0, 2, 2]]
    np.testing.assert_array_equal(scores, np.asarray([0.0], dtype=np.float64))
