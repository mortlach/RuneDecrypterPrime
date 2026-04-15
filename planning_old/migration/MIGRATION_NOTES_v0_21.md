# Migration notes — v0.21

This slice stays focused on `5455` and avoids further cut-over churn.

## What this adds

1. the first empirical `5455` comparison/control attempt
2. the first empirical result note for the thread
3. a small explicit note that `no_wli` remains an upstream reference home and is
   not being re-homed here
4. updated `5455` status and remaining-work files

## Why this slice matters

The `5455` home now has:
- control-question notes
- control-package notes
- baseline contract notes

What it still needed was one real empirical control result that did not pretend
to be a solve result.

This slice uses the already-verified LP/API parity anchor for that purpose.
