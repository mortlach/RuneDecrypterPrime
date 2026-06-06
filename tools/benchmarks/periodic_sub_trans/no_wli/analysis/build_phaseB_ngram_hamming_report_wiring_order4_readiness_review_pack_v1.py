from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_v1 as base,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_lane2b_post_review_pack_v1 as prior,
)


RUN_LABEL = "phaseB_ngram_hamming_report_wiring_order4_readiness_packaging_closed_review_pack_v1"
PACK_DIR_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "phaseB_ngram_hamming_report_wiring_order4_readiness_packaging_closed_review_pack_2026-06-04"
)
ZIP_REL = f"{PACK_DIR_REL}.zip"
ZIP_IDENTITY_REL = f"{ZIP_REL}.identity.json"
SUPERSEDED_ZIP_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "phaseB_ngram_hamming_report_wiring_order4_readiness_review_pack_2026-06-04.zip"
)
ORDER4_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_order4_build_readiness_hold_v1"
)
PORTABLE_REPRO_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_report_wiring_portable_pack_reproduction_v1"
)
LATEST_CONTEXT_REL = (
    "planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane2b_external_review_decision_2026-06-04.md",
    "planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_report_wiring_external_review_decision_2026-06-04.md",
    "planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_packaging_closed_unique_artifact_note_2026-06-04.md",
)
LATEST_COMPONENTS_REL = tuple(
    f"{ORDER4_DIR_REL}/{name}"
    for name in (
        "readiness_manifest.json",
        "abort_and_resume_contract.json",
        "partition_summary_rows.csv",
        "temporary_space_estimate_rows.csv",
        "readout.md",
    )
) + (
    f"{PORTABLE_REPRO_DIR_REL}/reproduction_manifest.json",
    f"{PORTABLE_REPRO_DIR_REL}/readout.md",
)
LATEST_SOURCE_REL = (
    "src/rune_decrypter_prime/scoring/retained_state.py",
    "src/rune_decrypter_prime/scoring/ngram_hamming/report_only_telemetry.py",
    "tools/benchmarks/periodic_sub_trans/common/scorer_sidecar.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_order4_build_readiness_hold_v1.py",
    "tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_report_wiring_order4_readiness_review_pack_v1.py",
)
LATEST_TESTS_REL = (
    "tests/scoring/ngram_hamming/test_report_only_telemetry.py",
    "tests/scoring/test_retained_state_plaintext_rescore.py",
    "tests/tools/test_benchmark_scorer_report_sidecar_smoke.py",
    "tests/tools/test_phaseB_ngram_hamming_order4_build_readiness_hold_v1.py",
)
FULL_REPO_DEPENDENT_TESTS_REL = (
    "tests/scoring/test_retained_state_plaintext_rescore.py",
    "tests/tools/test_benchmark_scorer_report_sidecar_smoke.py",
)
FULL_REPO_VERIFICATION_RESULT = "107 passed"
FOCUSED_VERIFICATION_RESULT = "35 passed"
PORTABLE_PACK_VERIFICATION_RESULT = "81 passed, 15 skipped without optional C++ extension"


