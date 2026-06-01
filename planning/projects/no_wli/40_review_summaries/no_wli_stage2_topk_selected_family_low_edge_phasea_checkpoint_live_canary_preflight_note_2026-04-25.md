# Stage-2 Selected-Family Phase-A Checkpoint Live-Canary Preflight Note

Date: 2026-04-25

## Outcome

- preflight bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T220602Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_preflight_v1/`
- recommendation:
  - `advance`
- failed checks:
  - `none`
- runtime launched:
  - `0`
- live runtime status:
  - still blocked until the launch note is accepted and the hardcoded runner
    guard is deliberately changed

## What Passed

- the harness is one-cell only:
  - `1111/search7002`
- lane role is explicit and recognized:
  - `filtered_family`
- expected verdict is:
  - `filter`
- carried contract is pinned:
  - restart `32`
  - `phaseA_best_init_match`
  - threshold `0.3865`
  - filter action `fallback_and_early_stop`
- the decider defers before restart `32`
- the decider filters at restart `32`
- decision fields are complete:
  - missing decision fields: `none`
- reference row is present:
  - retained exact replay `7002` elapsed `00:22:13`
  - baseline best match `0.754`
  - selected/reference resume match `0.310`
- output parent resolves under the repo root
- the post-run audit declares all five recommendation layers:
  - state
  - final event
  - summary-derived
  - recommendation JSON
  - readout

## Launch Boundary

The runner still has:

- `LIVE_CANARY_LAUNCH_APPROVED = False`

Direct execution returns:

- status `launch_blocked`
- recommendation `hold`

The Day 3 launch wrapper is staged but will also refuse to run while the guard
is false:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_launch_2026-04-25.ps1`
- `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_open_terminal_2026-04-25.ps1`

The wrapper records stdout/stderr to:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_2026-04-25.log`

and enforces:

- max wallclock `08:00:00`
- watchdog progress every `60s`
- process stop at the cap if the canary has not completed

## Decision

Day 2 passed. The next step is a Day 3 launch decision, not threshold tuning or
matrix widening.

Before launch:

- keep the canary one-cell only
- keep the contract unchanged
- record the launch note
- change the hardcoded launch guard to `True`
- launch through the pop-out PowerShell wrapper

After launch:

- run the live-canary provenance audit
- accept only if recommendation is `advance`, row mismatch count is `0`, and
  all five recommendation layers are present and set to `advance`
