from __future__ import annotations

import pytest

from rune_decrypter_prime.api._resolve import resolve_scorer_aliases
from rune_decrypter_prime.core.config import ScoringConfig
from rune_decrypter_prime.core.config.hard_crib import HardCribConfig, HardCribMode


pytestmark = pytest.mark.tier_a


def test_resolve_scorer_aliases_accepts_hard_crib_key():
    out = resolve_scorer_aliases({"hard_crib": {"enabled": True, "fixed_chars": {"0": [1]}}})
    assert "hard_crib" in out


def test_resolve_scorer_aliases_accepts_avg_window_policy_key():
    out = resolve_scorer_aliases({"objective": "avg.logp.win20", "avg_window_policy": "full_text"})
    assert out["avg_window_policy"] == "full_text"


def test_scoring_config_normalizes_hard_crib_dict():
    cfg = ScoringConfig(
        hard_crib={
            "enabled": True,
            "mode": "hard",
            "fixed_chars": {"0": [1, 1, 2]},
            "per_word_allowed": {"0": [[1, 2]]},
            "global_allowed_by_len": {"2": [[1, 2], [3, 4]]},
        }
    )
    assert isinstance(cfg.hard_crib, HardCribConfig)
    assert cfg.hard_crib.mode is HardCribMode.HARD
    assert cfg.hard_crib.fixed_chars[0] == (1, 2)
    assert cfg.hard_crib.per_word_allowed[0] == ((1, 2),)
    assert cfg.hard_crib.global_allowed_by_len[2] == ((1, 2), (3, 4))


def test_scoring_config_rejects_unknown_hard_crib_fields():
    with pytest.raises(ValueError, match="Unknown hard_crib field"):
        ScoringConfig(hard_crib={"enabled": True, "bogus": 1})


def test_scoring_config_rejects_non_numeric_word_sequences():
    with pytest.raises(TypeError, match="rune indices must be integers"):
        ScoringConfig(hard_crib={"enabled": True, "per_word_allowed": {0: [["A", "B"]]}})


def test_hard_crib_preserves_repeated_runes_in_word_rules():
    cfg = ScoringConfig(
        hard_crib={
            "enabled": True,
            "global_allowed_by_len": {3: [[24, 20, 20]]},
        }
    )
    assert cfg.hard_crib is not None
    assert cfg.hard_crib.global_allowed_by_len[3] == ((24, 20, 20),)
