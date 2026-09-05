# Worked examples

Choose a file close to the problem you want to try. This folder includes cipher
solves, comparisons between search methods, runs with several starts and longer
qualification programs. The [catalogue](../README.md) lists all of them with
their required assets, approximate runtime and expected result.

Run an example from the repository root:

```text
python -m tutorials.v1.examples.columnar_transposition
```

The module command lets the examples import shared input and reporting helpers.
Those helpers live in this repository; the RDP request itself uses
`from rdp import api`.

## Before running

Check the catalogue for the assets and time the example needs. Also check how
it uses the known answer: some scripts only compare the result afterwards,
while others use a reference score to decide when to stop searching.

The three qualification programs take from tens of minutes to several hours.
Select them explicitly when you intend to run that work.

## Things to change

In the columnar example, the permutation length sets the number of columns.
The hybrid solver's stage budgets control the work spent finding their order.
In repeating multiplication, the map defines the cipher rule and beam width
controls how many alternatives the search keeps. The scheduled-stream example
supplies a known schedule and searches for the repeating key.

Keep the scorer and seed fixed when comparing search budgets. If you change the
cipher, schedule or key shape, check that the inputs and expected result still
match the problem you want to try.

## Adding an example

A useful addition might cover a different kind of key, compare two approaches,
use a real source or fill a missing step in the getting-started route. Explain
what it adds, what it needs to run and how to judge the result. Changing a
constant in an existing example usually doesn't need another file.

Work still under investigation belongs in `cipher_development/`. Cases whose
main purpose is to catch regressions belong in `tests/`.
