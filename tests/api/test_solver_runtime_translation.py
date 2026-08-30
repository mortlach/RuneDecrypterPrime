from __future__ import annotations

import pytest

from rdp import api
from rdp.api.run import _runtime_solver_config


def _runtime(spec: api.SolverSpec):
    return _runtime_solver_config(spec, effective_seed=spec.seed or 0)


def test_beam_translation_owns_every_public_field() -> None:
    runtime = _runtime(api.SolverSpec.beam_search(
        width=31,
        rounds=7,
        restarts=3,
        expansion=api.advanced.BeamExpansionMode.SAMPLE,
        maximum_children_per_parent=19,
        sample_per_parent=11,
        top_parents_fraction=0.4,
        plateau_rounds=5,
        plateau_minimum_delta=0.002,
        target_score=0.75,
        seed=101,
    ))

    assert runtime.name == "beam"
    assert runtime.seed == 101
    assert runtime.params == {
        "beam_width": 31,
        "rounds": 7,
        "restarts": 3,
        "expand_mode": "sample",
        "expand.max_children_per_parent": 19,
        "sample_per_parent": 11,
        "top_parents_factor": 0.4,
        "plateau_rounds": 5,
        "plateau_min_delta": 0.002,
        "stop_score": 0.75,
    }


def test_genetic_algorithm_translation_owns_every_public_field() -> None:
    runtime = _runtime(api.SolverSpec.genetic_algorithm(
        population_size=91,
        generations=37,
        elite_fraction=0.12,
        mutation_probability=0.23,
        crossover_fraction=0.81,
        tournament_size=6,
        plateau_generations=13,
        plateau_minimum_delta=0.003,
        target_score=0.76,
        seed=102,
    ))

    assert runtime.name == "ga"
    assert runtime.seed == 102
    assert runtime.params == {
        "pop_size": 91,
        "generations": 37,
        "elite_frac": 0.12,
        "mut_prob": 0.23,
        "cx_frac": 0.81,
        "tournament_k": 6,
        "plateau_rounds": 13,
        "plateau_min_delta": 0.003,
        "stop_score": 0.76,
    }


def test_simulated_annealing_translation_owns_every_public_field() -> None:
    runtime = _runtime(api.SolverSpec.simulated_annealing(
        iterations=4321,
        initial_temperature=0.91,
        minimum_temperature=0.004,
        cooling_rate=0.997,
        automatic_cooling=True,
        reseed_interval=123,
        local_improvement_on_accept=True,
        rescue_drop_absolute=0.05,
        rescue_drop_ratio=0.4,
        plateau_iterations=77,
        plateau_minimum_delta=0.004,
        target_score=0.77,
        seed=103,
    ))

    assert runtime.name == "sa"
    assert runtime.seed == 103
    assert runtime.params == {
        "iters": 4321,
        "T0": 0.91,
        "Tmin": 0.004,
        "cool": 0.997,
        "auto_cooling": True,
        "sa_reseed_interval": 123,
        "local_improve_on_accept": True,
        "sa_rescue_drop_abs": 0.05,
        "sa_rescue_drop_ratio": 0.4,
        "plateau_rounds": 77,
        "plateau_min_delta": 0.004,
        "stop_score": 0.77,
    }


def test_hybrid_translation_preserves_nested_specs_and_seeds() -> None:
    ga = api.SolverSpec.genetic_algorithm(
        population_size=41,
        generations=17,
        elite_fraction=0.13,
        mutation_probability=0.24,
        crossover_fraction=0.82,
        tournament_size=5,
        plateau_generations=9,
        plateau_minimum_delta=0.005,
        target_score=0.71,
        seed=201,
    )
    sa = api.SolverSpec.simulated_annealing(
        iterations=765,
        initial_temperature=0.83,
        minimum_temperature=0.006,
        cooling_rate=0.994,
        automatic_cooling=False,
        reseed_interval=88,
        local_improvement_on_accept=True,
        rescue_drop_absolute=0.06,
        rescue_drop_ratio=0.3,
        plateau_iterations=66,
        plateau_minimum_delta=0.006,
        target_score=0.72,
        seed=202,
    )
    runtime = _runtime(api.SolverSpec.hybrid(
        genetic_algorithm=ga,
        simulated_annealing=sa,
        use_beam_search=True,
        beam_width=29,
        beam_rounds=8,
        beam_expansion=api.advanced.BeamExpansionMode.SAMPLE,
        sample_per_parent=14,
        top_parents_fraction=0.45,
        plateau_rounds=12,
        plateau_minimum_delta=0.007,
        target_score=0.78,
        seed=104,
    ))

    assert runtime.name == "hybrid"
    assert runtime.seed == 104
    assert runtime.params == {
        "ga": {
            "pop_size": 41,
            "generations": 17,
            "elite_frac": 0.13,
            "mut_prob": 0.24,
            "cx_frac": 0.82,
            "tournament_k": 5,
            "plateau_rounds": 9,
            "plateau_min_delta": 0.005,
            "stop_score": 0.71,
            "seed": 201,
        },
        "sa": {
            "iters": 765,
            "T0": 0.83,
            "Tmin": 0.006,
            "cool": 0.994,
            "auto_cooling": False,
            "sa_reseed_interval": 88,
            "local_improve_on_accept": True,
            "sa_rescue_drop_abs": 0.06,
            "sa_rescue_drop_ratio": 0.3,
            "plateau_rounds": 66,
            "plateau_min_delta": 0.006,
            "stop_score": 0.72,
            "seed": 202,
        },
        "use_beam": True,
        "beam_width": 29,
        "rounds": 8,
        "beam.expand_mode": "sample",
        "beam.sample_per_parent": 14,
        "beam.top_parents_factor": 0.45,
        "plateau_rounds": 12,
        "plateau_min_delta": 0.007,
        "stop_score": 0.78,
    }


@pytest.mark.parametrize(
    ("policy", "runtime_policy"),
    [
        (api.advanced.KaedingSlipPolicy.FIXED_INTERVAL, "fixed"),
        (api.advanced.KaedingSlipPolicy.ON_STALL, "stall"),
    ],
)
def test_kaeding_translation_owns_every_public_field(policy, runtime_policy) -> None:
    runtime = _runtime(api.SolverSpec.kaeding(
        steps=432,
        restarts=4,
        inner_batch_size=55,
        block_schedule=api.advanced.KaedingBlockSchedule.RANDOM,
        column_batch_size=66,
        column_interval=7,
        slip_blocks=2,
        slip_interval=8,
        slip_policy=policy,
        slip_swaps=9,
        stall_rounds=10,
        stall_slip_limit=3,
        stop_after_stall_slip_limit=True,
        plateau_rounds=11,
        plateau_minimum_delta=0.008,
        target_score=0.79,
        seed=105,
    ))

    assert runtime.name == "kaeding"
    assert runtime.seed == 105
    assert runtime.params == {
        "steps": 432,
        "restarts": 4,
        "inner_batch": 55,
        "block_schedule": "random",
        "col_batch": 66,
        "col_every": 7,
        "slip_blocks": 2,
        "slip_every": 8,
        "slip_policy": runtime_policy,
        "slip_swaps": 9,
        "stall_rounds": 10,
        "stall_slip_limit": 3,
        "stall_stop_on_limit": True,
        "plateau_rounds": 11,
        "plateau_min_delta": 0.008,
        "stop_score": 0.79,
    }
