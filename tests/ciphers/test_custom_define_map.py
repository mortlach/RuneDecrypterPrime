"""Guardrails for `define_map` / `define_cipher` extensibility."""
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, define_map, define_cipher
from rune_decrypter_prime.core.types import Direction, Device

pytestmark = pytest.mark.tier_a


def test_define_map_cipher_roundtrip_and_telemetry():
    """Custom map ciphers created via define_map/define_cipher should plug into RunAPI seamlessly."""
    xor_spec = define_map(
        function=lambda pt, k: (pt ^ k) % 29,
        name="unit_test_xor",
        degeneracy="forbid",
    )
    xor_spec.name = None  # allow engine to route via canonical user_map2 entry
    cipher_spec, key_spec = define_cipher(spec=xor_spec, key=KeySpec.const(value=7))

    rng = np.random.default_rng(2025)
    plaintext = rng.integers(0, 29, size=32, dtype=np.uint8)
    ciphertext = (plaintext ^ 7) % 29

    solver = SolverSpec.beam(beam_width=2, seed=314, progress_pct=1, stop_score=0.1)
    sol = RunAPI.run(
        text=ciphertext,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        encoding_dir=Direction.LTR,
        device=Device.CPU,
        telemetry_on=True,
        initial_keys=[[7]],
    )

    solved_key = np.asarray(sol.key, dtype=np.uint8)
    assert solved_key.size >= 1
    key_value = int(solved_key.reshape(-1)[0])
    assert key_value == 7
    telemetry = sol.meta.get("telemetry", {})
    run_block = telemetry.get("run", {})
    assert run_block.get("solver") == "beam"
    pipeline = run_block.get("pipeline", {})
    assert pipeline.get("text_encoding_direction") == "ltr"
