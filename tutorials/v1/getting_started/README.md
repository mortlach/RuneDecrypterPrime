# Getting started

This folder is the ordered route into ordinary RDP use. The numbered files are
small executable arguments: each introduces one cryptanalytic concept, runs or
prepares a bounded public-API request, and states the claim it can support.

The commentary assumes the reader can read Python. It explains RDP concepts,
why each object exists in the cryptanalytic process, nearby public alternatives,
and where known truth enters. It does not narrate Python syntax.

## Route

| Stops | Purpose |
| --- | --- |
| `01`–`03` | Separate known-key operations from search, then introduce `RunSpec`, key-space shapes, raw rune input and WLI. |
| `04`–`07` | Add reproducibility, interruptors, honest partial recovery and named Liber Primus sources. |
| `08`–`10` | Read result evidence, compare controlled search budgets, then prepare a real-source search without launching the longer solve. |

Run a file as a repository module from the repository root:

```text
python -m tutorials.v1.getting_started.02_first_search
```

Module execution keeps repository location setup out of the example. The `rdp`
package must already be installed as described in
[`docs/setup/installation.md`](../../../docs/setup/installation.md).

## Boundary

Every numbered file imports normal functionality through:

```python
from rdp import api
```

These files do not import repository fixtures, tutorial support or runtime
implementation modules. The larger [`examples/`](../examples/) folder is the
place for worked repository cases that need those facilities.

The complete route and runtime table is in the parent
[`tutorials/v1/README.md`](../README.md). The conceptual companion is
[`docs/guides/anatomy_of_a_run.md`](../../../docs/guides/anatomy_of_a_run.md).

## Adapting a nearby example

Start with one change: rail bounds in `02`, repeating-key length in `03`, or
beam width in `09`. Bounds and lengths describe the proposed problem; width
changes the search budget. The comments explain the distinction and link to
other key shapes, solvers and custom cipher/key development.

The supplied settings have a checked outcome. Once you change the problem,
review its reference comparison too; a failed example assertion may mean your
new hypothesis did not recover the constructed answer.
