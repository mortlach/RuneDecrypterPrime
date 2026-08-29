from __future__ import annotations
from rdp import api
import pytest
from rune_decrypter_prime.core.config import InterruptorConfig
pytestmark = pytest.mark.tier_a

def test_interruptor_config_pool_defaults_to_range():
    cfg = api.InterruptorConfig.search([5, 1, 3], minimum_count=0, maximum_count=None, strategy=api.advanced.InterruptorSearchStrategy.AUTO, maximum_combinations=5000)
    assert cfg.pool == [1, 3, 5]
    assert cfg.min_count == 0
    assert cfg.max_count == 3

def test_interruptor_config_exact_rejects_pool():
    with pytest.raises(ValueError):
        api.InterruptorConfig.search([1], minimum_count=2, maximum_count=1)

def test_interruptor_config_rejects_non_full_score_mode():
    with pytest.raises(NotImplementedError):
        api.InterruptorConfig.exact([1])

def test_interruptor_config_rejects_non_fixed_value_mode():
    with pytest.raises(NotImplementedError):
        api.InterruptorConfig.exact([1])
