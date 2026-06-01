# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Refinement Audit Note

Date: 2026-04-24

Status:

- completed
- advance

## Why this note exists

The raw provisional earlier-emission microprobe already closed one exact
surface:

- checkpoint `rank1` alone is not enough

That branch failed for a specific reason:

- kept `7003` stayed falsely filtered at every provisional checkpoint
- but the same snapshots already carried a stronger challenger in
  `phaseA_best_init_match`

So the next honest offline question was narrower:

- can a small refined provisional rule recover the trusted fixed `1111`
  keep/filter split materially earlier than the late live-read gate?

## Run

Audit runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1.py`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T192446Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1/`

Focused proof:

- `tests/tools/test_no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1.py`

## Outcome

Machine summary:

- recommendation:
  - `advance`
- selected rule:
  - `rank1_ge_0p30_or_best_ge_0p44`

Trusted-family fit:

- `5 / 5`

Earlier provisional pair fit:

- `7002 / 7003`

Selected checkpoint:

- restart `16`

Timing read:

- mean checkpoint elapsed share:
  - `0.212`
- mean share improvement versus the late live-read gate:
  - `0.674`

## Why this rule won

The audit found a clean separation on the retained evidence:

- filtered `best_init` max:
  - `0.378`
- rescued kept-lane `best_init` min:
  - `0.490`

So a small rescue threshold exists above the filtered ceiling and below the
kept floor. The selected `0.44` threshold is a midpoint-style choice inside
that safe interval rather than a knife-edge fit.

## Decision

- advance from raw provisional closure to refined checkpoint confirmation
- do not reopen checkpoint `rank1` alone
- do not reopen another action canary yet

## Next honest move

- run one second filtered / kept confirmation pair on:
  - `7001`
  - `7005`
- keep the branch runtime-small
- only reopen an action contract if that second pair confirms the refined rule
  materially earlier than the late live-read gate
