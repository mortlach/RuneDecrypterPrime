# Selector Checkpoint Family Provenance Audit Note

Date: 2026-04-25

## Outcome

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T081847Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1/`
- result:
  - `hold`
- next branch:
  - `stage2_topk_selected_family_low_edge_phasea_checkpoint_family_reconciliation_rerun`

## Question

Is the decisive remaining-family restart32 best-init bundle evidence-clean
enough for external review, or does it still contain provenance/reporting
mismatches across rows, state, events, summary, recommendation, and readout?

## Read

- recommendation values match:
  - `0`
- row mismatch count:
  - `1`
- mismatched search seeds:
  - `7002`
- state recommendation:
  - `hold`
- final event recommendation:
  - `hold`
- recommendation json recommendation:
  - `advance`
- readout recommendation:
  - `advance`

Row-level mismatch:

- `7002`
  - lane role:
    - `filtered_family`
  - saved `action_behaved_as_expected`:
    - `0`
  - recomputed shared-role value:
    - `1`
  - observed gate verdict:
    - `filter`
  - expected gate verdict:
    - `filter`
  - action applied:
    - `1`

## What We Learned

- the current blocker is now machine-confirmed inside the repo
- the raw measurement columns and the recomputed shared role-contract logic
  still support the filtered `7002` lane as a success
- the original derived row/control layer remains stale:
  - row flag `0`
  - state/event recommendation `hold`
- the later regenerated summary/readout layer remains `advance`

So the external-review blocker is now explicit and reproducible:

- provenance mismatch confirmed

## Decision

- keep the selector checkpoint science provisionally alive
- keep external review blocked on the current package
- keep live runtime blocked
- next work is still:
  - shared role-contract fix
  - focused regression coverage
  - a clean remaining-family rerun or explicit full reconciliation
