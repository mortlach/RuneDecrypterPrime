from __future__ import annotations
from rdp import api
import pytest
pytestmark = pytest.mark.tier_a

def test_interruptor_config_pool_defaults_to_range():
    cfg = api.InterruptorConfig.search([5, 1, 3], minimum_count=0, maximum_count=None, strategy=api.advanced.InterruptorSearchStrategy.AUTO, maximum_combinations=5000)
    assert cfg.parameters['candidate_positions'] == (1, 3, 5)
    assert cfg.parameters['minimum_count'] == 0
    assert cfg.parameters['maximum_count'] == 3

def test_interruptor_config_exact_rejects_pool():
    with pytest.raises(ValueError):
        api.InterruptorConfig.search([1], minimum_count=2, maximum_count=1)

def test_interruptor_config_exact_is_immutable_and_serializable():
    cfg = api.InterruptorConfig.exact([1])
    assert cfg.parameters['positions'] == (1,)
    assert cfg.to_dict() == {'mode': 'exact', 'parameters': {'positions': [1]}}
