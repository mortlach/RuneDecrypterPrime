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


RUN_LABEL = "phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1"
)
READINESS_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json"
)
PREP_STATUS_INDEX_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1/prep_status_index_manifest.json"
)
PROVENANCE_REVIEW_PACK_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_pack_manifest.json"
)
GATED_DIAGNOSTIC_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1/gated_diagnostic_manifest.json"
)
CANON_REFERENCE_REL = (
    "planning/temp_files/ngram_scorer_june_2026_docs/"
    "rdp_ngram_phrase_coherence_v3_2_canon_review.md"
)
LANE2_PLAN_REL = (
    "planning/projects/no_wli/20_active_plans/"
    "phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md"
)
ALLOW_REAL_BRIDGE_SCAN_AFTER_REVIEW = False
NO_BROAD_SCAN_LAUNCHED = True
NO_PRODUCTION_SCORER_CHANGES = True
INTENDED_FIRST_LAUNCH_SCOPE = "post-review microbatch only"
STOP_CONDITION = "readiness_pass_and_explicit_hardcoded_approval_or_block"


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


def build_launch_decision_record(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    readiness = read_json_if_exists(REPO_ROOT / READINESS_MANIFEST_REL)
    prep_index = read_json_if_exists(REPO_ROOT / PREP_STATUS_INDEX_MANIFEST_REL)
    review_pack = read_json_if_exists(REPO_ROOT / PROVENANCE_REVIEW_PACK_MANIFEST_REL)
    gated_diagnostic = read_json_if_exists(REPO_ROOT / GATED_DIAGNOSTIC_MANIFEST_REL)
    components = [
        component_row("readiness_gate", READINESS_MANIFEST_REL, readiness),
        component_row("prep_status_index", PREP_STATUS_INDEX_MANIFEST_REL, prep_index),
        component_row("full_raw_provenance_review_pack", PROVENANCE_REVIEW_PACK_MANIFEST_REL, review_pack),
        component_row("gated_diagnostic_scaffold", GATED_DIAGNOSTIC_MANIFEST_REL, gated_diagnostic),
    ]
    blocked_reasons = launch_blockers(readiness, review_pack, gated_diagnostic, components)
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blocked_reasons else "launchable_after_review",
        "blocked_reasons": blocked_reasons,
        "components": components,
        "canon_reference": CANON_REFERENCE_REL,
        "lane2_plan": LANE2_PLAN_REL,
        "allow_real_bridge_scan_after_review": ALLOW_REAL_BRIDGE_SCAN_AFTER_REVIEW,
        "bridge_broad_scan_ready": readiness.get("bridge_broad_scan_ready", False),
        "provenance_review_pack_status": review_pack.get("status", ""),
        "gated_diagnostic_status": gated_diagnostic.get("status", ""),
        "gated_real_candidate_scan_started": gated_diagnostic.get("real_candidate_scan_started", False),
        "gated_no_production_scorer_changes": gated_diagnostic.get("no_production_scorer_changes", False),
        "provenance_review_pack_pending_checks": review_pack.get("pending_review_checks", []),
        "completed_shards": readiness.get("completed_shards", prep_index.get("completed_shards", 0)),
        "total_shards": readiness.get("total_shards", prep_index.get("total_shards", 0)),
        "intended_first_launch_scope": INTENDED_FIRST_LAUNCH_SCOPE,
        "stop_condition": STOP_CONDITION,
        "no_broad_scan_launched": NO_BROAD_SCAN_LAUNCHED,
        "no_production_scorer_changes": NO_PRODUCTION_SCORER_CHANGES,
        "required_next_decisions": required_next_decisions(readiness, review_pack),
    }
    write_json(selected_output_dir / "launch_decision_record_manifest.json", manifest)
    write_readout(selected_output_dir / "readout.md", manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] allow_real_bridge_scan_after_review={manifest['allow_real_bridge_scan_after_review']}")
    return manifest


def launch_blockers(
    readiness: dict[str, Any],
    review_pack: dict[str, Any],
    gated_diagnostic: dict[str, Any],
    components: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if any(not row["exists"] for row in components):
        blockers.append("one or more launch-decision dependency manifests are missing")
    if readiness.get("status") != "pass":
        blockers.append("Lane 2 readiness manifest status is not pass")
    if readiness.get("bridge_broad_scan_ready") is not True:
        blockers.append("Lane 2 readiness gate is not pass")
    if review_pack.get("status") != "review_ready":
        blockers.append("full raw provenance review pack is not review_ready")
    if review_pack.get("pending_review_checks"):
        blockers.append("full raw provenance review pack still has pending review checks")
    if gated_diagnostic.get("real_candidate_scan_started") is not False:
        blockers.append("gated diagnostic indicates a real candidate scan has started")
    if gated_diagnostic.get("no_production_scorer_changes") is not True:
        blockers.append("gated diagnostic production scorer guard is not true")
    if ALLOW_REAL_BRIDGE_SCAN_AFTER_REVIEW is not True:
        blockers.append("hardcoded real bridge scan approval switch is false")
    if NO_BROAD_SCAN_LAUNCHED is not True:
        blockers.append("broad scan launch guard is not true")
    if NO_PRODUCTION_SCORER_CHANGES is not True:
        blockers.append("launch decision production scorer guard is not true")
    return blockers


def required_next_decisions(readiness: dict[str, Any], review_pack: dict[str, Any]) -> list[str]:
    decisions = [
        "finish or stop the full raw order-2/order-3 shard build with extractable provenance",
        "rerun shard provenance summary and full raw provenance review pack",
        "review the v3.2 canon drift guards against the generated pack",
    ]
    if readiness.get("bridge_broad_scan_ready") is not True:
        decisions.append("rerun Lane 2 readiness and prep status index after provenance passes")
    if review_pack.get("status") != "review_ready":
        decisions.append("do not change the real bridge scan approval switch yet")
    return decisions


def write_readout(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Bridge Lane 2 Launch Decision Record v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- bridge broad scan ready: `{manifest['bridge_broad_scan_ready']}`",
        f"- provenance review pack status: `{manifest['provenance_review_pack_status']}`",
        f"- hardcoded approval switch: `{manifest['allow_real_bridge_scan_after_review']}`",
        f"- completed shards: `{manifest['completed_shards']} / {manifest['total_shards']}`",
        f"- intended first launch scope: `{manifest['intended_first_launch_scope']}`",
        f"- stop condition: `{manifest['stop_condition']}`",
        f"- broad scan launched: `{not manifest['no_broad_scan_launched']}`",
        f"- production scorer changes: `{not manifest['no_production_scorer_changes']}`",
        "",
        "Blocked reasons:",
    ]
    if manifest["blocked_reasons"]:
        lines.extend(f"- {reason}" for reason in manifest["blocked_reasons"])
    else:
        lines.append("- none")
    lines.append("")
    lines.append("Required next decisions:")
    lines.extend(f"- {decision}" for decision in manifest["required_next_decisions"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    build_launch_decision_record()


if __name__ == "__main__":
    main()
