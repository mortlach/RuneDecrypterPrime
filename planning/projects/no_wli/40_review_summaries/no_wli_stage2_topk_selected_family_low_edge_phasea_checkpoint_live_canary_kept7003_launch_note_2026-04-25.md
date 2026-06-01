# Stage-2 Selected-Family Phase-A Checkpoint Kept-7003 Live-Canary Launch Note

Date: 2026-04-25

## Launch Decision

- launch approved:
  - `1`
- run shape:
  - one canary only
- canary:
  - fixed `1111/search7003`
- lane role:
  - `kept_family`
- expected verdict:
  - `keep`
- max wallclock:
  - `08:00:00`
- runtime mode:
  - pop-out PowerShell wrapper with repo-relative log

## Contract

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
- keep action:
  - no action
  - preserve selected-family attempt

## Preconditions

- filtered `7002` live canary:
  - passed
- kept `7003` preflight:
  - passed
- kept `7003` preflight bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T014014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_preflight_v1/`
- failed checks:
  - `none`
- retained exact replay reference:
  - elapsed `00:21:54`
  - baseline match `0.408`
  - selected/reference resume match `0.476`
- guard changed for this launch:
  - `LIVE_CANARY_LAUNCH_APPROVED = True`

## Launch Path

- open-terminal wrapper:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_open_terminal_2026-04-25.ps1`
- launch script:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_launch_2026-04-25.ps1`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_kept7003_2026-04-25.log`

## Stop Rule

- the launch wrapper emits watchdog progress every `60s`
- the wrapper stops the process at `08:00:00` if it has not completed
- no further canary may launch automatically

## Post-Run Gate

After completion, run the live-canary provenance audit.

Accept only if:

- audit recommendation is `advance`
- row mismatch count is `0`
- state recommendation is `advance`
- final event recommendation is `advance`
- summary-derived recommendation is `advance`
- recommendation JSON is `advance`
- readout is `advance`

Otherwise:

- hold
