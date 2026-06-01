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

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (  # noqa: E402
    check_phaseB_ngram_hamming_bridge_lane2_readiness_v1 as readiness,
)


RUN_LABEL = "phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1"
)
READINESS_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json"
)
ALLOW_REAL_BRIDGE_SCAN = False
NO_PRODUCTION_SCORER_CHANGES = True


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


def run_gated_diagnostic(
    *,
    readiness_manifest_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    readiness_path = readiness_manifest_path or (REPO_ROOT / READINESS_MANIFEST_REL)
    blocked_reasons: list[str] = []
    readiness_payload: dict[str, Any] = {}
    if not readiness_path.exists():
        blocked_reasons.append("missing Lane 2 readiness manifest")
    else:
        readiness_payload = read_json(readiness_path)
        if readiness_payload.get("bridge_broad_scan_ready") is not True:
            blocked_reasons.append("Lane 2 readiness gate is not pass")
    if ALLOW_REAL_BRIDGE_SCAN is not True:
        blocked_reasons.append("ALLOW_REAL_BRIDGE_SCAN is false")
    if NO_PRODUCTION_SCORER_CHANGES is not True:
        blocked_reasons.append("production scorer change guard is not true")

    status = "blocked" if blocked_reasons else "ready_no_scan_implemented"
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "blocked_reasons": blocked_reasons,
        "allow_real_bridge_scan": ALLOW_REAL_BRIDGE_SCAN,
        "no_production_scorer_changes": NO_PRODUCTION_SCORER_CHANGES,
        "readiness_manifest": repo_rel(readiness_path) if readiness_path.exists() else READINESS_MANIFEST_REL,
        "readiness_status": readiness_payload.get("status", ""),
        "readiness_bridge_broad_scan_ready": readiness_payload.get("bridge_broad_scan_ready", False),
        "completed_shards": readiness_payload.get("completed_shards", 0),
        "total_shards": readiness_payload.get("total_shards", 0),
        "real_candidate_scan_started": False,
    }
    write_json(selected_output_dir / "gated_diagnostic_manifest.json", manifest)
    write_readout(selected_output_dir / "readout.md", manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] real_candidate_scan_started={manifest['real_candidate_scan_started']}")
    return manifest


def write_readout(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Bridge Lane 2 Gated Diagnostic v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- readiness bridge broad scan ready: `{manifest['readiness_bridge_broad_scan_ready']}`",
        f"- allow real bridge scan: `{manifest['allow_real_bridge_scan']}`",
        f"- real candidate scan started: `{manifest['real_candidate_scan_started']}`",
        f"- completed shards: `{manifest['completed_shards']} / {manifest['total_shards']}`",
        "",
        "Blocked reasons:",
    ]
    if manifest["blocked_reasons"]:
        lines.extend(f"- {reason}" for reason in manifest["blocked_reasons"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This is a gate scaffold only. It intentionally does not contain a broad",
            "candidate scan implementation yet.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    run_gated_diagnostic()


if __name__ == "__main__":
    main()
