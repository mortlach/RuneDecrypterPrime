# Installation

RDP requires Python 3.11 or newer. V1 release proof covers Python 3.11 on
Windows and Ubuntu; newer Python versions and other platforms may work but have
not passed that same release matrix.

Use the same Python interpreter to install, run examples and run tests. Mixing
interpreters is an efficient way to create an uninteresting mystery.

## From a source checkout

From the repository root:

```text
python install.py
```

On Windows, the equivalent wrapper is:

```text
install.bat
```

The installer:

1. checks the Python version;
2. installs RDP in editable mode with test dependencies;
3. checks the required native imports;
4. verifies or installs the full V1 language-model assets;
5. runs bounded smoke tests.

Logs are written under `output/install_logs/`. Set `RDP_INSTALL_VERBOSE=1` when
you need successful command output as well as failures.

## Full language-model assets

The complete V1 scoring profile uses LM1–LM4 assets. LM1/LM2 are bundled with
the source. The larger files are pinned GitHub Release archives described by
`assets_manifest_v1.json`; they are not quietly placed in the wheel.

`python install.py` first reuses verified archives in `downloads/`. Otherwise
it downloads the pinned parts, verifies byte size and SHA256, extracts them
safely under `assets/`, and verifies the installed files.

If automatic download is unavailable:

1. download `rdp-v1-lm-large-part*.zip` from the V1 GitHub Release;
2. place the parts in `downloads/`;
3. run `python install.py` again.

Missing full assets do not cause a silent downgrade to a smaller scoring
profile.

## Installed wheel or sdist

The build produces the `rune-decrypter-prime` distribution. Install a local
artifact with pip in the normal way, for example:

```text
python -m pip install path/to/the-built-wheel.whl
```

The Python package contains the public `rdp` namespaces and small runtime data.
The repository’s `tutorials/`, `docs/`, tests and large release assets are not
promised as importable wheel contents. Code in the getting-started files uses
the installed API, but the files themselves are source-checkout companions.

## First proof

After a source install:

```text
python tutorials/v1/getting_started/01_known_key.py
python tutorials/v1/run_tutorials.py
```

The first command checks a known-key round trip. The second runs the normal
release selection and writes full subprocess output under
`output/tutorial_logs/`.

## Validation profiles

- The automatic push/pull-request gate installs the source-bundled `ci_light`
  assets, excludes tests marked `full_assets`, and runs the `RELEASE` group.
- The manual full proof installs `full_v1`, runs the complete pytest suite and
  runs the bounded `FULL_ASSET_EXAMPLES` group on Windows and Ubuntu.
- `QUALIFICATION` is separate. It contains several-hour scientific programs
  and is never part of an ordinary install or release run.

For a manual editable install while diagnosing packaging:

```text
python -m pip install -e ".[test]"
python -m pytest -q -p no:cacheprovider tests/contracts
```

The normal user path remains `python install.py`.
