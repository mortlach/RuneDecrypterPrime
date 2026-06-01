# 5455 empirical attempt 001 — payload parity control

Status: active
Work status: done
Project: p13_real_ciphertext_campaign

## Attempt title

Empirical attempt 001 — payload parity control

## Exact question

Do the two already-recognised `5455` payload routes agree on the same thread
object?

Routes being compared:
1. LP pages 54–55 span view
2. section 13 page-split route via `load_lp_master_section(13, split="page")`

## Why this is the first empirical attempt

This is the narrowest real empirical comparison available from the verified
evidence already in the bundle.

It asks a measurable control question:
- are the two recognised payload routes consistent?

It does **not** ask whether the ciphertext is solved.

## Inputs held fixed

- `5455` thread definition
- pages 54–55 / section-13 target span
- expected ciphertext-index length `308`
- existing transcript/API verification anchors

## Success condition

The attempt is successful when the verified code/test anchors support the claim
that:
- the two recognised payload routes are parity-consistent for the `5455` thread
- the expected ciphertext-index length remains `308`

## Why this matters for later notes

If this attempt holds, later empirical notes do not need to keep re-arguing what
the thread object is.
They can focus on actual comparison/control method choices instead.
