# Rune Decrypter Prime

Rune Decrypter Prime (RDP) is a cryptanalysis toolkit for runeglish and Liber
Primus.

It brings the main parts of a solve into one explicit, repeatable run:

```text
ciphertext
-> cipher hypothesis
-> key space
-> search
-> scoring
-> result and evidence
```

RDP began as a way to make increasingly complicated Liber Primus experiments
easier to express, compare and repeat. The same structure now supports a wider
set of ciphers, solvers and scoring methods, with a public API intended for
other solvers to use and extend.

The Python entry point is:

```python
from rdp import api
```

## Why RDP exists

Cryptanalysis becomes difficult to reason about when the cipher, search method,
scoring assumptions, starting information and known truth are mixed together.

RDP keeps those parts separate.

A run records what text was used, what cipher was tried, what keys were allowed,
how the search was performed, how candidates were scored, why the run stopped,
and what evidence is available for the result.

A promising result can then be repeated. Two approaches can be compared
without quietly changing five other things. Known plaintext can be used to check recovery without
becoming part of the search by accident.

## Who it is for

RDP is aimed at people who want to work on cipher problems rather than only run
a fixed decoder.

That includes:

- Liber Primus solvers
- people testing classical and custom cipher ideas
- developers comparing search methods and scoring models
- contributors adding ciphers, solvers, data sources or scoring methods
- anyone who wants a cryptanalytic experiment to be reproducible enough to
  inspect later

You do not need to understand the whole codebase to use it. Normal solving stays
on the public `rdp.api` surface.

## Design goals

The main design goal is to keep cipher, key, search, scoring and evaluation
separate enough to compare and extend them.

A few principles shape most of RDP:

**One clear public route.** Normal user code starts with `from rdp import api`
and builds typed requests.

**Explicit assumptions.** Cipher choice, key space, solver, scoring, direction,
WLI and starting information are visible in the run.

**Determinism where it matters.** Seeds, configuration, assets and effective run
state are recorded so that meaningful experiments can be repeated and compared.

**Truth stays separate from search.** Known keys and plaintext may be used to
check a completed result. They do not silently rank candidates or stop a normal
search.

**No silent substitution.** If a requested capability or asset is unavailable,
RDP reports the problem rather than quietly doing something else.

**Extension without parallel frameworks.** New capabilities join the existing
cipher, key, solver and scoring structure instead of creating a second way to
run the same problem.

The same model continues from a small solve into cipher development and qualification.

See [Project aims and design principles](docs/project_overview.md) for the fuller
version.

For how those pieces fit together internally, see
[Architecture](docs/architecture/README.md).

## Install

RDP needs Python 3.11 or newer.

From the repository root:

```text
python install.py
```

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
payload = api.liber_primus.payload_from_label("welcome_pilgrim")
```

The payload supplies aligned rune indices, WLI and source metadata.

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

## Status

The V1 codebase is being prepared as a stable community-facing release.

The public API, tutorials, test-backed contracts and solver/scoring components
are now organised around the same run model. The remaining release work is
mainly documentation consolidation, final validation and packaging rather than
another redesign of the user surface.
