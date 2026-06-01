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


RUN_LABEL = "phaseB_ngram_hamming_bridge_lane2_readiness_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_readiness_v1"
)
CONTRACT_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/contract_pack_manifest.json"
)
SHARD_PROVENANCE_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_provenance_manifest.json"
)
REQUIRED_GATE_STATUS = "await_full_raw_order2_order3_provenance_before_broad_run"


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_readiness(
    *,
    contract_manifest_path: Path | None = None,
    shard_provenance_manifest_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    contract_path = contract_manifest_path or (REPO_ROOT / CONTRACT_MANIFEST_REL)
    provenance_path = shard_provenance_manifest_path or (REPO_ROOT / SHARD_PROVENANCE_MANIFEST_REL)
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    blocked_reasons: list[str] = []
    if not contract_path.exists():
        blocked_reasons.append("missing Lane 2 contract manifest")
        contract: dict[str, Any] = {}
    else:
        contract = read_json(contract_path)
    if not provenance_path.exists():
        blocked_reasons.append("missing shard provenance manifest")
        provenance: dict[str, Any] = {}
    else:
        provenance = read_json(provenance_path)

    if contract:
        if contract.get("status") != "pass":
            blocked_reasons.append("Lane 2 contract pack status is not pass")
        if contract.get("no_broad_scan_launched") is not True:
            blocked_reasons.append("contract pack reports that a broad scan has launched")
        if contract.get("no_production_scorer_changes") is not True:
            blocked_reasons.append("contract pack reports production scorer changes")
        if contract.get("gate_status") != REQUIRED_GATE_STATUS:
            blocked_reasons.append("contract pack gate status has drifted")
    if provenance:
        if provenance.get("status") != "pass":
            blocked_reasons.append("full raw shard provenance status is not pass")
        if provenance.get("full_raw_ngram_rebuild_confirmed") is not True:
            blocked_reasons.append("full raw n-gram rebuild is not confirmed")
        if int(provenance.get("missing_shards", 0) or 0) != 0:
            blocked_reasons.append("one or more expected shards are missing")
        if int(provenance.get("failed_shards", 0) or 0) != 0:
            blocked_reasons.append("one or more shards failed")
        if int(provenance.get("missing_output_files", 0) or 0) != 0:
            blocked_reasons.append("one or more declared shard output files are missing")

    ready = not blocked_reasons
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if ready else "blocked",
        "bridge_broad_scan_ready": ready,
        "blocked_reasons": blocked_reasons,
        "contract_manifest": repo_rel(contract_path) if contract_path.exists() else CONTRACT_MANIFEST_REL,
        "shard_provenance_manifest": repo_rel(provenance_path) if provenance_path.exists() else SHARD_PROVENANCE_MANIFEST_REL,
        "contract_profile_manifest_hash": contract.get("profile_manifest_hash", ""),
        "shard_provenance_status": provenance.get("status", ""),
        "completed_shards": provenance.get("completed_shards", 0),
        "total_shards": provenance.get("total_shards", 0),
        "full_raw_ngram_rebuild_confirmed": provenance.get("full_raw_ngram_rebuild_confirmed", False),
    }
    write_json(selected_output_dir / "readiness_manifest.json", manifest)
    write_readout(selected_output_dir / "readout.md", manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] bridge_broad_scan_ready={manifest['bridge_broad_scan_ready']}")
    return manifest


def write_readout(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Bridge Lane 2 Readiness v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- bridge broad scan ready: `{manifest['bridge_broad_scan_ready']}`",
        f"- completed shards: `{manifest['completed_shards']} / {manifest['total_shards']}`",
        f"- full raw confirmed: `{manifest['full_raw_ngram_rebuild_confirmed']}`",
        f"- contract manifest: `{manifest['contract_manifest']}`",
        f"- shard provenance manifest: `{manifest['shard_provenance_manifest']}`",
        "",
        "Blocked reasons:",
    ]
    if manifest["blocked_reasons"]:
        lines.extend(f"- {reason}" for reason in manifest["blocked_reasons"])
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    check_readiness()


if __name__ == "__main__":
    main()
