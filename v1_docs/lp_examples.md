# Liber Primus Examples

Status: staged V1 draft

RDP has Liber Primus support because Liber Primus is the main real puzzle
domain that shaped the project. V1 explains that support clearly without
making every historical workbook part of the beginner path.

## Current Beginner LP Tutorial

The current pretty-print LP tutorial is:

```text
tutorials/v1/Tutorial_LP_Welcome_Pilgrim_Solve.py
```

It is included in the pretty-print release runner:

```text
python tutorials/v1/run_tutorials.py
```

This tutorial loads the solved-LP Welcome Pilgrim workbook, runs the solve
through the current RDP API, and prints the result through the standard RDP
display layer.

## Solved LP Workbooks

Solved LP workbooks live under:

```text
solving/solved_lp/
```

Current workbook files include:

| File | Role |
| --- | --- |
| `01_A_Warning.py` | solved LP workbook |
| `02_Welcome_Pilgrim.py` | solved LP workbook used by the pretty-print tutorial |
| `03_Some_Wisdom.py` | solved LP workbook |
| `04_Koan_A_Man.py` | solved LP workbook |
| `05_Loss_Of_Divinity.py` | solved LP workbook |
| `06_Koan_During_Lesson.py` | solved LP workbook |
| `07_Instruction.py` | solved LP workbook |
| `08_An_End.py` | solved LP workbook |
| `09_Parable.py` | solved LP workbook |

These are valuable evidence and examples, but they are not the same thing as
the beginner tutorial runner.

## Source Labels

LP inputs can be referred to by source labels.

The Welcome Pilgrim tutorial uses:

```text
red_rune.welcome_pilgrim
```

The LP source catalogue resolves labels like this into deterministic solver
payloads: rune indices, word-length index data, and metadata about where the
text came from.

## SourceReferenceInput

The public `RunSpec` input surface can represent LP inputs with `SourceReferenceInput`.

Supported LP source kinds are:

| Source kind | Meaning |
| --- | --- |
| `liber_primus.label` | a named LP source label |
| `liber_primus.locator` | a typed page/line/route locator |
| `liber_primus.partition` | a typed partition of the LP source |

The source ref records the source kind, asset id, asset version, and a small
JSON-safe `ref` mapping. RDP validates these fields early so a bad LP reference
does not become a vague solver failure later.

## Evidence Metadata

LP tutorial output shows enough metadata to explain what was solved.

For Welcome Pilgrim, the display summary can include:

- source label
- resolved source label
- recipe label
- cipher family
- solver variant
- scorer variant
- encoding direction
- match ratio
- oracle/truth-data fields

This is not decoration. It lets a reviewer tell whether a tutorial solved the
expected LP source with the expected recipe.

## What V1 Should Avoid

V1 docs do not pretend that every solved LP workbook is a polished beginner
lesson.

Use this distinction:

- tutorial: a curated lesson in `tutorials/v1/`
- workbook: a more detailed solved example in `solving/solved_lp/`
- source catalogue: the typed label/locator/partition layer for LP inputs
- report: the evidence that says what actually happened

That keeps the beginner path small while preserving the real LP context for
readers who want to go deeper.

## Open Alignment

Before release, decide which solved LP workbooks receive pretty-print
tutorial wrappers and which should remain advanced examples only.

The V1 docs list only the LP examples that are meant to be part of the
public release story.
