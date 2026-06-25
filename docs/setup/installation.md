# Installation

This page is the simple V1 install path.

All paths below are relative to the repository root.

## Requirements

- Python 3.11+
- A normal C/C++ build toolchain if native extensions need to be built locally
- Git is recommended, but not part of the Python package itself

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
5. runs compact V1 smoke tests

Installer logs are written under:

```text
output/install_logs/
```

To show successful command output while debugging, set this before running the
installer:

```text
RDP_INSTALL_VERBOSE=1
```

The installer does not silently upgrade build tools for you. If pip, setuptools,
or wheel are too old, upgrade them deliberately and rerun the installer.

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

The repository has three useful gates:

1. Full CI

   ```text
   .github/workflows/rdp_v1_full_ci.yml
   ```

   Runs install, full pytest, and the V1 release tutorial runner on Windows and
   Ubuntu.

2. Wheel CI

   ```text
   .github/workflows/rdp_v1_wheel_ci.yml
   ```

   Builds CPython 3.11 wheels on Windows and Ubuntu, installs them in a wheel
   test environment, checks native imports, and uploads wheel artifacts.

3. Install smoke

   ```text
   .github/workflows/install-smoke.yml
   ```

   Runs the clean installer path on Windows and Ubuntu.

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
