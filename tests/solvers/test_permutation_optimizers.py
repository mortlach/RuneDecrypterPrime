"""Guardrails for permutation-based solvers (GA / SA)."""
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, Direction, by_name
from tests.tutorials._utils import plaintext_match_rate
from tests._helpers.permutation_cases import columnar_roundtrip_case

pytestmark = pytest.mark.tier_a


def _assert_is_permutation(vec: np.ndarray):
    arr = np.asarray(vec, dtype=np.uint8).reshape(-1)
    assert np.unique(arr).size == arr.size, f"Key must be bijective (got {arr})"


def test_ga_permutation_solver_respects_seed_and_bijection():
    """
    GA must keep permutation keys bijective and benefit from seeded initial keys.
    """
    ct_idx, pt_idx, wli, perm, direction = columnar_roundtrip_case()

    solver = SolverSpec.ga(
        pop_size=32,
        generations=24,
        elite_frac=0.15,
        mut_prob=0.25,
        log_interval=0,
        progress_pct=1,
        seed=9001,
    )

    seeded = RunAPI.run(
        text=ct_idx,
        cipher=by_name.cipher("columnar", key_len=len(perm)),
        key=KeySpec.permutation(len=len(perm)),
        solver=solver,
        encoding_dir=direction,
        telemetry_on=False,
        wli_data=wli,
        initial_keys=[perm.tolist()],
    )

    random = RunAPI.run(
        text=ct_idx,
        cipher=by_name.cipher("columnar", key_len=len(perm)),
        key=KeySpec.permutation(len=len(perm)),
        solver=solver,
        encoding_dir=direction,
        telemetry_on=False,
        wli_data=wli,
    )

    _assert_is_permutation(seeded.key)
    _assert_is_permutation(random.key)

    seeded_match = plaintext_match_rate(seeded.plaintext_idx, pt_idx)
    random_match = plaintext_match_rate(random.plaintext_idx, pt_idx)

    assert seeded_match >= 0.95, f"Seeded GA must recover plaintext (>95%), got {seeded_match:.3f}"
    assert seeded_match >= random_match - 1e-6, (
        f"Seed advantage vanished (seeded={seeded_match:.3f}, random={random_match:.3f})"
    )


def test_sa_permutation_solver_preserves_bijection_and_reaches_quality():
    """
    SA neighbour / acceptance logic must keep permutation structure intact and reach a strong score.
    """
    ct_idx, pt_idx, wli, perm, direction = columnar_roundtrip_case()

    solver = SolverSpec.sa(
        sa_iters=320,
        sa_init_temp=0.7,
        sa_min_temp=1e-3,
        sa_cooling=0.995,
        sa_auto_cooling=True,
        sa_elitism=True,
        log_interval=0,
        progress_pct=1,
        seed=4242,
    )

    sol = RunAPI.run(
        text=ct_idx,
        cipher=by_name.cipher("columnar", key_len=len(perm)),
        key=KeySpec.permutation(len=len(perm)),
        solver=solver,
        encoding_dir=direction,
        telemetry_on=False,
        wli_data=wli,
        initial_keys=[perm.tolist()],
    )

    _assert_is_permutation(sol.key)
    match_rate = plaintext_match_rate(sol.plaintext_idx, pt_idx)

    assert match_rate >= 0.9, f"SA expected >=90% plaintext match, got {match_rate:.3f}"
    assert sol.score >= 0.3, f"SA score should stay healthy, got {sol.score:.3f}"
