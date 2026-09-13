"""Build the three V1 release-native modules in-place without installing RDP.

Ordinary LM scoring needs _fastlm. The canonical setup.py also builds the
retained Hamming and fast span-Hamming modules. --all additionally builds the
experimental n-gram Hamming module using its unchanged single-target builder.
Python dependencies and a C++ compiler must already be available.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import uuid
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SETUP_PY = ROOT / "setup.py"
NGRAM_REL = Path("src/rdp/scoring/ngram_hamming")
NGRAM_BUILDER = ROOT / NGRAM_REL / "setup_ngram_hamming_fast.py"
BUILD_REQUIREMENTS = ("setuptools", "pybind11", "wheel")
RELEASE_NATIVE_MODULES = (
    "rdp.scoring.language_model._fastlm",
    "rdp.scoring.hamming._hamming",
    "rdp.scoring.span_hamming._span_hamming_fast",
)
EXPERIMENTAL_NATIVE_MODULES = (
    "rdp.scoring.ngram_hamming._ngram_hamming_fast",
)


def _selected_modules(all_native: bool) -> tuple[str, ...]:
    return RELEASE_NATIVE_MODULES + (EXPERIMENTAL_NATIVE_MODULES if all_native else ())


def _missing_build_requirements() -> tuple[str, ...]:
    return tuple(name for name in BUILD_REQUIREMENTS if importlib.util.find_spec(name) is None)


def _output_directory() -> Path:
    inherited = os.environ.get("RDP_OUTPUT_ROOT")
    if inherited is not None:
        if not inherited.strip() or not Path(inherited).is_absolute():
            raise ValueError("RDP_OUTPUT_ROOT must be a nonempty absolute path")
        base = Path(inherited).resolve()
    else:
        base = Path(tempfile.gettempdir()).resolve() / "rdp"
    output = base / "build_native" / uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    return output


def _run(command: list[str], *, label: str, log: Path, cwd: Path = ROOT) -> None:
    print(f"\n{label}", flush=True)
    # JSON preserves argument boundaries, including Windows paths with spaces.
    print("  " + json.dumps(command), flush=True)
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    with log.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps({"command": command, "cwd": str(cwd)}) + "\n")
        stream.flush()
        with subprocess.Popen(
            command, cwd=cwd, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        ) as process:
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="", flush=True)
                stream.write(line)
                stream.flush()
            code = process.wait()
        if code:
            raise RuntimeError(f"{label} failed with exit code {code}; see {log}")


def _artifact(root: Path, module: str) -> Path:
    suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if not suffix:
        raise RuntimeError("this Python does not report a native extension suffix")
    return root / (module.replace(".", "/") + suffix)


def _require_artifacts(root: Path, modules: tuple[str, ...]) -> None:
    missing = [name for name in modules if not _artifact(root, name).is_file()]
    if missing:
        raise RuntimeError("build did not produce the selected modules: " + ", ".join(missing))


def _build_release(output: Path) -> None:
    library = output / "lib"
    _run(
        [sys.executable, "-B", "-X", "utf8", str(SETUP_PY),
         "build_ext", "--inplace", "--build-temp", str(output / "tmp"),
         "--build-lib", str(library)],
        label="Building V1 release-native extensions", log=output / "release.log",
    )
    # Do not let an old in-place binary conceal a missing source or skipped build.
    _require_artifacts(library, RELEASE_NATIVE_MODULES)


def _build_experimental(output: Path) -> None:
    # The retained builder owns its flags and creates short build directories
    # beside its source. Stage only its inputs so those directories stay external.
    stage = output / "research"
    (stage / "tools").mkdir(parents=True)
    inputs = [
        Path("pyproject.toml"), Path("README.md"), Path("LICENSE"),
        Path("src/rdp/__init__.py"), Path("src/rdp/scoring/__init__.py"),
        *(NGRAM_REL / name for name in (
            "__init__.py", "reference.py", "fast_backend.py", "bridge.py",
            "report_only_telemetry.py", "setup_ngram_hamming_fast.py",
            "fast_bindings.cpp", "FastNgramHamming.h",
        )),
    ]
    for relative in inputs:
        source = ROOT / relative
        if not source.is_file():
            raise RuntimeError(f"experimental build input missing: {relative.as_posix()}")
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    builder = stage / NGRAM_BUILDER.relative_to(ROOT)
    # Absolute source names are repeated below build_temp by distutils, which
    # can exceed Windows linker path limits. Only change their spelling, not
    # the retained builder's sources, compiler flags or extension configuration.
    code = r'''
import runpy
import sys
from pathlib import Path

builder = Path(sys.argv[1]).resolve()
namespace = runpy.run_path(str(builder), run_name="rdp_local_ngram_build")
root = namespace["REPO_ROOT"]
for extension in namespace["ext_modules"]:
    extension.sources = [Path(source).resolve().relative_to(root).as_posix()
                         for source in extension.sources]
sys.argv = [str(builder)]
namespace["main"]()
'''
    _run(
        [sys.executable, "-B", "-X", "utf8", "-c", code, str(builder)],
        label="Building retained experimental n-gram Hamming extension",
        log=output / "experimental.log", cwd=stage,
    )
    _require_artifacts(stage / "src", EXPERIMENTAL_NATIVE_MODULES)
    for name in EXPERIMENTAL_NATIVE_MODULES:
        shutil.copy2(_artifact(stage / "src", name), _artifact(SRC, name))


def _verify(modules: tuple[str, ...], output: Path) -> None:
    code = r'''
import importlib
import importlib.machinery
import json
import sys
import sysconfig
from pathlib import Path

spec = json.loads(sys.argv[1])
src = Path(spec["src"]).resolve()
sys.path.insert(0, str(src))
failures = []
for name in spec["modules"]:
    try:
        module = importlib.import_module(name)
        actual = Path(module.__file__).resolve()
        expected = src / (name.replace(".", "/") + sysconfig.get_config_var("EXT_SUFFIX"))
        if actual != expected or not isinstance(module.__loader__, importlib.machinery.ExtensionFileLoader):
            raise RuntimeError("import did not resolve to this checkout's native build")
    except Exception as exc:
        failures.append(name)
        print(f"[FAIL] {name}: {exc}")
    else:
        print(f"[ OK ] {name}: {actual.relative_to(src).as_posix()}")
if failures:
    raise SystemExit(1)
'''
    payload = json.dumps({"src": str(SRC), "modules": modules})
    _run(
        [sys.executable, "-I", "-B", "-X", "utf8", "-c", code, payload],
        label="Verifying fresh-process imports from this checkout",
        log=output / "imports.log",
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RDP native extensions in-place from this checkout")
    parser.add_argument("--all", action="store_true",
                        help="also build the retained experimental _ngram_hamming_fast extension")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not SETUP_PY.is_file():
        print("setup.py is missing from this checkout", file=sys.stderr)
        return 2
    if args.all and not NGRAM_BUILDER.is_file():
        print("experimental n-gram Hamming builder is missing", file=sys.stderr)
        return 2
    missing = _missing_build_requirements()
    if missing:
        print("Missing Python build requirements: " + ", ".join(missing), file=sys.stderr)
        print("Install them in this Python environment: python -m pip install pybind11 setuptools wheel",
              file=sys.stderr)
        print("A working C++ compiler is also required.", file=sys.stderr)
        return 2
    print("Rune Decrypter Prime native source build")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print("Default build: the three V1 release-native modules")
    print("Ordinary LM scoring specifically requires _fastlm")
    try:
        output = _output_directory()
        print(f"Build evidence: {output}", flush=True)
        _build_release(output)
        if args.all:
            _build_experimental(output)
        _verify(_selected_modules(args.all), output)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"\nBuild failed: {exc}", file=sys.stderr)
        print("Check the build log, C++ compiler and this Python's build requirements.",
              file=sys.stderr)
        return 1
    print("\nNative modules are ready in this checkout")
    if not args.all:
        print("Use --all to also build the retained experimental n-gram Hamming native module")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
