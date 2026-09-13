# Using RDP

There is more than one sensible way to use RDP.

If you just want the complete package working, use the normal installer. If you
want to inspect the source, change it, build the native modules yourself or work
at the Python prompt, those are normal ways to use the project too.

RDP V1 uses Python 3.11 as its qualified desktop baseline.

## Install RDP normally

For the simplest complete setup from a source checkout, run:

```text
python install.py
```

The installer prepares the package, checks the native modules, deals with the V1
language-model assets and runs its install checks.

A prebuilt release wheel is another normal route and does not require you to
have a C++ compiler.

See [Installation](../setup/installation.md) for the full installer details.

## Run directly from the source checkout

RDP uses a `src/` layout. Python needs to be able to see the repository's `src`
directory before `from rdp import api` can work directly from an uninstalled
checkout.

There are several ordinary ways to do that:

- put `src/` on `PYTHONPATH`
- mark `src/` as a source root in your IDE
- use the source-aware tutorial runner
- use an editable install

For the lightest source route, install NumPy in the Python environment you want
to use.

```text
python -m pip install numpy
```

That is enough for the basic public API, known-key operations and Liber Primus
source inspection. It is also enough for getting-started tutorials 01, 07 and
10.

### `PYTHONPATH`

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
```

In Command Prompt:

```bat
set "PYTHONPATH=%CD%\src"
```

In a POSIX shell:

```sh
export PYTHONPATH="$PWD/src"
```

Now normal Python imports from the checkout.

```text
python -X utf8
>>> from rdp import api
```

`-X utf8` is useful on terminals where rune output would otherwise use a legacy
console encoding.

Most Python IDEs can do the same thing by marking `src/` as a source root or
adding it to that interpreter's runtime import path. Choose the same interpreter
for its console, run and debug configurations.

## Scoring and normal solver use from source

Known-key operations do not need RDP's native scoring code. Normal language-model
scoring and the solver tutorials do.

Install the normal runtime dependencies in the environment.

```text
python -m pip install numpy zstandard tzdata platformdirs
```

For a local native build, also install the Python-side build tools.

```text
python -m pip install pybind11 setuptools wheel
```

You also need a working C++ compiler for your platform. This is a build in the
current environment, not an isolated installation, and the helper does not
download dependencies or change the environment for you.

Then build the native modules in place.

```text
python tools/build_native.py
```

The current V1 release build contains three native modules:

- `_fastlm` for the normal language-model scorer
- `_hamming` for the retained Hamming scoring work
- `_span_hamming_fast` for the retained fast span-Hamming work

Only `_fastlm` is required for ordinary V1 language-model scoring. The other two
are specialist capabilities, but the normal release build already builds all
three, so the convenience helper does the same.

If you are specifically hacking only on `_fastlm`, the retained single-target
builder is also available under `src/rdp/scoring/language_model/`.

### Build all retained native research modules

RDP also contains the newer experimental n-gram Hamming native module that was
not promoted into the V1 release artifact.

Build the release-native modules plus that retained experiment with:

```text
python tools/build_native.py --all
```

Building an experimental module does not turn it into a default scorer. It just
makes the implementation available for the research code that uses it.

Build scratch files and logs go under an absolute `RDP_OUTPUT_ROOT` when set,
or under the system temporary directory otherwise. Only the compiled modules
are placed in the checkout. Failed-build evidence is retained. The helper
verifies each selected module in a fresh Python process from this checkout.

Changing the C++ source does not automatically rebuild an existing `.pyd` or `.so`
file. Re-run the appropriate native build after changing native code.

See [Build and packaging notes](../setup/building.md) for compiler and packaging
detail.

## Editable install

A common open-source development workflow is an editable installation:

```text
python -m pip install -e .
```

This is an installation, but it points Python at the working source checkout
rather than making a separate copy of the Python package.

That is useful when you are changing RDP itself.

If you edit a Python file under `src/rdp`, a new Python process will use that
changed file. You do not need to reinstall RDP after every Python edit.

A Python interpreter that already imported a module normally keeps that module
in memory. Restart the interpreter, or deliberately reload the module, when you
want to pick up an edit during an interactive session.

Native C++ extensions are different. If you change the native source, rebuild
the extension before expecting Python to use the new code.

Changes to dependency metadata can also require running the editable install
again.

You can confirm where an editable install is importing from:

```text
python -X utf8 -c "import rdp; print(rdp.__file__)"
```

The path should point into the checkout you installed with `-e`. This route
builds the current three release-native modules and installs the declared
runtime dependencies. It does not fetch LM3/LM4 or provision CUDA by itself.

## Run the tutorials

Run one tutorial directly:

```text
python -X utf8 -m tutorials.v1.getting_started.01_known_key
```

Or use the source-aware runner:

```text
python tutorials/v1/run_tutorials.py --list
python tutorials/v1/run_tutorials.py getting-started
python tutorials/v1/run_tutorials.py release
python tutorials/v1/run_tutorials.py bundled
python tutorials/v1/run_tutorials.py --only 01 07 10
```

The runner adds this checkout's `src/` directory for itself and its child
processes. It does not install RDP and it does not install missing dependencies
for you.

The basic 01, 07 and 10 getting-started programs can run without an RDP-native
build. The other normal getting-started searches use language-model scoring and
therefore need `_fastlm`.

Full-asset and qualification examples have additional asset and runtime costs
and are kept separate from the ordinary tutorial route. Bundled LM1/LM2 is
enough for the release group. The two full-asset examples and three qualification
programs need full_v1 LM1–LM4. Hamming and fast span-Hamming are not prerequisites
for any of these groups as configured. See [Language-model assets](../setup/language_model_assets.md).

The default group is `release`. Use `full-assets` or `qualification` explicitly
for those groups, after checking their requirements and expected duration.
`--list` does not run anything. `--only` selects named items from the whole
catalogue and accepts numbers, filenames, stems or repository-relative paths.

See [Tutorials and examples](../tutorials/README.md) for the full catalogue and
rough runtimes.

## Use RDP interactively

RDP does not need a separate shell language. The public API is an ordinary
Python API.

Start Python:

```text
python -X utf8
```

Then try a known-key operation one line at a time:

```python
from rdp import api

