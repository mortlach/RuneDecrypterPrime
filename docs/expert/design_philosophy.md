# Design philosophy and motivations

Status: expert user guide

RDP exists to make decryption experiments repeatable, inspectable, and honest.

The project is not trying to be a magic black box. It is trying to make it clear
what was tried, what evidence was used, and why a run stopped.

## Motivation

Cryptanalysis experiments can easily become hard to trust:

```text
a script is changed
a seed is forgotten
a scorer changes silently
a solver uses a known answer without saying so
an optional backend changes behaviour
output is only printed to the terminal
```

RDP's design tries to stop that.

## Design goals

### Repeatability

A run should be repeatable when these match:

```text
input text
WLI/source data
cipher model
key model
solver settings
seed
scorer settings
backend/device
asset profile
```

### Inspectability

A user should be able to inspect:

```text
what ran
what was searched
what scored candidates
why the solver stopped
what result was accepted
where output was written
```

### Honest boundaries

RDP should separate:

```text
known source text
known key or truth data
solver search
scoring/ranking
tutorial acceptance
report-only diagnostics
```

If a known answer is used for tutorial stopping or validation, that should be
visible.

### Friendly outside, strict inside

For users and GUIs, RDP should expose friendly choices:

```text
tutorial gate
asset profile
cipher family
solver
seed
source label
```

Inside the runtime, those choices should become typed, explicit config.

### Reports over guesswork

Important decisions should appear in structured output, not only in console
text.

## Practical rule

If a feature cannot be explained, repeated, and inspected, it is not ready to be
presented as a stable user feature.
