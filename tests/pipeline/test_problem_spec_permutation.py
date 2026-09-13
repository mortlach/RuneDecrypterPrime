"""ProblemSpec-level permutation handling."""
from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rdp.core.config.cipher import CipherConfig
from rdp.core.problem.spec import ProblemSpec
from rdp.core.problem.instance import ProblemInstance
from rdp.core.types import Direction
pytestmark = pytest.mark.tier_a

def test_problem_spec_overrides_permutation_and_direction():
    length = 16
    ciphertext = np.arange(length, dtype=np.uint8).tolist()
    wli = [[i, length] for i in range(length)]
    perm = list(reversed(range(length)))
    cipher_cfg = CipherConfig(ciphertext=ciphertext, wli_data=wli, key_length=7, encoding_dir=Direction.LTR, name='vigenere', initial_text_permutation_indices=perm)
    scoring_cfg = api.ScoringConfig()
    spec = ProblemSpec(text='', text_encoding_direction=Direction.RTL, cipher_cfg=cipher_cfg, scorer_params=scoring_cfg, input_permutation=perm)
    instance = ProblemInstance.materialise(spec)
    pipeline = instance.pipeline_block
    assert pipeline['text_encoding_direction'] == 'rtl'
    perm_info = pipeline['input_permutation']
    assert perm_info['kind'] == 'custom'
    assert perm_info['length'] == length
