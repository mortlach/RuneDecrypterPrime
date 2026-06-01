# Stage-2 to Stage-3 Promoted Family Audit Note

Date: 2026-04-22

Status:

- completed
- branch-point audit

## Scope

This note records the first offline upstream family audit after the closed
entry-allocation line.

Study bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/`

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_stage3_promoted_family_audit_v1.py`

Primary family view:

- `prefix_hamming_le_24`

Cases:

- fixed `611/search7001-7005`
- fixed `1111/search7001-7005`
- fixed `1511/search7001-7005`

## Main result

Recommendation:

- `advance`

Next branch:

- `stage2_stage3_within_family_representative_selection_microprobe`

Reason:

- `1111` shows a persistent upstream within-family representative gap at both
  `stage2_topk` and `stage2_promoted`
- the same metric stays near zero on `611` and `1511`
- `1111` cross-family gap is much smaller than its within-family gap

## Cross-checked evidence

Fixture summary table:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/stage2_stage3_promoted_family_audit_fixture_summary_rows.csv`

Key rows:

- `1111`
  - `mean_stage2_topk_within_family_gap = 0.070`
  - `mean_stage2_promoted_within_family_gap = 0.070`
  - `mean_stage2_promoted_between_family_gap = 0.014`
  - `dominant_upstream_pattern = persistent_within_family_representative_gap`
- `611`
  - `mean_stage2_promoted_within_family_gap = 0.000`
- `1511`
  - `mean_stage2_promoted_within_family_gap = 0.000`

Recommendation payload:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/stage2_stage3_promoted_family_audit_recommendation.json`
- fields:
  - `recommendation = "advance"`
  - `next_branch_label = "stage2_stage3_within_family_representative_selection_microprobe"`
  - `mechanism_layer = "selection"`

Human readout:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/stage2_stage3_promoted_family_audit_readout.md`

## Interpretation

This changes the branch reading.

The current `1111` upstream problem does not mainly look like:

- missing promoted-family diversity
- or another entry-allocation bottleneck

It currently looks more like:

- a better upstream family already exists
- but the score-selected row is a weak representative inside that family
- and that distortion survives through `stage2_promoted` before Stage 3 starts

So the next honest microprobe should target upstream representative selection
inside the promoted family surface rather than another broad diversity or late
allocation run.
