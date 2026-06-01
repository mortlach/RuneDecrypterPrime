# Hard crib integration reference — 2026-04-09

Status: active
Work status: done
Project: benchmark_campaign_v1_1

This note preserves a future-method idea that may matter later for the harder
p13 cases, without pretending it is an active implementation target right now.

## Why this belongs here

The hard-crib idea is not really a `5455` project-home note yet.
It is more naturally a broader future-method reference for the p13 / benchmark
programme.

That makes this benchmark-side home a better fit than forcing it into the
downstream real-ciphertext thread pack.

## What the legacy note contributes

The old note argues for:
- hard cribs as must-match constraints
- early rejection before expensive scoring/optimisation continues
- a low-risk integration point at the runtime scoring choke-point
- explicit schema/config implications for scorer validation

## Why it is not active now

Right now:
- `5455` is still a downstream target, not the main development centre
- broader p13 work is still upstream
- the method idea may change substantially before it becomes implementation work

## Working rule

Keep this as:
- future-method reference
- useful design idea
- not active benchmark or 5455 implementation truth
