# Stage-2 Selected-Family Phase-A Checkpoint Kept-7003 Live-Canary Review Note

Date: 2026-04-25

## Outcome

- source bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T014422Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
- provenance audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T021629Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1/`
- canary recommendation:
  - `advance`
- audit recommendation:
  - `advance`
- row mismatch count:
  - `0`
- decision:
  - kept/no-harm live canary passed semantically and provenance-clean
  - live runtime is still not generally reopened
  - production/general policy is not claimed

## What Ran

- one canary only:
  - fixed `1111/search7003`
- lane role:
  - `kept_family`
- expected verdict:
  - `keep`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`
- family view:
  - `prefix_hamming_le_24`
- checkpoint:
  - restart `32`
- field:
  - `phaseA_best_init_match`
- threshold:
  - `0.3865`
- action:
  - no action
  - continue selected-family attempt
- budget:
  - `08:00:00`
- canary elapsed:
  - `00:30:51`

## Result

- status:
  - `completed`
- completed jobs:
  - `1 / 1`
- checkpoint restart:
  - `32`
- `phaseA_best_init_match`:
  - `0.490`
- threshold:
  - `0.3865`
- observed verdict:
  - `keep`
- expected verdict:
  - `keep`
- action applied:
  - `0`
- `action_stop_now`:
  - `0`
- `action_fallback_to_baseline`:
  - `0`
- fallback target:
  - empty, as expected for keep
- baseline match:
  - `0.408`
- current match:
  - `0.476`
- selected/reference resume match:
  - `0.476`
- delta versus baseline:
  - `0.068`
- delta versus selected/reference:
  - `0.000`
- action behaved as expected:
  - `1`

## Provenance Audit

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
- missing recommendation layers:
  - `none`

## Timing Read

The canary preserved the selected path and passed the checkpoint contract, but
it ran slower than the retained exact replay reference:

- reference exact replay elapsed:
  - `00:21:54`
- kept live canary elapsed:
  - `00:30:51`
- elapsed delta:
  - `+537.015s`
- elapsed ratio:
  - about `1.409x`

This should be treated as a timing anomaly on the kept/no-action lane, not as a
semantic checkpoint failure:

- the restart32 verdict was `keep`
- no action was applied
- the final selected-path result matched the retained exact replay
- provenance audit passed cleanly

## Operational Note

An accidental bare-process launch was started by running focused tests while
the hardcoded guard was true. That partial bundle was stopped and marked:

- `interrupted_before_wrapper_relaunch`

Partial source:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T014114Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`

It is not used as evidence.

The proper evidence source is the wrapped launch:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T014422Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`

After the run, the launch guard was reset:

- `LIVE_CANARY_LAUNCH_APPROVED = False`

## Decision

The complementary kept/no-harm canary passed the narrow checkpoint contract and
the evidence surface is clean.

Do not launch more canaries automatically. The next decision should reconcile
the two live canaries:

- filtered `7002`:
  - semantic pass
  - provenance pass
  - material runtime saving
- kept `7003`:
  - semantic pass
  - provenance pass
  - selected path preserved
  - timing anomaly versus reference

Live runtime remains blocked generally.
