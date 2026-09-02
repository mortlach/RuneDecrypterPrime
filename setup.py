from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import find_packages, setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PACKAGE_ROOT = SRC / "rune_decrypter_prime"
CI_ASSET_MANIFEST = ROOT / "assets_manifest_ci_light_v1.json"
CI_ASSET_SOURCE_ROOT = ROOT / "assets"
CI_LM_INDEX_REL = Path("language_model/lmp/index.json")
PACKAGE_DATA_REL = Path("rune_decrypter_prime/data")
PACKAGE_ASSETS_REL = PACKAGE_DATA_REL / "assets"
PACKAGE_CI_MANIFEST_REL = PACKAGE_DATA_REL / "assets_manifest_ci_light_v1.json"

_PACKAGE_EXCLUDES = [
    "rune_decrypter_prime.ciphers.dev",
    "rune_decrypter_prime.ciphers.dev.*",
    "rdp.keyops.dev",
    "rdp.keyops.dev.*",
    "rune_decrypter_prime.data.liber_primus.old",
    "rune_decrypter_prime.data.liber_primus.old.*",
]


def _rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _safe_asset_relpath(value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("CI-light asset manifest contains an empty final_relpath")
    rel = Path(value)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise RuntimeError(f"unsafe CI-light asset path: {value!r}")
    return rel


def _ci_asset_relpaths() -> tuple[Path, ...]:
    data = json.loads(CI_ASSET_MANIFEST.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2:
        raise RuntimeError("unexpected CI-light asset manifest schema")
    rows = data.get("installed_assets")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("CI-light asset manifest has no installed_assets")
    relpaths: list[Path] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("CI-light installed_assets rows must be objects")
        rel = _safe_asset_relpath(row.get("final_relpath"))
        key = rel.as_posix()
        if key in seen:
            raise RuntimeError(f"duplicate CI-light asset path: {key}")
        seen.add(key)
        relpaths.append(rel)
    # Runtime index metadata is required by LmPrimeRuntime but is not itself a
    # scored LM table, so it is carried alongside the manifest-listed assets.
    if CI_LM_INDEX_REL.as_posix() not in seen:
        relpaths.append(CI_LM_INDEX_REL)
    for rel in relpaths:
        source = CI_ASSET_SOURCE_ROOT / rel
        if not source.is_file():
            raise RuntimeError(f"source-bundled CI-light asset missing: {source}")
    return tuple(relpaths)


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


class A5BuildPy(_build_py):
    """Stage only the exact source-bundled CI-light runtime assets into wheels."""

    def _extra_outputs(self) -> list[Path]:
        build_root = Path(self.build_lib)
        outputs = [build_root / PACKAGE_CI_MANIFEST_REL]
        outputs.extend(build_root / PACKAGE_ASSETS_REL / rel for rel in _ci_asset_relpaths())
        return outputs

    def run(self) -> None:
        super().run()
        outputs = self._extra_outputs()
        manifest_target = outputs[0]
        manifest_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CI_ASSET_MANIFEST, manifest_target)
        for rel, target in zip(_ci_asset_relpaths(), outputs[1:]):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(CI_ASSET_SOURCE_ROOT / rel, target)

    def get_outputs(self, include_bytecode: int = 1) -> list[str]:
        base = list(super().get_outputs(include_bytecode=include_bytecode))
        return base + [str(path) for path in self._extra_outputs()]


class A5Sdist(_sdist):
    """Stage the exact CI-light asset allowlist into sdists, never local full assets."""

    def make_release_tree(self, base_dir: str, files: list[str]) -> None:
        super().make_release_tree(base_dir, files)
        release_root = Path(base_dir)
        # The manifest itself is already included by MANIFEST.in; copying again
        # is intentional and makes the source of this staged contract explicit.
        shutil.copyfile(CI_ASSET_MANIFEST, release_root / CI_ASSET_MANIFEST.name)
        for rel in _ci_asset_relpaths():
            source = CI_ASSET_SOURCE_ROOT / rel
            target = release_root / "assets" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


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
        [hamming_dir / "bindings.cpp", hamming_dir / "Hamming.cpp", hamming_dir / "Flat2DArray.cpp"],
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
    packages=find_packages(where="src", exclude=_PACKAGE_EXCLUDES),
    package_dir={"": "src"},
    ext_modules=extensions,
    cmdclass={"build_ext": build_ext, "build_py": A5BuildPy, "sdist": A5Sdist},
)
