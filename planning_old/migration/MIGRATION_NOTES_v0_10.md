# Migration notes — v0.10

This slice adds one coherent forensic-audit archive pack and one small
`rdp_v1` support note that explains its role.

## What this adds

1. `archive/forensic_audit_2026/`
   - built from the old `planning/old/v1OLD/audit1/` cluster

2. `projects/rdp_v1/36_forensic_reference/`
   - a small note explaining why the forensic audit still matters to `rdp_v1`
   - without letting it become a live entry point

## Why this slice matters

The audit/forensic material is clearly important historically:
- source reference maps
- verification tracker
- implementation plan
- decisions
- test proposals
- forensic PDF

But it belongs as preserved reference, not as a competing live project home.
