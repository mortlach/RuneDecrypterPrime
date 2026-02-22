from __future__ import annotations

from pathlib import Path

# === CONFIG ===
ALLOWED_EXTENSIONS = {".py"}
EXCLUDED_DIRS = {".git", ".idea", "__pycache__", ".pytest_cache", "output"}
EXCLUDED_FILES = {".gitignore"}

# skip whole subtrees by relative path prefix
EXCLUDED_PATH_PREFIXES = {
    Path("output/logs"),
    Path("output/trace"),
    Path("output/tests"),
    Path("output/tutorials"),
    Path("output/share"),
    Path("output/release"),
}


def should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)

    if path.is_dir() and path.name in EXCLUDED_DIRS:
        return True
    if path.is_file() and path.name in EXCLUDED_FILES:
        return True

    if path.is_file() and ALLOWED_EXTENSIONS and path.suffix not in ALLOWED_EXTENSIONS:
        return True

    for prefix in EXCLUDED_PATH_PREFIXES:
        try:
            rel.relative_to(prefix)
            return True
        except ValueError:
            continue

    return False


def print_dir_tree(root: Path, prefix: str = "", top_root: Path | None = None) -> None:
    if top_root is None:
        top_root = root

    entries = [p for p in root.iterdir() if not should_skip(p, top_root)]
    entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
    count = len(entries)

    for idx, path in enumerate(entries):
        connector = "|-- " if idx < count - 1 else "`-- "
        print(f"{prefix}{connector}{path.name}")
        if path.is_dir():
            child_prefix = f"{prefix}{'|   ' if idx < count - 1 else '    '}"
            print_dir_tree(path, child_prefix, top_root)


if __name__ == "__main__":
    print_dir_tree(Path.cwd())
