from __future__ import annotations
import pytest
from rune_decrypter_prime.core.types import Device, ScorerImpl
from tests._helpers.runner import run_vigenere_roundtrip_baseline
from tests._helpers.telemetry_contract import assert_basic_timing_fields, assert_pipeline_contract, assert_pipeline_stable, assert_no_magic_strings
pytestmark = pytest.mark.tier_a

def test_minimal_telemetry_contract(small_problem_cfg):
    known_key, found_key, meta1 = run_vigenere_roundtrip_baseline(device=Device.CPU, seed=small_problem_cfg['seed'], beam_width=small_problem_cfg['beam_width'], preview=small_problem_cfg['preview'], logging_over={'enable_trace': False})
    tel1 = meta1.get('telemetry', {})
    assert isinstance(tel1.get('tokens_processed', 0), (int, float))
    assert_basic_timing_fields(tel1)
    assert tel1.get('device') in (Device.CPU.value, Device.CUDA.value) or str(tel1.get('device', '')).startswith(Device.CUDA.value)
    sc = tel1.get('scorer', {})
    assert sc.get('dtype') == 'float64'
    assert sc.get('impl') in (ScorerImpl.NUMPY.value, ScorerImpl.TORCH.value, ScorerImpl.AUTO.value, ScorerImpl.UNIFIED.value)
    if tel1.get('device') == Device.CPU.value:
        assert sc.get('device') == Device.CPU.value
    assert_pipeline_contract(tel1)
    assert_no_magic_strings(tel1)
    _, _, meta2 = run_vigenere_roundtrip_baseline(device=Device.CPU, seed=small_problem_cfg['seed'], beam_width=small_problem_cfg['beam_width'], preview=small_problem_cfg['preview'], logging_over={'enable_trace': False})
    tel2 = meta2.get('telemetry', {})
    assert_pipeline_stable(tel1, tel2)
