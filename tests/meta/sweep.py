from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


ALLOWED_TOP_DIRS = {
    "src",
    "docs",
    "tools",
    "tests",
    "tutorials",
    "assets_packed",
    "solve",
}

ALLOWED_TOOLS_SUBDIRS = {
    "assets",
    "benchmarks",
    "ci",
    "docs_lint",
    "git_link_scrape",
    "repo_tidy",
    "repo_utils",
    "scaffold",
    "symbols",
}

# solve/ is a legacy shim kept as README-only.
ALLOWED_SOLVE_SUBDIRS: set[str] = set()

FORBIDDEN_ROOT_OUTPUT_FILES = {
    "setup.log",
    "setup_report.json",
    "preflight.log",
    "preflight_report.json",
    "benchmark_ready.json",
}

IGNORED_TOP_DIRS = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    # Generated local asset workspace from community setup/preflight.
    "assets",
    # Local working notes; intentionally top-level and gitignored.
    "planning",
    "output",
}

LOCAL_ONLY_ROOT_FILES = {
    # Agent/dev-ops context; local-only like planning/ and not distributable RDP content.
    "AGENTS.md",
}

ABSOLUTE_PATH_FIXTURE_FILES = {
    # Named privacy/redaction tests deliberately contain machine-path examples.
    Path("tests/test_artifact_policy.py"),
    Path("tests/scoring/test_retained_state_plaintext_rescore.py"),
}

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
    ".tsv",
    ".ps1",
    ".sh",
    ".bat",
    ".rst",
    ".xml",
}

WINDOWS_ABS_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:(?:\\|/)")
UNIX_ABS_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:home|Users|opt|var|etc|private|tmp|mnt|srv|root)/")


@dataclass(frozen=True)
class SweepIssue:
    kind: str
    path: str
    detail: str
    line: int | None = None


@dataclass(frozen=True)
class SweepResult:
    tree_issues: Sequence[SweepIssue]
    absolute_path_issues: Sequence[SweepIssue]

    @property
    def has_issues(self) -> bool:
        return bool(self.tree_issues or self.absolute_path_issues)


def _iter_repo_files(repo_root: Path) -> List[Path]:
    """
    Return repo-relative file paths without using git commands.

    We only walk policy-managed roots and root-level files. Runtime/cache folders
    (for example output/, .venv/, .git/) are excluded by top-level name.
    """
    files: List[Path] = []
    for child in repo_root.iterdir():
        if child.name in IGNORED_TOP_DIRS:
            continue
        if child.is_file():
            if child.name in LOCAL_ONLY_ROOT_FILES:
                continue
            files.append(child.relative_to(repo_root))
            continue
        if not child.is_dir():
            continue
        if child.name not in ALLOWED_TOP_DIRS:
            # Kept out of file scan; tree policy checks handle this separately.
            continue
        if child.name == "tools":
            for sub_name in sorted(ALLOWED_TOOLS_SUBDIRS):
                sub = child / sub_name
                if not sub.exists():
                    continue
                for entry in sub.rglob("*"):
                    if entry.is_file():
                        files.append(entry.relative_to(repo_root))
            continue
        if child.name == "solve":
            for sub_name in sorted(ALLOWED_SOLVE_SUBDIRS):
                sub = child / sub_name
                if not sub.exists():
                    continue
                for entry in sub.rglob("*"):
                    if entry.is_file():
                        files.append(entry.relative_to(repo_root))
            continue
        for entry in child.rglob("*"):
            if entry.is_file():
                files.append(entry.relative_to(repo_root))
    return sorted(files)


