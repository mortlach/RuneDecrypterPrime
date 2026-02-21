from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.benchmarks.community._campaign_common import load_json, read_jsonl, write_json, write_jsonl

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_SCHEMA = REPO_ROOT / "tools" / "benchmarks" / "community" / "schemas" / "manifest_schema_v1_1.json"


def _load_schema_validator(path: Path) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate_manifest_rows(rows: list[dict[str, Any]], schema_validator: Draft202012Validator) -> None:
    seen_job_ids: set[str] = set()
    for idx, row in enumerate(rows):
        errors = sorted(schema_validator.iter_errors(row), key=lambda item: item.path)
        if errors:
            first = errors[0]
            raise ValueError(f"manifest row {idx} failed schema validation: {first.message}")
        job_id = row.get("job_id")
        if job_id in seen_job_ids:
            raise ValueError(f"duplicate job_id in manifest: {job_id}")
        seen_job_ids.add(job_id)


def shard_manifest_rows(rows: list[dict[str, Any]], *, shard_count: int) -> list[list[dict[str, Any]]]:
    if shard_count <= 0:
        raise ValueError("shard_count must be >= 1")
    ordered_rows = sorted(rows, key=lambda row: row["job_id"])
    shards: list[list[dict[str, Any]]] = [[] for _ in range(shard_count)]
    for idx, row in enumerate(ordered_rows):
        shards[idx % shard_count].append(row)
    return shards


def _write_shards(
    *,
    shards: list[list[dict[str, Any]]],
    output_dir: Path,
    basename: str,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    width = max(2, len(str(max(0, len(shards) - 1))))
    shard_records: list[dict[str, Any]] = []

    for shard_idx, shard_rows in enumerate(shards):
        file_name = f"{basename}_{shard_idx:0{width}d}.jsonl"
        file_path = output_dir / file_name
        write_jsonl(file_path, shard_rows)
        shard_records.append(
            {
                "shard_index": shard_idx,
                "path": str(file_path),
                "row_count": len(shard_rows),
                "job_id_first": shard_rows[0]["job_id"] if shard_rows else None,
                "job_id_last": shard_rows[-1]["job_id"] if shard_rows else None,
            }
        )
    return shard_records


def shard_manifest_file(
    *,
    manifest_path: Path,
    manifest_schema_path: Path,
    output_dir: Path,
    shard_count: int,
    basename: str = "manifest_shard",
    index_output_path: Path | None = None,
) -> dict[str, Any]:
    rows = read_jsonl(manifest_path)
    schema_validator = _load_schema_validator(manifest_schema_path)
    _validate_manifest_rows(rows, schema_validator)

    shards = shard_manifest_rows(rows, shard_count=shard_count)
    shard_records = _write_shards(shards=shards, output_dir=output_dir, basename=basename)

    expected_job_ids = {row["job_id"] for row in rows}
    written_job_ids = {row["job_id"] for shard in shards for row in shard}
    if expected_job_ids != written_job_ids:
        missing = sorted(expected_job_ids - written_job_ids)
        extra = sorted(written_job_ids - expected_job_ids)
        raise RuntimeError(f"sharding mismatch: missing={len(missing)} extra={len(extra)}")

    summary = {
        "manifest_path": str(manifest_path),
        "manifest_rows": len(rows),
        "shard_count": shard_count,
        "basename": basename,
        "output_dir": str(output_dir),
        "shards": shard_records,
        "missing_jobs_count": 0,
        "duplicate_jobs_count": 0,
    }
    if index_output_path is None:
        index_output_path = output_dir / "shard_index.json"
    write_json(index_output_path, summary)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shard deterministic community benchmark manifest (v1.1).")
    parser.add_argument("--manifest", type=Path, required=True, help="path to manifest jsonl")
    parser.add_argument(
        "--manifest-schema",
        type=Path,
        default=DEFAULT_MANIFEST_SCHEMA,
        help=f"path to manifest schema json (default: {DEFAULT_MANIFEST_SCHEMA})",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="directory to write shard jsonl files")
    parser.add_argument("--num-shards", type=int, required=True, help="number of shards to create")
    parser.add_argument(
        "--basename",
        type=str,
        default="manifest_shard",
        help="output file basename prefix (default: manifest_shard)",
    )
    parser.add_argument(
        "--index-output",
        type=Path,
        default=None,
        help="optional output path for shard index json (default: <output-dir>/shard_index.json)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = shard_manifest_file(
        manifest_path=args.manifest,
        manifest_schema_path=args.manifest_schema,
        output_dir=args.output_dir,
        shard_count=args.num_shards,
        basename=args.basename,
        index_output_path=args.index_output,
    )
    print(
        "[community] manifest sharded "
        f"rows={summary['manifest_rows']} shards={summary['shard_count']} output_dir={args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
