# Phase-C Richer-Pool Replacement Reopen Closure Note

Date: 2026-04-22

Status:

- closed
- valid negative

## Result

The richer-pool downstream reopen is now closed from the completed exact-lane
bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260422T015033Z__phasec_richer_pool_phaseb_replacement_reopen_v1/`

Completed run facts:

- case:
  - `1111/search7002`
- retained richer-pool source:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260420T163353521403Z__bench_solve_pipeline_no_wli__ee62083`
- elapsed:
  - about `18m48s`
- recommendation:
  - `close`

## Exact-lane read

Controls:

- richer-pool `source_order`:
  - `0.750`
- richer-pool reorder floor `phaseb_topk_frontload_all_v1`:
  - `0.754`
  - delta vs control:
    - `+0.004`
  - winner changed:
    - `1`

Replacement widths:

- `phaseb_topk_replace_width_1_v1`:
  - `0.750`
  - delta vs control:
    - `0.000`
  - delta vs reorder floor:
    - `-0.004`
  - winner changed:
    - `0`
- `phaseb_topk_replace_width_2_v1`:
  - `0.750`
  - delta vs control:
    - `0.000`
  - delta vs reorder floor:
    - `-0.004`
  - winner changed:
    - `0`
- `phaseb_topk_replace_width_3_v1`:
  - `0.750`
  - delta vs control:
    - `0.000`
  - delta vs reorder floor:
    - `-0.004`
  - winner changed:
    - `0`

## Interpretation

- the richer supply did make downstream replacement structurally active
- replacement widths `1-3` all changed saved-start membership and order
- none of those active replacement edits changed the winner or improved score
- `phaseb_topk_frontload_all_v1` stayed the only exact-lane lift on this richer
  pool

So the reopen answered the real branch question cleanly:

- the extra retained `phaseB_topk` supply was real
- but narrow downstream `phaseB_topk`-only replacement still was not solver-usable
  on the exact saved-surface lane

## Decision

Do not:

- schedule runtime confirmation for this replacement family
- reopen quota first
- spend more time on richer-pool downstream replacement widths

Carry forward instead:

- the branch-point supply result remains valid
- the downstream replacement line is now closed
- the held next branch becomes active:
  - `stage3_entry_const_local_depth_p9`

## Next active line

The next active canary is:

- fixed-cell Stage-3 entry allocation compare
- preserve the bounded Stage 3.5 baseline stack
- change only Stage-3 entry allocation on `1111/search7004`
