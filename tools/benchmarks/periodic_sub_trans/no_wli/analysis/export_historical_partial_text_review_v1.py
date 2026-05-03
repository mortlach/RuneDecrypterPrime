from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


RUN_LABEL = "historical_partial_text_review_v1"
NO_WLI_ROOT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_partial_text_review_v1"
)
PACK_DIR_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02"
)
PACK_ZIP_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02.zip"
)

SCORER_REVIEW_PACK_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_scorer_failure_inventory_stage1_stage2_stage2b_review_pack_2026-05-02"
)

PARTIAL_TEXT_KEYS = {
    "plaintext_idx",
    "final_plaintext_idx",
    "init_plaintext_idx",
    "final_best_plaintext_idx",
    "best_plaintext_idx",
    "candidate_plaintext_idx",
}
TRUTH_TARGET_KEYS = {"target_plaintext_idx"}
SOURCE_SUFFIXES = (".json", ".jsonl")
PLAINTEXT_MARKERS = tuple(
    marker.encode("ascii")
    for marker in sorted(PARTIAL_TEXT_KEYS | TRUTH_TARGET_KEYS)
)
PROGRESS_EVERY_FILES = 250


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


REPO_ROOT = _find_repo_root()
NO_WLI_ROOT = REPO_ROOT / NO_WLI_ROOT_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL
PACK_DIR = REPO_ROOT / PACK_DIR_REL
PACK_ZIP = REPO_ROOT / PACK_ZIP_REL
SCORER_REVIEW_PACK = REPO_ROOT / SCORER_REVIEW_PACK_REL


OCCURRENCE_FIELDS = (
    "partial_text_hash",
    "token_count",
    "token_sequence_text",
    "data_file",
    "bundle_path",
    "artifact_path",
    "field_path",
    "field_name",
    "material_kind",
    "record_index",
    "fixture_seed",
    "search_seed",
    "text_id",
    "period",
    "columns",
    "best_stage",
    "candidate_hash",
    "source",
    "source_rank",
    "lane",
    "selection_bucket",
    "score",
    "match_ratio",
    "best_match_ratio",
    "stage3_match_ratio",
    "material_source",
)

UNIQUE_FIELDS = (
    "partial_text_hash",
    "token_count",
    "token_sequence_text",
    "occurrence_count",
    "candidate_hash_count",
    "bundle_count",
    "fixture_seed_count",
    "search_seed_count",
    "first_seen_data_file",
    "best_score",
    "best_match_ratio",
    "max_recorded_match_ratio",
    "example_candidate_hashes",
    "example_sources",
    "example_bundles",
)

INVENTORY_FIELDS = (
    "path",
    "file_type",
    "bytes",
    "loaded",
    "top_level_type",
    "partial_text_occurrences",
    "truth_target_occurrences",
    "error",
)


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def _finite_or_blank(value: Any) -> float | str:
    out = _safe_float(value)
    return float(out) if math.isfinite(out) else ""


