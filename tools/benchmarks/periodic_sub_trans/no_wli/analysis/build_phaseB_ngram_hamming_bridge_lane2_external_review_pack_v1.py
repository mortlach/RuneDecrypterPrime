from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_bridge_lane2_external_review_pack_v1"
PACK_DIR_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "phaseB_ngram_hamming_lane1_lane2_full_review_pack_2026-05-31"
)
ZIP_REL = f"{PACK_DIR_REL}.zip"
CANON_REFERENCE_REL = (
    "planning/temp_files/ngram_scorer_june_2026_docs/"
    "rdp_ngram_phrase_coherence_v3_2_canon_review.md"
)
CONTEXT_FILES_REL = (
    "AGENTS.md",
    "planning/temp_files/ngram_scorer_june_2026_docs/deep-research-report(2).md",
    "planning/temp_files/ngram_scorer_june_2026_docs/deep-research-report(3).md",
    "planning/temp_files/ngram_scorer_june_2026_docs/deep-research-report(4).md",
    "planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_implementation_brief_v0_1.md",
    CANON_REFERENCE_REL,
    "planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_scorer_discussion_brief_2026-05-30.md",
    "planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_scorer_investigation_context_review_2026-05-30.md",
    "planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_scorer_v2_response_review_2026-05-30.md",
    "planning/temp_files/ngram_scorer_june_2026_docs/v2 .txt",
    "planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md",
    "planning/projects/no_wli/00_CURRENT_STATE.md",
    "planning/projects/no_wli/04_ACTIVE_RUNBOOK.md",
)
COMPONENT_FILES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/contract_pack_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/profile_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/profile_manifest_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/schema_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/readout.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1/input_contract_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1/input_schema_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1/synthetic_candidate_chunk_row.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1/synthetic_pair_input_row.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1/readout.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/synthetic_contract_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/profile_manifest_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/all_cluster_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/score_candidate_cluster_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/all_profile_candidate_summary_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/score_candidate_candidate_summary_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/pair_ledger_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/zero_hit_audit_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/readout.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_provenance_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/readout.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/output_file_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/missing_shard_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/missing_required_output_combo_rows.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_pack_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_checklist.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/normal_strict_row_counts.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/README.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1/readout.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1/gated_diagnostic_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1/readout.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1/launch_decision_record_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1/readout.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1/prep_status_index_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1/readout.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1/prep_bundle_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1/README.md",
)
SOURCE_FILES_REL = (
    "src/rune_decrypter_prime/scoring/ngram_hamming/reference.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/fast_backend.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/bridge.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/__init__.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_asset_shards_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/summarise_phaseB_ngram_hamming_full_raw_asset_shards_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_contract_pack_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_input_contract_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/check_phaseB_ngram_hamming_bridge_lane2_readiness_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_provenance_review_pack_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_external_review_pack_v1.py",
)
TEST_FILES_REL = (
    "tests/scoring/ngram_hamming/test_bridge_profiles_and_clusters.py",
    "tests/scoring/ngram_hamming/test_reference_ngram_hamming.py",
    "tests/tools/test_phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_bridge_lane2_contract_pack_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_bridge_lane2_input_contract_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_bridge_lane2_readiness_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_full_raw_provenance_review_pack_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1.py",
    "tests/tools/test_phaseB_ngram_hamming_bridge_lane2_external_review_pack_v1.py",
)
NO_BROAD_SCAN_LAUNCHED = True
NO_PRODUCTION_SCORER_CHANGES = True


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def copy_file(source_rel: str, pack_root: Path, section: str) -> dict[str, Any]:
    source = REPO_ROOT / source_rel
    row = {"source_path": source_rel, "exists": source.exists(), "pack_path": ""}
    if not source.exists():
        return row
    destination = pack_root / section / source_rel
    ensure_under_repo(destination)
    shutil.copy2(source, destination)
    row["pack_path"] = repo_rel(destination)
    return row


def build_external_review_pack(pack_dir: Path | None = None, zip_path: Path | None = None) -> dict[str, Any]:
    selected_pack_dir = pack_dir or (REPO_ROOT / PACK_DIR_REL)
    selected_zip_path = zip_path or (REPO_ROOT / ZIP_REL)
    reset_pack_dir(selected_pack_dir)
    copied_files: list[dict[str, Any]] = []
    for rel_path in CONTEXT_FILES_REL:
        copied_files.append(copy_file(rel_path, selected_pack_dir, "10_context"))
    for rel_path in COMPONENT_FILES_REL:
        copied_files.append(copy_file(rel_path, selected_pack_dir, "20_component_outputs"))
    for rel_path in SOURCE_FILES_REL:
        copied_files.append(copy_file(rel_path, selected_pack_dir, "30_source"))
    for rel_path in TEST_FILES_REL:
        copied_files.append(copy_file(rel_path, selected_pack_dir, "40_tests"))

    status_payloads = read_status_payloads()
    missing_files = [row["source_path"] for row in copied_files if not row["exists"]]
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "packed_with_blocks" if not missing_files else "blocked",
        "pack_dir": repo_rel(selected_pack_dir),
        "zip_path": repo_rel(selected_zip_path),
        "missing_files": missing_files,
        "copied_files": copied_files,
        "component_statuses": component_statuses(status_payloads),
        "completed_shards": status_payloads["shard_provenance"].get("completed_shards", 0),
        "total_shards": status_payloads["shard_provenance"].get("total_shards", 0),
        "bridge_broad_scan_ready": status_payloads["readiness"].get("bridge_broad_scan_ready", False),
        "launch_decision_status": status_payloads["launch_decision"].get("status", ""),
        "provenance_review_pack_status": status_payloads["provenance_review_pack"].get("status", ""),
        "no_broad_scan_launched": NO_BROAD_SCAN_LAUNCHED,
        "no_production_scorer_changes": NO_PRODUCTION_SCORER_CHANGES,
        "review_position": review_position(status_payloads),
    }
    write_summary(selected_pack_dir / "10_context" / "review_summary.md", manifest)
    write_questions(selected_pack_dir / "10_context" / "review_questions.md")
    write_json(selected_pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    make_zip(selected_pack_dir, selected_zip_path)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] zip_path={manifest['zip_path']}")
    return manifest


