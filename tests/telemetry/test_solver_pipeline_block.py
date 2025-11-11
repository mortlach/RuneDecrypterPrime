"""Telemetry guardrails for solver spans."""
from __future__ import annotations

import pytest

from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, by_name
from rune_decrypter_prime.telemetry.pipeline import make_pipeline_block
from rune_decrypter_prime.core.types import Direction
from tests._helpers.permutation_cases import columnar_roundtrip_case

pytestmark = pytest.mark.tier_a


def _solver_factory(name: str):
    if name == "beam":
        return SolverSpec.beam(beam_width=2, progress_pct=1, seed=111)
    if name == "ga":
        return SolverSpec.ga(pop_size=16, generations=10, mut_prob=0.2, elite_frac=0.2, progress_pct=1, seed=222)
    if name == "sa":
        return SolverSpec.sa(
            sa_iters=120,
            sa_init_temp=0.6,
            sa_min_temp=1e-3,
            sa_cooling=0.99,
            sa_auto_cooling=True,
            progress_pct=1,
            seed=333,
        )
    raise ValueError(name)


@pytest.mark.parametrize("solver_name", ["beam", "ga", "sa"])
def test_solver_spans_include_pipeline_block(solver_name: str):
    ct_idx, _, wli, perm, direction = columnar_roundtrip_case()
    solver = _solver_factory(solver_name)

    # Apply a non-trivial permutation so telemetry must record it.
    custom_perm = list(reversed(range(len(ct_idx))))

    sol = RunAPI.run(
        text=ct_idx,
        cipher=by_name.cipher("columnar", key_len=len(perm)),
        key=KeySpec.permutation(len=len(perm)),
        solver=solver,
        encoding_dir=direction,
        telemetry_on=True,
        wli_data=wli,
        initial_keys=[perm.tolist()],
        initial_text_permutation_indices=custom_perm,
    )

    telemetry = sol.meta.get("telemetry", {})
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
