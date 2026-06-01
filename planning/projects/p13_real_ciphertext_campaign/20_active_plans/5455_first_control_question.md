# 5455 first control question

Status: active
Work status: in_progress
Project: p13_real_ciphertext_campaign

## Exact question

Before any broader real-ciphertext push, can we reproduce a **deterministic
input/control package** for the `5455` thread that fixes:

1. the canonical payload source as the LP pages 54–55 / section-13 span
2. the expected ciphertext-index length as `308`
3. the exact solve-proof / no-WLI upstream references that justify the first
   transfer attempt

## Why this is the first question

This is the narrowest useful question because it avoids pretending we already
have a result on the real-ciphertext problem itself.

It asks a simpler and necessary control question first:
- do we know exactly what object we are trying to solve
- and do we know exactly which upstream evidence should be treated as the first
  justified transfer basis

## Verified anchors already available in the bundle

### Payload anchor
- pages 54–55 span
- section 13 route
- `load_lp_master_section(13, split="page")`
- expected ciphertext-index length `308`

### Upstream support surfaces
- solve-proof bundle
- no-WLI planning/current-state/runbook
- p13 readiness-context pack

## Success condition for this question

The question is considered answered when the bundle contains one short result
note that states:

- the canonical payload route
- the canonical expected span length
- the first pinned upstream anchors
- any remaining ambiguity

## Non-goals

This question does **not** ask whether the real-ciphertext thread is solved.
It only asks whether the first control package is now properly pinned down.
