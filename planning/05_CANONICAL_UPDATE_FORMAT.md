# Canonical update format

This file defines the standard writing shape for new planning updates.

The goal is not bureaucracy.
The goal is to keep updates short, portable, and easy for multiple agents to
continue without losing track of what is true.

## Standard update rule

Every meaningful project update should touch one or more of:
- current state
- workstream index
- active runbook
- project snapshot
- result/status ledger

Do not rely on one giant rolling log as the only record of current truth.

## Standard header block for active planning docs

```text
Status: active
Work status: in_progress
Project: <project_name>
Owner: <person / owner-review / maintainer / agent>
Last updated: YYYY-MM-DD
Source-of-truth parents:
- <path>
- <path>
```

## Standard short structure for update notes

Use this shape unless there is a good reason not to.

```text
## What changed

## Why it matters

## Evidence / linked files

## Next step

## What did not change
```

## Standard project snapshot shape

Keep snapshots to one page.

```text
# <project> snapshot

Status:
Work status:

## Current role

## What is real

## What is still thin / blocked / unsettled

## Immediate next slice
```

## Standard result note shape

Use one narrow question only.

```text
## Date

## Thread / case / run id

## Exact question

## Inputs used

## Result summary

## Why this matters

## Next action
```

## Standard rules for agents

1. Update the document map when a source doc is promoted or moved.
2. Update the project snapshot when the project state materially changes.
3. Update the migration ledger when a new migration slice moves real material.
4. Prefer one small safe slice per chat over broad uncontrolled reorganisation.
5. Keep logs as evidence, not as the only source of truth.
