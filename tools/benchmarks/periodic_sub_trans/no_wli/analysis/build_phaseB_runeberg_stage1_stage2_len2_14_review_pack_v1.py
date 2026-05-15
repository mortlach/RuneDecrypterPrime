from __future__ import annotations

"""
Build a self-contained reviewer pack for the PhaseB Runeberg NOSE stage1/stage2
len2-14 combined run.

Repo-local automation scripts in this repository intentionally use hardcoded
configuration rather than CLI arguments.
"""

import csv
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RUN_LABEL = "phaseB_runeberg_stage1_stage2_len2_14_review_pack_2026-05-11"
OUTPUT_DIR_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "phaseB_runeberg_stage1_stage2_len2_14_review_pack_2026-05-11"
)
ZIP_REL = OUTPUT_DIR_REL + ".zip"

LOCAL_REPO_ROOT = Path(__file__).resolve().parents[5]
DJ_REPO_ROOT = Path(r"\\DJ\sjduk\OneDrive\Documents\github\RuneDecrypterPrime")

COMBINED_OUTPUT_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "stage1_stage2_fwd_full_len2_14_combined_v1"
)
SOURCE_BUNDLE_ZIP_REL = (
    "output/tools/get_src_extended_review_bundle/"
    "get_src_extended_review_bundle__20260511T145225Z.zip"
)
SOURCE_BUNDLE_SUMMARY_REL = (
    "output/tools/get_src_extended_review_bundle/"
    "get_src_extended_review_bundle__20260511T145225Z.summary.json"
)

RAW_DATA_FILE_NAMES = {
    "sample_rows.csv",
    "feature_rows.csv",
    "convergence_summary.csv",
}

SOURCE_FILES = (
    "AGENTS.md",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/combine_phaseB_runeberg_stage1_stage2_len2_14_runs_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_runeberg_stage1_stage2_len2_14_review_pack_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_damage_ladder_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_stage2_len2_14_pc_a.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_stage2_len2_14_pc_b.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_runeberg_medium_book_lists_v1.py",
    "tests/tools/test_phaseB_runeberg_nose_damage_ladder_v1.py",
    "tools/get_src_extended_review_bundle.py",
)

PLANNING_FILES = (
    "planning/working/stage2_fwd_full_len2_14_pc_a_launch_20260510.md",
    "planning/working/stage2_fwd_full_len2_14_pc_b_launch_20260510.md",
    "planning/review/phaseB_runeberg_nose_damage_ladder_medium_summary_review_20260509/README.md",
    "planning/projects/no_wli/20_active_plans/april_28_2026_summary_so_far.md",
)

LOCAL_RUN_DIRS = {
    "stage1_pc_b": (
        LOCAL_REPO_ROOT,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage1_fwd_full_1k_pc_b",
    ),
    "stage2_pc_b": (
        LOCAL_REPO_ROOT,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage2_fwd_full_len2_14_pc_b",
    ),
}

DJ_RUN_DIRS = {
    "stage1_pc_a": (
        DJ_REPO_ROOT,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage1_fwd_full_1k_pc_a",
    ),
    "stage2_pc_a": (
        DJ_REPO_ROOT,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage2_fwd_full_len2_14_pc_a",
    ),
}

STAGE1_COMBINED_REFERENCE = (
    DJ_REPO_ROOT,
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage1_fwd_full_1k_combined_pc_a_pc_b",
)

STAGE1_COMBINED_REFERENCE_FILES = (
    "combined_run_check.json",
    "combined_top_by_length.csv",
    "combined_length_update.csv",
    "combined_damaged_vs_null_by_view.csv.gz",
)

AGGREGATE_RUN_FILES = (
    "config.json",
    "run_manifest.json",
    "run_state.json",
    "final_summary.json",
    "readout.md",
    "input_manifest.csv",
    "timing_checkpoints.csv",
    "rolling_feature_summary.csv",
    "final_feature_summary.csv",
    "damaged_vs_null_summary.csv",
    "damaged_vs_null_by_view.csv.gz",
    "feature_histograms.csv.gz",
    "feature_quantiles.csv.gz",
    "dictionary_hash_manifest.csv",
)

COMBINED_FILES = (
    "combined_readout.md",
    "combined_run_check.json",
    "combined_top_by_length.csv",
    "combined_length_update.csv",
    "combined_damaged_vs_null_by_view.csv.gz",
)


def _repo_rel(path: Path, root: Path = LOCAL_REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(root.parent.resolve()).as_posix()
        except ValueError:
            return path.name


def _ensure_under_repo(path: Path) -> None:
    root = LOCAL_REPO_ROOT.resolve()
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"path escapes repo root: {path}")


