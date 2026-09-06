# Installation

RDP requires Python 3.11 or newer. V1 release proof covers Python 3.11 on
Windows and Ubuntu; newer Python versions and other platforms may work but have
not passed that same release matrix.

Use the same Python interpreter to install RDP, run examples and run tests.
Mixing interpreters is an efficient way to create an uninteresting mystery.

## Source checkout

From the repository root:

```text
python install.py
```

`python install.py` is the canonical source-install route. On Windows,
`install.bat` calls the same installer.

The installer:

1. checks the Python version;
2. installs RDP in editable mode with test dependencies;
3. reuses or provisions a working Torch CUDA runtime when supported NVIDIA
   hardware is detected;
4. checks the package and required native-extension imports;
5. installs or verifies the `full_v1` language-model asset profile;
6. runs a compact smoke-test selection.

CUDA provisioning only makes GPU execution available. It does not change a run
from CPU to CUDA; normal `RunSpec` requests still default to
`api.ComputeDevice.CPU`.

Installer evidence is written below the selected output root as
`install/<run-id>/`. In a source checkout the default root is `output/`, so the
usual path is `output/install/<run-id>/`. Set `RDP_INSTALL_VERBOSE=1` when you
need successful command output as well as failures.

See [output locations](../development/output_locations.md) for output-root
selection and [CUDA provisioning](../development/cuda_installation.md) for the
GPU policy.

## Full language-model assets

The complete `full_v1` profile contains the supported LM1-LM4 character and WLI
assets. The small LM1/LM2 baseline is source-bundled; the larger runtime files
are pinned release assets described by `assets_manifest_v1.json`.

`python install.py` first reuses verified archives in `downloads/`. Otherwise
it downloads the pinned parts, verifies their size and SHA-256, extracts them
safely under `assets/`, and verifies the installed files.

If automatic download is unavailable:

1. download the `rdp-v1-lm-large-part*.zip` files from the V1 GitHub Release;
2. place them in `downloads/`;
3. run `python install.py` again.

Missing full assets are an error. RDP does not quietly substitute the smaller
CI-light profile.

## Wheel or sdist

The distribution name is `rune-decrypter-prime`. A built wheel can be installed
with pip in the normal way, for example:

```text
python -m pip install path/to/the-built-wheel.whl
```

A plain pip install installs the package. It does not run RDP's source installer,
provision CUDA for the machine, or download the external full-asset bundle.

The installed package contains the public `rdp` namespaces and packaged runtime
data. Repository tutorials, documentation, tests and large release assets are
source-checkout companions rather than promised importable wheel contents.

## First proof

After a source install, run the first getting-started example:

```text
python -m tutorials.v1.getting_started.01_known_key
```

It encrypts a short message and decrypts it with the same known key. There is no
search involved yet; the point is simply to prove that the installed public API
works.

Then run the normal tutorial selection:

```text
python tutorials/v1/run_tutorials.py
```

For the rest of the learning route, continue with the
[quickstart](../guides/quickstart.md).

## CPU, CUDA and scoring backends

CPU is the default compute device. To request GPU execution, use
`api.ComputeDevice.CUDA` in the run specification. Scoring backend selection is
a separate typed choice; `ScorerBackend.AUTO` resolves against the requested
device and available capabilities.

An explicitly requested unavailable device or backend blocks clearly rather
than silently changing the request. See
[scorer backend selection](scorer_backend_selection.md).

## Validation levels

A successful `python install.py` proves the source install, full asset profile,
required imports and compact smoke tests. It is not the whole release matrix.

Maintainers use the CI-light push gate for ordinary changes and the manual full
proof for the complete Windows/Ubuntu release check. Several-hour qualification
runs are separate scientific work.

See the [install validation playbook](install_validation.md) for those checks.
