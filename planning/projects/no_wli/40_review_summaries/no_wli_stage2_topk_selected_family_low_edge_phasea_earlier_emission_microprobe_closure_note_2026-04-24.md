# Stage-2 Topk Selected-Family Low-Edge Phase-A Earlier-Emission Microprobe Closure Note

Date: 2026-04-24

Status:

- completed
- hold
- branch closed on the raw provisional `rank1` checkpoint surface

## Why this note exists

The selector branch had already established:

- a trusted late live-read gate:
  - `phasea_rank1_init_match >= 0.30`
- a trusted fixed `1111` split:
  - keep:
    - `7003,7004,7005`
  - filter:
    - `7001,7002`
- a failed first action canary:
  - semantics were fine
  - timing was too late

So the next honest question was narrower:

- can a provisional Phase-A checkpoint recover the same split materially earlier
  than the current late snapshot?

## Runs

Microprobe runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1.py`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1/`

Filtered canary:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_exact_replay_1111_search7002_v1/`

Kept canary:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T183152Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_exact_replay_1111_search7003_v1/`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_2026-04-24.log`

## Outcome

Machine summary:

- recommendation:
  - `hold`
- next branch:
  - `stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement`
- shared matching checkpoint count:
  - `0`

Per-canary result:

- `7002`
  - expected verdict:
    - `filter`
  - observed provisional verdict:
    - `filter`
  - matches at:
    - restart `16`
    - restart `32`
    - restart `48`
    - restart `64`
- `7003`
  - expected verdict:
    - `keep`
  - observed provisional verdict:
    - `filter`
  - mismatches at:
    - restart `16`
    - restart `32`
    - restart `48`
    - restart `64`

So the branch closed for a specific reason:

- the raw provisional checkpoint surface never reproduced the trusted split
- this is not just a timing failure
- it is a ranking-surface failure

## Key technical read

The kept-lane failure is explicit on `7003`.

At every provisional checkpoint:

- `phaseA_rank1_init_match = 0.243`
- provisional verdict:
  - `filter`

But the same provisional snapshots already carry a stronger challenger:

- `phaseA_best_init_match = 0.490`
- `phaseA_best_final_match = 0.490`

And the trusted late snapshot resolves to that stronger challenger:

- final late `phaseA_rank1_init_match = 0.490`
- final verdict:
  - `keep`

So the main lesson is:

- the good `7003` challenger already exists early
- the raw provisional `rank1` ordering is what is wrong

The filtered lane `7002` proves the complementary side:

- provisional `rank1` stays at `0.243`
- provisional best rises only to:
  - `0.329`
- final late `rank1` stays below the gate:
  - `0.289`

## Operational note

The science outputs completed cleanly.

There was one runner-tail housekeeping bug after the outputs were written:

- `refresh_catalog_safely(REPO_ROOT)`

That tail call was fixed to:

- `refresh_catalog_safely()`

The finished microprobe bundle was then repaired to a truthful completed state.

This does not change the scientific read above.

## Decision

- close the raw provisional `rank1` checkpoint branch
- do not widen this exact provisional surface to more runtime canaries
- move to checkpoint refinement instead of more earlier-emission-by-default work

## Next honest move

- compare provisional versus trusted late gate fields directly
- test whether a refined provisional rule can recover:
  - the trusted late family labels on `7001-7005`
  - the earlier provisional split on `7002/7003`
- if no small refined rule works, persist richer provisional ordering fields
  rather than spending another runtime action canary
