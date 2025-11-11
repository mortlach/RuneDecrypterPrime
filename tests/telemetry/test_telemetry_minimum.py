from __future__ import annotations
import numpy as np
import pytest

from rune_decrypter_prime.core.types import Device
from tests._helpers.runner import run_vigenere_roundtrip_baseline
from tests._helpers.telemetry_contract import (
    assert_min_telemetry,
    assert_basic_timing_fields,
    assert_pipeline_contract,
    assert_no_magic_strings,
)

pytestmark = pytest.mark.tier_a


@pytest.mark.parametrize("device", [Device.CPU])
def test_vigenere_roundtrip_min_telemetry(device, small_problem_cfg):
    """
    Smoke: tiny Vigenère roundtrip should emit the minimum telemetry block + v1 pipeline.
    """
    known_key, found_key, meta = run_vigenere_roundtrip_baseline(
        device=device,
        seed=small_problem_cfg["seed"],
        beam_width=small_problem_cfg["beam_width"],
        preview=small_problem_cfg["preview"],
        logging_over={"enable_trace": False},
    )

    # Correctness
    assert found_key.size == known_key.size
    assert np.array_equal(found_key, known_key)

    # Telemetry presence + minimal schema (device-sensitive)
    tel = meta.get("telemetry", {})
    assert_min_telemetry(tel, device=device.value)

    # Timing fields (v1 names) & basic sanity
    assert_basic_timing_fields(tel)

    # v1 pipeline contract (LTR/no permutation for this minimal test)
    assert_pipeline_contract(tel, expected_direction="ltr", expected_perm_kind="none")

    # Extra: dtype/impl sanity stays
    sc = tel.get("scorer", {})
    assert sc.get("dtype") == "float32"
    assert sc.get("impl") in ("numpy", "torch", "torch_cuda", "cuda")

    # No magic strings anywhere (ltr/rtl/etc.)
    assert_no_magic_strings(tel)
