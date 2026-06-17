# Source and tutorial interfaces

Status: expert user guide

This page explains the stable source/tutorial surfaces expert users and GUIs
should understand.

## Source interface

A source identifies the text being solved.

Common user-facing source choices:

```text
raw rune text
normalised rune indices
Liber Primus source label
Liber Primus locator or partition where supported
```

A source should not hide solver settings.

## Liber Primus labels

LP labels identify known text fragments.

Read:

```text
docs/guides/liber_primus_solved_sources.md
```

Important distinction:

```text
source label = which text
solve recipe = how to solve it
```

## Tutorial interface

Tutorials live under:

```text
tutorials/v1/
```

The manifest is:

```text
tutorials/v1/tutorial_manifest_v1.json
```

The runner is:

```text
tutorials/v1/run_all.py
```

## Manifest fields a GUI should care about

A GUI or expert catalogue should care about:

```text
tutorial id/name
script path
gate labels
asset profile
cipher family
acceptance kind
match threshold
active/optional/blocked status
known truth/key use
```

## Active versus optional versus blocked

A GUI should separate:

```text
active tutorials          normal user choices
optional tutorials        require optional assets or longer runs
blocked/legacy entries    not normal user choices
```

Blocked entries can be listed for transparency, but should not be shown as
recommended beginner actions.
