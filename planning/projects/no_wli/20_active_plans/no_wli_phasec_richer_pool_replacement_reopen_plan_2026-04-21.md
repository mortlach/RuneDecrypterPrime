# Phase-C richer-pool replacement reopen plan

Date: 2026-04-21

Status:

- active
- next study
- offline exact-lane reopen

## Why this note exists

The Phase-B challenger supply retake microbatch on `1111/search7002` with
`phaseb_supply_selected24_saved64_stage3only_v1` is now complete.

That microbatch changed the branch point:

- real spare retained non-selected `phaseB_topk` challengers now exist
- duplicates did not explain the new supply
- downstream `phaseB_topk`-only replacement is now structurally engageable
- top-line best-match outcome still stayed flat to slightly worse
- runtime cost was too high to justify another immediate upstream supply retry

So the next mechanism question moves downstream again, but only on the richer
retained pool that now exists.

## Main question

On the richer retained pool from the completed `1111/search7002` supply run,
can a narrow `phaseB_topk`-only replacement rule produce a real exact-lane gain
that beats the richer-pool control and reorder floor?

## Mechanism layer

- selection

## Working basis

Use only this completed richer-pool runtime bundle as the retained source:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260420T163353521403Z__bench_solve_pipeline_no_wli__ee62083`

Current richer-pool facts from that run:

- true spare non-selected retained `phaseB_topk` challengers:
  - `14`
- duplicate non-selected retained `phaseB_topk` challengers:
  - `0`
- replacement engageable:
  - `1`
- quota engageable:
  - `0`
- winner:
  - `stage3_best_phaseB / anchor`

## Why this is the right next move

This is the first downstream mechanism that is now genuinely unblocked.

It is also cheaper than another upstream runtime retry, and it can answer the
actual open question:

- does the new supply become solver-usable downstream
- or does it remain mostly archived variety with no practical lift?

## Required pre-run block

Before any compute-heavy reopen batch in this line, write:

- Question
- Suspicion
- Main alternative
- If suspicion is true, expect
- If alternative is true, expect
- Tomorrow's decision rule

## Budget rule

This reopen should stay inside an approximately `8h` wallclock budget.

So for this line:

- prefer offline saved-surface exact analysis over fresh runtime first
- keep the first reopen to the smallest independently complete width sweep
- do not schedule another `search7002` runtime as the first follow-up
- if a later runtime confirmation becomes justified, choose only a cell whose
  conservative retained timing evidence fits the target budget, or prove the
  budget with a same-family canary first

## Study label

Use a label in this shape:

- `phasec_richer_pool_phaseb_replacement_reopen_v1`

## Core study design

This is a narrow richer-pool downstream reopen, not a broad new matrix.

### Controls

Always include:

- richer-pool `source_order`
- richer-pool `phaseb_topk_frontload_all_v1`

These are the minimum floor for judging whether replacement is doing anything
useful beyond order-only changes.

### Replacement sweep

First pass widths:

- `phaseb_topk_replace_width_1_v1`
- `phaseb_topk_replace_width_2_v1`
- `phaseb_topk_replace_width_3_v1`

Semantics:

- keep the retained anchor fixed
- evict the weakest retained non-anchor selected starts using retained selected
  order only
- insert only non-selected retained `phaseB_topk` challengers
- preserve retained `phaseB_topk` order inside the replacement stream
- do not use any fresh cross-source scoring metric

Do not open quota first.

Quota stayed structurally saturated on the richer pool, so it is not the next
honest lever.

## Required outputs

This reopen must produce:

- one machine-readable per-policy summary table
- one machine-readable case-level delta table
- identity-level diagnostics for:
  - surface changed
  - evicted hashes
  - inserted hashes
  - winner hash/source/lane changes
- one short human readout
- one explicit promote / refine / close recommendation

## Analysis questions

The readout must answer:

- does any replacement width beat richer-pool `source_order`?
- does any replacement width beat the richer-pool reorder floor?
- are gains real winner changes or only cosmetic surface changes?
- does width `1` stay outcome-neutral even when spare challengers now exist?
- does widening replacement help, flatten, or add harm?

## Decision rules

### Promote to narrow runtime confirmation only if

- one replacement width clearly beats both richer-pool control and reorder floor
- the effect is larger than local drift / noise
- identity-level diagnostics show a meaningful downstream change
- the planned confirmation run can honestly fit the `~8h` runtime target

### Refine only if

- one width looks promising
- but the exact winner-change story is still unclear
- or the best confirmation cell is still ambiguous under the budget contract

### Close if

- no replacement width beats the richer-pool reorder floor
- or changes remain mostly cosmetic
- or any gain is too small to justify another expensive runtime step

If this line closes, the held next branch is:

- `stage3_entry_const_local_depth_p9`

## Not allowed in this reopen

Do not add any of these:

- another broader upstream supply runtime retry
- a quota-first reopen
- new cross-source scoring metrics
- broad case widening
- exact runtime confirmation before the richer-pool saved-surface read is clear
