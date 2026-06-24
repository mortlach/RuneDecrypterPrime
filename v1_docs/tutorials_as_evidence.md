# Tutorials As Evidence

Status: staged V1 draft

RDP tutorials have two jobs:

- teach a reader how a cipher or workflow behaves
- give release reviewers repeatable evidence that the workflow still runs

They are not secret production scoring rules.

## The Current Review Source

For the pretty-print V1 review, the current executable source of truth is:

```text
tutorials/v1/run_pretty_print_release.py
```

That runner contains:

- the selected tutorial list
- the minimum match threshold for each tutorial
- the compact console-output policy
- the log output folder

The full printout-review runner is:

```text
tutorials/v1/run_pretty_print_output_review.py
```

It uses the same list through the release runner, but echoes each captured
printout so reviewers can inspect formatting and wording.

## Target Tutorial Shape

Working V1 tutorials live in:

```text
tutorials/v1/
```

That includes:

- beginner tutorials
- normal release tutorials
- extended confidence tutorials
- near-solve showcase tutorials
- optional-asset tutorials
- advanced examples that are still healthy and runnable

Not every working tutorial has to be in the beginner release gate. The important
thing is that every working tutorial has a clear classification, a direct file
to run, and a visible evidence policy.

## Tutorial Manifest

The repository also contains:

```text
tutorials/v1/tutorial_manifest_v1.json
```

The manifest records tutorial classification ideas:

- gate
- asset profile
- acceptance kind
- minimum match ratio
- observed baseline
- oracle stop-score use
- whether the true key is supplied to the solver
- current status
- notes

The manifest now names the promoted tutorial files in `tutorials/v1/`. Older
replaced tutorial files live under `tutorials/legacy/`.

The preferred long-term state is one metadata story for all working
`tutorials/v1/` tutorials. A future tutorial must not require a reader to
manually reconcile several stale lists.

## Easy Update Rule

When a tutorial is added, promoted, renamed, or retired, update these together:

| Item | Why it changes |
| --- | --- |
| tutorial file | The runnable lesson. |
| pretty-print runner list | The selected human-facing review set and threshold. |
| tutorial manifest or successor metadata | Gate, asset profile, acceptance kind, status, and notes. |
| `v1_docs/tutorials.md` | Public tutorial list if the tutorial is selected. |
| `v1_docs/02_CROSSCHECK.md` | Records that docs still match code. |
| focused tests | Prevents silent drift. |

The final shape may be a generated docs table, a checked manifest-derived table,
or a small helper script. The goal is simple: adding tutorial number 22 should
be obvious and reviewable.

## What Counts As Evidence

A tutorial run is evidence for a specific lesson and setup.

Good evidence says:

- which tutorial ran
- what cipher family was used
- which runner selected it
- which asset profile it expects
- whether exact recovery is required
- what minimum match ratio is accepted
- whether truth or oracle data was used
- whether the result passed
- where the log can be inspected

Evidence is boring in the best way: repeatable, visible, and easy to
check.

## Acceptance Kinds

Current tutorial evidence uses these ideas:

| Acceptance kind | Meaning |
| --- | --- |
| process success | The tutorial only needs to complete successfully. |
| minimum match ratio | The recovered plaintext must meet a stated threshold. |
| near-solve minimum match | Exact recovery is not required, but the near-solve quality must be reported. |
| requires asset profile | The tutorial is valid only when the named assets are available. |
| blocked known issue | The tutorial is excluded until a known problem is fixed. |

The pretty-print runner currently uses minimum match thresholds for every
selected tutorial.

## Truth And Oracle Use

Many tutorials use known answers because tutorials are controlled lessons.

That is acceptable only when the report makes it visible. The reader must be
able to tell whether a known key, known plaintext, or oracle stop score was used
to guide or stop the lesson.

Truth data used for teaching must not quietly become production ranking logic.

## Match Ratio

The match ratio is an evidence score for the tutorial.

For exact tutorials, the threshold is usually:

```text
1.000
```

For near-solve or stochastic tutorials, the threshold may be lower. A lower
threshold is not a hidden failure if the tutorial is explicitly classified that
way and the output says so.

## Tutorial Reports

The compact tutorial report schema is:

```text
rdp_tutorial_run_report.v1
```

A tutorial report can include:

- title
- app version
- cipher
- recovered flag
- match ratio
- solver summary
- key summary
- benchmark summary
- timings
- telemetry presence
- solver-report truth/oracle fields
- rune and index previews

This report is for teaching and release evidence. It is not a replay file.

## What Tutorials Do Not Prove

A passing tutorial does not prove:

- every key length works
- every asset profile exists
- every scorer lane is production-ready
- every cipher variant is stable
- every long search will finish quickly

It proves the selected tutorial passed its stated acceptance rule in the current
release tree.

## Current Alignment Check

Before promoting these staged docs, check:

- the pretty-print runner list
- `tutorial_manifest_v1.json`
- release-contract tutorial gates
- tutorial report fields
- displayed `encoding_dir`
- oracle/truth-data fields
- final log paths

If two sources disagree in the future, the docs must name the disagreement and
choose one owner rather than smoothing over it.
