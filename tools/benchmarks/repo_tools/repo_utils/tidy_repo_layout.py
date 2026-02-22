#!/usr/bin/env python3
"""
tidy_repo_layout.py - normalize repo layout (non-destructive by default).

What it does (with --apply):
  - Move legacy trees to archive/<TS>/
  - Flatten tests/tests/* into tests/*
  - Sweep any tests/**/output/* into output/legacy_tests_migrated/<TS>/{relative}
  - Move rune_decrypter_prime/output/* into output/legacy_pkg_migrated/<TS>/{relative}
  - Create pytest.ini at repo root if missing (testpaths = tests)
  - Write output/tidy/<TS>/TIDY_REPORT.json
Dry-run is the default; use --apply to actually change files.
"""



from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass, asdict
import argparse, hashlib, json, os, shutil, sys, time
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------
# Config / helpers
# ---------------------------------------------------------------------

def _ts() -> str:
    # windows-safe timestamp (no colons)
    return time.strftime("%Y-%m-%dT%H-%M-%S%z")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]

@dataclass
class Moves:
    moved: List[Tuple[str, str]]
    skipped_identical: List[str]
    conflicts: List[Tuple[str, str]]
    errors: List[Tuple[str, str]]
    removed_empty_dirs: List[str]

@dataclass
class Report:
    repo_root: str
    timestamp: str
    dry_run: bool
    archive_dir: str
    legacy_pkg_out: str
    legacy_tests_out: str
    moves: Moves

def sha256_file(p: Path, chunk: int = 1 << 18) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def same_file(a: Path, b: Path) -> bool:
    try:
        return a.stat().st_size == b.stat().st_size and sha256_file(a) == sha256_file(b)
    except Exception:
        return False

def move_file(src: Path, dst: Path, do_apply: bool, moves: Moves) -> None:
    ensure_dir(dst.parent)
    if dst.exists():
        # identical? then skip
        if src.is_file() and dst.is_file() and same_file(src, dst):
            moves.skipped_identical.append(str(src))
            return
        # conflict: park under sibling "conflicts"
        conflict_dst = dst.parent / ("CONFLICT__" + dst.name)
        if do_apply:
            shutil.move(str(src), str(conflict_dst))
        moves.conflicts.append((str(src), str(conflict_dst)))
        return
    if do_apply:
        shutil.move(str(src), str(dst))
    moves.moved.append((str(src), str(dst)))

def rm_empty_dirs(root: Path, do_apply: bool, moves: Moves) -> None:
    # remove empty dirs bottom-up
    for d in sorted([p for p in root.rglob("*") if p.is_dir()], key=lambda p: len(str(p)), reverse=True):
        try:
            if any(d.iterdir()):
                continue
            if do_apply:
                d.rmdir()
            moves.removed_empty_dirs.append(str(d))
        except Exception as e:
            moves.errors.append((str(d), f"rmdir failed: {e!s}"))

# ---------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------

def archive_legacy(repo: Path, archive_root: Path, do_apply: bool, moves: Moves) -> None:
    for name in ("LEGACY_CODE", "rune_decrypter_prime_OLD_REF"):
        src = repo / name
        if src.exists():
            dst = archive_root / name
            ensure_dir(archive_root)
            if do_apply:
                shutil.move(str(src), str(dst))
            moves.moved.append((str(src), str(dst)))

def flatten_tests(repo: Path, do_apply: bool, moves: Moves) -> None:
    tests = repo / "tests"
    nested = tests / "tests"
    if not nested.exists():
        return
    # walk nested and move files up relative to tests/
    for p in nested.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(nested)  # want tests/<rel>
        target = tests / rel
        move_file(p, target, do_apply, moves)
    # remove empty dirs left behind
    rm_empty_dirs(nested, do_apply, moves)
    # remove the container folder if empty
    try:
        if not any(nested.iterdir()):
            if do_apply:
                nested.rmdir()
            moves.removed_empty_dirs.append(str(nested))
    except FileNotFoundError:
        pass

