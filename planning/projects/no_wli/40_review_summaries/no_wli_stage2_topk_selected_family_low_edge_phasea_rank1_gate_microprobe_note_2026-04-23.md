# Stage-2 Topk Selected-Family Low-Edge Phase-A Rank-1 Gate Microprobe Note

Date: 2026-04-23

Status:

- completed
- branch-point microprobe

## Scope

This note records the first operational microprobe for the concrete Phase-A
gate:

- gate:
  - `phasea_rank1_init_match >= 0.30`
- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

Study bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T023226Z__stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1/`

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1.py`

## Main result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_phasea_rank1_gate_persistence_microprobe`

Reason:

- the gate keeps the family counterfactual positive
- and it would have avoided almost all filtered-lane wallclock on the known
  bad lanes

## Cross-checked evidence

Summary payload:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T023226Z__stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1/stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_summary.json`

Key fields:

- `recommendation.recommendation = "advance"`
- `recommendation.next_branch_label = "stage2_topk_selected_family_low_edge_phasea_rank1_gate_persistence_microprobe"`
- `summary_row.counterfactual_family_mean_delta_vs_baseline = 0.0212`
- `summary_row.counterfactual_family_mean_delta_vs_retained_stage3_reference = 0.0296`
- `summary_row.counterfactual_family_worst_delta_vs_baseline = -0.003`
- `summary_row.filtered_estimated_saved_attempt_minutes_total = 42.31`
- `summary_row.filtered_estimated_saved_attempt_share = 0.9607`
- `summary_row.mean_phasea_gate_proxy_elapsed_seconds = 52.76`

Per-seed counterfactual table:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T023226Z__stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1/stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_rows.csv`

Key rows:

- `7001`
  - mode:
    - `baseline_fallback_after_phasea`
  - counterfactual delta vs baseline:
    - `0.000`
  - counterfactual delta vs retained:
    - `+0.008`
  - saved attempt seconds:
    - `1256.5`
- `7002`
  - mode:
    - `baseline_fallback_after_phasea`
  - counterfactual delta vs baseline:
    - `0.000`
  - counterfactual delta vs retained:
    - `+0.002`
  - saved attempt seconds:
    - `1282.0`
- `7003`
  - mode:
    - `candidate_replay_kept`
  - counterfactual delta vs baseline:
    - `+0.068`
- `7004`
  - mode:
    - `candidate_replay_kept`
  - counterfactual delta vs baseline:
    - `-0.003`
- `7005`
  - mode:
    - `candidate_replay_kept`
  - counterfactual delta vs baseline:
    - `+0.041`

## Interpretation

This changes the branch again.

What is now true:

- the gate is not only a descriptive split
- it is also an operationally meaningful stop / fallback candidate
- on the known bad lanes it would have cut about:
  - `42.3` minutes of exact-replay wallclock
  - while preserving a positive family counterfactual

So the next honest step is not another replay family.

It is a persistence / actionability microprobe:

- make the gate inspectable during real runs
- and decide how it should act:
  - fallback
  - early stop
  - or both
