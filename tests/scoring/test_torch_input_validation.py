from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Direction, ScorerImpl
from rune_decrypter_prime.scoring.windowing import START_TAG, END_TAG

pytestmark = pytest.mark.tier_a


def _mk_torch_scorer(*, use_wli: bool):
    pytest.importorskip("torch")
    cfg_c = CipherConfig(
        ciphertext=[0],
        wli_data=[],
        key_length=None,
        encoding_dir=Direction.LTR,
    )
    cfg_s = ScoringConfig(
        impl=ScorerImpl.TORCH,
        encoding_dir=Direction.LTR,
        include_char=True,
        use_word_breaks=use_wli,
        n_char=2,
        n_wli=2,
        dtype="float32",
    )
    return build_scorer(cfg_c, cfg_s)


def test_torch_rejects_boundary_tags_in_nose():
    scorer = _mk_torch_scorer(use_wli=False)
    pt = np.array([1, START_TAG, 3, END_TAG, 5], dtype=np.uint8)
    with pytest.raises(ValueError, match="NOSE input must not include boundary tags"):
        scorer.batch_score([pt])


def test_torch_rejects_token_out_of_range():
    scorer = _mk_torch_scorer(use_wli=False)
    pt = np.array([0, 31, 2, 3], dtype=np.int64)
    with pytest.raises(ValueError, match="rune tokens in \\[0..30\\]"):
        scorer.batch_score([pt])


def test_torch_rejects_wli_out_of_range():
    scorer = _mk_torch_scorer(use_wli=True)
    pt = np.array([0, 1, 2, 3], dtype=np.uint8)
    wli = np.array([[0, 4], [1, 4], [2, 4], [3, 64]], dtype=np.uint8)
    with pytest.raises(ValueError, match="WLI entries must be <= 63"):
        scorer.batch_score([pt], wli)
