# No-WLI Study 2 Readout Checklist (2026-03-28)

Use this checklist for the first live Study 2 compare only:

- control:
  - `stage3_preserve_tieband_probe_p9`
- candidate:
  - `stage3_phaseb_family_preserve_p9`
- seed:
  - `411`

## 1. Validity Check

Confirm the run finished cleanly:

- `completed_jobs = 2`
- `stopped_early = 0`
- no `last_error`

Confirm the intended semantic delta only:

- candidate `run_config.json` should differ from control mainly in:
  - `stage3.two_phase.family_preservation.policy`
  - `stage3.two_phase.family_preservation.family_view_id`
  - `stage3.two_phase.family_preservation.reserved_slots`

Do not treat the run as valid if it also changed:

- Phase-B ranking logic
- Phase-C start policy
- rescue settings
- Stage-3 entry policy

## 2. Phase-B Family Telemetry

Compare control vs candidate:

- `phaseB_family_preservation_policy`
- `phaseB_family_view_id`
- `phaseB_family_reserved_slots`
- `phaseB_family_count_in_top_band`
- `phaseB_family_preserved_count`
- `phaseB_family_reservation_applied`
- `phaseB_selected_unique_end_hash`
- `phaseB_downstream_selected_count`
- `phaseB_downstream_selected_unique_end_hash`

High-signal positive pattern:

- `phaseB_family_reservation_applied = 1`
- `phaseB_family_preserved_count` increases over control
- `phaseB_downstream_selected_unique_end_hash` stays same or increases

## 3. Phase-C Diversity Readout

Compare:

- `phaseC_candidate_pool_unique_end_hash`
- `phaseC_candidate_pool_source_counts`
- `phaseC_start_keys_used`
- `phaseC_start_unique_end_hash`
- `phaseC_start_source_counts`
- `phaseC_final_winner_source`

High-signal positive pattern:

- more distinct downstream Phase-B families survive into the Phase-C pool
- actual Phase-C starts become more diverse
- a non-anchor downstream source contributes real starts

## 4. Solve Readout

Compare:

- `best_stage`
- `best_match_ratio`
- `stage3_match_ratio`

Interpretation:

- valid positive:
  - family preservation telemetry changes as intended
  - downstream diversity rises
  - solve improves
- valid negative:
  - family preservation telemetry changes as intended
  - downstream diversity rises or is at least preserved differently
  - solve does not improve
- invalid:
  - intended policy is not reflected in config/telemetry
  - unrelated late-stage knobs changed

## 5. Evidence Paths To Save In The Log

For each run, record:

- run directory
- `run_config.json`
- `instances.json`
- `best_instance.json`
- `stages.json`
- `resume_handoffs/.../manifest.json`
- matrix:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v39_p9c3_seed411_phaseb_family_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v39_p9c3_seed411_phaseb_family_compare_2job.jsonl`
