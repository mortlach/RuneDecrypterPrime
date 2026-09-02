from __future__ import annotations
from rdp import api
from types import SimpleNamespace
import numpy as np
import pytest
from rdp.core.types import Device, Direction, ObjectiveFamily, ObjectiveSpec, Stat
from rdp.keyops.vector import VectorKeyOps
from rune_decrypter_prime.solvers.ga import GASolver
from rune_decrypter_prime.solvers.hybrid import HybridSolver
from rune_decrypter_prime.solvers.sa import SASolver
pytestmark = pytest.mark.tier_a

class _TinyProblem:

    def __init__(self) -> None:
        self.keyops = VectorKeyOps(1, mod=3)
        self.c_cfg = SimpleNamespace(device=Device.CPU, encoding_dir=Direction.LTR, wli_data=None)
        self.scorer = SimpleNamespace(objective=ObjectiveSpec(ObjectiveFamily.PCT, Stat.LOGP, 1))
        self.telemetry = {}

    def evaluate_keys(self, keys):
        batch = np.asarray(keys, dtype=np.uint8).reshape(-1, 1)
        return -np.abs(batch[:, 0].astype(float) - 2.0)

    def resolve_plaintext(self, key):
        return np.asarray(key, dtype=np.uint8).reshape(-1)


@pytest.mark.parametrize("value", [0, -1])
def test_public_ga_rejects_non_positive_generations(value):
    with pytest.raises(ValueError, match="generations must be >= 1"):
        api.SolverSpec.genetic_algorithm(population_size=4, generations=value)


@pytest.mark.parametrize("value", [0, -1])
def test_public_sa_rejects_non_positive_iterations(value):
    with pytest.raises(ValueError, match="iterations must be >= 1"):
        api.SolverSpec.simulated_annealing(iterations=value)

def test_public_hybrid_rejects_nested_non_positive_budgets():
    with pytest.raises(ValueError, match="generations must be >= 1"):
        api.SolverSpec.genetic_algorithm(population_size=4, generations=0)
    with pytest.raises(ValueError, match="iterations must be >= 1"):
        api.SolverSpec.simulated_annealing(iterations=0)

@pytest.mark.parametrize(('solver_cls', 'field', 'value'), [(GASolver, 'generations', 0), (GASolver, 'generations', -1), (SASolver, 'iters', 0), (SASolver, 'iters', -1)])
def test_direct_solver_boundary_rejects_non_positive_budgets(solver_cls, field, value):
    with pytest.raises(ValueError, match=f'{field} must be greater than zero'):
        solver_cls(_TinyProblem(), opt_cfg={field: value, 'pop_size': 4}, rng=np.random.default_rng(7), seed_keys=[[0]], verbose=False, log_interval=0)

def test_direct_hybrid_forwards_nested_budget_validation():
    ga_invalid = HybridSolver(_TinyProblem(), opt_cfg={'ga': {'generations': 0}, 'use_beam': False}, rng=np.random.default_rng(7), seed_keys=[[0]], verbose=False, log_interval=0)
    with pytest.raises(ValueError, match='generations must be greater than zero'):
        ga_invalid.solve()
    sa_invalid = HybridSolver(_TinyProblem(), opt_cfg={'ga': {'generations': 1, 'pop_size': 4}, 'sa': {'iters': 0}, 'use_beam': False}, rng=np.random.default_rng(7), seed_keys=[[0]], verbose=False, log_interval=0)
    with pytest.raises(ValueError, match='iters must be greater than zero'):
        sa_invalid.solve()

@pytest.mark.parametrize('builder', [lambda value: api.SolverSpec.genetic_algorithm(population_size=4, generations=value), lambda value: api.SolverSpec.simulated_annealing(iterations=value)])
def test_public_budget_types_are_strict(builder):
    for value in (True, 1.0, 'one'):
        with pytest.raises(TypeError):
            builder(value)

def test_positive_one_executes_exactly_one_ga_and_sa_iteration():
    ga = GASolver(_TinyProblem(), opt_cfg={'pop_size': 4, 'generations': 1}, rng=np.random.default_rng(11), seed_keys=[[0]], verbose=False, log_interval=0).solve()
    sa = SASolver(_TinyProblem(), opt_cfg={'iters': 1}, rng=np.random.default_rng(11), seed_keys=[[0]], verbose=False, log_interval=0).solve()
    assert np.isfinite(float(ga.score))
    assert np.isfinite(float(sa.score))
