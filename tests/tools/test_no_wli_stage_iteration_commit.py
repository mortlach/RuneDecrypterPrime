from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.stage_iteration_commit import (
    commit_iteration_outputs,
)


pytestmark = pytest.mark.tier_a


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_commit_iteration_outputs_requires_profile_id(tmp_path: Path) -> None:
    root = tmp_path
    run_dir = root / "output" / "run"
    final_dir = run_dir / "final_instances"
    hist_path = root / "history.csv"
    hist_path.write_text("", encoding="utf-8")

    inst_row = dict(
        tier="fixture_fixture_001_p9_c3_l1000",
        text_id=0,
        key_seed=211,
        period=9,
        columns=3,
        length=1000,
        status="unsolved",
        outcome_code="unsolved",
        solve_threshold=0.9,
        best_match_ratio=0.25,
        best_stage="stage2_search",
        stage1_sub_key_match=0.1,
        stage2_match_ratio=0.25,
        stage3_match_ratio=0.0,
        total_seconds=1.0,
        total_evals=12,
        stop_reason="unsolved",
        preview_best_latin="PREVIEW",
    )

    with pytest.raises(KeyError, match="profile_id"):
        commit_iteration_outputs(
            run_dir=run_dir,
            final_dir=final_dir,
            root=root,
            hist_path=hist_path,
            tiers=[],
            instances=[],
            stages=[],
            inst_row=inst_row,
            artifact_payload={},
            done=0,
            total=1,
            t0_all=0.0,
            last_hb=0.0,
            heartbeat_seconds=60.0,
            best_global=dict(
                match=float("-inf"),
                tier="",
                text_id=-1,
                key_seed=-1,
                stage="",
                preview="",
            ),
            history_rows_written=0,
            audit_rows_written=0,
            audit_enabled=False,
            audit_csv=root / "audit.csv",
            audit_jsonl=root / "audit.jsonl",
            audit_prev_chain_hash="0" * 64,
            write_json_fn=_write_json,
            build_summary_fn=lambda _tiers, _instances: {"count": len(_instances)},
            write_pipeline_snapshot_files_fn=lambda **kwargs: None,
            append_csv_row_fn=lambda _path, _row: None,
            append_iteration_audit_row_fn=lambda **kwargs: kwargs["prev_chain_hash"],
            hash_payload_fn=lambda payload: json.dumps(payload, sort_keys=True),
            sha256_file_fn=lambda _path: "sha256",
            format_seconds_fn=lambda seconds: f"{seconds:.1f}s",
        )
