from __future__ import annotations
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOTS = (REPO_ROOT / 'src' / 'rdp',)

@dataclass(frozen=True)
class EnumMember:
    path: str
    enum_class: str
    member_name: str
    value: str

    @property
    def qualified_name(self) -> str:
        return f'{self.enum_class}.{self.member_name}'

    @property
    def location(self) -> str:
        return f'{self.path}:{self.qualified_name}'

def _repo_relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()

def _read_py_text(path: Path) -> str:
    return path.read_text(encoding='utf-8-sig')

def _py_files() -> Iterable[Path]:
    for source_root in SRC_ROOTS:
        assert source_root.is_dir(), f'missing source root: {_repo_relative(source_root)}'
        for path in sorted(source_root.rglob('*.py')):
            parts = set(path.parts)
            if '__pycache__' in parts:
                continue
            yield path

def _base_name(base: ast.expr) -> str | None:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    if isinstance(base, ast.Subscript):
        return _base_name(base.value)
    return None

def _is_enum_class(node: ast.ClassDef) -> bool:
    return any((_base_name(base) in {'Enum', 'StrEnum', 'IntEnum'} for base in node.bases))

def _string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None

def _iter_string_enum_members() -> Iterable[EnumMember]:
    for path in _py_files():
        text = _read_py_text(path)
        tree = ast.parse(text, filename=str(path))
        relpath = _repo_relative(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or not _is_enum_class(node):
                continue
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                value = _string_literal(stmt.value)
                if value is None:
                    continue
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        yield EnumMember(path=relpath, enum_class=node.name, member_name=target.id, value=value)

def test_string_enum_inventory_can_be_built_without_parse_errors() -> None:
    """Keep the enum audit live without making duplicate wire values a requirement."""
    members = {member.qualified_name: member for member in _iter_string_enum_members()}
    assert members, "no string enum members found under the source package roots"
    expected_sentinels = {
        "Direction.LTR": "ltr",
        "TextDirection.LTR": "left_to_right",
        "SolverKind.BEAM_SEARCH": "beam_search",
        "ScorerBackend.NUMPY": "numpy",
    }
    missing = sorted(set(expected_sentinels) - set(members))
    assert not missing, f'enum scanner missed expected sentinel members: {missing}'
    wrong_values = {name: (members[name].value, expected) for name, expected in expected_sentinels.items() if members[name].value != expected}
    assert not wrong_values, f'enum scanner returned unexpected sentinel values: {wrong_values}'

def test_known_wrong_domain_enum_borrowing_patterns_are_absent() -> None:
    # Oracle/truth labels must not be borrowed for execution routes or parameter keys.
    forbidden_usages = (
        (
            'OracleUse.KNOWN_KEY_FASTPATH.value',
            ('SolverReportDetailKey.EXECUTION_ROUTE.value', 'execution_route'),
            'ExecutionRoute.KNOWN_KEY_FASTPATH.value',
        ),
        (
            'OracleUse.TEST_KEY.value',
            ('normalized_params', 'SolverParamKey'),
            'SolverParamKey.TEST_KEY.value',
        ),
    )
    failures: list[str] = []
    for path in _py_files():
        for line_number, line in enumerate(_read_py_text(path).splitlines(), start=1):
            for expression, contexts, replacement in forbidden_usages:
                if expression in line and any(context in line for context in contexts):
                    failures.append(
                        f'{_repo_relative(path)}:{line_number}: '
                        f'use {replacement} instead of {expression}'
                    )
    assert not failures, '\n'.join(failures)
