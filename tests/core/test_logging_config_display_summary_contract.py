from __future__ import annotations
from rdp import api
import json
import os
from pathlib import Path
import pytest
from rdp.core.config.logging_config import init_logging

def test_logging_config_accepts_display_summary_flag(tmp_path: Path) -> None:
    cfg = api.LoggingConfig(
        output_root=tmp_path / "output",
        run_category="tests",
        label="display-summary",
        portable_output=True,
        write_display_summary=True,
    )
    run_dir = init_logging(cfg)
    snap = json.loads((run_dir / "config" / "logging.json").read_text(encoding="utf-8"))
    assert snap["write_display_summary"] is True
    assert not os.path.isabs(snap["output_root"])


def test_logging_config_rejects_non_bool_display_summary_flag() -> None:
    with pytest.raises(TypeError, match="write_display_summary must be a bool"):
        api.LoggingConfig(write_display_summary=1)
