from __future__ import annotations

import pytest
from rdp import api

pytestmark = pytest.mark.tier_a


def test_scoring_config_owns_a_typed_hard_crib() -> None:
    hard_crib = api.advanced.HardCribConfig(
        enabled=True,
        mode=api.advanced.HardCribMode.HARD,
        fixed_characters={0: (1, 2)},
        per_word_allowed={0: ((1, 2),)},
        global_allowed_by_length={2: ((1, 2), (3, 4))},
    )
    config = api.ScoringConfig(hard_crib=hard_crib)
    assert config.hard_crib == hard_crib
    assert config.hard_crib.fixed_characters[0] == (1, 2)


def test_hard_crib_rejects_non_numeric_word_sequences() -> None:
    with pytest.raises((TypeError, ValueError)):
        api.advanced.HardCribConfig(per_word_allowed={0: (("A", "B"),)})


def test_hard_crib_preserves_repeated_runes() -> None:
    hard_crib = api.advanced.HardCribConfig(
        enabled=True,
        global_allowed_by_length={3: ((24, 20, 20),)},
    )
    assert api.ScoringConfig(hard_crib=hard_crib).hard_crib == hard_crib
