# Stage-2 Topk Family Representative Policy Audit Note

Date: 2026-04-22

Status:

- completed
- branch-narrowing audit

## Scope

This note records the first concrete within-family representative selector
audit after the upstream promoted-family diagnosis.

Study bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/`

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_family_representative_policy_audit_v1.py`

Family view:

- `prefix_hamming_le_24`

Policy:

- `selected_family_low_edge_eps_0p020_v1`

Cases:

- fixed `611/search7001-7005`
- fixed `1111/search7001-7005`
- fixed `1411/search7001-7005`
- fixed `1511/search7001-7005`

## Main result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_microprobe`

Reason:

- the low-edge selector stays inert on `611`, `1411`, and `1511`
- it switches all five `1111` lanes to the hidden stronger same-family row
- on `1111`, candidate and within-family oracle match on all five retained
  lanes

## Cross-checked evidence

Fixture summary table:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/stage2_topk_family_representative_policy_fixture_summary_rows.csv`

Key rows:

- `1111`
  - `candidate_active_run_count = 5`
  - `candidate_oracle_match_run_count = 5`
  - `mean_candidate_truth_delta_vs_baseline = 0.070`
  - `mean_candidate_score_delta_vs_baseline = -0.015156121010536872`
  - `mean_candidate_family_rank = 5.0`
- `611`
  - `candidate_active_run_count = 0`
  - `mean_candidate_truth_delta_vs_baseline = 0.0`
- `1411`
  - `candidate_active_run_count = 0`
  - `mean_candidate_truth_delta_vs_baseline = 0.0`
- `1511`
  - `candidate_active_run_count = 0`
  - `mean_candidate_truth_delta_vs_baseline = 0.0`

Recommendation payload:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/stage2_topk_family_representative_policy_recommendation.json`
- fields:
  - `recommendation = "advance"`
  - `next_branch_label = "stage2_topk_selected_family_low_edge_microprobe"`
  - `mechanism_layer = "selection"`
  - `candidate_policy_id = "selected_family_low_edge_eps_0p020_v1"`

Human readout:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/stage2_topk_family_representative_policy_audit_readout.md`

## Interpretation

This was the first clean conversion from diagnosis to candidate policy.

The current upstream `1111` issue now reads as:

- one already-present family region
- wrong representative chosen inside it
- one simple band-edge selector can recover the stronger row

The remaining question is not whether the selector exists.

The remaining question is:

- whether the selector is narrow and robust enough to specify one honest
  microprobe
