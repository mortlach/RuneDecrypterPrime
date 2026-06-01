# Locked Experiment Specs: Studies 1, 3, and 2

This document records the current no-code experimental baseline after the
review lock and the first two live implementation studies.

It is intended to prevent drift in how the studies are described and judged.

## 1. Locked Baseline

Current working diagnosis:

- main problem class:
  - Stage-3 family handling
- not mainly:
  - broad engineering collapse
  - late Stage-3.5 absence

Locked seed split:

- `211`-like:
  - mainly upstream reach / `good_family_absent`
- `411`-like:
  - mainly downstream exploitation / `good_family_undervalued`

Locked study order:

1. Study 1: constant local-depth Stage-3 entry
2. Study 3: Phase-C start balancing
3. Study 2: family-aware Phase-B preservation

Current status of that order:

- Study 1:
  - implemented
  - tested
  - live readout complete
  - valid negative
- Study 3:
  - implemented
  - tested
  - live readout complete
  - valid negative
- Study 2:
  - next live implementation target

## 2. Study 1 Spec: Constant Local-Depth Stage-3 Entry

### Hypothesis

If weak `211` runs are mainly failing because widened Stage-2 preservation is
being squeezed back down into too little Stage-3 local depth per promoted
family, then keeping local Stage-3 depth roughly constant as promoted-family
count rises should improve solve quality or downstream family diversity.

### Intervention Boundary

Allowed change:

- Stage-3 entry allocation only

Explicitly unchanged:

- Stage-3 inner scoring
- Phase-B ranking
- Phase-C start policy
- rescue logic
- Stage-3.5

### Control and Candidate

Control preset:

- `stage3_preserve_tieband_probe_p9`

Candidate preset:

- `stage3_entry_const_local_depth_p9`

### Execution Evidence

Control run:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T013131043374Z__bench_solve_pipeline_no_wli__55b7159`

Candidate run:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T050751414997Z__bench_solve_pipeline_no_wli__55b7159`

Proof that the policy executed:

- control `stage3_prep.json`:
  - `stage3_entry_allocation_policy = "legacy_fixed_budget"`
  - `stage3_entry_target_before_cap = 64`
- candidate `stage3_prep.json`:
  - `stage3_entry_allocation_policy = "constant_local_depth"`
  - `stage3_entry_target_before_cap = 288`

Proof that realized Stage-3 entry widened:

- control manifest:
  - `stage3_init3_count = 64`
- candidate manifest:
  - `stage3_init3_count = 144`

### Primary Readouts

- `best_match_ratio`
- `stage3_match_ratio`
- `phaseB_selected_unique_end_hash`
- `phaseC_candidate_pool_unique_end_hash`
- `phaseC_start_keys_used`
- `phaseC_start_source_counts`

### Result

Observed:

- `best_match_ratio` unchanged:
  - `0.574 -> 0.574`
- `stage3_match_ratio` unchanged:
  - `0.574 -> 0.574`
- downstream family counters unchanged

### Locked Conclusion

Study 1 is a valid negative on `seed211`.

What it falsifies:

- simple Stage-3 entry-budget starvation as the main limiter for this seed

What it does not falsify:

- hidden entry compression as a real mechanism in general
- upstream basin-generation failure on `211`

## 3. Study 3 Spec: Phase-C Start Balancing

### Hypothesis

If weak `411` runs already carry useful late-stage variety into the Phase-C
candidate pool but fail to exploit enough of it, then balancing Phase-C starts
across surviving sources should improve exploited variety and possibly improve
solve quality.

### Intervention Boundary

Allowed change:

- Phase-C `start_records` selection policy only

Explicitly unchanged:

- Phase-C candidate-pool composition
- Phase-B ranking and tie-band
- rescue logic
- Stage-3 entry policy
- Stage-3.5

### Control and Candidate

Control preset:

- `stage3_preserve_tieband_probe_p9`

Candidate preset:

- `stage3_phasec_start_balanced_p9`

### Execution Evidence

Control run:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T174120032623Z__bench_solve_pipeline_no_wli__55b7159`

Candidate run:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T211041031812Z__bench_solve_pipeline_no_wli__55b7159`

Isolation proof:

- `run_config.json` diff shows only intended semantic change:
  - `stage3.two_phase.phase_c.start_policy`
    - `source_order`
    - `balanced_sources_v1`

### Primary Readouts

- `phaseC_candidate_pool_source_counts`
- `phaseC_start_source_counts`
- `phaseC_start_keys_used`
- `phaseC_start_unique_end_hash`
- `best_match_ratio`
- `stage3_match_ratio`

### Result

Observed:

- candidate pool unchanged
- actual starts unchanged
- solve unchanged
- same six `candidate_hash` values in both `phasec_start_checkpoints.jsonl`

### Locked Conclusion

Study 3 is a valid negative on `seed411`.

What it falsifies:

- Phase-C start ordering alone as the main marginal lever on this seed under
  the current Phase-B output

What it supports:

- the bottleneck is earlier in downstream preservation
- by Phase-C start time there is no additional distinct `phaseB_topk`
  startable key to exploit

## 4. Study 2 Spec: Family-Aware Phase-B Preservation

### Hypothesis

If `411`-like runs are mainly losing useful families before Phase-C starts are
chosen, then reserving some downstream slots by family view before final global
fill should preserve more distinct startable families into Phase-C and may
improve solve quality.

### Intervention Boundary

Allowed change:

- Phase-B downstream preservation only

Explicitly unchanged:

- Phase-B scoring order
- Phase-B tie-band widening
- Phase-C rescue logic
- Stage-3 entry
- Stage-3.5

### Fixed Family-View Rule

Do not invent a new family view ad hoc.

Choose from:

- `prefix_hamming_le_24`
- `near_tail_h1`

Reference:

- `tools/benchmarks/periodic_sub_trans/no_wli/audit_basin_family_diversity_alignment.py`

### Recommended v1 Policy

Candidate behavior:

1. preserve the global top row exactly as today
2. reserve a small number of additional downstream slots from distinct families
3. fill remaining slots by the existing global order

Recommended first reservation count:

- `2`

### Required New Telemetry

- `phaseB_family_preservation_policy`
- `phaseB_family_view_id`
- `phaseB_family_reserved_slots`
- `phaseB_family_count_in_top_band`
- `phaseB_family_preserved_count`

### Required Readouts

- `phaseB_selected_unique_end_hash`
- `phaseC_candidate_pool_unique_end_hash`
- `phaseC_start_unique_end_hash`
- `phaseC_candidate_pool_source_counts`
- `phaseC_start_source_counts`
- `best_match_ratio`
- `stage3_match_ratio`

### Success Criteria

Valid positive:

- distinct families are provably preserved
- downstream diversity rises
- solve improves

Valid negative:

- distinct families are provably preserved
- downstream diversity rises
- solve still does not improve

Invalid result:

- Phase-B scoring order changes
- tie-band logic changes
- rescue changes
- family-view choice is not explicit in config / lock / telemetry

### First Long Compare After Implementation

Seed:

- `411`

Control:

- `stage3_preserve_tieband_probe_p9`

Candidate:

- one new Study 2 preset that differs only by:
  - family-preservation policy
  - fixed family-view id
  - fixed reserved-slot count

## 5. Bottom Line

This locked experimental baseline should now be treated as:

- Study 1:
  - recorded valid negative
- Study 3:
  - recorded valid negative
- Study 2:
  - next live implementation target

No further long runs should be scheduled on the current code until a Study 2
implementation and short proof slice exist.
