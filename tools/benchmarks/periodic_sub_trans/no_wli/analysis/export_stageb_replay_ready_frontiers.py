from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_frontier_fixture import (
    build_late_stage_frontier_fixture,
    write_late_stage_frontier_fixture,
)


RUNS = (
    dict(
        fixture_id="v46_seed411_control_replay_frontier",
        artifact_path=(
            REPO_ROOT
            / "output"
            / "tools"
            / "benchmarks"
            / "periodic_sub_trans"
            / "no_wli"
            / "20260331T161234912270Z__bench_solve_pipeline_no_wli__55b7159"
            / "final_instances"
            / "fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
        ),
    ),
    dict(
        fixture_id="v46_seed411_candidate_replay_frontier",
        artifact_path=(
            REPO_ROOT
            / "output"
            / "tools"
            / "benchmarks"
            / "periodic_sub_trans"
            / "no_wli"
            / "20260331T195317037506Z__bench_solve_pipeline_no_wli__37689eb"
            / "final_instances"
            / "fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
        ),
    ),
)
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


def _fixture_summary_lines(fixture: dict[str, object]) -> list[str]:
    return [
        f"# {str(fixture.get('fixture_id', '') or '')}",
        "",
        f"- run id: `{str(fixture.get('run_id', '') or '')}`",
        f"- source artifact: `{str(fixture.get('source_artifact_path', '') or '')}`",
        f"- phaseC start policy: `{str(fixture.get('phasec_start_policy', '') or '')}`",
        f"- frontier row source: `{str(fixture.get('phasec_frontier_row_source', '') or '')}`",
        f"- checkpoint path: `{str(fixture.get('phasec_checkpoint_path', '') or '')}`",
        f"- candidate count: `{int(fixture.get('candidate_count', 0) or 0)}`",
        f"- frontier key material complete: `{int(fixture.get('frontier_key_material_complete', 0) or 0)}`",
        f"- score-selected winner hash: `{str(fixture.get('score_selected_winner_hash', '') or '')}`",
        f"- oracle-best explored hash: `{str(fixture.get('oracle_best_explored_hash', '') or '')}`",
        "",
    ]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    exported: list[dict[str, object]] = []
    for run in RUNS:
        artifact_path = Path(run["artifact_path"])
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        fixture = build_late_stage_frontier_fixture(
            artifact_path=artifact_path,
            artifact=artifact,
            fixture_id=str(run["fixture_id"]),
        )
        output_path = OUTPUT_DIR / f"{str(run['fixture_id'])}.json"
        summary_path = OUTPUT_DIR / f"{str(run['fixture_id'])}.md"
        write_late_stage_frontier_fixture(
            fixture=fixture,
            output_path=output_path,
        )
        summary_path.write_text(
            "\n".join(_fixture_summary_lines(fixture)),
            encoding="utf-8",
        )
        exported.append(
            dict(
                fixture_id=str(run["fixture_id"]),
                output_path=str(output_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                summary_path=str(summary_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                frontier_key_material_complete=int(
                    fixture.get("frontier_key_material_complete", 0) or 0
                ),
                phasec_frontier_row_source=str(
                    fixture.get("phasec_frontier_row_source", "") or ""
                ),
            )
        )
    print(json.dumps(dict(exported=exported), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
