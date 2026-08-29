from __future__ import annotations
from rdp import api
import importlib
import json
from pathlib import Path
import pytest
from rune_decrypter_prime.core.config.logging_config import LoggingConfig
from rune_decrypter_prime.core.config.solution import Solution

def _solution() -> Solution:
    return Solution(key=[1, 2], plaintext=[0, 1], score=3.5)

def _base_kwargs(**overrides):
    kwargs = {'text': [0], 'cipher': api.CipherSpec.periodic_substitution(period=1), 'key': api.KeySpec.repeating(length=1), 'solver': api.SolverSpec.beam_search(width=2, seed=7, rounds=0), 'telemetry_on': False}
    kwargs.update(overrides)
    return kwargs

def _minimal_spec(*, logging=None) -> api.RunSpec:
    return api.RunSpec(problem_input=api.RawTextInput('abc'), cipher=api.CipherSpec.periodic_substitution(period=1), key_space=api.KeySpec.repeating(length=1), solver=api.SolverSpec.beam_search(width=2, seed=7, rounds=0), logging=logging, telemetry_enabled=False)

def _run_with_fake_execute(monkeypatch, tmp_path: Path, *, solution: Solution | None=None):
    run_module = importlib.import_module('rdp.api.run')
    captured = {'execute': []}

    def fake_execute_run(**kwargs):
        captured['execute'].append(kwargs)
        if kwargs['initialize_logging']:
            (tmp_path / 'config').mkdir(parents=True, exist_ok=True)
            (tmp_path / 'artifacts').mkdir(parents=True, exist_ok=True)
            (tmp_path / 'META.json').write_text('{}\n', encoding='utf-8')
            (tmp_path / 'config' / 'logging.json').write_text('{}\n', encoding='utf-8')
        return solution or _solution()
    monkeypatch.setattr(run_module, 'execute_run', fake_execute_run)
    monkeypatch.setattr(run_module.logging_state, 'get_run_dir', lambda: tmp_path)
    return captured

def _manifest_payload(run_dir: Path) -> dict[str, object]:
    path = run_dir / 'artifacts' / 'run_artifacts_manifest.json'
    return json.loads(path.read_text(encoding='utf-8'))

def test_default_runapi_writes_no_manifest(monkeypatch, tmp_path: Path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)
    api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=()), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=1), solver=api.SolverSpec.beam_search(width=1, rounds=0), scoring=api.ScoringConfig()))
    assert not (tmp_path / 'artifacts' / 'run_artifacts_manifest.json').exists()

def test_logging_dict_write_manifest_initializes_and_writes(monkeypatch, tmp_path: Path) -> None:
    captured = _run_with_fake_execute(monkeypatch, tmp_path)
    api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=()), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=1), solver=api.SolverSpec.beam_search(width=1, rounds=0), scoring=api.ScoringConfig()))
    assert captured['execute'][0]['initialize_logging'] is True
    cfg = captured['execute'][0]['logging_config']
    assert isinstance(cfg, LoggingConfig)
    assert cfg.write_run_artifacts_manifest is True
    payload = _manifest_payload(tmp_path)
    assert payload['manifest_version'] == 'api_run_artifacts.v1'

def test_logging_config_write_manifest_writes(monkeypatch, tmp_path: Path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)
    api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=()), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=1), solver=api.SolverSpec.beam_search(width=1, rounds=0), scoring=api.ScoringConfig()))
    assert (tmp_path / 'artifacts' / 'run_artifacts_manifest.json').exists()

def test_write_manifest_false_alone_does_not_initialize(monkeypatch, tmp_path: Path) -> None:
    captured = _run_with_fake_execute(monkeypatch, tmp_path)
    api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=()), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=1), solver=api.SolverSpec.beam_search(width=1, rounds=0), scoring=api.ScoringConfig()))
    assert captured['execute'][0]['initialize_logging'] is False
    assert captured['execute'][0]['logging_config'] is None
    assert not (tmp_path / 'artifacts' / 'run_artifacts_manifest.json').exists()

@pytest.mark.parametrize('value', [1, 0, 'true'])
def test_write_manifest_requires_exact_bool(monkeypatch, value) -> None:
    _run_with_fake_execute(monkeypatch, Path('unused'))
    with pytest.raises(TypeError, match='write_run_artifacts_manifest'):
        api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=()), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=1), solver=api.SolverSpec.beam_search(width=1, rounds=0), scoring=api.ScoringConfig()))

def test_logging_config_rejects_non_bool_write_manifest() -> None:
    with pytest.raises(TypeError, match='write_run_artifacts_manifest'):
        api.LoggingConfig(write_artifact_manifest=1)

def test_runspec_logging_write_manifest_writes(monkeypatch, tmp_path: Path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)
    spec = _minimal_spec(logging=api.LoggingConfig(write_event_log=False, write_artifact_manifest=True))
    api.run(spec)
    assert (tmp_path / 'artifacts' / 'run_artifacts_manifest.json').exists()

def test_runspec_rejects_outside_logging_write_manifest(monkeypatch, tmp_path: Path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match='write_run_artifacts_manifest'):
        api.run(_minimal_spec())

def test_write_solver_report_alone_does_not_write_manifest(monkeypatch, tmp_path: Path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)
    api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=()), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=1), solver=api.SolverSpec.beam_search(width=1, rounds=0), scoring=api.ScoringConfig()))
    assert (tmp_path / 'artifacts' / 'solver_report.json').exists()
    assert not (tmp_path / 'artifacts' / 'run_artifacts_manifest.json').exists()

def test_both_sidecars_write_solver_report_first_and_manifest_includes_row(monkeypatch, tmp_path: Path) -> None:
    _run_with_fake_execute(monkeypatch, tmp_path)
    api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=()), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=1), solver=api.SolverSpec.beam_search(width=1, rounds=0), scoring=api.ScoringConfig()))
    assert (tmp_path / 'artifacts' / 'solver_report.json').exists()
    payload = _manifest_payload(tmp_path)
    rows = payload['rows']
    assert isinstance(rows, list)
    assert [row['relpath'] for row in rows] == ['META.json', 'config/logging.json', 'artifacts/solver_report.json']

def test_manifest_only_path_does_not_build_solver_report(monkeypatch, tmp_path: Path) -> None:
    run_module = importlib.import_module('rdp.api.run')
    _run_with_fake_execute(monkeypatch, tmp_path)

    def fail_builder(**_kwargs):
        raise AssertionError('SolverReport should not be built')
    monkeypatch.setattr(run_module, 'build_solver_report', fail_builder)
    api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=()), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=1), solver=api.SolverSpec.beam_search(width=1, rounds=0), scoring=api.ScoringConfig()))
    assert (tmp_path / 'artifacts' / 'run_artifacts_manifest.json').exists()

def test_manifest_write_failure_is_not_silently_dropped(monkeypatch, tmp_path: Path) -> None:
    run_module = importlib.import_module('rdp.api.run')
    _run_with_fake_execute(monkeypatch, tmp_path)

    def fail_writer(*_args, **_kwargs):
        raise RuntimeError('manifest write failed')
    monkeypatch.setattr(run_module, 'write_run_artifacts_manifest_file', fail_writer)
    with pytest.raises(RuntimeError, match='manifest write failed'):
        api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=()), cipher=api.CipherSpec.vigenere(), key_space=api.KeySpec.repeating(length=1), solver=api.SolverSpec.beam_search(width=1, rounds=0), scoring=api.ScoringConfig()))
