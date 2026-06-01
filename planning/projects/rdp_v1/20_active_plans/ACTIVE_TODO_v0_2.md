# Active todo — v0.2

Status: active
Work status: in_progress
Project: rdp_v1

## Goal of this todo

Convert the owner-review and execution-pack material into one stable project
home without pretending the full code convergence is already done.

## Current top items

### T1. Freeze the live `rdp_v1` entry pack
Why:
- replace split entry points with one stable home

Files:
- `00_CURRENT_STATE.md`
- `01_WORKSTREAM_INDEX.md`
- `02_OPEN_QUESTIONS.md`
- `03_DOCUMENT_MAP.md`
- `04_ACTIVE_RUNBOOK.md`

Status:
- in progress

Exit condition:
- these five files are good enough to replace the old v1 entry habit

### T2. Keep a strict landed vs target-state note
Why:
- avoid pretending governance language is already fully implemented

Files:
- `30_architecture_specs/rdp_v1_current_code_crosscheck_note.md`

Status:
- started in v0.2

Exit condition:
- every major v1 architectural claim is marked as landed, partly landed, or not
  found in the reviewed bundle

### T3. Promote the real governing docs
Why:
- make the new home useful, not just empty scaffolding

Files already promoted:
- governance charter
- campaign spec
- refactor plan
- current phase
- current risks
- task register
- implementation plan
- ADR starter pack

Next concern:
- do not over-copy minor legacy notes before the main home is stable

### T4. Prepare the first v1 migration to legacy
Why:
- once the new home works, older active-index entry points should stop acting
  as live truth

Deferred until:
- new `rdp_v1` pack is stable enough to take over
