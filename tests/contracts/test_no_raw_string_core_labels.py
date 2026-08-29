from __future__ import annotations
from rdp import api
import pytest
from rune_decrypter_prime.core.component_contracts import EffectiveState, FallbackPolicy, LaneStatus, RankEffect, RequestState, ScorerLaneName
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig, SpanHammingMode
from rune_decrypter_prime.core.types import Device, Direction, KeyOpsFamily, ScorerImpl

def test_component_contracts_reject_raw_string_core_labels() -> None:
    with pytest.raises(TypeError, match='LaneStatus.lane'):
        LaneStatus(lane='hamming', request_state=RequestState.REQUESTED, effective_state=EffectiveState.ACTIVE, rank_effect=RankEffect.PRODUCTION, fallback_policy=FallbackPolicy.BLOCK)

def test_scoring_config_normalises_boundary_strings_to_enums() -> None:
    cfg = api.ScoringConfig(backend=api.advanced.ScorerBackend.TORCH, span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED)
    assert cfg.encoding_dir is Direction.RTL
    assert cfg.impl is ScorerImpl.TORCH
    assert cfg.span_hamming_mode is SpanHammingMode.CALIBRATED

def test_cipher_config_normalises_boundary_strings_to_enums() -> None:
    cfg = CipherConfig(ciphertext=[0, 1, 2], wli_data=[], key_length=3, device='cpu', encoding_dir='reverse', keyops_family='vector')
    assert cfg.device is Device.CPU
    assert cfg.encoding_dir is Direction.RTL
    assert cfg.keyops_family is KeyOpsFamily.VECTOR