def reset_pack_dir(pack_dir: Path) -> None:
    resolved = pack_dir.resolve()
    resolved.relative_to(REPO_ROOT.resolve())
    if resolved.exists():
        shutil.rmtree(resolved)


def read_status_payloads() -> dict[str, dict[str, Any]]:
    return {
        "contract": read_json_if_exists(
            REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/contract_pack_manifest.json"
        ),
        "input_contract": read_json_if_exists(
            REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1/input_contract_manifest.json"
        ),
        "synthetic": read_json_if_exists(
            REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/synthetic_contract_manifest.json"
        ),
        "shard_provenance": read_json_if_exists(
            REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_provenance_manifest.json"
        ),
        "provenance_review_pack": read_json_if_exists(
            REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_pack_manifest.json"
        ),
        "readiness": read_json_if_exists(
            REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json"
        ),
        "gated": read_json_if_exists(
            REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1/gated_diagnostic_manifest.json"
        ),
        "launch_decision": read_json_if_exists(
            REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1/launch_decision_record_manifest.json"
        ),
    }


def component_statuses(payloads: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {name: str(payload.get("status", "missing")) for name, payload in sorted(payloads.items())}


def review_position(payloads: dict[str, dict[str, Any]]) -> str:
    if payloads["readiness"].get("bridge_broad_scan_ready") is True:
        return "review readiness before any real bridge scan approval switch is changed"
    return "pre-launch blocked preparation review; do not approve real bridge scans from this pack"


def write_summary(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Bridge Lane 2 Prep External Review Summary - 2026-05-31",
        "",
        "## Review Position",
        "",
        manifest["review_position"],
        "",
        "This pack covers Lane 2 preparation since the v3.2 canon/bridge discussion. It is not a full raw provenance approval, not a broad bridge scan approval, and not a production scorer change.",
        "",
        "## Current State",
        "",
        f"- completed shards in latest extracted provenance: `{manifest['completed_shards']} / {manifest['total_shards']}`",
        f"- bridge broad scan ready: `{manifest['bridge_broad_scan_ready']}`",
        f"- provenance review pack status: `{manifest['provenance_review_pack_status']}`",
        f"- launch decision status: `{manifest['launch_decision_status']}`",
        f"- broad scan launched: `{not manifest['no_broad_scan_launched']}`",
        f"- production scorer changes: `{not manifest['no_production_scorer_changes']}`",
        "",
        "## What Is Ready For Review",
        "",
        "- canonical and bridge profile authority declarations",
        "- schema contracts for profile manifests, clusters, summaries, pair ledger, zero-hit audit, candidate chunks, pair inputs, and run config",
        "- synthetic-only contract smoke and gated diagnostic scaffold",
        "- partial full raw shard provenance extraction and blocked provenance review-pack scaffold",
        "- launch decision record with hardcoded real-scan approval still false",
        "",
        "## What Remains Blocked",
        "",
        "- broad real-candidate bridge diagnostics",
        "- full hard-pair report",
        "- order-4/order-5 expansion",
        "- production scoring changes",
        "- any claim that partial shard provenance is full raw evidence",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_questions(path: Path) -> None:
    ensure_under_repo(path)
    lines = [
        "# Lane 2 External Review Questions",
        "",
        "1. Do the profile authority fields and v3.2 canon links prevent silent drift between bridge diagnostics and the destination scorer?",
        "2. Are the cluster and summary schemas sufficient for the future bridge diagnostic without letting diagnostic-only profiles shape score-candidate support?",
        "3. Is the blocked full raw provenance review-pack checklist sufficient before any broad bridge scan?",
        "4. Is the launch decision record strict enough, especially the hardcoded approval switch and post-review microbatch scope?",
        "5. What additional evidence should be added before changing any real bridge scan approval switch?",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_zip(pack_dir: Path, zip_path: Path) -> None:
    ensure_under_repo(zip_path)
    if zip_path.exists():
        zip_path.unlink()
    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in sorted(path for path in pack_dir.rglob("*") if path.is_file()):
            archive.write(file_path, file_path.relative_to(pack_dir.parent).as_posix())


def main() -> None:
    build_external_review_pack()


if __name__ == "__main__":
    main()
