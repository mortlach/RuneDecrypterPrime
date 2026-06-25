# GUI and front-end interfaces

Status: expert integrator guide

This page is for people building a GUI, overlay, notebook UI, or external
front-end for RDP.

## Recommended integration model

Use RDP as a structured runner:

```text
GUI chooses source/tutorial/options
  -> RDP runs tutorial/API/solver
  -> RDP writes structured output
  -> GUI reads reports/artefacts/telemetry
  -> GUI displays progress and result
```

Do not build the GUI around scraping human console text.

## Stable inputs to display

A GUI should expose these user choices first:

```text
tutorial
source label
cipher family
solver type
seed
gate profile
asset profile
output location
```

Advanced panels may expose:

```text
match threshold
partial recovery threshold
solver budget
scorer options
direction
known source/known key policy
```

## Tutorial manifest as catalogue

The tutorial manifest is the best first catalogue for GUI work:

```text
tutorials/v1/tutorial_manifest_v1.json
```

Use it to populate:

```text
tutorial list
active/optional/blocked status
gate labels
asset profile requirement
script path
acceptance type
expected match ratio or threshold
```

The GUI should not present blocked or legacy tutorial entries as normal beginner
options.

## Outputs to read

Generated output belongs under:

```text
output/
```

Tutorial output is usually under:

```text
output/tutorials/
```

A GUI should read structured files where available:

```text
reports
artefact manifests
telemetry JSONL
tutorial summaries
```

Avoid relying on exact human console wording.
