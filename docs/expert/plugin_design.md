# Plugin design

Status: expert user guide

RDP's plugin idea is simple: add new cipher/scoring/solver behaviour without
turning the whole system into one large script.

Plugins should fit the existing component boundaries.

## Why plugins exist

Cryptanalysis experiments need many cipher and scoring variants.

A plugin-style design lets RDP add variants while keeping:

```text
source loading separate
cipher logic separate
solver logic separate
scoring logic separate
reports consistent
```

## Plugin principles

### One owner per behaviour

A new feature should have one obvious owner.

Examples:

```text
cipher transform        cipher/plugin
key shape               key spec / cipher config
solver budget           solver spec/config
scoring mode            scorer config
source label            source reference/catalogue
report field            report/artefact layer
```

### Public choices are friendly

A user or GUI should be able to pick meaningful options:

```text
cipher family
solver type
seed
asset profile
tutorial
source label
```

### Runtime state is explicit

Once a run starts, the runtime should have clear, typed state.

Avoid hidden globals, local script constants, or ad-hoc dictionaries as the main
state mechanism.

## Plugin metadata for GUIs

A future GUI benefits from metadata such as:

```text
display name
short description
input fields
allowed values
default values
whether optional assets are required
whether output is exact/near-solve/report-only
```

This metadata should be machine-readable where possible.
