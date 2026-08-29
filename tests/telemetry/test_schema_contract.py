from __future__ import annotations
import re
import json
import re
import json
import pytest
from tests._helpers.runner import run_vigenere_roundtrip_baseline
pytestmark = pytest.mark.tier_a
from rune_decrypter_prime.core.types import Direction, Device, ScorerImpl

def test_schema_contract_minimal_plus_pipeline(small_problem_cfg):
    _, _, meta = run_vigenere_roundtrip_baseline(device=Device.CPU, seed=small_problem_cfg['seed'], beam_width=small_problem_cfg['beam_width'], preview=small_problem_cfg['preview'], logging_over={'write_jsonl': True, 'enable_trace': False})
    tel = meta.get('telemetry', {})
    assert isinstance(tel.get('decrypt_time_s', 0.0), (int, float))
    assert isinstance(tel.get('score_time_s', 0.0), (int, float))
    assert isinstance(tel.get('wall_time_s', 0.0), (int, float))
    assert tel.get('device') in (Device.CPU.value, Device.CUDA.value)
    sc = tel.get('scorer', {})
    assert sc.get('impl') in (ScorerImpl.TORCH.value, ScorerImpl.NUMPY.value, ScorerImpl.AUTO.value, ScorerImpl.UNIFIED.value)
    assert sc.get('dtype') == 'float64'
    pipe = tel.get('pipeline', {})
    assert pipe.get('text_encoding_direction') in {Direction.LTR.value, Direction.RTL.value}
    ip = pipe.get('input_permutation', {})
    assert ip.get('kind') in {'none', 'custom'}
    assert isinstance(ip.get('length', 0), int) and ip['length'] > 0
    assert re.fullmatch('[0-9a-f]{32}', ip.get('hash', '')), f"bad perm hash: {ip.get('hash')}"
    h = ip.get('hash', '')
    assert isinstance(h, str) and len(h) == 32 and re.fullmatch('[0-9a-f]{32}', h), f'bad perm hash: {h}'
