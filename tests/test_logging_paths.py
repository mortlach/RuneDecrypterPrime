from __future__ import annotations
from rdp import api
import json
import os
import shutil
from pathlib import Path
import rdp.core.config.logging_config as logging_config

def _assert_local_path(value: str) -> None:
    assert value, 'path string must be non-empty'
    assert not os.path.isabs(value), f'{value} should be relative'

def test_meta_and_snapshot_paths_are_repo_local():
    repo_root = Path(__file__).resolve().parents[1]
    out_root = repo_root / 'output' / '__test_relpaths__'
    shutil.rmtree(out_root, ignore_errors=True)
    prev_paths = logging_config.current_paths()
    try:
        cfg = api.LoggingConfig(
            output_root=out_root,
            run_category="tests",
            label="pytest",
            verbose=False,
            show_progress=False,
            write_event_log=False,
        )
        run_dir = logging_config.init_logging(cfg)
        meta = json.loads((run_dir / 'META.json').read_text(encoding='utf-8'))
        assert meta['repo_root'] == '.'
        _assert_local_path(meta['out_root'])
        assert Path(meta['python']['executable']).name == meta['python']['executable']
        for pointer in meta['pointers'].values():
            _assert_local_path(pointer)
        snap = json.loads(
            (run_dir / "config" / "logging.json").read_text(encoding="utf-8")
        )
        _assert_local_path(snap["output_root"])
        if snap.get("run_directory"):
            _assert_local_path(snap["run_directory"])
    finally:
        logging_config._PATHS.clear()
        logging_config._PATHS.update(prev_paths)
        shutil.rmtree(out_root, ignore_errors=True)

def _init_test_logging(repo_root: Path, out_root: Path, **overrides):
    cfg = api.LoggingConfig.from_dict(
        {
            "output_root": str(out_root),
            "run_category": "tests",
            "label": "pytest",
            "verbose": False,
            "show_progress": False,
            "write_event_log": False,
            "portable_output": False,
            **overrides,
        }
    )
    run_dir = logging_config.init_logging(cfg)
    meta = json.loads((run_dir / 'META.json').read_text(encoding='utf-8'))
    snap = json.loads((run_dir / 'config' / 'logging.json').read_text(encoding='utf-8'))
    return (meta, snap)


def test_logging_config_explicit_nonportable_identity_behavior():
    repo_root = Path(__file__).resolve().parents[1]
    out_root = repo_root / 'output' / '__test_identity_default__'
    shutil.rmtree(out_root, ignore_errors=True)
    prev_paths = logging_config.current_paths()
    try:
        meta, snap = _init_test_logging(repo_root, out_root)
        assert meta["portable_output"] is False
        assert meta["identity_redacted"] is False
        assert meta["user"] is not None
        assert meta["host"] is not None
        assert snap["portable_output"] is False
        assert snap["write_solver_report"] is False
        assert snap["write_artifact_manifest"] is False
    finally:
        logging_config._PATHS.clear()
        logging_config._PATHS.update(prev_paths)
        shutil.rmtree(out_root, ignore_errors=True)

def test_logging_config_portable_output_redacts_identity():
    repo_root = Path(__file__).resolve().parents[1]
    out_root = repo_root / 'output' / '__test_portable_identity__'
    shutil.rmtree(out_root, ignore_errors=True)
    prev_paths = logging_config.current_paths()
    try:
        meta, snap = _init_test_logging(repo_root, out_root, portable_output=True)
        assert meta['portable_output'] is True
        assert meta['identity_redacted'] is True
        assert meta['user'] is None
        assert meta['host'] is None
        assert snap['portable_output'] is True
    finally:
        logging_config._PATHS.clear()
        logging_config._PATHS.update(prev_paths)
        shutil.rmtree(out_root, ignore_errors=True)

def test_logging_config_redact_identity_still_redacts_without_portable_output():
    repo_root = Path(__file__).resolve().parents[1]
    out_root = repo_root / 'output' / '__test_redact_identity__'
    shutil.rmtree(out_root, ignore_errors=True)
    prev_paths = logging_config.current_paths()
    try:
        meta, snap = _init_test_logging(repo_root, out_root, redact_identity=True)
        assert meta['portable_output'] is False
        assert meta['identity_redacted'] is True
        assert meta['user'] is None
        assert meta['host'] is None
        assert snap['portable_output'] is False
        assert snap['redact_identity'] is True
    finally:
        logging_config._PATHS.clear()
        logging_config._PATHS.update(prev_paths)
        shutil.rmtree(out_root, ignore_errors=True)
