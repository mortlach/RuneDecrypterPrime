from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.core.problem import ProblemSpec, ProblemInstance
from rune_decrypter_prime.core.types import Direction
pytestmark = pytest.mark.tier_a

class _DummyScorer:
    pass

def test_permutation_reporting_uses_core_length(monkeypatch):
    ct = np.arange(6, dtype=np.uint8).tolist()
    wli = [[i, 6] for i in range(6)]
    perm = [2, 0, 5, 3, 1, 4]
    cfg = CipherConfig(ciphertext=ct, wli_data=wli, key_length=1, name='vigenere', encoding_dir=Direction.LTR, interruptors_exact=[1, 4], initial_text_permutation_indices=perm)
    monkeypatch.setattr('rune_decrypter_prime.core.engine.builders.build_scorer', lambda *args, **kwargs: _DummyScorer())
    spec = ProblemSpec(text='', text_encoding_direction=Direction.LTR, cipher_cfg=cfg, scorer_params=api.ScoringConfig(), input_permutation=perm)
    instance = ProblemInstance.materialise(spec)
    assert instance.pipeline_block['input_permutation']['length'] == 6
