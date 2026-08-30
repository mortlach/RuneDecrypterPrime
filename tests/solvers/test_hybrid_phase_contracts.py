from __future__ import annotations
from types import SimpleNamespace
import numpy as np
import pytest
from rune_decrypter_prime.core.types import Device, Direction, ObjectiveFamily, ObjectiveSpec, Stat
from rune_decrypter_prime.keyops.vector import VectorKeyOps
from rune_decrypter_prime.solvers.hybrid import HybridSolver
pytestmark = pytest.mark.tier_a

class _TinyProblem:

    def __init__(self, *, key_length: int=2, modulus: int=5) -> None:
        self.keyops = VectorKeyOps(key_length, mod=modulus)
        self.c_cfg = SimpleNamespace(device=Device.CPU, encoding_dir=Direction.LTR, wli_data=None)
        self.scorer = SimpleNamespace(objective=ObjectiveSpec(ObjectiveFamily.PCT, Stat.LOGP, 1))
        self.telemetry = {}
        self.target = np.arange(key_length, dtype=np.int16) + 2

    def evaluate_keys(self, keys):
        batch = np.asarray(keys, dtype=np.int16).reshape(-1, self.keyops.K)
        return -np.sum(np.abs(batch - self.target), axis=1, dtype=np.float64)

    def resolve_plaintext(self, key):
        return np.asarray(key, dtype=np.uint8).reshape(-1)

def _result(key, score, *, beam_keys=None):
    meta = {}
    if beam_keys is not None:
        meta['beam'] = {'final_keys': np.asarray(beam_keys, dtype=np.int16)}
    return SimpleNamespace(key=np.asarray(key, dtype=np.int16), score=float(score), meta=meta)

def _controlled_phase_classes(calls, *, beam_result, ga_result, sa_result, rng_draws=None):

    class Beam:

        def __init__(self, _problem, *, rng, seed_keys, **_kwargs):
            calls.append(('beam', np.asarray(seed_keys, dtype=np.int16).copy()))
            if rng_draws is not None:
                rng_draws['beam'] = rng.integers(0, 2 ** 31, size=6).tolist()

        def solve(self):
            return beam_result

    class GA:

        def __init__(self, _problem, *, rng, seed_keys, **_kwargs):
            calls.append(('ga', np.asarray(seed_keys, dtype=np.int16).copy()))
            if rng_draws is not None:
                rng_draws['ga'] = rng.integers(0, 2 ** 31, size=6).tolist()

        def solve(self):
            return ga_result

    class SA:

        def __init__(self, _problem, *, rng, seed_keys, **_kwargs):
            calls.append(('sa', np.asarray(seed_keys, dtype=np.int16).copy()))
            if rng_draws is not None:
                rng_draws['sa'] = rng.integers(0, 2 ** 31, size=6).tolist()

        def solve(self):
            return sa_result
    return (Beam, GA, SA)

def _patch_phases(monkeypatch, phase_classes):
    beam, ga, sa = phase_classes
    monkeypatch.setattr('rune_decrypter_prime.solvers.hybrid.BeamSolver', beam)
    monkeypatch.setattr('rune_decrypter_prime.solvers.hybrid.GASolver', ga)
    monkeypatch.setattr('rune_decrypter_prime.solvers.hybrid.SASolver', sa)

def test_hybrid_orders_phases_hands_beam_to_ga_and_retained_winner_to_sa(monkeypatch):
    calls = []
    beam_keys = [[1, 1], [2, 2]]
    _patch_phases(monkeypatch, _controlled_phase_classes(calls, beam_result=_result([1, 1], 5.0, beam_keys=beam_keys), ga_result=_result([3, 3], 8.0), sa_result=_result([4, 4], 7.0)))
    solution = HybridSolver(_TinyProblem(), opt_cfg={'use_beam': True}, rng=np.random.default_rng(41), seed_keys=[[0, 0]], verbose=False, log_interval=0).solve()
    assert [phase for phase, _seeds in calls] == ['beam', 'ga', 'sa']
    np.testing.assert_array_equal(calls[1][1], np.asarray(beam_keys, dtype=np.int16))
    np.testing.assert_array_equal(calls[2][1], np.asarray([[3, 3]], dtype=np.int16))
    np.testing.assert_array_equal(solution.key, np.asarray([3, 3], dtype=np.int16))
    assert solution.score == 8.0
    assert solution.meta['from_phase'] == 'ga'

