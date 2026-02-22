from __future__ import annotations

import ast
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

EXCLUDED_DIR_NAMES = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "env",
    "venv",
    "output",
}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]


def _share_dir(repo_root: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{ts}__share__symbols"
    dest = repo_root / "output" / "share" / run_id
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def extract_definitions(filepath: Path) -> List[Dict[str, str]]:
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    results: List[Dict[str, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [arg.arg for arg in node.args.args]
            doc = ast.get_docstring(node)
            results.append(
                {
                    "type": "function",
                    "name": node.name,
                    "signature": f"{node.name}({', '.join(args)})",
                    "docstring": doc.strip().splitlines()[0] if doc else "",
                }
            )
        elif isinstance(node, ast.ClassDef):
            class_doc = ast.get_docstring(node)
            results.append(
                {
                    "type": "class",
                    "name": node.name,
                    "signature": "",
                    "docstring": class_doc.strip().splitlines()[0] if class_doc else "",
                }
            )
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [arg.arg for arg in item.args.args]
                    method_doc = ast.get_docstring(item)
                    results.append(
                        {
                            "type": "method",
                            "name": f"{node.name}.{item.name}",
                            "signature": f"{item.name}({', '.join(args)})",
                            "docstring": method_doc.strip().splitlines()[0] if method_doc else "",
                        }
                    )
    return results


def scan_repo(root_path: Path) -> List[Dict[str, str]]:
    all_defs: List[Dict[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            fullpath = Path(dirpath) / fname
            relpath = fullpath.relative_to(root_path)
            defs = extract_definitions(fullpath)
            for entry in defs:
                entry["file"] = relpath.as_posix()
                all_defs.append(entry)
    return sorted(all_defs, key=lambda d: (d["file"], d["name"]))


def main() -> None:
    repo_root = _repo_root()
    defs = scan_repo(repo_root / "src")
    share_dir = _share_dir(repo_root)
    out_path = share_dir / "project_symbol_index.txt"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"# Project Symbol Index for {repo_root.name}\n\n")
        for entry in defs:
            f.write(
                f"[{entry['type']:<8}] "
                f"{entry['file']:<50} "
                f"{entry['name']:<30} "
                f"{entry['signature']:<40} "
                f"{entry['docstring']}\n"
            )
    print(f"Index written to {out_path}")


if __name__ == "__main__":
    main()
