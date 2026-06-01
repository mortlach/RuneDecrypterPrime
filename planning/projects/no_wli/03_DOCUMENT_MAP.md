# Document map

This file maps the live `planning/projects/no_wli/` surface and points at the
current active no-WLI documents.

Historical flat working material, earlier refactor snapshots, and older review
packs are preserved under `planning_old/`.

## Live no-WLI planning surface

The active surface is:
- top-level `00-04`
- `10_full_logs/`
- `20_active_plans/`
- `30_analysis_specs/`
- `40_review_summaries/`
- `50_console_and_watch_logs/`
- `60_launch_scripts/`

## Top-level navigation docs

- `00_CURRENT_STATE.md`
  - short current-state snapshot
- `01_EXPERIMENT_INDEX.md`
  - compact study and run-group table
- `02_OPEN_QUESTIONS.md`
  - active fixed-instance solver-development questions
- `03_DOCUMENT_MAP.md`
  - this file
- `04_ACTIVE_RUNBOOK.md`
  - immediate next actions and fixed definitions

## Full logs

- `10_full_logs/no_wli_science_run_log_2026-03-26.md`
  - canonical chronology and evidence trail
- `10_full_logs/no_wli_solve_integrity_plan_2026-03-21.md`
  - integrity rules and interpretation boundaries

## Active plans

- `20_active_plans/phaseB_ngram_hamming_exact_no_cap_pilot_design_plan_2026-05-29.md`
  - review-ready design for the first exact no-cap pilot after C++ Slice 2;
    freezes candidate-source comparability as a hard preflight gate, observes
    that current manual-inspection candidate text rows do not contain full
    controlled damage-stream fingerprints, and stops before pilot runner
    implementation or launch
- `20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_plan_2026-05-14.md`
  - active approved scorer contract for robust no-WLI phrase/order evidence;
    supersedes exact joined filtered n-gram scanning after the sample exact
    report showed near-zero standalone hit support; builds a word-structured
    phrase-Hamming layer with fixed profiles P0-P5, FWD-only strict/normal
    assets, damage levels `20/30/40/50`, exact no-cap hit counting, Python
    reference tests, an independent C++ backend, staged pilots, and a full
    hard-pair report only after acceptance gates pass; Slice 0 damage audit,
    Slice 1 asset validation, Slice 2 phrase index, the Python reference
    matcher, C++ Slice 1 synthetic parity, and C++ Slice 2 tiny real-index
    smoke are now implemented and passing
- `20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_implementation_start_plan_2026-05-14.md`
  - approved-with-amendments implementation start plan and current implementation
    status note for the active n-gram Hamming coherence scorer; records
    repo-grounded backend, asset, candidate, and test intelligence, recommends
    `src/rune_decrypter_prime/scoring/ngram_hamming/` for reusable scorer code,
    and now records completed Slice 0-3 artifacts, the built C++ Slice 1
    synthetic parity gate, C++ Slice 2 tiny real-index smoke, and the remaining
    pilot gates
- `20_active_plans/phaseB_filtered_ngram_hard_pair_report_v1_plan_2026-05-14.md`
  - closed/superseded report-only plan for exact joined filtered n-gram scanning;
    ran on sample-mode strict/normal FWD assets, used `rune_token_ids`, kept
    2-4 grams as the core score and 5-grams diagnostic only, and showed exact
    sample n-gram support was too sparse (`N4`/`N6` truth preference `2 / 2594`,
    net `0`), motivating the active n-gram Hamming coherence scorer
- `20_active_plans/phaseB_span_hamming_multiscore_hard_pair_report_v1_plan_2026-05-14.md`
  - closed report-only plan for the whole-ladder span-Hamming hard-pair analysis
    after the data-taking pause; uses existing hard-pair candidate feature rows
    plus Stage 1+2, Stage 3, and Stage 4 calibration summaries to test
    transparent multi-score variants S0-S8 with rescue/break accounting; its
    Panel A, S5, and length-7-HD2 support outputs are now reference features for
    the n-gram Hamming coherence scorer
