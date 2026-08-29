from __future__ import annotations
from pathlib import Path
import pytest
pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]

def test_install_py_does_not_import_removed_benchmark_bootstrap() -> None:
    text = (ROOT / 'install.py').read_text(encoding='utf-8')
    assert 'tools.benchmarks' not in text
    assert 'community.bootstrap' not in text

def test_readme_clean_install_does_not_use_removed_benchmark_path() -> None:
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    removed = ('tools.benchmarks.community', 'tools/ci/install_smoke.py', 'assets_packed', 'benchmark_ready.json')
    for token in removed:
        assert token not in text

def test_readme_keeps_full_install_as_public_path() -> None:
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'python install.py' in text
    assert 'required V1 LM3/LM4 assets' in text
    assert 'CI-light' in text
    assert 'workflow-cost' in text
