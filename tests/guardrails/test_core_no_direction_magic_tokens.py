from __future__ import annotations
import ast
from pathlib import Path
import rune_decrypter_prime as rdp
_ALLOWED = {'core/types.py'}
_BANNED = {'fwd', 'rev'}

def _strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, 'body', None)
            if not body:
                continue
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, 'value', None), ast.Constant):
                if isinstance(first.value.value, str):
                    body.pop(0)
    return tree

def _scan_tokens(py: Path) -> list[tuple[int, str]]:
    src = py.read_text(encoding='utf-8', errors='ignore')
    try:
        tree = ast.parse(src, filename=str(py))
    except SyntaxError:
        return []
    tree = _strip_docstrings(tree)
    offenders: list[tuple[int, str]] = []

    class V(ast.NodeVisitor):

        def visit_Constant(self, node: ast.Constant) -> None:
            if isinstance(node.value, str):
                val = node.value.strip().lower()
                if val in _BANNED:
                    offenders.append((int(node.lineno), val))
            self.generic_visit(node)
    V().visit(tree)
    return offenders

def test_core_has_no_legacy_fwd_rev_literals_outside_allowlist() -> None:
    root = Path(rdp.__file__).resolve().parent
    core = root / 'core'
    all_offenders: list[str] = []
    for py in core.rglob('*.py'):
        rel = py.relative_to(root).as_posix()
        if rel in _ALLOWED:
            continue
        for lineno, token in _scan_tokens(py):
            all_offenders.append(f'- {rel}:{lineno} token={token!r}')
    assert not all_offenders, "Legacy direction string literals ('fwd'/'rev') are not allowed in core logic.\n" + '\n'.join(all_offenders)
