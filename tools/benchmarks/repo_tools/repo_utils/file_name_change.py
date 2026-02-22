from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]


def copy_with_renames(root: Path) -> None:
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            new_name = filename.replace("fwd", "ltr").replace("rev", "rtl")
            if new_name == filename:
                continue
            src = Path(dirpath) / filename
            dst = Path(dirpath) / new_name
            if dst.exists():
                print(f"Skipped (exists): {dst}")
                continue
            shutil.copy2(src, dst)
            print(f"Copied: {src} -> {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy language-model artefacts while renaming fwd/rev to ltr/rtl.")
    default_root = _repo_root() / "src" / "rune_decrypter_prime" / "data" / "language_model" / "lmp"
    parser.add_argument(
        "target",
        nargs="?",
        default=default_root,
        type=Path,
        help="Root folder to process (default: data/language_model/lmp)",
    )
    args = parser.parse_args()
    copy_with_renames(args.target.resolve())


if __name__ == "__main__":
    main()
