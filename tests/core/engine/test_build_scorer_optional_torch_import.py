from __future__ import annotations
from rdp import api
import sys
import types
import numpy as np
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device

class _FakeRuneScorer:

    def __init__(self, c_cfg, s_cfg):
        self.c_cfg = c_cfg
        self.s_cfg = s_cfg

def test_numpy_scorer_does_not_import_torch(monkeypatch):
    fake_numpy_module = types.ModuleType('rune_decrypter_prime.scoring.rune_scorer')
    fake_numpy_module.RuneScorer = _FakeRuneScorer
    monkeypatch.setitem(
        sys.modules, "rune_decrypter_prime.scoring.rune_scorer", fake_numpy_module
    )
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    scorer = build_scorer(
        CipherConfig(
            ciphertext=np.asarray([0], dtype=np.uint8),
            wli_data=None,
            key_length=None,
            device=Device.CPU,
        ),
        api.ScoringConfig(backend=api.advanced.ScorerBackend.NUMPY),
    )
    assert isinstance(scorer, _FakeRuneScorer)
    assert 'torch' not in sys.modules