def _reset_dir(path: Path) -> None:
    _ensure_under_repo(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _copy_file(src: Path, dst: Path, manifest: list[dict[str, Any]], *, reason: str) -> None:
    if src.name in RAW_DATA_FILE_NAMES:
        raise ValueError(f"refusing raw-data file: {src}")
    if not src.exists():
        manifest.append(
            {
                "pack_path": dst.as_posix(),
                "source_path": str(src),
                "bytes": 0,
                "status": "missing",
                "reason": reason,
            }
        )
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    manifest.append(
        {
            "pack_path": dst.as_posix(),
            "source_path": str(src),
            "bytes": int(dst.stat().st_size),
            "status": "copied",
            "reason": reason,
        }
    )


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON: {path}")
    return data


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _copy_source_and_planning(pack_dir: Path, manifest: list[dict[str, Any]]) -> None:
    for rel in SOURCE_FILES:
        _copy_file(
            LOCAL_REPO_ROOT / rel,
            pack_dir / "10_source_context" / rel,
            manifest,
            reason="source/test context",
        )
    for rel in PLANNING_FILES:
        src = LOCAL_REPO_ROOT / rel
        if not src.exists():
            src = DJ_REPO_ROOT / rel
        _copy_file(
            src,
            pack_dir / "20_planning_context" / rel,
            manifest,
            reason="planning context",
        )


def _copy_run_outputs(pack_dir: Path, manifest: list[dict[str, Any]]) -> None:
    for source_key, (root, rel_dir) in {**DJ_RUN_DIRS, **LOCAL_RUN_DIRS}.items():
        src_dir = root / rel_dir
        dst_dir = pack_dir / "30_run_summaries" / source_key
        for name in AGGREGATE_RUN_FILES:
            _copy_file(
                src_dir / name,
                dst_dir / name,
                manifest,
                reason=f"aggregate output for {source_key}",
            )

    reference_root, reference_rel = STAGE1_COMBINED_REFERENCE
    reference_src = reference_root / reference_rel
    reference_dst = pack_dir / "30_run_summaries" / "stage1_combined_reference"
    for name in STAGE1_COMBINED_REFERENCE_FILES:
        _copy_file(
            reference_src / name,
            reference_dst / name,
            manifest,
            reason="existing stage1 combined cross-check reference",
        )

    combined_src = LOCAL_REPO_ROOT / COMBINED_OUTPUT_REL
    combined_dst = pack_dir / "40_combined_outputs"
    for name in COMBINED_FILES:
        _copy_file(
            combined_src / name,
            combined_dst / name,
            manifest,
            reason="combined aggregate output",
        )


def _copy_source_bundle(pack_dir: Path, manifest: list[dict[str, Any]]) -> None:
    _copy_file(
        LOCAL_REPO_ROOT / SOURCE_BUNDLE_ZIP_REL,
        pack_dir / "90_source_bundle" / Path(SOURCE_BUNDLE_ZIP_REL).name,
        manifest,
        reason="full output zip from get_src_extended_review_bundle.py",
    )
    _copy_file(
        LOCAL_REPO_ROOT / SOURCE_BUNDLE_SUMMARY_REL,
        pack_dir / "90_source_bundle" / Path(SOURCE_BUNDLE_SUMMARY_REL).name,
        manifest,
        reason="summary output from get_src_extended_review_bundle.py",
    )


def _build_summary_files(pack_dir: Path) -> dict[str, Any]:
    combined_dir = LOCAL_REPO_ROOT / COMBINED_OUTPUT_REL
    run_check = _load_json(combined_dir / "combined_run_check.json")
    top_rows = _read_csv_rows(combined_dir / "combined_top_by_length.csv")
    length_rows = _read_csv_rows(combined_dir / "combined_length_update.csv")

    source_bundle_summary = _load_json(LOCAL_REPO_ROOT / SOURCE_BUNDLE_SUMMARY_REL)
    copied_runs = run_check.get("runs", {})
    total_elapsed = sum(float(row.get("elapsed_s", 0.0)) for row in copied_runs.values())
    total_samples = sum(int(row.get("samples_done", 0)) for row in copied_runs.values())
    total_feature_rows = sum(int(row.get("feature_rows_done", 0)) for row in copied_runs.values())

    overview = {
        "pack_label": RUN_LABEL,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "combined_output": COMBINED_OUTPUT_REL,
        "compatible": run_check.get("compatible"),
        "combined_unique_chunks": run_check.get("combined_unique_chunks"),
        "combined_chunk_range": [
            run_check.get("combined_min_corpus_chunk_index"),
            run_check.get("combined_max_corpus_chunk_index"),
        ],
        "chunk_id_overlap_count": run_check.get("chunk_id_overlap_count"),
        "corpus_chunk_index_overlap_count": run_check.get("corpus_chunk_index_overlap_count"),
        "gap_ranges": run_check.get("corpus_chunk_index_gap_ranges"),
        "total_samples": total_samples,
        "total_feature_rows": total_feature_rows,
        "total_elapsed_seconds": total_elapsed,
        "source_bundle_zip": SOURCE_BUNDLE_ZIP_REL,
        "source_bundle_summary": {
            "included_files_count": source_bundle_summary.get("included_files_count"),
            "excluded_entries_count": source_bundle_summary.get("excluded_entries_count"),
            "zip_size_bytes": source_bundle_summary.get("zip_size_bytes"),
        },
        "raw_data_policy": {
            "excluded_from_review_pack": sorted(RAW_DATA_FILE_NAMES),
            "included_outputs_are_aggregate_statistics": True,
        },
    }
    (pack_dir / "00_pack_summary.json").write_text(
        json.dumps(overview, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    _write_csv(
        pack_dir / "05_key_statistics" / "best_normalized_rows_by_length.csv",
        top_rows,
        list(top_rows[0].keys()) if top_rows else [],
    )
    _write_csv(
        pack_dir / "05_key_statistics" / "length_effect_size_summary.csv",
        length_rows,
        list(length_rows[0].keys()) if length_rows else [],
    )

    readme = _pack_readme(overview, top_rows, length_rows)
    (pack_dir / "README.md").write_text(readme, encoding="utf-8")
    (pack_dir / "01_REVIEWER_REQUEST.md").write_text(_reviewer_request(), encoding="utf-8")
    (pack_dir / "02_EVIDENCE_MAP.md").write_text(_evidence_map(), encoding="utf-8")
    return overview


def _pack_readme(overview: dict[str, Any], top_rows: list[dict[str, str]], length_rows: list[dict[str, str]]) -> str:
    top_lines = [
        (
            f"- len `{row['span_length']}`: d=`{row['cohen_d']}` "
            f"`{row['dictionary_cut']}` HD `{row['hd']}` `{row['feature_name']}` "
            f"`{row['damage_model']}` level `{row['damage_level']}` vs `{row['null_model']}`"
        )
        for row in top_rows
    ]
    length_lines = [
        (
            f"- len `{row['span_length']}`: median |d| `{row['median_abs_d']}`, "
            f"p90 |d| `{row['p90_abs_d']}`, max |d| `{row['max_abs_d']}`, "
            f"weak rows `{row['weak_rows_abs_d_lt_0_2']}`"
        )
        for row in length_rows
    ]
    return (
        f"# {RUN_LABEL}\n\n"
        "Self-contained review pack for the PhaseB Runeberg NOSE damage-ladder "
        "stage1/stage2 len2-14 combined summary.\n\n"
        "## What To Review\n\n"
        "- Whether the combined coverage is clean and contiguous.\n"
        "- Whether the length/HD damaged-vs-null effects support carrying lengths 2..14.\n"
        "- Whether the run split across local PC B and `\\\\DJ` PC A introduces any provenance concern.\n"
        "- Whether the aggregate summaries are sufficient before any next wider run.\n\n"
        "## Coverage Summary\n\n"
        f"- compatible: `{overview['compatible']}`\n"
        f"- unique chunks: `{overview['combined_unique_chunks']}`\n"
        f"- chunk range: `{overview['combined_chunk_range'][0]}..{overview['combined_chunk_range'][1]}`\n"
        f"- total samples: `{overview['total_samples']}`\n"
        f"- total feature rows represented by aggregate summaries: `{overview['total_feature_rows']}`\n"
        f"- chunk-id overlaps: `{overview['chunk_id_overlap_count']}`\n"
        f"- corpus-index overlaps: `{overview['corpus_chunk_index_overlap_count']}`\n"
        f"- gap ranges: `{len(overview['gap_ranges'])}`\n\n"
        "## Best Normalized Rows By Length\n\n"
        + "\n".join(top_lines)
        + "\n\n## Length Effect-Size Summary\n\n"
        + "\n".join(length_lines)
        + "\n\n## Pack Layout\n\n"
        "- `00_pack_summary.json`: machine-readable pack summary.\n"
        "- `01_REVIEWER_REQUEST.md`: prompt for an external reviewer.\n"
        "- `02_EVIDENCE_MAP.md`: contents and raw-data exclusion notes.\n"
        "- `05_key_statistics/`: compact top-line statistics copied from combined outputs.\n"
        "- `10_source_context/`: relevant scripts/tests.\n"
        "- `20_planning_context/`: launch/review planning notes.\n"
        "- `30_run_summaries/`: per-run aggregate outputs only.\n"
        "- `40_combined_outputs/`: full combined aggregate outputs.\n"
        "- `90_source_bundle/`: full generated output of `tools/get_src_extended_review_bundle.py`.\n\n"
        "## Raw Data Policy\n\n"
        "This review pack intentionally excludes raw `sample_rows.csv`, raw `feature_rows.csv`, "
        "and large convergence raw-like CSVs. Included CSV/GZ files are aggregate statistics, "
        "histograms, quantiles, summaries, configs, manifests, or readouts.\n"
    )


def _reviewer_request() -> str:
    return """# Reviewer Request

Please review the PhaseB Runeberg NOSE damaged-text span-Hamming evidence pack.

Questions:

1. Does `40_combined_outputs/combined_run_check.json` establish clean coverage for chunk indices `0..12399` without overlap or gaps?
2. Are the combined damaged-vs-null effects in `combined_length_update.csv` and `combined_top_by_length.csv` strong enough to keep lengths `2..14` in the next staged analysis?
3. Does length `14` still carry enough signal, or should future runs narrow before spending more runtime?
4. Are the Stage 1 and Stage 2 profiles pooled correctly for lengths `2..14`, given that Stage 1 also included length `1`?
5. Are there any provenance or data-splitting concerns from using PC A data from `\\\\DJ` and PC B data from the local machine?
6. Is the raw-data exclusion appropriate for review, or is there a specific aggregate recomputation missing?

Important: this pack is report-only. It does not propose production scorer changes.
"""


def _evidence_map() -> str:
    return """# Evidence Map

## Main Combined Evidence

- `40_combined_outputs/combined_readout.md`
- `40_combined_outputs/combined_run_check.json`
- `40_combined_outputs/combined_length_update.csv`
- `40_combined_outputs/combined_top_by_length.csv`
- `40_combined_outputs/combined_damaged_vs_null_by_view.csv.gz`

## Per-Run Aggregate Evidence

Each folder under `30_run_summaries/` contains aggregate-only files such as:

- `final_summary.json`
- `run_state.json`
- `run_manifest.json`
- `readout.md`
- `final_feature_summary.csv`
- `damaged_vs_null_summary.csv`
- `damaged_vs_null_by_view.csv.gz`
- `feature_histograms.csv.gz`
- `feature_quantiles.csv.gz`
- `timing_checkpoints.csv`
- `rolling_feature_summary.csv`

Raw `sample_rows.csv`, raw `feature_rows.csv`, and large convergence raw-like CSVs are intentionally absent.

## Source Bundle

`90_source_bundle/` contains the complete generated outputs from:

`tools/get_src_extended_review_bundle.py`

This includes:

- `get_src_extended_review_bundle__20260511T145225Z.zip`
- `get_src_extended_review_bundle__20260511T145225Z.summary.json`

## Provenance Notes

- PC A Stage 1 and Stage 2 data came from `\\\\DJ\\sjduk\\OneDrive\\Documents\\github\\RuneDecrypterPrime`.
- PC B Stage 1 and Stage 2 data came from the local repo.
- Existing `stage1_fwd_full_1k_combined_pc_a_pc_b` on `\\\\DJ` is included as a cross-check reference.
- The final combined coverage is contiguous for corpus chunk indices `0..12399`.
"""


def _write_manifest(pack_dir: Path, manifest: list[dict[str, Any]]) -> None:
    fields = ["pack_path", "source_path", "bytes", "status", "reason"]
    _write_csv(pack_dir / "MANIFEST.csv", manifest, fields)
    (pack_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _zip_pack(pack_dir: Path, zip_path: Path) -> None:
    _ensure_under_repo(zip_path)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(pack_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(pack_dir.parent).as_posix())


def build_review_pack() -> dict[str, Any]:
    pack_dir = LOCAL_REPO_ROOT / OUTPUT_DIR_REL
    zip_path = LOCAL_REPO_ROOT / ZIP_REL
    _reset_dir(pack_dir)
    manifest: list[dict[str, Any]] = []
    _copy_source_and_planning(pack_dir, manifest)
    _copy_run_outputs(pack_dir, manifest)
    _copy_source_bundle(pack_dir, manifest)
    overview = _build_summary_files(pack_dir)
    _write_manifest(pack_dir, manifest)
    _zip_pack(pack_dir, zip_path)
    summary = {
        **overview,
        "pack_dir": _repo_rel(pack_dir),
        "pack_zip": _repo_rel(zip_path),
        "pack_zip_size_bytes": int(zip_path.stat().st_size),
        "manifest_copied_count": sum(1 for row in manifest if row["status"] == "copied"),
        "manifest_missing_count": sum(1 for row in manifest if row["status"] == "missing"),
    }
    (pack_dir / "PACK_BUILD_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    summary = build_review_pack()
    print(
        f"[{RUN_LABEL}] pack_dir={summary['pack_dir']} "
        f"pack_zip={summary['pack_zip']} size={summary['pack_zip_size_bytes']}",
        flush=True,
    )
    print(
        f"[{RUN_LABEL}] copied={summary['manifest_copied_count']} "
        f"missing={summary['manifest_missing_count']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
