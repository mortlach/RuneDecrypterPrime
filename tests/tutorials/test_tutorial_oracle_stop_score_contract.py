from __future__ import annotations

import numpy as np

from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.utils import tutorial_utils


class _FakeScorer:
    def score(self, plaintext, wli) -> float:
        assert list(plaintext) == [1, 2, 3]
        assert wli == [(0, 3), (1, 3), (2, 3)]
        return 0.75


def test_tutorial_score_plaintext_passes_typed_config_objects(monkeypatch) -> None:
    calls = []

    def fake_build_scorer(cipher_cfg, scoring_cfg):
        calls.append((cipher_cfg, scoring_cfg))
        return _FakeScorer()

    monkeypatch.setattr(tutorial_utils, "build_scorer", fake_build_scorer)

    score = tutorial_utils.score_plaintext(
        np.asarray([1, 2, 3], dtype=np.uint8),
        [(0, 3), (1, 3), (2, 3)],
        {"include_char": True, "use_word_breaks": False},
        device="cpu",
    )

    assert score == 0.75
    assert len(calls) == 1
    assert isinstance(calls[0][0], CipherConfig)
    assert isinstance(calls[0][1], ScoringConfig)


def test_oracle_stop_score_reports_real_oracle_from_typed_helper(monkeypatch) -> None:
    monkeypatch.setattr(tutorial_utils, "score_plaintext", lambda *args, **kwargs: 0.82)

    result = tutorial_utils.oracle_stop_score(
        [1, 2, 3],
        None,
        {"include_char": True},
        margin=0.02,
    )

    assert result.oracle_score == 0.82
    assert result.stop_score == 0.7999999999999999
    assert result.reason == "oracle_ok"
