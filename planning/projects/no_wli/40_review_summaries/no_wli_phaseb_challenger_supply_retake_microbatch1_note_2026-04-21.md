# Phase-B challenger supply retake microbatch 1 note

Date: 2026-04-21

Status:

- completed
- branch point

## What ran

Completed microbatch:

- case:
  - `1111/search7002`
- preset:
  - `phaseb_supply_selected24_saved64_stage3only_v1`
- runtime bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260420T163353521403Z__bench_solve_pipeline_no_wli__ee62083`
- extracted readout:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260421T145900Z__phaseb_challenger_supply_retake_microbatch_v1/`

## Question

Can a one-job richer-supply canary create real spare retained `phaseB_topk`
challengers on the fixed panel before a deeper supply retry is justified?

## Result

- elapsed_hours:
  - `18.82`
- best_match_ratio:
  - `0.750`
- retained_best_match_ratio:
  - `0.754`
- best_match_delta_vs_retained:
  - `-0.004`
- phaseB_topk_saved_count:
  - `20`
- phaseB_topk_saved_unique_end_hash:
  - `20`
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

## Interpretation

The upstream supply suspicion is validated on this richer pool:

- real spare retained `phaseB_topk` challengers now exist
- the spare challenger count is not cosmetic duplicate growth
- downstream `phaseB_topk`-only replacement is now structurally live

What did not happen:

- the top-line outcome did not improve
- the winner stayed on the anchor lane
- quota did not become the live downstream lever because the non-anchor selected
  surface was already saturated with `phaseB_topk`

## Operational read

This microbatch was scientifically useful but operationally expensive.

- intended session budget:
  - about `12h`
- actual elapsed:
  - about `18.82h`

So this result does not justify another immediate deeper upstream supply retry.

## Decision

Close the Phase-B supply retake as a branch point after microbatch 1.

Next active line:

- narrow richer-pool downstream replacement reopen
- exact saved-surface lane first
- no new upstream supply runtime yet

Held next branch if the richer-pool reopen closes:

- `stage3_entry_const_local_depth_p9`
