# Reports and artefacts

Status: expert user guide

Reports and artefacts are the main evidence surface for expert users and GUIs.

## Why reports matter

Console output is useful for humans watching a run, but it is not enough for
repeatability.

Reports should answer:

```text
what ran
what options were used
what result was found
why the run stopped
where supporting files are
whether known truth/key was used
```

## Output location

Generated output belongs under:

```text
output/
```

Tutorial runs usually write under:

```text
output/tutorials/
```

Exact run-id folders may vary.

## What a GUI should read

Prefer structured data:

```text
tutorial report
solver report
artefact manifest
telemetry JSONL
summary JSON/CSV where available
```

Avoid making the GUI depend on human console sentences.

## Important report concepts

```text
tutorial name
gate profile
asset profile
script path
acceptance kind
match ratio
pass/fail status
near-solve status
solver stop reason
known truth/key use
result text/key
artefact paths
warnings
```

## Telemetry

Telemetry is runtime evidence written as structured events.

Useful event families include:

```text
telemetry.run
telemetry.solver_progress
telemetry.solver_spans
```
