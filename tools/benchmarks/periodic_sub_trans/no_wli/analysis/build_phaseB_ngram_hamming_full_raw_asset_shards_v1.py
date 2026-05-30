from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_full_raw_asset_shards_v1"
OUTPUT_ROOT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_asset_shards_v1"
)
CHECKED_BUILDER_REL = (
    "tools/benchmarks/scoring/word_ngrams/phaseB_filtered_ngram_index_v1_checked_patch/"
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_filtered_ngram_index_v1.py"
)

RUN_MODE = "full"
SHARD_MODE = "one_source_file_per_shard"
REQUIRED_ORDERS = (2, 3)
REQUIRED_CUTS = ("normal", "strict")
REQUIRED_DIRECTIONS = ("fwd",)
SAMPLE_LINE_LIMIT_PER_ORDER: None = None
PROGRESS_EVERY_LINES = 1_000_000
INTENDED_WALLCLOCK_BUDGET = "36h"
STOP_CONDITION = "all_shards_complete_or_first_clear_blocker"
CREATE_NEW_RUN = True
RESUME_LATEST_INCOMPLETE_RUN = True
USE_OPTIMIZED_SCAN = True


def utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "unknown"
    total = int(seconds)
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{sec:02d}s"
    return f"{minutes}m{sec:02d}s"


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


def safe_slug(value: str) -> str:
    text = value.replace("\\", "/").split("/")[-1]
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._")
    return text or "source"


