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
