from __future__ import annotations

from pathlib import Path

import json
import pytest

from tools.benchmarks.periodic_sub_trans.col_then_sub.stage_engine_trace import (
    make_stage_engine_trace_emitter,
)


pytestmark = pytest.mark.tier_a


def test_col_then_sub_stage_engine_trace_emitter_writes_jsonl(tmp_path: Path) -> None:
    emit = make_stage_engine_trace_emitter(run_dir=tmp_path)
    emit(
        event={"event": "stage_start", "stage_id": "stage_a_sub_discovery"},
        tier_name="t1",
        text_id=0,
        key_seed=111,
    )
    emit(
        event={"event": "stage_end", "stage_id": "stage_a_sub_discovery"},
        tier_name="t1",
        text_id=0,
        key_seed=111,
    )
    trace = tmp_path / "stage_engine_trace.jsonl"
    rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["event"] == "stage_start"
    assert rows[0]["stage_id"] == "stage_a_sub_discovery"
    assert rows[0]["tier"] == "t1"

