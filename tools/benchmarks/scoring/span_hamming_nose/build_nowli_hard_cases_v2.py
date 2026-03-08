from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUTPUT_JSON = REPO_ROOT / "tests/scoring/span_hamming/data/nowli_hard_cases_v2.json"


@dataclass(frozen=True)
class SelectedCase:
    artifact_relpath: str
    category: str
    note: str


SELECTED_CASES: tuple[SelectedCase, ...] = (
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p5_c1_l1000__text0__seed111.json",
        category="solved_control",
        note="Solved focus control from the canonical focus run.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p5_c3_l1000__text0__seed111.json",
        category="solved_control",
        note="Second solved focus control from the canonical focus run.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260301T021421Z__bench_solve_pipeline_no_wli__26d0fc2/final_instances/focus_p7_c3_l1000__text0__seed111.json",
        category="solved_control",
        note="Solved path-flip control for the focus_p7_c3 fixture family.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p5_c5_l1000__text0__seed111.json",
        category="false_high_basin",
        note="Known high basin that remains unsolved despite strong span-like structure.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p7_c1_l1000__text0__seed111.json",
        category="near_miss",
        note="Focus near-miss with moderate stage-3 match ratio.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p7_c5_l1000__text0__seed111.json",
        category="near_miss",
        note="Focus near-miss with later-stage progress but unsolved finish.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p9_c1_l1000__text0__seed111.json",
        category="near_miss",
        note="Higher-period focus near-miss used to widen the positive side of the unsolved set.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p9_c3_l1000__text0__seed111.json",
        category="near_miss",
        note="Another higher-period focus near-miss from stage-3 refine.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T011105Z__bench_solve_pipeline_no_wli__a023759/final_instances/scan_p7_c3_l1000__text0__seed111.json",
        category="near_miss",
        note="Scan-mode near-miss that reached stage-3 refine.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T220921Z__bench_solve_pipeline_no_wli__26d0fc2/final_instances/focus_p7_c3_l1000__text0__seed111.json",
        category="near_miss",
        note="Unsolved path-flip counterpart for the focus_p7_c3 fixture family.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p7_c3_l1000__text0__seed111.json",
        category="stalled_dead_basin",
        note="Canonical stalled focus dead-basin from stage-2 search.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p7_c7_l1000__text0__seed111.json",
        category="stalled_dead_basin",
        note="Second canonical stalled focus dead-basin from stage-2 search.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p9_c5_l1000__text0__seed111.json",
        category="stalled_dead_basin",
        note="Higher-period stalled focus dead-basin.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260227T231558Z__bench_solve_pipeline_no_wli__a023759/final_instances/scan_p7_c3_l1000__text0__seed111.json",
        category="stalled_dead_basin",
        note="Scan-mode stalled dead-basin with stage-2-only outcome.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T011105Z__bench_solve_pipeline_no_wli__a023759/final_instances/scan_p7_c7_l1000__text0__seed111.json",
        category="stalled_dead_basin",
        note="Scan-mode stalled dead-basin that timed out before stage-3.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p9_c7_l1000__text0__seed111.json",
        category="fragile_unsolved",
        note="Low-match stage-3 unsolved focus case.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260228T064036Z__bench_solve_pipeline_no_wli__e96d353/final_instances/focus_p9_c9_l1000__text0__seed111.json",
        category="fragile_unsolved",
        note="Second low-match stage-3 unsolved focus case.",
    ),
    SelectedCase(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/20260227T155741Z__bench_solve_pipeline_no_wli__1a0a6bd/final_instances/scan_p7_c7_l1000__text0__seed111.json",
        category="fragile_unsolved",
        note="Scan-mode low-match stage-3 unsolved case.",
    ),
)


def _rel_to_abs(relpath: str) -> Path:
    return (REPO_ROOT / relpath).resolve()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact_to_case(selected: SelectedCase, *, shared_target_plaintext_idx: list[int]) -> dict:
    artifact_fp = _rel_to_abs(selected.artifact_relpath)
    if not artifact_fp.exists():
        raise FileNotFoundError(f"Missing selected artifact: {artifact_fp}")
    payload = json.loads(artifact_fp.read_text(encoding="utf-8"))

    target = [int(v) for v in payload["target_plaintext_idx"]]
    if target != shared_target_plaintext_idx:
        raise ValueError(f"Target plaintext mismatch in {artifact_fp}")

    run_id = artifact_fp.parents[1].name
    tier = str(payload["tier"])
    case_id = f"{tier}__{run_id}"

    return {
        "case_id": case_id,
        "category": str(selected.category),
        "note": str(selected.note),
        "status": str(payload["status"]),
        "outcome_code": str(payload.get("outcome_code", payload["status"])),
        "best_stage": str(payload["best_stage"]),
        "best_match_ratio": float(payload["best_match_ratio"]),
        "best_score": float(payload["best_score"]),
        "length": int(payload["length"]),
        "period": int(payload["period"]),
        "columns": int(payload["columns"]),
        "text_id": int(payload["text_id"]),
        "key_seed": int(payload["key_seed"]),
        "offset_hint": int(payload["offset_hint"]),
        "offset_used": int(payload["offset_used"]),
        "source_run_id": run_id,
        "source_artifact_relpath": selected.artifact_relpath.replace("/", "\\"),
        "artifact_sha256": _sha256_bytes(artifact_fp.read_bytes()),
        "ciphertext_idx": [int(v) for v in payload["ciphertext_idx"]],
        "candidate_key_idx": [int(v) for v in payload["final_best_key_idx"]],
        "candidate_plaintext_idx": [int(v) for v in payload["final_best_plaintext_idx"]],
    }


def main() -> None:
    if OUTPUT_JSON.exists():
        OUTPUT_JSON.unlink()

    first_payload = json.loads(_rel_to_abs(SELECTED_CASES[0].artifact_relpath).read_text(encoding="utf-8"))
    shared_target_plaintext_idx = [int(v) for v in first_payload["target_plaintext_idx"]]

    cases = [_artifact_to_case(item, shared_target_plaintext_idx=shared_target_plaintext_idx) for item in SELECTED_CASES]
    source_run_ids = sorted({str(case["source_run_id"]) for case in cases})

    payload = {
        "dataset_kind": "span_hamming_nowli_hard_cases",
        "version": "v2",
        "source_run_id": "multiple",
        "source_run_ids": source_run_ids,
        "text_id": 0,
        "note": (
            "Broader frozen scorer-only corpus built from multiple reviewed no-WLI runs. "
            "True key is still not present in a clean reusable field in the saved final-instance artefacts."
        ),
        "shared_target_plaintext_idx": shared_target_plaintext_idx,
        "cases": cases,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[build_nowli_hard_cases_v2] wrote dataset: {OUTPUT_JSON}")
    print(f"[build_nowli_hard_cases_v2] cases={len(cases)} source_runs={len(source_run_ids)}")


if __name__ == "__main__":
    main()
