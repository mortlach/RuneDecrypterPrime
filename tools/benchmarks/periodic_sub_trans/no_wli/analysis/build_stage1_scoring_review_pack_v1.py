from __future__ import annotations

"""
Build a self-contained review pack for the Stage 1 scoring investigation.

Repo-local automation scripts in this repository intentionally use hardcoded
configuration rather than CLI arguments.
"""

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


RUN_LABEL = "stage1_scoring_investigation_review_pack_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/review_packs/"
    "stage1_scoring_investigation_review_pack_v1"
)
STAGING_DIR_NAME = "stage1_scoring_investigation_review_pack_v1"
ZIP_NAME = "stage1_scoring_investigation_review_pack_v1.zip"


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "AGENTS.md").exists() and (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


REPO_ROOT = _find_repo_root()
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL
STAGING_DIR = OUTPUT_DIR / STAGING_DIR_NAME
ZIP_PATH = OUTPUT_DIR / ZIP_NAME


SOURCE_FILES_REL = [
    "AGENTS.md",
    "planning/projects/no_wli/40_review_summaries/span_hamming_stage2_fixed500_summary_2026-05-03.md",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_span_hamming_500_normalized_canary_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_span_hamming_500_normalized_full_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/inspect_span_hamming_500_pattern_examples_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/sweep_span_hamming_500_composite_rules_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_span_hamming_500_len8_hd_buckets_canary_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_span_hamming_500_len8_hd_buckets_full_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_span_hamming_500_length_hd_fingerprint_canary_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_span_hamming_500_length_hd_fingerprint_full_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/sweep_span_hamming_500_fingerprint_noise_composites_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/sweep_span_hamming_500_fingerprint_noise_word_ngram_composites_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/sweep_span_hamming_500_robust_composite_space_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/audit_scorer_component_features_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/audit_scorer_component_contracts_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/audit_word_ngram_support_thresholds_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_stage1_scoring_review_pack_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/word_ngram_report.py",
    "src/rune_decrypter_prime/scoring/span_hamming/types.py",
    "src/rune_decrypter_prime/scoring/span_hamming/backend.py",
    "src/rune_decrypter_prime/scoring/span_hamming/fast_backend.py",
    "src/rune_decrypter_prime/scoring/span_hamming/FastSpanHamming.h",
    "src/rune_decrypter_prime/scoring/span_hamming/fast_bindings.cpp",
    "src/rune_decrypter_prime/scoring/word_ngrams/__init__.py",
    "src/rune_decrypter_prime/scoring/word_ngrams/in_memory.py",
    "src/rune_decrypter_prime/scoring/word_ngrams/runtime.py",
    "src/rune_decrypter_prime/scoring/word_ngrams/scorer.py",
    "src/rune_decrypter_prime/scoring/word_ngrams/sqlite_model.py",
    "tests/tools/test_no_wli_span_hamming_500_normalized_canary_v1.py",
    "tests/tools/test_no_wli_span_hamming_500_len8_hd_buckets_v1.py",
    "tests/tools/test_no_wli_span_hamming_500_length_hd_fingerprint_v1.py",
    "tests/tools/test_no_wli_span_hamming_500_fingerprint_noise_composites_v1.py",
    "tests/tools/test_no_wli_span_hamming_500_fingerprint_noise_word_ngram_composites_v1.py",
    "tests/tools/test_no_wli_span_hamming_500_robust_composite_space_v1.py",
    "tests/tools/test_no_wli_word_ngram_support_thresholds_v1.py",
    "tests/scoring/span_hamming/test_span_hamming_backend.py",
    "tests/scoring/span_hamming/test_fast_span_hamming_backend.py",
    "tests/scoring/word_ngrams/test_in_memory.py",
    "tests/scoring/word_ngrams/test_sqlite_model.py",
]


RESULT_DIRS_REL = [
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_normalized_canary_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_normalized_full_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_pattern_examples_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_composite_rules_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_len8_hd_buckets_canary_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_len8_hd_buckets_full_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_length_hd_fingerprint_canary_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_length_hd_fingerprint_full_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_fingerprint_noise_composites_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_fingerprint_noise_word_ngram_composites_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/word_ngram_support_thresholds_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/scorer_component_inventory_v1",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/scorer_component_contract_audit_v1",
]


RESULT_FILES_REL = [
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/scorer_component_feature_audit_v1/scorer_component_feature_audit_readout.md",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/scorer_component_feature_audit_v1/scorer_component_feature_audit_summary.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/scorer_component_feature_audit_v1/scorer_component_feature_audit_candidate_features.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/scorer_component_feature_audit_v1/scorer_component_feature_audit_feature_summary.csv",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/scorer_component_feature_audit_v1/scorer_component_feature_audit_missingness.csv",
]


README_TEXT = """# Stage 1 Scoring Investigation Review Pack

This pack is self-contained for reviewing the report-only Stage 1 scoring investigation around fixed-500 span-Hamming features, length/HD fingerprints, and word-ngram support.

## Start Here

1. Read `00_INITIAL_REVIEW_REQUEST_MESSAGE.md` for the suggested reviewer-facing request.
2. Read `01_REVIEWER_OVERVIEW_AND_STATUS.md` for the current interpretation and completed-vs-planned status.
3. Read `repo_files/planning/projects/no_wli/40_review_summaries/span_hamming_stage2_fixed500_summary_2026-05-03.md` for the live planning note.
4. Inspect result readouts in `repo_files/output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/*/*readout.md`.
5. Use `02_PARSE_INSTRUCTIONS.md` for CSV/JSON interpretation.

## Scope

- This is a review pack, not a runtime patch proposal.
- The included scans are report-only; they did not change production scoring behaviour.
- The main question is whether the observed scoring signals are robust enough to justify a next validation stage, not whether to immediately promote them into Phase-C.

## Repro Notes

The repo rule for helper scripts is no CLI arguments. To rerun a script, edit hardcoded constants in the source file if needed, then run it directly from the repository root.

Tests most relevant to this pack:

```powershell
py -3.11 -m pytest tests\\tools\\test_no_wli_span_hamming_500_normalized_canary_v1.py tests\\tools\\test_no_wli_span_hamming_500_len8_hd_buckets_v1.py tests\\tools\\test_no_wli_span_hamming_500_length_hd_fingerprint_v1.py tests\\tools\\test_no_wli_span_hamming_500_fingerprint_noise_composites_v1.py tests\\tools\\test_no_wli_span_hamming_500_fingerprint_noise_word_ngram_composites_v1.py tests\\tools\\test_no_wli_word_ngram_support_thresholds_v1.py
```

## What Is Not Included

- The wider word-ngram SQLite asset does not exist locally; only the 64-book phase2 SQLite was found.
- The huge scorer-component pair-feature tables are omitted. The candidate/features/readout/summary files are included.
- The timed-out broad robust composite run is included as source only; it is not counted as completed evidence.
"""


OVERVIEW_TEXT = """# Reviewer Overview And Status

## Current Best Read

The strongest signal so far is not a single word-count rule. It is a composite scoring family:

- fixed 500-token chunks,
- normalized medium/long span-Hamming support,
- a penalty for short fuzzy matches/noise,
- optional word-ngram trust as a side channel over exact selected word-token sequences.

Best completed report-only rows:

- Span-only composite: `selected_exact_span_minus_noise_lam0p75`, middle chunk, 470 rescues / 246 breaks, net +224.
- Span + word-ngram trust composite: `selected_exact_span_noise_plus_word_ngram_trust_lam0p75_w0p25`, middle chunk, 468 rescues / 214 breaks, net +254.
- Word-ngram support threshold alone: `n_positions` at min_positions 12, 94 rescues / 6 breaks, net +88.

The main caveat is split instability. The best span + word-ngram composite is even-seed net -50 and odd-seed net +304. That makes the signal promising but not promotion-ready.

## Completed Evidence

- Fixed-500 normalized span-Hamming full scan: 604 token hashes, 1812 chunks, 2594 pairs, 5 configs, 9060 scores.
- Len-8 HD bucket canary and full scan: weak direct value; high-HD buckets can be cap-shaped.
- Length/HD fingerprint canary and full scan over lengths 6-10, max_hd=length-3, cap100000: feasible and uncapped, but direct rows are modest.
- Fingerprint + short-noise composite sweep: improves net to +224.
- Fingerprint + short-noise + word-ngram trust sweep: improves net to +254, mainly by reducing breaks.
- Word-ngram support threshold audit: min_positions=12 is best direct threshold; raw xent/miss-rate does not currently add direct value.
- FastSpanHamming-backed lexical extraction canary: about 604 lexical reports in 56 seconds, much faster than the earlier slow extraction profile.

## Planned / Not Complete

- Proper grouped validation beyond even/odd seed split.
- Determine whether even-seed counter-signal is fixture-family artifact or true rule failure.
- Wider word-ngram asset comparison. No wider SQLite exists locally yet, so building one needs a canary/budget.
- Joint validation before any Phase-C decision-influencing change.

## Review Questions

- Is there evidence of leakage, overfitting, or fixture-family confounding in the pairwise setup?
- Is the even/odd split instability enough to reject the composite, or should it be grouped more carefully first?
- Should word-ngram support be retained only as a trust/side-channel feature?
- What is the smallest next validation run that can falsify the current composite interpretation?
"""


PARSE_TEXT = """# Parse Instructions For Reviewers

All paths below are inside `repo_files/` in this zip.

## Recommended Reading Order

1. `planning/projects/no_wli/40_review_summaries/span_hamming_stage2_fixed500_summary_2026-05-03.md`
2. `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_normalized_full_v1/span_hamming_500_normalized_readout.md`
3. `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_fingerprint_noise_composites_v1/span_hamming_500_fingerprint_noise_composite_readout.md`
4. `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_fingerprint_noise_word_ngram_composites_v1/span_hamming_500_fingerprint_noise_word_ngram_composite_readout.md`
5. `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/word_ngram_support_thresholds_v1/word_ngram_support_readout.md`

## Common CSV Fields

- `rescues`: pair cases where the current/control score picked the challenger but the investigated feature prefers the true winner.
- `breaks`: pair cases where the current/control score picked the true winner but the investigated feature prefers the challenger.
- `net`: `rescues - breaks`.
- `tie`: pair cases where the investigated feature gives no preference.
- `current_misranked_pair_count`: denominator for possible rescues under the current/control score.
- `current_correct_control_pair_count`: denominator for possible breaks under the current/control score.
- `chunk_kind`: fixed 500-token segment, usually `prefix`, `middle`, or `suffix`.
- `agg`: aggregator over chunks or repeated rule rows, depending on the sweep.

## Important Result Files

- `span_hamming_500_normalized_full_v1/*pair_feature_summary.csv`: baseline direct normalized span-Hamming feature comparisons.
- `span_hamming_500_len8_hd_buckets_full_v1/*pair_summary.csv`: len-8 HD bucket results.
- `span_hamming_500_length_hd_fingerprint_full_v1/*pair_summary.csv`: length/HD fingerprint results.
- `span_hamming_500_fingerprint_noise_composites_v1/*summary.csv`: span/fingerprint/noise composite sweep.
- `span_hamming_500_fingerprint_noise_word_ngram_composites_v1/*summary.csv`: composite sweep with word-ngram trust/xent/miss variants.
- `word_ngram_support_thresholds_v1/word_ngram_support_feature_summary.csv`: direct word-ngram support-threshold evidence.
- `*_split_validation.csv`: split checks. Treat these as critical because the best rows are not stable across fixture seed parity.

## Interpretation Guardrails

- Do not treat inactive word-ngram as bad-language evidence. It is missing/no-decision evidence.
- Do not treat high direct net as promotion-ready without split validation.
- The broad robust composite source is included, but its attempted run timed out and is not completed evidence.
- Wider word-ngram asset comparison has not been run.
"""


MESSAGE_TEXT = """Subject: Review request - Stage 1 scoring investigation pack

Hi,

Please review the attached Stage 1 scoring investigation pack for the no-WLI scoring work. The pack is self-contained and includes the relevant source scripts/tests, selected result artifacts, a status overview, and parse instructions.

The headline finding is that fixed-500 span-Hamming evidence becomes much more useful when treated as a composite signal: medium/long exact-ish span support minus short fuzzy noise, with word-ngram trust as a possible side channel. The best report-only composite reaches net +254 on the historical pair set, but it is not promotion-ready because the split validation is unstable, especially even-seed net -50 versus odd-seed net +304.

What I need reviewed:

- whether the pairwise scoring evidence looks overfit or confounded,
- whether the even/odd fixture split invalidates the current composite or just demands grouped validation,
- whether word-ngram support should remain only a trust/side-channel feature,
- what the smallest next validation run should be before any Phase-C scoring change.

Start with `README_FOR_REVIEWERS.md`, then `01_REVIEWER_OVERVIEW_AND_STATUS.md`, then the planning summary under `repo_files/planning/...`.
"""


def _repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _assert_under_repo(path: Path) -> None:
    resolved = path.resolve()
    root = REPO_ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise RuntimeError("path escapes repo root: " + str(path))


def _reset_output() -> None:
    _assert_under_repo(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if STAGING_DIR.exists():
        _assert_under_repo(STAGING_DIR)
        shutil.rmtree(STAGING_DIR)
    if ZIP_PATH.exists():
        _assert_under_repo(ZIP_PATH)
        ZIP_PATH.unlink()
    STAGING_DIR.mkdir(parents=True, exist_ok=True)


def _copy_file(rel_path: str, copied: list[dict[str, object]], missing: list[str]) -> None:
    src = REPO_ROOT / rel_path
    if not src.exists() or not src.is_file():
        missing.append(rel_path)
        return
    dst = STAGING_DIR / "repo_files" / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append({"path": rel_path, "bytes": int(src.stat().st_size), "kind": "file"})


def _copy_dir(rel_path: str, copied: list[dict[str, object]], missing: list[str]) -> None:
    src_dir = REPO_ROOT / rel_path
    if not src_dir.exists() or not src_dir.is_dir():
        missing.append(rel_path)
        return
    for src in sorted(path for path in src_dir.rglob("*") if path.is_file()):
        rel = _repo_rel(src)
        dst = STAGING_DIR / "repo_files" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append({"path": rel, "bytes": int(src.stat().st_size), "kind": "file"})


def _write_text_files() -> None:
    (STAGING_DIR / "README_FOR_REVIEWERS.md").write_text(README_TEXT, encoding="utf-8")
    (STAGING_DIR / "00_INITIAL_REVIEW_REQUEST_MESSAGE.md").write_text(MESSAGE_TEXT, encoding="utf-8")
    (STAGING_DIR / "01_REVIEWER_OVERVIEW_AND_STATUS.md").write_text(OVERVIEW_TEXT, encoding="utf-8")
    (STAGING_DIR / "02_PARSE_INSTRUCTIONS.md").write_text(PARSE_TEXT, encoding="utf-8")


def _write_manifest(copied: list[dict[str, object]], missing: list[str]) -> None:
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root_name": REPO_ROOT.name,
        "staging_dir": _repo_rel(STAGING_DIR),
        "zip_path": _repo_rel(ZIP_PATH),
        "copied_file_count": len(copied),
        "copied_total_bytes": sum(int(row["bytes"]) for row in copied),
        "copied_files": copied,
        "missing_requested_paths": missing,
        "notes": [
            "Pack is report-only evidence for review.",
            "Huge scorer-component pair-feature tables are intentionally omitted.",
            "No wider word-ngram SQLite asset was found locally.",
        ],
    }
    (STAGING_DIR / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _zip_staging() -> None:
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src in sorted(path for path in STAGING_DIR.rglob("*") if path.is_file()):
            zf.write(src, src.relative_to(STAGING_DIR.parent).as_posix())


def build_pack() -> dict[str, object]:
    _reset_output()
    copied: list[dict[str, object]] = []
    missing: list[str] = []
    _write_text_files()
    for rel_path in SOURCE_FILES_REL:
        _copy_file(rel_path, copied, missing)
    for rel_path in RESULT_FILES_REL:
        _copy_file(rel_path, copied, missing)
    for rel_path in RESULT_DIRS_REL:
        _copy_dir(rel_path, copied, missing)
    _write_manifest(copied, missing)
    _zip_staging()
    summary = {
        "run_label": RUN_LABEL,
        "output_dir": _repo_rel(OUTPUT_DIR),
        "staging_dir": _repo_rel(STAGING_DIR),
        "zip_path": _repo_rel(ZIP_PATH),
        "zip_bytes": int(ZIP_PATH.stat().st_size),
        "copied_file_count": len(copied),
        "missing_requested_paths": missing,
    }
    (OUTPUT_DIR / "build_summary.json").write_text(
        json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True), flush=True)
    return summary


def main() -> None:
    build_pack()


if __name__ == "__main__":
    main()
