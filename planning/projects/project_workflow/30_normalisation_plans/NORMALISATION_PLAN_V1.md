# Normalisation plan v1

Status: active
Work status: done
Project: project_workflow

## Phase 1
Lock the standard active-project schema.

## Phase 2
Normalise `rdp_v1` to that schema.

## Phase 3
Normalise `benchmark_campaign_v1_1` to that schema.

## Phase 4
Lightly normalise `p13_real_ciphertext_campaign` to that schema while keeping
it thin and downstream.

## Phase 5
Give completed/archive homes the lighter standard shape.

## Main discipline

Do not rewrite every file.
Do:
- keep a small front-door layer
- group secondary material cleanly
- push history behind the front door
