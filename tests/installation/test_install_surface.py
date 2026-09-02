from __future__ import annotations
import ast
import subprocess
import sys
import tomllib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def test_root_installer_does_not_import_removed_benchmark_bootstrap() -> None:
    text = (ROOT / 'install.py').read_text(encoding='utf-8')
    assert 'tools.benchmarks.community' not in text
    assert 'install_smoke.py' not in text

def test_root_installer_is_full_v1_and_ci_light_is_separate() -> None:
    install_text = (ROOT / 'install.py').read_text(encoding='utf-8')
    light_text = (ROOT / 'tools' / 'ci' / 'install_light.py').read_text(encoding='utf-8')
    assert 'INSTALL_MODE_LABEL = "Full V1 install"' in install_text
    assert 'DEFAULT_ASSET_PROFILE = "full_v1"' in install_text
    assert 'asset_profile_name=DEFAULT_ASSET_PROFILE' in install_text
    light_tree = ast.parse(light_text)
    assert any(
        isinstance(node, ast.Call)
        and any(
            keyword.arg == 'asset_profile_name'
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value == 'ci_light'
            for keyword in node.keywords
        )
        for node in ast.walk(light_tree)
    )
    assert 'CI light install' in light_text

def test_ci_light_wrapper_bootstraps_repo_root_for_standalone_execution(tmp_path: Path) -> None:
    wrapper = ROOT / 'tools' / 'ci' / 'install_light.py'
    probe = '\n'.join(('import importlib.util', f'wrapper = {str(wrapper)!r}', "spec = importlib.util.spec_from_file_location('rdp_ci_install_probe', wrapper)", 'assert spec is not None and spec.loader is not None', 'module = importlib.util.module_from_spec(spec)', 'spec.loader.exec_module(module)', 'module._load_install_module()', 'from tools.assets.asset_profiles import select_asset_profile', "profile = select_asset_profile(module.REPO_ROOT / 'asset_profiles_v1.json', 'ci_light')", "assert profile.name == 'ci_light'"))
    proc = subprocess.run([sys.executable, '-I', '-c', probe], cwd=tmp_path, text=True, encoding='utf-8', errors='replace', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    assert proc.returncode == 0, proc.stdout

def test_root_setup_builds_native_extensions_from_present_sources() -> None:
    text = (ROOT / 'setup.py').read_text(encoding='utf-8')
    assert text.count('rdp.scoring.language_model._fastlm') == 1
    assert text.count('rdp.scoring.hamming._hamming') == 1
    assert text.count('rdp.scoring.span_hamming._span_hamming_fast') == 1
    assert '_ngram_hamming_fast' not in text

def test_root_setup_uses_relative_extension_sources_for_editable_builds() -> None:
    text = (ROOT / 'setup.py').read_text(encoding='utf-8')
    assert 'relative_to(ROOT.resolve()).as_posix()' in text
    assert 'sources=[_rel(path) for path in sources]' in text
    assert 'sources=[str(path) for path in sources]' not in text

def test_pyproject_build_requires_pybind11_for_isolated_builds() -> None:
    text = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'pybind11' in text.split('[project]', 1)[0]

def test_pyproject_declares_required_runtime_dependencies() -> None:
    data = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    dependency_names = {str(item).split(';', 1)[0].strip().split('[', 1)[0].split('>', 1)[0].split('<', 1)[0].split('=', 1)[0].strip().lower() for item in data['project']['dependencies']}
    assert {'numpy', 'zstandard', 'tzdata'} <= dependency_names
