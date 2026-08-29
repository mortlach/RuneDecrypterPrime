# ============================================================
# rune_decrypter_prime/scoring/language_model/setup_fastlm.py
# One-file builder for the optional _fastlm extension.
# Edit BUILD_MODE below, then run this module with any Python workflow.
# ============================================================

from __future__ import annotations

from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
from pathlib import Path
import shutil
import sys
import traceback
import os

# --- toggle here only ---
BUILD_MODE: str = "safe"  # change to "fastmath" for local benchmarking

HERE = (
    Path(__file__).resolve().parent
)  # .../rune_decrypter_prime/scoring/language_model
SRC_CPP = HERE / "fastlm.cpp"
PKG_MOD = "rune_decrypter_prime.scoring.language_model._fastlm"


def find_repo_root(start: Path) -> Path:
    """Walk upward until we find a folder containing 'rune_decrypter_prime/'."""
    p = start
    while True:
        if (p / "rune_decrypter_prime").is_dir():
            return p
        if p.parent == p:
            # fallback to start if not found
            return start
        p = p.parent


REPO_ROOT = find_repo_root(HERE)  # should resolve to .../rune_decrypter_2
PKG_DIR = REPO_ROOT / "rune_decrypter_prime"

# Compile flags (portable by default; only flip the string to 'fastmath' for local speed)
if sys.platform == "win32":
    compile_args = ["/O2", "/EHsc", "/std:c++20", "/DNDEBUG"]
    link_args = []
    if BUILD_MODE == "fastmath":
        compile_args += ["/arch:AVX2", "/fp:fast"]
else:
    compile_args = ["-O3", "-DNDEBUG"]
    link_args = []
    if BUILD_MODE == "fastmath":
        compile_args += ["-ffast-math", "-march=native", "-funroll-loops"]

ext_modules = [
    Pybind11Extension(
        PKG_MOD,
        sources=[str(SRC_CPP)],
        include_dirs=[str(HERE)],
        extra_compile_args=compile_args,
        extra_link_args=link_args,
    )
]

# Short build dirs (under the real repo root → avoids long Windows paths)
BUILD_TEMP = REPO_ROOT / "build_tmp_fastlm"
BUILD_LIB = REPO_ROOT / "build_lib_fastlm"
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
    """Copy built _fastlm.*.pyd/.so into the package folder next to fastlm.cpp."""
    suffix = _dest_ext_suffix()
    built_dir = BUILD_LIB / "rune_decrypter_prime" / "scoring" / "language_model"
    cand = sorted(built_dir.glob(f"_fastlm*{suffix}"))
    if not cand:
        print("[fastlm] WARNING  Built artifact not found in:", built_dir)
        return None
    src = cand[0]
    dest = HERE / f"_fastlm{suffix}"
    shutil.copy2(src, dest)
    print(f"[fastlm] Copied: {src}  ->  {dest}")
    return dest


def _try_import():
    print("\n[fastlm] Verifying import ...")
    # Ensure the actual repo root is on sys.path
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        from rune_decrypter_prime.scoring.language_model import _fastlm  # type: ignore

        print("[fastlm] SUCCESS Import OK:", _fastlm)
    except Exception:
        print("[fastlm] WARNING  Import failed:")
        traceback.print_exc()


def main():
    print("============================================================")
    print(" Building optional _fastlm extension (one-click)")
    print(" Build mode:  ", BUILD_MODE)
    print(" Repo root:   ", REPO_ROOT)
    print("============================================================")
    # Critical: run setup() from the detected repo root
    os.chdir(REPO_ROOT)

    _ensure_default_args()
    setup(
        name="rune-decrypter-prime-fastlm",
        version="0.1.0",
        description="Optional fast LM scorer for rune_decrypter_prime",
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
    print("\n[fastlm] Done.")


if __name__ == "__main__":
    main()
