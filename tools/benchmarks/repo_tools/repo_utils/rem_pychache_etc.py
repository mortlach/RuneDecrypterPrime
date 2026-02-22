from __future__ import annotations

import argparse
import os
import shutil
import stat
from pathlib import Path
from typing import Dict, Union


def delete_pycache_folders(
    root: Union[str, Path],
    *,
    dry_run: bool = True,
    verbose: bool = False,
) -> Dict[str, int]:
    """
    Recursively find and delete all ``__pycache__`` directories under ``root``.
    """
    root_path = Path(root).expanduser().resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"Root path does not exist: {root_path}")
    if root_path == Path(root_path.anchor):
        raise ValueError(f"Refusing to run on filesystem root: {root_path}")

    found = 0
    deleted = 0

    def _on_rm_error(func, path, _exc_info):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    for dirpath, dirnames, _ in os.walk(root_path, topdown=True, followlinks=False):
        for name in list(dirnames):
            if name != "__pycache__":
                continue
            target = Path(dirpath) / name
            found += 1
            if verbose:
                action = "Would remove" if dry_run else "Removing"
                print(f"{action}: {target}")
            if not dry_run:
                try:
                    shutil.rmtree(target, onerror=_on_rm_error)
                    deleted += 1
                except Exception as exc:
                    if verbose:
                        print(f"Failed to remove {target}: {exc}")
            dirnames.remove(name)

    return {"found": found, "deleted": deleted}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete __pycache__ folders under a target tree.")
    parser.add_argument("--target", type=Path, default=_repo_root(), help="Root to scan (default: repo root).")
    parser.add_argument("--apply", action="store_true", help="Actually delete instead of dry-run.")
    parser.add_argument("--verbose", action="store_true", help="Print each touched directory.")
    args = parser.parse_args()
    summary = delete_pycache_folders(args.target, dry_run=not args.apply, verbose=args.verbose)
    print(summary)


if __name__ == "__main__":
    main()