def load_checked_builder() -> Any:
    builder_path = REPO_ROOT / CHECKED_BUILDER_REL
    if not builder_path.exists():
        raise FileNotFoundError(f"checked builder missing: {CHECKED_BUILDER_REL}")
    spec = importlib.util.spec_from_file_location("phaseB_filtered_ngram_index_builder_checked", builder_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load checked full raw builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def output_root() -> Path:
    return REPO_ROOT / OUTPUT_ROOT_REL


def latest_incomplete_run(root: Path) -> Path | None:
    if not root.exists():
        return None
    candidates = [
        path
        for path in root.iterdir()
        if path.is_dir() and (path / "shard_build_config.json").exists()
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for candidate in candidates:
        manifest = candidate / "shard_build_manifest.json"
        if not manifest.exists():
            return candidate
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return candidate
        if payload.get("status") != "pass":
            return candidate
    return None


def run_root() -> Path:
    root = output_root()
    root.mkdir(parents=True, exist_ok=True)
    if RESUME_LATEST_INCOMPLETE_RUN:
        existing = latest_incomplete_run(root)
        if existing is not None:
            return existing
    return root / f"{utc_label()}__{RUN_LABEL}"


def make_base_config(builder: Any) -> Any:
    return builder.BuildConfig(
        repo_root=REPO_ROOT,
        raw_ngram_root=builder.RAW_NGRAM_ROOT,
        raw_ngram_files_by_order=builder.RAW_NGRAM_FILES_BY_ORDER,
        raw_ngram_globs_by_order=builder.RAW_NGRAM_GLOBS_BY_ORDER,
        dictionary_dirs_by_cut=builder.DICTIONARY_DIRS_BY_CUT,
        output_root=output_root(),
        enabled_orders=REQUIRED_ORDERS,
        enabled_cuts=REQUIRED_CUTS,
        enabled_directions=REQUIRED_DIRECTIONS,
        run_mode=RUN_MODE,
        create_timestamped_run_dir=False,
        sample_line_limit_per_order=SAMPLE_LINE_LIMIT_PER_ORDER,
        progress_every_lines=PROGRESS_EVERY_LINES,
    )


def make_shard_config(builder: Any, base_config: Any, order: int, source_path: Path) -> Any:
    return builder.BuildConfig(
        repo_root=REPO_ROOT,
        raw_ngram_root=base_config.raw_ngram_root,
        raw_ngram_files_by_order={order: [source_path]},
        raw_ngram_globs_by_order={order: []},
        dictionary_dirs_by_cut=base_config.dictionary_dirs_by_cut,
        output_root=base_config.output_root,
        enabled_orders=(order,),
        enabled_cuts=REQUIRED_CUTS,
        enabled_directions=REQUIRED_DIRECTIONS,
        run_mode=RUN_MODE,
        create_timestamped_run_dir=False,
        sample_line_limit_per_order=SAMPLE_LINE_LIMIT_PER_ORDER,
        progress_every_lines=PROGRESS_EVERY_LINES,
        require_plain_lowercase_words=base_config.require_plain_lowercase_words,
        aggregate_duplicate_rune_keys=base_config.aggregate_duplicate_rune_keys,
    )


def write_json(path: Path, payload: object) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(posixish(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_under_repo(path)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def shard_manifest_path(run_dir: Path, order: int, shard_index: int, source_path: Path) -> Path:
    shard_dir = run_dir / f"order_{order}" / f"shard_{shard_index:04d}__{safe_slug(source_path.name)}"
    return shard_dir / "shard_manifest.json"


def shard_is_complete(run_dir: Path, order: int, shard_index: int, source_path: Path) -> bool:
    manifest_path = shard_manifest_path(run_dir, order, shard_index, source_path)
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return manifest.get("status") == "pass"


def write_top_level_config(run_dir: Path, base_config: Any, source_rows: list[dict[str, Any]]) -> None:
    payload = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "run_mode": RUN_MODE,
        "asset_mode": "full",
        "shard_mode": SHARD_MODE,
        "required_orders": list(REQUIRED_ORDERS),
        "required_cuts": list(REQUIRED_CUTS),
        "required_directions": list(REQUIRED_DIRECTIONS),
        "sample_line_limit_per_order": SAMPLE_LINE_LIMIT_PER_ORDER,
        "sample_line_limit_per_order_present": False,
        "intended_wallclock_budget": INTENDED_WALLCLOCK_BUDGET,
        "stop_condition": STOP_CONDITION,
        "resume_latest_incomplete_run": RESUME_LATEST_INCOMPLETE_RUN,
        "use_optimized_scan": USE_OPTIMIZED_SCAN,
        "optimized_scan_contract": (
            "parse once, compute cut eligibility once, encode once per kept phrase/direction, "
            "then add the encoded phrase to all kept cut buckets"
        ),
        "source_file_count": len(source_rows),
        "source_rows": source_rows,
        "raw_ngram_root_name": Path(str(base_config.raw_ngram_root)).name,
        "dictionary_dirs_by_cut": {k: str(v) for k, v in base_config.dictionary_dirs_by_cut.items()},
    }
    write_json(run_dir / "shard_build_config.json", payload)


def build_source_rows(builder: Any, base_config: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for order in REQUIRED_ORDERS:
        paths = builder.expand_ngram_paths(base_config, int(order))
        if not paths:
            raise FileNotFoundError(f"no raw n-gram source files found for order {order}")
        for shard_index, path in enumerate(paths, start=1):
            rows.append(
                {
                    "ngram_order": int(order),
                    "shard_index": int(shard_index),
                    "source_file_name": path.name,
                    "source_file_bytes": int(path.stat().st_size),
                    "source_path_name": path.name,
                }
            )
    return rows


def write_progress_manifest(
    run_dir: Path,
    rows: list[dict[str, Any]],
    started: float,
    *,
    resume_completed_bytes_at_start: int = 0,
    resume_completed_shards_at_start: int = 0,
) -> dict[str, Any]:
    completed = [row for row in rows if row.get("status") == "pass"]
    blocked = [row for row in rows if row.get("status") == "blocked"]
    elapsed = time.monotonic() - started
    completed_bytes = sum(int(row.get("source_file_bytes", 0)) for row in completed)
    total_bytes = sum(int(row.get("source_file_bytes", 0)) for row in rows)
    completed_this_run_bytes = max(0, completed_bytes - int(resume_completed_bytes_at_start))
    remaining_bytes = max(0, total_bytes - completed_bytes)
    eta = (
        elapsed * remaining_bytes / completed_this_run_bytes
        if completed_this_run_bytes > 0 and remaining_bytes > 0
        else None
    )
    manifest = {
        "run_label": RUN_LABEL,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blocked else ("pass" if len(completed) == len(rows) else "running_or_interrupted"),
        "asset_mode": "full",
        "sample_line_limit_per_order": SAMPLE_LINE_LIMIT_PER_ORDER,
        "sample_line_limit_per_order_present": False,
        "shard_mode": SHARD_MODE,
        "completed_shards": len(completed),
        "total_shards": len(rows),
        "blocked_shards": len(blocked),
        "completed_bytes": completed_bytes,
        "completed_this_run_bytes": completed_this_run_bytes,
        "total_bytes": total_bytes,
        "elapsed_seconds": elapsed,
        "elapsed": format_duration(elapsed),
        "eta_by_completed_bytes": format_duration(eta),
        "eta_method": "resume_adjusted_completed_bytes",
        "resume_completed_bytes_at_start": int(resume_completed_bytes_at_start),
        "resume_completed_shards_at_start": int(resume_completed_shards_at_start),
        "intended_wallclock_budget": INTENDED_WALLCLOCK_BUDGET,
        "stop_condition": STOP_CONDITION,
        "run_root": repo_rel(run_dir),
    }
    write_json(run_dir / "shard_build_manifest.json", manifest)
    write_csv(
        run_dir / "shard_build_progress.csv",
        rows,
        [
            "ngram_order",
            "shard_index",
            "source_file_name",
            "source_file_bytes",
            "status",
            "elapsed_seconds",
            "aggregate_rows",
            "dictionary_kept_rows",
            "output_file_count",
            "manifest_path",
            "blocked_reason",
        ],
    )
    return manifest


def populate_completed_shards(
    *,
    run_dir: Path,
    rows: list[dict[str, Any]],
    path_lookup: dict[tuple[int, int], Path],
) -> tuple[int, int]:
    completed_count = 0
    completed_bytes = 0
    for row in rows:
        order = int(row["ngram_order"])
        shard_index = int(row["shard_index"])
        source_path = path_lookup[(order, shard_index)]
        if not shard_is_complete(run_dir, order, shard_index, source_path):
            continue
        manifest_path = shard_manifest_path(run_dir, order, shard_index, source_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        row["status"] = "pass"
        row["elapsed_seconds"] = manifest.get("elapsed_seconds", "")
        row["aggregate_rows"] = sum(int(item.get("aggregate_rows", 0)) for item in manifest.get("output_files", []))
        row["dictionary_kept_rows"] = sum(int(item.get("dictionary_kept_rows", 0)) for item in manifest.get("output_files", []))
        row["output_file_count"] = len(manifest.get("output_files", []))
        row["manifest_path"] = repo_rel(manifest_path)
        completed_count += 1
        completed_bytes += int(row["source_file_bytes"])
    return completed_count, completed_bytes


def scan_sources_for_order_optimized(
    *,
    builder: Any,
    n: int,
    paths: list[Path],
    dictionary_sets: Any,
    config: Any,
) -> tuple[dict[tuple[int, str, str], dict[bytes, Any]], list[Any], list[Any]]:
    aggregates: dict[tuple[int, str, str], dict[bytes, Any]] = {
        (int(n), cut, direction): {}
        for cut in config.enabled_cuts
        for direction in config.enabled_directions
    }
    output_stats: dict[tuple[int, str, str], Any] = {
        (int(n), cut, direction): builder.OutputStats(
            n=int(n),
            dictionary_cut=cut,
            encoding_direction=direction,
        )
        for cut in config.enabled_cuts
        for direction in config.enabled_directions
    }
    source_stats: list[Any] = []

    max_lines = None if config.run_mode == "full" else int(config.sample_line_limit_per_order)
    total_lines_for_order = 0
    total_files = len(paths)
    total_bytes = sum(int(path.stat().st_size) for path in paths if path.exists())
    completed_bytes = 0
    order_started = time.monotonic()

    for file_index, fp in enumerate(paths, start=1):
        if not fp.exists():
            raise FileNotFoundError(f"N-gram source file not found: {fp}")
        stat = builder.SourceStats(n=int(n), source_file=str(fp), bytes_total=int(fp.stat().st_size))
        source_stats.append(stat)
        file_started = time.monotonic()
        with fp.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if max_lines is not None and total_lines_for_order >= max_lines:
                    break
                total_lines_for_order += 1
                stat.lines_seen += 1
                parsed, reason = builder.parse_ngram_line_with_reason(
                    line,
                    expected_n=int(n),
                    require_plain_words=config.require_plain_lowercase_words,
                )
                for out_stat in output_stats.values():
                    if out_stat.n == int(n):
                        out_stat.input_rows_seen += 1
                if parsed is None:
                    if reason == "bad_count":
                        stat.rejected_bad_count += 1
                    elif reason == "wrong_order":
                        stat.rejected_wrong_order += 1
                    elif reason == "non_plain":
                        stat.rejected_non_plain += 1
                    continue

                stat.valid_format_rows += 1
                cut_keeps: dict[str, bool] = {}
                for cut in config.enabled_cuts:
                    selected_words = dictionary_sets[cut]
                    keeps = all(word in selected_words for word in parsed.words)
                    cut_keeps[cut] = keeps
                    for direction in config.enabled_directions:
                        out_stat = output_stats[(int(n), cut, direction)]
                        out_stat.valid_format_rows += 1
                        if not keeps:
                            out_stat.dictionary_rejected_rows += 1

                if not any(cut_keeps.values()):
                    continue

                latin_ngram = " ".join(parsed.words)
                for direction in config.enabled_directions:
                    encoded = builder.encode_phrase(parsed.words, direction=direction)
                    if not encoded.rune_token_ids:
                        for keeps in cut_keeps.values():
                            if keeps:
                                stat.rejected_empty_encoding += 1
                        continue
                    for cut, keeps in cut_keeps.items():
                        if not keeps:
                            continue
                        out_key = (int(n), cut, direction)
                        out_stat = output_stats[out_key]
                        bucket = aggregates[out_key]
                        row = bucket.get(encoded.key)
                        if row is None:
                            row = builder.AggregateRow(encoded=encoded)
                            bucket[encoded.key] = row
                        row.add(latin_ngram=latin_ngram, count=parsed.count, source_file=fp.name)
                        out_stat.dictionary_kept_rows += 1
                        out_stat.count_sum += int(parsed.count)

                if config.progress_every_lines > 0 and total_lines_for_order % int(config.progress_every_lines) == 0:
                    elapsed = time.monotonic() - order_started
                    completed_fraction = completed_bytes / total_bytes if total_bytes else 0.0
                    eta = (elapsed / completed_fraction - elapsed) if completed_fraction > 0 else None
                    line_rate = total_lines_for_order / elapsed if elapsed > 0 else 0.0
                    print(
                        f"[{RUN_LABEL}] n={n} files_completed={file_index - 1}/{total_files} "
                        f"completed_bytes={completed_bytes:,}/{total_bytes:,} "
                        f"lines={total_lines_for_order:,} current_file={fp.name} "
                        f"elapsed={format_duration(elapsed)} eta_by_completed_bytes={format_duration(eta)} "
                        f"lines_per_sec={line_rate:,.1f}",
                        flush=True,
                    )
        completed_bytes += stat.bytes_total
        elapsed = time.monotonic() - order_started
        completed_fraction = completed_bytes / total_bytes if total_bytes else 0.0
        eta = (elapsed / completed_fraction - elapsed) if completed_fraction > 0 else None
        print(
            f"[{RUN_LABEL}] n={n} files_completed={file_index}/{total_files} "
            f"completed_bytes={completed_bytes:,}/{total_bytes:,} "
            f"file_elapsed={format_duration(time.monotonic() - file_started)} "
            f"elapsed={format_duration(elapsed)} eta_by_completed_bytes={format_duration(eta)}",
            flush=True,
        )
        if max_lines is not None and total_lines_for_order >= max_lines:
            break

    for key, bucket in aggregates.items():
        output_stats[key].aggregate_rows = len(bucket)
    return aggregates, source_stats, list(output_stats.values())


def build_one_shard(
    *,
    builder: Any,
    dictionary_sets: Any,
    base_config: Any,
    run_dir: Path,
    order: int,
    shard_index: int,
    total_shards: int,
    source_path: Path,
    started: float,
    completed_before: int,
    total_bytes: int,
    completed_bytes_before: int,
    resume_completed_bytes_at_start: int,
) -> dict[str, Any]:
    shard_dir = run_dir / f"order_{order}" / f"shard_{shard_index:04d}__{safe_slug(source_path.name)}"
    ensure_under_repo(shard_dir / "placeholder")
    shard_start = time.monotonic()
    print(
        f"[{RUN_LABEL}] shard_start={completed_before + 1}/{total_shards} "
        f"order={order} shard={shard_index} source={source_path.name} "
        f"bytes={source_path.stat().st_size:,} elapsed={format_duration(time.monotonic() - started)}",
        flush=True,
    )
    shard_config = make_shard_config(builder, base_config, order, source_path)
    if USE_OPTIMIZED_SCAN:
        aggregates, source_stats, output_stats = scan_sources_for_order_optimized(
            builder=builder,
            n=int(order),
            paths=[source_path],
            dictionary_sets=dictionary_sets,
            config=shard_config,
        )
    else:
        aggregates, source_stats, output_stats = builder.scan_sources_for_order(
            n=int(order),
            paths=[source_path],
            dictionary_sets=dictionary_sets,
            config=shard_config,
        )
    output_files: list[dict[str, Any]] = []
    for stat in output_stats:
        bucket = aggregates[(stat.n, stat.dictionary_cut, stat.encoding_direction)]
        rel = Path(f"{stat.dictionary_cut}_{stat.encoding_direction}") / f"ngram{stat.n}.csv.gz"
        fp = shard_dir / rel
        builder.write_aggregate_csv(
            fp,
            bucket.values(),
            n=stat.n,
            cut=stat.dictionary_cut,
            direction=stat.encoding_direction,
        )
        stat.output_file = repo_rel(fp)
        output_files.append(
            {
                "dictionary_cut": stat.dictionary_cut,
                "direction": stat.encoding_direction,
                "ngram_order": int(stat.n),
                "output_file": repo_rel(fp),
                "bytes": fp.stat().st_size,
                "aggregate_rows": int(stat.aggregate_rows),
                "dictionary_kept_rows": int(stat.dictionary_kept_rows),
                "count_sum": int(stat.count_sum),
            }
        )
    elapsed = time.monotonic() - shard_start
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "asset_mode": "full",
        "sample_line_limit_per_order": SAMPLE_LINE_LIMIT_PER_ORDER,
        "sample_line_limit_per_order_present": False,
        "shard_mode": SHARD_MODE,
        "use_optimized_scan": USE_OPTIMIZED_SCAN,
        "ngram_order": int(order),
        "shard_index": int(shard_index),
        "source_file_name": source_path.name,
        "source_file_bytes": int(source_path.stat().st_size),
        "elapsed_seconds": elapsed,
        "elapsed": format_duration(elapsed),
        "output_files": output_files,
        "source_stats": [stat.__dict__ for stat in source_stats],
        "output_stats": [stat.__dict__ for stat in output_stats],
    }
    write_json(shard_dir / "shard_manifest.json", manifest)
    completed_bytes = completed_bytes_before + int(source_path.stat().st_size)
    total_elapsed = time.monotonic() - started
    completed_this_run_bytes = max(0, completed_bytes - int(resume_completed_bytes_at_start))
    remaining_bytes = max(0, total_bytes - completed_bytes)
    eta = (
        total_elapsed * remaining_bytes / completed_this_run_bytes
        if completed_this_run_bytes > 0 and remaining_bytes > 0
        else None
    )
    print(
        f"[{RUN_LABEL}] shard_done={completed_before + 1}/{total_shards} "
        f"order={order} shard={shard_index} elapsed={format_duration(elapsed)} "
        f"total_elapsed={format_duration(total_elapsed)} eta_by_completed_bytes={format_duration(eta)} "
        f"outputs={len(output_files)}",
        flush=True,
    )
    return manifest


def main() -> None:
    builder = load_checked_builder()
    builder.RUN_LABEL = RUN_LABEL
    base_config = make_base_config(builder)
    run_dir = run_root()
    run_dir.mkdir(parents=True, exist_ok=True)
    dictionary_sets = builder.load_dictionary_sets(base_config)
    source_rows = build_source_rows(builder, base_config)
    write_top_level_config(run_dir, base_config, source_rows)

    path_lookup: dict[tuple[int, int], Path] = {}
    for order in REQUIRED_ORDERS:
        for shard_index, path in enumerate(builder.expand_ngram_paths(base_config, int(order)), start=1):
            path_lookup[(int(order), int(shard_index))] = path

    total_shards = len(source_rows)
    total_bytes = sum(int(row["source_file_bytes"]) for row in source_rows)
    started = time.monotonic()
    rows = [dict(row, status="", elapsed_seconds="", aggregate_rows="", dictionary_kept_rows="", output_file_count="", manifest_path="", blocked_reason="") for row in source_rows]
    completed_count, completed_bytes = populate_completed_shards(
        run_dir=run_dir,
        rows=rows,
        path_lookup=path_lookup,
    )
    resume_completed_count = completed_count
    resume_completed_bytes = completed_bytes
    write_progress_manifest(
        run_dir,
        rows,
        started,
        resume_completed_bytes_at_start=resume_completed_bytes,
        resume_completed_shards_at_start=resume_completed_count,
    )

    print(f"[{RUN_LABEL}] run_root={repo_rel(run_dir)}", flush=True)
    print(f"[{RUN_LABEL}] shard_mode={SHARD_MODE} total_shards={total_shards} total_bytes={total_bytes:,}", flush=True)
    print(f"[{RUN_LABEL}] use_optimized_scan={USE_OPTIMIZED_SCAN} resume_latest_incomplete_run={RESUME_LATEST_INCOMPLETE_RUN}", flush=True)
    print(
        f"[{RUN_LABEL}] resume_completed_shards={resume_completed_count}/{total_shards} "
        f"resume_completed_bytes={resume_completed_bytes:,}/{total_bytes:,}",
        flush=True,
    )
    print(f"[{RUN_LABEL}] intended_wallclock_budget={INTENDED_WALLCLOCK_BUDGET} stop_condition={STOP_CONDITION}", flush=True)

    for row in rows:
        order = int(row["ngram_order"])
        shard_index = int(row["shard_index"])
        source_path = path_lookup[(order, shard_index)]
        if shard_is_complete(run_dir, order, shard_index, source_path):
            continue
        try:
            manifest = build_one_shard(
                builder=builder,
                dictionary_sets=dictionary_sets,
                base_config=base_config,
                run_dir=run_dir,
                order=order,
                shard_index=shard_index,
                total_shards=total_shards,
                source_path=source_path,
                started=started,
                completed_before=completed_count,
                total_bytes=total_bytes,
                completed_bytes_before=completed_bytes,
                resume_completed_bytes_at_start=resume_completed_bytes,
            )
            manifest_path = shard_manifest_path(run_dir, order, shard_index, source_path)
            row["status"] = "pass"
            row["elapsed_seconds"] = manifest.get("elapsed_seconds", "")
            row["aggregate_rows"] = sum(int(item.get("aggregate_rows", 0)) for item in manifest.get("output_files", []))
            row["dictionary_kept_rows"] = sum(int(item.get("dictionary_kept_rows", 0)) for item in manifest.get("output_files", []))
            row["output_file_count"] = len(manifest.get("output_files", []))
            row["manifest_path"] = repo_rel(manifest_path)
            completed_count += 1
            completed_bytes += int(row["source_file_bytes"])
            write_progress_manifest(
                run_dir,
                rows,
                started,
                resume_completed_bytes_at_start=resume_completed_bytes,
                resume_completed_shards_at_start=resume_completed_count,
            )
        except Exception as exc:
            row["status"] = "blocked"
            row["blocked_reason"] = f"{type(exc).__name__}: {exc}"
            write_progress_manifest(
                run_dir,
                rows,
                started,
                resume_completed_bytes_at_start=resume_completed_bytes,
                resume_completed_shards_at_start=resume_completed_count,
            )
            print(f"[{RUN_LABEL}] blocked order={order} shard={shard_index} reason={row['blocked_reason']}", flush=True)
            raise

    manifest = write_progress_manifest(
        run_dir,
        rows,
        started,
        resume_completed_bytes_at_start=resume_completed_bytes,
        resume_completed_shards_at_start=resume_completed_count,
    )
    print(f"[{RUN_LABEL}] status={manifest['status']} completed_shards={manifest['completed_shards']}/{manifest['total_shards']}", flush=True)


if __name__ == "__main__":
    main()
