"""Determinism canary on the public api.run surface."""
from __future__ import annotations
from rdp import api
import json
import numpy as np
import pytest
from rune_decrypter_prime.utils.runeglish import Runeglish
pytestmark = pytest.mark.tier_a

def _encrypt_fixture_text(*, text: str, direction: api.TextDirection, key: np.ndarray):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(
        text,
        direction="ltr" if direction is api.TextDirection.LEFT_TO_RIGHT else "rtl",
    )
    cipher = api.CipherSpec.vigenere(alphabet_size=29)
    ct_idx = api.encrypt(tuple(int(value) for value in pt_idx), cipher=cipher, key=tuple(int(value) for value in key))
    return (np.asarray(ct_idx, dtype=np.uint8), np.asarray(pt_idx, dtype=np.uint8), wli)

def test_determinism_canary() -> None:
    direction = api.TextDirection.LEFT_TO_RIGHT
    key = np.array([3, 1, 4, 1, 5], dtype=np.uint8)
    ct_idx, _pt_idx, wli = _encrypt_fixture_text(text='deterministic canary for run api seed replay', direction=direction, key=key)
    solver = api.SolverSpec.beam_search(width=4, seed=1234, rounds=0)
    cipher_spec = api.CipherSpec.vigenere(alphabet_size=29)
    key_spec = api.KeySpec.repeating(length=int(key.size))
    sol_a = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=tuple(int(value) for value in ct_idx), word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=api.ScoringConfig(), initial_keys=(tuple(int(value) for value in key),), telemetry_enabled=True, text_direction=direction, compute_device=api.ComputeDevice.CPU))
    sol_b = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=tuple(int(value) for value in ct_idx), word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=api.ScoringConfig(), initial_keys=(tuple(int(value) for value in key),), telemetry_enabled=True, text_direction=direction, compute_device=api.ComputeDevice.CPU))
    assert np.array_equal(sol_a.plaintext, sol_b.plaintext)
    assert np.array_equal(sol_a.key, sol_b.key)
    assert float(sol_a.score) == pytest.approx(float(sol_b.score), rel=0, abs=0)
    json.dumps(dict(sol_a.telemetry), sort_keys=True)
    json.dumps(dict(sol_b.telemetry), sort_keys=True)
