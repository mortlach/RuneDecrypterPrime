"""Generate a minimal class/function symbol index for docs lint coverage."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import Iterable, List, Tuple


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]


DEFAULT_ROOT = _repo_root() / "src" / "rune_decrypter_prime"


def walk_py(root: Path) -> Iterable[Path]:
    return root.rglob("*.py")


def extract_symbols(py_path: Path, module: str) -> List[Tuple[str, str, str, str]]:
    try:
        src = py_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src)
    except Exception:
        return []
    rows = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            rows.append(("[class]", module, node.name, node.name))
        elif isinstance(node, ast.FunctionDef):
            rows.append(("[function]", module, node.name, f"{node.name}()"))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate symbol index for docs lint coverage.")
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Root package to scan (default: src/rune_decrypter_prime).",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.exists():
        raise SystemExit(f"[symbol-index] root does not exist: {root}")

    rows: List[Tuple[str, str, str, str]] = []
    for py in sorted(walk_py(root)):
        rel_module = py.relative_to(root).as_posix()
        rows.extend(extract_symbols(py, rel_module))

    for kind, module, qual, sym in rows:
        print(f"{kind} {module} {qual} {sym}")


if __name__ == "__main__":
    main()
