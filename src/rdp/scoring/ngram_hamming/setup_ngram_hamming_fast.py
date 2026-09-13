from __future__ import annotations

import os
import shutil
import sys
import traceback
from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup


HERE = Path(__file__).resolve().parent
SRC_CPP = [HERE / "fast_bindings.cpp"]
PKG_MOD = "rdp.scoring.ngram_hamming._ngram_hamming_fast"


def _find_repo_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / "src").is_dir() and (parent / "tools").is_dir():
            return parent
    return start


REPO_ROOT = _find_repo_root(HERE)

if sys.platform == "win32":
    COMPILE_ARGS = ["/Ox", "/Ob2", "/Oi", "/Ot", "/GL", "/EHsc", "/std:c++20", "/DNDEBUG"]
    LINK_ARGS: list[str] = ["/LTCG"]
else:
    COMPILE_ARGS = ["-O3", "-march=native", "-DNDEBUG", "-std=c++20"]
    LINK_ARGS = []

ext_modules = [
    Pybind11Extension(
        PKG_MOD,
        sources=[str(path) for path in SRC_CPP],
        include_dirs=[str(HERE)],
        extra_compile_args=COMPILE_ARGS,
        extra_link_args=LINK_ARGS,
    )
]

BUILD_TEMP = REPO_ROOT / "build_tmp_ngram_hamming_fast"
BUILD_LIB = REPO_ROOT / "build_lib_ngram_hamming_fast"
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


def _ensure_default_args() -> None:
    if len(sys.argv) == 1:
        sys.argv += ["build_ext", "--inplace"]


def _dest_ext_suffix() -> str:
    from distutils.sysconfig import get_config_var

    return get_config_var("EXT_SUFFIX") or (".pyd" if sys.platform == "win32" else ".so")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def _copy_built() -> Path | None:
    suffix = _dest_ext_suffix()
    built_dir = BUILD_LIB / "rdp" / "scoring" / "ngram_hamming"
    candidates = sorted(built_dir.glob(f"_ngram_hamming_fast*{suffix}"))
    if not candidates:
        print("[ngram_hamming_fast] WARNING: built artifact not found in:", _repo_rel(built_dir))
        return None
    src = candidates[0]
    dest = HERE / f"_ngram_hamming_fast{suffix}"
    shutil.copy2(src, dest)
    print(f"[ngram_hamming_fast] copied: {_repo_rel(src)} -> {_repo_rel(dest)}")
    return dest


def _try_import() -> None:
    print("\n[ngram_hamming_fast] verifying import ...")
    src_dir = REPO_ROOT / "src"
    for path in (REPO_ROOT, src_dir):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    try:
        from rdp.scoring.ngram_hamming import _ngram_hamming_fast  # type: ignore

        print("[ngram_hamming_fast] import OK:", _ngram_hamming_fast.__name__)
    except Exception:
        print("[ngram_hamming_fast] WARNING import failed:")
        traceback.print_exc()


def main() -> None:
    print("============================================================")
    print(" Building optional _ngram_hamming_fast extension (C++)")
    print(" Repo root:", _repo_rel(REPO_ROOT))
    print("============================================================")

    os.chdir(REPO_ROOT)
    _ensure_default_args()
    setup(
        name="rune-decrypter-prime-ngram-hamming-fast",
        version="0.1.0",
        description="Optional fast n-gram Hamming backend for Rune Decrypter Prime",
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
    print("\n[ngram_hamming_fast] done.")


if __name__ == "__main__":
    main()
