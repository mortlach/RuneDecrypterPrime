"""Determinism canary on the public RunAPI surface."""
from __future__ import annotations

import json

import numpy as np
import pytest

from rune_decrypter_prime.api import Direction, KeySpec, RunAPI, SolverSpec, by_name, cipher_instance
from rune_decrypter_prime.utils.runeglish import Runeglish


pytestmark = pytest.mark.tier_a


def _encrypt_fixture_text(*, text: str, direction: Direction, key: np.ndarray):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=direction.value)
    cipher = cipher_instance("vigenere", key_length=key.size, text_transposition=direction.value)
    ct_idx = cipher.encrypt(plaintext=np.asarray(pt_idx, dtype=np.uint8), key=key)
    return np.asarray(ct_idx, dtype=np.uint8), np.asarray(pt_idx, dtype=np.uint8), wli


def test_determinism_canary() -> None:
    direction = Direction.LTR
    key = np.array([3, 1, 4, 1, 5], dtype=np.uint8)
    ct_idx, _pt_idx, wli = _encrypt_fixture_text(
        text="deterministic canary for run api seed replay",
        direction=direction,
        key=key,
    )

    solver = SolverSpec.beam(beam_width=4, progress_pct=1, seed=1234)
    cipher_spec = by_name.cipher("vigenere", key_len=int(key.size))
    key_spec = KeySpec.repeat(len=int(key.size))

    sol_a = RunAPI.run(
        text=ct_idx,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        encoding_dir=direction,
        device="cpu",
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
        device="cpu",
        wli_data=wli,
        telemetry_on=True,
        initial_keys=[key.tolist()],
    )

    assert np.array_equal(sol_a.plaintext_idx, sol_b.plaintext_idx)
    assert np.array_equal(sol_a.key, sol_b.key)
    assert float(sol_a.score) == pytest.approx(float(sol_b.score), rel=0, abs=0)

    # Canary guard: telemetry payloads remain JSON-serializable.
    json.dumps(getattr(sol_a, "meta", {}), sort_keys=True)
    json.dumps(getattr(sol_b, "meta", {}), sort_keys=True)
