# Stage-2 Selected-Family Phase-A Checkpoint Live-Canary Review Note

Date: 2026-04-25

## Outcome

- source bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T004304Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
- provenance audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T012105Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1/`
- canary recommendation:
  - `advance`
- audit recommendation:
  - `advance`
- decision:
  - first live canary passed
  - one further narrow canary is justified
  - live runtime is not generally reopened
  - production/general policy is not claimed

## What Ran

- one canary only:
  - fixed `1111/search7002`
- lane role:
  - `filtered_family`
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
  - fallback to retained baseline
  - early stop
- budget:
  - `08:00:00`
- actual wrapper elapsed:
  - `00:14:01`
- canary bundle elapsed:
  - `00:13:39`

## Result

- status:
  - `completed`
- completed jobs:
  - `1 / 1`
- checkpoint restart:
  - `32`
- `phaseA_best_init_match`:
  - `0.329`
- threshold:
  - `0.3865`
- observed verdict:
  - `filter`
- expected verdict:
  - `filter`
- action applied:
  - `1`
- `action_stop_now`:
  - `1`
- `action_fallback_to_baseline`:
  - `1`
- fallback target:
  - `retained_baseline`
- baseline match:
  - `0.754`
- current match:
  - `0.754`
- delta versus baseline:
  - `0.000`
- selected/reference resume match:
  - `0.310`
- delta versus selected/reference:
  - `0.444`
- exact-replay reference elapsed:
  - `00:22:13`
- canary elapsed:
  - `00:13:33`
- saved attempt seconds:
  - `519.954`
- saved attempt share:
  - `0.390`
- action behaved as expected:
  - `1`

## Provenance Audit

- bundle complete:
  - `1`
- row mismatch count:
  - `0`
- mismatched seeds:
  - `none`
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

## Readout Status Blemish

The source readout markdown contains one stale status line:

- `final status: running`

The state file, final event, row, summary, recommendation JSON, and audit all
show the source bundle completed and advanced. The stale markdown status line
came from a runner write-order issue: the markdown readout was written before
the final state payload was updated.

Fix applied after the run:

- the launch guard was reset to `LIVE_CANARY_LAUNCH_APPROVED = False`
- the runner now writes the readout after final state update for future runs

This blemish does not change the canary decision because the audited
recommendation layers and row recomputation pass, but it should be noted if
this bundle is shared.

## Decision

This first live canary produced a complete and auditable checkpoint decision
under the reviewed restart32 `phaseA_best_init_match` contract.

It supports one further narrow canary, preferably the complementary
kept/no-harm canary, still with:

- no threshold tuning
- no broad matrix
- no automatic live-runtime reopening
- no production/general-policy claim

Live runtime remains blocked generally.