def test_hybrid_weaker_ga_cannot_displace_beam_and_sa_receives_global_winner(monkeypatch):
    calls = []
    _patch_phases(monkeypatch, _controlled_phase_classes(calls, beam_result=_result([4, 4], 10.0, beam_keys=[[4, 4], [1, 1]]), ga_result=_result([2, 2], 5.0), sa_result=_result([0, 0], 4.0)))
    solution = HybridSolver(_TinyProblem(), opt_cfg={'use_beam': True}, rng=np.random.default_rng(42), seed_keys=[[0, 0]], verbose=False, log_interval=0).solve()
    np.testing.assert_array_equal(calls[2][1], np.asarray([[4, 4]], dtype=np.int16))
    np.testing.assert_array_equal(solution.key, np.asarray([4, 4], dtype=np.int16))
    assert solution.score == 10.0
    assert solution.meta['from_phase'] == 'beam'

@pytest.mark.parametrize(('stop_score', 'beam_score', 'ga_score', 'expected_phases', 'expected_key'), [(9.0, 9.0, -999.0, ['beam'], [1, 1]), (9.0, 5.0, 9.0, ['beam', 'ga'], [3, 3])])
def test_hybrid_stop_score_terminates_between_phases(monkeypatch, stop_score, beam_score, ga_score, expected_phases, expected_key):
    calls = []
    _patch_phases(monkeypatch, _controlled_phase_classes(calls, beam_result=_result([1, 1], beam_score, beam_keys=[[1, 1]]), ga_result=_result([3, 3], ga_score), sa_result=_result([4, 4], 99.0)))
    solution = HybridSolver(_TinyProblem(), opt_cfg={'use_beam': True}, rng=np.random.default_rng(43), seed_keys=[[0, 0]], stop_score=stop_score, verbose=False, log_interval=0).solve()
    assert [phase for phase, _seeds in calls] == expected_phases
    np.testing.assert_array_equal(solution.key, np.asarray(expected_key, dtype=np.int16))
    assert solution.score == stop_score

def test_hybrid_child_phase_rng_streams_repeat_and_are_phase_distinct(monkeypatch):

    def run_once():
        calls = []
        draws = {}
        _patch_phases(monkeypatch, _controlled_phase_classes(calls, beam_result=_result([1, 1], 1.0, beam_keys=[[1, 1]]), ga_result=_result([2, 2], 2.0), sa_result=_result([3, 3], 3.0), rng_draws=draws))
        HybridSolver(_TinyProblem(), opt_cfg={'use_beam': True}, rng=np.random.default_rng(4404), seed_keys=[[0, 0]], verbose=False, log_interval=0).solve()
        return draws
    first = run_once()
    second = run_once()
    assert first == second
    assert len({tuple(first[phase]) for phase in ('beam', 'ga', 'sa')}) == 3


def test_hybrid_explicit_nested_seeds_own_ga_and_sa_rng_streams(monkeypatch):
    calls = []
    draws = {}
    _patch_phases(
        monkeypatch,
        _controlled_phase_classes(
            calls,
            beam_result=_result([1, 1], 1.0, beam_keys=[[1, 1]]),
            ga_result=_result([2, 2], 2.0),
            sa_result=_result([3, 3], 3.0),
            rng_draws=draws,
        ),
    )

    HybridSolver(
        _TinyProblem(),
        opt_cfg={"use_beam": True, "ga": {"seed": 201}, "sa": {"seed": 202}},
        rng=np.random.default_rng(999),
        seed_keys=[[0, 0]],
        verbose=False,
        log_interval=0,
    ).solve()

    assert draws["ga"] == np.random.default_rng(201).integers(0, 2 ** 31, size=6).tolist()
    assert draws["sa"] == np.random.default_rng(202).integers(0, 2 ** 31, size=6).tolist()

def test_small_real_hybrid_route_runs_end_to_end():
    problem = _TinyProblem(key_length=1, modulus=3)
    solution = HybridSolver(problem, opt_cfg={'use_beam': True, 'beam_width': 3, 'rounds': 1, 'expand.parent_mode': 'all', 'ga': {'pop_size': 4, 'generations': 2, 'mut_prob': 0.5}, 'sa': {'iters': 3, 'T0': 0.5, 'Tmin': 0.1, 'cool': 0.8}}, rng=np.random.default_rng(45), seed_keys=[[0]], verbose=False, log_interval=0).solve()
    np.testing.assert_array_equal(solution.plaintext, solution.key.astype(np.uint8))
    assert solution.key.shape == (1,)
    assert 0 <= int(solution.key[0]) < 3
    assert np.isfinite(solution.score)
    assert solution.meta['from_phase'] in {'beam', 'ga', 'sa'}
