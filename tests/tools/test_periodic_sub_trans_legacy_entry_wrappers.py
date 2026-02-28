from __future__ import annotations

import py_compile
from pathlib import Path

import pytest


pytestmark = pytest.mark.tier_a


_WRAPPERS = {
    "tools/benchmarks/bench_solve_periodic_columnar_pipeline_no_wli.py":
        "tools.benchmarks.periodic_sub_trans.no_wli.runner",
    "tools/benchmarks/bench_solve_periodic_columnar_pipeline_col_then_sub.py":
        "tools.benchmarks.periodic_sub_trans.col_then_sub.runner",
    "tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py":
        "tools.benchmarks.periodic_sub_trans.sub_then_col.runner",
    "tools/benchmarks/periodic_sub_trans/col_then_sub/bench_solve_periodic_columnar_pipeline_col_then_sub.py":
        "tools.benchmarks.periodic_sub_trans.col_then_sub.runner",
}


def test_legacy_periodic_sub_trans_entry_wrappers_exist_and_compile():
    for rel in _WRAPPERS:
        path = Path(rel)
        assert path.exists(), f"missing wrapper: {rel}"
        py_compile.compile(str(path), doraise=True)


def test_legacy_periodic_sub_trans_entry_wrappers_are_thin_and_non_cli():
    for rel, module_path in _WRAPPERS.items():
        text = Path(rel).read_text(encoding="utf-8")
        assert "argparse" not in text
        assert "add_argument" not in text
        assert f"from {module_path} import main" in text
        assert 'if __name__ == "__main__":' in text
        assert "main()" in text
