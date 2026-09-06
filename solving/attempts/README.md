# LP attempts

This folder contains reproducible attempts against unsolved or diagnostic Liber
Primus material.

An attempt records:

```text
question
source_label
cipher / model hypothesis
prior information
truth policy
search and scoring setup
expected outcome
result summary
```

For genuinely unsolved material the normal truth policy is `no_truth`.

A failed solve still records something if the tested hypothesis, budget and
result are clear.

## Source handling

Load text through the LP catalogue or reviewed transcript locators.

Do not hand-copy ciphertext into a new attempt when a registered source already
exists.

See [Liber Primus data](../../docs/reference/liber_primus.md).

## Keep claims narrow

An attempt that uses a crib, prepared key, fixed period or restricted candidate
pool should say so.

Changing prior information changes the experiment.

See [Comparing solve experiments](../../docs/guides/working_a_solve.md).

## Solved examples first

Use the solved workbook to check a cipher/search/scoring route before applying
it to unsolved material.

See [Solved LP workbook](../solved_lp/README.md).
