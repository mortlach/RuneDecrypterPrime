# Rune Decrypter Prime

Rune Decrypter Prime (RDP) is a cryptanalysis and cipher-development framework
built around Runeglish and the 29-rune alphabet of Liber Primus.

At its simplest, it is a way to take a cipher idea, a key or key space, and some
Liber Primus text and actually try it without writing another one-off solver
from scratch. You can change the cipher, keys, search or scoring while keeping
the rest of the experiment the same.

## Contents

- [Why RDP exists](#why-rdp-exists)
- [What RDP is for](#what-rdp-is-for)
- [Why repeatability matters](#why-repeatability-matters)
- [Try RDP](#try-rdp)
- [Try something and share it](#try-something-and-share-it)
- [Start solving](#start-solving)
- [Working with Liber Primus](#working-with-liber-primus)
- [Extending RDP](#extending-rdp)
- [CPU and CUDA](#cpu-and-cuda)
- [Output](#output)
- [Choose how you want to use RDP](#choose-how-you-want-to-use-rdp)
  - [Install RDP normally](#install-rdp-normally)
  - [Run directly from the source checkout](#run-directly-from-the-source-checkout)
  - [Use an editable install](#use-an-editable-install)
  - [Build the native modules yourself](#build-the-native-modules-yourself)
- [Project History](#project-history)

## Why RDP exists

Liber Primus solving has accumulated a great many ideas over the years.
Someone tries a cipher, another person changes the period, someone else adds a
sequence or an interruptor rule, and six months later the surviving description
is often something like:

> I tried this method and found nothing.

Possibly. But what, exactly, was tried?

RDP makes the experiment explicit enough that somebody else can run it again.

```text
source text
-> cipher hypothesis
-> key or key space
-> search
-> scoring
-> result and evidence
```

A small experiment might iterate over one key length or apply an existing cipher
to a section of Liber Primus. A larger one might search a structured key space,
compare scoring models or develop a new cipher construction.

They use the same underlying machinery.

## What RDP is for

For practical solving, RDP provides Liber Primus source material, rune
representations, Runeglish language handling, cipher implementations, key
models, solvers and scoring tools needed to turn an idea into a repeatable
experiment.

For example, you should not need to rebuild Vigenere, rune conversion, key
iteration, language scoring and LP source handling every time you want to test
one new thought.

For cipher development, RDP separates those parts so new ciphers, key structures,
search methods and scoring evidence can be developed independently, then
combined through the same run model.

That gives us something useful between a notebook experiment and a finished
solver: a place where new ideas can be tried quickly without becoming another
private framework.

Over time the number of supported methods and documented attempts will grow.

## Why repeatability matters

A result is more useful when another solver can inspect what produced it.

RDP records the important parts of a run: source text, cipher, allowed keys,
solver settings, scoring model, starting information, seed, stopping condition
and result.

That makes these different statements distinguishable:

```text
I applied this known key and reproduced the plaintext.

I searched this key space and recovered the known solution.

I tested this hypothesis under these settings and it did not recover anything.

I used known plaintext to investigate the structure around a solution.
```

They are not the same claim.

RDP tries to keep the difference visible.

It cannot prevent bad cryptanalysis. That would be an ambitious dependency. It
can at least make it easier to tell what was actually done.

## Try RDP

A minimal known-key check looks like this:

```python
from rdp import api

plaintext: api.RuneIndices = (0, 3, 20, 20, 3, 7, 2, 18)
key: api.ConcreteKey = (3, 1, 4)

cipher = api.CipherSpec.vigenere()
ciphertext = api.encrypt(plaintext, cipher=cipher, key=key)
recovered = api.decrypt(ciphertext, cipher=cipher, key=key)

assert recovered == plaintext
```

No solver is involved because the key is already known.

You can run the same calls interactively:

```text
python
```

```python
from rdp import api
```

or put them in your own script, notebook or IDE console.

The tutorial runner can show what is available:

```text
python tutorials/v1/run_tutorials.py --list
```

and run the getting-started route:

```text
python tutorials/v1/run_tutorials.py getting-started
```

Choose the route that matches what you want to do next:

- **Learn RDP:** [Learn RDP by solving](docs/learn/README.md)
- **Solve Liber Primus:** [Start solving Liber Primus](solving/lp_getting_started/README.md)
- **Develop or extend RDP:** [Extending RDP](docs/guides/extending_rdp.md)
- **Try something and share it:** [Liber Primus attempts](solving/attempts/README.md) · [Contributing](CONTRIBUTING.md)

The fuller [documentation index](docs/README.md) is there when you need more
control or want to understand the internals.

RDP has also been built and run under Pyodide/WebAssembly in a real browser.
V1 does not ship a browser front end. Check [CicadaSolvers](https://www.cicadasolvers.com/)
for current community work and experiments.

## Try something and share it

The quickest way to use RDP is to give yourself a concrete question and try it.
Pick some Liber Primus text, choose a method, and see what happens. A period-10
Vigenere test is already a perfectly reasonable experiment. So is changing one
assumption in an existing example or trying a cipher idea of your own.

If you want to share the result, keep the exact input file, the script, and a
short note about what you tried. It does not have to recover plaintext to be
useful. The point is that the next person can see what really ran instead of
hearing that "somebody tried that once".

See [Liber Primus attempts](solving/attempts/README.md). For wider Cicada 3301
background and current community links, including places to find live discussion,
start with the [Uncovering Cicada Wiki](https://uncovering-cicada.fandom.com/wiki/Uncovering_Cicada_Wiki).

Bugs, feature requests and changes to RDP itself are covered in
[Contributing](CONTRIBUTING.md).

## Start solving

The main documentation route is:

1. [Quickstart](docs/guides/quickstart.md)
2. [Ciphertext input](docs/guides/ciphertext_input.md)
3. [Word-length information](docs/guides/word_length_information.md)
4. [Building a run](docs/guides/building_a_run.md)
5. [Comparing solve experiments](docs/guides/working_a_solve.md)
6. [Reading a result](docs/guides/results.md)
7. [Tutorials and examples](docs/tutorials/README.md)

Worked Liber Primus material is under [Solving examples](solving/README.md).

## Working with Liber Primus

Liber Primus data is available through the public namespace:

```python
from rdp import api

source = api.liber_primus.source("welcome_pilgrim")
```

Pass the source directly as `RunSpec.problem_input`. It keeps the catalogue
label and transcript version with the run, so the input remains identifiable.

Direct source-data access is also available when you need to inspect rune
indices, word-length information or source metadata before constructing a run.

The same namespace also provides transcript, page, locator and partition access.
See [Liber Primus data](docs/reference/liber_primus.md).

## Extending RDP

The extension path follows the same ownership model:

- new cipher behaviour belongs with the cipher implementation and `CipherSpec`
- new key structure belongs with key operations and `KeySpec`
- new search behaviour belongs with a solver and `SolverSpec`
- new scoring evidence belongs in the scoring system
- exploratory cipher work can begin under `cipher_development/`
- broader repeatable qualification belongs under `tools/robustness/`

The public API should remain small even as the implementation grows.

See [Extending RDP](docs/guides/extending_rdp.md) and
[Contributing](CONTRIBUTING.md).

## CPU and CUDA

RDP runs on CPU by default.

CUDA is available on supported NVIDIA hardware when a run asks for:

```python
compute_device=api.ComputeDevice.CUDA
```

See [CUDA setup](docs/development/cuda_installation.md).

## Output

A run gives you more than a candidate plaintext. `api.run(request)` returns a
`RunResult` in memory, with the key, score, stop status and evidence about how
the search ran. You can inspect those fields in Python or print a readable
summary:

```python
api.display.print_result(
    result,
    spec=request,
    options=api.display.SummaryOptions.for_console(),
)
```

Here is actual console output from the small
[Reading a result tutorial](tutorials/v1/getting_started/08_reading_a_result.py).
It searches a rail-fence example and checks the recovered key and plaintext
afterwards. This is a teaching fixture, not a Liber Primus recovery claim.

<details>
<summary>Show the example console output</summary>

```text
Reading a result
Best key       : (7,)
Best score     : 0.8917643401728653
Execution      : completed
Stop category  : budget
Stop reason    : max_rounds_reached
Solver         : beam_search
Evaluations    : 15
Requested seed : 2718
Effective seed : 2718
Oracle ranking : False
RDP standard summary
====================
schema: api_display_summary.v1
encoding_dir: left_to_right
cipher: rail_fence
solver: beam_search
score: 0.8917643401728653
stop_reason: max_rounds_reached
stop_category: budget

Plaintext
---------
TH·E·R·E·W·A·S·A·T·A·B·L·E·S·E·T·O·U·T·U·N·D·E·R·A·T·R·E·E

Recovered key
-------------
{"length": 1, "preview": [7], "truncated": false}

Warnings
--------
- stop category is budget
```

Run it yourself from a prepared checkout:

```text
python -X utf8 -m tutorials.v1.getting_started.08_reading_a_result
```

</details>

The budget warning describes why the search stopped. It does not say whether
the plaintext is correct; the tutorial checks that separately against its known
answer. RuneLatin is a representation of the runes, not an English translation.

For a run worth keeping or comparing, the main outputs are:

- **Candidate data:** the recovered key, score, rune indices, rune text,
  RuneLatin and word-length information in `RunResult`
- **Run reports:** solver outcome and evaluation counts, scorer capabilities,
  requested versus effective configuration, seed/reproducibility metadata and
  explicit oracle-use information
- **Text and JSON summaries:** `api.display` renders the same result for a
  terminal, notebook or another tool; a logged run can save
  `artifacts/rdp_display_summary.json` and `artifacts/solver_report.json`
- **Telemetry and live progress:** timing, progress and execution details help
  explain how two searches differed; telemetry stays in memory unless you
  export it, and `progress_callback` supplies live updates
- **Saved-run metadata and artifact manifests:** `META.json`,
  `config/logging.json` and an optional
  `artifacts/run_artifacts_manifest.json` identify the saved files;
  `RunResult.artifacts` lists the registered outputs actually present

A plain run does not need a run directory. To save the reports, pass
`api.LoggingConfig` through `RunSpec.logging`, choose an output location and
enable `write_solver_report`, `write_display_summary` and
`write_artifact_manifest` as needed.

Keep the original input and `RunSpec` alongside the evidence. When comparing
runs, look at the candidate, stopping reason, evaluations and elapsed time, not
only the final score. Keep the scoring configuration fixed when comparing
numeric scores directly, and record any changes to the seed, search budget or
starting information.

See [Reading a result](docs/guides/results.md),
[Displaying results](docs/guides/displaying_results.md),
[Saved outputs](docs/guides/outputs.md),
[Telemetry](docs/guides/telemetry.md) and
[Comparing solve experiments](docs/guides/working_a_solve.md).

## Choose how you want to use RDP

RDP 1.0.0 needs Python 3.11 or newer.

There are a few normal ways to work with it. Use whichever fits what you are
trying to do.

### Install RDP normally

If you just want RDP set up and ready to use, from the repository root run:

```text
python install.py
```

The installer uses the Python environment you choose, builds the native scoring
modules and checks the V1 assets.

If a Linux distribution protects its system Python, RDP explains the available
next steps rather than changing that protection automatically.

See [Installation](docs/setup/installation.md).

### Run directly from the source checkout

You do not have to install RDP as a package to use the source.

Install the Python dependencies:

```text
python -m pip install numpy zstandard tzdata platformdirs
```

Then make `src/` available to Python. There are several ordinary ways to do
that, including `PYTHONPATH`, setting the source root in your IDE, or using the
source-aware tutorial runner.

For example, on PowerShell:

```text
$env:PYTHONPATH = "$PWD\src"
python -m tutorials.v1.getting_started.01_known_key
```

On Command Prompt:

```text
set PYTHONPATH=%CD%\src
python -m tutorials.v1.getting_started.01_known_key
```

On Linux or macOS:

```text
PYTHONPATH="$PWD/src" python -m tutorials.v1.getting_started.01_known_key
```

Known-key operations, Liber Primus source access and some of the first tutorials
work without compiling RDP's native scoring code.

See [Using RDP](docs/guides/using_rdp.md) for the different source-use options.

### Use an editable install

If you are working on RDP itself, an editable install is often convenient:

```text
python -m pip install -e .
```

Python then imports RDP from your checkout. Changes you make to Python source
will be picked up by new Python processes without reinstalling the package.

An interpreter that has already imported a module may need to be restarted or
the module reloaded. Changes to the native C++ code still need to be rebuilt.

### Build the native modules yourself

RDP is mostly Python, but some scoring code is native C++.

Building it yourself is a normal way to work with the project, especially if
you want to change the scoring code or work on the experimental scoring
backends.

From the repository root:

```text
python tools/build_native.py
```

This builds the native modules used by the V1 release package. For all retained
native and experimental modules:

```text
python tools/build_native.py --all
```

See [Build and packaging notes](docs/setup/building.md) for compiler and build
details.

## Project History

For the longer history of RDP, see [Project history](docs/project_history.md).
