# Integration history map — 2026-04-09

Status: active
Work status: done
Project: rdp_v1

This note records the old `workgin/` merge notes now preserved under the active
`rdp_v1` home as supporting history.

## Promoted source files

- `planning/old/workgin/merge_integration_plan_local_vs_network_2026-03-08.md`
- `planning/old/workgin/merge_issue_log_2026-03-08.md`

## Why they are worth keeping

### A. Merge integration plan
Useful because it captures:
- planned port over blind merge
- integration scope across API/core/scoring/tools/tests
- explicit merge constraints and review decisions

### B. Merge issue log
Useful because it captures concrete prevention rules such as:
- no machine absolute paths in tracked code
- runner binding smoke checks
- optional asset fallback behaviour for default startup

## Current role

These notes are:
- useful supporting integration history
- not the live `rdp_v1` entry pack
- not archive-only yet, because their lessons still map naturally to current
  convergence work
