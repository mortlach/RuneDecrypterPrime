# V1 Documentation Review Summary

Status: staged review note

This page summarises the current `v1_docs/` rewrite for review.

The docs are still staged. The old `docs/` tree remains in place until the new
reader path is approved and promoted.

## Review Goal

The V1 docs should be comprehensive without turning into a code dump.

They need to serve four readers:

- a beginner running RDP for the first time
- a tutorial reviewer checking printouts and thresholds
- a developer adding or maintaining a tutorial
- a technical reader who wants the design contracts

## Reader Path

Start here:

```text
README.md
install.md
tutorials.md
troubleshooting.md
```

Then read:

```text
core_design.md
runes_and_text.md
runs_reports_and_artifacts.md
tutorials_as_evidence.md
outputs.md
```

Use the reference and development pages when checking exact contracts:

```text
reference/
development/
```

## Current Policy

The staged docs now use the current V1 policy:

- beginner commands use plain `python`
- no beginner virtual-environment assumption
- no RDP tutorial environment variables
- no tutorial CLI switch surface
- no separate tutorial config file for normal review
- selected tutorials live under `tutorials/v1/`
- older replaced tutorials live under `tutorials/legacy/`
- the normal tutorial gate is `run_pretty_print_release.py`
- the full output review runner is `run_pretty_print_output_review.py`

## Tutorial State

The selected pretty-print tutorial set has 21 tutorials.

The runner and manifest have been checked together:

```text
selected=21
manifest=21
missing_files=[]
missing_manifest=[]
extra_manifest=[]
threshold_mismatch=[]
```

The public tutorial list in `tutorials.md` matches the selected runner list.

## Style Review

The public-facing pages now avoid sounding like old planning notes. They state
the current contract directly where the code and policy are settled.

Planning language remains in:

```text
00_REWRITE_PLAN.md
01_SOURCE_MAP.md
02_CROSSCHECK.md
03_REMAINING_WORK.md
```

Those files are review ledgers, not final beginner documentation.

## Checks Run

The staged docs have been checked for:

- broken local Markdown links
- stale PrettyPrint tutorial names
- stale `_legacy_blocked` paths
- beginner-path environment-variable instructions
- runner/manifest/tutorial-list alignment

Current link check result:

```text
missing_links=0
```

## Review Questions

Reviewers should decide:

- whether `v1_docs/` should be promoted as one new docs area or split into the
  existing `docs/` tree page by page
- whether `docs/INDEX.md` should become a redirect-style page or be removed
- whether the LP docs should list only `Welcome Pilgrim` for V1, or also point
  advanced readers to the other solved workbooks
- whether the tutorial table should stay hand-written for V1 or be generated
  from the runner/manifest in a later cleanup
- whether each pretty-print tutorial output is friendly and consistent enough
  after a full output-review run

## Before Promotion

Before these docs become public V1 docs:

1. Run the normal tutorial gate.
2. Run the full printout-review runner, or review its captured logs.
3. Update `02_CROSSCHECK.md` with the final results.
4. Choose the promotion layout.
5. Replace, redirect, or retire stale pages in the old `docs/` tree.
