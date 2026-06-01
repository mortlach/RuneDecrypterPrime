# Stage-2 Selected-Family Phase-A Checkpoint Kept-Lane Timing-Risk Audit Note

Date: 2026-04-26

Status:

- existing-log timing audit complete
- one timing-risk probe approved
- live runtime still blocked generally

Audit output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T073234Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_audit_v1/`

## Finding

The kept/no-action `7003` timing caveat is localized to the live kept runtime
surface, not the semantic checkpoint contract.

Comparison:

- retained exact replay `7003`: `1314.422s`
- family action replay `7003`: `1323.015s`, ratio `1.007`
- live kept/no-action `7003`: `1851.437s`, ratio `1.409`
- live delta versus retained exact replay: `537.0s`

The slowdown is already visible by checkpoint `32`:

- family checkpoint32 elapsed: `550.5s`
- live checkpoint32 elapsed: `775.6s`
- live/family checkpoint32 ratio: `1.409`
- family/live verdicts: `keep` / `keep`

It remains visible in Phase B:

- retained Phase B step2112 local seconds: `150.1`
- family Phase B step2112 local seconds: `149.6`
- live Phase B step2112 local seconds: `202.3`
- live/reference Phase B step2112 ratio: `1.347`

## Interpretation

The checkpoint contract is not implicated semantically:

- the verdict remained `keep`
- no action was applied
- selected path preservation held
- provenance audit passed

The risk is operational timing reproducibility on the live kept/no-action path.
This does not reopen live runtime generally and does not justify a matrix.

## Probe Approval

One timing-risk probe is approved:

- fixture: fixed `1111`
- search seed: `7003`
- lane role: `kept_family`
- expected verdict: `keep`
- action contract: no action
- restart count: `32`
- field: `phaseA_best_init_match`
- threshold: `0.3865`
- run label: `stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1`

Budget:

- expected wallclock anchor: `1851.437s` from the prior live kept canary
- intended normal completion: under `1h`
- hard cap: `8h`
- stop condition: exactly one run; stop and hold if the cap is reached without
  usable checkpoint evidence or if the bundle is not auditable

Decision rule:

- advance timing analysis only if the probe completes or cleanly reaches the
  checkpoint surface, all artefact layers agree, row recomputation has zero
  mismatches, and elapsed timing can be compared against retained exact replay,
  family-action replay, and the prior live kept canary
- otherwise hold

No threshold tuning, selector development, matrix launch, or broad live-runtime
reopening is approved by this note.
