from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
RUN_LABEL = "phaseB_ngram_hamming_canary_probe_review_pack_2026-05-29"
PACK_DIR_REL = f"planning/projects/no_wli/40_review_summaries/{RUN_LABEL}"
PACK_ZIP_REL = f"{PACK_DIR_REL}.zip"

PLAN_REL = "planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_implementation_start_plan_2026-05-14.md"
ASSET_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_canary_probe_assets_summary_v1"
)
CANARY_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_canary_probe_v1"
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


def read_json(rel: str) -> dict[str, object]:
    path = REPO_ROOT / rel
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def build_review_summary(pack_dir: Path) -> None:
    asset = read_json(f"{ASSET_REL}/canary_probe_asset_summary_manifest.json")
    canary = read_json(f"{CANARY_REL}/canary_probe_manifest.json")
    lines = [
        "# PhaseB N-Gram Hamming Canary Probe Review Summary - 2026-05-29",
        "",
        "## Verdict Target",
        "",
        "This pack is a canary-probe review pack. It proves workflow, data integrity, output schemas, P2/P3 scan plumbing, and full-run gate behaviour.",
        "It is not a full raw asset/provenance pass and must not be used for long-run runtime sizing.",
        "",
        "## Length-Bias Warning",
        "",
        "P2/P3 whole-phrase scoring uses `min_phrase_token_length >= 8`.",
        "This is not fixed-length 8-rune scoring.",
        "An 8-rune phrase and a 20-rune phrase can both score, but they are not equivalent evidence.",
        "The 20-rune phrase is stricter in relative mismatch terms.",
        "",
        "```text",
        "scan_mode = whole_phrase_only",
        "internal_phrase_windows = false",
        "```",
        "",
        "P3 eligible phrase counts may equal P2 eligible phrase counts. The P3 effect is measured by P3-retained hits and P2-only hits rejected by P3.",
        "",
        "## Probe Asset Summary",
        "",
        f"- status: `{asset.get('status', 'not_run')}`",
        f"- asset mode: `{asset.get('asset_mode', '')}`",
        f"- full asset available: `{asset.get('full_asset_available', '')}`",
        f"- full raw rebuild confirmed: `{asset.get('full_raw_ngram_rebuild_confirmed', '')}`",
        f"- sample line limit per order: `{asset.get('sample_line_limit_per_order', '')}`",
        f"- phrase entries: `{asset.get('phrase_entry_count', '')}`",
        f"- phrase index SHA256: `{asset.get('phrase_index_sha256', '')}`",
        "",
        "## Canary Probe",
        "",
        f"- status: `{canary.get('status', 'not_run')}`",
        f"- completed scan cells: `{canary.get('completed_scan_cells', '')}` / `{canary.get('expected_scan_cells', '')}`",
        f"- backend implementation: `{canary.get('backend_impl', '')}`",
        f"- Python fallback allowed: `{canary.get('python_fallback_allowed', '')}`",
        f"- full-run gate on probe assets: `{canary.get('full_run_gate_on_probe_assets', '')}`",
        f"- total hits: `{canary.get('total_hit_count', '')}`",
        "",
        "## Next Decision",
        "",
        "If this probe is accepted, the next tranche should set up the real full raw asset build/run launcher with declared budget, progress logs, resumable outputs, and no hidden caps.",
        "",
        "## Still Forbidden",
        "",
        "- production scorer changes",
        "- sample/probe evidence presented as full raw",
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
        "build_phaseB_ngram_hamming_canary_probe_assets_v1.py",
        "summarise_phaseB_ngram_hamming_canary_probe_assets_v1.py",
        "run_phaseB_ngram_hamming_canary_probe_v1.py",
        "build_phaseB_ngram_hamming_canary_probe_review_pack_v1.py",
    ):
        copy_file(f"tools/benchmarks/periodic_sub_trans/no_wli/analysis/{name}", f"20_implementation/source/{name}")
    copy_file(
        "tests/tools/test_phaseB_ngram_hamming_full_raw_asset_canary_v1.py",
        "20_implementation/tests/test_phaseB_ngram_hamming_full_raw_asset_canary_v1.py",
    )
    for name in (
        "canary_probe_asset_summary_manifest.json",
        "canary_probe_asset_file_rows.csv",
        "canary_probe_profile_eligibility_rows.csv",
        "canary_probe_word_length_pattern_rows.csv",
        "readout.md",
    ):
        copy_file(f"{ASSET_REL}/{name}", f"30_outputs/asset_summary/{name}")
    for name in (
        "canary_probe_manifest.json",
        "canary_probe_cell_timing_rows.csv",
        "canary_probe_hit_rows.jsonl",
        "hit_summary_by_phrase_length_bin.csv",
        "word_length_pattern_distribution.csv",
        "phrase_log_count_bin_distribution.csv",
        "total_hd_distribution.csv",
        "normalised_total_hd_distribution.csv",
        "short_word_fraction_distribution.csv",
        "non_short_word_token_count_distribution.csv",
        "normalised_non_short_hd_distribution.csv",
        "p2_p3_hit_retention_rows.csv",
        "candidate_chunk_profile_aggregate_rows.csv",
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
    summary = {
        "pack_dir": PACK_DIR_REL,
        "zip_path": PACK_ZIP_REL,
        "entry_count": len(names),
        "backslash_entries": sum("\\" in name for name in names),
    }
    (pack_dir / "PACK_BUILD_SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    summary = build_pack()
    print(f"[{RUN_LABEL}] zip={summary['zip_path']}")
    print(f"[{RUN_LABEL}] entries={summary['entry_count']} backslash_entries={summary['backslash_entries']}")


if __name__ == "__main__":
    main()
