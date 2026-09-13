import rdp.api.normalize
import pytest
from rdp.core.types import ScorerImpl, SolverName

@pytest.mark.parametrize('inp,exp', [('numpy', ScorerImpl.NUMPY), ('torch', ScorerImpl.TORCH), ('unified', ScorerImpl.UNIFIED), ('auto', ScorerImpl.AUTO)])
def test_normalize_scorer_impl_accepts_string(inp, exp):
    out = rdp.api.normalize.normalize_scorer_impl(inp)
    assert out == exp

@pytest.mark.parametrize('inp,exp', [(ScorerImpl.NUMPY, 'numpy'), (ScorerImpl.TORCH, 'torch'), (ScorerImpl.UNIFIED, 'unified'), (ScorerImpl.AUTO, 'auto')])
def test_normalize_scorer_impl_accepts_enum_like(inp, exp):
    out = rdp.api.normalize.normalize_scorer_impl(inp)
    assert getattr(out, 'value', out) == exp

@pytest.mark.parametrize('inp,exp', [('beam', SolverName.BEAM), ('ga', SolverName.GA), ('sa', SolverName.SA), ('hybrid', SolverName.HYBRID)])
def test_normalize_optimizer_name_accepts_string(inp, exp):
    out = rdp.api.normalize.normalize_optimizer_name(inp)
    assert out == exp

@pytest.mark.parametrize('inp,exp', [(SolverName.BEAM, 'beam'), (SolverName.GA, 'ga'), (SolverName.SA, 'sa'), (SolverName.HYBRID, 'hybrid')])
def test_normalize_optimizer_name_accepts_enum_like(inp, exp):
    out = rdp.api.normalize.normalize_optimizer_name(inp)
    assert getattr(out, 'value', out) == exp
