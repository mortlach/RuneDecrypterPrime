# No-WLI planning baseline

This folder is the stable working home for the active No-WLI planning material.

It now lives at:
- `planning/projects/no_wli/`

It keeps the full evidence logs intact, but the top layer should always answer
three questions quickly:
- what is currently true
- what is actively being worked
- where the frozen evidence packs live

## Start here

1. `00_CURRENT_STATE.md`
2. `01_EXPERIMENT_INDEX.md`
3. `02_OPEN_QUESTIONS.md`
4. `03_DOCUMENT_MAP.md`
5. `04_ACTIVE_RUNBOOK.md`

## Folder layout

- `10_full_logs/`
  - append-only evidence logs and integrity notes
- `20_active_plans/`
  - active study plans and implementation plans
- `30_analysis_specs/`
  - authoritative contracts for active and frozen analysis branches
- `40_review_summaries/`
  - frozen review packs and comparison notes
- `50_console_and_watch_logs/`
  - saved watcher and console logs
- `60_launch_scripts/`
  - one-off PowerShell launch and watch helpers

## Working rules

- Do not delete the full logs; they remain the evidence trail.
- Keep the top-level files short and actively maintained.
- Add new studies to `01_EXPERIMENT_INDEX.md` and then expand the full science
  log.
- Keep "what is currently true" in `00_CURRENT_STATE.md`, not buried inside
  chronology.
- Keep unresolved items in `02_OPEN_QUESTIONS.md` and prune closed ones.
- Treat only the top-level `00-04` files plus the `10/20/30/40/50/60`
  buckets as the live no-WLI planning surface.
- Historical flat working material, refactor snapshots, and older review packs
  are preserved under `planning_old/`.

## Current headline state

- Fixed-instance mode v1 infrastructure is complete and validated.
- The first fixed `20`-job `p9/c3/l1000/no-WLI` panel is fully retained across
  `v71`, `v72a`, `v72b`, and `v73`.
- The integrated review now treats the panel as a real structured benchmark:
  - `1511` is the positive control
  - `611` is the middle unsolved case
  - `1111` is the conversion-failure case
  - `1411` is a useful but caveated cross-check case
- The active phase is now:
  - `fixed_instance_solver_development_v1`
- The richer-pool downstream replacement reopen is now closed:
  - `phaseb_topk_frontload_all_v1` stayed the only exact-lane lift on the
    richer `1111/search7002` pool
  - narrow replacement widths were active but flat
- The fixed `1111/search7004` two-job entry-allocation canary is now closed as
  an operational runtime shape:
  - rescued partial control evidence was useful
  - but the candidate never ran and the two-job session was not an honest
    canary unit
- The queued `1111/search7005` same-family follow-on did not launch:
  - the cutoff gate failed before the first canary job completed
- The fixed `1111/search7004` one-job entry-allocation probe is now closed:
  - the process was stopped after running past the written `8h` stop rule
  - only `4 / 6` Phase-C starts completed
  - the best partial read only reproduced the retained `0.432` anchor-family
    best
  - the config could widen Stage-3 entry by at most `+2` keys, so it was not
    an honest strong-allocation test
- The contingent `1111/search7005` same-family follow-on is now closed as a
  non-launch:
  - once `7004` closed as an underpowered non-signal, the replication gate
    disappeared
- The upstream representative-selection branch is now narrowed in three steps:
  - promoted-family audit:
    - `1111` shows a persistent upstream within-family representative gap at
      both `stage2_topk` and `stage2_promoted`
  - concrete policy audit:
    - `selected_family_low_edge_eps_0p020_v1` switches all five retained
      `1111` lanes while staying inert on `611`, `1411`, and `1511`
  - family-view / score-band sensitivity sweep:
    - only `prefix_hamming_le_24` yields a clean activation window
    - the smallest clean band is `eps = 0.016`
    - `eps = 0.015` is harmful on `1111`
    - `eps = 0.025` attenuates the gain sharply
  - saved handoff audit:
    - the concrete selector changes `best2_key`, `promoted_keys`, and `init3`
      on all five retained `1111` lanes
    - it stays inert on `611`, `1411`, and `1511`
