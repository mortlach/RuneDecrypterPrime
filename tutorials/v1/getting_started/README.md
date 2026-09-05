# Getting started

Start here if you can read Python and are new to RDP. The files build on one
another, from using a known key to preparing a search against a Liber Primus
source. Read them in filename order; each explains the new choices beside
the code that uses them.

## The route

| Files | What we do |
| --- | --- |
| `01`–`03` | Encrypt with a known key, find an unknown rail count, then search for a repeating key. |
| `04`–`07` | Repeat a run, use known interruptors, inspect a partial recovery and load a Liber Primus source. |
| `08`–`10` | Read the result reports, compare search budgets and prepare a real-source search. |

Install RDP using the [installation guide](../../../docs/setup/installation.md),
then run a file from the repository root:

```text
python -m tutorials.v1.getting_started.02_first_search
```

Every file uses `from rdp import api`. You can use the same calls in your own
program; the numbered files themselves are included in the source checkout.
Some of the larger [worked examples](../examples/) also use repository helpers
to prepare their inputs and reports.

The parent [catalogue](../README.md) lists each file and its approximate runtime.
[Anatomy of a run](../../../docs/guides/anatomy_of_a_run.md) brings the main RDP
objects and their options together in one place.

## Things to change

Try changing the rail range in `02`, the repeating-key length in `03`, or the
beam width in `09`. The first two change which keys RDP can try. Beam width
changes how much of the search it keeps exploring.

Each supplied example checks its result against an expected outcome. When you
change the problem, check that comparison too. A failed assertion may simply
mean your new settings didn't recover the original message.
