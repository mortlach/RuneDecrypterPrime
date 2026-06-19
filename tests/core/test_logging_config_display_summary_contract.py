from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from rune_decrypter_prime.core.config.logging_config import LoggingConfig, init_logging


def test_logging_config_accepts_display_summary_flag(tmp_path: Path) -> None:
    cfg = LoggingConfig(
        repo_root=str(tmp_path),
        out_root=str(tmp_path / "output"),
        run_kind="tests",
        label="display-summary",
        portable_output=True,
        write_rdp_display_summary=True,
    )

    run_dir = init_logging(cfg)

    snap = json.loads((run_dir / "config" / "logging.json").read_text(encoding="utf-8"))
    assert snap["write_rdp_display_summary"] is True
    assert snap["repo_root"] == "."
    assert not os.path.isabs(snap["out_root"])


def test_logging_config_rejects_non_bool_display_summary_flag() -> None:
    with pytest.raises(TypeError, match="write_rdp_display_summary must be a bool"):
        LoggingConfig(write_rdp_display_summary=1)  # type: ignore[arg-type]