- The first exact execution microprobe for that selector is now complete:
  - fixed `1111/search7004`
  - runtime:
    - `01:07:53`
  - the selector created a strong challenger lane up to `0.420`
  - but the replay still lost to:
    - artifact baseline `0.423`
    - retained Stage-3 reference `0.432`
- The exact selector family matrix across fixed `1111/search7001-7005` is now
  complete:
  - runtime:
    - `01:52:14`
  - one clean exact win:
    - `7003`
    - replay `0.476`
    - delta vs baseline `+0.068`
    - delta vs retained Stage-3 reference `+0.153`
  - one baseline-only supporting win:
    - `7005`
    - replay `0.413`
    - delta vs baseline `+0.041`
    - delta vs retained Stage-3 reference `-0.003`
  - one slight local loss:
    - `7004`
    - delta vs baseline `-0.003`
  - two severe collapses:
    - `7001`
      - delta vs baseline `-0.267`
    - `7002`
      - delta vs baseline `-0.444`
  - family mean delta vs baseline:
    - `-0.121`
- The Phase-A competitiveness audit on that exact family is now complete:
  - best gate:
    - `phasea_rank1_init_match >= 0.30`
  - kept seeds:
    - `7003,7004,7005`
  - filtered seeds:
    - `7001,7002`
  - counterfactual family mean delta vs baseline:
    - `+0.021`
  - current read:
    - the selector split is already visible from an early Phase-A
      competitiveness signal
    - the next honest branch is now a concrete gated microprobe rather than a
      generic postmortem label
- The Phase-A rank-1 gate microprobe is now complete:
  - gate:
    - `phasea_rank1_init_match >= 0.30`
  - counterfactual family mean delta vs baseline:
    - `+0.021`
  - counterfactual family mean delta vs retained:
    - `+0.030`
  - filtered saved attempt minutes total:
    - `42.3`
  - filtered saved attempt share:
    - `0.961`
  - current read:
    - the gate is operationally meaningful, not just descriptive
    - the next honest branch is now gate persistence / actionability, not a
      new replay family
- The Phase-A gate persistence microprobe is now complete:
  - the replay bundle now writes:
    - `resume_bundle/phasea_gate_snapshot.json`
  - progress now includes:
    - `stage3_phasea_gate_snapshot`
  - the exact replay wrapper now exposes:
    - `phasea_gate_snapshot_json_relpath`
  - focused verification:
    - `40 passed`
- The first exact live-read canary exposed a real schema gap:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T034213Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
  - snapshot file existed
  - key gate fields were still `null`
  - snapshot share was about `0.891`
- The patched `7004` live-read canary is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061020Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
  - runtime:
    - `00:23:56`
  - result:
    - same local replay negative
  - live-read outcome:
    - `phaseA_rank1_init_match = 0.415`
    - verdict:
      - `keep`
    - snapshot share:
      - `0.878`
- The longer fixed `1111` family follow-on is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1/`
  - runtime:
    - `02:03:21`
  - result:
    - `advance`
  - live-read family outcome:
    - snapshot present on `5 / 5`
    - snapshot usable on `5 / 5`
    - verdict matched expected split on `5 / 5`
    - keep:
      - `7003,7004,7005`
    - filter:
      - `7001,7002`
    - mean snapshot share:
      - `0.881`
- The first explicit both-action microprobe is now also complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T161225Z__stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1/`
  - filtered `7002` emitted the correct:
    - `filter`
  - and applied the configured:
    - fallback plus early stop
  - but timing failed badly:
    - prior exact replay `7002`:
      - `00:22:13`
    - current filtered action canary:
      - `01:09:52`
    - snapshot share:
      - `0.9996`
  - the microbatch stopped over budget before launching `7003`
