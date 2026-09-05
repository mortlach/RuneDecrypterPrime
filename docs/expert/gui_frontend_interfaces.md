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

## Runnable examples are not a GUI protocol

`tutorials/v1/README.md` is the human catalogue and
`tutorials/v1/run_tutorials.py` is a source-checkout runner. Neither is a stable
machine-readable GUI protocol. A front-end should own its navigation metadata,
construct typed `RunSpec` values, and call `api.run`.

The catalogue remains useful review material for asset requirements, result
policy and truth use. Do not scrape its Markdown tables or console prose at
runtime.

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
