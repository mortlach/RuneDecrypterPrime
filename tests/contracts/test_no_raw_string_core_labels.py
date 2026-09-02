from __future__ import annotations
from rdp import api
import pytest
from rdp.core.component_contracts import (
    CapabilityEffectiveState,
    FallbackPolicy,
    ScoringLaneStatus,
    RankingEffect,
    CapabilityRequestState,
)
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import SpanHammingMode
from rdp.core.types import (
    Device,
    Direction,
    KeyOpsFamily,
    ScorerBackend,
)

def test_component_contracts_reject_raw_string_core_labels() -> None:
    with pytest.raises(TypeError, match="ScoringLaneStatus.lane"):
        ScoringLaneStatus(
            lane="hamming",
            request_state=CapabilityRequestState.REQUESTED,
            effective_state=CapabilityEffectiveState.ACTIVE,
            ranking_effect=RankingEffect.PRODUCTION,
            fallback_policy=FallbackPolicy.BLOCK,
        )


def test_scoring_config_preserves_typed_boundary_enums() -> None:
    cfg = api.ScoringConfig(
        backend=api.advanced.ScorerBackend.TORCH,
        span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED,
    )
    assert cfg.backend is ScorerBackend.TORCH
    assert cfg.span_hamming_mode is SpanHammingMode.CALIBRATED

def test_cipher_config_normalises_boundary_strings_to_enums() -> None:
    cfg = CipherConfig(ciphertext=[0, 1, 2], wli_data=[], key_length=3, device='cpu', encoding_dir='reverse', keyops_family='vector')
    assert cfg.device is Device.CPU
    assert cfg.encoding_dir is Direction.RTL
    assert cfg.keyops_family is KeyOpsFamily.VECTOR
