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
from tools.benchmarks.periodic_sub_trans.no_wli import resume_probe_utils as probe_utils


SOURCE_ARTIFACT_FALLBACK_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260324T004559684950Z__bench_solve_pipeline_no_wli__55b7159/"
    "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed211.json"
)
PREFER_LIVE_STAGE3_BUNDLE = True

VARIANTS: list[dict[str, Any]] = [
    dict(
        id="baseline_recovered_policy",
        description="Recovered narrow Stage-3 policy, saved handoff only.",
        run_config_override={},
    ),
    dict(
        id="init96_top12",
        description="Raise Stage-3 init breadth and keep more Phase-B seeds.",
        run_config_override={
            "stage3": {
                "init_keys": 96,
                "span_basin_judge": {
                    "k": 96,
                    "tie_eps": 0.005,
                    "tie_max_seeds": 24,
                },
                "two_phase": {
                    "phase_b_top_n": 12,
                },
            }
        },
    ),
    dict(
        id="init128_top16_relaxed_gates",
        description="More Stage-3 breadth plus looser Phase-B promotion gates.",
        run_config_override={
            "stage3": {
                "init_keys": 128,
                "span_basin_judge": {
                    "k": 128,
                    "tie_eps": 0.005,
                    "tie_max_seeds": 24,
                },
                "two_phase": {
                    "phase_b_top_n": 16,
                    "gate_delta_floor": 0.001,
                    "gate_end_gain_floor": 0.0,
                },
            }
        },
    ),
    dict(
        id="init128_top16_phasec10",
        description="Broader Stage-3 plus more Phase-C starts from the same handoff.",
        run_config_override={
            "stage3": {
                "init_keys": 128,
                "span_basin_judge": {
                    "k": 128,
                    "tie_eps": 0.005,
                    "tie_max_seeds": 24,
                },
                "two_phase": {
                    "phase_b_top_n": 16,
                    "gate_delta_floor": 0.001,
                    "gate_end_gain_floor": 0.0,
                    "phase_c": {
                        "start_keys": 10,
                    },
                },
            }
        },
    ),
]


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _checkpoint_summary(output_dir: Path) -> dict[str, Any]:
    return probe_utils.summarize_phasec_checkpoint_rows(
        probe_utils.load_jsonl(output_dir / "phasec_start_checkpoints.jsonl")
    )


def _variant_row(
    *,
    variant_id: str,
    description: str,
    output_dir: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    flow = dict(payload.get("stage3_flow", {}) or {})
    return dict(
        variant_id=str(variant_id),
        description=str(description),
        output_dir=resume_mod._repo_rel(output_dir),
        resume_source=str(payload.get("resume_source", "") or ""),
        bundle_dir_relpath=str(payload.get("bundle_dir_relpath", "") or ""),
        resume_best_stage=str(payload.get("resume_best_stage", "") or ""),
        resume_best_match_ratio=float(payload.get("resume_best_match_ratio", float("nan"))),
        resume_best_score=float(payload.get("resume_best_score", float("nan"))),
        best3_match=float(flow.get("best3_match", float("nan"))),
        best3_score=float(flow.get("best3_score", float("nan"))),
        stop_reason=str(flow.get("stop_reason", "") or ""),
        stage35_selected=int(flow.get("stage35_selected", 0) or 0),
        phasec_final_winner_lane=str(flow.get("phaseC_final_winner_lane", "") or ""),
        phasec_final_winner_source=str(flow.get("phaseC_final_winner_source", "") or ""),
        checkpoint_summary=_checkpoint_summary(output_dir),
        run_config_override=dict(payload.get("run_config_override", {}) or {}),
    )


def _write_report(path: Path, *, summary: Mapping[str, Any]) -> None:
    lines = [
        "# Seed 211 Stage-3 Policy Resume Probe",
        "",
        f"Source artifact: `{summary['source_artifact_relpath']}`",
        f"Source selection: `{summary['source_selection_reason']}`",
        f"Selected bundle source: `{summary['selected_bundle_source']}`",
        "",
        "| Variant | Resume Match | Resume Score | Stop Reason | Checkpoint Best Truth | Checkpoint Best Score Match |",
        "| --- | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in list(summary.get("variants", []) or []):
        checkpoint = dict(row.get("checkpoint_summary", {}) or {})
        lines.append(
            "| "
            + str(row.get("variant_id", ""))
            + " | "
            + f"{float(row.get('resume_best_match_ratio', float('nan'))):.3f}"
            + " | "
            + f"{float(row.get('resume_best_score', float('nan'))):.6f}"
            + " | "
            + str(row.get("stop_reason", ""))
            + " | "
            + (
                f"{float(checkpoint.get('best_truth_match', float('nan'))):.3f}"
                if int(checkpoint.get("row_count", 0) or 0) > 0
                else "n/a"
            )
            + " | "
            + (
                f"{float(checkpoint.get('best_score_match', float('nan'))):.3f}"
                if int(checkpoint.get("row_count", 0) or 0) > 0
                else "n/a"
            )
            + " |"
        )
    _write_text(path, "\n".join(lines) + "\n")


def main() -> None:
    source_info = probe_utils.resolve_probe_source_artifact(
        fallback_artifact_path=SOURCE_ARTIFACT_FALLBACK_PATH,
        key_seed=211,
        prefer_live_stage3_bundle=bool(PREFER_LIVE_STAGE3_BUNDLE),
    )
    case = resume_mod.load_artifact_case(artifact_path=Path(source_info["artifact_path"]))
    root_dir = resume_mod.OUTPUT_ROOT / f"{resume_mod._utc_label()}_seed211_stage3_policy_probe"
    root_dir.mkdir(parents=True, exist_ok=True)

    variant_rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        variant_id = str(variant["id"])
        output_dir = root_dir / variant_id
        payload = resume_mod.run_stage3_resume_from_artifact(
            case,
            output_dir=output_dir,
            run_config_override=dict(variant.get("run_config_override", {}) or {}),
            enable_stage35=False,
        )
        resume_mod.write_resume_bundle(payload, output_dir=output_dir)
        variant_rows.append(
            _variant_row(
                variant_id=variant_id,
                description=str(variant.get("description", "") or ""),
                output_dir=output_dir,
                payload=payload,
            )
        )

    summary = dict(
        probe="seed211_stage3_policy_probe",
        source_artifact_relpath=resume_mod._repo_rel(case.artifact_path),
        run_config_relpath=resume_mod._repo_rel(case.run_config_path),
        source_selection_reason=str(source_info.get("selection_reason", "") or ""),
        selected_bundle_source=str(source_info.get("selected_bundle_source", "") or ""),
        source_manifest_relpath=str(source_info.get("selected_manifest_relpath", "") or ""),
        live_bundle_candidate_count=int(source_info.get("live_bundle_candidate_count", 0) or 0),
        live_bundle_candidate_relpaths=list(source_info.get("live_bundle_candidate_relpaths", []) or []),
        output_dir=resume_mod._repo_rel(root_dir),
        variants=variant_rows,
    )
    resume_mod._write_json(root_dir / "summary.json", summary)
    _write_report(root_dir / "report.md", summary=summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
