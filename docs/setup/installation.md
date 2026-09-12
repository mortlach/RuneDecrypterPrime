# Installation

RDP needs Python 3.11 or newer. V1 is tested on Python 3.11 on Windows and
Ubuntu.

From the repository root:

```text
python install.py
```

That root command is the standard and simplest entry point. Optional platform
wrappers are kept under `tools/installation/`:

```text
tools/installation/install.ps1
tools/installation/install.bat
tools/installation/install.sh
```

Each wrapper resolves the repository root from its own location and invokes the
same root `install.py`.

The installer installs the checkout, checks the compiled parts of RDP, makes
sure the V1 language files are available, and checks the install at the end.

It uses the Python environment that launched it. It does not create or select
an environment for you.

## Externally managed Python on Linux

Some Linux distributions protect their system Python using PEP 668. On those
systems, pip may refuse the package-installation step.

The installer reports this case and leaves the choice with you. Run it with
another Python or from an environment you manage, or explicitly override the
protection:

```text
python install.py --break-system-packages
```

That option allows pip to modify an externally managed Python installation.
RDP never enables it automatically.

See [Troubleshooting](../guides/troubleshooting.md) if pip still refuses the
installation.

A supported NVIDIA GPU can also be prepared for CUDA. RDP still uses CPU unless
a run asks for CUDA explicitly.

For the run-side choice, see
[CPU, CUDA and scoring](scorer_backend_selection.md).

## Language files

The smaller LM1 and LM2 language files are included with the source.

The larger LM3 and LM4 files are release assets. The source installer checks
for them and obtains them when needed.

If the automatic download is unavailable, place the V1 large-language-model
release archives in `downloads/` and run the same installer command again.

A missing required asset is an error. RDP does not silently replace it with a
different scoring setup.

That behaviour follows the project rule that requested capabilities should fail
clearly rather than quietly change the experiment.

See [Language-model assets](language_model_assets.md) for profiles, pinned
manifests and verification, and
[Project aims and design principles](../project_overview.md) for the design rule.

## Check the install

Run:

```text
python -m tutorials.v1.getting_started.01_known_key
```

This checks the public known-key path.

Then run the normal tutorial set:

```text
python tutorials/v1/run_tutorials.py
```

The tutorial groups and their purpose are described in
[Tutorials and examples](../tutorials/README.md).

## Installing a built wheel

For an existing wheel:

```text
python -m pip install path/to/downloaded-release.whl
```

A wheel installs the package itself.

The source installer remains the normal route for a complete checkout with the
V1 assets and machine-specific CUDA checks.

## What this proves

A successful install shows that the package installed, required assets were
found, key imports work and the installer checks passed.

It does not replace the larger release or qualification checks.

See [Install validation](install_validation.md) for the different validation
levels, then [Quickstart](../guides/quickstart.md) for the first solve.

## Installer command output

Use `python install.py --verbose` to stream child-command output while keeping
the same installation logs. The default keeps successful command output quiet.
