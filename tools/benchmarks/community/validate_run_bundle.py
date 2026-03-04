from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.benchmarks.community._campaign_common import (
    INTEGRITY_CHAIN_GENESIS,
    INTEGRITY_CHAIN_HASH,
    INTEGRITY_CHAIN_VERSION,
    load_json,
    read_jsonl,
    verify_results_integrity,
    write_json,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_SCHEMA = REPO_ROOT / "tools" / "benchmarks" / "community" / "schemas" / "manifest_schema_v1_1.json"
DEFAULT_RESULT_SCHEMA = REPO_ROOT / "tools" / "benchmarks" / "community" / "schemas" / "result_schema_v1_1.json"

REQUIRED_BUNDLE_FILES = (
    "run_meta.json",
    "setup_report.json",
    "setup.log",
    "preflight_report.json",
    "preflight.log",
    "campaign_config_v1_1.json",
    "profile_catalog_v1_1.json",
    "shard_manifest.jsonl",
    "results.jsonl",
    "results_integrity.jsonl",
    "run.log",
)


def _load_schema_validator(path: Path) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _error_message(error) -> str:
    where = ".".join(str(part) for part in error.path)
    if where:
        return f"{where}: {error.message}"
    return str(error.message)


def validate_run_bundle(
    *,
    run_bundle_path: Path,
    manifest_schema_path: Path,
    result_schema_path: Path,
    expected_campaign_id: str | None = None,
    expected_git_sha: str | None = None,
    require_fastlm_true: bool = True,
) -> dict[str, Any]:
    run_bundle_path = run_bundle_path.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not run_bundle_path.exists() or not run_bundle_path.is_dir():
        return {
            "ok": False,
            "run_bundle_path": str(run_bundle_path),
            "errors": [f"run_bundle is missing or not a directory: {run_bundle_path}"],
            "warnings": [],
        }

    for rel in REQUIRED_BUNDLE_FILES:
        if not (run_bundle_path / rel).exists():
            errors.append(f"missing required file: {rel}")

    if errors:
        return {
            "ok": False,
            "run_bundle_path": str(run_bundle_path),
            "errors": errors,
            "warnings": warnings,
        }

    manifest_validator = _load_schema_validator(manifest_schema_path)
    result_validator = _load_schema_validator(result_schema_path)

    run_meta = load_json(run_bundle_path / "run_meta.json")
    campaign_config = load_json(run_bundle_path / "campaign_config_v1_1.json")
    shard_rows = read_jsonl(run_bundle_path / "shard_manifest.jsonl")
    result_rows = read_jsonl(run_bundle_path / "results.jsonl")
    integrity_rows = read_jsonl(run_bundle_path / "results_integrity.jsonl")

    campaign_id = str(campaign_config.get("campaign_id", "")).strip()
    git_sha = str(campaign_config.get("git_sha", "")).strip()
    if not campaign_id:
        errors.append("campaign_config_v1_1.json missing campaign_id")
    if not git_sha:
        errors.append("campaign_config_v1_1.json missing git_sha")

    if expected_campaign_id is not None and campaign_id != str(expected_campaign_id):
        errors.append(f"campaign_id mismatch: expected={expected_campaign_id} got={campaign_id}")
    if expected_git_sha is not None and git_sha != str(expected_git_sha):
        errors.append(f"git_sha mismatch: expected={expected_git_sha} got={git_sha}")

    if str(run_meta.get("campaign_id", "")) != campaign_id:
        errors.append("run_meta campaign_id does not match campaign_config campaign_id")
    if str(run_meta.get("git_sha", "")) != git_sha:
        errors.append("run_meta git_sha does not match campaign_config git_sha")
    if bool(run_meta.get("campaign_mode")) is not True:
        errors.append("run_meta campaign_mode must be true")
    if bool(run_meta.get("autoskip_proven_disabled")) is not True:
        errors.append("run_meta autoskip_proven_disabled must be true")

    manifest_job_ids: set[str] = set()
    for idx, row in enumerate(shard_rows):
        errs = sorted(manifest_validator.iter_errors(row), key=lambda e: list(e.path))
        if errs:
            errors.append(f"shard_manifest row {idx} invalid: {_error_message(errs[0])}")
            continue
        if str(row.get("campaign_id")) != campaign_id:
            errors.append(f"shard_manifest row {idx} campaign_id mismatch")
        if str(row.get("git_sha")) != git_sha:
            errors.append(f"shard_manifest row {idx} git_sha mismatch")
        job_id = str(row.get("job_id"))
        if job_id in manifest_job_ids:
            errors.append(f"duplicate job_id in shard_manifest: {job_id}")
        manifest_job_ids.add(job_id)

    result_job_ids: set[str] = set()
    for idx, row in enumerate(result_rows):
        errs = sorted(result_validator.iter_errors(row), key=lambda e: list(e.path))
        if errs:
            errors.append(f"results row {idx} invalid: {_error_message(errs[0])}")
            continue
        if str(row.get("campaign_id")) != campaign_id:
            errors.append(f"results row {idx} campaign_id mismatch")
        if str(row.get("git_sha")) != git_sha:
            errors.append(f"results row {idx} git_sha mismatch")
        job_id = str(row.get("job_id"))
        if job_id in result_job_ids:
            errors.append(f"duplicate job_id in results: {job_id}")
        result_job_ids.add(job_id)
        if job_id not in manifest_job_ids:
            errors.append(f"results row {idx} job_id not present in shard_manifest: {job_id}")
        if str(row.get("device")) != "cpu":
            errors.append(f"results row {idx} device must be cpu")
        if str(row.get("scoring_backend")) != "numpy":
            errors.append(f"results row {idx} scoring_backend must be numpy")
        if require_fastlm_true and bool(row.get("fastlm_present")) is not True:
            errors.append(f"results row {idx} fastlm_present must be true")

    if len(result_rows) == 0:
        warnings.append("results.jsonl has zero rows")

    integrity_errors, final_chain_hash = verify_results_integrity(
        result_rows=result_rows,
        integrity_rows=integrity_rows,
    )
    errors.extend(integrity_errors)

    integrity_meta = run_meta.get("results_integrity")
    if not isinstance(integrity_meta, dict):
        errors.append("run_meta missing results_integrity block")
    else:
        if str(integrity_meta.get("integrity_version")) != INTEGRITY_CHAIN_VERSION:
            errors.append(
                "run_meta results_integrity.integrity_version mismatch: "
                f"expected={INTEGRITY_CHAIN_VERSION}"
            )
        if str(integrity_meta.get("hash_algorithm")) != INTEGRITY_CHAIN_HASH:
            errors.append(
                "run_meta results_integrity.hash_algorithm mismatch: "
                f"expected={INTEGRITY_CHAIN_HASH}"
            )
        if str(integrity_meta.get("genesis_hash")) != INTEGRITY_CHAIN_GENESIS:
            errors.append(
                "run_meta results_integrity.genesis_hash mismatch: "
                f"expected={INTEGRITY_CHAIN_GENESIS}"
            )
        try:
            meta_row_count = int(integrity_meta.get("row_count"))
        except Exception:
            meta_row_count = -1
        if meta_row_count != len(result_rows):
            errors.append(
                "run_meta results_integrity.row_count mismatch: "
                f"meta={meta_row_count} results={len(result_rows)}"
            )
        if str(integrity_meta.get("final_chain_hash")) != str(final_chain_hash):
            errors.append(
                "run_meta results_integrity.final_chain_hash mismatch with recomputed chain"
            )

    report = {
        "ok": len(errors) == 0,
        "run_bundle_path": str(run_bundle_path),
        "campaign_id": campaign_id,
        "git_sha": git_sha,
        "manifest_rows": len(shard_rows),
        "result_rows": len(result_rows),
        "unique_manifest_job_ids": len(manifest_job_ids),
        "unique_result_job_ids": len(result_job_ids),
        "integrity_chain_hash": str(final_chain_hash),
        "errors": errors,
        "warnings": warnings,
    }
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate community benchmark run bundle (v1.1).")
    parser.add_argument("--run-bundle", type=Path, required=True, help="path to run_bundle directory")
    parser.add_argument(
        "--manifest-schema",
        type=Path,
        default=DEFAULT_MANIFEST_SCHEMA,
        help=f"path to manifest schema json (default: {DEFAULT_MANIFEST_SCHEMA})",
    )
    parser.add_argument(
        "--result-schema",
        type=Path,
        default=DEFAULT_RESULT_SCHEMA,
        help=f"path to result schema json (default: {DEFAULT_RESULT_SCHEMA})",
    )
    parser.add_argument("--campaign-id", type=str, default=None, help="optional expected campaign_id")
    parser.add_argument("--git-sha", type=str, default=None, help="optional expected git_sha")
    parser.add_argument(
        "--allow-fastlm-false",
        action="store_true",
        help="allow fastlm_present=false rows (default: reject)",
    )
    parser.add_argument("--report-json", type=Path, default=None, help="optional output path for validation report json")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = validate_run_bundle(
        run_bundle_path=args.run_bundle,
        manifest_schema_path=args.manifest_schema,
        result_schema_path=args.result_schema,
        expected_campaign_id=args.campaign_id,
        expected_git_sha=args.git_sha,
        require_fastlm_true=not bool(args.allow_fastlm_false),
    )
    if args.report_json is not None:
        write_json(args.report_json, report)
    if report["ok"]:
        print(
            "[community] bundle valid "
            f"path={report['run_bundle_path']} results={report['result_rows']} manifest={report['manifest_rows']}"
        )
        return 0

    print(
        "[community] bundle invalid "
        f"path={report['run_bundle_path']} errors={len(report['errors'])}"
    )
    for msg in report["errors"]:
        print(f"  - {msg}")
    for msg in report["warnings"]:
        print(f"  * warning: {msg}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
