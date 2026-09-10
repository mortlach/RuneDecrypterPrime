from __future__ import annotations
import rdp.api.pipeline
from rdp import api
import importlib
import json
from types import SimpleNamespace
import numpy as np
import pytest
import rdp.core.config.logging_config as logging_config
from rdp.core.config.cipher import CipherConfig
from rdp.core.config.logging_config import LoggingConfig
from rdp.core.config.solver import SolverConfig
from rdp.core.types import Device, Direction

def _minimal_cipher_config() -> CipherConfig:
    return CipherConfig(ciphertext=np.asarray([0], dtype=np.uint8), wli_data=None, key_length=1, name='vigenere', device=Device.CPU, encoding_dir=api.TextDirection.LTR)

def _run_logging_route(monkeypatch, logging, *, progress_callback=None):
    captured = {}

    def fake_execute_run(**kwargs):
        captured.update(kwargs)
        return 'ok'
    run_module = importlib.import_module('rdp.api.run')
    monkeypatch.setattr(run_module, 'execute_run', fake_execute_run)
    result = api.run(
        api.RunSpec(
            problem_input=api.RuneInput(value=[0]),
            cipher=api.CipherSpec.vigenere(),
            key_space=api.KeySpec.repeating(length=1),
            solver=api.SolverSpec.beam_search(width=1, seed=1, rounds=None),
            scoring=api.ScoringConfig(),
            logging=logging,
            telemetry_enabled=False,
            text_direction=api.TextDirection.LTR,
        ),
        progress_callback=progress_callback,
    )
    assert isinstance(result, api.RunResult)
    return captured

def test_run_logging_none_does_not_initialize(monkeypatch):
    captured = _run_logging_route(monkeypatch, None)
    assert captured['logging_config'] is None
    assert captured['logging_runtime'] == {}
    assert captured['initialize_logging'] is False

def test_run_progress_controls_do_not_initialize_logging(monkeypatch):
    callback = lambda _event: None
    captured = _run_logging_route(
        monkeypatch,
        None,
        progress_callback=callback,
    )
    assert captured['logging_config'] is None
    assert captured['logging_runtime'] == {'progress_callback': callback}
    assert captured['initialize_logging'] is False

def test_run_rejects_untyped_logging_dictionary(monkeypatch):
    with pytest.raises(TypeError, match='logging'):
        _run_logging_route(monkeypatch, {})

def test_run_typed_logging_config_initializes(monkeypatch, tmp_path):
    cfg = api.LoggingConfig(
        output_root=tmp_path,
        run_category='tests',
        portable_output=True,
    )
    captured = _run_logging_route(monkeypatch, cfg)
    assert isinstance(captured['logging_config'], LoggingConfig)
    assert captured['logging_config'].portable_output is True
    assert captured['logging_config'].run_category == 'tests'
    assert captured['logging_runtime'] == {}
    assert captured['initialize_logging'] is True

@pytest.mark.parametrize('value', [1, 0, 'true'])
def test_logging_config_rejects_non_bool_write_solver_report(value):
    with pytest.raises(TypeError, match='write_solver_report'):
        api.LoggingConfig(write_solver_report=value)

@pytest.mark.parametrize('value', [1, 0, 'true'])
def test_logging_config_rejects_non_bool_write_artifact_manifest(value):
    with pytest.raises(TypeError, match='write_artifact_manifest'):
        api.LoggingConfig(write_artifact_manifest=value)

def test_run_logging_config_instance_initializes(monkeypatch, tmp_path):
    cfg = api.LoggingConfig(output_root=tmp_path, run_category='tests')
    captured = _run_logging_route(monkeypatch, cfg)
    assert captured['logging_config'] is cfg
    assert captured['logging_runtime'] == {}
    assert captured['initialize_logging'] is True

def test_logging_parser_is_reserved_for_serialized_config(monkeypatch, tmp_path):
    cfg = api.LoggingConfig.from_dict({'output_root': str(tmp_path), 'run_category': 'tests'})
    captured = _run_logging_route(monkeypatch, cfg)
    assert isinstance(captured['logging_config'], LoggingConfig)
    assert captured['logging_config'].run_category == 'tests'
    assert captured['initialize_logging'] is True


@pytest.mark.parametrize('field', ['verbose', 'show_progress', 'write_event_log'])
def test_logging_parser_rejects_removed_public_fields(field):
    with pytest.raises(ValueError, match='unsupported LoggingConfig'):
        api.LoggingConfig.from_dict({field: False})


def test_remaining_logging_fields_round_trip(tmp_path):
    config = api.LoggingConfig(
        output_root=tmp_path / 'output',
        run_category='tests',
        label='round-trip',
        run_directory=tmp_path / 'run',
        redact_identity=True,
        portable_output=False,
        write_solver_report=True,
        write_display_summary=True,
        write_artifact_manifest=True,
    )

    restored = api.LoggingConfig.from_dict({
        'output_root': str(config.output_root),
        'run_category': config.run_category,
        'label': config.label,
        'run_directory': str(config.run_directory),
        'redact_identity': config.redact_identity,
        'portable_output': config.portable_output,
        'write_solver_report': config.write_solver_report,
        'write_display_summary': config.write_display_summary,
        'write_artifact_manifest': config.write_artifact_manifest,
    })

    assert restored == config

