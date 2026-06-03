from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_full_raw_local_payload_copy_validation_v1"
ASSET_MANIFEST_REL = "assets/ngram_hamming/phaseB_full_raw_v1/asset_manifest.json"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_local_payload_copy_validation_v1"
)
VALIDATED_PAYLOAD_ROOT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_asset_shards_v1"
)
REQUIRED_ORDERS = (2, 3)
REQUIRED_CUTS = ("normal", "strict")
REQUIRED_DIRECTIONS = ("fwd",)


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def posixish(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): posixish(item) for key, item in value.items()}
    if isinstance(value, list):
        return [posixish(item) for item in value]
    if isinstance(value, str):
        return value.replace("\\", "/")
    return value


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(posixish(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Iterable[str]) -> None:
    ensure_under_repo(path)
    fields = list(fieldnames)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024 * 4), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_bad_manifest_path(path_value: str) -> bool:
    return "\\" in path_value or Path(path_value).is_absolute() or ":" in path_value


def payload_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in manifest.get("files", []):
        if str(row.get("role", "")) == "shard_payload":
            rows.append(dict(row))
    return rows


def required_coverage_status(rows: Iterable[Mapping[str, Any]]) -> tuple[bool, list[str]]:
    present = {
        (int(row.get("ngram_order", -1)), str(row.get("dictionary_cut", "")), str(row.get("direction", "")))
        for row in rows
        if int(row.get("aggregate_rows", 0) or 0) > 0
    }
    missing = [
        f"order={order} cut={cut} direction={direction}"
        for order in REQUIRED_ORDERS
        for cut in REQUIRED_CUTS
        for direction in REQUIRED_DIRECTIONS
        if (order, cut, direction) not in present
    ]
    return not missing, missing


