# RDP v1 forensic reference note

Status: active
Work status: done
Project: rdp_v1

This note explains why the old forensic audit pack still matters to `rdp_v1`.

## Why it matters

`rdp_v1` is partly a convergence and boundary-truth project.
Older forensic audit material can still help with:
- source-file traceability
- older bug-hunt context
- earlier implementation-plan logic
- verifying what had already been audited before later refactors

## Where the preserved pack now lives

- `planning/archive/forensic_audit_2026/`

## What should not happen

Do not treat the forensic audit pack as the live `rdp_v1` home.
It is supporting historical evidence only.

## When to use it

Use it when:
- checking an older source/reference claim
- understanding why a previous audit made a certain recommendation
- tracing older proposed tests or bug-hunt items

Otherwise, start from the live `rdp_v1` home.
