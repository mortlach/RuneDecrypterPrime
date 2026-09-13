"""Narrow named-source and ordinary Beam contracts for first-run scripts."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from rdp import api
from rdp.api.source_resolution import resolve_source_input_ref
from rdp.data.liber_primus.lp_main import main_transcript_asset_identity


def test_named_source_preserves_canonical_identity_and_resolves_existing_payload():
    source = api.liber_primus.source('welcome_pilgrim')
    assert isinstance(source, api.SourceReferenceInput)
    assert api.liber_primus.source('solved.welcome_pilgrim') == source
    assert source.asset_version == main_transcript_asset_identity()['asset_version']
    restored = api.SourceReferenceInput(**json.loads(json.dumps(dict(source_kind=source.source_kind, asset_id=source.asset_id,
        asset_version=source.asset_version, reference=dict(source.reference)))))
    assert restored == source
    resolved = resolve_source_input_ref(restored)
    source_data = api.liber_primus.load_source('welcome_pilgrim')
    assert isinstance(source_data, api.liber_primus.SourceData)
    assert source_data.indices == source_data.ct_idx
    assert source_data.word_length_information == source_data.wli
    assert resolved.ct_idx == tuple(source_data.ct_idx)
    assert resolved.wli == tuple(tuple(pair) for pair in source_data.wli)
    assert resolved.source_ref == source
    assert not hasattr(api.liber_primus, 'SolverPayload')
    assert not hasattr(api.liber_primus, 'payload_from_label')
    with pytest.raises(ValueError, match='asset_version'):
        resolve_source_input_ref(replace(source, asset_version='wrong-version'))


@pytest.mark.parametrize('label, error', [('unknown-page', KeyError), ('', ValueError), (None, ValueError)])
def test_named_source_rejects_invalid_labels(label, error):
    with pytest.raises(error):
        api.liber_primus.source(label)


def test_beam_defaults_have_the_same_serialized_request_as_explicit_settings():
    solver = api.SolverSpec.beam_search()
    assert solver == api.SolverSpec.beam_search(width=64, rounds=None, seed=None)
    assert solver.parameters["rounds"] is None
    serialized = json.loads(json.dumps(solver.to_dict()))
    restored = api.SolverSpec.from_name(serialized['kind'], parameters={**serialized['parameters'], 'seed': serialized['seed']})
    assert restored == solver
    assert restored.replay_key == solver.replay_key


def test_beam_zero_rounds_is_not_an_automatic_budget_alias():
    with pytest.raises(ValueError, match="rounds must be >= 1"):
        api.SolverSpec.beam_search(rounds=0)


@pytest.mark.parametrize('length', [3, 4])
def test_ordinary_beam_repeats_across_fixed_vector_key_lengths(length):
    request = api.RunSpec(
        problem_input=api.RuneInput('ᚠᚢᚦᚩᚱᚳᚠᚢᚦᚩᚱᚳ'),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=length),
        solver=api.SolverSpec.beam_search(),
    )
    first = api.run(request)
    second = api.run(replace(request, solver=api.SolverSpec.beam_search(width=64, rounds=None)))
    assert (first.key, first.plaintext_indices, first.score) == (second.key, second.plaintext_indices, second.score)
    assert first.solver_report.requested_seed is None
    assert first.solver_report.effective_seed == 0
    assert first.reproducibility.requested_seed is None
    assert first.reproducibility.effective_seed == 0
    assert first.solver_report.steps <= max(2 * length, 12)
    assert first.solver_report.evaluations > 0
    requested = first.configuration.solver.requested
    effective = first.configuration.solver.effective
    assert requested["parameters"]["plateau_rounds"] is None
    assert requested["parameters"]["rounds"] is None
    assert effective["parameters"]["plateau_rounds"] == 16
    assert effective["parameters"]["rounds"] == max(2 * length, 12)
    assert effective["seed"] == 0
    assert dict(first.reproducibility.solver_config) == dict(effective)


def test_sa_result_reports_runtime_defaults_and_effective_seed():
    request = api.RunSpec(
        problem_input=api.RuneInput("THERE WAS A TABLE"),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=3),
        solver=api.SolverSpec.simulated_annealing(iterations=2, seed=None),
    )

    result = api.run(request)

    requested = result.configuration.solver.requested
    effective = result.configuration.solver.effective
    assert requested["parameters"]["initial_temperature"] is None
    assert requested["parameters"]["minimum_temperature"] is None
    assert requested["parameters"]["cooling_rate"] is None
    assert effective["parameters"]["T0"] == pytest.approx(1.0)
    assert effective["parameters"]["Tmin"] == pytest.approx(0.001)
    assert effective["parameters"]["cool"] == pytest.approx(0.995)
    assert effective["parameters"]["plateau_rounds"] == 300
    assert effective["seed"] == 0
    assert result.reproducibility.requested_seed is None
    assert result.reproducibility.effective_seed == 0
    assert dict(result.reproducibility.solver_config) == dict(effective)


def test_hybrid_result_reports_resolved_child_phase_defaults():
    request = api.RunSpec(
        problem_input=api.RuneInput("THERE WAS A TABLE"),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=3),
        solver=api.SolverSpec.hybrid(
            genetic_algorithm=api.SolverSpec.genetic_algorithm(
                population_size=4,
                generations=1,
            ),
            simulated_annealing=api.SolverSpec.simulated_annealing(iterations=1),
            use_beam_search=False,
            plateau_rounds=None,
            seed=None,
        ),
    )

    result = api.run(request)

    effective = result.configuration.solver.effective
    phases = effective["parameters"]["phases"]
    assert effective["parameters"]["plateau_rounds"] == 24
    assert phases["ga"]["pop_size"] == 4
    assert phases["ga"]["generations"] == 1
    assert phases["sa"]["iters"] == 1
    assert phases["sa"]["T0"] == pytest.approx(1.0)
    assert phases["sa"]["Tmin"] == pytest.approx(0.001)
    assert phases["sa"]["cool"] == pytest.approx(0.995)


def test_packaged_transcript_identity_uses_the_staged_manifest(monkeypatch, tmp_path):
    from rdp.data.liber_primus import lp_main

    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / 'assets' / 'manifests' / 'assets_manifest_ci_light_v1.json').read_text())
    row = next(row for row in manifest['installed_assets']
               if row['asset_id'] == lp_main.MAIN_TRANSCRIPT_ASSET_ID)
    assert row['asset_version'] == main_transcript_asset_identity()['asset_version']
    package = tmp_path / 'rdp/data'
    package.mkdir(parents=True)
    (package / 'assets_manifest_ci_light_v1.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(lp_main, '__file__', str(package / 'liber_primus/lp_main.py'))

    def no_checkout(_start):
        raise FileNotFoundError('isolated installation')

    monkeypatch.setattr(lp_main, 'find_repo_root', no_checkout)
    # Bypass the process cache so this fixture cannot affect later source tests.
    identity = lp_main._cached_main_transcript_asset_identity.__wrapped__()
    assert identity == (row['asset_id'], row['asset_version'])