def sweep_tests_out(repo: Path, legacy_tests_out: Path, do_apply: bool, moves: Moves) -> None:
    tests = repo / "tests"
    if not tests.exists():
        return
    # any "output" dir under tests/** gets moved
    for outdir in sorted(tests.rglob("output")):
        if not outdir.is_dir():
            continue
        rel_from_tests = outdir.relative_to(tests)
        dst_root = legacy_tests_out / rel_from_tests.parent
        # move contents, preserve substructure
        for p in outdir.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(outdir)
            move_file(p, dst_root / rel, do_apply, moves)
        # cleanup emptied outdir
        rm_empty_dirs(outdir, do_apply, moves)
        try:
            if do_apply and outdir.exists():
                outdir.rmdir()
                moves.removed_empty_dirs.append(str(outdir))
        except Exception as e:
            moves.errors.append((str(outdir), f"post-sweep rmdir failed: {e!s}"))

def migrate_pkg_out(repo: Path, legacy_pkg_out: Path, do_apply: bool, moves: Moves) -> None:
    pkg_out = repo / "rune_decrypter_prime" / "output"
    if not pkg_out.exists():
        return
    # move everything inside to legacy_pkg_out/<same_rel>
    for p in pkg_out.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(pkg_out)
        move_file(p, legacy_pkg_out / rel, do_apply, moves)
    rm_empty_dirs(pkg_out, do_apply, moves)
    try:
        if do_apply and pkg_out.exists():
            pkg_out.rmdir()
            moves.removed_empty_dirs.append(str(pkg_out))
    except Exception as e:
        moves.errors.append((str(pkg_out), f"post-migrate rmdir failed: {e!s}"))

def ensure_pytest_ini(repo: Path, do_apply: bool, moves: Moves) -> None:
    ini = repo / "pytest.ini"
    if ini.exists():
        return
    content = (
        "[pytest]\n"
        "testpaths = tests\n"
        "addopts = -q\n"
    )
    if do_apply:
        ini.write_text(content, encoding="utf-8")
    moves.moved.append(("<create pytest.ini>", str(ini)))

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Repo layout tidy")
    parser.add_argument("--apply", action="store_true", help="Perform changes (default is dry-run)")
    parser.add_argument("--out-root", default="output", help="Where to write reports and legacy migrations")
    args = parser.parse_args()

    repo = _repo_root()
    out_root = (repo / args.out_root).resolve()
    ts = _ts()

    tidy_root = out_root / "tidy" / ts
    archive_root = repo / "archive" / ts
    legacy_tests_out = out_root / "legacy_tests_migrated" / ts
    legacy_pkg_out = out_root / "legacy_pkg_migrated" / ts
    for p in (tidy_root, archive_root, legacy_tests_out, legacy_pkg_out):
        ensure_dir(p)

    moves = Moves(moved=[], skipped_identical=[], conflicts=[], errors=[], removed_empty_dirs=[])

    # execute steps
    archive_legacy(repo, archive_root, args.apply, moves)
    flatten_tests(repo, args.apply, moves)
    sweep_tests_out(repo, legacy_tests_out, args.apply, moves)
    migrate_pkg_out(repo, legacy_pkg_out, args.apply, moves)
    ensure_pytest_ini(repo, args.apply, moves)

    # report
    report = Report(
        repo_root=str(repo),
        timestamp=ts,
        dry_run=not args.apply,
        archive_dir=str(archive_root),
        legacy_pkg_out=str(legacy_pkg_out),
        legacy_tests_out=str(legacy_tests_out),
        moves=moves,
    )
    (tidy_root / "TIDY_REPORT.json").write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

    # pretty summary + exit code
    total_moves = len(moves.moved)
    total_conflicts = len(moves.conflicts)
    total_errors = len(moves.errors)

    print("\n" + "=" * 72)
    print(("DRY-RUN" if not args.apply else "APPLY") + " — TIDY SUMMARY")
    print("-" * 72)
    print(f"repo root:       {repo}")
    print(f"archive dir:     {archive_root}")
    print(f"legacy tests ->  {legacy_tests_out}")
    print(f"legacy package ->{legacy_pkg_out}")
    print(f"moved items:     {total_moves}")
    print(f"skipped identical:{len(moves.skipped_identical)}")
    print(f"conflicts:       {total_conflicts}")
    print(f"errors:         {total_errors}")
    print(f"report:          {tidy_root / 'TIDY_REPORT.json'}")
    print("=" * 72)

    if total_errors > 0:
        print("❌ Tidy finished WITH ERRORS (see report).")
        return 2
    if total_conflicts > 0:
        print("⚠️ Tidy hit conflicts; your files were preserved as CONFLICT__*. Review and resolve.")
        # still success, but warn
        return 0
    print("✅ Tidy finished cleanly.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
