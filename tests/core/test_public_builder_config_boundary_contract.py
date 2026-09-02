from __future__ import annotations
from rdp import api
from types import SimpleNamespace
import pytest
from rdp.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.engine.builders import build_cipher, build_scorer

def test_build_cipher_requires_typed_cipher_config() -> None:
    with pytest.raises(TypeError, match='CipherConfig'):
        build_cipher(SimpleNamespace(name='vigenere'))
    with pytest.raises(TypeError, match='CipherConfig'):
        build_cipher({'name': 'vigenere'})

def test_build_scorer_requires_typed_cipher_config() -> None:
    with pytest.raises(TypeError, match='CipherConfig'):
        build_scorer(SimpleNamespace(ciphertext=[0, 1, 2]), api.ScoringConfig())
    with pytest.raises(TypeError, match='CipherConfig'):
        build_scorer({'ciphertext': [0, 1, 2]}, api.ScoringConfig())

def test_build_scorer_requires_typed_scoring_config() -> None:
    cfg = CipherConfig(ciphertext=[0, 1, 2], wli_data=[], key_length=3)
    with pytest.raises(TypeError, match='ScoringConfig'):
        build_scorer(cfg, SimpleNamespace(impl='numpy'))
    with pytest.raises(TypeError, match='ScoringConfig'):
        build_scorer(cfg, {'impl': 'numpy'})
