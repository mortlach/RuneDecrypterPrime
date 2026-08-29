"""Telemetry guardrails for solver spans."""
from __future__ import annotations
from rdp import api
import pytest
from rune_decrypter_prime.telemetry.pipeline import make_pipeline_block
from tests._helpers.permutation_cases import columnar_roundtrip_case
pytestmark = pytest.mark.tier_a

def _solver_factory(name: str):
    if name == 'beam':
        return api.SolverSpec.beam_search(width=2, seed=111, rounds=0)
    if name == 'ga':
        return api.SolverSpec.genetic_algorithm(population_size=16, generations=10, mutation_probability=0.2, elite_fraction=0.2, seed=222)
    if name == 'sa':
        return api.SolverSpec.simulated_annealing(iterations=120, initial_temperature=0.6, minimum_temperature=0.001, cooling_rate=0.99, automatic_cooling=True, seed=333)
    raise ValueError(name)

@pytest.mark.parametrize('solver_name', ['beam', 'ga', 'sa'])
def test_solver_spans_include_pipeline_block(solver_name: str):
    ct_idx, _, wli, perm, direction = columnar_roundtrip_case()
    solver = _solver_factory(solver_name)
    custom_perm = tuple(reversed(range(len(ct_idx))))
    sol = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(
                indices=tuple(int(value) for value in ct_idx), word_lengths=wli
            ),
            cipher=api.CipherSpec.columnar(columns=len(perm), alphabet_size=29),
            key_space=api.KeySpec.permutation(length=len(perm)),
            solver=solver,
            scoring=api.ScoringConfig(),
            initial_keys=(tuple(int(value) for value in perm),),
            telemetry_enabled=True,
            text_direction=direction,
            text_permutation=custom_perm,
        )
    )
    telemetry = sol.telemetry
    assert telemetry, "Telemetry missing from solution meta"
    expected_pipeline = make_pipeline_block(
        text_encoding_direction=direction,
        ciphertext_len=len(ct_idx),
        text_permutation=custom_perm,
    )
    assert telemetry.get("pipeline") == expected_pipeline
    assert telemetry.get("run", {}).get("pipeline") == expected_pipeline
    spans = telemetry.get("solver_spans", {})
    assert solver_name in spans, f"Missing solver span for {solver_name}"
    span_pipeline = spans[solver_name]["result"].get("pipeline")
    assert span_pipeline == expected_pipeline, f"{solver_name} span lost pipeline block"
