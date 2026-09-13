# Local Pyodide wheel build and smoke

Build the normal RDP package for WebAssembly and test its installed public API.
This is the same Python/RDP implementation, not a separate web cryptanalysis
engine. Website integration and release automation are outside this tooling.

## Contents

- [Pinned target](#pinned-target)
- [Build](#build)
- [Smoke the wheel](#smoke-the-wheel)

## Pinned target

`versions.json` is consumed by both entry points. The supported stack is:

| Component | Version |
| --- | --- |
| Pyodide | 314.0.6 |
| Python (build host and Pyodide) | 3.14.2 |
| pyodide-build / pyodide-cli | 0.39.0 / 0.5.0 |
| Emscripten | 5.0.3 |
| Node | 24.19.0 |
| Pyodide ABI | 2026_0, wasm32 |

Qualified host: Ubuntu 24.04.4 LTS under WSL2. Linux/WSL needs Bash, Git, tar,
Python and the already-installed external toolchain. Activate the build Python
environment and the matching `emsdk_env.sh`; set `PYODIDE_XBUILDENV_PATH` to its
existing xbuildenv. Tool versions and selected ABI must match exactly. These
scripts do not install/upgrade SDKs or change shell profiles.

## Build

From the repository root, with that environment active:

```sh
bash tools/pyodide/build_wheel.sh
```

Output defaults to ignored `build/pyodide/`; set `RDP_PYODIDE_OUTPUT` to a fresh
external directory if preferred. Relative output paths are repository-relative.
The script stages current **Git-tracked file contents** into a separate generated
directory and builds there. Add new required package files to Git before building.
Untracked downloads and local Full-V1 assets are not copied. The existing package
builder controls CI-light data; the resulting wheel's exact asset allowlist,
hashes, native WASM modules and ABI tag are checked before writing `wheel.json`.

The wheel is under `build/pyodide/wheels/`, with target tag
`cp314-cp314-pyemscripten_2026_0_wasm32`. `wheel.json` records filename, SHA-256,
size, revision, working-tree status, pins and build duration. A prior completed
output is not overwritten: choose a fresh output directory for another build.
Staging and failed-build evidence remain under the output directory for inspection.
Do not commit wheels, build trees, SDKs, caches, or logs.

Do not set local compiler overrides (`CFLAGS`, `CXXFLAGS`, `CPPFLAGS`, `LDFLAGS`,
`EMCC_CFLAGS`, `CC`, `CXX`), `PYTHONPATH` or `PYTHONOPTIMIZE`. Normal safe package
compiler flags are preserved; there is no fast-math or platform-specific tuning.

## Smoke the wheel

Use the same output setting as the build:

```sh
export RDP_PYODIDE_DIST="$(pyodide config get dist_dir)"
node tools/pyodide/run_smoke.mjs
```

Alternatively set `RDP_PYODIDE_WHEEL` to an exact wheel path. Relative wheel paths
are repository-relative. Without that setting, the launcher reads `wheel.json`
and verifies its recorded hash. Node imports the pinned runtime directly from
the external distribution; no npm project or node_modules is needed.

The launcher creates a fresh Pyodide filesystem without mounting the checkout or
inheriting its Python environment. It copies in the selected wheel, installs it
with micropip, and executes `smoke.py`. Compiled dependencies use the pinned
Pyodide package index (NumPy 2.4.6, zstandard 0.25.0, micropip 0.11.1). Pure
Python dependencies use exact pins (tzdata 2026.3, platformdirs 4.11.8)
resolved by micropip; network access to the Pyodide CDN/PyPI is needed on an empty
cache. Package downloads are cached under the output directory.

`smoke.json` and console output report B1–B8: installed RDP location and wheel
byte identity, three extensions, package data, known-key roundtrip, scalar/batch
scoring, exact small Beam recovery, exact fixed-seed GA recovery, and LP loading.
Failures return nonzero. Re-running smoke replaces its generated report.
The default smoke does **not** run the full Welcome Pilgrim search, P7/C7,
campaigns or the full validation suite. No truth-derived initial keys or stop
scores are supplied to its searches.
