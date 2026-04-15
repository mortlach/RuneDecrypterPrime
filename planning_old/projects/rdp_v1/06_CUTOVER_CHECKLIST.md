# RDP v1 cut-over checklist

Status: active
Work status: done
Project: rdp_v1

This checklist defines what should be true before the new `rdp_v1` home can be
treated as the default entry point instead of the older split reading habit.

## Minimum live pack that must be stable

- `00_CURRENT_STATE.md`
- `01_WORKSTREAM_INDEX.md`
- `03_DOCUMENT_MAP.md`
- `04_ACTIVE_RUNBOOK.md`
- `05_REMAINING_WORK.md`
- current code-crosscheck note(s)

## Conditions to call the home "good enough"

### C1. Current-state file reads clearly as present truth
- no obvious target-state drift
- main status and purpose are clear

### C2. Workstream index matches the real project shape
- governance
- convergence
- execution pack
- support/reference layers clearly secondary

### C3. Support layers are clearly split
- active support is identified
- historical-but-useful support is identified
- archive-later candidates are identified

### C4. Code-facing crosscheck is explicit
- target-state items are still marked as target-state
- confirmed current code surfaces are named

### C5. Old entry habits can safely be downgraded
- there is no need to start from old `planning/v1/...` paths first
- old active-index behaviour is no longer needed for orientation

### C6. Live backlinks to old planning surfaces are replaced
- active/spec files no longer depend on `planning/working/...` or `planning/review/...` paths
- any remaining old-path references are clearly historical or archived
- remaining orphan files are explicitly classified before retirement

## Still not required for cut-over

Not required before cut-over:
- full archive triage of every old v1 note
- perfect final architecture convergence
- moving every historical support note out immediately

## Current use

These conditions are now satisfied enough for practical use:
- the repo-wide canonical-cutover note now exists
- the old `planning/v1/` reading habit is retired in practice
