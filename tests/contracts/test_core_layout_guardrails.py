from __future__ import annotations
import ast
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
RDP_CORE_ROOT = SRC_ROOT / "rdp" / "core"
ENGINE_CORE_ROOT = SRC_ROOT / "rune_decrypter_prime" / "core"
RUNE_SCORER = SRC_ROOT / "rune_decrypter_prime" / "scoring" / "rune_scorer.py"
CONSTRUCTION_BOUNDARY_FILES = {
    RDP_CORE_ROOT / "config" / "run.py",
    RDP_CORE_ROOT / "config" / "scoring.py",
    RDP_CORE_ROOT / "config" / "cipher.py",
    RDP_CORE_ROOT / "config" / "hard_crib.py",
    RDP_CORE_ROOT / "config" / "interruptor.py",
    RDP_CORE_ROOT / "config" / "logging_config.py",
    RDP_CORE_ROOT / "component_contracts.py",
    RDP_CORE_ROOT / "types.py",
}
TELEMETRY_OR_PAYLOAD_DICT_CHECKS = {
    ENGINE_CORE_ROOT / "engine" / "engine.py": {"tele"},
    RDP_CORE_ROOT / "problem" / "runtime.py": {
        "self.telemetry",
        "sc_tel",
        "extra",
        "extra2",
    },
    RUNE_SCORER: {"stats", "obj", "last"},
}


def _python_files_under_core() -> list[Path]:
    return sorted(
        path
        for root in (RDP_CORE_ROOT, ENGINE_CORE_ROOT)
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )

def _core_runtime_files() -> list[Path]:
    return [path for path in _python_files_under_core() if path not in CONSTRUCTION_BOUNDARY_FILES and path.name != '__init__.py']

def _runtime_and_numpy_scorer_files() -> list[Path]:
    return _core_runtime_files() + [RUNE_SCORER]

def _source_for(node: ast.AST, text: str) -> str:
    return ast.get_source_segment(text, node) or ''

def _is_dict_or_mapping_check(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Name) or node.func.id != 'isinstance' or len(node.args) < 2:
        return False
    target = node.args[1]
    if isinstance(target, ast.Name):
        return target.id in {'dict', 'Mapping'}
    if isinstance(target, ast.Tuple):
        return any((isinstance(elt, ast.Name) and elt.id in {'dict', 'Mapping'} for elt in target.elts))
    return False

def _checked_expression(node: ast.Call, text: str) -> str:
    return _source_for(node.args[0], text).strip() if node.args else ''

def test_core_has_no_module_package_name_collisions() -> None:
    collisions: list[str] = []
    for root in (RDP_CORE_ROOT, ENGINE_CORE_ROOT):
        for package_init in root.rglob('__init__.py'):
            package_dir = package_init.parent
            sibling_module = package_dir.with_suffix('.py')
            if sibling_module.exists():
                collisions.append(f'{sibling_module.relative_to(SRC_ROOT)} conflicts with {package_dir.relative_to(SRC_ROOT)}/')
    assert collisions == []

def test_core_runtime_has_no_hidden_config_getters() -> None:
    forbidden = {'_cfg_get', '_config_get', '_get_cfg', '_get_config'}
    hits: list[str] = []
    for path in _runtime_and_numpy_scorer_files():
        text = path.read_text(encoding='utf-8')
        for token in forbidden:
            if token in text:
                hits.append(f'{path.relative_to(REPO_ROOT)} contains {token}')
    assert hits == []

def test_core_runtime_does_not_import_aggregate_config_package() -> None:
    hits: list[str] = []
    for path in _core_runtime_files():
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module == 'rdp.core.config':
                hits.append(f'{path.relative_to(REPO_ROOT)} imports aggregate core.config')
            if node.level > 0 and node.module == 'config':
                hits.append(f'{path.relative_to(REPO_ROOT)} imports relative aggregate core.config')
    assert hits == []

def test_runtime_config_paths_do_not_accept_dict_like_configs() -> None:
    hits: list[str] = []
    for path in _runtime_and_numpy_scorer_files():
        if path in CONSTRUCTION_BOUNDARY_FILES:
            continue
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text, filename=str(path))
        allowed_payload_names = TELEMETRY_OR_PAYLOAD_DICT_CHECKS.get(path, set())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_dict_or_mapping_check(node):
                continue
            checked = _checked_expression(node, text)
            if checked in allowed_payload_names:
                continue
            hits.append(f'{path.relative_to(REPO_ROOT)}:{node.lineno} checks {checked!r} for dict/Mapping outside a documented construction or payload boundary')
    assert hits == []

def test_numpy_scorer_uses_direct_scoring_config_attributes() -> None:
    text = RUNE_SCORER.read_text(encoding='utf-8')
    assert 'getattr(scorer_cfg' not in text

def test_decryption_problem_uses_direct_canonical_config_attributes() -> None:
    path = RDP_CORE_ROOT / 'problem' / 'runtime.py'
    text = path.read_text(encoding='utf-8')
    assert 'getattr(self.c_cfg' not in text
    assert 'getattr(self.s_cfg' not in text

def test_core_runtime_uses_direct_typed_config_attributes() -> None:
    checked_files = {ENGINE_CORE_ROOT / 'solver_engine.py': ['getattr(cfg', 'getattr(cfg.cipher', 'getattr(self.cfg.cipher'], RDP_CORE_ROOT / 'problem' / 'instance.py': ['getattr(spec.cipher_cfg', 'getattr(spec.scorer_params']}
    hits: list[str] = []
    for path, forbidden_fragments in checked_files.items():
        text = path.read_text(encoding='utf-8')
        for fragment in forbidden_fragments:
            if fragment in text:
                hits.append(f'{path.relative_to(REPO_ROOT)} contains {fragment}')
    assert hits == []
