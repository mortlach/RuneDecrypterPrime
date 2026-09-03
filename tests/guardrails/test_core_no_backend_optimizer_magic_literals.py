from __future__ import annotations
import ast
import re
from pathlib import Path
import rdp
import rune_decrypter_prime
_BANNED = {'numpy', 'torch', 'unified', 'auto', 'beam', 'ga', 'sa', 'hybrid', 'cpu', 'cuda'}
_PATTERN = re.compile('\\b(?:numpy|torch|unified|auto|beam|ga|sa|hybrid|cpu|cuda)\\b', re.IGNORECASE)
_ALLOWLIST = {'core/types.py', 'core/config/logging_config.py', 'core/config/cipher.py', 'core/config/scoring.py', 'core/engine/engine.py', 'core/engine/finalization.py', 'core/problem/instance.py'}

def _strip_docstrings(tree: ast.AST) -> ast.AST:
    """Remove module/class/function docstrings so we don't scan them."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                expr = node.body[0]
                if isinstance(getattr(expr, 'value', None), ast.Constant) and isinstance(expr.value.value, str):
                    node.body.pop(0)
    return tree

def _scan_file(py: Path) -> list[tuple[str, int, str, str]]:
    """
    Return list of offenders as tuples:
      (kind, lineno, token, context)
    kind ∈ {'import','name','attr','string'}
    """
    src = py.read_text(encoding='utf-8', errors='ignore')
    try:
        tree = ast.parse(src, filename=str(py))
    except SyntaxError:
        return []
    tree = _strip_docstrings(tree)
    offenders: list[tuple[str, int, str, str]] = []

    class V(ast.NodeVisitor):

        def visit_Import(self, node: ast.Import):
            for alias in node.names:
                head = alias.name.split('.')[0].lower()
                if head in _BANNED:
                    offenders.append(('import', node.lineno, head, f'import {alias.name}'))
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom):
            if node.module:
                head = node.module.split('.')[0].lower()
                if head in _BANNED:
                    offenders.append(('import', node.lineno, head, f'from {node.module} import ...'))
            self.generic_visit(node)

        def visit_Name(self, node: ast.Name):
            ident = node.id.lower()
            if ident in _BANNED:
                offenders.append(('name', node.lineno, ident, node.id))
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute):
            base = node.value
            if isinstance(base, ast.Name):
                ident = base.id.lower()
                if ident in _BANNED:
                    offenders.append(('attr', node.lineno, ident, f'{base.id}.{node.attr}'))
            self.generic_visit(node)

        def visit_Constant(self, node: ast.Constant):
            if isinstance(node.value, str):
                if _PATTERN.search(node.value):
                    val = node.value
                    preview = val if len(val) <= 60 else val[:57] + '...'
                    offenders.append(('string', node.lineno, '<str>', preview))
            self.generic_visit(node)
    V().visit(tree)
    return offenders

def test_core_has_no_backend_optimizer_magic_literals():
    all_offenders: list[str] = []
    package_roots = (
        Path(rdp.__file__).resolve().parent,
        Path(rune_decrypter_prime.__file__).resolve().parent,
    )
    for root in package_roots:
        for py in (root / 'core').rglob('*.py'):
            rel = py.relative_to(root).as_posix()
            if rel in _ALLOWLIST:
                continue
            for kind, lineno, token, ctx in _scan_file(py):
                all_offenders.append(f'- {rel}:{lineno} [{kind}] {ctx}')
    assert not all_offenders, 'Backend/optimizer magic strings found in core code (comments/docstrings ignored).\n' + '\n'.join(all_offenders)
