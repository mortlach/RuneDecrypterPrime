from __future__ import annotations
from types import SimpleNamespace
import numpy as np
import pytest
from rdp.core.types import Direction, Device, ObjectiveFamily, ObjectiveSpec, SolverName, Stat
from rdp.solvers.solver_base import SolverBase
pytestmark = pytest.mark.tier_a

class _DummyKeyOps:

    def __init__(self, K: int):
        self.caps = SimpleNamespace(length=K)
        self.dtype = np.uint8

    def normalize(self, key):
        return np.asarray(key, dtype=np.uint8).reshape(-1)

    def random(self, rng):
        return np.zeros((self.caps.length,), dtype=np.uint8)

class _DummyProblem:

    def __init__(self, objective: ObjectiveSpec):
        self.keyops = _DummyKeyOps(1)
        self.c_cfg = SimpleNamespace(device=Device.CPU, encoding_dir=Direction.LTR)
        self.scorer = SimpleNamespace(objective=objective)

class _DummySolver(SolverBase):

    def __init__(self, problem, *, rng, seed_keys, score_map):
        self._score_map = score_map
        super().__init__(problem, optimizer_name=SolverName.BEAM, params={}, rng=rng, seed_keys=seed_keys, stop_score=None, verbose=False, log_interval=0)

    def _score_batch(self, keys):
        keys_arr = np.asarray(keys, dtype=np.uint8)
        if keys_arr.ndim == 1:
            keys_arr = keys_arr.reshape(1, -1)
        out = []
        for row in keys_arr:
            out.append(float(self._score_map[tuple((int(x) for x in row.tolist()))]))
        return np.asarray(out, dtype=np.float64)

def test_objective_direction():
    objective = ObjectiveSpec(ObjectiveFamily.NEGLOGP, Stat.LOGP, None)
    problem = _DummyProblem(objective)
    seed_keys = [np.array([0], dtype=np.uint8), np.array([1], dtype=np.uint8)]
    score_map = {(0,): 10.0, (1,): 1.0}
    rng = np.random.default_rng(0)
    solver = _DummySolver(problem, rng=rng, seed_keys=seed_keys, score_map=score_map)
    best = solver._maybe_best_of_seeds(rng)
    assert best.tolist() == [1]
