from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping


PHASEC_START_CHECKPOINT_JSONL = "phasec_start_checkpoints.jsonl"


def build_phasec_start_checkpoint_path(*, run_dir: Path) -> Path:
    return Path(run_dir) / str(PHASEC_START_CHECKPOINT_JSONL)


def build_phasec_start_checkpoint_row(
    *,
    run_id: str,
    tier_name: str,
    text_id: int,
    key_seed: int,
    summary_row: Mapping[str, Any],
) -> Dict[str, Any]:
    row = dict(summary_row)
    return dict(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        run_id=str(run_id),
        tier=str(tier_name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        stage="stage3_phaseC_start",
        match_init=row.get("init_match", None),
        match_final=row.get("final_match", None),
        score_init=row.get("init_score", None),
        score_final=row.get("final_score", None),
        **row,
    )


def append_phasec_start_checkpoint(
    *,
    path: Path | None,
    row: Mapping[str, Any],
    append_jsonl_row_fn: Callable[[Path, Dict[str, Any]], None] | None,
) -> int:
    if path is None or append_jsonl_row_fn is None:
        return 0
    append_jsonl_row_fn(Path(path), dict(row))
    return 1
