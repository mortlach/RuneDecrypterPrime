from __future__ import annotations
import ast
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / '.github' / 'workflows'
PUSH_GATE = WORKFLOWS / 'rdp_v1_full_ci.yml'
FULL_PROOF = WORKFLOWS / 'rdp_v1_full_proof.yml'
PROFILE_MANIFEST = ROOT / 'asset_profiles_v1.json'
TUTORIAL_MANIFEST = ROOT / 'tutorials' / 'v1' / 'tutorial_manifest_v1.json'

def _decorator_names(path: Path, function_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    function = next((node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name))
    names: set[str] = set()
    for decorator in function.decorator_list:
        names.add(ast.unparse(decorator))
    return names

def test_one_authoritative_push_gate_and_one_manual_full_proof() -> None:
    workflows = sorted(WORKFLOWS.glob('*.yml'))
    push_files = [path.name for path in workflows if '\n  push:\n' in path.read_text(encoding='utf-8') or '\n  pull_request:\n' in path.read_text(encoding='utf-8')]
    assert push_files == [PUSH_GATE.name]
    push = PUSH_GATE.read_text(encoding='utf-8')
    assert 'name: RDP V1 push gate' in push
    assert 'python tools/ci/install_light.py' in push
    assert '"not full_assets"' in push
    assert 'TutorialRunSet.CI_LIGHT' in push
    proof = FULL_PROOF.read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in proof
    assert '\n  push:\n' not in proof
    assert 'python install.py' in proof
    assert 'TutorialRunSet.ALL_WORKING' in proof
    assert 'windows-latest' in proof and 'ubuntu-latest' in proof
    assert '"3.11"' in proof

def test_non_gate_workflows_are_manual_and_labelled_non_authoritative() -> None:
    for path in sorted(WORKFLOWS.glob('*.yml')):
        if path in {PUSH_GATE, FULL_PROOF}:
            continue
        text = path.read_text(encoding='utf-8')
        assert 'workflow_dispatch:' in text
        assert '\n  push:\n' not in text
        assert '\n  pull_request:\n' not in text
        assert 'non-authoritative' in text.splitlines()[0]

def test_full_asset_integration_tests_are_explicitly_marked() -> None:
    assert 'pytest.mark.full_assets' in _decorator_names(ROOT / 'tests' / 'api' / 'test_two_period_cribs_api.py', 'test_real_route_returns_standard_exact_solution_with_installed_assets')
    assert 'pytest.mark.full_assets' in _decorator_names(ROOT / 'tests' / 'tutorials' / 'test_two_period_cribs_tutorial.py', 'test_fast_walkthrough_returns_exact_plaintext_and_key')
    marked = {'tests/scoring/test_scorer_smoothing_effect.py': ('test_smoothing_choice_changes_scores_for_random_text',), 'tests/scoring/test_lm_raw_data_integrity.py': ('test_joint_tables_have_expected_shapes_and_zero_counts', 'test_ecdf_tables_are_monotone_and_end_at_0_1'), 'tests/utils/test_seed_utils_periodic_columnar.py': ('test_seed_generator_quality_beats_random_baseline_fraction_of_gap',)}
    for relpath, function_names in marked.items():
        for function_name in function_names:
            assert 'pytest.mark.full_assets' in _decorator_names(ROOT / relpath, function_name)
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'full_assets: requires the canonical full_v1' in pyproject

def test_tutorial_labels_use_only_canonical_profiles() -> None:
    profiles = json.loads(PROFILE_MANIFEST.read_text(encoding='utf-8'))['profiles']
    manifest = json.loads(TUTORIAL_MANIFEST.read_text(encoding='utf-8'))
    assert manifest['asset_profile_default'] == 'full_v1'
    assert manifest['asset_profile_contract'] == '../../asset_profiles_v1.json'
    assert {row['required_asset_profile'] for row in manifest['tutorials']} <= set(profiles)
    two_period = {row['path']: row for row in manifest['tutorials'] if row['path'].startswith('Tutorial_TwoPeriodCribs')}
    assert two_period
    assert {row['required_asset_profile'] for row in two_period.values()} == {'full_v1'}