def validate_payload_copy(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    manifest_path = REPO_ROOT / ASSET_MANIFEST_REL
    validation_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    hash_mismatch_rows: list[dict[str, Any]] = []
    byte_mismatch_rows: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    if not manifest_path.is_file():
        blocked_reasons.append("asset manifest is missing")
        manifest: dict[str, Any] = {}
        rows: list[dict[str, Any]] = []
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = payload_rows(manifest)

    bad_path_count = 0
    checked_count = 0
    for index, row in enumerate(rows, start=1):
        rel_path = str(row.get("path", ""))
        expected_bytes = int(row.get("bytes", 0) or 0)
        expected_sha256 = str(row.get("sha256", ""))
        path_bad = is_bad_manifest_path(rel_path)
        exists = False
        actual_bytes: int | str = ""
        actual_sha256 = ""
        status = "pass"
        reason = ""
        if path_bad:
            bad_path_count += 1
            status = "blocked"
            reason = "path is not repo-relative POSIX"
        else:
            path = REPO_ROOT / rel_path
            exists = path.is_file()
            if not exists:
                status = "missing"
                reason = "payload file is missing"
            else:
                checked_count += 1
                actual_bytes = path.stat().st_size
                if int(actual_bytes) != expected_bytes:
                    status = "byte_count_mismatch"
                    reason = "byte count mismatch"
                actual_sha256 = sha256_file(path)
                if actual_sha256 != expected_sha256:
                    status = "hash_mismatch" if status == "pass" else f"{status};hash_mismatch"
                    reason = f"{reason}; hash mismatch".strip("; ")
        out_row = {
            "path": rel_path,
            "exists": exists,
            "status": status,
            "reason": reason,
            "expected_bytes": expected_bytes,
            "actual_bytes": actual_bytes,
            "expected_sha256": expected_sha256,
            "actual_sha256": actual_sha256,
            "ngram_order": row.get("ngram_order", ""),
            "dictionary_cut": row.get("dictionary_cut", ""),
            "direction": row.get("direction", ""),
        }
        validation_rows.append(out_row)
        if status == "missing":
            missing_rows.append(out_row)
        if "byte_count_mismatch" in status:
            byte_mismatch_rows.append(out_row)
        if "hash_mismatch" in status:
            hash_mismatch_rows.append(out_row)
        if index == 1 or index == len(rows) or index % 100 == 0:
            print(f"[{RUN_LABEL}] payload_files_validated={index}/{len(rows)}", flush=True)

    coverage_ok, missing_coverage = required_coverage_status(rows)
    if bad_path_count:
        blocked_reasons.append("manifest contains non repo-relative POSIX payload paths")
    if missing_rows:
        blocked_reasons.append("one or more payload files are missing")
    if byte_mismatch_rows:
        blocked_reasons.append("one or more payload files have byte-count mismatches")
    if hash_mismatch_rows:
        blocked_reasons.append("one or more payload files have SHA-256 mismatches")
    if not coverage_ok:
        blocked_reasons.append("required order/cut/direction coverage is missing")

    status = "pass" if not blocked_reasons else "blocked"
    validation = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "asset_id": manifest.get("asset_id", "") if manifest else "",
        "validated_payload_root": VALIDATED_PAYLOAD_ROOT_REL,
        "manifest_path": ASSET_MANIFEST_REL,
        "payload_files_expected": len(rows),
        "payload_files_checked": checked_count,
        "missing_files": len(missing_rows),
        "hash_mismatches": len(hash_mismatch_rows),
        "byte_count_mismatches": len(byte_mismatch_rows),
        "bad_manifest_paths": bad_path_count,
        "required_orders": list(REQUIRED_ORDERS),
        "required_cuts": list(REQUIRED_CUTS),
        "required_directions": list(REQUIRED_DIRECTIONS),
        "required_coverage_present": coverage_ok,
        "missing_required_coverage": missing_coverage,
        "blocked_reasons": blocked_reasons,
    }

    fields = (
        "path",
        "exists",
        "status",
        "reason",
        "expected_bytes",
        "actual_bytes",
        "expected_sha256",
        "actual_sha256",
        "ngram_order",
        "dictionary_cut",
        "direction",
    )
    write_json(selected_output_dir / "validation_manifest.json", validation)
    write_csv(selected_output_dir / "payload_file_validation_rows.csv", validation_rows, fields)
    write_csv(selected_output_dir / "missing_payload_files.csv", missing_rows, fields)
    write_csv(selected_output_dir / "hash_mismatch_rows.csv", hash_mismatch_rows, fields)
    write_csv(selected_output_dir / "byte_count_mismatch_rows.csv", byte_mismatch_rows, fields)
    write_readout(selected_output_dir / "readout.md", validation)
    print(f"[{RUN_LABEL}] status={status}")
    print(f"[{RUN_LABEL}] payload_files_checked={checked_count}/{len(rows)}")
    return validation


def write_readout(path: Path, validation: Mapping[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# Phase B N-gram Hamming Full Raw Local Payload Copy Validation v1",
        "",
        f"Status: `{validation['status']}`",
        "",
        f"- asset id: `{validation['asset_id']}`",
        f"- manifest path: `{validation['manifest_path']}`",
        f"- validated payload root: `{validation['validated_payload_root']}`",
        f"- expected payload files: `{validation['payload_files_expected']}`",
        f"- checked payload files: `{validation['payload_files_checked']}`",
        f"- missing files: `{validation['missing_files']}`",
        f"- byte-count mismatches: `{validation['byte_count_mismatches']}`",
        f"- hash mismatches: `{validation['hash_mismatches']}`",
        f"- bad manifest paths: `{validation['bad_manifest_paths']}`",
        f"- required coverage present: `{validation['required_coverage_present']}`",
        "",
        "This validates the ignored local full raw shard payload copy. It does not",
        "approve production scoring, broad candidate scans, or order-2 score authority.",
    ]
    if validation.get("blocked_reasons"):
        lines.extend(["", "## Blocked Reasons"])
        lines.extend(f"- {reason}" for reason in validation["blocked_reasons"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    validate_payload_copy()


if __name__ == "__main__":
    main()
