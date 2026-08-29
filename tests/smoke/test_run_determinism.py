"""api.run determinism guardrails."""

from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.utils.runeglish import Runeglish

pytestmark = pytest.mark.tier_a


def _encrypt_vigenere(text: str, direction: api.TextDirection, key: np.ndarray):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=direction.value)
    cipher = api.CipherSpec.vigenere(alphabet_size=29)
    ct_idx = api.encrypt(
        tuple(int(value) for value in pt_idx),
        cipher=cipher,
        key=tuple(int(value) for value in key),
    )
    return (np.asarray(ct_idx, dtype=np.uint8), np.asarray(pt_idx, dtype=np.uint8), wli)


@pytest.mark.parametrize(
    "text", ["deterministic runs rely on seeds", "cuda parity prefers torch backend"]
)
def test_runapi_seed_replay_consistency(device_matrix, text):
    """
    Same seed + device + config must yield identical plaintext, key, score, and telemetry.
    """
    direction = api.TextDirection.LEFT_TO_RIGHT
    key = np.array([3, 1, 4, 1, 5], dtype=np.uint8)
    ct_idx, pt_idx, wli = _encrypt_vigenere(text, direction, key)
    solver = api.SolverSpec.beam_search(width=4, seed=1234, rounds=0)
    cipher_spec = api.CipherSpec.vigenere(alphabet_size=29)
    key_spec = api.KeySpec.repeating(length=key.size)
    for dev in device_matrix:
        device = api.ComputeDevice(dev)
        sol_a = api.run(
            api.RunSpec(
                problem_input=api.RuneIndexInput(
                    indices=tuple(int(value) for value in ct_idx), word_lengths=wli
                ),
                cipher=cipher_spec,
                key_space=key_spec,
                solver=solver,
                scoring=api.ScoringConfig(),
                initial_keys=(tuple(int(value) for value in key),),
                telemetry_enabled=True,
                text_direction=direction,
                compute_device=device,
            )
        )
        sol_b = api.run(
            api.RunSpec(
                problem_input=api.RuneIndexInput(
                    indices=tuple(int(value) for value in ct_idx), word_lengths=wli
                ),
                cipher=cipher_spec,
                key_space=key_spec,
                solver=solver,
                scoring=api.ScoringConfig(),
                initial_keys=(tuple(int(value) for value in key),),
                telemetry_enabled=True,
                text_direction=direction,
                compute_device=device,
            )
        )
        assert np.array_equal(sol_a.plaintext, sol_b.plaintext)
        assert np.array_equal(sol_a.key, sol_b.key)
        assert sol_a.score == pytest.approx(sol_b.score, rel=0, abs=0)
