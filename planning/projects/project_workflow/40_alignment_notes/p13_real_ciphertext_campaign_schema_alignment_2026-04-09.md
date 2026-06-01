# p13 real-ciphertext campaign schema alignment — 2026-04-09

Status: active
Work status: done
Project: project_workflow

## What has now been done

`p13_real_ciphertext_campaign` has now had a real schema-normalisation pass.

It keeps:
- front-door files
- `10_active_plans/`
- `20_specs_and_analysis/`
- `30_status_and_results/`
- `95_evidence_snapshots/`

It now keeps broader context behind:
- `40_supporting_reference/`

Historical cutover/archive material is now expected to sit outside the live
home under:
- `planning_old/projects/p13_real_ciphertext_campaign/`

## Why this is the right model

This keeps the thread-specific reading path dominant while still preserving
broader p13/no-WLI context as secondary material.

It is the right thin/downstream version of the common active-project schema.
