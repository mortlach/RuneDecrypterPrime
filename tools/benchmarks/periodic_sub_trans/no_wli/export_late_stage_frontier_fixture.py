from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_frontier_fixture import (
    build_late_stage_frontier_fixture,
    write_late_stage_frontier_fixture,
)


ARTIFACT_PATH = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "20260331T075915341627Z__bench_solve_pipeline_no_wli__55b7159"
    / "final_instances"
    / "fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
)
FIXTURE_ID = "v45_seed411_late_frontier"
OUTPUT_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "late_stage_frontier_fixtures"
)
OUTPUT_PATH = OUTPUT_DIR / f"{FIXTURE_ID}.json"
SUMMARY_PATH = OUTPUT_DIR / f"{FIXTURE_ID}.md"


def main() -> None:
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    fixture = build_late_stage_frontier_fixture(
        artifact_path=ARTIFACT_PATH,
        artifact=artifact,
        fixture_id=FIXTURE_ID,
    )
    write_late_stage_frontier_fixture(
        fixture=fixture,
        output_path=OUTPUT_PATH,
    )
    lines = [
        f"# {FIXTURE_ID}",
        "",
        f"- source artifact: `{str(ARTIFACT_PATH.relative_to(REPO_ROOT)).replace(chr(92), '/')}`",
        f"- candidate count: `{int(fixture.get('candidate_count', 0) or 0)}`",
        f"- winner hash: `{str(fixture.get('score_selected_winner_hash', '') or '')}`",
        f"- oracle-best explored hash: `{str(fixture.get('oracle_best_explored_hash', '') or '')}`",
        f"- frontier key material complete: `{int(fixture.get('frontier_key_material_complete', 0) or 0)}`",
        f"- candidates with final_key_idx: `{int(fixture.get('candidates_with_final_key_idx', 0) or 0)}`",
        f"- candidates with final_plaintext_idx: `{int(fixture.get('candidates_with_final_plaintext_idx', 0) or 0)}`",
        "",
        "This export is for scorer-fixture preparation. If frontier key material is incomplete, the saved run needs a rerun after the Phase-C frontier persistence hardening landed.",
        "",
    ]
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            dict(
                fixture_id=FIXTURE_ID,
                output_path=str(OUTPUT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                summary_path=str(SUMMARY_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                candidate_count=int(fixture.get("candidate_count", 0) or 0),
                frontier_key_material_complete=int(
                    fixture.get("frontier_key_material_complete", 0) or 0
                ),
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
