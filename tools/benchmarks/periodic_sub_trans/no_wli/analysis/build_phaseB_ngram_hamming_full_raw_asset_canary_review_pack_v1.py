from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
RUN_LABEL = "phaseB_ngram_hamming_full_raw_asset_canary_review_pack_2026-05-29"
PACK_DIR_REL = f"planning/projects/no_wli/40_review_summaries/{RUN_LABEL}"
PACK_ZIP_REL = f"{PACK_DIR_REL}.zip"

PLAN_REL = "planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_implementation_start_plan_2026-05-14.md"
SUMMARY_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_assets_summary_v1"
)
CANARY_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_canary_v1"
)


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_file(src_rel: str, dest_rel: str) -> None:
    src = REPO_ROOT / src_rel
    dest = REPO_ROOT / PACK_DIR_REL / dest_rel
    if src.exists():
        ensure_under_repo(dest)
        shutil.copy2(src, dest)


def build_review_summary(pack_dir: Path) -> None:
    summary_manifest_path = REPO_ROOT / SUMMARY_REL / "full_raw_asset_summary_manifest.json"
    canary_manifest_path = REPO_ROOT / CANARY_REL / "canary_manifest.json"
    summary = json.loads(summary_manifest_path.read_text(encoding="utf-8")) if summary_manifest_path.exists() else {}
    canary = json.loads(canary_manifest_path.read_text(encoding="utf-8")) if canary_manifest_path.exists() else {}
    lines = [
        "# PhaseB N-Gram Hamming Full Raw Asset/Canary Review Summary - 2026-05-29",
        "",
        "## Length-Bias Warning",
        "",
        "P2/P3 whole-phrase scoring uses `min_phrase_token_length >= 8`.",
        "This is not fixed-length 8-rune scoring.",
        "An 8-rune phrase and a 20-rune phrase can both score, but they are not equivalent evidence.",
        "The 20-rune phrase is stricter in relative mismatch terms.",
        "This is a deliberate data-taking choice, not a settled production scoring policy.",
        "",
        "```text",
        "scan_mode = whole_phrase_only",
        "internal_phrase_windows = false",
        "```",
        "",
        "## Asset Provenance",
        "",
        f"- status: `{summary.get('status', 'not_run')}`",
        f"- asset mode: `{summary.get('asset_mode', '')}`",
        f"- full raw confirmed: `{summary.get('full_raw_ngram_rebuild_confirmed', '')}`",
        f"- sample line limit per order: `{summary.get('sample_line_limit_per_order', '')}`",
        f"- phrase entries: `{summary.get('phrase_entry_count', '')}`",
        f"- phrase index SHA256: `{summary.get('phrase_index_sha256', '')}`",
        "",
        "## Canary",
        "",
        f"- status: `{canary.get('status', 'not_run')}`",
        f"- completed scan cells: `{canary.get('completed_scan_cells', '')}`",
        f"- attempts/sec: `{canary.get('attempts_per_second', '')}`",
        f"- total hits: `{canary.get('total_hit_count', '')}`",
        "",
        "## Still Forbidden",
        "",
        "- production scorer changes",
        "- sample-index evidence presented as full raw",
        "- hidden candidate caps",
        "- hidden sample-line caps",
        "- silent backfill",
        "- phrase-internal windows",
    ]
    (pack_dir / "10_context" / "review_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_pack() -> dict[str, object]:
    pack_dir = REPO_ROOT / PACK_DIR_REL
    if pack_dir.exists():
        shutil.rmtree(pack_dir)
    (pack_dir / "10_context").mkdir(parents=True, exist_ok=True)
    (pack_dir / "20_implementation" / "source").mkdir(parents=True, exist_ok=True)
    (pack_dir / "20_implementation" / "tests").mkdir(parents=True, exist_ok=True)
    (pack_dir / "30_outputs" / "asset_summary").mkdir(parents=True, exist_ok=True)
    (pack_dir / "30_outputs" / "canary").mkdir(parents=True, exist_ok=True)
    copy_file("AGENTS.md", "10_context/AGENTS.md")
    copy_file(PLAN_REL, "10_context/active_plan.md")
    build_review_summary(pack_dir)
    for name in (
        "build_phaseB_ngram_hamming_full_raw_assets_v1.py",
        "summarise_phaseB_ngram_hamming_full_raw_assets_v1.py",
        "run_phaseB_ngram_hamming_full_raw_canary_v1.py",
        "build_phaseB_ngram_hamming_full_raw_asset_canary_review_pack_v1.py",
    ):
        copy_file(f"tools/benchmarks/periodic_sub_trans/no_wli/analysis/{name}", f"20_implementation/source/{name}")
    copy_file(
        "tests/tools/test_phaseB_ngram_hamming_full_raw_asset_canary_v1.py",
        "20_implementation/tests/test_phaseB_ngram_hamming_full_raw_asset_canary_v1.py",
    )
    for name in (
        "full_raw_asset_summary_manifest.json",
        "full_raw_asset_file_rows.csv",
        "full_raw_profile_eligibility_rows.csv",
        "full_raw_word_length_pattern_rows.csv",
        "readout.md",
    ):
        copy_file(f"{SUMMARY_REL}/{name}", f"30_outputs/asset_summary/{name}")
    for name in (
        "canary_manifest.json",
        "canary_cell_timing_rows.csv",
        "runtime_projection_rows.csv",
        "hit_summary_by_phrase_length_bin.csv",
        "word_length_pattern_distribution.csv",
        "phrase_log_count_bin_distribution.csv",
        "p2_p3_hit_retention_rows.csv",
        "readout.md",
    ):
        copy_file(f"{CANARY_REL}/{name}", f"30_outputs/canary/{name}")
    zip_path = REPO_ROOT / PACK_ZIP_REL
    ensure_under_repo(zip_path)
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        for path in sorted(pack_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(pack_dir).as_posix())
    with ZipFile(zip_path) as zf:
        names = zf.namelist()
    summary = {"pack_dir": PACK_DIR_REL, "zip_path": PACK_ZIP_REL, "entry_count": len(names), "backslash_entries": sum("\\" in name for name in names)}
    (pack_dir / "PACK_BUILD_SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    summary = build_pack()
    print(f"[{RUN_LABEL}] zip={summary['zip_path']}")
    print(f"[{RUN_LABEL}] entries={summary['entry_count']} backslash_entries={summary['backslash_entries']}")


if __name__ == "__main__":
    main()
