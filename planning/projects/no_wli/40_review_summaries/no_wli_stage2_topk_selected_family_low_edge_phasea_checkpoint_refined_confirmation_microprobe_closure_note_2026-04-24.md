# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Refined Confirmation Microprobe Closure Note

Date: 2026-04-24

## Outcome

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1/`
- result:
  - `hold`
- next branch:
  - `stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_field_persistence`

## Question

Did the refined provisional rule `rank1>=0.30 or best>=0.44` survive a second
filtered / kept pair in the same exact-replay family early enough to justify
reopening an action contract?

## Read

- filtered `7001` confirmed cleanly:
  - provisional verdict:
    - `filter`
  - shared checkpoints:
    - `16 / 32 / 48 / 64`
  - provisional `best_init`:
    - `0.378`
- kept `7005` failed cleanly:
  - provisional verdict at checkpoints `16 / 32 / 48 / 64`:
    - `filter`
  - expected:
    - `keep`
  - provisional `best_init`:
    - `0.395`
  - it never crossed the refined rescue threshold:
    - `0.44`
- total microprobe elapsed:
  - `00:45:35`
- budget:
  - held under the written `01:00:00`

## What We Learned

- the refined composite rule was not just slightly weak:
  - it failed on every checkpoint for the moderate kept lane `7005`
- the saved provisional surface looks more stable than the rule:
  - `phaseA_rank1_init_match` stayed fixed at `0.243`
  - `phaseA_best_init_match` stayed fixed per lane across checkpoints
- so the next question is not another action canary
- it is whether the useful signal is really:
  - a persistent `phaseA_best_init_match` band
  - rather than the current composite threshold

## Decision

- close the refined confirmation microprobe as:
  - `hold`
- do not reopen the refined both-action contract
- move to a short field-persistence audit on the provisional checkpoint bundle
  surface, filling the missing `7004` provisional lane if needed
