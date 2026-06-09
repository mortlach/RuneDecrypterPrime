from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]

PACK_NAME = "phaseB_strict_o3_o4_fwd_initial_joint_diagnostic_review_pack_2026-06-08"
PACK_DIR = REPO_ROOT / "planning/projects/no_wli/40_review_summaries" / PACK_NAME
ZIP_PATH = PACK_DIR.with_suffix(".zip")
RUN_DIR = (
    REPO_ROOT
    / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_strict_o3_o4_fwd_initial_joint_diagnostic_v1"
)
LOG_PATH = (
    REPO_ROOT
    / "planning/projects/no_wli/50_console_and_watch_logs/"
    / "phaseB_strict_o3_o4_fwd_initial_joint_diagnostic_bounded_8h_2026-06-07.log"
)
DESIGN_DIR = (
    REPO_ROOT
    / "planning/projects/no_wli/35_design/o3_o4_initial_integration_scoring_dev_pack_2026-06-07"
)

OUTPUT_FILES = (
    "run_manifest.json",
    "run_state.json",
    "final_summary.json",
    "progress_rows.csv",
    "sample_rows.csv",
    "sample_o3_summary_rows.csv",
    "sample_o4_summary_rows.csv",
    "joint_feature_rows.csv",
    "joint_rule_rows.csv",
    "joint_rule_by_damage_rows.csv",
    "joint_rule_by_null_class_rows.csv",
    "known_damage_runtime_projection_rows.csv",
    "failed_sample_rows.csv",
    "incomplete_sample_rows.csv",
    "readout.md",
)

SOURCE_FILES = (
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_strict_o3_o4_fwd_joint_diagnostic_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_strict_o3_o4_fwd_joint_resume_smoke_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_strict_o3_o4_fwd_initial_joint_diagnostic_review_pack_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/common/phaseB_common_asset_authority_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/common/phaseB_common_resume_runner_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/common/phaseB_damage_levels_contract_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/common/phaseB_joint_feature_contract_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/common/phaseB_joint_rule_grid_reference_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/common/phaseB_build_initial_o3_o4_joint_feature_table_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/damage_models_reference_v2.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/runtime_projection_reference_v2.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/strict_o3_anchor_reference_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_strict_o4_fwd_bridge_reference_v1.py",
)

TEST_FILES = (
    "tests/tools/test_phaseB_common_asset_authority_v1.py",
    "tests/tools/test_phaseB_common_resume_runner_v1.py",
    "tests/tools/test_phaseB_damage_levels_contract_v1.py",
    "tests/tools/test_phaseB_joint_feature_contract_v1.py",
    "tests/tools/test_phaseB_joint_rule_grid_reference_v1.py",
)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(rel_path: str, text: str) -> None:
    target = PACK_DIR / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def copy_file(src: Path, rel_path: str, copied: list[dict[str, Any]]) -> None:
    if not src.exists():
        raise FileNotFoundError(repo_rel(src))
    target = PACK_DIR / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target)
    copied.append(
        {
            "pack_path": rel_path,
            "source_path": repo_rel(src),
            "bytes": src.stat().st_size,
            "sha256": sha256(src),
        }
    )


