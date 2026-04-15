from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

# ---------------------------------------------------------------------------
# One-click extended review bundle (hardcoded switches; no CLI args)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]

SRC_ROOT = REPO_ROOT / "src"
TEST_ROOT = REPO_ROOT / "tests"
TOOLS_BENCHMARK_ROOT = REPO_ROOT / "tools" / "benchmarks"
TOOLS_GET_SRC_ZIP_ROOT = REPO_ROOT / "tools" / "get_src_zip"
PLANNING_WORKING_ROOT = REPO_ROOT / "planning" / "projects" / "no_wli"
NO_WLI_OUTPUT_ROOT = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
)
ROOT_FILES: tuple[Path, ...] = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "requirements.txt",
    Path(__file__).resolve(),
)

OUTPUT_ROOT = REPO_ROOT / "output" / "tools" / "get_src_extended_review_bundle"

USE_TIMESTAMPED_NAME = True
ZIP_STEM = "get_src_extended_review_bundle"
STATIC_ZIP_NAME = "get_src_extended_review_bundle.zip"
WRITE_SUMMARY_JSON = True

BENCHMARK_INCLUDE_ROOT_NAMES = {
    "periodic_sub_trans",
    "solve_proof",
    "scoring",
    "community",
    "config",
}
BENCHMARK_INCLUDE_FILE_NAMES = {
    "README.md",
    "tidy_output_root.py",
    "bench_solve_periodic_columnar_pipeline_no_wli.py",
    "bench_solve_periodic_columnar_pipeline_col_then_sub.py",
    "bench_solve_periodic_columnar_pipeline_sub_then_col.py",
}

COMMON_EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".vscode",
    ".idea",
    "build_tmp_fastlm",
    "build_lib_fastlm",
    "build_tmp_hamming",
    "build_lib_hamming",
}
CODE_EXCLUDED_DIR_NAMES = COMMON_EXCLUDED_DIR_NAMES | {
    "data",
}
PLANNING_EXCLUDED_DIR_PREFIXES = (
    "no_wli_external_review_pack_",
    "no_wli_deep_research_pack_",
)
COMMON_EXCLUDED_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".obj",
    ".o",
    ".bin",
    ".npy",
    ".npz",
    ".zip",
    ".7z",
    ".tar",
    ".gz",
    ".zst",
}
COMMON_EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}
COMMON_EXCLUDED_FILE_GLOBS = {
    "*.bin.zst",
}


@dataclass(frozen=True)
class BundleRootSpec:
    scan_root: Path
    root_label: str
    excluded_dir_names: frozenset[str] = frozenset(COMMON_EXCLUDED_DIR_NAMES)
    excluded_dir_prefixes: tuple[str, ...] = ()
    include_path: Callable[[Path], bool] | None = None
    recursive: bool = True


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _zip_name() -> str:
    if USE_TIMESTAMPED_NAME:
        return f"{ZIP_STEM}__{_utc_stamp()}.zip"
    return STATIC_ZIP_NAME


def _to_repo_rel(path: Path, repo_root: Path) -> str:
    p = path.resolve()
    r = repo_root.resolve()
    try:
        return str(p.relative_to(r)).replace("\\", "/")
    except ValueError:
        return "<external>"


def _has_excluded_dir(
    rel_path: Path,
    *,
    excluded_dir_names: frozenset[str],
    excluded_dir_prefixes: Sequence[str],
) -> bool:
    for part in rel_path.parts[:-1]:
        if part in excluded_dir_names:
            return True
        if any(part.startswith(prefix) for prefix in excluded_dir_prefixes):
            return True
    return False


def _is_excluded_file(rel_path: Path) -> bool:
    if rel_path.name in COMMON_EXCLUDED_FILE_NAMES:
        return True
    if rel_path.suffix.lower() in COMMON_EXCLUDED_FILE_SUFFIXES:
        return True
    return any(rel_path.match(glob) for glob in COMMON_EXCLUDED_FILE_GLOBS)


def _make_benchmark_include_path(
    benchmark_root: Path,
) -> Callable[[Path], bool]:
    def _include_benchmark_path(path: Path) -> bool:
        try:
            rel = path.relative_to(benchmark_root)
        except ValueError:
            return False
        if len(rel.parts) == 1:
            return rel.name in BENCHMARK_INCLUDE_FILE_NAMES
        return rel.parts[0] in BENCHMARK_INCLUDE_ROOT_NAMES

    return _include_benchmark_path