- The raw provisional earlier-emission microprobe is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1/`
  - result:
    - `hold`
  - branch closure:
    - raw provisional `rank1` alone is not enough
  - key read:
    - filtered `7002` already matched early at restart `16`
    - kept `7003` still misfired as `filter` at every provisional checkpoint
    - but the same early snapshots already carried:
      - `phaseA_best_init_match = 0.490`
- The checkpoint-refinement audit is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T192446Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1/`
  - result:
    - `advance`
  - selected refined rule:
    - `rank1_ge_0p30_or_best_ge_0p44`
  - selected shared checkpoint:
    - restart `16`
  - mean checkpoint elapsed share:
    - `0.212`
  - mean share improvement versus the late live gate:
    - `0.674`
- The refined checkpoint confirmation microprobe is now closed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1/`
  - result:
    - `hold`
  - key read:
    - filtered `7001` stayed correctly below the provisional rescue floor:
      - `phaseA_best_init_match = 0.378`
    - kept `7005` stayed incorrectly below that same floor:
      - `phaseA_best_init_match = 0.395`
    - both values persisted unchanged across checkpoints:
      - `16 / 32 / 48 / 64`
  - branch consequence:
    - the next question is field persistence, not another action canary
- The strict field-persistence audit is now closed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210520Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1/`
  - result:
    - `hold`
  - key read:
    - filtered `7002` still moved between:
      - restart `16`
        - `0.289`
      - restart `32`
        - `0.329`
- The stabilization-window audit is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210839Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1/`
  - result:
    - `advance`
  - selected field:
    - `phaseA_best_init_match`
  - earliest stable separating window:
    - restart `32`
  - threshold midpoint:
    - `0.3865`
  - mean share improvement versus the late gate:
    - `0.455`
- The restart-32 best-init action microprobe is now closed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T211444Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1/`
  - result:
    - `advance`
  - key read:
    - filtered `7001`
      - verdict:
        - `filter`
      - action checkpoint:
        - restart `32`
      - saved attempt share:
        - `0.562`
    - kept `7005`
      - verdict:
    - `keep`
      - action checkpoint:
        - restart `32`
      - delta vs prior exact replay:
        - `0.000`
- The remaining-family restart32 best-init microbatch is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`
  - result:
    - `advance`
  - family-contract read:
    - verdict match:
      - `3 / 3`
    - filtered `7002`:
      - action checkpoint:
        - restart `32`
      - saved attempt seconds:
        - `759.7`
      - saved attempt share:
        - `0.570`
      - landed at retained baseline:
        - `0.754`
    - kept `7003/7004`:
      - no-harm count:
        - `2 / 2`
      - delta vs reference exact replay:
        - `0.000`
    - family mean delta vs baseline:
      - `+0.0217`
    - mean checkpoint share of reference attempts:
      - `0.421`
  - operational caveat:
    - kept `7004` preserved the exact outcome but inflated elapsed wallclock to
      `00:37:37` versus its reference exact replay anchor `00:24:17`
- The kept-`7004` timing postmortem audit is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T001151Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1/`
  - result:
    - `advance`
  - timing-postmortem read:
    - `7003` stays timing-stable under the same action wiring
    - `7004` first decides `keep` early at restart `32`
    - `7004` slowdown is already visible by restart `64` and deep in Phase B
    - the anomaly does not read like a gate-logic failure
  - final handoff status:
    - review-ready after provenance reconciliation
    - science claim is provisionally supported on fixed
      `1111/search7001-7005`
    - live runtime remains blocked
    - production/general policy is not claimed
    - final hardened provenance audit:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T190612Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1/`
- No active multi-hour serial no-WLI family run is currently confirmed from
  repo state.
- The next honest move is now:
  - keep generic family-diversity and entry-allocation runtime closed
  - keep the concrete upstream selector out of live runtime in raw form
  - carry forward the validated late gate:
    - `phasea_rank1_init_match >= 0.30`
  - keep the action-choice question effectively closed in the narrow sense:
    - `both` is not the blocker
    - timing is the blocker
  - keep the raw provisional branch closed:
    - checkpoint `rank1` alone is not the right early surface
  - keep the failed composite refined rule closed:
    - `rank1>=0.30 or best>=0.44`
  - keep the strict restart-16 field-persistence criterion closed
  - carry forward the validated provisional action rule:
    - restart `32`
    - `phaseA_best_init_match >= 0.3865`
  - treat the fixed `1111` family generalization question as semantically
    complete
  - treat the selector checkpoint science as provisionally supported on fixed
    `1111/search7001-7005`
  - carry the selector checkpoint subtopic as review-ready after provenance
    reconciliation
  - keep live runtime blocked until a separate explicit live-canary decision is
    written
  - do not claim production/general policy from this subtopic
- The next selector-checkpoint branch is active planning only:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_plan_2026-04-25.md`
  - preferred first cell:
    - fixed `1111/search7002`
  - max runtime:
    - `08:00:00`
  - Day 2 preflight:
    - passed
    - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_preflight_note_2026-04-25.md`
  - launch wrapper:
    - `60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_open_terminal_2026-04-25.ps1`
  - Day 3 canary:
    - passed
    - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_review_note_2026-04-25.md`
  - complementary kept/no-harm canary:
    - passed semantically and provenance-clean
    - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_kept7003_review_note_2026-04-25.md`
  - live-canary reconciliation:
    - closed as semantic pass with timing caveat
    - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_reconciliation_note_2026-04-26.md`
  - no further canary from this branch; any further runtime should be a
    separate timing-risk follow-up
