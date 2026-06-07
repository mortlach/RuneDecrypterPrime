from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_common_resume_runner_v1 import (  # noqa: E402
    attempted_sample_ids,
    completed_sample_ids,
    config_hash,
    safe_sample_file_id,
    validate_resume_config,
    write_csv,
    write_json_atomic,
)


RUN_LABEL = "phaseB_strict_o3_o4_fwd_joint_resume_smoke_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / RUN_LABEL


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def part_path(sample_id: str) -> Path:
    return OUTPUT_DIR / "sample_joint_hit_parts" / f"{safe_sample_file_id(sample_id)}.csv"


def run() -> dict[str, object]:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {
        "run_label": RUN_LABEL,
        "direction": "fwd",
        "orders": [3, 4],
        "dictionary_cut": "strict",
        "report_only": True,
    }
    current_hash = config_hash(cfg)
    sample_fields = ["sample_id", "config_hash", "source_kind", "model_name", "damage_level", "repeat_index"]
    summary_fields = [*sample_fields, "commit_status"]
    part_fields = ["sample_id", "config_hash", "part_status"]
    committed = "chunk0|clean|none||r0"
    attempted_only = "chunk0|damaged|burst_substitution|0.30|r0"
    write_csv(OUTPUT_DIR / "sample_rows.csv", [
        {"sample_id": committed, "config_hash": current_hash, "source_kind": "clean", "model_name": "none", "damage_level": "", "repeat_index": 0},
        {"sample_id": attempted_only, "config_hash": current_hash, "source_kind": "damaged", "model_name": "burst_substitution", "damage_level": "0.30", "repeat_index": 0},
    ], sample_fields)
    write_csv(OUTPUT_DIR / "sample_joint_summary_rows.csv", [
        {"sample_id": committed, "config_hash": current_hash, "source_kind": "clean", "model_name": "none", "damage_level": "", "repeat_index": 0, "commit_status": "complete"},
    ], summary_fields)
    old_part = part_path(attempted_only)
    old_part.parent.mkdir(parents=True, exist_ok=True)
    write_csv(old_part, [{"sample_id": attempted_only, "config_hash": current_hash, "part_status": "old_incomplete"}], part_fields)
    write_json_atomic(OUTPUT_DIR / "run_manifest.json", {**cfg, "config_hash": current_hash, "status": "interrupted_fixture"})

    validate_resume_config(OUTPUT_DIR / "sample_joint_summary_rows.csv", OUTPUT_DIR / "run_manifest.json", current_hash)
    before_completed = completed_sample_ids(OUTPUT_DIR / "sample_joint_summary_rows.csv", current_hash)
    before_attempted = attempted_sample_ids(OUTPUT_DIR / "sample_rows.csv", current_hash)
    to_retry = sorted(before_attempted - before_completed)
    skipped = sorted(before_completed)
    removed_parts = 0
    rebuilt_parts = 0
    for sample_id in to_retry:
        p = part_path(sample_id)
        if p.exists():
            p.unlink()
            removed_parts += 1
        write_csv(p, [{"sample_id": sample_id, "config_hash": current_hash, "part_status": "rebuilt"}], part_fields)
        rebuilt_parts += 1
    write_csv(OUTPUT_DIR / "sample_joint_summary_rows.csv", [
        {"sample_id": committed, "config_hash": current_hash, "source_kind": "clean", "model_name": "none", "damage_level": "", "repeat_index": 0, "commit_status": "complete"},
        {"sample_id": attempted_only, "config_hash": current_hash, "source_kind": "damaged", "model_name": "burst_substitution", "damage_level": "0.30", "repeat_index": 0, "commit_status": "complete"},
    ], summary_fields)
    after_completed = completed_sample_ids(OUTPUT_DIR / "sample_joint_summary_rows.csv", current_hash)
    duplicate_commits = len(after_completed) != 2
    final = {
        **cfg,
        "config_hash": current_hash,
        "status": "pass" if not duplicate_commits and to_retry == [attempted_only] and skipped == [committed] and removed_parts == 1 and rebuilt_parts == 1 else "fail",
        "finished_utc": utc_now(),
        "committed_samples_skipped": skipped,
        "attempted_only_samples_retried": to_retry,
        "incomplete_parts_removed": removed_parts,
        "parts_rebuilt": rebuilt_parts,
        "duplicate_summary_commits": duplicate_commits,
    }
    write_json_atomic(OUTPUT_DIR / "final_summary.json", final)
    write_json_atomic(OUTPUT_DIR / "run_state.json", {**final, "updated_utc": utc_now()})
    print(json.dumps(final, indent=2, sort_keys=True))
    if final["status"] != "pass":
        raise SystemExit(1)
    return final


if __name__ == "__main__":
    run()