- `20_active_plans/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1_plan_2026-05-14.md`
  - closed/superseded report-only next plan after the multiscore span-Hamming review; tests
    whether order, phrase, and ngram coherence can preserve span-Hamming rescues
    while suppressing local-word false-positive breaks on the same hard-pair set;
    implementation completed with positive broad combined result
    `C7_len7_hd2_exact_support_plus_coherence` and zero-break conservative
    support result `C8_span_plus_coherence_conservative`; first superseded by
    exact filtered n-gram v1 and now carried forward as a baseline for the
    n-gram Hamming coherence scorer

## Current review packs

- `40_review_summaries/phaseB_ngram_hamming_exact_no_cap_pilot_design_review_pack_2026-05-29.zip`
  - design-only review pack for the exact no-cap pilot; includes parent context,
    the design plan, observed manifest-field intelligence, and review questions
    about candidate-source comparability before any pilot runner is implemented
- `40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_fast_real_index_smoke_review_pack_2026-05-29.zip`
  - review pack for the C++ Slice 2 tiny real-index smoke; includes the
    no-fallback fast smoke runner, focused test, output manifest/readout, and
    verification showing `backend_impl=cpp_fast`, exact parity with the Python
    reference, and `44` bounded n-gram Hamming tests passing
- `40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_cpp_slice1_source_review_pack_2026-05-15.zip`
  - source review pack for C++ Slice 1; includes independent in-memory C++
    backend source, pybind wrapper, Python availability wrapper, build script,
    and synthetic parity tests; originally recorded a missing-build-tools
    blocker, now cleared locally on 2026-05-29 with `_ngram_hamming_fast` built
    and `41` parity/reference/tool tests passing
- `40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_pre_cpp_contract_review_pack_2026-05-15.zip`
  - source-inclusive review pack for the source-level pre-C++ amendments after
    the 2026-05-15 source-level review; includes direction-aware profiles,
    strict length/candidate token validation, core FWD invalid-row blocking,
    explicit duplicate count fields, regenerated manifests, smoke output, and
    updated tests before C++ backend work
- `40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_impl_review_pack_2026-05-15.zip`
  - replacement source-inclusive implementation review pack after pack-level
    review passed with amendments and code-level review was blocked by missing
    source/test contents; includes source files, tests, amended manifests,
    asset detail CSVs, profile eligibility summary, tiny Python smoke output,
    and updated review questions before C++ backend work
- `40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_impl_review_pack_2026-05-14.zip`
  - portable implementation review pack for the completed Slice 0-3/reference
    work; includes active planning context, changed-file inventory,
    damage-source/asset/phrase-index manifests and readouts, verification
    summary, and review questions before C++ backend work; superseded for
    code-level review by the 2026-05-15 source-inclusive pack
- `40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_start_review_pack_2026-05-14.zip`
  - portable review pack for the n-gram Hamming coherence implementation start plan;
    includes the active plan, implementation start plan, predecessor readouts,
    repo-intelligence summary, reviewer signoff answers, and approved amendments
- `20_active_plans/no_wli_stage35_resume_from_handoff_focus_family_rescue_plan_2026-04-29.md`
  - current active planning note for the late-stage-only handoff/archive rescue
    branch; target order is `1111/search7005`, `1111/search7004`, then
    `1111/search7002` as control; latest static output also records selected-row
    runner material, smoke preflight, the completed real `7005` selected-row
    run, the posthoc guard-passing rank-2 archive read, and the completed
    `7005` guard-selector follow-up that accepted the `0.422` row plus the
    `7004` secondary confirmation and first offline archive policy audit that
    exposed a truth-positive row blocked by the search-score guard
- `20_active_plans/no_wli_phasec_multi_thread_long_harvest_plan_2026-04-27.md`
  - completed Phase-C long-harvest atlas; closes broad frontload-depth / quota
    / replacement saved-surface reshuffling and carries exact-replay
    determinism evidence
- `20_active_plans/no_wli_stage3_entry_const_local_depth_reorder_signal_panel_plan_2026-04-27.md`
  - completed capped Stage-3 entry panel note; records that v79 completed only
    the `1111/search7002` legacy-entry control job and did not answer the
    constant-local-depth comparison
