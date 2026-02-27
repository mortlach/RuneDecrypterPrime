from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from array import array
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parents[4]
    _SRC = _ROOT / "src"
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    if _SRC.exists() and str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

from tools.benchmarks.scoring.span_hamming_nose.bench_span_hamming_nose_suite import (
    _build_calibration,
    _write_summary_csv,
)
from tools.benchmarks.scoring.span_hamming_nose.schema import PlanRow, read_plan_csv, write_plan_csv

REPO_ROOT = Path(__file__).resolve().parents[4]


# ---------------------------------------------------------------------------
# Config block (no CLI; edit constants here)
# ---------------------------------------------------------------------------
# Option A: explicit shard run dirs (recommended for production merges).
SHARD_RUN_DIRS: list[str] = []

# Option B: auto-discover latest shard set from parent.
SHARD_PARENT_DIR = Path("output/tools/benchmarks/scoring/span_hamming_nose_suite")
SHARD_GROUP_PREFIX: str | None = None

OUTPUT_ROOT = Path("output/tools/benchmarks/scoring/span_hamming_nose_suite_merged")
RUN_DIR_OVERRIDE: str | None = None

WRITE_MERGED_SAMPLES = True
DEDUPE_BY_SAMPLE_ID = True
REQUIRE_FULL_SHARD_SET = True


@dataclass(frozen=True)
class MergeConfig:
    shard_run_dirs: list[Path]
    shard_parent_dir: Path
    shard_group_prefix: str | None
    output_root: Path
    run_dir: Path | None
    write_merged_samples: bool
    dedupe_by_sample_id: bool
    require_full_shard_set: bool = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False),
        encoding="utf-8",
    )


