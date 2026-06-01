from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1"
SHARD_ROOT_PARENT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_asset_shards_v1"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1"
)
REQUIRED_DIRECTIONS = ("fwd",)
REQUIRED_CUTS = ("normal", "strict")
REQUIRED_ORDERS = (2, 3)


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(posixish(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def latest_shard_run_root(parent: Path | None = None) -> Path:
    root_parent = parent or (REPO_ROOT / SHARD_ROOT_PARENT_REL)
    candidates = [
        path
        for path in root_parent.iterdir()
        if path.is_dir() and (path / "shard_build_config.json").exists()
    ] if root_parent.exists() else []
    if not candidates:
        raise FileNotFoundError(f"no shard build config found under {SHARD_ROOT_PARENT_REL}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def expected_shard_rows(run_root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    source_rows = config.get("source_rows", [])
    if not isinstance(source_rows, list):
        return []
    return [
        {
            "ngram_order": int(row.get("ngram_order", 0) or 0),
            "shard_index": int(row.get("shard_index", 0) or 0),
            "source_file_name": str(row.get("source_file_name", "")),
            "source_file_bytes": int(row.get("source_file_bytes", 0) or 0),
            "expected_manifest_rel": expected_manifest_rel(run_root, row),
        }
        for row in source_rows
    ]


def expected_manifest_rel(run_root: Path, row: dict[str, Any]) -> str:
    order = int(row.get("ngram_order", 0) or 0)
    shard_index = int(row.get("shard_index", 0) or 0)
    source_name = str(row.get("source_file_name", ""))
    matches = sorted(
        (run_root / f"order_{order}").glob(f"shard_{shard_index:04d}__*/shard_manifest.json")
        if (run_root / f"order_{order}").exists()
        else []
    )
    if matches:
        return repo_rel(matches[0])
    safe_source = source_name.replace("\\", "/").split("/")[-1]
    return f"{repo_rel(run_root)}/order_{order}/shard_{shard_index:04d}__{safe_source}/shard_manifest.json"


def load_completed_manifest_rows(run_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    shard_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []
    for manifest_path in sorted(run_root.glob("order_*/shard_*/shard_manifest.json")):
        manifest = read_json(manifest_path)
        status = str(manifest.get("status", ""))
        order = int(manifest.get("ngram_order", 0) or 0)
        shard_index = int(manifest.get("shard_index", 0) or 0)
        source_file_bytes = int(manifest.get("source_file_bytes", 0) or 0)
        output_files = manifest.get("output_files", [])
        source_stats = manifest.get("source_stats", [])
        source_lines = sum(int(row.get("lines_seen", 0) or 0) for row in source_stats if isinstance(row, dict))
        valid_rows = sum(int(row.get("valid_format_rows", 0) or 0) for row in source_stats if isinstance(row, dict))
        shard_rows.append(
            {
                "manifest_path": repo_rel(manifest_path),
                "status": status,
                "ngram_order": order,
                "shard_index": shard_index,
                "source_file_name": str(manifest.get("source_file_name", "")),
                "source_file_bytes": source_file_bytes,
                "elapsed_seconds": float(manifest.get("elapsed_seconds", 0.0) or 0.0),
                "source_lines_seen": source_lines,
                "source_valid_format_rows": valid_rows,
                "output_file_count": len(output_files) if isinstance(output_files, list) else 0,
                "aggregate_rows": sum(int(row.get("aggregate_rows", 0) or 0) for row in output_files if isinstance(row, dict)),
                "dictionary_kept_rows": sum(int(row.get("dictionary_kept_rows", 0) or 0) for row in output_files if isinstance(row, dict)),
            }
        )
        if not isinstance(output_files, list):
            continue
        for row in output_files:
            if not isinstance(row, dict):
                continue
            output_file = str(row.get("output_file", ""))
            output_path = REPO_ROOT / output_file
            output_rows.append(
                {
                    "manifest_path": repo_rel(manifest_path),
                    "ngram_order": int(row.get("ngram_order", order) or order),
                    "shard_index": shard_index,
                    "source_file_name": str(manifest.get("source_file_name", "")),
                    "dictionary_cut": str(row.get("dictionary_cut", "")),
                    "direction": str(row.get("direction", "")),
                    "output_file": output_file.replace("\\", "/"),
                    "output_file_exists": output_path.exists(),
                    "bytes": int(row.get("bytes", 0) or 0),
                    "aggregate_rows": int(row.get("aggregate_rows", 0) or 0),
                    "dictionary_kept_rows": int(row.get("dictionary_kept_rows", 0) or 0),
                    "count_sum": int(row.get("count_sum", 0) or 0),
                }
            )
    return shard_rows, output_rows


def source_word_lengths(source_file_name: str) -> tuple[int, ...]:
    stem = Path(source_file_name.replace("\\", "/")).stem
    parts = stem.replace("_", " ").split()
    lengths: list[int] = []
    for part in parts:
        if not part.isdigit():
            return ()
        lengths.append(int(part))
    return tuple(lengths)


def distribution_rows(
    output_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    phrase_totals: dict[tuple[int, str, str, int], dict[str, int]] = {}
    word_totals: dict[tuple[int, str, str, int, int], dict[str, int]] = {}
    parse_counters = {
        "length_partition_source_output_files": 0,
        "length_partition_parsed_output_files": 0,
        "length_partition_unparsed_output_files": 0,
        "length_partition_source_aggregate_rows": 0,
        "length_partition_parsed_aggregate_rows": 0,
        "length_partition_unparsed_aggregate_rows": 0,
        "length_partition_source_dictionary_kept_rows": 0,
        "length_partition_parsed_dictionary_kept_rows": 0,
        "length_partition_unparsed_dictionary_kept_rows": 0,
    }
    for row in output_rows:
        word_lengths = source_word_lengths(str(row.get("source_file_name", "")))
        aggregate_rows = int(row.get("aggregate_rows", 0) or 0)
        dictionary_kept_rows = int(row.get("dictionary_kept_rows", 0) or 0)
        parse_counters["length_partition_source_output_files"] += 1
        parse_counters["length_partition_source_aggregate_rows"] += aggregate_rows
        parse_counters["length_partition_source_dictionary_kept_rows"] += dictionary_kept_rows
        if not word_lengths:
            parse_counters["length_partition_unparsed_output_files"] += 1
            parse_counters["length_partition_unparsed_aggregate_rows"] += aggregate_rows
            parse_counters["length_partition_unparsed_dictionary_kept_rows"] += dictionary_kept_rows
            continue
        parse_counters["length_partition_parsed_output_files"] += 1
        parse_counters["length_partition_parsed_aggregate_rows"] += aggregate_rows
        parse_counters["length_partition_parsed_dictionary_kept_rows"] += dictionary_kept_rows
        order = int(row.get("ngram_order", 0) or 0)
        cut = str(row.get("dictionary_cut", ""))
        direction = str(row.get("direction", ""))
        count_sum = int(row.get("count_sum", 0) or 0)
        phrase_key = (order, cut, direction, sum(word_lengths))
        phrase_bucket = phrase_totals.setdefault(
            phrase_key,
            {"row_count": 0, "dictionary_kept_rows": 0, "aggregate_rows": 0, "count_sum": 0, "source_output_file_count": 0},
        )
        phrase_bucket["row_count"] += aggregate_rows
        phrase_bucket["dictionary_kept_rows"] += dictionary_kept_rows
        phrase_bucket["aggregate_rows"] += aggregate_rows
        phrase_bucket["count_sum"] += count_sum
        phrase_bucket["source_output_file_count"] += 1
        for index, word_length in enumerate(word_lengths, start=1):
            word_key = (order, cut, direction, index, word_length)
            word_bucket = word_totals.setdefault(
                word_key,
                {
                    "row_count": 0,
                    "dictionary_kept_rows": 0,
                    "aggregate_rows": 0,
                    "count_sum": 0,
                    "source_output_file_count": 0,
                },
            )
            word_bucket["row_count"] += aggregate_rows
            word_bucket["dictionary_kept_rows"] += dictionary_kept_rows
            word_bucket["aggregate_rows"] += aggregate_rows
            word_bucket["count_sum"] += count_sum
            word_bucket["source_output_file_count"] += 1
    phrase_rows = [
        {
            "ngram_order": order,
            "dictionary_cut": cut,
            "direction": direction,
            "phrase_token_length": phrase_token_length,
            **counts,
        }
        for (order, cut, direction, phrase_token_length), counts in sorted(phrase_totals.items())
    ]
    word_rows = [
        {
            "ngram_order": order,
            "dictionary_cut": cut,
            "direction": direction,
            "word_position": word_position,
            "word_token_length": word_token_length,
            **counts,
        }
        for (order, cut, direction, word_position, word_token_length), counts in sorted(word_totals.items())
    ]
    return phrase_rows, word_rows, parse_counters


def build_missing_rows(expected_rows: list[dict[str, Any]], shard_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    completed_keys = {
        (int(row["ngram_order"]), int(row["shard_index"]))
        for row in shard_rows
        if row.get("status") == "pass"
    }
    return [
        {
            "ngram_order": row["ngram_order"],
            "shard_index": row["shard_index"],
            "source_file_name": row["source_file_name"],
            "source_file_bytes": row["source_file_bytes"],
            "expected_manifest_rel": row["expected_manifest_rel"],
        }
        for row in expected_rows
        if (int(row["ngram_order"]), int(row["shard_index"])) not in completed_keys
    ]


def count_by_key(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    counts: Counter[tuple[Any, ...]] = Counter(tuple(row.get(key, "") for key in keys) for row in rows)
    return [
        {**{key: value for key, value in zip(keys, values, strict=True)}, "row_count": count}
        for values, count in sorted(counts.items())
    ]


def missing_required_output_combos(
    output_rows: list[dict[str, Any]],
    required_orders: tuple[int, ...],
    required_cuts: tuple[str, ...],
    required_directions: tuple[str, ...],
) -> list[dict[str, Any]]:
    present = {
        (
            int(row.get("ngram_order", 0) or 0),
            str(row.get("dictionary_cut", "")),
            str(row.get("direction", "")),
        )
        for row in output_rows
        if row.get("output_file_exists")
    }
    return [
        {
            "ngram_order": order,
            "dictionary_cut": cut,
            "direction": direction,
        }
        for order in required_orders
        for cut in required_cuts
        for direction in required_directions
        if (order, cut, direction) not in present
    ]


def summarise_shard_provenance(
    run_root: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    selected_run_root = run_root or latest_shard_run_root()
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    config_path = selected_run_root / "shard_build_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"missing shard_build_config.json under {repo_rel(selected_run_root)}")
    config = read_json(config_path)
    expected_rows = expected_shard_rows(selected_run_root, config)
    shard_rows, output_rows = load_completed_manifest_rows(selected_run_root)
    phrase_length_distribution_rows, word_length_distribution_rows, length_partition_counters = distribution_rows(output_rows)
    missing_rows = build_missing_rows(expected_rows, shard_rows)
    failed_rows = [row for row in shard_rows if row.get("status") != "pass"]
    output_missing_rows = [row for row in output_rows if not row.get("output_file_exists")]
    required_orders = tuple(int(value) for value in config.get("required_orders", REQUIRED_ORDERS))
    required_cuts = tuple(str(value) for value in config.get("required_cuts", REQUIRED_CUTS))
    required_directions = tuple(str(value) for value in config.get("required_directions", REQUIRED_DIRECTIONS))
    missing_output_combo_rows = missing_required_output_combos(
        output_rows,
        required_orders,
        required_cuts,
        required_directions,
    )
    completed_rows = [row for row in shard_rows if row.get("status") == "pass"]
    status = (
        "pass"
        if expected_rows
        and not missing_rows
        and not failed_rows
        and not output_missing_rows
        and not missing_output_combo_rows
        else "running_or_interrupted"
    )
    completed_source_bytes = sum(int(row.get("source_file_bytes", 0) or 0) for row in completed_rows)
    total_source_bytes = sum(int(row.get("source_file_bytes", 0) or 0) for row in expected_rows)
    completed_fraction = completed_source_bytes / total_source_bytes if total_source_bytes else 0.0
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "asset_mode": "full",
        "full_raw_ngram_rebuild_confirmed": status == "pass",
        "sample_line_limit_per_order": config.get("sample_line_limit_per_order"),
        "sample_line_limit_per_order_present": config.get("sample_line_limit_per_order") is not None,
        "run_root": repo_rel(selected_run_root),
        "required_orders": list(required_orders),
        "required_cuts": list(required_cuts),
        "required_directions": list(required_directions),
        "total_shards": len(expected_rows),
        "completed_shards": len(completed_rows),
        "missing_shards": len(missing_rows),
        "failed_shards": len(failed_rows),
        "output_files": len(output_rows),
        "missing_output_files": len(output_missing_rows),
        "missing_required_output_combos": len(missing_output_combo_rows),
        "missing_required_output_combo_rows": missing_output_combo_rows,
        "phrase_length_distribution_rows": len(phrase_length_distribution_rows),
        "word_length_distribution_rows": len(word_length_distribution_rows),
        "phrase_length_distribution_present": bool(phrase_length_distribution_rows),
        "word_length_distribution_present": bool(word_length_distribution_rows),
        "distribution_derivation": "source_file_name_word_length_partition_contract",
        **length_partition_counters,
        "source_bytes_total": total_source_bytes,
        "source_bytes_completed": completed_source_bytes,
        "source_bytes_completed_fraction": completed_fraction,
        "aggregate_rows": sum(int(row.get("aggregate_rows", 0) or 0) for row in output_rows),
        "dictionary_kept_rows": sum(int(row.get("dictionary_kept_rows", 0) or 0) for row in output_rows),
        "source_lines_seen": sum(int(row.get("source_lines_seen", 0) or 0) for row in completed_rows),
        "source_valid_format_rows": sum(int(row.get("source_valid_format_rows", 0) or 0) for row in completed_rows),
        "shard_count_by_order": count_by_key(completed_rows, ("ngram_order",)),
        "output_count_by_order_cut_direction": count_by_key(output_rows, ("ngram_order", "dictionary_cut", "direction")),
        "blocked_reasons": blocked_reasons(
            status,
            missing_rows,
            failed_rows,
            output_missing_rows,
            missing_output_combo_rows,
        ),
    }
    write_json(selected_output_dir / "shard_provenance_manifest.json", manifest)
    write_csv(selected_output_dir / "shard_rows.csv", shard_rows)
    write_csv(selected_output_dir / "output_file_rows.csv", output_rows)
    write_csv(selected_output_dir / "missing_shard_rows.csv", missing_rows)
    write_csv(selected_output_dir / "missing_required_output_combo_rows.csv", missing_output_combo_rows)
    write_csv(selected_output_dir / "phrase_length_distribution_rows.csv", phrase_length_distribution_rows)
    write_csv(selected_output_dir / "word_length_distribution_rows.csv", word_length_distribution_rows)
    write_readout(selected_output_dir / "readout.md", manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] completed_shards={manifest['completed_shards']}/{manifest['total_shards']}")
    return manifest


def blocked_reasons(
    status: str,
    missing_rows: list[dict[str, Any]],
    failed_rows: list[dict[str, Any]],
    output_missing_rows: list[dict[str, Any]],
    missing_output_combo_rows: list[dict[str, Any]],
) -> list[str]:
    if status == "pass":
        return []
    reasons: list[str] = []
    if missing_rows:
        reasons.append("not all expected shard manifests are complete")
    if failed_rows:
        reasons.append("one or more shard manifests are non-pass")
    if output_missing_rows:
        reasons.append("one or more declared shard output files are missing")
    if missing_output_combo_rows:
        reasons.append("one or more required order/cut/direction output combos are missing")
    return reasons


def write_readout(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Full Raw Asset Shard Provenance v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- run root: `{manifest['run_root']}`",
        f"- completed shards: `{manifest['completed_shards']} / {manifest['total_shards']}`",
        f"- missing shards: `{manifest['missing_shards']}`",
        f"- failed shards: `{manifest['failed_shards']}`",
        f"- output files declared: `{manifest['output_files']}`",
        f"- missing output files: `{manifest['missing_output_files']}`",
        f"- missing required output combos: `{manifest['missing_required_output_combos']}`",
        f"- phrase length distribution rows: `{manifest['phrase_length_distribution_rows']}`",
        f"- word length distribution rows: `{manifest['word_length_distribution_rows']}`",
        f"- length partition parsed output files: `{manifest['length_partition_parsed_output_files']} / {manifest['length_partition_source_output_files']}`",
        f"- length partition unparsed output files: `{manifest['length_partition_unparsed_output_files']}`",
        f"- length partition unparsed aggregate rows: `{manifest['length_partition_unparsed_aggregate_rows']}`",
        f"- source bytes completed fraction: `{manifest['source_bytes_completed_fraction']:.6f}`",
        f"- full raw confirmed: `{manifest['full_raw_ngram_rebuild_confirmed']}`",
        "",
        "This is a shard provenance summary. It is allowed to be partial while the",
        "full raw shard builder is still running, but a partial status must not be",
        "used as a full raw asset/provenance pass.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    summarise_shard_provenance()


if __name__ == "__main__":
    main()
