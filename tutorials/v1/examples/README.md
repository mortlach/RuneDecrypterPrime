# Worked examples

This folder contains retained cipher problems, solver comparisons, robustness
recipes and qualification programs. It is a reference library, not a course and
not an ordered difficulty ladder.

The examples answer larger questions than the numbered getting-started route.
Some use repository fixtures, text preparation or reporting support to create a
repeatable problem. The actual RDP request should still cross the public boundary
through `from rdp import api`; repository support is not presented as installed
API.

Run an example as a module from the repository root:

```text
python -m tutorials.v1.examples.columnar_transposition
```

This convention allows normal package imports and keeps `_ROOT`, `_SRC` and
`sys.path` manipulation out of reader-facing code.

## What belongs here

- a meaningful cipher or solver case;
- a comparison that changes one important part of the recipe;
- a robustness recipe with a stated acceptance condition;
- a real-source workflow that connects evidence to a repeatable run;
- an explicit qualification program whose assets and runtime are declared.

A changed constant alone is not another example. Unstable investigations belong
under `cipher_development/`; regression-only cases belong under `tests/`.

## Before running

Use the parent [`catalogue`](../README.md) to check:

- purpose and cipher/solver combination;
- public, experimental or repository-only surface;
- required asset profile;
- approximate runtime;
- expected exact, partial or thresholded result;
- whether known truth affects setup, stopping or only validation.

The three qualification files can take from tens of minutes to several hours.
They are never selected merely because somebody asked to run the examples.

## Useful changes

Choose a script with the key structure your problem needs. In the columnar
example, the permutation fixes the column count while hybrid stage budgets
control search work. In repeating multiplication, the map is the cipher rule
and beam width controls retained alternatives. The scheduled-stream example
separates the supplied schedule from the unknown repeating key.

Keep the scorer and seed fixed when comparing a budget. If you change the
cipher, schedule or key shape, you have changed the hypothesis; check that its
inputs and acceptance condition still describe what you intend to demonstrate.
