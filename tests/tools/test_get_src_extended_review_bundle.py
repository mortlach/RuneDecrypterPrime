from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest

from tools import get_src_extended_review_bundle as bundle_mod

pytestmark = pytest.mark.tier_a


def _write(path: Path, content: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_make_get_src_extended_review_bundle_includes_review_inputs_without_bloat(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    src_root = repo_root / "src"
    test_root = repo_root / "tests"
    benchmark_root = repo_root / "tools" / "benchmarks"
    tools_get_src_zip_root = repo_root / "tools" / "get_src_zip"
    planning_working_root = repo_root / "planning" / "working"
    no_wli_output_root = (
        repo_root
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
    )
    zip_path = repo_root / "output" / "tools" / "bundle" / "review.zip"

    _write(repo_root / "AGENTS.md", "# rules\n")
    _write(repo_root / "README.md", "# readme\n")
    _write(repo_root / "requirements.txt", "pytest\n")
    _write(src_root / "rune_decrypter_prime" / "core.py", "print('ok')\n")
    _write(src_root / "rune_decrypter_prime" / "data" / "huge.bin", "NOPE")
    _write(test_root / "tools" / "test_core.py", "def test_ok():\n    pass\n")
    _write(benchmark_root / "README.md", "# bench\n")
    _write(benchmark_root / "periodic_sub_trans" / "no_wli" / "runner.py", "# run\n")
    _write(benchmark_root / "other" / "skip.py", "# skip\n")
    _write(tools_get_src_zip_root / "get_src_extended.py", "# old tool\n")
    _write(planning_working_root / "no_wli_science_run_log_2026-03-26.md", "# log\n")
    _write(
        planning_working_root
        / "no_wli_external_review_pack_2026-03-30"
        / "nested.txt",
        "NOPE\n",
    )
    _write(no_wli_output_root / "fixture_matrix_run_state_demo.json", "{}\n")
    _write(
        no_wli_output_root
        / "20260403T000000Z__bench_solve_pipeline_no_wli__demo"
        / "final_instances"
        / "fixture_fixture_001_p5_c1_l1000__text0__seed511.json",
        "{}\n",
    )
    _write(no_wli_output_root / "analysis" / "space_map_v1_atlas" / "summary.json", "{}\n")
    _write(no_wli_output_root / "skip.zip", "NOPE")

    summary = bundle_mod.make_get_src_extended_review_bundle(
        repo_root=repo_root,
        src_root=src_root,
        test_root=test_root,
        benchmark_root=benchmark_root,
        tools_get_src_zip_root=tools_get_src_zip_root,
        planning_working_root=planning_working_root,
        no_wli_output_root=no_wli_output_root,
        output_root=zip_path.parent,
        zip_path_override=zip_path,
        root_files=(
            repo_root / "AGENTS.md",
            repo_root / "README.md",
            repo_root / "requirements.txt",
        ),
    )

    assert zip_path.exists()
    assert int(summary["included_files_count"]) >= 9
    assert int(summary["excluded_entries_count"]) >= 3

    with ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())

    assert "AGENTS.md" in names
    assert "README.md" in names
    assert "requirements.txt" in names
    assert "src/rune_decrypter_prime/core.py" in names
    assert "tests/tools/test_core.py" in names
    assert "tools/benchmarks/README.md" in names
    assert "tools/benchmarks/periodic_sub_trans/no_wli/runner.py" in names
    assert "tools/get_src_zip/get_src_extended.py" in names
    assert "planning/working/no_wli_science_run_log_2026-03-26.md" in names
    assert "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_demo.json" in names
    assert (
        "output/tools/benchmarks/periodic_sub_trans/no_wli/20260403T000000Z__bench_solve_pipeline_no_wli__demo/final_instances/fixture_fixture_001_p5_c1_l1000__text0__seed511.json"
        in names
    )
    assert (
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/summary.json"
        in names
    )

    assert "src/rune_decrypter_prime/data/huge.bin" not in names
    assert "tools/benchmarks/other/skip.py" not in names
    assert (
        "planning/working/no_wli_external_review_pack_2026-03-30/nested.txt"
        not in names
    )
    assert "output/tools/benchmarks/periodic_sub_trans/no_wli/skip.zip" not in names
