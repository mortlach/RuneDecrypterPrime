from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.benchmarks.community._campaign_common import (
    load_json,
    resolve_orders,
    sha256_hex_from_obj,
    stable_int_from_obj,
    write_json,
    write_jsonl,
)
from tools.benchmarks.community.config import load_profile_catalog_from_dict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN_CONFIG = REPO_ROOT / "tools" / "benchmarks" / "community" / "examples" / "campaign_config_v1_1.json"
DEFAULT_PROFILE_CATALOG = REPO_ROOT / "tools" / "benchmarks" / "community" / "profile_catalog_v1_1.json"
DEFAULT_MANIFEST_SCHEMA = REPO_ROOT / "tools" / "benchmarks" / "community" / "schemas" / "manifest_schema_v1_1.json"


def _load_schema_validator(path: Path) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate_campaign_config(config: dict[str, Any]) -> None:
    if config.get("campaign_spec_version") != "v1.1":
        raise ValueError("campaign_spec_version must be 'v1.1'")
    if not isinstance(config.get("campaign_id"), str) or not config["campaign_id"].strip():
        raise ValueError("campaign_id must be a non-empty string")
    if not isinstance(config.get("git_sha"), str) or not config["git_sha"].strip():
        raise ValueError("git_sha must be a non-empty string")
    if not isinstance(config.get("campaign_seed"), int) or config["campaign_seed"] < 0:
        raise ValueError("campaign_seed must be a non-negative integer")
    if not isinstance(config.get("replicates_per_cell"), int) or config["replicates_per_cell"] <= 0:
        raise ValueError("replicates_per_cell must be a positive integer")

    fixtures = config.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("fixtures must be a non-empty list")
    fixture_ids: set[str] = set()
    for idx, fixture in enumerate(fixtures):
        if not isinstance(fixture, dict):
            raise ValueError(f"fixtures[{idx}] must be an object")
        fixture_id = fixture.get("text_fixture_id")
        if not isinstance(fixture_id, str) or not fixture_id.strip():
            raise ValueError(f"fixtures[{idx}].text_fixture_id must be a non-empty string")
        if fixture_id in fixture_ids:
            raise ValueError(f"duplicate text_fixture_id in fixtures: {fixture_id}")
        fixture_ids.add(fixture_id)

    grid = config.get("grid")
    if not isinstance(grid, dict):
        raise ValueError("grid must be an object")
    for key in ("period_min", "period_max", "columns_min", "columns_max"):
        if not isinstance(grid.get(key), int):
            raise ValueError(f"grid.{key} must be an integer")
    if not isinstance(grid.get("orders"), list) or not grid["orders"]:
        raise ValueError("grid.orders must be a non-empty list")

    if grid["period_min"] > grid["period_max"]:
        raise ValueError("grid.period_min must be <= grid.period_max")
    if grid["columns_min"] > grid["columns_max"]:
        raise ValueError("grid.columns_min must be <= grid.columns_max")
    if grid["period_min"] < 7 or grid["period_max"] > 13:
        raise ValueError("grid periods must be in [7, 13] for v1.1")
    if grid["columns_min"] < 1 or grid["columns_max"] > 13:
        raise ValueError("grid columns must be in [1, 13] for v1.1")


def _available_profile_ids(profile_catalog: dict[str, Any]) -> list[str]:
    catalog = load_profile_catalog_from_dict(profile_catalog)
    return list(catalog.profiles_by_id.keys())


def resolve_profile_ids(campaign_config: dict[str, Any], profile_catalog: dict[str, Any]) -> tuple[str, ...]:
    available_profile_ids = _available_profile_ids(profile_catalog)
    requested = campaign_config.get("profile_ids")
    if requested is None:
        return tuple(available_profile_ids)
    if not isinstance(requested, list) or not requested:
        raise ValueError("profile_ids must be a non-empty list when provided")

    bad = [value for value in requested if value not in available_profile_ids]
    if bad:
        raise ValueError(f"profile_ids contains unknown profile(s): {bad}")

    deduped: list[str] = []
    seen: set[str] = set()
    for profile_id in requested:
        if profile_id in seen:
            continue
        seen.add(profile_id)
        deduped.append(profile_id)
    return tuple(deduped)


def _row_run_seed(
    *,
    campaign_seed: int,
    text_fixture_id: str,
    period: int,
    columns: int,
    order: str,
    profile_id: str,
    replicate_idx: int,
) -> int:
    return stable_int_from_obj(
        {
            "campaign_seed": campaign_seed,
            "text_fixture_id": text_fixture_id,
            "period": period,
            "columns": columns,
            "order": order,
            "profile_id": profile_id,
            "replicate_idx": replicate_idx,
        },
        bits=63,
    )


def _row_job_id(row_without_job_id: dict[str, Any]) -> str:
    return sha256_hex_from_obj(row_without_job_id)


