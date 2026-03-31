from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


RESUME_MODE = "stage2_to_stage3"
SOURCE_ARTIFACT_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260321T190828084704Z__bench_solve_pipeline_no_wli__55b7159/"
    "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json"
)
ENABLE_STAGE35_IN_STAGE3_RESUME = False
STAGE35_CFG_OVERRIDE: dict[str, Any] | None = None


def main() -> None:
    case = resume_mod.load_artifact_case(artifact_path=SOURCE_ARTIFACT_PATH)
    output_dir = resume_mod.make_resume_output_dir(case, mode=RESUME_MODE)

    if str(RESUME_MODE) == "stage2_to_stage3":
        payload = resume_mod.run_stage3_resume_from_artifact(
            case,
            output_dir=output_dir,
            enable_stage35=bool(ENABLE_STAGE35_IN_STAGE3_RESUME),
            stage35_cfg_override=STAGE35_CFG_OVERRIDE,
        )
    elif str(RESUME_MODE) == "stage3_to_stage35":
        payload = resume_mod.run_stage35_resume_from_artifact(
            case,
            stage35_cfg_override=STAGE35_CFG_OVERRIDE,
        )
    else:
        raise ValueError(f"Unsupported RESUME_MODE: {RESUME_MODE}")

    resume_mod.write_resume_bundle(payload, output_dir=output_dir)
    print(
        json.dumps(
            dict(
                mode=str(payload.get("mode", "")),
                artifact_relpath=str(payload.get("artifact_relpath", "")),
                run_config_relpath=str(payload.get("run_config_relpath", "")),
                output_dir=resume_mod._repo_rel(output_dir),
                resume_best_stage=str(payload.get("resume_best_stage", "")),
                resume_best_match_ratio=payload.get("resume_best_match_ratio"),
                resume_best_score=payload.get("resume_best_score"),
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
