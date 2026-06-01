# 5455 comparison attempt 001

Status: active
Work status: in_progress
Project: p13_real_ciphertext_campaign

## Attempt title

Comparison attempt 001 — deterministic control package freeze

## Purpose

This is the first real comparison/control attempt for the `5455` thread.

It does **not** attempt to solve the real-ciphertext problem directly.
It asks a narrower and necessary question:

- can we freeze one deterministic payload/input contract and one deterministic
  upstream-anchor set, so later thread-specific runs are comparable and not
  ad-hoc?

## Exact attempt question

Using the already pinned `5455` control package, can we define one canonical
attempt input contract that later result notes must reference?

## Why this counts as a real attempt

This is more than the earlier control-question note.
That earlier note asked what the first useful question should be.

This attempt now fixes:
- what later attempts must hold constant
- what later attempts are allowed to vary
- what counts as a comparable thread note

## Inputs that must stay fixed

- LP pages 54–55 / section-13 payload route
- `load_lp_master_section(13, split="page")`
- expected ciphertext-index length `308`
- first pinned upstream anchors from:
  - solve-proof support
  - no-WLI current-state / experiment-index / runbook
  - p13 readiness-context notes as context only

## Things later attempts may vary

Later real thread attempts may vary:
- exact comparison method
- exact optimisation/selection path
- what upstream no-WLI artefact is emphasised most
- what run/log evidence is attached

But they should not silently vary the payload source itself.

## Success condition

This attempt is successful when:
- the input contract note exists
- the result note for this attempt states that the contract is frozen
- future `5455` notes can refer back to this attempt as the baseline control package
