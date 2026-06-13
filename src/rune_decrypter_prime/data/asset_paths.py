from __future__ import annotations

from pathlib import Path


_REPO_MARKERS = ("assets_manifest_v1.json", "pyproject.toml", ".git")


def find_repo_root(start: Path | None = None) -> Path:
    cur = (start or Path(__file__)).resolve()
    if cur.is_file():
        cur = cur.parent
    while True:
        if any((cur / marker).exists() for marker in _REPO_MARKERS):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise FileNotFoundError(
        "Could not locate repository root from "
        f"{start or Path(__file__)}. Expected one of: {', '.join(_REPO_MARKERS)}"
    )


def resolve_assets_path(*parts: str, start: Path | None = None) -> Path:
    root = find_repo_root(start or Path(__file__))
    return (root / "assets" / Path(*parts)).resolve()


def to_repo_relative(path: Path, *, start: Path | None = None) -> str:
    p = Path(path).resolve()
    try:
        root = find_repo_root(start or Path(__file__))
        return str(p.relative_to(root)).replace("\\", "/")
    except Exception:
        return str(p)


__all__ = ["find_repo_root", "resolve_assets_path", "to_repo_relative"]