- `20_active_plans/no_wli_stage2_stage3_promoted_family_audit_plan_2026-04-22.md`
  - current upstream fixed-panel audit and branch-decision note
- `20_active_plans/no_wli_stage2_topk_family_representative_policy_audit_plan_2026-04-22.md`
  - first concrete selector audit on the saved `stage2_topk` surface
- `20_active_plans/no_wli_stage2_topk_family_representative_policy_sensitivity_plan_2026-04-22.md`
  - family-view and score-band sweep that narrows the selector to one setting
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_handoff_audit_plan_2026-04-22.md`
  - saved handoff gate for the narrowed selector before replay/runtime
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_execution_microprobe_plan_2026-04-23.md`
  - completed first exact execution gate for the narrowed selector
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_plan_2026-04-23.md`
  - completed bounded exact-family replay matrix across fixed `1111/search7001-7005`
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_plan_2026-04-23.md`
  - Phase-A split audit that narrows the selector branch to a concrete early
    competitiveness gate
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_plan_2026-04-23.md`
  - operational microprobe showing the concrete Phase-A gate is also worth the
    runtime it can save
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_persistence_microprobe_plan_2026-04-23.md`
  - persistence pass that makes the Phase-A gate visible mid-run inside the
    replay resume bundle
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_plan_2026-04-23.md`
  - completed fixed `1111` family live-read plan and result basis after the
    patched `7004` predecessor canary
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_plan_2026-04-24.md`
  - completed first explicit both-action microprobe on filtered `7002` with a
    built-in stop-budget check before the kept canary
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_plan_2026-04-24.md`
  - completed retained-bundle audit that selects the refined provisional rule
    `rank1>=0.30 or best>=0.44`
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_plan_2026-04-24.md`
  - completed two-canary confirmation microprobe on `7001/7005` for the
    composite refined checkpoint rule
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_plan_2026-04-24.md`
  - completed strict persistence audit of the full retained `1111` checkpoint
    fields after the composite refined rule failed on kept `7005`
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_plan_2026-04-24.md`
  - completed hard-pair action microprobe that validates the restart32
    `phaseA_best_init_match >= 0.3865` contract on `7001/7005`
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_plan_2026-04-24.md`
  - completed remaining-family microbatch plan on `7002/7003/7004` for the
    same restart32 best-init action contract
- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_plan_2026-04-24.md`
  - completed short audit that explains the kept-`7004` timing anomaly without
    reopening runtime
- `20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_plan_2026-04-22.md`
  - latest closed one-job fixed-cell `1111/search7004` entry-allocation probe
- `20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_canary_plan_2026-04-22.md`
  - prior paired-canary basis, now closed operationally
- `20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_plan_2026-04-22.md`
  - prior same-family paired-follow-on basis, now a non-launch record
- `20_active_plans/no_wli_runtime_budgeting_reference_note_2026-04-20.md`
  - current wallclock budgeting reference before any multi-hour launch
- `20_active_plans/no_wli_fixed_instance_solver_development_plan_2026-04-14.md`
  - earlier phase basis for the current solver-development stream
- `20_active_plans/no_wli_fixed_instance_mode_infrastructure_plan_2026-04-08.md`
  - frozen baseline plan for the completed infrastructure phase
- earlier March/April study plans in the same folder
  - preserved background only unless explicitly re-opened

## Analysis specs

- `30_analysis_specs/no_wli_fixed_instance_solver_development_v1_spec_2026-04-14.md`
  - authoritative contract for the active solver-development phase
- `30_analysis_specs/no_wli_fixed_instance_mode_v1_spec_2026-04-08.md`
  - frozen baseline contract for the completed infrastructure phase
- `30_analysis_specs/no_wli_partial_state_space_map_data_contract_2026-04-02.md`
  - `space_map_v1` data contract
- `30_analysis_specs/no_wli_space_map_v1_classifier_spec_2026-04-03.md`
  - `space_map_v1` classifier vocabulary
