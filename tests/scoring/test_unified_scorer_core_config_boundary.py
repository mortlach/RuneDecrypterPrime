from __future__ import annotations
from rdp import api
import pytest
from rune_decrypter_prime.core.config import ScoringConfig
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.scoring.unified_rune_scorer import UnifiedRuneScorer

def _cipher_config() -> CipherConfig:
    return CipherConfig(ciphertext=[0, 1, 2], wli_data=[], key_length=3)

def test_unified_scorer_rejects_raw_cipher_config_dict() -> None:
    with pytest.raises(TypeError, match='cfg_cipher must be CipherConfig'):
        UnifiedRuneScorer({}, api.ScoringConfig())

def test_unified_scorer_rejects_raw_scoring_config_dict() -> None:
    with pytest.raises(TypeError, match='cfg_scorer must be ScoringConfig'):
        UnifiedRuneScorer(_cipher_config(), {})
