from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_checkpoint import (
    PHASEC_START_CHECKPOINT_JSONL,
)


def _read_checkpoint_rows(path: Path) -> list[Dict[str, Any]]:
    if not Path(path).exists():
        return []
    out: list[Dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not str(line).strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, Mapping):
            out.append(dict(row))
    return out


def resolve_phasec_checkpoint_path(
    *,
    artifact_path: Path,
    artifact: Mapping[str, Any],
) -> Path:
    artifact_obj = dict(artifact or {})
    stage3_diag = dict(artifact_obj.get("stage3_diagnostics", {}) or {})
    checkpoint_name = str(
        stage3_diag.get("phaseC_checkpoint_jsonl_name", "") or ""
    ).strip()
    if not checkpoint_name:
        checkpoint_name = str(PHASEC_START_CHECKPOINT_JSONL)
    return Path(artifact_path).parents[1] / checkpoint_name


def load_phasec_frontier_rows_with_source(
    *,
    artifact_path: Path,
    artifact: Mapping[str, Any],
) -> Dict[str, Any]:
    artifact_obj = dict(artifact or {})
    stage3_diag = dict(artifact_obj.get("stage3_diagnostics", {}) or {})
    summaries = [
        dict(row)
        for row in list(stage3_diag.get("phaseC_start_summaries", []) or [])
        if isinstance(row, Mapping)
    ]
    if summaries:
        return dict(
            rows=summaries,
            source="artifact",
            checkpoint_path=str(
                resolve_phasec_checkpoint_path(
                    artifact_path=artifact_path,
                    artifact=artifact_obj,
                )
            ).replace("\\", "/"),
        )

    checkpoint_path = resolve_phasec_checkpoint_path(
        artifact_path=artifact_path,
        artifact=artifact_obj,
    )
    checkpoint_rows = _read_checkpoint_rows(checkpoint_path)
    if checkpoint_rows:
        return dict(
            rows=checkpoint_rows,
            source="checkpoint",
            checkpoint_path=str(checkpoint_path).replace("\\", "/"),
        )

    return dict(
        rows=[],
        source="missing",
        checkpoint_path=str(checkpoint_path).replace("\\", "/"),
    )


def load_phasec_frontier_rows(
    *,
    artifact_path: Path,
    artifact: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    payload = load_phasec_frontier_rows_with_source(
        artifact_path=artifact_path,
        artifact=artifact,
    )
    return [dict(row) for row in list(payload.get("rows", []) or [])]