- `30_analysis_specs/no_wli_late_family_quality_v1_spec_2026-04-08.md`
- `30_analysis_specs/no_wli_late_family_quality_v2_spec_2026-04-08.md`
- `30_analysis_specs/no_wli_late_family_quality_v3_spec_2026-04-08.md`
- `30_analysis_specs/no_wli_seed_family_triage_shadow_v1_spec_2026-04-08.md`
  - frozen background contracts for the earlier review stack

## Analysis branch docs

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/SPEC.md`
  - branch-local mirror of the active phase contract
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/EXPERIMENT_PLAN.md`
  - branch-local execution note for the active phase

## Review packs and summaries

- `40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
  - main fixed-panel external review pack
- `40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`
  - `1111` stage35 and family supplement
- `40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`
  - cross-seed family read plus `1111` focus-family diagnostic pack
- `40_review_summaries/no_wli_stage2_stage3_promoted_family_audit_note_2026-04-22.md`
  - current branch-point note for the upstream promoted-family audit
- `40_review_summaries/no_wli_stage2_topk_family_representative_policy_audit_note_2026-04-22.md`
  - concrete selector audit note
- `40_review_summaries/no_wli_stage2_topk_family_representative_policy_sensitivity_note_2026-04-22.md`
  - selector-narrowing sensitivity note
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_handoff_audit_note_2026-04-22.md`
  - saved handoff audit note for the narrowed selector
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_closure_note_2026-04-23.md`
  - closure note for the first exact execution gate on fixed `1111/search7004`
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_closure_note_2026-04-23.md`
  - closure note for the fixed `1111/search7001-7005` exact-family replay matrix
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_note_2026-04-23.md`
  - branch-point note for the early Phase-A competitiveness gate audit
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_note_2026-04-23.md`
  - branch-point note for the operational Phase-A gate microprobe
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_persistence_microprobe_note_2026-04-23.md`
  - implementation note for the persisted Phase-A gate snapshot
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_live_read_canary_1111_search7004_note_2026-04-24.md`
  - first live-read canary note that records the snapshot-schema gap found
    before the patched rerun
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_closure_note_2026-04-24.md`
  - completed family live-read closure note that validates the keep/filter split
    but leaves timing as the remaining open action question
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_closure_note_2026-04-24.md`
  - closure note for the first explicit both-action microprobe, which shows
    the blocker is timing rather than action choice
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_closure_note_2026-04-24.md`
  - closure note for the raw provisional checkpoint microprobe, which closes
    checkpoint `rank1` alone and moves the branch to refinement
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_note_2026-04-24.md`
  - note for the retained-bundle refinement audit that selects
    `rank1>=0.30 or best>=0.44`
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_closure_note_2026-04-24.md`
  - closure note for the failed second-pair confirmation of the composite
    refined checkpoint rule
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_note_2026-04-24.md`
  - note for the strict field-persistence audit, which holds because filtered
    `7002` still moved between restart `16` and `32`
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_note_2026-04-24.md`
  - note for the stabilization-window audit that selects restart `32` on
    `phaseA_best_init_match`
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_closure_note_2026-04-24.md`
  - closure note for the first successful restart32 best-init action contract
    on the hard pair `7001/7005`
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_closure_note_2026-04-24.md`
  - closure note for the remaining-family microbatch that passes the full
    fixed-`1111` semantic contract and leaves only the kept-`7004` timing
    caveat
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_note_2026-04-25.md`
  - note for the audit that clears the kept-`7004` overrun as a broad runtime
    anomaly rather than a gate-logic failure
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_subtopic_synthesis_note_2026-04-25.md`
  - compact synthesis note for the carried selector-checkpoint claim; the
    original synthesis preceded final provenance reconciliation
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_last5_experiments_summary_2026-04-25.md`
  - compact summary of the last five selector-checkpoint experiments, including
    the two late holds and the final timing-postmortem advance
- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25/`
  - current selector-checkpoint review pack folder
  - status:
    - review-ready after provenance reconciliation
  - zip:
    - `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25.zip`
  - paired src bundle:
    - `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260425T191004Z.zip`

- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_reconciliation_plan_2026-04-25.md`
  - completed reconciliation plan after the first external-review pass blocked
    the package on provenance/reporting mismatch

- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_plan_2026-04-25.md`
  - active planning note for the next narrow live-canary preparation branch;
    freezes the reviewed restart32 best-init contract, preferred filtered
    `1111/search7002` canary, `08:00:00` max runtime, and Day 2/Day 3 gates
    before any launch

- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_preflight_note_2026-04-25.md`
  - Day 2 preflight note for the live-canary branch; records the passing
    preflight bundle, the still-blocked launch guard, and the staged
    8-hour-watchdog launch wrapper

- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_launch_note_2026-04-25.md`
  - Day 3 launch note for the one-cell filtered live canary; records the
    hardcoded guard flip, one-cell scope, 8-hour cap, and post-run audit gate

- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_review_note_2026-04-25.md`
  - Day 3 review note for the completed filtered live canary; records the
    source bundle, passing provenance audit, runtime saving, and the remaining
    boundary that live runtime is not generally reopened

- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_kept7003_launch_note_2026-04-25.md`
  - launch note for the complementary kept/no-harm `1111/search7003` live
    canary; records the preflight, guard flip, one-cell scope, and audit gate

- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_kept7003_review_note_2026-04-25.md`
  - review note for the kept/no-harm `1111/search7003` live canary; records
    the semantic pass, clean provenance audit, and timing caveat versus the
    retained exact replay reference

- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_reconciliation_note_2026-04-26.md`
  - reconciliation note for the filtered `7002` and kept `7003` live canaries;
    closes the branch as a semantic/provenance pass with a kept-lane timing
    caveat and blocks further checkpoint-canary widening from this branch

- `20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_followup_plan_2026-04-26.md`
  - active planning note for the next timing-risk follow-up; uses existing
    retained exact replay, family microbatch, and live kept-`7003` bundles only
    before proposing any further runtime

- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_external_review_first_pass_note_2026-04-25.md`
  - compact note recording the current agreed verdict:
    science likely survives, pack does not

- `40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_family_provenance_audit_note_2026-04-25.md`
  - note for the short provenance audit that machine-confirms the remaining
    family bundle mismatch:
    `7002` row recomputes as success while state/event still say `hold`

- `20_active_plans/no_wli_review_pack_method_note_2026-04-25.md`
  - current review-pack method note; updated so sendable review packs should
    include the generated source zip inside the pack when size permits, with
    reviewer-facing paths written relative to the review zip root
- `40_review_summaries/no_wli_solver_development_pivot_synthesis_2026-05-02.md`
  - external-review synthesis after closing broad local-rescue policy widening;
    recommends moving up to ledger / oracle-gap tooling or held-out validation
    before more runtime
- `40_review_summaries/no_wli_solver_development_pivot_review_pack_2026-05-02/`
  - current self-contained strategy-level external review pack
  - nested source bundle:
    - `90_source_bundle/get_src_extended_review_bundle__20260502T022329Z.zip`
  - zip:
    - `40_review_summaries/no_wli_solver_development_pivot_review_pack_2026-05-02.zip`
- `40_review_summaries/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_closure_note_2026-04-22.md`
  - closure note for the stopped over-budget `1111/search7004` one-job probe
- older review notes in `40_review_summaries/`
  - background evidence only; not live entry points

## Console logs and launch scripts

- `50_console_and_watch_logs/`
  - watcher and console logs for retained run history
- current no-WLI runtime references:
  - `50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_canary_2026-04-22.log`
  - `50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_queue_2026-04-22.log`
  - `50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_2026-04-23.log`
  - `50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_2026-04-24.log`
  - `50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_2026-04-24.log`
  - `50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_2026-04-24.log`
  - `50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_2026-04-24.log`
  - `50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_2026-04-24.log`
