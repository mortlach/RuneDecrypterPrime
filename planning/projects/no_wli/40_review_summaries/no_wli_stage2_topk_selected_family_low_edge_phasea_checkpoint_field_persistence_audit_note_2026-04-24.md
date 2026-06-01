# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Field-Persistence Audit Note

Date: 2026-04-24

## Outcome

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210520Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1/`
- result:
  - `hold`

## Question

Across the retained fixed `1111/search7001-7005` family, does
`phaseA_best_init_match` persist cleanly enough from restart `16` onward that
the next provisional rule should be a direct best-init threshold rather than
the composite `rank1 or best` rule?

## Read

- the missing provisional lane was completed first:
  - `7004`
  - stable provisional `best_init`:
    - `0.415`
- the strict full-window persistence test failed for one concrete reason:
  - filtered `7002` moved between:
    - restart `16`
      - `0.289`
    - restart `32`
      - `0.329`
- after that move, the family still looked promising:
  - filtered max:
    - `0.378`
  - kept min:
    - `0.395`
  - raw gap:
    - `0.017`
- but under the original strict criterion:
  - `phaseA_best_init_match`
  - was not yet persistent across every lane from restart `16`

## What We Learned

- this was not an extractor bug
- it was a sharper science result:
  - the family does not stabilize early enough at restart `16`
- so the next honest question is:
  - what is the earliest stabilization window?
- not:
  - whether a best-init field exists at all

## Decision

- close the strict field-persistence audit as:
  - `hold`
- immediately refine to a stabilization-window audit rather than reopening any
  action contract
