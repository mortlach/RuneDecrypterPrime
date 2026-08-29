"""Guardrails for permutation-based solvers (GA / SA)."""
from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from tests.tutorials._utils import plaintext_match_rate
from tests._helpers.permutation_cases import columnar_roundtrip_case
pytestmark = pytest.mark.tier_a

def _assert_is_permutation(vec: np.ndarray):
    arr = np.asarray(vec, dtype=np.uint8).reshape(-1)
    assert np.unique(arr).size == arr.size, f'Key must be bijective (got {arr})'

def test_ga_permutation_solver_respects_seed_and_bijection():
    """
    GA must keep permutation keys bijective and benefit from seeded initial keys.
    """
    ct_idx, pt_idx, wli, perm, direction = columnar_roundtrip_case()
    solver = api.SolverSpec.genetic_algorithm(population_size=32, generations=24, elite_fraction=0.15, mutation_probability=0.25, seed=9001)
    seeded = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=tuple(int(value) for value in ct_idx), word_lengths=wli), cipher=api.CipherSpec.columnar(columns=len(perm), alphabet_size=29), key_space=api.KeySpec.permutation(length=len(perm)), solver=solver, scoring=api.ScoringConfig(), initial_keys=(tuple(int(value) for value in perm),), telemetry_enabled=False, text_direction=direction))
    random = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=tuple(int(value) for value in ct_idx), word_lengths=wli), cipher=api.CipherSpec.columnar(columns=len(perm), alphabet_size=29), key_space=api.KeySpec.permutation(length=len(perm)), solver=solver, scoring=api.ScoringConfig(), telemetry_enabled=False, text_direction=direction))
    _assert_is_permutation(seeded.key)
    _assert_is_permutation(random.key)
    seeded_match = plaintext_match_rate(seeded.plaintext, pt_idx)
    random_match = plaintext_match_rate(random.plaintext, pt_idx)
    assert seeded_match >= 0.95, f'Seeded GA must recover plaintext (>95%), got {seeded_match:.3f}'
    assert seeded_match >= random_match - 1e-06, f'Seed advantage vanished (seeded={seeded_match:.3f}, random={random_match:.3f})'

def test_sa_permutation_solver_preserves_bijection_and_reaches_quality():
    """
    SA neighbour / acceptance logic must keep permutation structure intact and reach a strong score.
    """
    ct_idx, pt_idx, wli, perm, direction = columnar_roundtrip_case()
    solver = api.SolverSpec.simulated_annealing(iterations=320, initial_temperature=0.7, minimum_temperature=0.001, cooling_rate=0.995, automatic_cooling=True, seed=4242)
    sol = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=tuple(int(value) for value in ct_idx), word_lengths=wli), cipher=api.CipherSpec.columnar(columns=len(perm), alphabet_size=29), key_space=api.KeySpec.permutation(length=len(perm)), solver=solver, scoring=api.ScoringConfig(), initial_keys=(tuple(int(value) for value in perm),), telemetry_enabled=False, text_direction=direction))
    _assert_is_permutation(sol.key)
    match_rate = plaintext_match_rate(sol.plaintext, pt_idx)
    assert match_rate >= 0.9, f'SA expected >=90% plaintext match, got {match_rate:.3f}'
