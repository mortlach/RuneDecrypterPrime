from __future__ import annotations

import pytest

from rune_decrypter_prime.core.config import InterruptorConfig

pytestmark = pytest.mark.tier_a


def test_interruptor_config_pool_defaults_to_range():
    cfg = InterruptorConfig(mode="pool", pool=[5, 1, 3])
    assert cfg.pool == [1, 3, 5]
    assert cfg.min_count == 0
    assert cfg.max_count == 3


def test_interruptor_config_exact_rejects_pool():
    with pytest.raises(ValueError):
        InterruptorConfig(mode="exact", exact=[1], pool=[2])