def _collect_single_file(
    *,
    repo_root: Path,
    file_path: Path,
    included: list[Path],
    excluded: list[str],
) -> None:
    if not file_path.exists():
        excluded.append(f"[missing] {_to_repo_rel(file_path, repo_root)}")
        return
    if not file_path.is_file():
        excluded.append(f"[not_file] {_to_repo_rel(file_path, repo_root)}")
        return
    rel = Path(_to_repo_rel(file_path, repo_root))
    if _is_excluded_file(rel):
        excluded.append(str(rel).replace("\\", "/"))
        return
    included.append(file_path)


def collect_files_from_root(
    *,
    repo_root: Path,
    spec: BundleRootSpec,
) -> tuple[list[Path], list[str]]:
    if not spec.scan_root.exists():
        return [], [f"[missing] {spec.root_label}: {_to_repo_rel(spec.scan_root, repo_root)}"]

    if spec.scan_root.is_file():
        included: list[Path] = []
        excluded: list[str] = []
        _collect_single_file(
            repo_root=repo_root,
            file_path=spec.scan_root,
            included=included,
            excluded=excluded,
        )
        return included, excluded

    walker = spec.scan_root.rglob("*") if spec.recursive else spec.scan_root.glob("*")
    included = []
    excluded = []
    for path in sorted(walker):
        if path.is_dir():
            continue
        rel_from_root = path.relative_to(spec.scan_root)
        rel_repo = str(path.relative_to(repo_root)).replace("\\", "/")
        if _has_excluded_dir(
            rel_from_root,
            excluded_dir_names=spec.excluded_dir_names,
            excluded_dir_prefixes=spec.excluded_dir_prefixes,
        ):
            excluded.append(rel_repo)
            continue
        if _is_excluded_file(rel_from_root):
            excluded.append(rel_repo)
            continue
        if spec.include_path is not None and not spec.include_path(path):
            excluded.append(rel_repo)
            continue
        included.append(path)
    return included, excluded


def _default_root_specs(
    *,
    repo_root: Path,
    src_root: Path,
    test_root: Path,
    benchmark_root: Path,
    tools_get_src_zip_root: Path,
    planning_working_root: Path,
    no_wli_output_root: Path,
    root_files: Iterable[Path],
) -> tuple[BundleRootSpec, ...]:
    specs = [
        BundleRootSpec(
            scan_root=src_root,
            root_label="src",
            excluded_dir_names=frozenset(CODE_EXCLUDED_DIR_NAMES),
        ),
        BundleRootSpec(
            scan_root=test_root,
            root_label="tests",
            excluded_dir_names=frozenset(COMMON_EXCLUDED_DIR_NAMES),
        ),
        BundleRootSpec(
            scan_root=benchmark_root,
            root_label="tools/benchmarks",
            excluded_dir_names=frozenset(CODE_EXCLUDED_DIR_NAMES),
            include_path=_make_benchmark_include_path(benchmark_root),
        ),
        BundleRootSpec(
            scan_root=tools_get_src_zip_root,
            root_label="tools/get_src_zip",
            excluded_dir_names=frozenset(CODE_EXCLUDED_DIR_NAMES),
        ),
        BundleRootSpec(
            scan_root=planning_working_root,
            root_label="planning/projects/no_wli",
            excluded_dir_names=frozenset(COMMON_EXCLUDED_DIR_NAMES),
            excluded_dir_prefixes=PLANNING_EXCLUDED_DIR_PREFIXES,
        ),
        BundleRootSpec(
            scan_root=no_wli_output_root,
            root_label="output/tools/benchmarks/periodic_sub_trans/no_wli",
            excluded_dir_names=frozenset(COMMON_EXCLUDED_DIR_NAMES),
        ),
    ]
    specs.extend(
        BundleRootSpec(
            scan_root=file_path,
            root_label=_to_repo_rel(file_path, repo_root),
            excluded_dir_names=frozenset(COMMON_EXCLUDED_DIR_NAMES),
        )
        for file_path in root_files
    )
    return tuple(specs)


