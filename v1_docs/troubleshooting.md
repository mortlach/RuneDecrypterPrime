# Troubleshooting

Status: staged V1 draft

This page is for the simple V1 path:

```text
python install.py
python tutorials/v1/run_pretty_print_release.py
```

Use the same Python for both commands. Many confusing failures come from
installing with one Python and running tutorials with another.

## First Rule

Do not start by changing files.

First, rerun the command that failed and read the log path printed by the tool.
Most failures are already sorted into a small number of plain categories.

## Install Fails

Run:

```text
python install.py
```

If install fails, look for the newest log under:

```text
output/install_logs/
```

Common causes:

- Python is older than 3.11.
- Package build tools are too old.
- A native extension did not build or import.
- Required V1 asset files are missing.
- Compact smoke tests failed after installation.

The installer prints the failing step name. Use that step name first; it is more
useful than the last line of a long build log.

## Tutorial Runner Fails

Run:

```text
python tutorials/v1/run_pretty_print_release.py
```

The normal runner prints one line per tutorial and ends with:

```text
Pretty-print summary
selected=21 run=21 passed=21 failed=0
```

If `failed` is not `0`, open the log for the failing tutorial under:

```text
output/tutorial_pretty_print_logs/
```

Each log is named after the tutorial file. For example, a failure in
`Tutorial_Autokey.py` writes:

```text
output/tutorial_pretty_print_logs/Tutorial_Autokey.txt
```

## Reviewing The Full Printout

If the compact runner passes but the tutorial output looks unclear, use the
output-review runner:

```text
python tutorials/v1/run_pretty_print_output_review.py
```

It uses the same tutorial list as the normal runner, but echoes each captured
printout to the console and writes logs under:

```text
output/tutorial_pretty_print_output_review_logs/
```

Use this for documentation and release review. The normal runner is better for a
quick pass/fail check.

## Reading A Tutorial Failure

Check these fields first:

- `encoding_dir`
- cipher
- solver
- `match_ratio`
- stop reason
- oracle/truth-data fields
- recovered key preview
- warnings

If `encoding_dir` is wrong or missing, plaintext can look wrong even when the
rune-index solve is correct. Rune text is not always one English letter per
rune, so display bugs can look like spelling bugs.

## Match Ratio Is Below The Minimum

The runner compares the last reported match ratio with the tutorial threshold in
`tutorials/v1/run_pretty_print_release.py`.

If the tutorial is an exact-recovery lesson, the minimum is usually `1.000`.
Some longer or stochastic tutorials use a lower threshold. That threshold is
part of the tutorial contract and should be easy to see in the runner.

## A Word Looks Misspelled

Check [runes_and_text.md](runes_and_text.md) before assuming the solver failed.

RDP often displays canonical rune-latin text. For example, English `LOOKED` may
display as `LOOCED` because the rune alphabet has no separate `K` rune in this
normalised view. That is different from a direction bug such as displaying
`READ` as `RAED`.

## What To Record For Review

When asking for help, include:

- the command that failed
- the failing tutorial name, if any
- the final summary line
- the relevant log path
- the first clear error message
- whether install passed on the same machine

Do not paste large generated logs into documentation pages. Keep logs in
`output/`, which is local runtime output.