plaintext = (0, 3, 20, 20, 3, 7, 2, 18)
key = (3, 1, 4)

cipher = api.CipherSpec.vigenere()
ciphertext = api.encrypt(plaintext, cipher=cipher, key=key)
ciphertext

recovered = api.decrypt(ciphertext, cipher=cipher, key=key)
recovered
recovered == plaintext
```

Liber Primus data is available through the same namespace:

```python
source = api.liber_primus.source("welcome_pilgrim")
source.source_kind
source.ref["label"]
source.asset_id

data = api.liber_primus.load_source("welcome_pilgrim")
len(data.ct_idx), len(data.wli)
```

Once `_fastlm` is built and the scoring dependencies are present, the same
interpreter can score candidates or construct a `RunSpec`.

```python
candidate = api.RuneInput("THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG")
api.score(candidate)
api.score_many((candidate, candidate))
```

These calls use the requested language-model tables and calibration files.
The default scorer uses LM2. Numeric candidates need aligned word-length
information for the default WLI lane, or an explicitly character-only scoring
configuration. Missing requested capabilities fail rather than change the score.

The same API can be used from:

- the standard Python interpreter
- IPython or Jupyter
- an IDE console
- a normal `.py` script
- an AI coding environment that can run Python

A small idea often starts nicely at the prompt. Once it becomes an experiment
worth keeping, put the same calls in a script with its input so somebody else
can run it again.

## Browser use

RDP V1 has also been built and exercised under Pyodide/WebAssembly in a real
browser, including the native modules, scoring, solver examples and Liber Primus
data.

The V1 repository does not ship a public browser front end. For current
community browser experiments and other live Cicada work, check
[CicadaSolvers](https://www.cicadasolvers.com/).

Developers interested in the WebAssembly build itself can see the
[Pyodide build and smoke tooling](../../tools/pyodide/README.md).

## Which route should I use

If you just want RDP working, use `python install.py`.

If you want to inspect or change the Python source, use `PYTHONPATH`, your IDE's
source-path support or an editable install.

If you want normal scoring from an uninstalled checkout, build the native
modules in place.

If you are working on the retained Hamming, span-Hamming or n-gram Hamming
research, build the specialist native modules you need.

They all lead to the same public Python API.
