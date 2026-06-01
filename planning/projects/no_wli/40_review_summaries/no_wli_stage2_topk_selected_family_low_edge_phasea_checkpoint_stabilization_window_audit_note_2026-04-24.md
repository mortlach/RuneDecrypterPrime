# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Stabilization-Window Audit Note

Date: 2026-04-24

## Outcome

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210839Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1/`
- result:
  - `advance`
- next branch:
  - `stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_canary`

## Question

If full checkpoint persistence from restart `16` is too strict because filtered
`7002` is still moving, what is the earliest checkpoint window where the
retained `1111` family becomes stable enough to support a clean best-init
threshold?

## Read

- selected field:
  - `phaseA_best_init_match`
- earliest stable separating window:
  - restart `32`
- filtered max:
  - `0.378`
- kept min:
  - `0.395`
- threshold midpoint:
  - `0.3865`
- mean elapsed share at restart `32`:
  - `0.426`
- mean share improvement versus the late gate:
  - `0.455`

Per-family values from restart `32` onward:

- filtered:
  - `7001`
    - `0.378`
  - `7002`
    - `0.329`
- kept:
  - `7003`
    - `0.490`
  - `7004`
    - `0.415`
  - `7005`
    - `0.395`

## What We Learned

- the full-family provisional branch is now concrete
- `rank1` remains useless
- `best_init` is the right scalar
- restart `16` is too early
- restart `32` is early enough and still materially earlier than the late gate

## Decision

- advance to one real restart-32 best-init action canary on the hard pair:
  - filtered `7001`
  - kept `7005`
