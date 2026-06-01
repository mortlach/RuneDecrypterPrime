from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1"
)
COMPONENT_FILES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/contract_pack_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/schema_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/profile_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1/input_contract_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1/input_schema_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_provenance_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/synthetic_contract_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1/prep_status_index_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1/gated_diagnostic_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_pack_manifest.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_checklist.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/normal_strict_row_counts.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1/launch_decision_record_manifest.json",
)
READINESS_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json"
)
PREP_STATUS_INDEX_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1/prep_status_index_manifest.json"
)
CONTEXT_FILES_REL = (
    "planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_v3_2_canon_review.md",
    "planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md",
    "planning/projects/no_wli/00_CURRENT_STATE.md",
    "planning/projects/no_wli/04_ACTIVE_RUNBOOK.md",
)
SOURCE_FILES_REL = (
    "src/rune_decrypter_prime/scoring/ngram_hamming/reference.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/fast_backend.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/bridge.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/__init__.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/summarise_phaseB_ngram_hamming_full_raw_asset_shards_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_contract_pack_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/check_phaseB_ngram_hamming_bridge_lane2_readiness_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_input_contract_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_provenance_review_pack_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1.py",
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


def copy_file_into_bundle(source_rel: str, bundle_root: Path, section: str) -> dict[str, Any]:
    source = REPO_ROOT / source_rel
    row = {
        "source_path": source_rel,
        "exists": source.exists(),
        "bundle_path": "",
    }
    if not source.exists():
        return row
    destination = bundle_root / section / source_rel
    ensure_under_repo(destination)
    shutil.copy2(source, destination)
    row["bundle_path"] = repo_rel(destination)
    return row


def build_prep_bundle(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    copied_rows: list[dict[str, Any]] = []
    for rel_path in COMPONENT_FILES_REL:
        copied_rows.append(copy_file_into_bundle(rel_path, selected_output_dir, "10_component_outputs"))
    for rel_path in CONTEXT_FILES_REL:
        copied_rows.append(copy_file_into_bundle(rel_path, selected_output_dir, "20_context"))
    for rel_path in SOURCE_FILES_REL:
        copied_rows.append(copy_file_into_bundle(rel_path, selected_output_dir, "30_source"))

    readiness = read_json_if_exists(REPO_ROOT / READINESS_MANIFEST_REL)
    prep_index = read_json_if_exists(REPO_ROOT / PREP_STATUS_INDEX_MANIFEST_REL)
    missing = [row["source_path"] for row in copied_rows if not row["exists"]]
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not missing else "blocked",
        "missing_files": missing,
        "copied_files": copied_rows,
        "no_broad_scan_launched": NO_BROAD_SCAN_LAUNCHED,
        "no_production_scorer_changes": NO_PRODUCTION_SCORER_CHANGES,
        "bridge_broad_scan_ready": readiness.get("bridge_broad_scan_ready", False),
        "readiness_status": readiness.get("status", ""),
        "completed_shards": readiness.get("completed_shards", prep_index.get("completed_shards", 0)),
        "total_shards": readiness.get("total_shards", prep_index.get("total_shards", 0)),
        "readiness_blocked_reasons": readiness.get("blocked_reasons", []),
    }
    write_json(selected_output_dir / "prep_bundle_manifest.json", manifest)
    write_readout(selected_output_dir / "README.md", manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] copied_files={sum(1 for row in copied_rows if row['exists'])}/{len(copied_rows)}")
    return manifest


def write_readout(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Bridge Lane 2 Prep Bundle v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- bridge broad scan ready: `{manifest['bridge_broad_scan_ready']}`",
        f"- readiness status: `{manifest['readiness_status']}`",
        f"- completed shards: `{manifest['completed_shards']} / {manifest['total_shards']}`",
        f"- broad scan launched: `{not manifest['no_broad_scan_launched']}`",
        f"- production scorer changes: `{not manifest['no_production_scorer_changes']}`",
        "",
        "This bundle is a preparation handoff, not an approval pack for broad",
        "bridge diagnostics.",
    ]
    if manifest["missing_files"]:
        lines.append("")
        lines.append("Missing files:")
        lines.extend(f"- {path}" for path in manifest["missing_files"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    build_prep_bundle()


if __name__ == "__main__":
    main()