def csv_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def class_counts(rows: Iterable[dict[str, str]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = row.get(field, "")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def build_reviewer_summary(final_summary: dict[str, Any]) -> str:
    joint_rows = read_csv_rows(RUN_DIR / "joint_feature_rows.csv")
    rule_rows = read_csv_rows(RUN_DIR / "joint_rule_rows.csv")
    by_damage = read_csv_rows(RUN_DIR / "joint_rule_by_damage_rows.csv")
    by_null = read_csv_rows(RUN_DIR / "joint_rule_by_null_class_rows.csv")
    projection = read_csv_rows(RUN_DIR / "known_damage_runtime_projection_rows.csv")
    ordinary = next((row for row in by_null if row["null_class"] == "ordinary_null"), {})
    hard = next((row for row in by_null if row["null_class"] == "hard_local_order_control"), {})
    return "\n".join(
        [
            "# Strict O3/O4 Initial Joint Diagnostic Review Pack",
            "",
            "## Verdict For Review",
            "",
            "This pack is report-only evidence for the first strict/FWD O3+O4 joint diagnostic run.",
            "It does not approve production scoring, production ranking, REV scope, normal O4 scope, or a longer run.",
            "",
            "## Run Facts",
            "",
            f"- status: `{final_summary.get('status')}`",
            f"- run mode: `{final_summary.get('run_mode')}`",
            f"- report only: `{final_summary.get('report_only')}`",
            f"- direction: `{final_summary.get('direction')}`",
            f"- dictionary cut: `{final_summary.get('dictionary_cut')}`",
            f"- sample count: `{final_summary.get('sample_count')}`",
            f"- O3 summary rows: `{final_summary.get('o3_summary_rows')}`",
            f"- O4 summary rows: `{final_summary.get('o4_summary_rows')}`",
            f"- joint feature rows: `{final_summary.get('joint_feature_rows')}`",
            f"- failed sample rows: `{final_summary.get('failed_sample_rows')}`",
            f"- incomplete sample rows: `{final_summary.get('incomplete_sample_rows')}`",
            f"- elapsed seconds: `{float(final_summary.get('elapsed_seconds', 0.0)):.1f}`",
            f"- peak memory MB: `{float(final_summary.get('peak_memory_mb', 0.0)):.1f}`",
            "",
            "## Main Readout",
            "",
            f"- ordinary null rows: `{ordinary.get('row_count', '')}`; O3 nonzero: `{ordinary.get('o3_nonzero_count', '')}`; O4 nonzero: `{ordinary.get('o4_nonzero_count', '')}`; strong confirm: `{ordinary.get('strong_confirm_count', '')}`",
            f"- hard local-order control rows: `{hard.get('row_count', '')}`; O3 nonzero: `{hard.get('o3_nonzero_count', '')}`; O4 nonzero: `{hard.get('o4_nonzero_count', '')}`; strong confirm: `{hard.get('strong_confirm_count', '')}`",
            "- ordinary nulls collapsed to zero in this bounded run.",
            "- block-shuffle controls remain deliberately hard and should not be treated as ordinary nulls.",
            "- O4 confirmation is present but still report-only telemetry.",
            "",
            "## Rule Counts",
            "",
            *[
                f"- `{row['phrase_confidence_class']}`: rows `{row['row_count']}`, O3 nonzero `{row['o3_nonzero_count']}`, O4 nonzero `{row['o4_nonzero_count']}`, strong confirm `{row['strong_confirm_count']}`"
                for row in rule_rows
            ],
            "",
            "## Damage-Level Counts",
            "",
            *[
                f"- damage `{row['damage_level'] or 'clean/null/control'}`: rows `{row['row_count']}`, O3 nonzero `{row['o3_nonzero_count']}`, O4 nonzero `{row['o4_nonzero_count']}`, strong confirm `{row['strong_confirm_count']}`"
                for row in by_damage
            ],
            "",
            "## Runtime Projection",
            "",
            *[
                f"- `{row['stage_name']}`: `{row['projected_hours']}` hours for `{row['total_samples']}` samples"
                for row in projection
            ],
            "",
            "## Review Questions",
            "",
            "- Did O3 and O4 run on the same samples?",
            "- Are all rows strict/FWD only?",
            "- Did target-actual damage remain valid?",
            "- Does O4 add useful confirmation beyond O3?",
            "- Do ordinary nulls collapse while hard local-order controls stay high?",
            "- Is the runtime acceptable for the next 25/50 chunk staging decision?",
            "",
            "## Joint Feature Class Distribution",
            "",
            json.dumps(class_counts(joint_rows, "phrase_confidence_class"), indent=2, sort_keys=True),
            "",
        ]
    )


def build_review_pack() -> dict[str, Any]:
    if PACK_DIR.exists():
        shutil.rmtree(PACK_DIR)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    PACK_DIR.mkdir(parents=True)

    final_summary = read_json(RUN_DIR / "final_summary.json")
    if final_summary.get("status") != "complete":
        raise RuntimeError("joint diagnostic run is not complete")
    if not final_summary.get("fwd_only_confirmed"):
        raise RuntimeError("FWD-only confirmation is missing")
    if int(final_summary.get("failed_sample_rows", -1)) != 0:
        raise RuntimeError("failed sample rows are nonzero")
    if int(final_summary.get("incomplete_sample_rows", -1)) != 0:
        raise RuntimeError("incomplete sample rows are nonzero")

    copied: list[dict[str, Any]] = []
    for name in OUTPUT_FILES:
        copy_file(RUN_DIR / name, f"30_outputs/{name}", copied)
    copy_file(LOG_PATH, "20_logs/visible_bounded_run_log.txt", copied)
    for rel in SOURCE_FILES:
        copy_file(REPO_ROOT / rel, f"50_source/{rel}", copied)
    for rel in TEST_FILES:
        copy_file(REPO_ROOT / rel, f"40_tests/{rel}", copied)
    for src in sorted(DESIGN_DIR.rglob("*.md")):
        rel = src.relative_to(DESIGN_DIR).as_posix()
        copy_file(src, f"10_design/{rel}", copied)

    write_text("00_start_here.md", build_reviewer_summary(final_summary))
    write_text(
        "02_authority_and_limits.md",
        "\n".join(
            [
                "# Authority And Limits",
                "",
                "- report_only: true",
                "- production scorer change: false",
                "- production ranking authority: false",
                "- direction: fwd only",
                "- dictionary cut: strict only",
                "- O3 and O4 rows are diagnostic telemetry only",
                "- ordinary nulls and hard local-order controls must remain separated",
                "- this pack gates the next 25/50 chunk staging decision only",
                "",
            ]
        ),
    )

    output_counts = {name: csv_count(RUN_DIR / name) for name in OUTPUT_FILES if name.endswith(".csv")}
    summary = {
        "status": "packed_review_ready",
        "pack_name": PACK_NAME,
        "created_utc": utc_now(),
        "run_status": final_summary.get("status"),
        "run_output": repo_rel(RUN_DIR),
        "zip_path": repo_rel(ZIP_PATH),
        "entry_count": None,
        "zip_size_bytes": None,
        "backslash_entries": None,
        "output_row_counts": output_counts,
        "final_summary": final_summary,
        "copied_files": copied,
    }
    write_text("PACK_BUILD_SUMMARY.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACK_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACK_DIR).as_posix())

    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = archive.namelist()
    summary["entry_count"] = len(names)
    summary["zip_size_bytes"] = ZIP_PATH.stat().st_size
    summary["backslash_entries"] = sum(1 for name in names if "\\" in name)
    write_text("PACK_BUILD_SUMMARY.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACK_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACK_DIR).as_posix())
    return summary


if __name__ == "__main__":
    result = build_review_pack()
    print(json.dumps(result, indent=2, sort_keys=True))
