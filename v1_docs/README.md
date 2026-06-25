# RDP V1 documentation rewrite

Status: draft documentation work area

This folder is the staging area for the new V1 documentation set.

It is separate from `docs/` so the new reader path can be built and reviewed
without disturbing the existing documentation tree too early. The old `docs/`
folder remains source material and contract evidence until individual pages are
replaced, redirected, archived, or kept.

## Current rule

Do not copy old planning folders, logs, generated output, handoff packs, or local
archive material into this folder.

Use old planning documents only as read-only context. Any content promoted here
must be rewritten against the current clean release tree.

## First command path

The public beginner path should stay simple:

```text
python install.py
python tutorials/v1/run_tutorials.py
```

For printout review, edit `tutorials/v1/run_tutorials.py` and set:

```python
CONSOLE_OUTPUT = ConsoleOutput.FULL
```

No special shell setup, no separate tutorial config file, and no CLI-heavy
tutorial control in beginner docs.

## Plan

The phased plan lives in:

```text
00_REWRITE_PLAN.md
```

The current cross-check ledger lives in:

```text
02_CROSSCHECK.md
```

The remaining-work checklist lives in:

```text
03_REMAINING_WORK.md
```

The review summary lives in:

```text
04_REVIEW_SUMMARY.md
```

## Draft Pages

- `install.md`
- `tutorials.md`
- `troubleshooting.md`
- `outputs.md`
- `core_design.md`
- `runes_and_text.md`
- `runs_reports_and_artifacts.md`
- `tutorials_as_evidence.md`
- `lp_examples.md`
- `development/testing.md`
- `development/adding_a_tutorial.md`
- `development/docs_style.md`
- `reference/run_spec.md`
- `reference/reports.md`
- `reference/artifacts.md`
- `reference/tutorial_runners.md`
- `reference/tutorial_manifest.md`
- `01_SOURCE_MAP.md`
- `02_CROSSCHECK.md`
- `03_REMAINING_WORK.md`
- `04_REVIEW_SUMMARY.md`
