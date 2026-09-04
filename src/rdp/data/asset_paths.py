from __future__ import annotations

from pathlib import Path


_REPO_MARKERS = ("assets_manifest_v1.json", "pyproject.toml", ".git")
# Packaged CI-light assets have one exact installed location beside this module.
# This is not a namespace search or fallback.
_PACKAGE_DATA_ROOT = Path(__file__).resolve().parent
_PACKAGE_ASSETS_ROOT = _PACKAGE_DATA_ROOT / "assets"
_PACKAGE_CI_MANIFEST = _PACKAGE_DATA_ROOT / "assets_manifest_ci_light_v1.json"


def find_repo_root(start: Path | None = None) -> Path:
    """Locate a source checkout root. This is a development/source helper only."""
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


def _source_assets_root(start: Path) -> Path | None:
    try:
        repo_root = find_repo_root(start)
    except FileNotFoundError:
        return None
    assets = (repo_root / "assets").resolve()
    return assets if assets.is_dir() else None


def _package_assets_root() -> Path | None:
    """Return the exact CI-light asset root staged into an installed wheel."""
    root = _PACKAGE_ASSETS_ROOT.resolve()
    manifest = _PACKAGE_CI_MANIFEST.resolve()
    return root if root.is_dir() and manifest.is_file() else None


def find_assets_root(start: Path | None = None) -> Path:
    """Resolve the canonical local asset root without env/CWD/home fallbacks.

    Precedence is deliberate:
      1. source checkout top-level ``assets/``;
      2. the exact CI-light assets staged into the installed wheel.

    Complete external LM1-LM4 data remains explicit through the existing
    scoring ``model_root`` contract. No environment-variable or CWD search is
    introduced here.
    """
    origin = (start or Path(__file__)).resolve()
    source_assets = _source_assets_root(origin)
    if source_assets is not None:
        return source_assets
    package_assets = _package_assets_root()
    if package_assets is not None:
        return package_assets
    raise FileNotFoundError(
        "No RDP asset root is available. Expected a source checkout 'assets/' "
        "directory or the source-bundled CI-light assets staged in the installed "
        "wheel. Complete external LM assets must be supplied through model_root."
    )


def resolve_assets_path(*parts: str, start: Path | None = None) -> Path:
    return (find_assets_root(start or Path(__file__)) / Path(*parts)).resolve()


def to_repo_relative(path: Path, *, start: Path | None = None) -> str:
    """Return a portable display path without leaking a private absolute path."""
    p = Path(path).resolve()
    try:
        root = find_repo_root(start or Path(__file__))
        return str(p.relative_to(root)).replace("\\", "/")
    except (FileNotFoundError, ValueError):
        pass
    try:
        rel = p.relative_to(_PACKAGE_ASSETS_ROOT.resolve())
        base = "rdp/data/assets"
        return base if str(rel) == "." else f"{base}/{rel.as_posix()}"
    except ValueError:
        return f"<external:{p.name or 'path'}>"


__all__ = ["find_repo_root", "find_assets_root", "resolve_assets_path", "to_repo_relative"]
