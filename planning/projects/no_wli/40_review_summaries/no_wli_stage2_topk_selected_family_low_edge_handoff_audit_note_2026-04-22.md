# Stage-2 Topk Selected-Family Low-Edge Handoff Audit Note

Date: 2026-04-22

Status:

- completed
- final cheap gate before execution testing

## Scope

This note records the saved handoff audit for the narrowed selector:

- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

Study bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T031321Z__stage2_topk_selected_family_low_edge_handoff_audit_v1/`

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_handoff_audit_v1.py`

## Main result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_eps_0p016_microprobe`

Reason:

- the concrete selector changes `best2_key` and the saved Stage-3 handoff on
  all five retained `1111` lanes
- it remains completely inert on `611`, `1411`, and `1511`

## Cross-checked evidence

Fixture summary table:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T031321Z__stage2_topk_selected_family_low_edge_handoff_audit_v1/stage2_topk_selected_family_low_edge_handoff_audit_fixture_summary_rows.csv`

Key rows:

- `1111`
  - `candidate_active_run_count = 5`
  - `best2_key_changed_run_count = 5`
  - `init3_changed_run_count = 5`
  - `mean_candidate_truth_delta_vs_baseline = 0.070`
  - `mean_init3_edit_count = 7.8`
  - `mean_stage3_promoted_keys_edit_count = 7.8`
- `611`
  - `best2_key_changed_run_count = 0`
  - `init3_changed_run_count = 0`
- `1411`
  - `best2_key_changed_run_count = 0`
  - `init3_changed_run_count = 0`
- `1511`
  - `best2_key_changed_run_count = 0`
  - `init3_changed_run_count = 0`

Recommendation payload:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T031321Z__stage2_topk_selected_family_low_edge_handoff_audit_v1/stage2_topk_selected_family_low_edge_handoff_audit_recommendation.json`
- fields:
  - `recommendation = "advance"`
  - `next_branch_label = "stage2_topk_selected_family_low_edge_eps_0p016_microprobe"`
  - `candidate_policy_id = "selected_family_low_edge_eps_0p016_v1"`

Human readout:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T031321Z__stage2_topk_selected_family_low_edge_handoff_audit_v1/stage2_topk_selected_family_low_edge_handoff_audit_readout.md`

## Interpretation

The selector has now passed the last cheap non-execution gate.

It is no longer accurate to describe this branch as:

- interesting only at the row-selection level

It is now accurate to say:

- the selector changes the real saved Stage-3 handoff on all five retained
  `1111` lanes
- the selector still stays inert on the controls

So the next honest branch should now be some execution test, not another
offline selector refinement.
