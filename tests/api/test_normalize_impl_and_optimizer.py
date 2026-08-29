"""
Why: We want the API to accept declared choices (strings) or Enums at inputs,
      while core runs on typed values. This test nails the contract in one place.
Proves: api.normalize has helpers for scorer impl and optimizer name that return Enums.
"""
from rdp import api
import rdp.api.normalize
import pytest
from rune_decrypter_prime.core.types import ScorerImpl, SolverName

@pytest.mark.parametrize('inp,expect', [(ScorerImpl.NUMPY, ScorerImpl.NUMPY), ('numpy', ScorerImpl.NUMPY), ('torch', ScorerImpl.TORCH), ('unified', ScorerImpl.UNIFIED), ('auto', ScorerImpl.AUTO)])
def test_normalize_scorer_impl(inp, expect):
    assert rdp.api.normalize.normalize_scorer_impl(inp) is expect

@pytest.mark.parametrize('bad', ['np', 'tp', 0, object()])
def test_normalize_scorer_impl_bad(bad):
    with pytest.raises(Exception):
        rdp.api.normalize.normalize_scorer_impl(bad)

@pytest.mark.parametrize('inp,expect', [(SolverName.BEAM, SolverName.BEAM), ('beam', SolverName.BEAM), ('ga', SolverName.GA), ('sa', SolverName.SA), ('hybrid', SolverName.HYBRID)])
def test_normalize_optimizer_name(inp, expect):
    assert rdp.api.normalize.normalize_optimizer_name(inp) is expect

@pytest.mark.parametrize('bad', ['anneal', 'genetic', 42])
def test_normalize_optimizer_name_bad(bad):
    with pytest.raises(Exception):
        rdp.api.normalize.normalize_optimizer_name(bad)