def collect_review_bundle_files(
    *,
    repo_root: Path = REPO_ROOT,
    src_root: Path = SRC_ROOT,
    test_root: Path = TEST_ROOT,
    benchmark_root: Path = TOOLS_BENCHMARK_ROOT,
    tools_get_src_zip_root: Path = TOOLS_GET_SRC_ZIP_ROOT,
    planning_working_root: Path = PLANNING_WORKING_ROOT,
    no_wli_output_root: Path = NO_WLI_OUTPUT_ROOT,
    root_files: Sequence[Path] = ROOT_FILES,
) -> tuple[list[Path], list[str], list[dict[str, object]]]:
    seen: set[Path] = set()
    included_all: list[Path] = []
    excluded_all: list[str] = []
    root_summaries: list[dict[str, object]] = []

    specs = _default_root_specs(
        repo_root=repo_root,
        src_root=src_root,
        test_root=test_root,
        benchmark_root=benchmark_root,
        tools_get_src_zip_root=tools_get_src_zip_root,
        planning_working_root=planning_working_root,
        no_wli_output_root=no_wli_output_root,
        root_files=root_files,
    )
    for spec in specs:
        included, excluded = collect_files_from_root(repo_root=repo_root, spec=spec)
        unique_included = []
        for path in included:
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            unique_included.append(path)
            included_all.append(path)
        excluded_all.extend(excluded)
        root_summaries.append(
            {
                "root_label": spec.root_label,
                "scan_root": _to_repo_rel(spec.scan_root, repo_root),
                "included_files_count": int(len(unique_included)),
                "excluded_entries_count": int(len(excluded)),
            }
        )

    return included_all, excluded_all, root_summaries


def make_get_src_extended_review_bundle(
    *,
    repo_root: Path = REPO_ROOT,
    src_root: Path = SRC_ROOT,
    test_root: Path = TEST_ROOT,
    benchmark_root: Path = TOOLS_BENCHMARK_ROOT,
    tools_get_src_zip_root: Path = TOOLS_GET_SRC_ZIP_ROOT,
    planning_working_root: Path = PLANNING_WORKING_ROOT,
    no_wli_output_root: Path = NO_WLI_OUTPUT_ROOT,
    output_root: Path = OUTPUT_ROOT,
    zip_path_override: Path | None = None,
    root_files: Sequence[Path] = ROOT_FILES,
) -> dict[str, object]:
    output_root.mkdir(parents=True, exist_ok=True)
    included, excluded, root_summaries = collect_review_bundle_files(
        repo_root=repo_root,
        src_root=src_root,
        test_root=test_root,
        benchmark_root=benchmark_root,
        tools_get_src_zip_root=tools_get_src_zip_root,
        planning_working_root=planning_working_root,
        no_wli_output_root=no_wli_output_root,
        root_files=root_files,
    )

    zip_path = zip_path_override if zip_path_override is not None else output_root / _zip_name()
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED, compresslevel=9) as zf:
        for file_path in included:
            arcname = _to_repo_rel(file_path, repo_root)
            if arcname == "<external>":
                continue
            zf.write(file_path, arcname=arcname)

    summary: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": ".",
        "zip_path": _to_repo_rel(zip_path, repo_root),
        "included_files_count": int(len(included)),
        "excluded_entries_count": int(len(excluded)),
        "zip_size_bytes": int(zip_path.stat().st_size),
        "roots": root_summaries,
    }

    if WRITE_SUMMARY_JSON:
        summary_path = zip_path.with_suffix(".summary.json")
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary["summary_path"] = _to_repo_rel(summary_path, repo_root)

    return summary


def main() -> int:
    summary = make_get_src_extended_review_bundle()
    print("[get_src_extended_review_bundle] complete")
    print(f"[get_src_extended_review_bundle] zip={summary['zip_path']}")
    print(
        "[get_src_extended_review_bundle] files "
        f"included={summary['included_files_count']} "
        f"excluded={summary['excluded_entries_count']}"
    )
    print(f"[get_src_extended_review_bundle] size_bytes={summary['zip_size_bytes']}")
    if "summary_path" in summary:
        print(f"[get_src_extended_review_bundle] summary={summary['summary_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
