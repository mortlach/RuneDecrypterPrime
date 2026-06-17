# Tutorial catalogue

Status: user guide

The runnable tutorial scripts live under:

```text
tutorials/v1/
```

The manifest that describes them is:

```text
tutorials/v1/tutorial_manifest_v1.json
```

The runner is:

```text
tutorials/v1/run_all.py
```

## Normal tutorial run

```text
python tutorials/v1/run_all.py
```

Success means:

```text
failed   : 0
```

## What the catalogue tells you

The manifest can describe:

```text
tutorial name
script path
gate labels
asset profile
cipher family
acceptance kind
match ratio or threshold
known truth/key use
active, optional, or blocked status
```

## Active tutorials

Active tutorials are normal user choices for the selected gate.

Examples may include:

```text
ScheduledStreamLookup real-solve tutorials
Vigenere examples
monoalphabetic substitution examples
columnar transposition examples
crib-drag/API examples
Liber Primus labelled-source examples
```

## Optional tutorials

Optional tutorials may require extra assets or take longer.

A GUI or user-facing tool should label them as optional.

## Blocked or legacy entries

Blocked entries can remain in the manifest for transparency, but they should not
be shown as recommended beginner actions.

## Tutorial notes

User-facing tutorial notes live under:

```text
docs/tutorials/
```

Start with:

```text
docs/tutorials/index.md
```
