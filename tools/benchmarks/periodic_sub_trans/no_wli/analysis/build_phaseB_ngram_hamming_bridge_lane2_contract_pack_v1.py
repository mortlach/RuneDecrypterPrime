from __future__ import annotations

import csv
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

from rune_decrypter_prime.scoring.ngram_hamming.bridge import (  # noqa: E402
    CANDIDATE_SUMMARY_REQUIRED_FIELDS,
    CLUSTER_ROW_REQUIRED_FIELDS,
    PAIR_LEDGER_REQUIRED_FIELDS,
    PROFILE_MANIFEST_REQUIRED_FIELDS,
    ZERO_HIT_AUDIT_REQUIRED_FIELDS,
    bridge_profile_specs,
    canonical_profile_specs,
    profile_manifest_hash,
    profile_manifest_rows,
    score_candidate_profile_ids,
)


RUN_LABEL = "phaseB_ngram_hamming_bridge_lane2_contract_pack_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_contract_pack_v1"
)
CANON_REFERENCE_REL = (
    "planning/temp_files/ngram_scorer_june_2026_docs/"
    "rdp_ngram_phrase_coherence_v3_2_canon_review.md"
)
LANE2_PLAN_REL = (
    "planning/projects/no_wli/20_active_plans/"
    "phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md"
)
NO_BROAD_SCAN_LAUNCHED = True
NO_PRODUCTION_SCORER_CHANGES = True


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def schema_manifest() -> dict[str, Any]:
    return {
        "profile_manifest_required_fields": sorted(PROFILE_MANIFEST_REQUIRED_FIELDS),
        "cluster_row_required_fields": sorted(CLUSTER_ROW_REQUIRED_FIELDS),
        "candidate_summary_required_fields": sorted(CANDIDATE_SUMMARY_REQUIRED_FIELDS),
        "pair_ledger_required_fields": sorted(PAIR_LEDGER_REQUIRED_FIELDS),
        "zero_hit_audit_required_fields": sorted(ZERO_HIT_AUDIT_REQUIRED_FIELDS),
    }


def build_contract_pack(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    canonical_specs = canonical_profile_specs()
    bridge_specs = bridge_profile_specs()
    all_specs = (*canonical_specs, *bridge_specs)
    profile_rows = profile_manifest_rows(all_specs)
    manifest_hash = profile_manifest_hash(all_specs)
    score_candidate_ids = sorted(score_candidate_profile_ids(all_specs))
    schema = schema_manifest()
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "canon_reference": CANON_REFERENCE_REL,
        "lane2_plan": LANE2_PLAN_REL,
        "profile_manifest_path": f"{OUTPUT_DIR_REL}/profile_manifest_rows.csv",
        "profile_manifest_json_path": f"{OUTPUT_DIR_REL}/profile_manifest.json",
        "schema_manifest_path": f"{OUTPUT_DIR_REL}/schema_manifest.json",
        "profile_manifest_hash": manifest_hash,
        "canonical_profile_count": len(canonical_specs),
        "bridge_profile_count": len(bridge_specs),
        "total_profile_count": len(all_specs),
        "score_candidate_profile_ids": score_candidate_ids,
        "no_broad_scan_launched": NO_BROAD_SCAN_LAUNCHED,
        "no_production_scorer_changes": NO_PRODUCTION_SCORER_CHANGES,
        "gate_status": "await_full_raw_order2_order3_provenance_before_broad_run",
    }
    write_csv(selected_output_dir / "profile_manifest_rows.csv", profile_rows)
    write_json(selected_output_dir / "profile_manifest.json", {"profile_manifest_hash": manifest_hash, "profiles": profile_rows})
    write_json(selected_output_dir / "schema_manifest.json", schema)
    write_json(selected_output_dir / "contract_pack_manifest.json", manifest)
    write_readout(selected_output_dir / "readout.md", manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] profile_manifest_hash={manifest_hash}")
    return manifest


def write_readout(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Bridge Lane 2 Contract Pack v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- canon reference: `{manifest['canon_reference']}`",
        f"- lane 2 plan: `{manifest['lane2_plan']}`",
        f"- profile manifest hash: `{manifest['profile_manifest_hash']}`",
        f"- canonical profile count: `{manifest['canonical_profile_count']}`",
        f"- bridge profile count: `{manifest['bridge_profile_count']}`",
        f"- score-candidate-capable profile ids: `{json.dumps(manifest['score_candidate_profile_ids'])}`",
        f"- broad scan launched: `{not manifest['no_broad_scan_launched']}`",
        f"- production scorer changes: `{not manifest['no_production_scorer_changes']}`",
        f"- gate status: `{manifest['gate_status']}`",
        "",
        "This pack freezes the Lane 2 contract surfaces only. It does not approve",
        "or run broad bridge diagnostics.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    build_contract_pack()


if __name__ == "__main__":
    main()
