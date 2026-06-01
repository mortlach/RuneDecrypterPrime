# Stage-2 Topk Selected-Family Low-Edge Phase-A Competitiveness Audit Note

Date: 2026-04-23

Status:

- completed
- branch-point audit

## Scope

This note records the first cheap explanatory audit after the mixed exact
replay family result for the narrowed upstream selector:

- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

Study bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/`

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1.py`

Scope:

- fixed `1111/search7001-7005`
- uses the completed exact replay family as frozen input

## Main result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe`

Best gate:

- `rank1_init_ge_0p30`

Reason:

- an early Phase-A competitiveness gate cleanly filters both hard collapse
  lanes while keeping all three non-catastrophic lanes
- the resulting counterfactual family mean delta versus baseline turns
  positive

## Cross-checked evidence

Summary payload:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/stage2_topk_selected_family_low_edge_phasea_competitiveness_summary.json`

Recommendation fields:

- `recommendation = "advance"`
- `best_gate_id = "rank1_init_ge_0p30"`
- `best_metric_name = "phasea_rank1_init_match"`
- `best_threshold = 0.3`
- `next_branch_label = "stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe"`

Per-seed case rows:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/stage2_topk_selected_family_low_edge_phasea_competitiveness_case_rows.csv`

Key rows:

- `7001`
  - case:
    - `local_search_collapse_after_phasea`
  - `phasea_rank1_init_match = 0.254`
  - `phasea_best_to_stage3_conversion_delta = -0.227`
- `7002`
  - case:
    - `phasea_competitiveness_below_floor`
  - `phasea_rank1_init_match = 0.289`
  - `phasea_best_to_stage3_conversion_delta = +0.001`
- `7003`
  - case:
    - `clean_exact_positive`
  - `phasea_rank1_init_match = 0.490`
- `7004`
  - case:
    - `competitive_near_floor`
  - `phasea_rank1_init_match = 0.415`
- `7005`
  - case:
    - `baseline_positive_near_retained`
  - `phasea_rank1_init_match = 0.395`

Threshold summary:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/stage2_topk_selected_family_low_edge_phasea_competitiveness_threshold_summary_rows.csv`

Best threshold row:

- `rank1_init_ge_0p30`
  - kept seeds:
    - `7003,7004,7005`
  - filtered seeds:
    - `7001,7002`
  - kept mean delta versus baseline:
    - `+0.035`
  - filtered mean delta versus baseline:
    - `-0.356`
  - counterfactual family mean delta versus baseline:
    - `+0.021`
  - counterfactual family mean delta versus retained:
    - `+0.028`
  - `filters_all_hard_collapses = 1`
  - `keeps_all_noncatastrophic = 1`

## Interpretation

What is now true:

- the mixed selector family result is already partly explainable from an early
  Phase-A signal
- the two collapse lanes are not the same failure mode:
  - `7001` is weak at Phase A and then collapses further in local search
  - `7002` is already below a usable competitiveness floor
- `phasea_rank1_init_match >= 0.30` is the simplest current gate that:
  - removes both collapse lanes
  - keeps all three non-catastrophic lanes
  - turns the family counterfactual positive

So the next honest step is no longer a generic "postmortem".

It is a concrete conditioned-gate microprobe on the Phase-A rank-1 signal.
