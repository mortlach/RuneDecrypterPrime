from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from rune_decrypter_prime.core.config import logging_config as logging_config
from rune_decrypter_prime.core.config.logging_config import LoggingConfig


def _assert_local_path(value: str) -> None:
    assert value, "path string must be non-empty"
    assert not os.path.isabs(value), f"{value} should be relative"


def test_meta_and_snapshot_paths_are_repo_local():
    repo_root = Path(__file__).resolve().parents[1]
    out_root = repo_root / "output" / "__test_relpaths__"
    shutil.rmtree(out_root, ignore_errors=True)

    prev_paths = logging_config.current_paths()

    try:
        cfg = LoggingConfig(
            repo_root=str(repo_root),
            out_root=str(out_root),
            run_kind="tests",
            label="pytest",
            verbose=False,
            print_progress=False,
            write_jsonl=False,
        )
        run_dir = logging_config.init_logging(cfg)

        meta = json.loads((run_dir / "META.json").read_text(encoding="utf-8"))
        assert meta["repo_root"] == "."
        _assert_local_path(meta["out_root"])
        assert Path(meta["python"]["executable"]).name == meta["python"]["executable"]
        for pointer in meta["pointers"].values():
            _assert_local_path(pointer)

        snap = json.loads((run_dir / "config" / "logging.json").read_text(encoding="utf-8"))
        assert snap["repo_root"] == "."
        _assert_local_path(snap["out_root"])
        if snap.get("fixed_run_dir"):
            _assert_local_path(snap["fixed_run_dir"])
    finally:
        logging_config._PATHS.clear()
        logging_config._PATHS.update(prev_paths)
        shutil.rmtree(out_root, ignore_errors=True)


def _init_test_logging(repo_root: Path, out_root: Path, **overrides):
    cfg = LoggingConfig(
        repo_root=str(repo_root),
        out_root=str(out_root),
        run_kind="tests",
        label="pytest",
        verbose=False,
        print_progress=False,
        write_jsonl=False,
        **overrides,
    )
    run_dir = logging_config.init_logging(cfg)
    meta = json.loads((run_dir / "META.json").read_text(encoding="utf-8"))
    snap = json.loads((run_dir / "config" / "logging.json").read_text(encoding="utf-8"))
    return meta, snap


def test_logging_config_default_identity_behavior_is_unchanged():
    repo_root = Path(__file__).resolve().parents[1]
    out_root = repo_root / "output" / "__test_identity_default__"
    shutil.rmtree(out_root, ignore_errors=True)
    prev_paths = logging_config.current_paths()

    try:
        meta, snap = _init_test_logging(repo_root, out_root)

        assert meta["portable_output"] is False
        assert meta["identity_redacted"] is False
        assert meta["user"] is not None
        assert meta["host"] is not None
        assert snap["portable_output"] is False
    finally:
        logging_config._PATHS.clear()
        logging_config._PATHS.update(prev_paths)
        shutil.rmtree(out_root, ignore_errors=True)


def test_logging_config_portable_output_redacts_identity():
    repo_root = Path(__file__).resolve().parents[1]
    out_root = repo_root / "output" / "__test_portable_identity__"
    shutil.rmtree(out_root, ignore_errors=True)
    prev_paths = logging_config.current_paths()

    try:
        meta, snap = _init_test_logging(repo_root, out_root, portable_output=True)

        assert meta["portable_output"] is True
        assert meta["identity_redacted"] is True
        assert meta["user"] is None
        assert meta["host"] is None
        assert snap["portable_output"] is True
    finally:
        logging_config._PATHS.clear()
        logging_config._PATHS.update(prev_paths)
        shutil.rmtree(out_root, ignore_errors=True)


def test_logging_config_redact_identity_still_redacts_without_portable_output():
    repo_root = Path(__file__).resolve().parents[1]
    out_root = repo_root / "output" / "__test_redact_identity__"
    shutil.rmtree(out_root, ignore_errors=True)
    prev_paths = logging_config.current_paths()

    try:
        meta, snap = _init_test_logging(repo_root, out_root, redact_identity=True)

        assert meta["portable_output"] is False
        assert meta["identity_redacted"] is True
        assert meta["user"] is None
        assert meta["host"] is None
        assert snap["portable_output"] is False
        assert snap["redact_identity"] is True
    finally:
        logging_config._PATHS.clear()
        logging_config._PATHS.update(prev_paths)
        shutil.rmtree(out_root, ignore_errors=True)