- The next timing-risk follow-up is planning-only:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_followup_plan_2026-04-26.md`
  - no runtime is approved by that plan
- The completed infrastructure stream is now frozen baseline background:
  - `20_active_plans/no_wli_fixed_instance_mode_infrastructure_plan_2026-04-08.md`
  - `30_analysis_specs/no_wli_fixed_instance_mode_v1_spec_2026-04-08.md`

## Main live references

- latest closed probe plan:
  - `20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_plan_2026-04-22.md`
- latest probe closure note:
  - `40_review_summaries/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_closure_note_2026-04-22.md`
- current upstream audit plan:
  - `20_active_plans/no_wli_stage2_stage3_promoted_family_audit_plan_2026-04-22.md`
- current upstream audit note:
  - `40_review_summaries/no_wli_stage2_stage3_promoted_family_audit_note_2026-04-22.md`
- current upstream audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/`
- current representative-policy audit plan:
  - `20_active_plans/no_wli_stage2_topk_family_representative_policy_audit_plan_2026-04-22.md`
- current representative-policy audit note:
  - `40_review_summaries/no_wli_stage2_topk_family_representative_policy_audit_note_2026-04-22.md`
- current representative-policy audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/`
- current representative-policy sensitivity plan:
  - `20_active_plans/no_wli_stage2_topk_family_representative_policy_sensitivity_plan_2026-04-22.md`
- current representative-policy sensitivity note:
  - `40_review_summaries/no_wli_stage2_topk_family_representative_policy_sensitivity_note_2026-04-22.md`
- current representative-policy sensitivity bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/`
- current selected-family handoff audit plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_handoff_audit_plan_2026-04-22.md`
- current selected-family handoff audit note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_handoff_audit_note_2026-04-22.md`
- current selected-family handoff audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T031321Z__stage2_topk_selected_family_low_edge_handoff_audit_v1/`
- completed execution microprobe plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_execution_microprobe_plan_2026-04-23.md`
- execution microprobe closure note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_closure_note_2026-04-23.md`
- completed execution microprobe bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- exact-family matrix plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_plan_2026-04-23.md`
- exact-family matrix closure note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_closure_note_2026-04-23.md`
- exact-family matrix bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/`
- current Phase-A competitiveness audit plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_plan_2026-04-23.md`
- current Phase-A competitiveness audit note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_note_2026-04-23.md`
- current Phase-A competitiveness audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/`
- current Phase-A rank-1 gate microprobe plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_plan_2026-04-23.md`
- current Phase-A rank-1 gate microprobe note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_note_2026-04-23.md`
- current Phase-A rank-1 gate microprobe bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T023226Z__stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1/`
- current Phase-A gate persistence microprobe plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_persistence_microprobe_plan_2026-04-23.md`
- current Phase-A gate persistence microprobe note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_persistence_microprobe_note_2026-04-23.md`
- current Phase-A gate live-read canary note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_live_read_canary_1111_search7004_note_2026-04-24.md`
- current Phase-A gate live-read follow-on closure note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_closure_note_2026-04-24.md`
- current Phase-A gate live-read follow-on plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_plan_2026-04-23.md`
- current raw provisional earlier-emission closure note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_closure_note_2026-04-24.md`
- current checkpoint-refinement audit plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_plan_2026-04-24.md`
- current checkpoint-refinement audit note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_note_2026-04-24.md`
- current checkpoint-refinement audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T192446Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1/`
- refined-checkpoint confirmation plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_plan_2026-04-24.md`
- refined-checkpoint confirmation closure note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_closure_note_2026-04-24.md`
- refined-checkpoint confirmation bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1/`
- strict field-persistence audit plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_plan_2026-04-24.md`
- strict field-persistence audit note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_note_2026-04-24.md`
- stabilization-window audit note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_note_2026-04-24.md`
- stabilization-window audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210839Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1/`
- best-init window action microprobe plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_plan_2026-04-24.md`
- best-init window action microprobe closure note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_closure_note_2026-04-24.md`
- best-init window action microprobe bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T211444Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1/`
- best-init window family microbatch plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_plan_2026-04-24.md`
- best-init window family microbatch closure note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_closure_note_2026-04-24.md`
- best-init window family microbatch bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`
- best-init window timing postmortem audit plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_plan_2026-04-24.md`
- best-init window timing postmortem audit note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_note_2026-04-25.md`
- selector checkpoint subtopic synthesis note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_subtopic_synthesis_note_2026-04-25.md`
- selector checkpoint last-5 summary note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_last5_experiments_summary_2026-04-25.md`
- selector checkpoint review pack:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25/`
  - zip:
    - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25.zip`
  - paired src bundle:
    - `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260425T191004Z.zip`
