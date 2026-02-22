#!/usr/bin/env python3
"""
share_packager.py — build a source manifest and a matching ZIP bundle (no git/CLI).

One call builds:
  • MANIFEST.json (sha256 per file + stable manifest hash)
  • ZIP bundle containing repo sources (+ optional tests) and an embedded MANIFEST.json
  • META.json with quick pointers

Output location:
  <out_root>/share/<TIMESTAMP>__share__<label>/

Config:
  - repo_root: root of the main repository
  - out_root:  where /share output goes (independent of repo_root)
  - test_root: optional separate folder that contains tests (outside repo_root OK)

"""
from __future__ import annotations
from pathlib import Path
from typing import Iterable, Dict, Any, Union, Sequence, Set, Optional, Tuple
import os, json, hashlib, zipfile, datetime as _dt, re
from zoneinfo import ZoneInfo

PathLike = Union[str, os.PathLike]

_THIS_FILE = Path(__file__).resolve()
def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]

_DEFAULT_REPO_ROOT = _repo_root()
_DEFAULT_OUT_ROOT = _DEFAULT_REPO_ROOT / "output"
_DEFAULT_TEST_ROOT: Optional[Path] = None  # set if you want by default
_DEFAULT_LABEL = "rune-decrypter"

REPO_ROOT = _DEFAULT_REPO_ROOT.resolve()
OUT_ROOT = _DEFAULT_OUT_ROOT.resolve()
TEST_ROOT = _DEFAULT_TEST_ROOT
LABEL = _DEFAULT_LABEL

# Timezone for timestamped folders (windows-safe formatting, no colon in %z)
_TZ = ZoneInfo("America/Los_Angeles")

# -----------------------------------------------------------------------------
# Include / Exclude rules (tuned for sharing source/config/docs)
# -----------------------------------------------------------------------------
INCLUDE_EXT: Set[str] = {
    # Python & stubs
    ".py", ".pyi", ".pyx", ".pxd", ".pxi", ".bak",
    # C/C++ and headers
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx",
    # Other languages
    ".rs", ".go", ".java", ".kt", ".swift", ".m", ".mm", ".cs", ".php", ".rb",
    # JS/TS
    ".ts", ".tsx", ".js", ".jsx",
    # Config / data (sources)
    ".toml", ".yaml", ".yml", ".ini", ".cfg", ".json",
    # Docs
    ".md", ".rst", ".txt",
    # Lightweight arrays/tables (adjust if too big)
    ".npz", ".npy",
}
INCLUDE_BASENAMES: Set[str] = {
    "LICENSE", "LICENSE.txt", "README", "README.md",
    "pyproject.toml", "requirements.txt", "Pipfile", "Pipfile.lock",
    "setup.cfg", "setup.py", "MANIFEST.in", ".gitignore",
}

EXCLUDE_DIRS: Set[str] = {
    ".git", "__pycache__", ".idea", ".vscode", ".mypy_cache", ".pytest_cache",
    "build", "dist", "node_modules", ".venv", "venv", "env", ".tox", ".eggs",
    ".ruff_cache", ".ipynb_checkpoints", "htmlcov", "site", ".coverage",
    ".hypothesis", ".gradle", ".parcel-cache", ".next", ".nuxt",
    # project outputs / generated
    "out", "output", "logs",
    # large bundled assets we don't want in share zip
    "data",
}
EXCLUDE_FILE_SUFFIXES: Set[str] = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib",
    ".o", ".obj", ".a", ".lib",
    ".class",
    # binary/data we want to skip in shares
    ".npz", ".npy", ".csv", ".tsv", ".pkl", ".gz", ".zip", ".xz", ".bz2",
}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _slug(s: str) -> str:
    s = re.sub(r"\s+", "-", s.strip())
    return re.sub(r"[^A-Za-z0-9_.\-]", "", s)[:60] or "share"

def _timestamp() -> str:
    # Windows-safe: no ":" in offsets or time
    return _dt.datetime.now(tz=_TZ).strftime("%Y-%m-%dT%H-%M-%S%z")

def _out_share_dir(out_root: Path, label: str | None = None) -> Path:
    ts = _timestamp()
    name = f"{ts}__share__{_slug(label or _DEFAULT_LABEL)}"
    p = (out_root / "share" / name).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p

def _is_excluded_dir(name: str) -> bool:
    if name in EXCLUDE_DIRS:
        return True
    # Hide other dot-directories by default (unless whitelisted)
    return name.startswith(".") and name not in {"."}

def _include_file(p: Path) -> bool:
    if p.is_dir() or p.is_symlink():
        return False
    suf = p.suffix.lower()
    if suf in EXCLUDE_FILE_SUFFIXES:
        return False
    # Skip anything under a /data/ component unless explicitly whitelisted
    parts = {part.lower() for part in p.parts}
    if "data" in parts:
        # Allow top-level README or license in data, but skip payloads
        if p.name.lower().startswith("readme"):
            return True
        return False
    if p.name in INCLUDE_BASENAMES:
        return True
    return suf in INCLUDE_EXT

def _walk_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _is_excluded_dir(d)]
        for fn in filenames:
            if fn.startswith(".") and fn not in INCLUDE_BASENAMES:
                continue
            p = Path(dirpath) / fn
            if _include_file(p):
                yield p

def _sha256_file(p: Path, chunk: int = 1 << 16) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

# -----------------------------------------------------------------------------
# Collection (multi-root)
# -----------------------------------------------------------------------------
RootSpec = Tuple[str, Path]  # (arc_prefix, root_path)