def _corpus_books_signature(cfg_json: dict[str, Any]) -> str | None:
    rows = cfg_json.get("resolved_books", []) or []
    if not isinstance(rows, list) or not rows:
        return None
    items: list[tuple[str, str, int]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        book_id = str(row.get("book_id", "")).strip()
        direction = str(row.get("direction", "")).strip().lower()
        try:
            n_tokens = int(row.get("n_tokens", 0))
        except Exception:
            n_tokens = 0
        if not book_id:
            continue
        items.append((book_id, direction, n_tokens))
    if not items:
        return None
    payload = json.dumps(sorted(items), separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _to_float(value: Any, default: float = float("nan")) -> float:
    try:
        if value is None:
            return float(default)
        text = str(value).strip()
        if text == "":
            return float(default)
        return float(text)
    except Exception:
        return float(default)


def _get_or_create_group_bucket(
    group_values: dict[tuple[str, int, str], dict[str, array]],
    key: tuple[str, int, str],
) -> dict[str, array]:
    bucket = group_values.get(key)
    if bucket is None:
        bucket = {
            "span": array("f"),
            "char1": array("f"),
            "char2": array("f"),
            "char3": array("f"),
            "char4": array("f"),
        }
        group_values[key] = bucket
    return bucket


def _resolve_cfg() -> MergeConfig:
    explicit = [Path(p).expanduser().resolve() for p in SHARD_RUN_DIRS if str(p).strip()]
    parent = Path(SHARD_PARENT_DIR).expanduser()
    if not parent.is_absolute():
        parent = (REPO_ROOT / parent).resolve()
    else:
        parent = parent.resolve()

    out_root = Path(OUTPUT_ROOT).expanduser()
    if not out_root.is_absolute():
        out_root = (REPO_ROOT / out_root).resolve()
    else:
        out_root = out_root.resolve()

    run_dir = None
    if RUN_DIR_OVERRIDE:
        run_path = Path(RUN_DIR_OVERRIDE).expanduser()
        if not run_path.is_absolute():
            run_path = (REPO_ROOT / run_path).resolve()
        else:
            run_path = run_path.resolve()
        run_dir = run_path

    return MergeConfig(
        shard_run_dirs=explicit,
        shard_parent_dir=parent,
        shard_group_prefix=(str(SHARD_GROUP_PREFIX).strip() if SHARD_GROUP_PREFIX else None),
        output_root=out_root,
        run_dir=run_dir,
        write_merged_samples=bool(WRITE_MERGED_SAMPLES),
        dedupe_by_sample_id=bool(DEDUPE_BY_SAMPLE_ID),
        require_full_shard_set=bool(REQUIRE_FULL_SHARD_SET),
    )


def _discover_latest_shard_dirs(parent: Path, group_prefix: str | None) -> list[Path]:
    if not parent.exists() or not parent.is_dir():
        raise FileNotFoundError(f"shard parent dir not found: {parent}")
    pat = re.compile(r"^(?P<base>.+)__shard(?P<idx>\d+)of(?P<count>\d+)$")
    groups_by_base: dict[tuple[str, int], list[tuple[int, Path]]] = {}
    groups_by_sig: dict[tuple[int, str], dict[int, tuple[float, Path]]] = {}
    for child in parent.iterdir():
        if not child.is_dir():
            continue
        m = pat.match(child.name)
        if not m:
            continue
        base = m.group("base")
        if group_prefix and not base.startswith(group_prefix):
            continue
        idx = int(m.group("idx"))
        count = int(m.group("count"))
        child_resolved = child.resolve()
        groups_by_base.setdefault((base, count), []).append((idx, child_resolved))

        # Prefer signature-based grouping so shards launched at different times
        # (different timestamp prefixes) can still be paired deterministically.
        cfg_path = child_resolved / "run_config.json"
        if not cfg_path.exists():
            continue
        try:
            cfg_json = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        sig_key = json.dumps(_signature(cfg_json), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        gk = (count, sig_key)
        slot = groups_by_sig.setdefault(gk, {})
        mtime = child_resolved.stat().st_mtime
        prev = slot.get(idx)
        if prev is None or mtime > prev[0]:
            slot[idx] = (mtime, child_resolved)

    if not groups_by_base and not groups_by_sig:
        raise FileNotFoundError("No shard run dirs found for merge")

    # 1) Best path: pick latest complete signature group.
    complete_sig_groups: list[tuple[float, list[Path]]] = []
    for (count, _sig), slot in groups_by_sig.items():
        expected = set(range(int(count)))
        if not expected.issubset(set(slot.keys())):
            continue
        members = [slot[i][1] for i in sorted(expected)]
        newest = max(p.stat().st_mtime for p in members)
        complete_sig_groups.append((newest, members))
    if complete_sig_groups:
        complete_sig_groups.sort(key=lambda item: item[0])
        return complete_sig_groups[-1][1]

    # 2) Backward-compatible fallback: latest base-group (may be partial).
    chosen_key = max(
        groups_by_base.keys(),
        key=lambda k: max(p.stat().st_mtime for _, p in groups_by_base[k]),
    )
    members = sorted(groups_by_base[chosen_key], key=lambda x: x[0])
    return [p for _, p in members]


def _resolve_source_dirs(cfg: MergeConfig) -> list[Path]:
    if cfg.shard_run_dirs:
        dirs = [p for p in cfg.shard_run_dirs if p.exists() and p.is_dir()]
        if len(dirs) != len(cfg.shard_run_dirs):
            missing = [str(p) for p in cfg.shard_run_dirs if not p.exists()]
            raise FileNotFoundError(f"Missing shard dirs: {missing}")
        return dirs
    return _discover_latest_shard_dirs(cfg.shard_parent_dir, cfg.shard_group_prefix)


def _load_run_config(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "run_config.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing run_config.json in {run_dir}")
    return json.loads(path.read_text(encoding="utf-8"))


def _signature(cfg_json: dict[str, Any]) -> dict[str, Any]:
    sig = {
        "suite_version": cfg_json.get("suite_version"),
        "token_key": cfg_json.get("token_key"),
        "global_seed": cfg_json.get("global_seed"),
        "directions": cfg_json.get("directions"),
        "length_buckets": cfg_json.get("length_buckets"),
        "min_stride": cfg_json.get("min_stride"),
        "stride_factor": cfg_json.get("stride_factor"),
        "max_windows_per_book_by_l": cfg_json.get("max_windows_per_book_by_l"),
        "max_windows_fallback": cfg_json.get("max_windows_fallback"),
        "generators": cfg_json.get("generators"),
        "corrupt_pcts": cfg_json.get("corrupt_pcts"),
        "enable_char_baselines": cfg_json.get("enable_char_baselines"),
        "span_config": cfg_json.get("span_config"),
        "plan_rows_all": cfg_json.get("plan_rows_all"),
        "corpus_books_sig": _corpus_books_signature(cfg_json),
    }
    return sig


def _validate_compatible(run_cfgs: list[dict[str, Any]], *, require_full_shard_set: bool) -> None:
    base_sig = _signature(run_cfgs[0])
    for idx, cfg in enumerate(run_cfgs[1:], start=1):
        sig = _signature(cfg)
        if sig != base_sig:
            raise ValueError(f"Incompatible run_config signature at shard index {idx}")

    # Char baselines may be disabled in some suite runs; merger must still work
    # for span-only outputs (char columns become NaN/empty in summaries).

    shard_count = run_cfgs[0].get("shard_count")
    if shard_count is not None:
        target_count = int(shard_count)
        seen = sorted(
            {
                int(cfg.get("shard_index"))
                for cfg in run_cfgs
                if cfg.get("shard_index") is not None
            }
        )
        expected = list(range(target_count))
        if require_full_shard_set:
            if len(run_cfgs) != target_count or seen != expected:
                raise ValueError(
                    f"Shard index set is incomplete/inconsistent. "
                    f"seen={seen}, expected={expected}, provided_cfgs={len(run_cfgs)}"
                )
        else:
            if seen != expected[: len(seen)]:
                raise ValueError(f"Shard index set is inconsistent. seen={seen}, expected_prefix={expected}")


def _merge_plan(shard_dirs: list[Path], out_path: Path) -> list[PlanRow]:
    by_row_id: dict[str, PlanRow] = {}
    for run_dir in shard_dirs:
        plan_rows = read_plan_csv(run_dir / "plan.csv")
        for row in plan_rows:
            by_row_id.setdefault(row.row_id, row)
    merged = sorted(by_row_id.values(), key=lambda r: (r.direction, r.length_bucket, r.book_id, r.start))
    reindexed: list[PlanRow] = []
    for idx, row in enumerate(merged):
        reindexed.append(
            PlanRow(
                row_idx=idx,
                row_id=row.row_id,
                direction=row.direction,
                length_bucket=row.length_bucket,
                book_id=row.book_id,
                book_path=row.book_path,
                start=row.start,
                text_length=row.text_length,
                stride=row.stride,
            )
        )
    write_plan_csv(out_path, reindexed)
    return reindexed


def _merge_completed_rows(shard_dirs: list[Path], out_path: Path) -> int:
    header = ["row_idx", "row_id", "direction", "length_bucket", "book_id", "start", "completed_at_utc"]
    seen: set[str] = set()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for run_dir in shard_dirs:
            path = run_dir / "completed_rows.csv"
            if not path.exists():
                continue
            with path.open("r", encoding="utf-8", newline="") as src:
                reader = csv.DictReader(src)
                for row in reader:
                    row_id = str(row.get("row_id", "")).strip()
                    if not row_id or row_id in seen:
                        continue
                    seen.add(row_id)
                    writer.writerow({k: str(row.get(k, "")) for k in header})
    return len(seen)


def _rewrite_completed_rows_to_merged_plan(
    *,
    completed_rows_path: Path,
    merged_plan: list[PlanRow],
) -> None:
    if not completed_rows_path.exists():
        return
    by_row_id = {row.row_id: row for row in merged_plan}
    header = ["row_idx", "row_id", "direction", "length_bucket", "book_id", "start", "completed_at_utc"]
    rows_out: list[dict[str, str]] = []
    with completed_rows_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_id = str(row.get("row_id", "")).strip()
            if not row_id:
                continue
            plan = by_row_id.get(row_id)
            if plan is None:
                continue
            rows_out.append(
                {
                    "row_idx": str(int(plan.row_idx)),
                    "row_id": row_id,
                    "direction": str(plan.direction),
                    "length_bucket": str(int(plan.length_bucket)),
                    "book_id": str(plan.book_id),
                    "start": str(int(plan.start)),
                    "completed_at_utc": str(row.get("completed_at_utc", "")),
                }
            )
    with completed_rows_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows_out:
            writer.writerow(row)


def _merge_book_manifest(run_cfgs: list[dict[str, Any],], out_path: Path) -> int:
    header = ["book_id", "path", "direction", "n_tokens", "in_shard"]
    by_id: dict[str, dict[str, str]] = {}
    in_shard_ids: set[str] = set()
    for cfg in run_cfgs:
        for row in cfg.get("resolved_books", []) or []:
            book_id = str(row.get("book_id", "")).strip()
            if not book_id:
                continue
            by_id.setdefault(
                book_id,
                {
                    "book_id": book_id,
                    "path": str(row.get("path", "")),
                    "direction": str(row.get("direction", "")),
                    "n_tokens": str(int(row.get("n_tokens", 0))),
                    "in_shard": "0",
                },
            )
        for row in cfg.get("shard_books", []) or []:
            book_id = str(row.get("book_id", "")).strip()
            if book_id:
                in_shard_ids.add(book_id)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for book_id in sorted(by_id.keys()):
            row = dict(by_id[book_id])
            row["in_shard"] = "1" if book_id in in_shard_ids else "0"
            writer.writerow(row)
    return len(by_id)


def _merge_samples(
    *,
    shard_dirs: list[Path],
    out_samples_path: Path | None,
    dedupe_by_sample_id: bool,
) -> tuple[dict[tuple[str, int, str], dict[str, array]], int]:
    required_cols = {
        "sample_id",
        "row_id",
        "direction",
        "length_bucket",
        "generator",
        "span_raw",
        "char1_score",
        "char2_score",
        "char3_score",
        "char4_score",
    }
    merged_header: list[str] = []
    for run_dir in shard_dirs:
        samples_path = run_dir / "samples.csv"
        if not samples_path.exists():
            raise FileNotFoundError(f"Missing samples.csv in {run_dir}")
        with samples_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = list(reader.fieldnames or [])
            missing = sorted(required_cols - set(fields))
            if missing:
                raise ValueError(f"samples.csv missing required columns in {run_dir}: {missing}")
            for col in fields:
                if col not in merged_header:
                    merged_header.append(col)

    seen_sample_ids: set[str] = set()
    merged_rows = 0
    group_values: dict[tuple[str, int, str], dict[str, array]] = {}

    out_handle = None
    out_writer = None
    if out_samples_path is not None:
        out_samples_path.parent.mkdir(parents=True, exist_ok=True)
        out_handle = out_samples_path.open("w", encoding="utf-8", newline="")
        out_writer = csv.DictWriter(out_handle, fieldnames=merged_header)
        out_writer.writeheader()

    try:
        for run_dir in shard_dirs:
            samples_path = run_dir / "samples.csv"
            with samples_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    sample_id = str(row.get("sample_id", "")).strip()
                    if dedupe_by_sample_id and sample_id:
                        if sample_id in seen_sample_ids:
                            continue
                        seen_sample_ids.add(sample_id)

                    direction = str(row.get("direction", "")).strip().lower()
                    length_bucket = int(row.get("length_bucket", 0))
                    generator = str(row.get("generator", "")).strip().upper()
                    gk = (direction, length_bucket, generator)
                    vals = _get_or_create_group_bucket(group_values, gk)
                    vals["span"].append(_to_float(row.get("span_raw")))
                    vals["char1"].append(_to_float(row.get("char1_score")))
                    vals["char2"].append(_to_float(row.get("char2_score")))
                    vals["char3"].append(_to_float(row.get("char3_score")))
                    vals["char4"].append(_to_float(row.get("char4_score")))
                    merged_rows += 1

                    if out_writer is not None:
                        out_writer.writerow({k: str(row.get(k, "")) for k in merged_header})
    finally:
        if out_handle is not None:
            out_handle.close()

    return group_values, merged_rows


def run_merge(cfg: MergeConfig) -> Path:
    shard_dirs = _resolve_source_dirs(cfg)
    run_cfgs = [_load_run_config(d) for d in shard_dirs]
    _validate_compatible(run_cfgs, require_full_shard_set=cfg.require_full_shard_set)

    if cfg.run_dir is not None:
        out_dir = cfg.run_dir
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = cfg.output_root / f"{_utc_now()}__span_hamming_nose_suite_merged"
        out_dir.mkdir(parents=True, exist_ok=True)

    merged_plan = _merge_plan(shard_dirs, out_dir / "plan.csv")
    completed_count = _merge_completed_rows(shard_dirs, out_dir / "completed_rows.csv")
    _rewrite_completed_rows_to_merged_plan(
        completed_rows_path=out_dir / "completed_rows.csv",
        merged_plan=merged_plan,
    )
    book_count = _merge_book_manifest(run_cfgs, out_dir / "book_manifest.csv")

    merged_samples_path = (out_dir / "samples.csv") if cfg.write_merged_samples else None
    group_values, merged_sample_rows = _merge_samples(
        shard_dirs=shard_dirs,
        out_samples_path=merged_samples_path,
        dedupe_by_sample_id=cfg.dedupe_by_sample_id,
    )

    _write_summary_csv(out_dir / "summary.csv", group_values)
    _write_json(out_dir / "calibration.json", _build_calibration(group_values))

    ref = run_cfgs[0]
    merged_cfg = {
        "merge_type": "span_hamming_nose_shards",
        "created_at_utc": _utc_now(),
        "source_shards": [str(p) for p in shard_dirs],
        "source_shard_count": int(len(shard_dirs)),
        "dedupe_by_sample_id": bool(cfg.dedupe_by_sample_id),
        "write_merged_samples": bool(cfg.write_merged_samples),
        "merged_plan_rows": int(len(merged_plan)),
        "merged_completed_rows": int(completed_count),
        "merged_samples_rows": int(merged_sample_rows),
        "merged_book_count": int(book_count),
        "suite_version": ref.get("suite_version"),
        "token_key": ref.get("token_key"),
        "global_seed": ref.get("global_seed"),
        "directions": ref.get("directions"),
        "length_buckets": ref.get("length_buckets"),
        "generators": ref.get("generators"),
        "span_config": ref.get("span_config"),
        "corpus_list_hash": ref.get("corpus_list_hash"),
        "shard_count_expected": ref.get("shard_count"),
        "shard_strategy": ref.get("shard_strategy"),
    }
    _write_json(out_dir / "run_config.json", merged_cfg)

    return out_dir


def main() -> int:
    cfg = _resolve_cfg()
    run_dir = run_merge(cfg)
    print(f"[span_hamming_nose_merge] run_dir={run_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