def write_review_summary(path: Path, manifest: dict[str, Any]) -> None:
    base.ensure_under_repo(path)
    lines = [
        "# Report Wiring And Order-4 Readiness Review Summary",
        "",
        f"- status: `{manifest['status']}`",
        f"- report wiring status: `{manifest['report_wiring_status']}`",
        f"- report wiring rank effect: `{manifest['report_wiring_rank_effect']}`",
        f"- full repo verification: `{manifest['full_repo_verification_result']}`",
        f"- focused verification: `{manifest['focused_verification_result']}`",
        f"- portable pack verification: `{manifest['portable_pack_verification_result']}`",
        f"- portable extracted-pack reproduction: `{manifest['portable_pack_reproduction_status']}`",
        f"- full-repo-dependent included tests: `{len(manifest['full_repo_dependent_test_files'])}`",
        f"- order-4 readiness status: `{manifest['order4_readiness_status']}`",
        f"- order-4 full build approved: `{manifest['order4_full_build_approved']}`",
        f"- zip size reporting: `{manifest.get('zip_size_reporting', 'pending')}`",
        "",
        "This pack requests review of actual opt-in report/export wiring and the",
        "separate machine-readable order-4 build hold. It requests no production",
        "scoring/ranking authority and no order-4 full-build approval.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_test_scope(path: Path, manifest: dict[str, Any]) -> None:
    base.ensure_under_repo(path)
    lines = [
        "# Review Pack Test Scope",
        "",
        f"- full repo verification: `{manifest['full_repo_verification_result']}`",
        f"- focused verification: `{manifest['focused_verification_result']}`",
        f"- portable review-pack verification: `{manifest['portable_pack_verification_result']}`",
        "",
        "The portable result applies only to the files listed in",
        "`portable_test_scope.json`. Those files are duplicated under",
        "`30_source/tests` so normal pytest discovery from `30_source` needs no",
        "full-repo source tree or `PYTHONPATH`. The following valuable integration",
        "tests remain in `40_tests` for review but require the full repo source tree:",
        "",
        *[f"- `{name}`" for name in manifest["full_repo_dependent_test_files"]],
        "",
        "The reduced pack does not claim that every included test is independently",
        "collectable without the full repo.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_portable_pytest_config(path: Path) -> None:
    base.ensure_under_repo(path)
    path.write_text(
        "\n".join(
            (
                "[pytest]",
                "testpaths = tests",
                "pythonpath = src .",
                "markers =",
                "    tier_a: fast/default gate tests",
                "    cuda: tests requiring CUDA runtime",
                "addopts = -ra",
                "",
            )
        ),
        encoding="utf-8",
    )


def write_portable_test_package_markers(pack_dir: Path) -> None:
    for relative_path in ("30_source/tests/__init__.py", "30_source/tests/tools/__init__.py"):
        path = pack_dir / relative_path
        base.ensure_under_repo(path)
        path.write_text("", encoding="utf-8")


def build_review_pack() -> dict[str, Any]:
    readiness_manifest = json.loads(
        (base.REPO_ROOT / ORDER4_DIR_REL / "readiness_manifest.json").read_text(encoding="utf-8")
    )
    if readiness_manifest.get("status") != "hold_not_approved":
        raise RuntimeError("order-4 readiness evidence must remain on hold")
    if readiness_manifest.get("full_build_approved") is not False:
        raise RuntimeError("order-4 full build must not be approved by this pack")

    original_context = base.CONTEXT_FILES_REL
    original_components = base.COMPONENT_FILES_REL
    original_source = base.SOURCE_FILES_REL
    original_tests = base.TEST_FILES_REL
    try:
        base.CONTEXT_FILES_REL = (
            *original_context,
            *prior.ADDITIONAL_CONTEXT_REL,
            *LATEST_CONTEXT_REL,
        )
        base.COMPONENT_FILES_REL = (
            *original_components,
            *prior.ADDITIONAL_COMPONENTS_REL,
            *LATEST_COMPONENTS_REL,
        )
        base.SOURCE_FILES_REL = (
            *original_source,
            *prior.ADDITIONAL_SOURCE_REL,
            *LATEST_SOURCE_REL,
        )
        base.TEST_FILES_REL = (
            *original_tests,
            *prior.ADDITIONAL_TESTS_REL,
            *LATEST_TESTS_REL,
        )
        manifest = base.build_lane2_gated_diagnostic_evidence_review_pack(
            pack_dir=base.REPO_ROOT / PACK_DIR_REL,
            zip_path=base.REPO_ROOT / ZIP_REL,
        )
    finally:
        base.CONTEXT_FILES_REL = original_context
        base.COMPONENT_FILES_REL = original_components
        base.SOURCE_FILES_REL = original_source
        base.TEST_FILES_REL = original_tests

    manifest.update(
        {
            "run_label": RUN_LABEL,
            "artifact_identity": "packaging_closed_unique_filename",
            "supersedes_zip_path": SUPERSEDED_ZIP_REL,
            "superseded_zip_must_not_be_sent": True,
            "report_wiring_status": "implemented_report_export_only",
            "report_wiring_opt_in": True,
            "report_wiring_default_effect": "absent_without_explicit_config",
            "report_wiring_rank_effect": "none",
            "full_repo_verification_result": FULL_REPO_VERIFICATION_RESULT,
            "focused_verification_result": FOCUSED_VERIFICATION_RESULT,
            "portable_pack_verification_result": PORTABLE_PACK_VERIFICATION_RESULT,
            "portable_pack_reproduction_status": "portable_scope_reproduced",
            "developer_test_result": FULL_REPO_VERIFICATION_RESULT,
            "report_wiring_focused_test_result": FOCUSED_VERIFICATION_RESULT,
            "portable_test_result": PORTABLE_PACK_VERIFICATION_RESULT,
            "order4_readiness_status": readiness_manifest["status"],
            "order4_full_build_approved": readiness_manifest["full_build_approved"],
            "production_scorer_change": False,
            "production_ranking_change": False,
        }
    )
    all_included_tests = tuple(
        dict.fromkeys((*base.TEST_FILES_REL, *prior.ADDITIONAL_TESTS_REL, *LATEST_TESTS_REL))
    )
    portable_test_files = tuple(
        path for path in all_included_tests if path not in FULL_REPO_DEPENDENT_TESTS_REL
    )
    manifest["portable_test_scope"] = "explicit_reduced_pack_subset"
    manifest["portable_test_files"] = list(portable_test_files)
    manifest["full_repo_dependent_test_files"] = list(FULL_REPO_DEPENDENT_TESTS_REL)
    manifest["all_included_tests_portable"] = False
    manifest["portable_test_layout"] = "duplicated_under_30_source_for_normal_pytest_discovery"
    pack_dir = base.REPO_ROOT / PACK_DIR_REL
    zip_path = base.REPO_ROOT / ZIP_REL
    portable_copy_rows = [
        base.copy_file(path, pack_dir, "30_source")
        for path in portable_test_files
    ]
    portable_copy_missing = [row["source_path"] for row in portable_copy_rows if not row["exists"]]
    if portable_copy_missing:
        raise RuntimeError(f"portable test copies missing: {portable_copy_missing}")
    manifest["copied_files"].extend(portable_copy_rows)
    write_portable_pytest_config(pack_dir / "30_source" / "pytest.ini")
    write_portable_test_package_markers(pack_dir)
    write_review_summary(pack_dir / "10_context" / "review_summary.md", manifest)
    write_test_scope(pack_dir / "10_context" / "test_scope.md", manifest)
    base.write_json(
        pack_dir / "10_context" / "portable_test_scope.json",
        {
            "scope": manifest["portable_test_scope"],
            "result": manifest["portable_pack_verification_result"],
            "portable_test_files": manifest["portable_test_files"],
            "full_repo_dependent_test_files": manifest["full_repo_dependent_test_files"],
            "all_included_tests_portable": False,
            "portable_test_layout": manifest["portable_test_layout"],
        },
    )
    base.write_json(pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    entry_count, backslash_entries = base.make_zip(pack_dir, zip_path)
    manifest["entry_count"] = entry_count
    manifest["backslash_entries"] = backslash_entries
    manifest["zip_size_reporting"] = "external_identity_sidecar_avoids_self_reference"
    write_review_summary(pack_dir / "10_context" / "review_summary.md", manifest)
    write_test_scope(pack_dir / "10_context" / "test_scope.md", manifest)
    base.write_json(pack_dir / "PACK_BUILD_SUMMARY.json", manifest)
    entry_count, backslash_entries = base.make_zip(pack_dir, zip_path)
    observed_zip_size = zip_path.stat().st_size
    if observed_zip_size > base.MAX_ZIP_BYTES:
        raise RuntimeError("review pack exceeds hard compressed-size limit")
    zip_sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    identity = {
        "artifact_identity": manifest["artifact_identity"],
        "zip_path": ZIP_REL,
        "zip_size_bytes": observed_zip_size,
        "zip_sha256": zip_sha256,
        "entry_count": entry_count,
        "backslash_entries": backslash_entries,
        "supersedes_zip_path": SUPERSEDED_ZIP_REL,
        "superseded_zip_must_not_be_sent": True,
    }
    base.write_json(base.REPO_ROOT / ZIP_IDENTITY_REL, identity)
    manifest["zip_size_bytes"] = observed_zip_size
    manifest["zip_sha256"] = zip_sha256
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] entry_count={entry_count} zip_size_bytes={manifest['zip_size_bytes']}")
    return manifest


def main() -> None:
    build_review_pack()


if __name__ == "__main__":
    main()
