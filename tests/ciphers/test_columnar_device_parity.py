"""Future-facing parity tests for permutation ciphers."""
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, by_name
from tests._helpers.permutation_cases import columnar_roundtrip_case

pytestmark = pytest.mark.tier_a


def test_columnar_solver_device_parity(device_matrix):
    """
    Columnar solver should return identical plaintext/keys across devices.
    """
    ct_idx, pt_idx, wli, perm, direction = columnar_roundtrip_case()
    solver = SolverSpec.beam(beam_width=2, progress_pct=1, seed=2025)
    cipher_spec = by_name.cipher("columnar", key_len=len(perm))
    key_spec = KeySpec.permutation(len=len(perm))

    baseline = None
    for dev in device_matrix:
        sol = RunAPI.run(
            text=ct_idx,
            cipher=cipher_spec,
            key=key_spec,
            solver=solver,
            device=dev,
            encoding_dir=direction,
            wli_data=wli,
            telemetry_on=True,
            initial_keys=[perm.tolist()],
        )
        arr_plain = np.asarray(sol.plaintext_idx, dtype=np.uint8)
        if baseline is None:
            baseline = (
                arr_plain,
                np.asarray(sol.key, dtype=np.uint8),
                sol.score,
                sol.meta["telemetry"]["pipeline"],
            )
            continue

        base_plain, base_key, base_score, base_pipeline = baseline
        assert np.array_equal(arr_plain, base_plain), f"Plaintext mismatch for device {dev}"
        assert np.array_equal(sol.key, base_key), f"Key mismatch for device {dev}"
        assert sol.score == pytest.approx(base_score, rel=1e-7, abs=1e-9), f"Score drift on {dev}"
        assert sol.meta["telemetry"]["pipeline"] == base_pipeline, f"Pipeline mismatch on {dev}"
