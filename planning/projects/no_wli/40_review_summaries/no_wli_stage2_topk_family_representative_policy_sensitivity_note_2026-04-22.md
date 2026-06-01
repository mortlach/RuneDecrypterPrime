# Stage-2 Topk Family Representative Policy Sensitivity Note

Date: 2026-04-22

Status:

- completed
- branch-finalizing sweep

## Scope

This note records the family-view and score-band sweep that narrowed the
representative-selection branch to one concrete selector.

Study bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/`

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_family_representative_policy_sensitivity_v1.py`

Cases:

- fixed `611/search7001-7005`
- fixed `1111/search7001-7005`
- fixed `1411/search7001-7005`
- fixed `1511/search7001-7005`

## Main result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_eps_0p016_microprobe`

Chosen policy:

- `selected_family_low_edge_eps_0p016_v1`

Reason:

- only `prefix_hamming_le_24` produces a clean `1111`-only activation window
- the useful band begins at `eps = 0.016`
- `eps = 0.015` is harmful on `1111`
- wider `eps = 0.025` attenuates the gain sharply

## Cross-checked evidence

Setting summary table:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/stage2_topk_family_representative_policy_sensitivity_setting_summary_rows.csv`

Key `1111` rows under `prefix_hamming_le_24`:

- `eps = 0.010`
  - `candidate_active_run_count = 0`
  - `mean_candidate_truth_delta_vs_baseline = 0.000`
- `eps = 0.015`
  - `candidate_active_run_count = 5`
  - `mean_candidate_truth_delta_vs_baseline = -0.023`
  - `candidate_any_negative_truth_delta = 1`
- `eps = 0.016`
  - `candidate_active_run_count = 5`
  - `mean_candidate_truth_delta_vs_baseline = 0.070`
  - `candidate_any_negative_truth_delta = 0`
- `eps = 0.020`
  - `candidate_active_run_count = 5`
  - `mean_candidate_truth_delta_vs_baseline = 0.070`
  - `candidate_any_negative_truth_delta = 0`
- `eps = 0.025`
  - `candidate_active_run_count = 5`
  - `mean_candidate_truth_delta_vs_baseline = 0.005`
  - `candidate_any_negative_truth_delta = 0`

Cross-view read:

- `exact_key`
  - inert across all swept bands
- `exact_tail`
  - inert across all swept bands
- `near_tail_h1`
  - inert across all swept bands
- `prefix_hamming_le_24`
  - only view with a clean selective activation window

Recommendation payload:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/stage2_topk_family_representative_policy_sensitivity_recommendation.json`
- fields:
  - `recommendation = "advance"`
  - `next_branch_label = "stage2_topk_selected_family_low_edge_eps_0p016_microprobe"`
  - `candidate_policy_id = "selected_family_low_edge_eps_0p016_v1"`
  - `family_view_id = "prefix_hamming_le_24"`
  - `score_band_eps = 0.016`

Human readout:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/stage2_topk_family_representative_policy_sensitivity_readout.md`

## Interpretation

The branch is now much sharper.

The next representative-selection step should not be described generically as:

- "some within-family selector"

It should be described concretely as:

- `prefix_hamming_le_24`
- `selected_family_low_edge_eps_0p016_v1`

This is now the smallest honest upstream selector worth carrying into the next
microprobe.
