from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

from setuptools import find_packages


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
OLD_PACKAGE = "rune_" + "decrypter_prime"

ACTIVE_DOCUMENTS = (
    "README.md",
    "src/README.md",
    "src/rdp/README.md",
    "src/rdp/api/README.md",
    "cipher_development/README.md",
    "solving/README.md",
    "docs/architecture/interruptors.md",
    "docs/architecture/overview.md",
    "docs/guides/architecture.md",
    "docs/guides/documentation_playbook.md",
    "docs/guides/extending_hands_on_to_experts.md",
    "docs/guides/hamming_scorer.md",
    "docs/guides/outputs.md",
    "docs/guides/philosophy.md",
    "docs/guides/span_hamming_scorer.md",
    "docs/guides/troubleshooting.md",
    "docs/howto/add_cipher.md",
    "docs/howto/add_solver.md",
    "docs/repo/structure.md",
    "docs/setup/building.md",
    "docs/tests_docs/tools.md",
    "v1_docs/01_SOURCE_MAP.md",
    "v1_docs/coder/cipher_pipeline.md",
    "v1_docs/coder/docstring_policy.md",
    "v1_docs/coder/extension_points.md",
    "v1_docs/coder/key_pipeline.md",
    "v1_docs/coder/module_map.md",
    "v1_docs/coder/README.md",
    "v1_docs/coder/scoring_pipeline.md",
    "v1_docs/coder/solver_pipeline.md",
    "v1_docs/coder/stability_and_internals.md",
    "v1_docs/coder/telemetry_and_reports.md",
    "v1_docs/howto/add_cipher.md",
    "v1_docs/howto/add_scorer_lane.md",
    "v1_docs/howto/add_solver.md",
    "v1_docs/reference/artifacts.md",
    "v1_docs/reference/reports.md",
)

NEGATIVE_EXECUTABLE_EVIDENCE = {
    "tests/contracts/test_a5_keyops_registry_contract.py",
    "tests/contracts/test_d7_final_summary_doc.py",
    "tests/core/engine/test_engine_ownership_contract.py",
    "tests/core/test_no_dead_config_shim_imports.py",
    "tests/data/test_book_corpus.py",
    "tests/meta/test_d3_contract_sweep.py",
    "tests/scoring/test_scoring_package_import_policy.py",
    "tests/solvers/test_solver_package_import_policy.py",
    "tests/tutorials/test_v1_migration_dataflow_contracts.py",
    "tools/ci/a5_artifact_contract.py",
    "tools/ci/a5_installed_wheel_smoke.py",
}

HISTORICAL_OLD_PATH_EVIDENCE = {
    "docs/release_contracts/v1/D7_FINAL_SUMMARY.md",
    "docs/release_contracts/v1/V1_AUTHORITY_AND_DECISIONS.md",
    "docs/release_contracts/v1/core_runtime_config_contract.md",
    "docs/release_contracts/v1/d3_numpy_strict_requested_lanes.md",
    "docs/release_contracts/v1/d3_stage_overlays/d3_1_2_capability_gate_overlay.md",
    "docs/release_contracts/v1/d3_stage_overlays/d3_3_scorer_lane_report_overlay.md",
    "docs/release_contracts/v1/d3_stage_overlays/d3_4_numpy_builder_wiring_overlay.md",
    "docs/release_contracts/v1/d3_stage_overlays/d3_6_solver_report_scorer_lanes_overlay.md",
    "docs/release_contracts/v1/d3_stage_overlays/d3_7_targeted_contract_sweep_overlay.md",
    "docs/release_contracts/v1/final_source_to_wp_decision_target_test_chain.csv",
    "docs/release_contracts/v1/v1_cleanup_deprecation_ledger.json",
}


def _project_files(*roots: str) -> list[Path]:
    files: list[Path] = []
    for root_name in roots:
        root = ROOT / root_name
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(path for path in root.rglob("*") if path.is_file())
    return files


def test_source_tree_and_package_discovery_are_rdp_only() -> None:
    assert not (SRC / OLD_PACKAGE).exists()
    packages = set(find_packages(where=str(SRC)))
    assert packages
    assert {name.split(".", 1)[0] for name in packages} == {"rdp"}
    assert "rdp.utils" not in packages
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["setuptools"]["packages"]["find"]["include"] == ["rdp*"]


def test_old_package_is_not_import_discoverable_from_source() -> None:
    script = "\n".join(
        (
            "from importlib.machinery import PathFinder",
            "import rdp",
            "from rdp import api",
            "assert rdp.__all__ == ['api']",
            "assert api.__name__ == 'rdp.api'",
            f"assert PathFinder.find_spec({OLD_PACKAGE!r}, [{str(SRC)!r}]) is None",
        )
    )
    launch = f"import sys\nsys.path.insert(0, {str(SRC)!r})\n{script}"
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", launch],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_retained_executable_old_path_text_is_exact_negative_evidence() -> None:
    found = {
        path.relative_to(ROOT).as_posix()
        for path in _project_files(
            "src",
            "tests",
            "tutorials/v1",
            "solving",
            "cipher_development",
            "tools",
            ".github",
            "setup.py",
            "pyproject.toml",
            "MANIFEST.in",
        )
        if path.suffix.lower() not in {".pyc", ".pyd", ".so"}
        and not any(part.endswith(".egg-info") for part in path.parts)
        and OLD_PACKAGE in path.read_text(encoding="utf-8", errors="ignore")
    }
    assert found == NEGATIVE_EXECUTABLE_EVIDENCE


def test_active_documentation_contains_no_old_package_path() -> None:
    missing = [path for path in ACTIVE_DOCUMENTS if not (ROOT / path).is_file()]
    assert missing == []
    offenders = [
        path
        for path in ACTIVE_DOCUMENTS
        if OLD_PACKAGE in (ROOT / path).read_text(encoding="utf-8", errors="strict")
    ]
    assert offenders == []


def test_historical_old_path_text_is_exactly_allowlisted() -> None:
    found = {
        path.relative_to(ROOT).as_posix()
        for path in _project_files("docs", "v1_docs")
        if OLD_PACKAGE in path.read_text(encoding="utf-8", errors="ignore")
    }
    assert found == HISTORICAL_OLD_PATH_EVIDENCE
