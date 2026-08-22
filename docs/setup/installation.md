# Installation

This page is the simple V1 install path.

All paths below are relative to the repository root unless a clean installed-wheel proof is explicitly described.

## Requirements and qualified platforms

- The package requires Python 3.11 or newer at the metadata/API level.
- The V1 release gate is currently qualified on **Python 3.11** on **Windows** and **Ubuntu/Linux**.
- Newer Python versions or other platforms may work, but are not release-qualified until the same gates are run there.
- A normal C/C++ build toolchain is required if native extensions need to be built locally.
- Git is recommended for source development, but is not part of the installed Python package.

## Simple install

Run this from the repository root:

```text
python install.py
```

On Windows you can also use:

```text
install.bat
```

The installer is deliberately conservative. It:

1. checks the Python version
2. installs the package in editable mode with test extras
3. checks required V1 asset sentinels
4. checks required native imports
5. installs or verifies the required V1 LM3/LM4 release assets
6. runs compact V1 smoke tests

Installer logs are written under:

```text
output/install_logs/
```

To show successful command output while debugging, set this before running the installer:

```text
RDP_INSTALL_VERBOSE=1
```

The installer does not silently upgrade build tools for you. If pip, setuptools,
or wheel are too old, upgrade them deliberately and rerun the installer.

## Large V1 language-model assets

Full V1 requires the LM3/LM4 language-model assets. They are distributed as
GitHub Release zip parts, not committed to normal Git history and not silently
embedded into the production wheel.

`python install.py` first reuses valid local bundles from:

```text
downloads/
```

If the bundles are not there, it downloads the pinned release files listed in
`assets_manifest_v1.json`, verifies each zip by SHA256 and byte size, extracts
them safely under `assets/`, then verifies the final runtime files.

If automatic download fails, use the manual fallback:

```text
Download rdp-v1-lm-large-part*.zip from the V1 GitHub Release.
Place them under downloads/.
Run python install.py again.
```

The installer does not silently downgrade to LM2 if required LM3/LM4 assets are
missing or corrupt. Clean installed-wheel/scorer proofs supply any external full
LM root through the existing explicit `model_root` configuration; RDP does not
search user/home/current-working-directory locations for substitute assets.

## Run the V1 tutorial gate

After install:

```text
python tutorials/v1/run_tutorials.py
```

The pretty-print runner is the normal V1 tutorial review path. Its tutorial
list, thresholds, output policy, and log folder are visible as constants near
the top of `tutorials/v1/run_tutorials.py`.

Generated tutorial output is written under:

```text
output/
```

## Run all tests after a manual install

For the full expert test gate:

```text
python -m pytest -q -p no:cacheprovider
```

This is the same broad pytest command used by full CI.

## CI gates used for V1

The repository has two authoritative validation gates:

1. Normal push gate: `.github/workflows/rdp_v1_full_ci.yml`
   - `ci_light` on Windows and Ubuntu with Python 3.11
   - excludes `full_assets`
   - runs `TutorialRunSet.CI_LIGHT`

2. Manual full proof: `.github/workflows/rdp_v1_full_proof.yml`
   - complete `full_v1` profile
   - all tests and active V1 tutorials
   - Windows and Ubuntu with Python 3.11

The package workflow `.github/workflows/rdp_v1_wheel_build_proof.yml` is a separate
manual packaging proof. It builds CPython 3.11 wheels plus an sdist, performs an
isolated installed-wheel import/native-module check outside `src`, and validates
artifact allow/deny boundaries. It is not a substitute for either validation gate.

## Manual install notes

For normal development, prefer `python install.py`.

If you need to debug the package install manually, the core editable install is:

```text
python -m pip install -e ".[test]"
```

Then run:

```text
python -m pytest -q -p no:cacheprovider tests/contracts
python tutorials/v1/run_tutorials.py
```

Use the full pytest command above before promoting a branch.

## CI install note

GitHub push and pull-request workflows use an internal CI-light install script:

```text
python tools/ci/install_light.py
```

That script is not the user install path. It skips the real large LM download so
ordinary CI does not fetch the release bundles on every run. The full product
contract remains `python install.py`.