def _check_top_level_policy(repo_root: Path, *, strict: bool) -> List[SweepIssue]:
    """
    Check top-level directory policy.

    strict=False: report only managed roots when they violate nested rules.
    strict=True: fail if any non-ignored top-level directory is outside allow-list.
    """
    if not strict:
        return []
    issues: List[SweepIssue] = []
    for child in sorted(repo_root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        if child.name in IGNORED_TOP_DIRS:
            continue
        if child.name not in ALLOWED_TOP_DIRS:
            issues.append(
                SweepIssue(
                    kind="tree_policy",
                    path=child.name,
                    detail=f"top-level directory '{child.name}' is not in allowed set {sorted(ALLOWED_TOP_DIRS)}",
                )
            )
    tools_dir = repo_root / "tools"
    if tools_dir.exists():
        for child in sorted(tools_dir.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir():
                continue
            if child.name in ALLOWED_TOOLS_SUBDIRS:
                continue
            issues.append(
                SweepIssue(
                    kind="tree_policy",
                    path=f"tools/{child.name}",
                    detail=f"tools subdir '{child.name}' is not in allowed set {sorted(ALLOWED_TOOLS_SUBDIRS)}",
                )
            )
    solve_dir = repo_root / "solve"
    if solve_dir.exists():
        for child in sorted(solve_dir.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir():
                continue
            if child.name in ALLOWED_SOLVE_SUBDIRS:
                continue
            if ALLOWED_SOLVE_SUBDIRS:
                detail = f"solve subdir '{child.name}' is not in allowed set {sorted(ALLOWED_SOLVE_SUBDIRS)}"
            else:
                detail = f"solve subdir '{child.name}' is not allowed (solve/ is README-only shim)"
            issues.append(
                SweepIssue(
                    kind="tree_policy",
                    path=f"solve/{child.name}",
                    detail=detail,
                )
            )
    return issues


def _check_tree_policy(paths: Iterable[Path]) -> List[SweepIssue]:
    issues: List[SweepIssue] = []

    for p in paths:
        parts = p.parts
        if len(parts) == 1 and parts[0] in FORBIDDEN_ROOT_OUTPUT_FILES:
            issues.append(
                SweepIssue(
                    kind="tree_policy",
                    path=parts[0],
                    detail="runtime artifact must be written under output/, not repo root",
                )
            )
            continue
        if len(parts) <= 1:
            continue
        if parts[0] == "tools":
            if len(parts) < 2 or parts[1] not in ALLOWED_TOOLS_SUBDIRS:
                issues.append(
                    SweepIssue(
                        kind="tree_policy",
                        path=p.as_posix(),
                        detail=(
                            "tracked tools path must be under "
                            f"tools/{' or tools/'.join(sorted(ALLOWED_TOOLS_SUBDIRS))}"
                        ),
                    )
                )
        if parts[0] == "solve":
            if len(parts) < 2 or parts[1] not in ALLOWED_SOLVE_SUBDIRS:
                if ALLOWED_SOLVE_SUBDIRS:
                    detail = (
                        "tracked solve path must be under "
                        f"solve/{' or solve/'.join(sorted(ALLOWED_SOLVE_SUBDIRS))}"
                    )
                else:
                    detail = "tracked solve path is not allowed; keep solve/ as README-only shim"
                issues.append(
                    SweepIssue(
                        kind="tree_policy",
                        path=p.as_posix(),
                        detail=detail,
                    )
                )
    return issues


def _is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def _check_absolute_paths(repo_root: Path, paths: Iterable[Path]) -> List[SweepIssue]:
    issues: List[SweepIssue] = []
    for rel_path in paths:
        if rel_path in ABSOLUTE_PATH_FIXTURE_FILES:
            continue
        if not _is_text_candidate(rel_path):
            continue
        full_path = repo_root / rel_path
        if not full_path.exists():
            continue
        try:
            lines = full_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for line_no, line in enumerate(lines, start=1):
            if WINDOWS_ABS_RE.search(line) or UNIX_ABS_RE.search(line):
                preview = line.strip()
                if len(preview) > 140:
                    preview = preview[:137] + "..."
                issues.append(
                    SweepIssue(
                        kind="absolute_path",
                        path=rel_path.as_posix(),
                        line=line_no,
                        detail=preview,
                    )
                )
    return issues


def run_sweep(repo_root: Path, *, strict_top_level: bool = False) -> SweepResult:
    repo_root = repo_root.resolve()
    repo_paths = _iter_repo_files(repo_root)
    tree_issues = _check_top_level_policy(repo_root, strict=strict_top_level)
    tree_issues.extend(_check_tree_policy(repo_paths))
    absolute_path_issues = _check_absolute_paths(repo_root, repo_paths)
    return SweepResult(tree_issues=tree_issues, absolute_path_issues=absolute_path_issues)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repo tidy sweep checks.")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--strict-top-level",
        action="store_true",
        help="Fail when any non-ignored top-level directory is outside the allow-list.",
    )
    args = parser.parse_args()

    result = run_sweep(Path(args.repo_root), strict_top_level=args.strict_top_level)
    if result.tree_issues:
        print("[tree-policy]")
        for issue in result.tree_issues:
            print(f"  - {issue.path}: {issue.detail}")
    if result.absolute_path_issues:
        print("[absolute-paths]")
        for issue in result.absolute_path_issues:
            line_suffix = f":{issue.line}" if issue.line else ""
            print(f"  - {issue.path}{line_suffix}: {issue.detail}")

    if result.has_issues:
        print(
            f"FAILED: {len(result.tree_issues)} tree issue(s), "
            f"{len(result.absolute_path_issues)} absolute-path issue(s)"
        )
        return 1

    print("OK: repo tidy sweep passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
