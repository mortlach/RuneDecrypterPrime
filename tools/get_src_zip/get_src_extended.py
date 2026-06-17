from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

# ---------------------------------------------------------------------------
# One-click source zipper (hardcoded switches; no CLI args by repo rule)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

SRC_ROOT = REPO_ROOT / "src"
TEST_ROOT = REPO_ROOT / "tests"

BENCHMARK_ROOT = REPO_ROOT / "tools" / "benchmarks"
BENCHMARK_ROOT = REPO_ROOT / "tutorials"

# Only include these subfolders under tools/benchmarks (edit to suit your repo).
# Examples: {"periodic_sub_trans", "scoring", "community"}
INCLUDED_BENCHMARK_SUBDIRS: set[str] = {
    "v1",
    # "periodic_sub_trans",
    # "scoring",
    # "community",
}

OUTPUT_ROOT = REPO_ROOT / "output" / "tools" / "benchmarks" / "zip_src_nobloat"

USE_TIMESTAMPED_NAME = True
ZIP_STEM = "src_test_bench_nobloat"
STATIC_ZIP_NAME = "src_test_bench_nobloat.zip"
WRITE_SUMMARY_JSON = True

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "data",
    "build_tmp_fastlm",
    "build_lib_fastlm",
    "build_tmp_hamming",
    "build_lib_hamming",
}

EXCLUDED_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".obj",
    ".o",
}

EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}

EXCLUDED_FILE_GLOBS = {
    "*.bin",
    "*.bin.zst",
    "*.npz",
    "*.npy",
}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _zip_name() -> str:
    if USE_TIMESTAMPED_NAME:
        return f"{ZIP_STEM}__{_utc_stamp()}.zip"
    return STATIC_ZIP_NAME


def _has_excluded_dir(rel_path: Path) -> bool:
    return any(part in EXCLUDED_DIR_NAMES for part in rel_path.parts)


def _is_excluded_file(rel_path: Path) -> bool:
    name = rel_path.name
    if name in EXCLUDED_FILE_NAMES:
        return True
    if rel_path.suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return True
    return any(rel_path.match(glob) for glob in EXCLUDED_FILE_GLOBS)


def _to_repo_rel(path: Path, repo_root: Path) -> str:
    p = path.resolve()
    r = repo_root.resolve()
    try:
        return str(p.relative_to(r)).replace("\\", "/")
    except ValueError:
        return "<external>"


def _is_under_allowed_benchmark_subdir(path: Path) -> bool:
    """
    True if path is under tools/benchmarks/<allowed>/...
    If INCLUDED_BENCHMARK_SUBDIRS is empty, include nothing from benchmarks.
    """
    if not INCLUDED_BENCHMARK_SUBDIRS:
        return False

    try:
        rel = path.relative_to(BENCHMARK_ROOT)
    except ValueError:
        return False

    # rel is like "<subdir>/.../file.py"
    parts = rel.parts
    if not parts:
        return False
    return parts[0] in INCLUDED_BENCHMARK_SUBDIRS


def collect_files_from_root(
    *,
    repo_root: Path,
    scan_root: Path,
    root_label: str,
    benchmark_mode: bool = False,
) -> tuple[list[Path], list[str]]:
    """
    Collect includable files under scan_root.

    - Excludes paths containing EXCLUDED_DIR_NAMES anywhere in the relative path.
    - Excludes files by suffix/name/glob.
    - If benchmark_mode=True, only includes files under allowed benchmark subdirs.
    """
    if not scan_root.exists():
        # Treat missing roots as "nothing to do" rather than hard fail.
        return [], [f"[missing] {root_label}: {scan_root}"]

    included: list[Path] = []
    excluded: list[str] = []

    for path in sorted(scan_root.rglob("*")):
        if path.is_dir():
            continue

        if benchmark_mode and not _is_under_allowed_benchmark_subdir(path):
            arcname = str(path.relative_to(repo_root)).replace("\\", "/")
            excluded.append(arcname)
            continue

        rel_from_root = path.relative_to(scan_root)

        if _has_excluded_dir(rel_from_root):
            arcname = str(path.relative_to(repo_root)).replace("\\", "/")
            excluded.append(arcname)
            continue

        if _is_excluded_file(rel_from_root):
            arcname = str(path.relative_to(repo_root)).replace("\\", "/")
            excluded.append(arcname)
            continue

        included.append(path)

    return included, excluded


def make_zip_src_nobloat(
    *,
    repo_root: Path = REPO_ROOT,
    src_root: Path = SRC_ROOT,
    test_root: Path = TEST_ROOT,
    benchmark_root: Path = BENCHMARK_ROOT,
    output_root: Path = OUTPUT_ROOT,
    zip_path_override: Path | None = None,
) -> dict[str, object]:
    output_root.mkdir(parents=True, exist_ok=True)

    included_all: list[Path] = []
    excluded_all: list[str] = []

    inc, exc = collect_files_from_root(repo_root=repo_root, scan_root=src_root, root_label="src")
    included_all.extend(inc)
    excluded_all.extend(exc)

    inc, exc = collect_files_from_root(repo_root=repo_root, scan_root=test_root, root_label="test")
    included_all.extend(inc)
    excluded_all.extend(exc)

    inc, exc = collect_files_from_root(
        repo_root=repo_root,
        scan_root=benchmark_root,
        root_label="tools/benchmarks",
        benchmark_mode=True,
    )
    included_all.extend(inc)
    excluded_all.extend(exc)

    zip_path = zip_path_override if zip_path_override is not None else (output_root / _zip_name())
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED, compresslevel=9) as zf:
        for file_path in included_all:
            arcname = str(file_path.relative_to(repo_root)).replace("\\", "/")
            zf.write(file_path, arcname=arcname)

    summary: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": ".",
        "src_root": _to_repo_rel(src_root, repo_root),
        "test_root": _to_repo_rel(test_root, repo_root),
        "benchmark_root": _to_repo_rel(benchmark_root, repo_root),
        "included_benchmark_subdirs": sorted(INCLUDED_BENCHMARK_SUBDIRS),
        "zip_path": _to_repo_rel(zip_path, repo_root),
        "included_files_count": int(len(included_all)),
        "excluded_files_count": int(len(excluded_all)),
        "zip_size_bytes": int(zip_path.stat().st_size),
    }

    if WRITE_SUMMARY_JSON:
        summary_path = zip_path.with_suffix(".summary.json")
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary["summary_path"] = _to_repo_rel(summary_path, repo_root)

    return summary


def main() -> int:
    summary = make_zip_src_nobloat()
    print("[zip_src_nobloat] complete")
    print(f"[zip_src_nobloat] zip={summary['zip_path']}")
    print(
        "[zip_src_nobloat] files "
        f"included={summary['included_files_count']} excluded={summary['excluded_files_count']}"
    )
    print(f"[zip_src_nobloat] size_bytes={summary['zip_size_bytes']}")
    if "summary_path" in summary:
        print(f"[zip_src_nobloat] summary={summary['summary_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
