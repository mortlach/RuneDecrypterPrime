# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Best-Init Window Action Microprobe Closure Note

Date: 2026-04-24

## Outcome

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T211444Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1/`
- result:
  - `advance`
- next branch:
  - `stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch`

## Question

If the retained `1111` family stabilizes at restart `32` on
`phaseA_best_init_match >= 0.3865`, does wiring that rule as both fallback and
early stop save real wallclock on filtered `7001` while keeping `7005`
no-harm relative to its prior exact replay?

## Read

- filtered `7001`:
  - observed gate verdict:
    - `filter`
  - action applied:
    - `1`
  - first checkpoint:
    - restart `32`
  - elapsed:
    - `00:09:33`
  - saved attempt seconds:
    - `736.0`
  - saved attempt share:
    - `0.562`
  - landed at retained baseline:
    - `0.428`
- kept `7005`:
  - observed gate verdict:
    - `keep`
  - action applied:
    - `0`
  - first checkpoint:
    - restart `32`
  - elapsed:
    - `00:22:32`
  - delta vs prior exact replay:
    - `0.000`
  - final best match:
    - `0.413`
- mean checkpoint share of prior exact attempts:
  - `0.439`
- total microprobe elapsed:
  - `00:32:09`

## What We Learned

- the simpler restart-32 best-init rule is a real action contract
- it solves both halves of the problem on the hard pair:
  - filtered lane saves real wallclock
  - kept lane stays no-harm
- the branch is now past:
  - live-read correctness
  - raw provisional failure
  - composite refined-rule failure
  - first successful provisional action contract

## Decision

- advance to a wider best-init window family microbatch rather than another
  one-off canary
