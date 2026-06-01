# Stage-2 Selected-Family Phase-A Checkpoint Live-Canary Launch Note

Date: 2026-04-25

## Launch Decision

- launch approved:
  - `1`
- run shape:
  - one canary only
- canary:
  - fixed `1111/search7002`
- lane role:
  - `filtered_family`
- expected verdict:
  - `filter`
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
- filter action:
  - fallback to retained baseline
  - early stop selected-family attempt
- keep action:
  - no action

## Preconditions

- Day 2 preflight:
  - passed
- preflight bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T220602Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_preflight_v1/`
- failed checks:
  - `none`
- direct runner guard before this launch note:
  - `LIVE_CANARY_LAUNCH_APPROVED = False`
- guard changed for this launch:
  - `LIVE_CANARY_LAUNCH_APPROVED = True`

## Launch Path

- open-terminal wrapper:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_open_terminal_2026-04-25.ps1`
- launch script:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_launch_2026-04-25.ps1`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_2026-04-25.log`

## Stop Rule

- the launch wrapper emits watchdog progress every `60s`
- the wrapper stops the process at `08:00:00` if it has not completed
- no second canary may launch automatically

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
