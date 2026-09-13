# Build and packaging notes

[Installation](installation.md) is the simplest complete setup.
[Using RDP](../guides/using_rdp.md) covers direct source use and interactive Python.

RDP is mostly Python with native scoring modules underneath. Building from
source is supported and encouraged when you want to inspect or change those
modules. A prebuilt release wheel does not require a local RDP compiler.

## Build the native modules locally

Use the Python environment where you will run RDP. Install the runtime and
Python-side build requirements:

```text
python -m pip install numpy zstandard tzdata platformdirs
python -m pip install pybind11 setuptools wheel
python tools/build_native.py
```

The helper delegates to the canonical `setup.py build_ext --inplace` build.
It uses the current environment rather than creating an isolated build
environment, and does not install dependencies or fetch language-model assets.

The default builds the same three modules as the current V1 release package:

- `_fastlm` is required for ordinary language-model scoring
- `_hamming` supports retained specialist dictionary-Hamming scoring
- `_span_hamming_fast` supports retained fast span-Hamming research and probes

Neither Hamming extension is required by the normal tutorial groups. The
production span-Hamming backend is Python, separate from its fast probe backend.

To additionally build the retained experimental n-gram Hamming module:

```text
python tools/build_native.py --all
```

That fourth binary remains outside release wheels and does not become a default
ranking signal. The retained single-module builders are still available. The
helper runs the experimental builder on a temporary copy of its inputs, keeping
its compiler settings unchanged and its scratch files outside the checkout.

The helper verifies selected imports in a fresh process and checks that they
come from this checkout. Build failure or import failure returns nonzero.
Only the compiled modules are placed in `src/rdp`. Logs and temporary build
files are kept under an absolute `RDP_OUTPUT_ROOT`, or the system temporary
directory if it is unset. Failed-build evidence is retained for diagnosis.

### Compiler prerequisites

You need a C++20-capable compiler and headers for the Python interpreter you use:

- Windows: Microsoft C++ Build Tools with the C++ workload and Windows SDK
- Linux: a C++ compiler such as GCC and the matching Python development headers
- macOS: a compatible Clang toolchain and SDK are plausible, but macOS is not
  part of V1's qualified desktop build matrix

V1's desktop baseline is CPython 3.11 on Windows and Ubuntu. Interpreter
architecture and compiled-module architecture must match.

The canonical release flags remain `/O2 /EHsc /std:c++20 /DNDEBUG` on Windows
and `-O3 -DNDEBUG -std=c++20` elsewhere. The helper does not introduce its own
compiler configuration or alter the retained experimental builder's flags.

Editing C++ does not rebuild an existing `.pyd` or `.so`, even with an editable
install. Run the native build again, then restart Python before using the new
binary. Python-only edits are different, as explained in
[Editable install](../guides/using_rdp.md#editable-install).

## Wheel check

The [Python wheel workflow](../../.github/workflows/rdp_v1_wheel_build_proof.yml)
builds eight wheels: CPython 3.11, 3.12, 3.13 and 3.14 on Windows and Linux
x86-64. Each job installs its wheel in an isolated environment, checks the
native modules and public API operations, and verifies package contents.
The routine CI matrix separately runs the CI-light tests and release tutorials
on all four Python versions on Windows and Ubuntu.

Package-related pull requests run the wheel workflow automatically. It can
also be run manually, and the full release proof calls the same workflow.
Each job uploads its packages and checksums. The final collection job verifies
all eight wheels and produces one `rdp-v1-native-packages-<commit>` artifact
containing the wheels, the Linux 3.11 source archive and `SHA256SUMS.txt`.
The source archive is independent of the Python version used to install it.

For additional wheels from an existing release, run the workflow manually from
the branch containing the build changes and set `source_ref` to the release tag
(for example, `v1.0.0`). The workflow resolves that reference once and uses the
resulting commit for all eight package builds and CI-light test/tutorial jobs.
The test environment supplies `setuptools` even when the old source does not list
it as a test dependency. The source checkout is not patched.

The job summaries and `SHA256SUMS.txt` record the package source commit separately
from the workflow run commit. The combined package artifact is produced only after
all builds and any requested source-validation jobs pass. With `source_ref` blank,
normal PR and full-proof builds use their triggering commit, as before.

These are CI artifacts tied to the checked-out commit. Published downloads are
listed on the [releases page](https://github.com/mortlach/RuneDecrypterPrime/releases).

The canonical 53-job solver and full-asset validation remains on Python 3.11.
Pyodide uses its separate pinned WebAssembly environment; these desktop builds
do not extend the CUDA or other platform qualification.

See [Install validation](install_validation.md) for the distinction between
routine, full and qualification checks.

## Compiled scoring code

The compiled scoring sources live under:

```text
src/rdp/scoring/language_model/
src/rdp/scoring/hamming/
src/rdp/scoring/span_hamming/
src/rdp/scoring/ngram_hamming/
```

If one of these areas moves, the package configuration needs the corresponding
change.

Changes to the scoring behaviour itself should also be reflected in
[Scoring](../guides/scoring.md) and the
[Scoring parameter reference](../reference/parameters/scoring.md).

## Source development

For ordinary development from a checkout:

```text
python install.py
```

The wheel workflow is for changes where the package build itself is under test.

For the wider implementation route, see
[Development](../development/README.md) and
[Contributing](../../CONTRIBUTING.md).
