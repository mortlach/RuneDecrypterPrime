from __future__ import annotations

import sys
from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import find_packages, setup


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PACKAGE_ROOT = SRC / "rune_decrypter_prime"


def _rel(path: Path) -> str:
    """Return a setuptools-safe path relative to setup.py."""
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _compile_args() -> list[str]:
    if sys.platform == "win32":
        return ["/O2", "/EHsc", "/std:c++20", "/DNDEBUG"]
    return ["-O3", "-DNDEBUG", "-std=c++20"]


def _extension_if_sources_exist(
    module_name: str,
    sources: list[Path],
    include_dirs: list[Path],
) -> Pybind11Extension | None:
    missing = [path for path in sources if not path.is_file()]
    if missing:
        return None
    return Pybind11Extension(
        module_name,
        sources=[_rel(path) for path in sources],
        include_dirs=[_rel(path) for path in include_dirs],
        extra_compile_args=_compile_args(),
    )


lm_dir = PACKAGE_ROOT / "scoring" / "language_model"
hamming_dir = PACKAGE_ROOT / "scoring" / "hamming"
span_hamming_dir = PACKAGE_ROOT / "scoring" / "span_hamming"

extensions: list[Pybind11Extension] = []

for maybe_ext in (
    _extension_if_sources_exist(
        "rune_decrypter_prime.scoring.language_model._fastlm",
        [lm_dir / "fastlm.cpp"],
        [lm_dir],
    ),
    _extension_if_sources_exist(
        "rune_decrypter_prime.scoring.hamming._hamming",
        [
            hamming_dir / "bindings.cpp",
            hamming_dir / "Hamming.cpp",
            hamming_dir / "Flat2DArray.cpp",
        ],
        [hamming_dir],
    ),
    _extension_if_sources_exist(
        "rune_decrypter_prime.scoring.span_hamming._span_hamming_fast",
        [span_hamming_dir / "fast_bindings.cpp"],
        [span_hamming_dir],
    ),
):
    if maybe_ext is not None:
        extensions.append(maybe_ext)


setup(
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=extensions,
    cmdclass={"build_ext": build_ext},
)
