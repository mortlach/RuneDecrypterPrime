# Migration notes — v0.14

This slice does a support-layer freshness triage pass and folds one more obvious
old cluster into its natural archive home.

## What this adds

1. `rdp_v1` support freshness triage note
2. benchmark-campaign support freshness triage note
3. old `v1OLD/bughunt/` cluster folded into the forensic-audit archive

## Why this slice matters

The main remaining problem in the active homes is no longer missing structure.
It is ambiguity about which support notes are:
- likely still live support
- historical but useful
- candidates to move to archive later

This slice starts making that explicit.
