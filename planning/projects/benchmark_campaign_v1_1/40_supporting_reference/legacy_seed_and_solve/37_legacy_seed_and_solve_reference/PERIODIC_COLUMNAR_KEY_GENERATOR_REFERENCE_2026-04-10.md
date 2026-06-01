# Periodic-columnar key generator reference - 2026-04-10

Status: active
Work status: done
Project: benchmark_campaign_v1_1

This note records a preserved older key-generator design spec.

## Preserved source file

- `planning/old/v1OLD/seed_gen_plans`

Preserved here as:
- `seed_gen_plans_legacy_reference.txt`

## Why it is worth keeping

This note is useful because it captures:
- a deterministic audited seed-generator design for periodic-then-columnar keys
- explicit input/output and invariants for full-key generation
- separation between cheap structured seed generation and later refinement
- scorer-reuse and determinism requirements that still match repo norms

## Current role

This is:
- legacy seed/method reference
- useful design context for older benchmark seeding ideas
- not active benchmark or solver truth
