# Outputs

Status: user guide

RDP writes generated output under:

```text
output/
```

Do not commit generated output.

## Tutorial output

Tutorial runs usually write under:

```text
output/tutorials/
```

Exact folder names can vary by run.

## What you may find

```text
logs
reports
summary files
telemetry
artefacts from a run
```

## What to inspect first

For a tutorial run, start with the tutorial summary and any report files in the
run folder.

For expert users and GUI/front-end developers, read:

```text
docs/expert/reports_and_artifacts.md
docs/expert/gui_interface_contract.md
```

## Common warnings

A run may tell you:

```text
optional asset missing
near-solve threshold used
known truth/key used for checking
solver stopped by budget
tutorial entry is optional or blocked
```

Those warnings are important and should not be hidden.
