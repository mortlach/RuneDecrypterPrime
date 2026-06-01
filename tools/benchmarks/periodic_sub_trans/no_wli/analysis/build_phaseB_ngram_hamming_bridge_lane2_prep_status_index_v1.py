from __future__ import annotations

import json
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


RUN_LABEL = "phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1"
)
CONTRACT_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/contract_pack_manifest.json"
)
SYNTHETIC_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/synthetic_contract_manifest.json"
)
INPUT_CONTRACT_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_input_contract_v1/input_contract_manifest.json"
)
SHARD_PROVENANCE_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_provenance_manifest.json"
)
READINESS_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json"
)
PROVENANCE_REVIEW_PACK_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_pack_manifest.json"
)
LAUNCH_DECISION_RECORD_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1/launch_decision_record_manifest.json"
)


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


def component_row(name: str, rel_path: str, payload: dict[str, Any]) -> dict[str, Any]:
    path = REPO_ROOT / rel_path
    return {
        "component": name,
        "path": repo_rel(path) if path.exists() else rel_path,
        "exists": path.exists(),
        "status": payload.get("status", "missing"),
        "run_label": payload.get("run_label", ""),
    }


def build_prep_status_index(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    contract = read_json_if_exists(REPO_ROOT / CONTRACT_MANIFEST_REL)
    input_contract = read_json_if_exists(REPO_ROOT / INPUT_CONTRACT_MANIFEST_REL)
    synthetic = read_json_if_exists(REPO_ROOT / SYNTHETIC_MANIFEST_REL)
    shard_provenance = read_json_if_exists(REPO_ROOT / SHARD_PROVENANCE_MANIFEST_REL)
    readiness = read_json_if_exists(REPO_ROOT / READINESS_MANIFEST_REL)
    provenance_review_pack = read_json_if_exists(REPO_ROOT / PROVENANCE_REVIEW_PACK_MANIFEST_REL)
    launch_decision = read_json_if_exists(REPO_ROOT / LAUNCH_DECISION_RECORD_MANIFEST_REL)
    components = [
        component_row("contract_pack", CONTRACT_MANIFEST_REL, contract),
        component_row("input_contract", INPUT_CONTRACT_MANIFEST_REL, input_contract),
        component_row("synthetic_contract_smoke", SYNTHETIC_MANIFEST_REL, synthetic),
        component_row("shard_provenance", SHARD_PROVENANCE_MANIFEST_REL, shard_provenance),
        component_row("readiness_gate", READINESS_MANIFEST_REL, readiness),
        component_row("full_raw_provenance_review_pack", PROVENANCE_REVIEW_PACK_MANIFEST_REL, provenance_review_pack),
        component_row("launch_decision_record", LAUNCH_DECISION_RECORD_MANIFEST_REL, launch_decision),
    ]
    missing = [row["component"] for row in components if not row["exists"]]
    blocked_reasons = []
    if missing:
        blocked_reasons.append("one or more Lane 2 prep components are missing")
    if readiness.get("bridge_broad_scan_ready") is not True:
        blocked_reasons.append("Lane 2 broad bridge scan is not ready")
    if provenance_review_pack.get("status") != "review_ready":
        blocked_reasons.append("full raw provenance review pack is not review_ready")
    if launch_decision.get("status") != "launchable_after_review":
        blocked_reasons.append("launch decision record is not launchable_after_review")
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blocked_reasons else "pass",
        "blocked_reasons": blocked_reasons,
        "components": components,
        "contract_profile_manifest_hash": contract.get("profile_manifest_hash", ""),
        "input_contract_status": input_contract.get("status", ""),
        "input_contract_no_real_candidate_scan": input_contract.get("no_real_candidate_scan", False),
        "synthetic_smoke_status": synthetic.get("status", ""),
        "synthetic_no_real_candidate_scan": synthetic.get("no_real_candidate_scan", False),
        "shard_provenance_status": shard_provenance.get("status", ""),
        "provenance_review_pack_status": provenance_review_pack.get("status", ""),
        "provenance_review_pack_pending_checks": provenance_review_pack.get("pending_review_checks", []),
        "launch_decision_record_status": launch_decision.get("status", ""),
        "completed_shards": shard_provenance.get("completed_shards", 0),
        "total_shards": shard_provenance.get("total_shards", 0),
        "bridge_broad_scan_ready": readiness.get("bridge_broad_scan_ready", False),
        "readiness_blocked_reasons": readiness.get("blocked_reasons", []),
    }
    write_json(selected_output_dir / "prep_status_index_manifest.json", manifest)
    write_readout(selected_output_dir / "readout.md", manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] bridge_broad_scan_ready={manifest['bridge_broad_scan_ready']}")
    return manifest


def write_readout(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Bridge Lane 2 Prep Status Index v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- completed shards: `{manifest['completed_shards']} / {manifest['total_shards']}`",
        f"- bridge broad scan ready: `{manifest['bridge_broad_scan_ready']}`",
        f"- synthetic smoke status: `{manifest['synthetic_smoke_status']}`",
        f"- input contract status: `{manifest['input_contract_status']}`",
        f"- provenance review pack status: `{manifest['provenance_review_pack_status']}`",
        f"- launch decision record status: `{manifest['launch_decision_record_status']}`",
        f"- synthetic no real candidate scan: `{manifest['synthetic_no_real_candidate_scan']}`",
        f"- contract profile manifest hash: `{manifest['contract_profile_manifest_hash']}`",
        "",
        "Components:",
    ]
    for row in manifest["components"]:
        lines.append(f"- {row['component']}: `{row['status']}` at `{row['path']}`")
    lines.append("")
    lines.append("Blocked reasons:")
    if manifest["blocked_reasons"]:
        lines.extend(f"- {reason}" for reason in manifest["blocked_reasons"])
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    build_prep_status_index()


if __name__ == "__main__":
    main()
