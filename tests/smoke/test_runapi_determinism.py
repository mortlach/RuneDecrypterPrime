"""RunAPI determinism guardrails."""
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import (
    RunAPI,
    SolverSpec,
    KeySpec,
    Direction,
    by_name,
    cipher_instance,
)
from rune_decrypter_prime.utils.runeglish import Runeglish

pytestmark = pytest.mark.tier_a


def _encrypt_vigenere(text: str, direction: Direction, key: np.ndarray):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=direction.value)
    cipher = cipher_instance("vigenere", key_length=key.size, text_transposition=direction.value)
    ct_idx = cipher.encrypt(plaintext=np.asarray(pt_idx, dtype=np.uint8), key=key)
    return np.asarray(ct_idx, dtype=np.uint8), np.asarray(pt_idx, dtype=np.uint8), wli


@pytest.mark.parametrize("text", ["deterministic runs rely on seeds", "cuda parity prefers torch backend"])
def test_runapi_seed_replay_consistency(device_matrix, text):
    """
    Same seed + device + config must yield identical plaintext, key, score, and telemetry.
    """
    direction = Direction.LTR
    key = np.array([3, 1, 4, 1, 5], dtype=np.uint8)
    ct_idx, pt_idx, wli = _encrypt_vigenere(text, direction, key)

    solver = SolverSpec.beam(beam_width=4, progress_pct=1, seed=1234)
    cipher_spec = by_name.cipher("vigenere", key_len=key.size)
    key_spec = KeySpec.repeat(len=key.size)

    for dev in device_matrix:
        sol_a = RunAPI.run(
            text=ct_idx,
            cipher=cipher_spec,
            key=key_spec,
            solver=solver,
            encoding_dir=direction,
            device=dev,
            wli_data=wli,
            telemetry_on=True,
            initial_keys=[key.tolist()],
        )
        sol_b = RunAPI.run(
            text=ct_idx,
            cipher=cipher_spec,
            key=key_spec,
            solver=solver,
            encoding_dir=direction,
            device=dev,
            wli_data=wli,
            telemetry_on=True,
            initial_keys=[key.tolist()],
        )

        assert np.array_equal(sol_a.plaintext_idx, sol_b.plaintext_idx)
        assert np.array_equal(sol_a.key, sol_b.key)
        assert sol_a.score == pytest.approx(sol_b.score, rel=0, abs=0)