- selector checkpoint final handoff archive note:
  - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_final_handoff_archive_note_2026-04-25.md`
- selector checkpoint live-canary preparation plan:
  - `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_plan_2026-04-25.md`
- review-pack method note:
  - `20_active_plans/no_wli_review_pack_method_note_2026-04-25.md`
- refined-checkpoint confirmation log:
  - `50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_2026-04-24.log`
- execution runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
- follow-on family runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1.py`
- exact-family matrix runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1.py`
- historical prepared execution launchers:
  - `60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_launch_2026-04-23.ps1`
  - `60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_open_terminal_2026-04-23.ps1`
- completed exact-family matrix log:
  - `50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_2026-04-23.log`
- completed exact-family matrix launchers:
  - `60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_launch_2026-04-23.ps1`
  - `60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_open_terminal_2026-04-23.ps1`
- prior paired-canary basis:
  - `20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_canary_plan_2026-04-22.md`
- current operational closure note:
  - `40_review_summaries/no_wli_stage3_entry_const_local_depth_fixed_canary_operational_closure_note_2026-04-22.md`
- runtime budgeting reference:
  - `20_active_plans/no_wli_runtime_budgeting_reference_note_2026-04-20.md`
- current closure note:
  - `40_review_summaries/no_wli_phasec_richer_pool_replacement_reopen_closure_note_2026-04-22.md`
- authoritative phase contract:
  - `30_analysis_specs/no_wli_fixed_instance_solver_development_v1_spec_2026-04-14.md`
- main fixed-panel review pack:
  - `40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- family supplements:
  - `40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`
  - `40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`

## Snapshot history

A dated snapshot of the initial refactor baseline is preserved under:
- `planning_old/archive/no_wli_planning_refactor_20260404/`

Retired live-surface residue from the earlier no-WLI refactor is preserved
under:
- `planning_old/legacy/no_wli_live_surface_residue_2026-04-14/`