- `60_launch_scripts/`
  - one-off PowerShell launch and watch helpers from the completed fixed-panel
    collection phase
  - current Stage 3.5 local-rescue launchers:
    - `60_launch_scripts/no_wli_stage35_guard_selector_frontier_deepening_harvest_launch_2026-04-29.ps1`
    - `60_launch_scripts/no_wli_stage35_guard_selector_frontier_deepening_harvest_open_terminal_2026-04-29.ps1`
  - current Stage 3.5 local-rescue console log:
    - `50_console_and_watch_logs/no_wli_stage35_guard_selector_frontier_deepening_harvest_2026-04-29.log`
  - completed Stage 3.5 deepening output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/`
  - completed Stage 3.5 shallow-plus-deepening join/dedup output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/`
  - completed rank-6 selected-start safety output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T014439Z__stage35_rank6_selected_start_gate_safety_v1/`
  - current rank-6 local-rescue policy sketch:
    - `40_review_summaries/no_wli_stage35_rank6_local_rescue_policy_sketch_2026-04-30.md`
  - current rank-6 local-rescue canary design:
    - `40_review_summaries/no_wli_stage35_rank6_local_rescue_canary_design_2026-04-30.md`
  - current rank-6 local-rescue canary launchers:
    - `60_launch_scripts/no_wli_stage35_rank6_local_rescue_canary_launch_2026-04-30.ps1`
    - `60_launch_scripts/no_wli_stage35_rank6_local_rescue_canary_open_terminal_2026-04-30.ps1`
  - current rank-6 local-rescue canary console log:
    - `50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_canary_2026-04-30.log`
  - completed rank-6 local-rescue canary output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T015732Z__stage35_rank6_local_rescue_canary_v1/`
  - current rank-6 local-rescue recall/audit launchers:
    - `60_launch_scripts/no_wli_stage35_rank6_local_rescue_recall_audit_launch_2026-04-30.ps1`
    - `60_launch_scripts/no_wli_stage35_rank6_local_rescue_recall_audit_open_terminal_2026-04-30.ps1`
  - current rank-6 local-rescue recall/audit console log:
    - `50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_recall_audit_2026-04-30.log`
  - completed rank-6 local-rescue recall/audit output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T021919Z__stage35_rank6_local_rescue_recall_audit_v1/`
  - completed rank-6 boundary-feature audit output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T032952Z__stage35_rank6_boundary_feature_audit_v1/`
  - rank-6 boundary rule revision note:
    - `40_review_summaries/no_wli_stage35_rank6_boundary_rule_revision_note_2026-04-30.md`
  - completed rank-6 route-lineage boundary audit output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T033637Z__stage35_rank6_route_lineage_boundary_audit_v1/`
  - rank-6 route-lineage external-review note:
    - `40_review_summaries/no_wli_stage35_rank6_route_lineage_boundary_review_note_2026-04-30.md`
  - rank-6 route-lineage review pack:
    - `40_review_summaries/no_wli_stage35_rank6_route_lineage_review_pack_2026-04-30/`
  - zipped rank-6 route-lineage review pack:
    - `40_review_summaries/no_wli_stage35_rank6_route_lineage_review_pack_2026-04-30.zip`
  - paired generated source bundle:
    - `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260430T041152Z.zip`
  - moved final dev review draft:
    - `40_review_summaries/no_wli_stage35_rank6_route_lineage_final_dev_review_draft_2026-04-30.md`
  - review action note:
    - `40_review_summaries/no_wli_stage35_rank6_route_lineage_review_action_note_2026-04-30.md`
  - completed strict route-lineage confirmation-prep output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T151237Z__stage35_rank6_route_lineage_confirmation_prep_v1/`
  - route-lineage additive confirmation design:
    - `40_review_summaries/no_wli_stage35_rank6_route_lineage_additive_confirmation_design_2026-04-30.md`
  - route-lineage additive confirmation closeout:
    - `40_review_summaries/no_wli_stage35_rank6_route_lineage_additive_confirmation_closeout_2026-04-30.md`
  - completed route-lineage additive confirmation output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153119Z__stage35_rank6_route_lineage_additive_confirmation_v1/`
  - route-lineage additive confirmation console log:
    - `50_console_and_watch_logs/no_wli_stage35_rank6_route_lineage_additive_confirmation_2026-04-30.log`
  - constant-local-depth handoff activation output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022336Z__stage3_entry_const_local_depth_handoff_activation_v1/`
  - constant-local-depth handoff resume plan:
    - `20_active_plans/no_wli_stage3_entry_const_local_depth_handoff_resume_plan_2026-05-01.md`
  - constant-local-depth handoff 7005 runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_handoff_7005_v1.py`
  - constant-local-depth handoff 7005 launch script:
    - `60_launch_scripts/no_wli_stage3_entry_const_local_depth_handoff_7005_launch_2026-05-01.ps1`
  - constant-local-depth handoff 7005 console log:
    - `50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_handoff_7005_2026-05-01.log`
  - completed constant-local-depth handoff 7005 output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/`
  - constant-local-depth handoff 7004 runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_handoff_7004_v1.py`
  - constant-local-depth handoff 7004 launch script:
    - `60_launch_scripts/no_wli_stage3_entry_const_local_depth_handoff_7004_launch_2026-05-01.ps1`
  - constant-local-depth handoff 7004 console log:
    - `50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_handoff_7004_2026-05-01.log`
  - completed constant-local-depth handoff 7004 output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/`
  - constant-local-depth handoff closeout:
    - `40_review_summaries/no_wli_stage3_entry_const_local_depth_handoff_closeout_2026-05-01.md`
  - constant-local-depth downstream-selection audit extractor:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage3_entry_const_local_depth_downstream_selection_audit_v1.py`
  - completed constant-local-depth downstream-selection audit output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T155731Z__stage3_entry_const_local_depth_downstream_selection_audit_v1/`
  - Stage 3.5 accept-gate broader offline audit extractor:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_accept_gate_broader_offline_audit_v1.py`
  - completed Stage 3.5 accept-gate broader offline audit output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T160206Z__stage35_accept_gate_broader_offline_audit_v1/`
  - Stage 3.5 frontier-space robustness harvest plan:
    - `20_active_plans/no_wli_stage35_frontier_space_robustness_harvest_plan_2026-05-01.md`
  - Stage 3.5 frontier-space robustness harvest runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_frontier_space_robustness_harvest_v1.py`
  - Stage 3.5 frontier-space robustness harvest launch scripts:
    - `60_launch_scripts/no_wli_stage35_frontier_space_robustness_harvest_launch_2026-05-01.ps1`
    - `60_launch_scripts/no_wli_stage35_frontier_space_robustness_harvest_open_terminal_2026-05-01.ps1`
  - Stage 3.5 frontier-space robustness harvest console log:
    - `50_console_and_watch_logs/no_wli_stage35_frontier_space_robustness_harvest_2026-05-01.log`
  - completed Stage 3.5 frontier-space robustness harvest output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T161846Z__stage35_frontier_space_robustness_harvest_v1/`
  - Stage 3.5 frontier-space robustness harvest closeout:
    - `40_review_summaries/no_wli_stage35_frontier_space_robustness_harvest_closeout_2026-05-01.md`
  - Stage 3.5 frontier-space acceptance-boundary audit extractor:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_frontier_space_acceptance_boundary_audit_v1.py`
  - completed Stage 3.5 frontier-space acceptance-boundary audit output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T235632Z__stage35_frontier_space_acceptance_boundary_audit_v1/`
  - refreshed runtime references:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T234300Z__no_wli_runtime_history_reference_v1/`
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T234300Z__fixed_runtime_wallclock_reference_v1/`
  - historical prepared probe launchers for the now-closed `1111/search7004`
    one-job probe:
    - `60_launch_scripts/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_launch_2026-04-22.ps1`
    - `60_launch_scripts/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_open_terminal_2026-04-22.ps1`
  - completed exact-family matrix launchers:
    - `60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_launch_2026-04-23.ps1`
    - `60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_open_terminal_2026-04-23.ps1`
  - current remaining-family microbatch launchers:
    - `60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_launch_2026-04-24.ps1`
    - `60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_open_terminal_2026-04-24.ps1`

## Historical references

- `planning_old/archive/no_wli_planning_refactor_20260404/`
  - dated snapshot of the initial no-WLI refactor baseline
- `planning_old/archive/no_wli_external_review_passes_20260326_20260330/`
  - preserved earlier external-review source packs
- `planning_old/legacy/no_wli_live_surface_residue_2026-04-14/`
  - retired live-surface residue removed from the active tree
- older logs that still say `planning/working/...`
  - read those as historical references under `planning_old/working/`