def collect_files_from_roots(roots: Sequence[RootSpec]) -> list[Tuple[str, Path, str]]:
    """
    Returns a list of tuples: (arc_path, abs_path, rel_path_from_root)
    where arc_path is what will appear inside the zip.
    """
    rows: list[Tuple[str, Path, str]] = []
    for arc_prefix, root in roots:
        if not root:
            continue
        root = root.resolve()
        for p in _walk_files(root):
            rel = str(p.relative_to(root)).replace("\\", "/")
            arc = f"{arc_prefix}/{rel}" if arc_prefix else rel
            rows.append((arc, p, rel))
    rows.sort(key=lambda r: r[0].lower())
    return rows

# -----------------------------------------------------------------------------
# Manifest (stable)
# -----------------------------------------------------------------------------
def build_manifest(repo_root: Path, out_root: Path, test_root: Optional[Path], files: Sequence[Tuple[str, Path, str]]) -> Dict[str, Any]:
    entries = []
    for arc, abspath, rel in files:
        try:
            size = abspath.stat().st_size
            sha = _sha256_file(abspath)
        except OSError:
            continue
        entries.append({
            "arc": arc,                 # path inside the zip
            "root": "tests" if test_root and str(abspath).startswith(str(test_root)) else "repo",
            "rel": rel,                 # relative to that root
            "bytes": size,
            "sha256": sha,
        })

    blob = json.dumps(sorted(entries, key=lambda x: x["arc"]), separators=(",", ":"), sort_keys=True).encode()
    manifest_hash = hashlib.sha256(blob).hexdigest()

    return {
        "created": _timestamp(),
        "label": LABEL,
        "repo_root": str(repo_root),
        "out_root": str(out_root),
        "test_root": str(test_root) if test_root else None,
        "manifest_sha256": manifest_hash,
        "files": entries,
    }

def write_manifest(manifest: Dict[str, Any], out_dir: Path) -> Path:
    dst = out_dir / "MANIFEST.json"
    dst.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return dst

# -----------------------------------------------------------------------------
# ZIP (repo + optional tests)
# -----------------------------------------------------------------------------
def create_zip_with_manifest(
    out_dir: Path,
    repo_root: Path,
    out_root: Path,
    test_root: Optional[Path],
    files: Sequence[Tuple[str, Path, str]],
    name: Optional[str] = None,
    manifest: Optional[Dict[str, Any]] = None,
) -> Path:
    if name is None:
        ts_simple = _dt.datetime.now(tz=_TZ).strftime("%Y%m%d_%H%M%S")
        # Use repo name in the filename for clarity
        name = f"{repo_root.name}_{ts_simple}_share.zip"
    zip_path = out_dir / name

    count = 0
    total = 0

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if manifest is not None:
            zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2))

        for arc, abspath, _rel in files:
            zf.write(abspath, arc)
            count += 1
            try:
                total += abspath.stat().st_size
            except OSError:
                pass

    print(f"[share.zip] Repo root:  {repo_root}")
    if test_root:
        print(f"[share.zip] Test root:  {test_root}")
    print(f"[share.zip] Out dir:    {out_dir}")
    print(f"[share.zip] Wrote:      {zip_path}")
    print(f"[share.zip] Files:      {count} (~{total/1024:.1f} KiB)")
    return zip_path

# -----------------------------------------------------------------------------
# One-shot bundle creator
# -----------------------------------------------------------------------------
def create_share_bundle(
    repo_root: Path = REPO_ROOT,
    out_root: Path = OUT_ROOT,
    test_root: Optional[Path] = TEST_ROOT,
    label: str | None = LABEL,
) -> Dict[str, str]:
    """
    Build a share bundle:
      <out_root>/share/<TS>__share__<label>/{MANIFEST.json, META.json, *.zip}
    Zip contains:
      repo/...      (contents of repo_root)
      tests/...     (contents of test_root), if provided
      MANIFEST.json (embedded)
    """
    out_dir = _out_share_dir(out_root, label=label)

    roots: list[RootSpec] = [("repo", repo_root)]
    if test_root:
        roots.append(("tests", test_root))

    files = collect_files_from_roots(roots)
    manifest = build_manifest(repo_root, out_root, test_root, files)

    manifest_path = write_manifest(manifest, out_dir)
    zip_path = create_zip_with_manifest(out_dir, repo_root, out_root, test_root, files, manifest=manifest)

    # META shortcut
    (out_dir / "META.json").write_text(json.dumps({
        "repo_root": str(repo_root),
        "out_root": str(out_root),
        "test_root": str(test_root) if test_root else None,
        "label": label,
        "created": _timestamp(),
        "zip": str(zip_path),
        "manifest": str(manifest_path),
    }, indent=2), encoding="utf-8")

    print(f"[share] Output dir: {out_dir}")
    return {"out_dir": str(out_dir), "manifest": str(manifest_path), "zip": str(zip_path)}

# -----------------------------------------------------------------------------
# Script entry
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # -----------------------------------------------------------------------------
    # Defaults (editable)
    # -----------------------------------------------------------------------------


    print(f"[share] Using repo_root={REPO_ROOT}")
    print(f"[share] Using out_root={OUT_ROOT}")
    print(f"[share] Using test_root={TEST_ROOT}")
    res = create_share_bundle(REPO_ROOT, OUT_ROOT, TEST_ROOT, LABEL)
    print(json.dumps(res, indent=2))