def _execute_run_for_logging(monkeypatch, *, logging_runtime, initialize_logging=False, logging_config=None):
    return rdp.api.pipeline.execute_run(ciphertext=np.array([0], dtype=np.uint8), wli=None, cipher=api.CipherSpec.vigenere(), key=api.KeySpec.repeating(length=1), solver=SolverConfig(name='beam', params={}, seed=1), scoring=api.ScoringConfig(), scorer_name='rune', logging_config=logging_config, logging_runtime=logging_runtime, initialize_logging=initialize_logging, telemetry_on=False, device=Device.CPU, encoding_dir=Direction.LTR, initial_keys=None, initial_text_permutation_indices=None, interruptors=None, interruptors_exact=None, interruptors_pool=None, interruptors_max=None)

def test_execute_run_initializes_before_materialization(monkeypatch):
    calls = []
    cfg = api.LoggingConfig()
    fake_instance = SimpleNamespace(problem=SimpleNamespace(telemetry=None), pipeline_block='pipeline')

    def fake_init_logging(logging_config):
        calls.append(('init', logging_config))

    def fake_materialize(**_kwargs):
        calls.append(('materialize', None))
        return _minimal_cipher_config()

    monkeypatch.setattr(rdp.api.pipeline, 'init_logging', fake_init_logging)
    monkeypatch.setattr(rdp.api.pipeline, 'materialize_cipher_config', fake_materialize)
    monkeypatch.setattr(rdp.api.pipeline.ProblemInstance, 'materialise', staticmethod(lambda _spec: fake_instance))
    monkeypatch.setattr(rdp.api.pipeline, 'engine_solve', lambda _instance, _cfg: 'engine')
    monkeypatch.setattr(rdp.api.pipeline, 'finalize_solution', lambda *_args, **_kwargs: 'done')
    result = _execute_run_for_logging(monkeypatch, logging_config=cfg, logging_runtime={'log_interval': 3}, initialize_logging=True)
    assert result == 'done'
    assert calls == [('init', cfg), ('materialize', None)]

def test_execute_run_portable_output_writes_redacted_meta(monkeypatch, tmp_path):
    prev_paths = logging_config.current_paths()
    cfg = api.LoggingConfig(output_root=tmp_path / 'out', run_category='tests', label='portable', portable_output=True)
    fake_instance = SimpleNamespace(problem=SimpleNamespace(telemetry=None), pipeline_block='pipeline')
    monkeypatch.setattr(rdp.api.pipeline, 'materialize_cipher_config', lambda **_kwargs: _minimal_cipher_config())
    monkeypatch.setattr(rdp.api.pipeline.ProblemInstance, 'materialise', staticmethod(lambda _spec: fake_instance))
    monkeypatch.setattr(rdp.api.pipeline, 'engine_solve', lambda _instance, _cfg: 'engine')
    monkeypatch.setattr(rdp.api.pipeline, 'finalize_solution', lambda *_args, **_kwargs: 'done')
    try:
        result = _execute_run_for_logging(monkeypatch, logging_config=cfg, logging_runtime={}, initialize_logging=True)
        run_dir = logging_config.get_run_dir()
        meta = json.loads((run_dir / 'META.json').read_text(encoding='utf-8'))
        snap = json.loads((run_dir / 'config' / 'logging.json').read_text(encoding='utf-8'))
        assert result == 'done'
        assert meta['portable_output'] is True
        assert meta['identity_redacted'] is True
        assert meta['user'] is None
        assert meta['host'] is None
        assert snap['portable_output'] is True
    finally:
        logging_config._PATHS.clear()
        logging_config._PATHS.update(prev_paths)

def test_execute_run_preserves_normal_path_runtime_controls(monkeypatch):
    callback = lambda *_args, **_kwargs: None
    captured = {}
    fake_instance = SimpleNamespace(problem=SimpleNamespace(telemetry=None), pipeline_block='pipeline')
    monkeypatch.setattr(rdp.api.pipeline, 'materialize_cipher_config', lambda **_kwargs: _minimal_cipher_config())
    monkeypatch.setattr(rdp.api.pipeline.ProblemInstance, 'materialise', staticmethod(lambda _spec: fake_instance))

    def fake_engine_solve(_instance, cfg):
        captured['log_interval'] = cfg.log_interval
        captured['progress_callback'] = cfg.progress_callback
        return 'result'

    def fake_finalize_solution(problem, result, **_kwargs):
        return {'telemetry': problem.telemetry, 'result': result}
    monkeypatch.setattr(rdp.api.pipeline, 'engine_solve', fake_engine_solve)
    monkeypatch.setattr(rdp.api.pipeline, 'finalize_solution', fake_finalize_solution)
    result = _execute_run_for_logging(monkeypatch, logging_runtime={'log_interval': 7, 'progress_callback': callback})
    assert captured['log_interval'] == 7
    assert captured['progress_callback'] is callback
    assert result['telemetry'] is None
