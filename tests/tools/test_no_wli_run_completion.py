from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.run_completion import (
    finalize_run_outputs,
)


pytestmark = pytest.mark.tier_a


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_finalize_run_outputs_prefers_full_artifact_for_best_instance(
    tmp_path: Path,
) -> None:
    root = tmp_path
    run_dir = root / "output" / "run"
    final_dir = run_dir / "final_instances"
    best_dir = run_dir / "best"
    hist_path = root / "history.csv"
    run_manifest_path = run_dir / "run_manifest.json"
    hist_path.write_text("", encoding="utf-8")

    best_row = {
        "tier": "fixture_fixture_001_p9_c3_l1000",
        "text_id": 0,
        "key_seed": 511,
        "best_match_ratio": 0.761,
        "preview_best_latin": "PREVIEW TEXT",
        "truth_key_hamming_total": 17,
    }
    artifact_name = "fixture_fixture_001_p9_c3_l1000__text0__seed511.json"
    _write_json(
        final_dir / artifact_name,
        {
            "best_match_ratio": 0.761,
            "stage3_diagnostics": {"phaseC_start_summaries": [{"start_idx": 1}]},
            "truth_diagnostics": {"available": True, "key_hamming_total": 17},
            "target_key_idx": [1, 2, 3],
            "stage3_topk": [{"rank": 1, "match_ratio": 0.761}],
        },
    )

    def _write_snapshots(*, run_dir: Path, instances, stages, summary) -> None:
        _write_json(run_dir / "summary.json", summary)
        _write_json(run_dir / "instances.json", list(instances))
        _write_json(run_dir / "stages.json", list(stages))

    finalize_run_outputs(
        run_dir=run_dir,
        final_dir=final_dir,
        best_dir=best_dir,
        root=root,
        hist_path=hist_path,
        t0_all=0.0,
        oracle_consulted_in_decisions=False,
        total=1,
        done=1,
        status_counts={"solved": 0, "stalled": 0, "unsolved": 1, "skipped_proven": 0},
        history_rows_written=1,
        audit_rows_written=0,
        audit_prev_chain_hash="",
        tiers=[],
        instances=[best_row],
        stages=[],
        run_manifest={},
        run_manifest_path=run_manifest_path,
        write_json_fn=_write_json,
        write_pipeline_snapshot_files_fn=_write_snapshots,
        build_summary_fn=lambda _tiers, _instances: {"count": len(_instances)},
        sha256_file_fn=lambda _path: "sha256",
        format_seconds_fn=lambda seconds: f"{seconds:.1f}s",
    )

    best_instance = json.loads(
        (best_dir / "best_instance.json").read_text(encoding="utf-8")
    )
    assert best_instance["preview_best_latin"] == "PREVIEW TEXT"
    assert best_instance["target_key_idx"] == [1, 2, 3]
    assert best_instance["truth_diagnostics"]["available"] is True
    assert best_instance["stage3_diagnostics"]["phaseC_start_summaries"][0]["start_idx"] == 1
    assert best_instance["stage3_topk"][0]["rank"] == 1


def test_finalize_run_outputs_rejects_missing_status_counts(tmp_path: Path) -> None:
    root = tmp_path
    run_dir = root / "output" / "run"
    final_dir = run_dir / "final_instances"
    best_dir = run_dir / "best"
    hist_path = root / "history.csv"
    run_manifest_path = run_dir / "run_manifest.json"
    hist_path.write_text("", encoding="utf-8")

    with pytest.raises(KeyError, match="skipped_proven"):
        finalize_run_outputs(
            run_dir=run_dir,
            final_dir=final_dir,
            best_dir=best_dir,
            root=root,
            hist_path=hist_path,
            t0_all=0.0,
            oracle_consulted_in_decisions=False,
            total=1,
            done=1,
            status_counts={"solved": 0, "stalled": 0, "unsolved": 1},
            history_rows_written=1,
            audit_rows_written=0,
            audit_prev_chain_hash="",
            tiers=[],
            instances=[],
            stages=[],
            run_manifest={},
            run_manifest_path=run_manifest_path,
            write_json_fn=_write_json,
            write_pipeline_snapshot_files_fn=lambda **kwargs: None,
            build_summary_fn=lambda _tiers, _instances: {"count": len(_instances)},
            sha256_file_fn=lambda _path: "sha256",
            format_seconds_fn=lambda seconds: f"{seconds:.1f}s",
        )
