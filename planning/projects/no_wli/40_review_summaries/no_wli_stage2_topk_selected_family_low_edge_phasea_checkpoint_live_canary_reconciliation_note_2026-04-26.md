# Stage-2 Selected-Family Phase-A Checkpoint Live-Canary Reconciliation Note

Date: 2026-04-26

## Verdict

- live-canary prep status:
  - closed as evidence-clean for the narrow two-canary read
- checkpoint contract:
  - passed semantically on filtered `7002`
  - passed semantically on kept `7003`
- provenance:
  - clean for both canaries
- timing:
  - favorable on filtered `7002`
  - unfavorable on kept `7003`
- live runtime:
  - still blocked generally
- production/general policy:
  - not claimed
- next work:
  - do not launch more canaries automatically
  - if continuing, open a separate timing-risk follow-up rather than widening
    this checkpoint branch

## Evidence Bundles

Filtered canary:

- source:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T004304Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
- provenance audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T012105Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1/`

Kept canary:

- source:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T014422Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
- provenance audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T021629Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1/`

Partial non-evidence bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T014114Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
- status:
  - `interrupted_before_wrapper_relaunch`
- decision:
  - not used as evidence

## Layer Reconciliation

Both audited canaries have:

- source status:
  - `completed`
- bundle complete:
  - `1`
- row mismatch count:
  - `0`
- recommendation values present:
  - `1`
- recommendation values match:
  - `1`
- state recommendation:
  - `advance`
- final event recommendation:
  - `advance`
- summary-derived recommendation:
  - `advance`
- recommendation JSON:
  - `advance`
- readout recommendation:
  - `advance`

So there is no live-canary provenance split like the earlier family-microbatch
handoff issue.

## Filtered 7002 Read

- lane role:
  - `filtered_family`
- observed / expected verdict:
  - `filter / filter`
- checkpoint restart:
  - `32`
- `phaseA_best_init_match`:
  - `0.329`
- threshold:
  - `0.3865`
- action applied:
  - `1`
- fallback target:
  - `retained_baseline`
- baseline / current match:
  - `0.754 / 0.754`
- selected/reference resume match:
  - `0.310`
- retained exact replay elapsed:
  - `00:22:13`
- live canary elapsed:
  - `00:13:33`
- saved attempt seconds / share:
  - `519.954 / 0.390`

Interpretation:

- the filtered canary supports the intended operational mechanism:
  - collapse-like selected-family lane
  - restart32 filter
  - baseline fallback
  - material runtime saving
  - no score harm versus retained baseline

## Kept 7003 Read

- lane role:
  - `kept_family`
- observed / expected verdict:
  - `keep / keep`
- checkpoint restart:
  - `32`
- `phaseA_best_init_match`:
  - `0.490`
- threshold:
  - `0.3865`
- action applied:
  - `0`
- baseline / current match:
  - `0.408 / 0.476`
- selected/reference resume match:
  - `0.476`
- retained exact replay elapsed:
  - `00:21:54`
- live canary elapsed:
  - `00:30:51`
- elapsed delta / ratio:
  - `+537.015s / about 1.409x`

Interpretation:

- the kept canary supports the semantic checkpoint contract:
  - viable selected-family lane
  - restart32 keep
  - no action
  - selected path preserved
  - no score harm versus retained exact replay
- the kept canary does not support a clean runtime-efficiency claim:
  - it is materially slower than the retained exact replay reference
  - the slowdown occurs under a no-action keep lane, so it does not read as a
    fallback/early-stop correctness failure
  - it remains an operational timing risk

## Correct Reading

The correct reading is not:

- the checkpoint failed
- live runtime is generally reopened
- the threshold is a production policy
- the selector generally helps

The correct reading is:

- the reviewed restart32 `phaseA_best_init_match >= 0.3865` contract is now
  observed live on both sides of the split
- filtered `7002` demonstrates the intended fallback-plus-early-stop benefit
- kept `7003` demonstrates no-action path preservation
- both live bundles are provenance-clean
- kept-lane timing is still not clean enough to make a broad runtime claim

## Branch Decision

Close this live-canary branch as:

- semantically passed
- provenance passed
- timing caveat carried

Do not widen in this branch.

Do not reopen live runtime generally.

If more work is needed, make it a separate timing-risk follow-up with its own
budget and stop condition, focused on why kept/no-action lanes can inflate
wallclock even when the checkpoint decision is correct.
