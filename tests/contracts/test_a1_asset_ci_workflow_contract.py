from __future__ import annotations

import ast
import importlib.util
import json
import re
import shlex
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / '.github' / 'workflows'
PUSH_GATE = WORKFLOWS / 'rdp_v1_full_ci.yml'
FULL_PROOF = WORKFLOWS / 'rdp_v1_full_proof.yml'
PROFILE_MANIFEST = ROOT / 'assets' / 'manifests' / 'asset_profiles_v1.json'
TUTORIAL_RUNNER = ROOT / 'tutorials' / 'v1' / 'run_tutorials.py'

def _tutorial_runner():
    name = 'rdp_asset_profile_runner_test'
    spec = importlib.util.spec_from_file_location(name, TUTORIAL_RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def _decorator_names(path: Path, function_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    function = next(node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name)
    names: set[str] = set()
    for decorator in function.decorator_list:
        names.add(ast.unparse(decorator))
    return names

def test_cheap_pr_gate_and_main_or_manual_full_proof() -> None:
    workflows = sorted(WORKFLOWS.glob('*.yml'))
    push_files = [path.name for path in workflows if '\n  push:\n' in path.read_text(encoding='utf-8') or '\n  pull_request:\n' in path.read_text(encoding='utf-8')]
    assert push_files == [PUSH_GATE.name, FULL_PROOF.name]
    push = PUSH_GATE.read_text(encoding='utf-8')
    assert 'name: RDP V1 push gate' in push
    assert 'python tools/ci/install_light.py' in push
    assert '"not full_assets"' in push
    assert 'TutorialRunSet.RELEASE' in push
    proof = FULL_PROOF.read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in proof
    assert proof.split('\non:\n', 1)[1].split('\npermissions:', 1)[0].strip() == (
        'workflow_dispatch:\n  push:\n    branches:\n      - main'
    )
    assert '\n  pull_request:\n' not in proof
    assert 'python install.py' in proof
    assert 'python tools/run_validation.py' in proof
    assert 'TutorialRunSet.FULL_ASSET_EXAMPLES' in proof
    assert 'windows-latest' in proof and 'ubuntu-latest' in proof
    assert '"3.11"' in proof

def test_non_gate_workflows_are_manual_and_labelled_non_authoritative() -> None:
    for path in sorted(WORKFLOWS.glob('*.yml')):
        if path in {PUSH_GATE, FULL_PROOF}:
            continue
        text = path.read_text(encoding='utf-8')
        assert 'workflow_dispatch:' in text
        assert text.split('\non:\n', 1)[1].split('\npermissions:', 1)[0].strip() == 'workflow_dispatch:'
        assert '\n  push:\n' not in text
        assert '\n  pull_request:\n' not in text
        assert 'non-authoritative' in text.splitlines()[0]


def test_manual_native_workflow_checks_the_canonical_public_api(monkeypatch, tmp_path: Path) -> None:
    from rdp import api

    text = (WORKFLOWS / 'rdp_v1_wheel_ci.yml').read_text(encoding='utf-8')
    block = re.search(r'^      CIBW_TEST_COMMAND: >-\n((?:        .+\n)+)', text, re.M)
    assert block is not None
    command = shlex.split(' '.join(line.strip() for line in block[1].splitlines()))
    assert command[:2] == ['python', '-c']
    assert len(command) == 3
    code = command[2].replace('{project}', ROOT.as_posix())
    tree = ast.parse(code)
    assert ast.unparse(tree.body[0]) == 'import runpy'
    expected_call = ast.parse(
        f"runpy.run_path('{ROOT.as_posix()}/tools/ci/a5_installed_wheel_smoke.py')['_assert_v1_public_contract']()"
    ).body[0]
    assert ast.dump(tree.body[1]) == ast.dump(expected_call)
    assert [node.names[0].name for node in tree.body[2:] if isinstance(node, ast.Import)] == [
        'rdp.scoring.language_model._fastlm',
        'rdp.scoring.hamming._hamming',
        'rdp.scoring.span_hamming._span_hamming_fast',
    ]
    # Exercise the workflow's API check outside the checkout CWD, without a build.
    public_check = compile(ast.Module(body=tree.body[:2], type_ignores=[]), '<manual-wheel-api-check>', 'exec')
    monkeypatch.chdir(tmp_path)
    exec(public_check, {})
    monkeypatch.setattr(api, '__all__', api.__all__[1:])
    with pytest.raises(AssertionError, match='installed public surface mismatch'):
        exec(public_check, {})

def test_full_asset_integration_tests_are_explicitly_marked() -> None:
    assert 'pytest.mark.full_assets' in _decorator_names(ROOT / 'tests' / 'api' / 'test_two_period_cribs_api.py', 'test_real_route_returns_standard_exact_solution_with_installed_assets')
    assert 'pytest.mark.full_assets' in _decorator_names(ROOT / 'tests' / 'tutorials' / 'test_two_period_cribs_tutorial.py', 'test_fast_walkthrough_returns_exact_plaintext_and_key')
    marked = {'tests/scoring/test_scorer_smoothing_effect.py': ('test_smoothing_choice_changes_scores_for_random_text',), 'tests/scoring/test_lm_raw_data_integrity.py': ('test_joint_tables_have_expected_shapes_and_zero_counts', 'test_ecdf_tables_are_monotone_and_end_at_0_1'), 'tests/utils/test_seed_utils_periodic_columnar.py': ('test_seed_generator_quality_beats_random_baseline_fraction_of_gap',)}
    for relpath, function_names in marked.items():
        for function_name in function_names:
            assert 'pytest.mark.full_assets' in _decorator_names(ROOT / relpath, function_name)
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'full_assets: requires the canonical full_v1' in pyproject

def test_full_asset_example_exceptions_remain_explicit() -> None:
    profiles = json.loads(PROFILE_MANIFEST.read_text(encoding='utf-8'))['profiles']
    assert {'ci_light', 'full_v1'} <= set(profiles)
    assert profiles['ci_light']['verification_manifest'] == 'assets/manifests/assets_manifest_ci_light_v1.json'
    assert profiles['full_v1']['verification_manifest'] == 'assets/manifests/assets_manifest_v1.json'
    runner = _tutorial_runner()
    two_period = {
        name
        for name in runner.FULL_ASSET_ONLY_NAMES
        if name.startswith('two_period_cribs')
    }
    assert two_period == {
        'two_period_cribs.py',
        'two_period_cribs_interruptors.py',
        'two_period_cribs_p13_p31_search.py',
    }
