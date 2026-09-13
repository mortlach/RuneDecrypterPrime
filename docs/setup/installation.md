# Installation

RDP needs Python 3.11 or newer. Routine CI tests CPython 3.11, 3.12, 3.13 and
3.14 on Windows and Ubuntu. The longer 53-job release validation runs on 3.11.

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

The full installer is not the only way to use a checkout. [Using RDP](../guides/using_rdp.md)
covers direct source use, editable installs, local native builds and interactive
Python. A tutorial needs the dependencies and capabilities it uses, not a fresh
full installation before every run.

The installer installs the checkout, checks the compiled parts of RDP, makes
sure the V1 language files are available, and checks the install at the end.

It uses the Python environment that launched it. It does not create or select
an environment for you.

For example, `python3.12 install.py` on Linux builds and installs RDP for that
Python 3.12 environment. To use a virtual environment, create it with the
Python version you want, then run the installer with that environment's Python.
The source installer builds locally; it does not download a prebuilt RDP wheel
or switch Python versions.

## Download and install V1 from the command line

These commands download the `v1.0.0` source, create a separate Python environment,
and run the full installer, including the LM3/LM4 asset downloads and installation
checks. They build the native modules locally.

Start in the parent folder where you want RDP. You need Git, an installed 64-bit
CPython 3.11–3.14, and the [compiler prerequisites](building.md#compiler-prerequisites).
On Linux, install your distribution's venv support and matching Python development
headers too. The commands create `RDP-v1` and `rdp-v1-env`; use unused folder names.

**Windows PowerShell:**

```powershell
cmd /c "git clone --depth 1 --branch v1.0.0 https://github.com/mortlach/RuneDecrypterPrime.git RDP-v1 && py -3 -m venv rdp-v1-env && cd RDP-v1 && ..\rdp-v1-env\Scripts\python.exe -m pip install setuptools && ..\rdp-v1-env\Scripts\python.exe install.py"
```

`cmd /c` lets the same line work in Windows PowerShell 5.1 and PowerShell 7;
each step runs only if the preceding step succeeds. The `py` launcher uses your
installed Python 3. To choose a particular installed version, replace `py -3`
with, for example, `py -3.12`.

**Linux (bash or sh):**

```bash
git clone --depth 1 --branch v1.0.0 https://github.com/mortlach/RuneDecrypterPrime.git RDP-v1 && python3 -m venv rdp-v1-env && cd RDP-v1 && ../rdp-v1-env/bin/python -m pip install setuptools && ../rdp-v1-env/bin/python install.py
```

`python3` must be one of the versions above. Replace it with `python3.12`, for
example, to select that installed interpreter. No environment activation or
system-Python override is needed. The explicit `setuptools` installation supplies
a test dependency omitted from the original V1 source's test extras.

Afterwards, open `RDP-v1` and use `..\rdp-v1-env\Scripts\python.exe` on Windows,
or `../rdp-v1-env/bin/python` on Linux, in place of `python` in the commands below.

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

For manual downloads, get both ZIPs from the
[V1 language-model asset release](https://github.com/mortlach/rdp_assets/releases/tag/rdp-v1.0.0-lm-large),
place them in `downloads/`, and run the same installer command again.

Already working from source or an editable install? You can
[prepare just the assets](language_model_assets.md#assets-only-without-reinstalling-rdp)
without reinstalling RDP or rebuilding its native modules.

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

Choose a wheel matching your Python version, operating system and architecture.
For example, `cp312-cp312` is for CPython 3.12, and `win_amd64` is for 64-bit
x86 Windows. Linux x86-64 wheels use `manylinux` platform tags. Each wheel works
with the matching Python minor version; a 3.11 wheel cannot be used with 3.12.
See the [release downloads](https://github.com/mortlach/RuneDecrypterPrime/releases)
for the published files.

For an existing wheel:

```text
python -m pip install path/to/downloaded-release.whl
```

A wheel installs the package and the small bundled asset profile. It does not
fetch LM3/LM4. Follow
[the wheel and separate-directory instructions](language_model_assets.md#installed-wheel-or-a-separate-model-directory)
to obtain the full models and select them through `ScoringConfig.language_model_root`.

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
