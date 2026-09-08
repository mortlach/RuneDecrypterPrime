# Rune Decrypter Prime

Rune Decrypter Prime (RDP) is a cryptanalysis and cipher-development framework
built around Runeglish and Liber Primus.

At its simplest, it is a way to take a cipher idea, a key or key space, and some
Liber Primus text and actually try it without writing another one-off solver
from scratch.

That matters more than it may sound.

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

## Start here

If you want to try RDP rather than study it, start with
[Learn RDP by solving](docs/learn/README.md).

The learning route keeps the examples small and uses ordinary defaults. It
introduces one idea at a time:

```text
load some text
-> try a known cipher
-> search a key
-> change one thing
-> use real Liber Primus data
-> read the result
```

You do not need to understand the architecture, scoring backends or solver
internals first.

The fuller [documentation index](docs/README.md) is there when you need it.

## What RDP is for

RDP has two closely related jobs.

The first is practical solving.

It provides Liber Primus source material, rune representations, Runeglish
language handling, existing cipher implementations, key models, solvers and
scoring tools needed to turn an idea into a repeatable experiment.

You should not need to rebuild Vigenere, rune conversion, key iteration,
language scoring and LP source handling every time you want to test one new
thought.

The second is cipher development.

RDP separates the parts of a cryptanalytic problem so new ciphers, key
structures, search methods and scoring evidence can be developed independently,
then combined through the same run model.

That gives us something useful between a notebook experiment and a finished
solver: a place where new ideas can be tried quickly without becoming another
private framework.

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

## Who it is for

RDP is for people working on Liber Primus and related cipher problems, from a
short experimental script to development of a new cipher or search method.

If you are new to the project, use the
[learning route](docs/learn/README.md).

If you already know what you want to build, use the
[full documentation](docs/README.md).

For the internal design, see [Architecture](docs/architecture/README.md).

For adding ciphers, key models or solvers, see
[Extending RDP](docs/guides/extending_rdp.md).

## Install

RDP needs Python 3.11 or newer.

From the repository root:

```text
python install.py
```

Optional PowerShell, Command Prompt and POSIX shell wrappers are under
[`tools/installation/`](tools/installation/README.md).

The installer uses the Python environment you choose. If a Linux distribution
protects its system Python, the installer explains the available next steps
rather than changing that protection automatically. See
[Installation](docs/setup/installation.md).

Then run the first tutorial:

```text
python -m tutorials.v1.getting_started.01_known_key
```

## Start solving

The main documentation route is:

1. [Quickstart](docs/guides/quickstart.md)
2. [Ciphertext input](docs/guides/ciphertext_input.md)
3. [Word-length information](docs/guides/word_length_information.md)
4. [Defining a run](docs/guides/anatomy_of_a_run.md)
5. [Comparing solve experiments](docs/guides/working_a_solve.md)
6. [Reading a result](docs/guides/results.md)
7. [Tutorials and examples](docs/tutorials/README.md)

The full documentation index is in [docs/README.md](docs/README.md).

Worked Liber Primus material is under [Solving examples](solving/README.md).

## A small known-key check

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

## Working with Liber Primus

Liber Primus data is available through the public namespace:

```python
source = api.liber_primus.source("welcome_pilgrim")
```

Pass the source directly as `RunSpec.problem_input`. It keeps the catalogue
label and transcript version with the run, so the input remains identifiable.

Direct payload access is also available when you need to inspect rune indices,
word-length information or source metadata before constructing a run.

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

`api.run(...)` returns a `RunResult` in memory.

Add `api.LoggingConfig` when a run is worth saving to disk. See
[Outputs](docs/guides/outputs.md).
