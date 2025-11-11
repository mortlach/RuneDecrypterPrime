# repo/tests/api_contract/test_normalize_scorer_and_optimizer_enums.py
import pytest

from rune_decrypter_prime.api.normalize import (
    normalize_scorer_impl, normalize_optimizer_name
)

from rune_decrypter_prime.core.types import Direction, ScorerImpl, SolverName  # sanity import for package


@pytest.mark.parametrize("inp,exp", [
    ("numpy", ScorerImpl.NUMPY),
    ("torch", ScorerImpl.TORCH),
    ("unified", ScorerImpl.UNIFIED),
    ("auto", ScorerImpl.AUTO),
])
def test_normalize_scorer_impl_accepts_string(inp, exp):
    out = normalize_scorer_impl(inp)
    # For now we assert the canonical string value (Enum.value when you add it)
    assert out == exp

@pytest.mark.parametrize("inp,exp", [
    (ScorerImpl.NUMPY, "numpy"),
    (ScorerImpl.TORCH, "torch"),
    (ScorerImpl.UNIFIED, "unified"),
    (ScorerImpl.AUTO, "auto"),
])
def test_normalize_scorer_impl_accepts_enum_like(inp, exp):
    out = normalize_scorer_impl(inp)
    assert getattr(out, "value", out) == exp

@pytest.mark.parametrize("inp,exp", [
    ("beam", SolverName.BEAM),
    ("ga", SolverName.GA),
    ("sa", SolverName.SA),
    ("hybrid", SolverName.HYBRID),
])
def test_normalize_optimizer_name_accepts_string(inp, exp):
    out = normalize_optimizer_name(inp)
    assert out == exp

@pytest.mark.parametrize("inp,exp", [
    (SolverName.BEAM, "beam"),
    (SolverName.GA, "ga"),
    (SolverName.SA, "sa"),
    (SolverName.HYBRID, "hybrid"),
])
def test_normalize_optimizer_name_accepts_enum_like(inp, exp):
    out = normalize_optimizer_name(inp)
    assert getattr(out, "value", out) == exp