def build_manifest_rows(campaign_config: dict[str, Any], profile_catalog: dict[str, Any]) -> list[dict[str, Any]]:
    _validate_campaign_config(campaign_config)
    selected_profile_ids = resolve_profile_ids(campaign_config, profile_catalog)

    grid = campaign_config["grid"]
    periods = list(range(grid["period_min"], grid["period_max"] + 1))
    columns = list(range(grid["columns_min"], grid["columns_max"] + 1))
    orders = resolve_orders(grid["orders"])
    replicates_per_cell = int(campaign_config["replicates_per_cell"])
    campaign_seed = int(campaign_config["campaign_seed"])

    fixture_ids = sorted(str(item["text_fixture_id"]) for item in campaign_config["fixtures"])

    config_fingerprint = sha256_hex_from_obj(
        {
            "campaign_config": campaign_config,
            "profile_catalog": profile_catalog,
            "selected_profile_ids": list(selected_profile_ids),
        }
    )

    rows: list[dict[str, Any]] = []
    for text_fixture_id in fixture_ids:
        for period in periods:
            for col in columns:
                for order in orders:
                    for profile_id in selected_profile_ids:
                        for replicate_idx in range(replicates_per_cell):
                            row_base: dict[str, Any] = {
                                "campaign_id": str(campaign_config["campaign_id"]),
                                "git_sha": str(campaign_config["git_sha"]),
                                "text_fixture_id": text_fixture_id,
                                "period": int(period),
                                "columns": int(col),
                                "order": str(order),
                                "profile_id": str(profile_id),
                                "run_seed": _row_run_seed(
                                    campaign_seed=campaign_seed,
                                    text_fixture_id=text_fixture_id,
                                    period=period,
                                    columns=col,
                                    order=order,
                                    profile_id=profile_id,
                                    replicate_idx=replicate_idx,
                                ),
                                "replicate_idx": int(replicate_idx),
                                "config_fingerprint": config_fingerprint,
                            }
                            row = dict(row_base)
                            row["job_id"] = _row_job_id(row_base)
                            rows.append(row)

    rows.sort(
        key=lambda row: (
            row["text_fixture_id"],
            row["period"],
            row["columns"],
            row["order"],
            row["profile_id"],
            row["replicate_idx"],
            row["job_id"],
        )
    )

    job_ids = [row["job_id"] for row in rows]
    if len(job_ids) != len(set(job_ids)):
        raise ValueError("duplicate job_id detected while generating manifest")
    return rows


def _validate_manifest_rows(rows: list[dict[str, Any]], schema_validator: Draft202012Validator) -> None:
    for idx, row in enumerate(rows):
        errors = sorted(schema_validator.iter_errors(row), key=lambda item: item.path)
        if errors:
            first = errors[0]
            raise ValueError(f"manifest row {idx} failed schema validation: {first.message}")


def generate_manifest(
    *,
    campaign_config_path: Path,
    profile_catalog_path: Path,
    manifest_schema_path: Path,
    output_path: Path,
    summary_output_path: Path | None = None,
) -> dict[str, Any]:
    campaign_config = load_json(campaign_config_path)
    profile_catalog = load_json(profile_catalog_path)
    schema_validator = _load_schema_validator(manifest_schema_path)

    rows = build_manifest_rows(campaign_config, profile_catalog)
    _validate_manifest_rows(rows, schema_validator)
    write_jsonl(output_path, rows)

    selected_profiles = resolve_profile_ids(campaign_config, profile_catalog)
    summary = {
        "campaign_id": campaign_config["campaign_id"],
        "git_sha": campaign_config["git_sha"],
        "campaign_seed": campaign_config["campaign_seed"],
        "manifest_path": str(output_path),
        "rows": len(rows),
        "fixtures": sorted({row["text_fixture_id"] for row in rows}),
        "profile_ids": list(selected_profiles),
        "orders": sorted({row["order"] for row in rows}),
        "period_min": min(row["period"] for row in rows) if rows else None,
        "period_max": max(row["period"] for row in rows) if rows else None,
        "columns_min": min(row["columns"] for row in rows) if rows else None,
        "columns_max": max(row["columns"] for row in rows) if rows else None,
        "config_fingerprint": rows[0]["config_fingerprint"] if rows else None,
    }
    if summary_output_path is not None:
        write_json(summary_output_path, summary)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic community benchmark manifest (v1.1).")
    parser.add_argument(
        "--campaign-config",
        type=Path,
        default=DEFAULT_CAMPAIGN_CONFIG,
        help=f"path to campaign config json (default: {DEFAULT_CAMPAIGN_CONFIG})",
    )
    parser.add_argument(
        "--profile-catalog",
        type=Path,
        default=DEFAULT_PROFILE_CATALOG,
        help=f"path to profile catalog json (default: {DEFAULT_PROFILE_CATALOG})",
    )
    parser.add_argument(
        "--manifest-schema",
        type=Path,
        default=DEFAULT_MANIFEST_SCHEMA,
        help=f"path to manifest schema json (default: {DEFAULT_MANIFEST_SCHEMA})",
    )
    parser.add_argument("--output", type=Path, required=True, help="path to output manifest jsonl")
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=None,
        help="optional path to write manifest summary json",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary_path = args.summary_output
    if summary_path is None:
        summary_path = args.output.with_suffix(".summary.json")
    summary = generate_manifest(
        campaign_config_path=args.campaign_config,
        profile_catalog_path=args.profile_catalog,
        manifest_schema_path=args.manifest_schema,
        output_path=args.output,
        summary_output_path=summary_path,
    )
    print(
        "[community] manifest generated "
        f"rows={summary['rows']} campaign_id={summary['campaign_id']} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
