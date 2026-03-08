from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from tools.benchmarks.periodic_sub_trans.common.trace_writer import StageTraceWriter


def make_stage_engine_trace_emitter(*, run_dir: Path):
    writer = StageTraceWriter(output_path=run_dir / "stage_engine_trace.jsonl")

    def _emit(
        *,
        event: Mapping[str, Any],
        tier_name: str,
        text_id: int,
        key_seed: int,
    ) -> None:
        payload = dict(event)
        payload.update(
            tier=str(tier_name),
            text_id=int(text_id),
            key_seed=int(key_seed),
        )
        writer.append(payload)

    return _emit