def _safe_int_text(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return ""


def is_rune_token_sequence(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for item in value:
        if isinstance(item, bool):
            return False
        try:
            token = int(item)
        except (TypeError, ValueError):
            return False
        if token < 0 or token > 28:
            return False
    return True


def normalise_tokens(value: Sequence[Any]) -> list[int]:
    return [int(item) for item in value]


def token_sequence_text(tokens: Sequence[int]) -> str:
    return " ".join(str(int(token)) for token in tokens)


def partial_text_hash(tokens: Sequence[int]) -> str:
    payload = " ".join(str(int(token)) for token in tokens).encode("ascii")
    return hashlib.sha256(payload).hexdigest()[:24]


def _bundle_path_for(path: Path) -> str:
    try:
        rel = path.resolve().relative_to(NO_WLI_ROOT.resolve())
    except ValueError:
        return ""
    parts = rel.parts
    if not parts:
        return ""
    first = parts[0]
    if "__bench_solve_pipeline_no_wli__" in first:
        return (NO_WLI_ROOT / first).as_posix().replace("\\", "/")
    return ""


def _display_bundle_path(path: Path) -> str:
    bundle = _bundle_path_for(path)
    if not bundle:
        return ""
    return _repo_rel(Path(bundle))


def _pick(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return ""


def _context_value(
    *,
    key: str,
    parent: Mapping[str, Any],
    root: Mapping[str, Any],
) -> Any:
    if key == "fixture_seed":
        return _pick(parent.get("fixture_seed"), parent.get("key_seed"), root.get("fixture_seed"), root.get("key_seed"))
    if key == "score":
        return _pick(
            parent.get("final_score"),
            parent.get("score"),
            parent.get("init_score"),
            root.get("final_score"),
            root.get("best_score"),
            root.get("score"),
        )
    if key == "match_ratio":
        return _pick(
            parent.get("final_match"),
            parent.get("match_ratio"),
            parent.get("truth_match_ratio"),
            parent.get("init_match"),
            root.get("final_match"),
            root.get("best_match_ratio"),
            root.get("stage3_match_ratio"),
        )
    return _pick(parent.get(key), root.get(key))


def _iter_json_records(path: Path) -> Iterable[tuple[Any, int | str, str]]:
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                yield json.loads(line), idx, "jsonl"
        return
    yield json.loads(path.read_text(encoding="utf-8")), "", "json"


def _has_plaintext_marker(path: Path) -> bool:
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                return False
            if any(marker in chunk for marker in PLAINTEXT_MARKERS):
                return True


def _progress_line(*, completed: int, total: int, started: float, partial_count: int, target_count: int) -> str:
    elapsed = time.perf_counter() - started
    if completed and total:
        rate = elapsed / completed
        remaining = max(total - completed, 0) * rate
    else:
        remaining = 0.0
    return (
        "[historical_partial_text_review_v1] "
        f"scanned={completed}/{total} "
        f"partial_occurrences={partial_count} "
        f"truth_targets={target_count} "
        f"elapsed={elapsed:.1f}s "
        f"eta={remaining:.1f}s"
    )


def _walk_plaintext_fields(
    obj: Any,
    *,
    path_parts: list[str],
    parent: Mapping[str, Any],
    root: Mapping[str, Any],
) -> Iterable[tuple[str, str, list[int], Mapping[str, Any]]]:
    if isinstance(obj, Mapping):
        current_parent = obj
        for key, value in obj.items():
            next_path = path_parts + [str(key)]
            if key in PARTIAL_TEXT_KEYS and is_rune_token_sequence(value):
                yield ".".join(next_path), key, normalise_tokens(value), current_parent
            elif key in TRUTH_TARGET_KEYS and is_rune_token_sequence(value):
                yield ".".join(next_path), key, normalise_tokens(value), current_parent
            else:
                yield from _walk_plaintext_fields(
                    value,
                    path_parts=next_path,
                    parent=current_parent,
                    root=root,
                )
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            yield from _walk_plaintext_fields(
                item,
                path_parts=path_parts + [f"[{idx}]"],
                parent=parent,
                root=root,
            )


def _source_files() -> list[Path]:
    paths = [
        path
        for suffix in SOURCE_SUFFIXES
        for path in NO_WLI_ROOT.rglob(f"*{suffix}")
        if path.is_file()
    ]
    return sorted(set(paths))


def collect_occurrences() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    partial_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    inventory_rows: list[dict[str, Any]] = []
    source_files = _source_files()
    started = time.perf_counter()
    total_files = len(source_files)
    print(
        "[historical_partial_text_review_v1] "
        f"starting scan source_files={total_files} root={NO_WLI_ROOT_REL}",
        flush=True,
    )
    for file_index, file_path in enumerate(source_files, start=1):
        loaded = 0
        error = ""
        top_type = ""
        partial_count = 0
        target_count = 0
        try:
            if not _has_plaintext_marker(file_path):
                records = []
                top_type = "skipped_no_plaintext_marker"
            else:
                records = list(_iter_json_records(file_path))
                loaded = 1
        except Exception as exc:
            records = []
            error = type(exc).__name__ + ": " + str(exc)
        for record, record_idx, material_source in records:
            top_type = type(record).__name__
            root = record if isinstance(record, Mapping) else {}
            for field_path, field_name, tokens, parent in _walk_plaintext_fields(
                record,
                path_parts=["root"],
                parent=root,
                root=root,
            ):
                row = {
                    "partial_text_hash": partial_text_hash(tokens),
                    "token_count": len(tokens),
                    "token_sequence_text": token_sequence_text(tokens),
                    "data_file": _repo_rel(file_path),
                    "bundle_path": _display_bundle_path(file_path),
                    "artifact_path": _repo_rel(file_path) if "final_instances" in file_path.parts or file_path.name == "best_instance.json" else "",
                    "field_path": field_path,
                    "field_name": field_name,
                    "material_kind": "truth_target" if field_name in TRUTH_TARGET_KEYS else "candidate_partial",
                    "record_index": record_idx,
                    "fixture_seed": _safe_int_text(_context_value(key="fixture_seed", parent=parent, root=root)),
                    "search_seed": _safe_int_text(_context_value(key="search_seed", parent=parent, root=root)),
                    "text_id": _safe_int_text(_context_value(key="text_id", parent=parent, root=root)),
                    "period": _safe_int_text(_context_value(key="period", parent=parent, root=root)),
                    "columns": _safe_int_text(_context_value(key="columns", parent=parent, root=root)),
                    "best_stage": str(_context_value(key="best_stage", parent=parent, root=root) or ""),
                    "candidate_hash": str(_context_value(key="candidate_hash", parent=parent, root=root) or ""),
                    "source": str(_context_value(key="source", parent=parent, root=root) or ""),
                    "source_rank": _safe_int_text(_context_value(key="source_rank", parent=parent, root=root)),
                    "lane": str(_context_value(key="lane", parent=parent, root=root) or ""),
                    "selection_bucket": str(_context_value(key="selection_bucket", parent=parent, root=root) or ""),
                    "score": _finite_or_blank(_context_value(key="score", parent=parent, root=root)),
                    "match_ratio": _finite_or_blank(_context_value(key="match_ratio", parent=parent, root=root)),
                    "best_match_ratio": _finite_or_blank(_context_value(key="best_match_ratio", parent=parent, root=root)),
                    "stage3_match_ratio": _finite_or_blank(_context_value(key="stage3_match_ratio", parent=parent, root=root)),
                    "material_source": material_source,
                }
                if field_name in TRUTH_TARGET_KEYS:
                    target_rows.append({field: row.get(field, "") for field in OCCURRENCE_FIELDS})
                    target_count += 1
                else:
                    partial_rows.append({field: row.get(field, "") for field in OCCURRENCE_FIELDS})
                    partial_count += 1
        inventory_rows.append(
            {
                "path": _repo_rel(file_path),
                "file_type": file_path.suffix.lower().lstrip("."),
                "bytes": file_path.stat().st_size,
                "loaded": loaded,
                "top_level_type": top_type,
                "partial_text_occurrences": partial_count,
                "truth_target_occurrences": target_count,
                "error": error,
            }
        )
        if file_index == 1 or file_index % PROGRESS_EVERY_FILES == 0 or file_index == total_files:
            print(
                _progress_line(
                    completed=file_index,
                    total=total_files,
                    started=started,
                    partial_count=len(partial_rows),
                    target_count=len(target_rows),
                ),
                flush=True,
            )
    return partial_rows, target_rows, inventory_rows


def _count_unique(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return len({str(row.get(key, "") or "") for row in rows if str(row.get(key, "") or "")})


def _best_float(rows: Sequence[Mapping[str, Any]], key: str, *, high: bool = True) -> float | str:
    vals = [_safe_float(row.get(key)) for row in rows]
    vals = [val for val in vals if math.isfinite(val)]
    if not vals:
        return ""
    return float(max(vals) if high else min(vals))


def build_unique_rows(partial_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in partial_rows:
        groups[str(row.get("partial_text_hash", "") or "")].append(row)
    unique_rows: list[dict[str, Any]] = []
    for text_hash, rows in groups.items():
        first = rows[0]
        candidate_hashes = sorted({str(row.get("candidate_hash", "") or "") for row in rows if row.get("candidate_hash")})
        sources = sorted({str(row.get("source", "") or "") for row in rows if row.get("source")})
        bundles = sorted({str(row.get("bundle_path", "") or "") for row in rows if row.get("bundle_path")})
        unique_rows.append(
            {
                "partial_text_hash": text_hash,
                "token_count": first.get("token_count", ""),
                "token_sequence_text": first.get("token_sequence_text", ""),
                "occurrence_count": len(rows),
                "candidate_hash_count": len(candidate_hashes),
                "bundle_count": len(bundles),
                "fixture_seed_count": _count_unique(rows, "fixture_seed"),
                "search_seed_count": _count_unique(rows, "search_seed"),
                "first_seen_data_file": first.get("data_file", ""),
                "best_score": _best_float(rows, "score"),
                "best_match_ratio": _best_float(rows, "match_ratio"),
                "max_recorded_match_ratio": _best_float(rows, "match_ratio"),
                "example_candidate_hashes": ";".join(candidate_hashes[:8]),
                "example_sources": ";".join(sources[:8]),
                "example_bundles": ";".join(bundles[:5]),
            }
        )
    unique_rows.sort(
        key=lambda row: (
            int(row.get("occurrence_count", 0) or 0),
            _safe_float(row.get("best_match_ratio")),
            _safe_float(row.get("best_score")),
            int(row.get("token_count", 0) or 0),
        ),
        reverse=True,
    )
    return [{field: row.get(field, "") for field in UNIQUE_FIELDS} for row in unique_rows]


def build_summary(
    *,
    partial_rows: Sequence[Mapping[str, Any]],
    target_rows: Sequence[Mapping[str, Any]],
    unique_rows: Sequence[Mapping[str, Any]],
    inventory_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_field = Counter(str(row.get("field_name", "") or "") for row in partial_rows)
    by_source = Counter(str(row.get("source", "") or "none") for row in partial_rows)
    by_length = Counter(str(row.get("token_count", "") or "unknown") for row in partial_rows)
    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "no_wli_root": NO_WLI_ROOT_REL,
        "source_file_count": len(inventory_rows),
        "source_files_loaded_count": sum(int(row.get("loaded", 0) or 0) for row in inventory_rows),
        "source_files_with_partial_text_count": sum(int(row.get("partial_text_occurrences", 0) or 0) > 0 for row in inventory_rows),
        "partial_text_occurrence_count": len(partial_rows),
        "unique_partial_text_count": len(unique_rows),
        "truth_target_occurrence_count": len(target_rows),
        "unique_truth_target_count": _count_unique(target_rows, "partial_text_hash"),
        "candidate_hash_count": _count_unique(partial_rows, "candidate_hash"),
        "bundle_count": _count_unique(partial_rows, "bundle_path"),
        "fixture_seed_count": _count_unique(partial_rows, "fixture_seed"),
        "search_seed_count": _count_unique(partial_rows, "search_seed"),
        "token_length_counts": dict(sorted(by_length.items(), key=lambda item: item[0])),
        "field_name_counts": dict(sorted(by_field.items())),
        "source_counts": dict(sorted(by_source.items())),
        "top_repeated_partial_texts": [dict(row) for row in list(unique_rows)[:20]],
        "representation_rule": "Canonical text is numeric rune/base-29 token sequence, values 0..28. No English rendering is emitted.",
        "truth_target_rule": "target_plaintext_idx rows are exported separately and excluded from candidate partial-text clusters.",
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=True, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_readout(summary: Mapping[str, Any]) -> str:
    lines = [
        "# no-WLI Historical Partial Text Review v1",
        "",
        "## Representation Rule",
        "",
        "- Canonical partial text is numeric rune/base-29 token sequence only.",
        "- Token values must be `0..28`.",
        "- No English rendering, transliteration, digraph rendering, or word-like text is emitted.",
        "- `target_plaintext_idx` truth material is exported separately and excluded from candidate partial-text clusters.",
        "",
        "## Summary",
        "",
        f"- source files scanned: `{summary['source_file_count']}`",
        f"- source files loaded: `{summary['source_files_loaded_count']}`",
        f"- source files with partial text: `{summary['source_files_with_partial_text_count']}`",
        f"- partial-text occurrences: `{summary['partial_text_occurrence_count']}`",
        f"- unique partial texts: `{summary['unique_partial_text_count']}`",
        f"- candidate hashes represented: `{summary['candidate_hash_count']}`",
        f"- bundles represented: `{summary['bundle_count']}`",
        f"- fixture seeds represented: `{summary['fixture_seed_count']}`",
        f"- search seeds represented: `{summary['search_seed_count']}`",
        f"- truth target occurrences separated: `{summary['truth_target_occurrence_count']}`",
        f"- unique truth targets separated: `{summary['unique_truth_target_count']}`",
        "",
        "## Field Counts",
        "",
    ]
    for key, value in dict(summary.get("field_name_counts", {})).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Source Counts", ""])
    for key, value in list(dict(summary.get("source_counts", {})).items())[:20]:
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Review Files",
            "",
            "- `historical_output_inventory.csv/jsonl` lists scanned source files and missing/error status.",
            "- `partial_text_occurrences.csv/jsonl` lists every candidate partial-text occurrence found.",
            "- `unique_partial_text_rows.csv/jsonl` clusters candidate partial texts by numeric-token hash.",
            "- `truth_target_occurrences.csv/jsonl` keeps truth targets separate from candidate partial texts.",
            "- `historical_partial_text_summary.json` contains aggregate counts and top repeated clusters.",
            "",
            "## Caveats",
            "",
            "- This is a repository-output inventory, not a new benchmark run.",
            "- Occurrence counts are not independent evidence counts.",
            "- Match/truth fields are carried through only when already present in source material.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs() -> dict[str, Any]:
    started = time.perf_counter()
    partial_rows, target_rows, inventory_rows = collect_occurrences()
    unique_rows = build_unique_rows(partial_rows)
    summary = build_summary(
        partial_rows=partial_rows,
        target_rows=target_rows,
        unique_rows=unique_rows,
        inventory_rows=inventory_rows,
    )
    summary["elapsed_seconds"] = float(time.perf_counter() - started)
    summary["output_dir"] = _repo_rel(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(OUTPUT_DIR / "historical_output_inventory.csv", inventory_rows, INVENTORY_FIELDS)
    _write_jsonl(OUTPUT_DIR / "historical_output_inventory.jsonl", inventory_rows)
    _write_csv(OUTPUT_DIR / "partial_text_occurrences.csv", partial_rows, OCCURRENCE_FIELDS)
    _write_jsonl(OUTPUT_DIR / "partial_text_occurrences.jsonl", partial_rows)
    _write_csv(OUTPUT_DIR / "unique_partial_text_rows.csv", unique_rows, UNIQUE_FIELDS)
    _write_jsonl(OUTPUT_DIR / "unique_partial_text_rows.jsonl", unique_rows)
    _write_csv(OUTPUT_DIR / "truth_target_occurrences.csv", target_rows, OCCURRENCE_FIELDS)
    _write_jsonl(OUTPUT_DIR / "truth_target_occurrences.jsonl", target_rows)
    _write_json(OUTPUT_DIR / "historical_partial_text_summary.json", summary)
    (OUTPUT_DIR / "historical_partial_text_readout.md").write_text(
        build_readout(summary),
        encoding="utf-8",
    )
    print(
        "[historical_partial_text_review_v1] "
        f"source_files={summary['source_file_count']} "
        f"partial_occurrences={summary['partial_text_occurrence_count']} "
        f"unique_partial_texts={summary['unique_partial_text_count']} "
        f"output_dir={summary['output_dir']}",
        flush=True,
    )
    return summary


def _copy_tree_contents(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def build_review_pack() -> dict[str, Any]:
    summary = write_outputs()
    if PACK_DIR.exists():
        shutil.rmtree(PACK_DIR)
    PACK_DIR.mkdir(parents=True, exist_ok=True)

    partial_dst = PACK_DIR / "historical_partial_texts"
    _copy_tree_contents(OUTPUT_DIR, partial_dst)

    scorer_dst = PACK_DIR / "current_scorer_failure_review"
    _copy_tree_contents(SCORER_REVIEW_PACK, scorer_dst)

    source_dst = PACK_DIR / "source_scripts"
    source_dst.mkdir(parents=True, exist_ok=True)
    source_paths = [
        Path("tools/benchmarks/periodic_sub_trans/no_wli/analysis/export_historical_partial_text_review_v1.py"),
        Path("tools/benchmarks/periodic_sub_trans/no_wli/analysis/export_scorer_component_inventory_v1.py"),
        Path("tools/benchmarks/periodic_sub_trans/no_wli/analysis/analyse_current_scorer_failure_v1.py"),
        Path("tools/benchmarks/periodic_sub_trans/no_wli/analysis/enrich_current_scorer_failure_sidecars_v1.py"),
        Path("tools/benchmarks/periodic_sub_trans/no_wli/analysis/probe_repetition_window_consistency_v1.py"),
        Path("tools/benchmarks/periodic_sub_trans/no_wli/analysis/analyse_repetition_failure_groups_v1.py"),
    ]
    for rel in source_paths:
        src = REPO_ROOT / rel
        if src.exists():
            shutil.copy2(src, source_dst / src.name)

    tests_dst = PACK_DIR / "tests"
    tests_dst.mkdir(parents=True, exist_ok=True)
    test_paths = [
        Path("tests/tools/test_no_wli_historical_partial_text_review_v1.py"),
        Path("tests/tools/test_no_wli_scorer_component_inventory_v1.py"),
        Path("tests/tools/test_no_wli_current_scorer_failure_v1.py"),
        Path("tests/tools/test_no_wli_current_scorer_failure_sidecars_v1.py"),
        Path("tests/tools/test_no_wli_repetition_window_consistency_probe_v1.py"),
        Path("tests/tools/test_no_wli_repetition_failure_groups_v1.py"),
    ]
    for rel in test_paths:
        src = REPO_ROOT / rel
        if src.exists():
            shutil.copy2(src, tests_dst / src.name)

    readme = [
        "# no-WLI Historical Partial Text and Scorer Review Pack",
        "",
        "Date: 2026-05-02",
        "",
        "## Purpose",
        "",
        "This pack widens review beyond the current scorer truth-gap slice. It inventories historical no-WLI output material and clusters unique candidate partial texts by numeric rune/base-29 token sequence.",
        "",
        "## Mandatory Representation Rule",
        "",
        "- Candidate partial texts are represented only as numeric rune/base-29 token sequences.",
        "- Token values are `0..28`.",
        "- No English rendering is included because English chars are not reversible to runes due to digraphs/trigraphs.",
        "- `target_plaintext_idx` truth material is separated from candidate partial-text clusters.",
        "",
        "## Open First",
        "",
        "1. `historical_partial_texts/historical_partial_text_readout.md`",
        "2. `historical_partial_texts/historical_partial_text_summary.json`",
        "3. `historical_partial_texts/unique_partial_text_rows.csv`",
        "4. `historical_partial_texts/partial_text_occurrences.csv`",
        "5. `current_scorer_failure_review/README.md`",
        "",
        "## Historical Partial Text Summary",
        "",
        f"- source files scanned: `{summary['source_file_count']}`",
        f"- source files with partial text: `{summary['source_files_with_partial_text_count']}`",
        f"- partial-text occurrences: `{summary['partial_text_occurrence_count']}`",
        f"- unique partial texts: `{summary['unique_partial_text_count']}`",
        f"- candidate hashes represented: `{summary['candidate_hash_count']}`",
        f"- bundles represented: `{summary['bundle_count']}`",
        f"- fixture seeds represented: `{summary['fixture_seed_count']}`",
        f"- truth target occurrences separated: `{summary['truth_target_occurrence_count']}`",
        "",
        "## Included Data",
        "",
        "- `historical_partial_texts/historical_output_inventory.csv/jsonl`",
        "- `historical_partial_texts/partial_text_occurrences.csv/jsonl`",
        "- `historical_partial_texts/unique_partial_text_rows.csv/jsonl`",
        "- `historical_partial_texts/truth_target_occurrences.csv/jsonl`",
        "- `historical_partial_texts/historical_partial_text_summary.json`",
        "- `current_scorer_failure_review/` contains the accepted scorer/repetition reports through Stage 2e.",
        "- `source_scripts/` contains the report scripts.",
        "- `tests/` contains the focused tests.",
        "",
        "## Caveats",
        "",
        "- This is a historical output inventory, not a new solver run.",
        "- Occurrence counts are not independent evidence counts.",
        "- Match/truth fields are included only where already present in source material.",
        "- The current scorer findings remain report-only and do not justify a runtime scorer replacement.",
    ]
    (PACK_DIR / "README.md").write_text("\n".join(readme).rstrip() + "\n", encoding="utf-8")

    if PACK_ZIP.exists():
        PACK_ZIP.unlink()
    shutil.make_archive(str(PACK_ZIP.with_suffix("")), "zip", PACK_DIR)
    summary["pack_dir"] = _repo_rel(PACK_DIR)
    summary["pack_zip"] = _repo_rel(PACK_ZIP)
    print(
        "[historical_partial_text_review_v1] "
        f"pack_dir={summary['pack_dir']} pack_zip={summary['pack_zip']}",
        flush=True,
    )
    return summary


def main() -> None:
    build_review_pack()


if __name__ == "__main__":
    main()
