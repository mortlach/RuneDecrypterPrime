# Stage-2 Selected-Family Phase-A Checkpoint Kept-Lane Timing-Risk Probe Review Note

Date: 2026-04-26

Status:

- throughput-caveat probe complete
- semantic checkpoint outcome passed
- provenance audit passed
- valid long-run evidence saved
- kept-lane throughput caveat confirmed
- no further runtime approved from this branch

Source bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T073609Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1/`

Provenance audit:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T084800Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_provenance_audit_v1/`

Runtime log:

- `planning/working/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_20260426T0735Z.log`

Refreshed runtime references:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T084830Z__no_wli_runtime_history_reference_v1/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T084830Z__fixed_runtime_wallclock_reference_v1/`

## What Ran

One explicitly approved throughput-caveat probe:

- fixture/search: fixed `1111/search7003`
- lane role: `kept_family`
- expected verdict: `keep`
- checkpoint: restart `32`
- field: `phaseA_best_init_match`
- threshold: `0.3865`
- action contract: no action
- hard cap: `8h`

The run completed in `01:07:00` for the child replay and `01:07:01` for the
wrapper, well inside the cap.

## Semantic Result

The semantic checkpoint result passed:

- `phaseA_best_init_match = 0.49`
- threshold `0.3865`
- observed verdict `keep`
- expected verdict `keep`
- action applied `0`
- fallback target empty
- final/current resume best match `0.476`
- reference selected-path match `0.476`
- delta versus selected reference `0.0`
- delta versus baseline `0.068`

This means the selected path was preserved. The checkpoint contract is still
not implicated semantically.

## Provenance Result

The provenance audit passed:

- recommendation `advance`
- state recommendation `advance`
- final event recommendation `advance`
- summary-derived recommendation `advance`
- recommendation JSON `advance`
- readout `advance`
- recommendation values present `1`
- recommendation values match `1`
- row mismatch count `0`
- bundle complete `1`

## Timing Result

The kept-lane throughput caveat reproduced and strengthened.

Elapsed comparison:

- retained exact replay `7003`: `1314.422s`
- family action replay `7003`: `1323.015s`
- prior live kept/no-action `7003`: `1851.437s`
- repeat throughput probe `7003`: `4020.468s`

Ratios:

- repeat versus retained exact replay: `3.059x`
- repeat versus family action replay: `3.039x`
- repeat versus prior live kept/no-action: `2.172x`

Checkpoint32 timing:

- family action replay checkpoint32: `550.467s`
- prior live kept/no-action checkpoint32: `775.621s`
- repeat throughput-probe checkpoint32: `1487.231s`
- repeat versus family checkpoint32: `2.702x`
- repeat versus prior live checkpoint32: `1.917x`

Phase B step2112 timing:

- retained exact replay: `150.148s`
- family action replay: `149.644s`
- prior live kept/no-action: `202.321s`
- repeat throughput probe: `438.584s`
- repeat versus retained exact replay: `2.921x`
- repeat versus family action replay: `2.931x`
- repeat versus prior live kept/no-action: `2.168x`

## Interpretation

The throughput caveat is real enough to carry as a claim boundary:

- the kept/no-action checkpoint decision is semantically correct
- the selected path is preserved
- provenance is clean
- the live kept/no-action wallclock is variable

This does not invalidate the fixed-family replay result or the reviewed
checkpoint contract. It blocks runtime-saving or production-readiness claims
from kept/no-action lanes, but it does not block moving on to separate science
experiments.

## Decision

Close this follow-up as:

- semantic/provenance pass
- valid long-run evidence saved
- kept-lane throughput caveat confirmed
- live runtime still blocked generally
- production/general policy not claimed
- no matrix approved
- no more throughput repeats approved from this branch

Recommended next work can move back to science experiments. Only open a
separate runtime-instrumentation investigation if a future claim depends on
precise live wallclock.
