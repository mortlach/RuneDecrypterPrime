# Stage-2 Topk Selected-Family Low-Edge Phase-A Rank-1 Gate Microprobe Plan

Date: 2026-04-23

Status:

- completed
- advance
- persistence-branch decision ready

## Why this note exists

The Phase-A competitiveness audit already found one concrete gate:

- `phasea_rank1_init_match >= 0.30`

That was enough to explain the split.

It was not yet enough to say whether the gate mattered operationally.

The next honest short step was therefore:

- keep the same fixed exact family
- keep the same gate
- ask whether this gate would have made the branch both:
  - safer
  - and materially cheaper

## Main question

If we condition the concrete selector on `phasea_rank1_init_match >= 0.30` and
fall back immediately on filtered lanes, does the fixed `1111` exact-family
read become both safer and cheaper?

## Mechanism layer

- selection

## Pre-run block

Question:

- is the concrete Phase-A rank-1 gate only explanatory, or would it actually
  save enough bad-run spend to justify making it inspectable during real runs?

Suspicion:

- the gate will keep the three non-catastrophic lanes
- filter the two collapse lanes
- turn the family counterfactual positive
- and avoid most of the filtered lanes' wallclock

Main alternative:

- the gate may look clean on outcome but save too little runtime to justify the
  extra implementation work

If suspicion is true, expect:

- counterfactual family mean delta vs baseline to stay positive
- counterfactual worst delta vs baseline to stay near neutral
- filtered lanes to lose most of their paid runtime after the Phase-A proxy

If alternative is true, expect:

- the counterfactual family to stay flat or worse
- or the filtered lanes to save too little time to matter

Tomorrow's decision rule:

- advance only if the gate:
  - keeps the family counterfactual positive
  - avoids catastrophic loss on the kept set
  - and saves a large majority of filtered-lane wallclock
- refine otherwise

## Why this is the right science-method step now

This is the method correction after finding the gate:

- do not jump straight from offline split to live runtime
- first prove the gate would actually avoid waste on the known bad lanes
- only then spend time on making it inspectable during real runs

## Frozen inputs

Use exactly:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/`

## Implementation

Single-script operational microprobe:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1.py`

Focused proof:

- `tests/tools/test_no_wli_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1.py`

## Required outputs

This microprobe must emit:

- one machine-readable per-seed counterfactual table
- one machine-readable family summary
- one short markdown readout
- one explicit advance / refine / close recommendation

Completed output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T023226Z__stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1/`

## Result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_phasea_rank1_gate_persistence_microprobe`

Main read:

- gate:
  - `rank1_init_ge_0p30`
- kept seeds:
  - `7003,7004,7005`
- filtered seeds:
  - `7001,7002`
- counterfactual family mean delta vs baseline:
  - `+0.021`
- counterfactual family mean delta vs retained:
  - `+0.030`
- total filtered saved attempt minutes:
  - `42.3`
- filtered saved attempt share:
  - `0.961`
- mean Phase-A gate proxy elapsed:
  - `52.8s`

Interpretation:

- the gate is not just explanatory
- on the known bad lanes it would have prevented most of the wasted exact
  replay spend
- the next honest step is now to make that gate inspectable and actionable
  during real runs
