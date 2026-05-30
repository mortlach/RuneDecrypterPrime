from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
RUN_LABEL = "phaseB_ngram_hamming_pre_long_run_external_review_pack_2026-05-30"
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


def build_review_questions(pack_dir: Path) -> None:
    lines = [
        "# Review Questions",
        "",
        "Please review this as a pre-long-run gate, not as a scoring-result review.",
        "",
        "1. Did the canary probe prove the intended workflow/data contract for orders 2 and 3?",
        "2. Is the probe labelled clearly enough that nobody can mistake it for full raw evidence?",
        "3. Does the full-run gate correctly reject the canary probe assets?",
        "4. Are P2 and P3 contracts, especially `len8` as a minimum full-phrase length gate, explicit enough?",
        "5. Are the output schemas sufficient for the later long-run review?",
        "6. What exact amendments are required before launching the real full raw build/run?",
        "7. Should the next long-run tranche build all requested assets at once, or complete independently reviewable cells first?",
        "",
        "Still forbidden before approval:",
        "",
        "- production scorer changes",
        "- sample/probe evidence presented as full raw",
        "- hidden candidate caps",
        "- hidden sample-line caps",
        "- silent backfill",
        "- phrase-internal windows",
        "- full long matrix launch before the reviewer approves the launcher/budget shape",
    ]
    (pack_dir / "10_context" / "review_questions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_review_summary(pack_dir: Path) -> None:
    asset = read_json(f"{ASSET_REL}/canary_probe_asset_summary_manifest.json")
    canary = read_json(f"{CANARY_REL}/canary_probe_manifest.json")
    full_gate_reasons = canary.get("full_run_gate_blocked_reasons", [])
    lines = [
        "# PhaseB N-Gram Hamming Pre-Long-Run External Review Summary - 2026-05-30",
        "",
        "## Decision Needed",
        "",
        "Approve or amend the next long-run preparation step. Do not treat this pack as approval to claim full raw scoring evidence.",
        "",
        "The completed canary probe proves that the workflow can build capped order-2/order-3 probe assets, summarise provenance, scan P2/P3 with the C++ backend, record the required diagnostics, and reject probe assets through the future full-run gate.",
        "",
        "## Canary Probe Result",
        "",
        f"- probe asset status: `{asset.get('status', 'not_run')}`",
        f"- canary status: `{canary.get('status', 'not_run')}`",
        f"- asset mode: `{asset.get('asset_mode', '')}`",
        f"- sample line limit per order: `{asset.get('sample_line_limit_per_order', '')}`",
        f"- full asset available: `{asset.get('full_asset_available', '')}`",
        f"- full raw rebuild confirmed: `{asset.get('full_raw_ngram_rebuild_confirmed', '')}`",
        f"- probe phrase entries: `{asset.get('phrase_entry_count', '')}`",
        f"- completed scan cells: `{canary.get('completed_scan_cells', '')}` / `{canary.get('expected_scan_cells', '')}`",
        f"- cuts: `{', '.join(str(v) for v in canary.get('cuts', []))}`",
        f"- orders: `{', '.join(str(v) for v in canary.get('orders', []))}`",
        f"- direction: `{canary.get('direction', '')}`",
        f"- backend implementation: `{canary.get('backend_impl', '')}`",
        f"- Python fallback allowed: `{canary.get('python_fallback_allowed', '')}`",
        f"- full-run gate on probe assets: `{canary.get('full_run_gate_on_probe_assets', '')}`",
        f"- total hits: `{canary.get('total_hit_count', '')}`",
        "",
        "## Full-Run Gate Evidence",
        "",
        "The future full-run gate rejected the canary probe assets, as intended:",
        "",
        "```text",
        *[str(reason) for reason in full_gate_reasons],
        "```",
        "",
        "## Length-Bias Warning",
        "",
        "P2/P3 whole-phrase scoring uses `min_phrase_token_length >= 8`.",
        "This is a minimum length gate, not fixed-length 8-rune scoring.",
        "An 8-rune phrase and a 20-rune phrase can both score, but they are not equivalent evidence.",
        "The 20-rune phrase is stricter in relative mismatch terms.",
        "",
        "```text",
        "scan_mode = whole_phrase_only",
        "internal_phrase_windows = false",
        "```",
        "",
        "P3 eligible phrase counts may equal P2 eligible phrase counts. The extra P3 rule is a hit-level short-word guard, so its effect is measured by P3-retained hits and P2-only hits rejected by P3.",
        "",
        "## Proposed Next Long-Run Shape",
        "",
        "Pending review, prepare a real full raw long-run tranche with:",
        "",
        "```text",
        "asset_mode = full",
        "sample_line_limit_per_order = none / absent",
        "direction = fwd",
        "cuts = normal, strict",
        "orders = 2, 3",
        "profiles = P2, P3",
        "exclude = P0, P1, rev, orders 4/5, phrase-internal windows, production scorer changes",
        "```",
        "",
        "The long-run launcher must declare a wallclock budget and stop condition, emit progress/ETA logs, write extractable partial outputs, and keep all paths repo-relative.",
        "",
        "## Reviewer Caution",
        "",
        "The canary probe timing is not valid long-run sizing evidence because it used capped probe assets. The next long-run setup must either use a same-family completed full cell or a written explicit estimate with margin before launching a multi-job matrix.",
        "",
        "## Still Forbidden",
        "",
        "- production scorer changes",
        "- sample/probe evidence presented as full raw",
        "- hidden candidate caps",
        "- hidden sample-line caps",
        "- silent backfill",
        "- phrase-internal windows",
        "- full long matrix launch before this pre-long-run review is approved",
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
    (pack_dir / "40_contract").mkdir(parents=True, exist_ok=True)

    copy_file("AGENTS.md", "10_context/AGENTS.md")
    copy_file(PLAN_REL, "10_context/active_plan.md")
    build_review_summary(pack_dir)
    build_review_questions(pack_dir)

    for name in (
        "build_phaseB_ngram_hamming_canary_probe_assets_v1.py",
        "summarise_phaseB_ngram_hamming_canary_probe_assets_v1.py",
        "run_phaseB_ngram_hamming_canary_probe_v1.py",
        "build_phaseB_ngram_hamming_canary_probe_review_pack_v1.py",
        "build_phaseB_ngram_hamming_pre_long_run_external_review_pack_v1.py",
        "build_phaseB_ngram_hamming_full_raw_assets_v1.py",
        "summarise_phaseB_ngram_hamming_full_raw_assets_v1.py",
        "run_phaseB_ngram_hamming_full_raw_canary_v1.py",
    ):
        copy_file(f"tools/benchmarks/periodic_sub_trans/no_wli/analysis/{name}", f"20_implementation/source/{name}")

    for name in (
        "reference.py",
        "fast_backend.py",
        "fast_bindings.cpp",
        "FastNgramHamming.h",
    ):
        copy_file(f"src/rune_decrypter_prime/scoring/ngram_hamming/{name}", f"40_contract/{name}")

    for name in (
        "test_phaseB_ngram_hamming_full_raw_asset_canary_v1.py",
    ):
        copy_file(f"tests/tools/{name}", f"20_implementation/tests/{name}")
    for name in (
        "test_reference_ngram_hamming.py",
        "test_fast_ngram_hamming_backend.py",
    ):
        copy_file(f"tests/scoring/ngram_hamming/{name}", f"20_implementation/tests/{name}")

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
