from __future__ import annotations

import os
import shutil
import sys
import traceback
from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

HERE = Path(__file__).resolve().parent
SRC_CPP = [
    HERE / "bindings.cpp",
    HERE / "Hamming.cpp",
    HERE / "Flat2DArray.cpp",
]
PKG_MOD = "rune_decrypter_prime.scoring.hamming._hamming"


def _find_repo_root(start: Path) -> Path:
    p = start
    while True:
        if (p / "rune_decrypter_prime").is_dir():
            return p
        if p.parent == p:
            return start
        p = p.parent


REPO_ROOT = _find_repo_root(HERE)

if sys.platform == "win32":
    compile_args = ["/O2", "/EHsc", "/std:c++20", "/DNDEBUG"]
    link_args = []
else:
    compile_args = ["-O3", "-DNDEBUG", "-std=c++20"]
    link_args = []

ext_modules = [
    Pybind11Extension(
        PKG_MOD,
        sources=[str(s) for s in SRC_CPP],
        include_dirs=[str(HERE)],
        extra_compile_args=compile_args,
        extra_link_args=link_args,
    )
]

BUILD_TEMP = REPO_ROOT / "build_tmp_hamming"
BUILD_LIB = REPO_ROOT / "build_lib_hamming"
BUILD_TEMP.mkdir(exist_ok=True)
BUILD_LIB.mkdir(exist_ok=True)


class _BuildExtShort(build_ext):
    def finalize_options(self):
        super().finalize_options()
        self.build_temp = str(BUILD_TEMP)
        self.build_lib = str(BUILD_LIB)
        os.makedirs(self.build_temp, exist_ok=True)
        os.makedirs(self.build_lib, exist_ok=True)
        self.inplace = True


def _ensure_default_args():
    if len(sys.argv) == 1:
        sys.argv += ["build_ext", "--inplace"]


def _dest_ext_suffix() -> str:
    from distutils.sysconfig import get_config_var

    return get_config_var("EXT_SUFFIX") or (
        ".pyd" if sys.platform == "win32" else ".so"
    )


def _copy_built():
    suffix = _dest_ext_suffix()
    built_dir = BUILD_LIB / "rune_decrypter_prime" / "scoring" / "hamming"
    cand = sorted(built_dir.glob(f"_hamming*{suffix}"))
    if not cand:
        print("[hamming] WARNING: Built artifact not found in:", built_dir)
        return None
    src = cand[0]
    dest = HERE / f"_hamming{suffix}"
    shutil.copy2(src, dest)
    print(f"[hamming] Copied: {src} -> {dest}")
    return dest


def _try_import():
    print("\n[hamming] Verifying import …")
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        from rune_decrypter_prime.scoring.hamming import _hamming  # type: ignore

        print("[hamming] SUCCESS Import OK:", _hamming)
    except Exception:
        print("[hamming] WARNING Import failed:")
        traceback.print_exc()


def main():
    print("============================================================")
    print(" Building optional _hamming extension (C++)")
    print(" Repo root:", REPO_ROOT)
    print("============================================================")

    os.chdir(REPO_ROOT)
    _ensure_default_args()
    setup(
        name="rune-decrypter-prime-hamming",
        version="0.1.0",
        description="Optional Hamming scorer for rune_decrypter_prime",
        ext_modules=ext_modules,
        cmdclass={"build_ext": _BuildExtShort},
        options={
            "build_ext": {
                "inplace": True,
                "build_lib": str(BUILD_LIB),
                "build_temp": str(BUILD_TEMP),
            }
        },
    )
    _copy_built()
    _try_import()
    print("\n[hamming] Done.")


if __name__ == "__main__":
    main()
