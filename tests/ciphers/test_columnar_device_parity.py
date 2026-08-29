"""Future-facing parity tests for permutation ciphers."""

from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from tests._helpers.permutation_cases import columnar_roundtrip_case

pytestmark = pytest.mark.tier_a


def test_columnar_solver_device_parity(device_matrix):
    """
    Columnar solver should return identical plaintext/keys across devices.
    """
    ct_idx, pt_idx, wli, perm, direction = columnar_roundtrip_case()
    solver = api.SolverSpec.beam_search(width=2, seed=2025, rounds=0)
    cipher_spec = api.CipherSpec.columnar(columns=len(perm), alphabet_size=29)
    key_spec = api.KeySpec.permutation(length=len(perm))
    baseline = None
    for dev in device_matrix:
        device = api.ComputeDevice(dev)
        sol = api.run(
            api.RunSpec(
                problem_input=api.RuneIndexInput(
                    indices=tuple(int(value) for value in ct_idx), word_lengths=wli
                ),
                cipher=cipher_spec,
                key_space=key_spec,
                solver=solver,
                scoring=api.ScoringConfig(
                    compute_dtype=api.advanced.FloatDType.FLOAT64
                ),
                initial_keys=(tuple(int(value) for value in perm),),
                telemetry_enabled=True,
                text_direction=direction,
                compute_device=device,
            )
        )
        arr_plain = np.asarray(sol.plaintext, dtype=np.uint8)
        if baseline is None:
            baseline = (
                arr_plain,
                np.asarray(sol.key, dtype=np.uint8),
                sol.score,
                sol.telemetry["pipeline"],
            )
            continue
        base_plain, base_key, base_score, base_pipeline = baseline
        assert np.array_equal(
            arr_plain, base_plain
        ), f"Plaintext mismatch for device {dev}"
        assert np.array_equal(sol.key, base_key), f"Key mismatch for device {dev}"
        import math

        SCORE_ABS_FLOOR = 1e-07
        abs_tol = max(SCORE_ABS_FLOOR, 2048 * math.ulp(base_score))
        assert sol.score == pytest.approx(
            base_score, abs=abs_tol, rel=0.0
        ), f"Score drift on {dev}"
        assert sol.telemetry["pipeline"] == base_pipeline, f"Pipeline mismatch on {dev}"
