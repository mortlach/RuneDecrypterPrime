# Active runbook

## N-gram scorer canon/bridge overlay - 2026-05-30

Accepted coordination basis:

- `planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_v3_2_canon_review.md`

Operational read:

- continue the current full raw FWD order-2/order-3 normal/strict shard build
- treat order-2/order-3 work as a staged bridge/probe toward the research-led
  scorer architecture
- do not silently descope the canonical destination into the bridge
- keep order 4 deferred for data-plane/sizing reasons only, not as a design
  rejection
- keep order 5 optional/diagnostic, not deleted
- keep production scoring unchanged

Canonical destination families:

- diagnostic: `B2R`, `N3S_diag`, `F5D`
- score-candidate: `N3C`, `S3W`, `N4L`, `S34C_main`

Bridge/probe families must declare:

- `profile_origin`
- `canonical_profile_id`
- `parameter_status`
- `score_authority`

Immediate next allowed work while the shard build runs:

- maintain bridge diagnostic schemas and tests
- prepare a provenance review pack structure
- refine the order-2/order-3 bridge diagnostic plan
- inspect live build progress and extractable shard coverage

Lane 2 preparation plan:

- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md`

Lane 2 preparation status on 2026-05-31:

- `src/rune_decrypter_prime/scoring/ngram_hamming/bridge.py` now holds the
  canonical/bridge profile authority specs, manifest hashing, and overlap/touch
  cluster helper.
- `tests/scoring/ngram_hamming/test_bridge_profiles_and_clusters.py` covers the
  v3.2 drift guards that can be tested synthetically.
- Verification passed:
  - latest focused Lane 2 set: `41 passed in 0.99s`
- Current full-raw build watch:
  - prior worker crashed/stopped after the manifest reached `641 / 1118`
    completed shards
  - restart on 2026-05-31 resumed the same run root, not a new run
  - resumed worker PID: `12928`
  - resume log line: `resume_completed_shards=641/1118`
  - restarted at: `shard_start=642/1118 order=3 shard=442`
  - final watch-log line: `status=pass completed_shards=1118/1118`
  - live watch log:
    `planning/projects/no_wli/50_console_and_watch_logs/phaseB_ngram_hamming_full_raw_asset_shards_resume_2026-05-31.log`
- Partial shard provenance helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/summarise_phaseB_ngram_hamming_full_raw_asset_shards_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1`
  - current status: `pass`, full raw confirmed
  - latest extraction: `1118 / 1118`
- Full raw provenance review-pack scaffold:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_provenance_review_pack_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1`
  - current status: `review_ready`, with checklist and copied evidence/context
  - phrase length distribution rows: `98`
  - word length distribution rows: `140`
  - pending required checks: none
- Permanent Lane 1 asset contract:
  - asset home: `assets/ngram_hamming/phaseB_full_raw_v1`
  - manifest: `assets/ngram_hamming/phaseB_full_raw_v1/asset_manifest.json`
  - asset status: `review_ready_candidate`
  - payload storage mode: manifest-indexed retained outputs, because the shard
    payload is too large for normal source-control tracking
  - listed payload files: `2236`
  - asset validation status: `pass`
  - hash failures: `0`
  - missing files: `0`
- Lane 1 closure review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane1_full_raw_language_asset_closure_review_pack_2026-06-01.zip`
  - status: `packed_review_ready`
  - entry count: `42`
  - backslash entries: `0`
  - `50_asset_index` mirrors the asset manifest, README, and permanent asset
    provenance files
  - closure safety state is derived from component manifests:
    - no production scorer change state: `true`
    - no real scan state: `true`
- Length-partition parse counters:
  - source output files: `2236`
  - parsed output files: `1728`
  - unparsed output files: `508`
  - source aggregate rows: `1115443486`
  - parsed aggregate rows: `1115443486`
  - unparsed aggregate rows: `0`
- Lane 2 launch decision record:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1`
  - current status: `blocked`, approval switch `false`
  - blocker is the hardcoded real bridge scan approval switch
- Lane 2 external review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane1_lane2_full_review_pack_2026-05-31`
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane1_lane2_full_review_pack_2026-05-31.zip`
  - current status: `packed_with_blocks`
  - includes planning specs/research docs, Lane 1 provenance summaries, Lane 2
    component outputs, source, and tests
  - packed source closure includes `reference.py`, `fast_backend.py`,
    `bridge.py`, and `__init__.py`
  - supersedes the earlier
    `phaseB_ngram_hamming_bridge_lane2_prep_external_review_pack_2026-05-31.zip`
    and dependency-closure-only zip
- Lane 2 contract pack:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_contract_pack_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1`
  - profile manifest hash: `bc48b348d6afa6f0402514f6055cbe4ec33fb328e1b658144c67d4f812b85e28`
  - current status: schema/profile contract only, not a broad-run approval
- Lane 2 readiness checker:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/check_phaseB_ngram_hamming_bridge_lane2_readiness_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1`
  - current status: `pass`
  - bridge broad scan ready: `true`
- Lane 2 synthetic contract smoke:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1`
  - current status: `pass`, synthetic-only, no real candidate scan
- Lane 2 prep status index:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1`
  - current status: `blocked`, now includes the full raw provenance review-pack
    scaffold and launch decision record
- Lane 2 gated diagnostic scaffold:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1`
  - current status: `blocked`, real candidate scan started `false`
- Lane 2 input contract:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_input_contract_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1`
  - current status: `pass`, no real candidate scan
- Lane 2 prep bundle:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1`
  - current status: `pass`, copied files `31 / 31`

Do not launch until full raw provenance review:

- broad bridge scans
- full hard-pair report
- order-4 or order-5 expansion
- matched-null pilot that depends on the full raw bridge outputs
- production scoring changes

Current wording guard:

- Lane 1 closure does not approve Lane 2 real bridge diagnostics.
- Lane 1 closure does not approve production scorer changes.
- Order 4 is outside this Lane 1 asset tranche, not rejected.
- Order 5 diagnostics remain future diagnostic scope.
- Counts and log-counts remain diagnostic only.

## PhaseB scorer contract overlay - 2026-05-14

Current active scorer-development plan:

- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_plan_2026-05-14.md`
- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_implementation_start_plan_2026-05-14.md`

What changed:

- exact filtered n-gram v1 is closed as a valid negative for exact joined phrase
  scanning on damaged no-WLI candidates
- the next live line is robust word-structured n-gram Hamming coherence
- the approved v1 scorer is FWD-only, no-WLI, no-cap, and report-first
- the implementation start plan is approved with amendments before coding
- Slice 0 damage-source audit is now required before controlled `20-50%`
  damage-ladder claims
- it must use `rune_token_ids`, never `rune_key_hex`, for candidate scanning
- it must build an independent C++ backend after Python reference tests define
  the contract
- Slice 0, Slice 1, Slice 2, and the Python reference matcher are now
  implemented, with passing reference/tool tests
- the phrase-index builder produced `196680` entries under
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_phrase_index_v1`
- implementation review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_impl_review_pack_2026-05-14.zip`
- pack-level review passed with amendments, but code-level review was blocked
  because the first implementation pack omitted source/test contents
- pre-C++ amendments are now implemented, including profile eligibility summary
  and tiny bounded Python reference smoke
- replacement source-inclusive review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_impl_review_pack_2026-05-15.zip`
- source-level review passed with pre-C++ amendments
- the pre-C++ contract amendments are now implemented and packed:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_pre_cpp_contract_review_pack_2026-05-15.zip`
- C++ Slice 1 source is implemented, the optional `_ngram_hamming_fast`
  extension now builds locally, import verification passes, and synthetic
  C++/Python parity tests execute and pass
- C++ Slice 2 tiny real-index smoke now passes with `backend_impl=cpp_fast`,
  `python_fallback_allowed=false`, and exact parity against the Python reference
- fast real-index smoke review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_fast_real_index_smoke_review_pack_2026-05-29.zip`
- exact no-cap pilot design plan:
  - `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_exact_no_cap_pilot_design_plan_2026-05-29.md`
- exact no-cap pilot design review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_exact_no_cap_pilot_design_review_pack_2026-05-29.zip`
- C++ Slice 1 source review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_cpp_slice1_source_review_pack_2026-05-15.zip`

Immediate next step:

- pause for review of the exact no-cap pilot design before pilot runner
  implementation or launch

Do not start with the full hard-pair report. Required order is asset validation,
phrase index, Python reference matcher, reference tests, independent C++ backend,
backend parity tests, exact no-cap pilot, expanded pilot, then full hard-pair
report only after gates pass.

## Current immediate action

The active stream is now planning for:

- `stage35_resume_from_handoff_focus_family_rescue_v1`

Do not launch runtime from this runbook without a separate explicit launch
decision. If any proposed run is expected to take about an hour or more, ask
before launching it.

Current target order:

- `1111/search7005`
  - primary selector/rescue headroom target
- `1111/search7004`
  - secondary fragmentation target
- `1111/search7002`
  - control / proof-of-runner target

Known handoff/archive roots:

- `1111/search7005`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260412T053512632846Z__bench_solve_pipeline_no_wli__9557c0f/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7005/`
- `1111/search7004`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260412T031328680128Z__bench_solve_pipeline_no_wli__9557c0f/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7004/`
- `1111/search7002`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260428T035424021944Z__bench_solve_pipeline_no_wli__ee62083/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7002/`

Each listed handoff root currently has:

- `manifest.json`
- `stage2_resume.json`
- `stage3_prep.json`
- `stage35_seed_archive.json`

Planning note:

- `planning/projects/no_wli/20_active_plans/no_wli_stage35_resume_from_handoff_focus_family_rescue_plan_2026-04-29.md`

Completed static inventory:

- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_resume_from_handoff_focus_family_rescue_v1.py`
- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T043455Z__stage35_resume_from_handoff_focus_family_rescue_v1/`
- result:
  - `3 / 3` target rows feasible for static archive design
  - all required handoff files present
  - selected-row material complete:
    - `17 / 17` archive seed rows
  - existing late-stage entry point:
    - `artifact_resume.run_stage35_from_selected_trial_row`
  - no upstream recompute required by that entry point
  - selected-row headroom:
    - `1111/search7005`:
      - best selected `0.416` versus retained `0.372`
    - `1111/search7004`:
      - best selected `0.432` versus retained `0.423`
    - `1111/search7002`:
      - best selected `0.752` versus retained `0.754`
  - runtime launched:
    - `0`

Completed smoke preflight:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_v1.py`
- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T044610Z__stage35_resume_from_handoff_focus_family_rescue_v1__smoke_preflight/`
- target:
  - `1111/search7005`
- selected row:
  - `c9e69b90b779e318`
- selected source / lane:
  - `stage3_best_phaseB / anchor`
- smoke config:
  - `rounds = 0`
  - `seed_keep = 2`
  - `beam_width = 2`
  - `max_runtime_seconds = 30`
- smoke result:
  - retained:
    - `0.372`
  - selected row start:
    - `0.416`
  - smoke resume:
    - `0.416`
  - elapsed:
    - `1.485s`
  - progress events:
    - `3`
  - partial dumps:
    - `3`
  - real science runtime launched:
    - `0`

Recommended next:

- decide whether to launch the real `1111/search7005`
  selected-best-frontier micro-canary
- timing anchor:
  - retained `1111/search7005` Stage 3.5 follow-up took `1996.242s`
    (`33m16s`)
- proposed cap:
  - `3600s`
- stop condition:
  - stop after one bounded Stage 3.5 round or `3600s`, whichever comes first
- because the projected runtime with margin is close to the one-hour user
  guard, require explicit launch confirmation before starting it

Completed first real selected-row run:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_real_7005_v1.py`
- launch wrapper:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_resume_from_handoff_focus_family_rescue_real_7005_launch_2026-04-29.ps1`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_resume_from_handoff_focus_family_rescue_real_7005_2026-04-29.log`
- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T060445Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_v1__real_selected_best_frontier_one_round/`
- target:
  - `1111/search7005`
- selected row:
  - `c9e69b90b779e318`
- stop condition:
  - one bounded Stage 3.5 round completed
- cap:
  - none
- result:
  - retained:
    - `0.372`
  - selected start:
    - `0.416`
  - resume best:
    - `0.416`
  - delta versus retained:
    - `+0.044`
  - delta versus selected:
    - `+0.000`
  - accept reason:
    - `search_score_drop_guard_failed`
  - elapsed:
    - `2.991s`
  - evals:
    - `1470`

Recommended next after real `7005`:

- guard-selector follow-up is complete:
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1.py`
  - bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T145906Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/`
  - accepted resume best:
    - `0.422`
  - delta versus retained:
    - `+0.050`
  - delta versus selected-row start:
    - `+0.006`
  - accept reason:
    - `accepted_via_guard_passing_selector`
  - selected archive rank:
    - `2`
  - selected candidate:
    - `7068135ec036da03`
  - elapsed:
    - `6.361s`
- do not deepen `7005` immediately
- `7004` secondary confirmation is complete:
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1.py`
  - bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T150415Z__stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/`
  - retained:
    - `0.423`
  - selected start:
    - `0.432`
  - reported local top resume:
    - `0.425`
  - accept reason:
    - `search_score_drop_guard_failed`
  - selected:
    - `0`
  - elapsed:
    - `10.620s`
  - posthoc:
    - rank 6 `3b5b0ca607c51fbe` reached truth `0.438` but failed the
      search-score guard
  - current decision:
  - stop this exact strict guard-selector runtime shape
  - carry the branch as mixed positive:
    - `7005` accepted strict guard-selector improvement
    - `7004` showed a truth-positive local row blocked by the search-score
      guard
  - next work should be offline guard-relaxation/policy audit before any more
    runtime
- first offline guard-selector archive policy audit is complete:
  - extractor:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_guard_selector_archive_policy_audit_v1.py`
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T151026Z__stage35_guard_selector_archive_policy_audit_v1/`
  - cases:
    - `2`
  - archive rows:
    - `24`
  - accepted-positive cases:
    - `1 / 2`
  - cases with blocked truth-positive rows:
    - `1 / 2`
  - recommendation:
    - stop strict guard-selector runtime
    - only continue with broader offline guard-relaxation/policy analysis
- broader guard-relaxation archive data-taking run:
  - status:
    - completed
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_relaxation_archive_policy_long_audit_v1.py`
  - launch wrapper:
    - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_relaxation_archive_policy_long_audit_launch_2026-04-29.ps1`
  - terminal opener:
    - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_relaxation_archive_policy_long_audit_open_terminal_2026-04-29.ps1`
  - console log:
    - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_relaxation_archive_policy_long_audit_2026-04-29.log`
  - budget:
    - `28800s`
  - stop condition:
    - all discovered archive sources processed or wallclock budget reached
  - partial writeback:
    - every `5` sources
  - outcome:
    - `264 / 264` sources
    - `931` archive rows
    - `8.084s`
    - strict search-score guard remains best default
- broader selected-frontier runtime harvest:
  - status:
    - launching
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_selector_frontier_runtime_harvest_v1.py`
  - launch wrapper:
    - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_selector_frontier_runtime_harvest_launch_2026-04-29.ps1`
  - terminal opener:
    - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_selector_frontier_runtime_harvest_open_terminal_2026-04-29.ps1`
  - console log:
    - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_selector_frontier_runtime_harvest_2026-04-29.log`
  - budget:
    - `28800s`
  - per-cell cap:
    - `900s`
  - stop conditions:
    - queue exhausted
    - wallclock budget reached
    - first-cell serial projection exceeds budget
  - partial writeback:
    - after every cell

Current closed blockers:

- broad Phase-C saved-surface reshuffling is closed
- the six-job full-pipeline Stage-3 entry panel should not be rerun as-is
- the Stage2 checkpoint branch is review-ready but remains non-production and
  live-runtime blocked

## Immediate readout

The fixed `20`-job `p9/c3/l1000/no-WLI` panel is complete as a retained
benchmark basis.

Panel coverage:

- `v71`
  - original jobs `1-3`
- `v72a`
  - original jobs `4-5`
- `v72b`
  - original jobs `6-10`
- `v73`
  - original jobs `11-20`

Retained completion state:

- `20` completed-job bundles retained with:
  - `run_manifest.json`
  - `final_instances`
  - `best/best_instance.json`
- two non-panel residues remain:
  - interrupted local `v71` job-4 residue without `best/best_instance.json`
  - one stale `v72b` log reference to a non-retained path

Current benchmark read:

- `1511`
  - positive control
- `611`
  - middle unsolved case
- `1111`
  - conversion-failure case
- `1411`
  - useful but caveated cross-check case

The active stream is now:

- `fixed_instance_solver_development_v1`

Current next-branch read:

- upstream fixed-panel audit complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/`
- concrete selector audit complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/`
- selector sensitivity sweep complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/`
- selected-family handoff audit complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T031321Z__stage2_topk_selected_family_low_edge_handoff_audit_v1/`
- first exact selector replay complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- exact selector family matrix complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/`
- Phase-A competitiveness audit complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/`
- Phase-A rank-1 gate microprobe complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T023226Z__stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1/`
- branch result:
  - `advance`
- current interpretation:
  - `1111` already carries a better upstream family region
  - the main current issue is representative selection inside that region
  - the selector is now concrete:
    - family view:
      - `prefix_hamming_le_24`
    - policy:
      - `selected_family_low_edge_eps_0p016_v1`
  - the selector now also changes the saved Stage-3 handoff on `1111`
  - the exact-family execution read is now mixed:
    - clean exact win on `7003`
    - baseline-positive near win on `7005`
    - slight local loss on `7004`
    - severe collapses on `7001` and `7002`
  - the raw selector is therefore:
    - not uniformly exact-negative
    - not live-promotable
  - the split is now partly explained by an early Phase-A gate:
    - `phasea_rank1_init_match >= 0.30`
  - that gate is now also operationally meaningful:
    - `42.3` filtered saved attempt minutes
    - `0.961` filtered saved attempt share
  - that gate is now also persisted inside the replay bundle:
    - `resume_bundle/phasea_gate_snapshot.json`
  - the first cheap live-read canary is now preserved as the schema-gap
    finding on:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T034213Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
  - that canary proved the file write, but not yet the live decision surface:
    - snapshot file exists
    - gate metric fields were still `null`
    - snapshot timing was late at about `53m42s`
  - the patched `7004` live-read canary is now also complete on:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061020Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
  - that patched canary made the live surface usable:
    - `phaseA_rank1_init_match = 0.415`
    - verdict:
      - `keep`
    - snapshot share:
      - `0.878`
  - the bounded family follow-on is now complete:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1.py`
    - completed bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1/`
    - completed coverage:
      - `5 / 5`
    - machine recommendation:
      - `advance`
    - verdict match:
      - `5 / 5`
    - mean snapshot share:
      - `0.881`
  - the first explicit both-action microprobe is now complete:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1.py`
    - completed bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T161225Z__stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1/`
    - filtered `7002` canary:
      - verdict:
        - `filter`
      - action applied:
        - yes
      - fallback result:
        - retained baseline `0.754`
      - elapsed:
        - `01:09:52`
      - snapshot share:
        - `0.9996`
    - session result:
      - `stopped_over_budget`
      - `7003` not launched
  - current branch read:
    - live-read correctness is now validated
    - the first both-action canary shows the blocker is timing, not action
      choice
    - raw provisional `rank1` is now closed
    - the retained refinement audit and second-pair confirmation are now both
      closed
    - strict restart16 field persistence is also closed
    - the retained stabilization-window audit selected:
      - restart `32`
      - `phaseA_best_init_match >= 0.3865`
    - the first restart32 best-init action canary is now complete:
      - filtered `7001` saved real wallclock
      - kept `7005` stayed no-harm
    - the remaining-family restart32 best-init microbatch is also complete:
      - filtered `7002`
        - saved real wallclock
      - kept `7003`
        - stayed no-harm
      - kept `7004`
        - stayed no-harm on outcome but ran slower than its reference exact
          replay
    - the kept-`7004` timing postmortem audit is now also complete:
      - `7003` stays timing-stable under the same action wiring
      - `7004` first decides `keep` early at restart `32`
      - the slowdown is already visible by restart `64` and deep in Phase B
      - the anomaly does not read like a gate-logic failure
    - the selector checkpoint science is provisionally supported on fixed
      `1111/search7001-7005`
    - the first external-review pass blocked the package on provenance rather
      than science
    - that provenance blocker is now resolved:
      - reconciled family bundle:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T170754Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_reconciled_v1/`
      - hardened provenance audit:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T190612Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1/`
      - result:
        - review-ready after provenance reconciliation
    - live runtime remains blocked until a separate explicit canary decision is
      written
    - next branch is active planning only:
      - one filtered collapse-lane live canary preparation plan
      - preferred first cell:
        - fixed `1111/search7002`
      - max runtime:
        - `08:00:00`
      - plan:
        - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_plan_2026-04-25.md`
      - Day 2 preflight:
        - passed
        - bundle:
          - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T220602Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_preflight_v1/`
        - failed checks:
          - `none`
        - runtime launched:
          - `0`
      - launch wrapper:
        - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_open_terminal_2026-04-25.ps1`
      - Day 3 canary:
        - passed
        - source:
          - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T004304Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
        - audit:
          - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T012105Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1/`
        - row mismatch count:
          - `0`
      - no second canary until the Day 4 review decision is accepted
      - complementary kept/no-harm canary:
        - passed semantically and provenance-clean
        - source:
          - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T014422Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
        - audit:
          - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T021629Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1/`
        - timing caveat:
          - `+537.015s` versus retained exact replay reference
      - reconciliation is now complete:
        - semantic pass
        - provenance pass
        - kept-lane timing caveat
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_reconciliation_note_2026-04-26.md`
      - do not launch more checkpoint canaries from this branch
      - if continuing, open a separate timing-risk follow-up
      - timing-risk follow-up plan:
        - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_followup_plan_2026-04-26.md`
        - no runtime approved

The completed infrastructure stream is now frozen baseline background:

- `planning/projects/no_wli/20_active_plans/no_wli_fixed_instance_mode_infrastructure_plan_2026-04-08.md`
- `planning/projects/no_wli/30_analysis_specs/no_wli_fixed_instance_mode_v1_spec_2026-04-08.md`

## Active planning and contract

- current upstream audit plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_stage3_promoted_family_audit_plan_2026-04-22.md`
- current upstream audit note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_stage3_promoted_family_audit_note_2026-04-22.md`
- current representative-policy audit plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_family_representative_policy_audit_plan_2026-04-22.md`
- current representative-policy audit note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_family_representative_policy_audit_note_2026-04-22.md`
- current representative-policy sensitivity plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_family_representative_policy_sensitivity_plan_2026-04-22.md`
- current representative-policy sensitivity note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_family_representative_policy_sensitivity_note_2026-04-22.md`
- current selected-family handoff audit plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_handoff_audit_plan_2026-04-22.md`
- current selected-family handoff audit note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_handoff_audit_note_2026-04-22.md`
- completed execution microprobe plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_execution_microprobe_plan_2026-04-23.md`
- execution microprobe closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_closure_note_2026-04-23.md`
- completed execution microprobe bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- execution runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
- historical prepared execution launchers:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_launch_2026-04-23.ps1`
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_open_terminal_2026-04-23.ps1`
- exact-family matrix plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_plan_2026-04-23.md`
- exact-family matrix closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_closure_note_2026-04-23.md`
- exact-family matrix bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/`
- current Phase-A competitiveness audit plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_plan_2026-04-23.md`
- current Phase-A competitiveness audit note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_note_2026-04-23.md`
- current Phase-A competitiveness audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/`
- current Phase-A rank-1 gate microprobe plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_plan_2026-04-23.md`
- current Phase-A rank-1 gate microprobe note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_note_2026-04-23.md`
- current Phase-A rank-1 gate microprobe bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T023226Z__stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1/`
- current Phase-A gate persistence microprobe plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_persistence_microprobe_plan_2026-04-23.md`
- current Phase-A gate persistence microprobe note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_persistence_microprobe_note_2026-04-23.md`
- current Phase-A gate live-read canary note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_live_read_canary_1111_search7004_note_2026-04-24.md`
- current Phase-A gate live-read follow-on closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_closure_note_2026-04-24.md`
- current Phase-A gate live-read follow-on plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_plan_2026-04-23.md`
- current both-action microprobe plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_plan_2026-04-24.md`
- current both-action microprobe closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_closure_note_2026-04-24.md`
- current raw provisional earlier-emission closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_closure_note_2026-04-24.md`
- current checkpoint-refinement audit plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_plan_2026-04-24.md`
- current checkpoint-refinement audit note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_note_2026-04-24.md`
- current checkpoint-refinement confirmation plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_plan_2026-04-24.md`
- refined-checkpoint confirmation closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_closure_note_2026-04-24.md`
- strict field-persistence audit plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_plan_2026-04-24.md`
- strict field-persistence audit note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_note_2026-04-24.md`
- current stabilization-window audit note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_note_2026-04-24.md`
- current best-init window action microprobe plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_plan_2026-04-24.md`
- current best-init window action microprobe closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_closure_note_2026-04-24.md`
- current best-init window family microbatch plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_plan_2026-04-24.md`
- best-init window family microbatch closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_closure_note_2026-04-24.md`
- best-init window family microbatch output dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`
- best-init window timing postmortem audit plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_plan_2026-04-24.md`
- best-init window timing postmortem audit note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_note_2026-04-25.md`
- selector checkpoint subtopic synthesis note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_subtopic_synthesis_note_2026-04-25.md`
- selector checkpoint last-5 summary note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_last5_experiments_summary_2026-04-25.md`
- selector checkpoint review pack:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25/`
  - zip:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25.zip`
  - paired src bundle:
    - `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260425T191004Z.zip`
- selector checkpoint reconciliation plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_reconciliation_plan_2026-04-25.md`
- selector checkpoint first external-review note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_external_review_first_pass_note_2026-04-25.md`
- selector checkpoint family provenance audit note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_family_provenance_audit_note_2026-04-25.md`
- selector checkpoint final handoff archive note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_final_handoff_archive_note_2026-04-25.md`
- selector checkpoint live-canary preparation plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_plan_2026-04-25.md`
- review-pack method note:
  - `planning/projects/no_wli/20_active_plans/no_wli_review_pack_method_note_2026-04-25.md`
- completed failed `7004` live-read canary output dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T034213Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- completed patched `7004` live-read canary output dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061020Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- completed follow-on family output dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1/`
- completed both-action microprobe output dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T161225Z__stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1/`
- completed raw provisional earlier-emission bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1/`
- completed checkpoint-refinement audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T192446Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1/`
- completed refined-confirmation bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1/`
- refined-confirmation closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_closure_note_2026-04-24.md`
- completed strict field-persistence audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210520Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1/`
- strict field-persistence audit note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_note_2026-04-24.md`
- completed stabilization-window audit bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210839Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1/`
- best-init window action microprobe bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T211444Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1/`
- current best-init window family microbatch runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1.py`
- current best-init window family microbatch focused proof:
  - `tests/tools/test_no_wli_phasea_checkpoint_best_init_window_family_microbatch_v1.py`
- follow-on family runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1.py`
- both-action microprobe runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1.py`
- refined-confirmation runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1.py`
- best-init window action microprobe runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1.py`
- patched snapshot backfill:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- exact-family matrix runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1.py`
- exact-family matrix log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_2026-04-23.log`
- earlier-emission microprobe log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_2026-04-24.log`
- refined-confirmation microprobe log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_2026-04-24.log`
- best-init window action microprobe log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_2026-04-24.log`
- exact-family matrix launchers:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_launch_2026-04-23.ps1`
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_open_terminal_2026-04-23.ps1`
- latest closed probe plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_plan_2026-04-22.md`
- latest probe closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_closure_note_2026-04-22.md`
- prior paired-canary plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_canary_plan_2026-04-22.md`
- prior contingent follow-on plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_plan_2026-04-22.md`
- general runtime budgeting reference:
  - `planning/projects/no_wli/20_active_plans/no_wli_runtime_budgeting_reference_note_2026-04-20.md`
- current closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_phasec_richer_pool_replacement_reopen_closure_note_2026-04-22.md`
- current branch-point closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_phaseb_challenger_supply_retake_microbatch1_note_2026-04-21.md`
- prior active reopen plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_phasec_richer_pool_replacement_reopen_plan_2026-04-21.md`
- prior active supply retake plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_phaseb_challenger_supply_retake_plan_2026-04-20.md`
- prior operational closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_phaseb_challenger_supply_matrix_v1_operational_closure_note_2026-04-20.md`
- prior phase-B challenger supply matrix plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_phaseb_challenger_supply_matrix_plan_2026-04-19.md`
- prior closed saved-surface mass/frontload plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_phasec_saved_surface_phaseb_mass_and_frontload_matrix_plan_2026-04-18.md`
- prior late-pool closure basis:
  - `planning/projects/no_wli/20_active_plans/no_wli_late_candidate_pool_composition_plan_2026-04-18.md`
- prior solver-development basis:
  - `planning/projects/no_wli/20_active_plans/no_wli_fixed_instance_solver_development_plan_2026-04-14.md`
- authoritative contract:
  - `planning/projects/no_wli/30_analysis_specs/no_wli_fixed_instance_solver_development_v1_spec_2026-04-14.md`

## Frozen benchmark inputs

- main fixed-panel review pack:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- `1111` supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`
- cross-seed plus `1111` focus-family supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`

## Current baseline bundle

- current combined output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160503Z__fixed_instance_solver_development_v1/`
- generated files:
  - `panel_baseline_rows.jsonl`
  - `instance_summary_rows.jsonl`
  - `instance_search_matrix.csv`
  - `fixed_instance_solver_baseline_cases.md`
  - `1111_conversion_compare_rows.csv`
  - `1111_conversion_failure_audit.md`
  - `1511_positive_control_compare_rows.csv`
  - `1511_positive_control_audit.md`
  - `611_middle_case_compare_rows.csv`
  - `611_middle_case_audit.md`
  - `1411_caveat_and_use_note.md`
  - `candidate_solver_change_shortlist.md`
- this is now the frozen baseline digest plus the completed case audits and
  narrow candidate shortlist

## Current candidate verification bundle

- current candidate-1 retained replay output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160357Z__candidate1_guard_accept_611_search7005_replay_v1/`
- key files:
  - `candidate1_replay_comparison.json`
  - `candidate1_replay_comparison.md`
  - `candidate1_replay/stage35_summary.json`
- current read:
  - candidate 1 accept fires on retained `611/search7005`
  - `top_score_then_search` chooses archive rank `3` inside the score band
  - replay best match is `0.572`
  - that is below the original run best `0.585`
- use status:
  - do not run candidate 1 live in the current form

## Candidate 3 closure record

- active runtime proxy:
  - `phaseb_topk_anchor_swap_v1`
- canary preset:
  - `stage3_phasec_phaseb_topk_anchor_swap_p9`
- closure status:
  - operationally closed without promotion
  - closure note:
    - `planning/projects/no_wli/40_review_summaries/no_wli_candidate3_closure_decision_note_2026-04-18.md`
- whole-panel shadow bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T151927Z__candidate3_phasec_phaseb_topk_anchor_shadow_v1/`
- shadow read:
  - `19/20` retained runs can engage the anchor-swap rule
  - `11` engageable runs favor the first actual `phaseB_topk` start
  - `7` engageable runs favor the retained anchor
  - `1` engageable run is equal
- verifier cleanup now landed:
  - stage3-only exact replay summaries compare against the retained Stage-3
    reference, not just the artifact-level overall best
  - the one-hour `611/search7004` exact control attempt is preserved explicitly
    as insufficient
- first cleaned exact control:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T163546Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`
- control read:
  - retained Stage-3 reference `0.571`
  - replay best `0.435`
  - delta `-0.136`
- replay-fidelity audit on that control:
  - latest bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T153730Z__candidate3_exact_control_replay_fidelity_1511_search7004_v1/`
  - first unavailable retained surface:
    - none
  - first actual persisted mismatch:
    - `phaseB_downstream_selected_ordered_hashes`
- rerun exact control with patched replay surfaces:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T015030Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`
  - replay-side surface read:
    - `phaseB_downstream_selected_summaries = 32`
    - `phaseB_topk_saved_summaries = 1`
    - `phaseC_start_source_counts = {'stage3_best_phaseB': 1, 'phaseA_selected': 5}`
  - run-level read remains:
    - retained Stage-3 reference `0.571`
    - replay best `0.435`
    - delta `-0.136`
- current interpretation:
  - replay fidelity is not strong enough on this case to justify the matched
    candidate exact pass yet
  - the blocker is now explicit Phase-B surface drift before candidate3 acts,
    not a missing replay-side audit surface
- saved-surface verifier for the same case:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T052238Z__candidate3_phasec_saved_surface_1511_search7004_v1/`
  - stable saved-surface read:
    - candidate3 can engage on the exact saved Phase-C start surface
    - first distinct `phaseB_topk` start is rank `2`
    - saved-surface `phaseB_topk` minus anchor final match is `0.005`
  - scope:
    - stable per-case ordering reference only
    - not a fresh candidate replay
- saved-surface exact replay helper on the same case is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T054445Z__candidate3_phasec_saved_surface_exact_1511_search7004_v1/`
  - exact saved-surface read:
    - control reproduces retained `0.571`
    - candidate3 lands at `0.569`
    - candidate minus control is `-0.002`
    - control winner stays on retained `phaseB_topk` rank `2`
    - candidate winner shifts to `phaseB_topk` rank `3`
  - interpretation:
    - the narrowed Phase-C-only lane is stable enough to judge candidate3 on
      `1511/search7004`
    - on that exact saved-surface lane, candidate3 is a small negative
- four additional exact saved-surface checks now exist:
  - `611/search7004`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055021Z__candidate3_phasec_saved_surface_exact_611_search7004_v1/`
    - control `0.758`
    - candidate `0.758`
    - candidate minus control `0.000`
  - `611/search7001`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T152806Z__candidate3_phasec_saved_surface_exact_611_search7001_v1/`
    - control `0.381`
    - candidate `0.383`
    - retained Stage-3 reference `0.450`
    - candidate minus control `+0.002`
    - read:
      - small control-relative gain only
      - saved-surface control still misses the retained Stage-3 winner badly,
        so this is not a clean decision gate
  - `1111/search7002`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055755Z__candidate3_phasec_saved_surface_exact_1111_search7002_v1/`
    - control `0.750`
    - candidate `0.754`
    - retained Stage-3 reference `0.752`
    - candidate minus control `+0.004`
  - `1511/search7005`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T153047Z__candidate3_phasec_saved_surface_exact_1511_search7005_v1/`
    - control `0.686`
    - candidate `0.686`
    - retained Stage-3 reference `0.691`
    - candidate minus control `0.000`
    - read:
      - near-stable positive-control lane
      - candidate3 is neutral here
  - `1511/search7002`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7002_v1/`
    - control `0.842`
    - candidate `0.842`
    - retained Stage-3 reference `0.842`
    - candidate minus control `0.000`
    - read:
      - stable positive-control lane
      - candidate3 is neutral here
  - `1511/search7003`:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7003_v1/`
    - control `0.844`
    - candidate `0.844`
    - retained Stage-3 reference `0.845`
    - candidate minus control `0.000`
    - read:
      - near-stable positive-control lane
      - candidate3 is neutral here
  - remaining supported-case batch is now complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T041606Z__candidate3_phasec_saved_surface_exact_remaining_cases_v1/`
    - this closes the saved-surface exact lane across the full supported fixed
      panel
  - full supported exact-lane matrix:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T042939Z__candidate3_saved_surface_exact_matrix_v1/`
    - supported fixed-panel cases covered:
      - `19`
    - missing supported cases:
      - `0`
    - full usable-gate read:
      - positives `3`
      - neutrals `6`
      - negatives `1`
      - drifted context lanes `9`
    - per-instance usable-gate read:
      - `611`: `1` positive, `1` neutral
      - `1111`: `2` positives, `1` neutral
      - `1411`: `1` neutral
      - `1511`: `3` neutrals, `1` negative
    - updated interpretation:
      - candidate3 is no longer just an `1111`-only effect
      - the clean new non-`1111` usable positive is `611/search7003`
      - the total panel read is still mixed and not strong enough for live
        promotion
  - local policy-variant exploration is now complete on the exact
    saved-surface lane:
    - bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T043706Z__phasec_saved_surface_policy_variants_v1/`
    - compared policies:
      - `phaseb_topk_anchor_swap_v1`
      - `phaseb_topk_frontload_two_v1`
      - `phaseb_topk_frontload_all_v1`
    - one-seed usable-gate read:
      - anchor-swap:
        - `3` positives
        - `6` neutrals
        - `1` negative
      - frontload-all:
        - `4` positives
        - `4` neutrals
        - `2` negatives
      - frontload-two:
        - `2` positives
        - `6` neutrals
        - `2` negatives
    - interpretation:
      - `phaseb_topk_frontload_all_v1` is the strongest nearby local variant
      - it beats anchor-swap on `4` usable gates and loses on `2`
      - it especially improves `1511/search7002`, `1511/search7005`, and
        `1111/search7004`
      - it clearly hurts `611/search7003` and `611/search7004`
  - retained-seed robustness sweep is now complete on the most informative
    usable lanes:
    - bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T052352Z__phasec_saved_surface_policy_seed_sweep_v1/`
    - cases swept:
      - `611/search7003`
      - `1111/search7004`
      - `1511/search7003`
      - `1511/search7004`
      - `1511/search7005`
    - seed offsets:
      - `-2,-1,0,1,2`
    - sweep summary:
      - anchor-swap mean delta vs control:
        - `-0.002`
      - frontload-all mean delta vs control:
        - `+0.001`
      - frontload-two mean delta vs control:
        - `-0.003`
    - robustness interpretation:
      - `phaseb_topk_frontload_all_v1` looks stronger than anchor-swap in this
        retained-seed sweep, but still not robust enough to promote directly
      - it wins the retained seed on `1111/search7004` and `1511/search7005`
        and stays competitive on some nearby seeds
      - anchor-swap stays clearly best on `611/search7003`
      - policy preference is still case- and seed-dependent rather than cleanly
        dominant
  - closure interpretation:
    - candidate3 exact saved-surface evidence is mixed and small-effect
    - candidate3 is not blocked mainly by replay fidelity anymore on the
      narrowed saved-surface lane
    - candidate3 remains a narrow positional reorder probe rather than an
      established solver improvement
    - candidate3 is operationally closed without promotion
    - do not schedule another broad replay batch or a final narrow
      confirmation run
    - next honest move is a new paradigm or a consciously designed conditioned
      rule, not another blind live run
- do not start any candidate 3 live runtime
- for long candidate3 investigations, prefer the pop-out launch path:
  - runner:
    - `planning/projects/no_wli/60_launch_scripts/no_wli_candidate3_long_investigation_launch_2026-04-18.ps1`
  - window launcher:
    - `planning/projects/no_wli/60_launch_scripts/no_wli_candidate3_long_investigation_open_terminal_2026-04-18.ps1`

## Next-phase transition note

Candidate 3 is now closed without promotion.

The downstream late candidate-pool composition line is also closed in its first
two forms:

- saved-pool replacement / eviction matrix:
  - `close`
- saved-surface `phaseB_topk` mass and frontload matrix:
  - `close`

Carry-forward read:

- reorder-only controls stayed the only line with small positive signal
- downstream quota and `phaseB_topk`-only replacement stayed structurally
  blocked because there were no spare eligible retained `phaseB_topk`
  challengers outside the selected set
- the next honest mechanism question therefore moves upstream into Phase-B
  challenger supply

Operational rule from this point:

- no more downstream late-pool composition batches are authorized unless the
  upstream supply study creates real spare retained `phaseB_topk` challengers
- runtime remains the scarce overnight resource
- every overnight batch must still end in one of:
  - promote
  - refine
  - close

## Current upstream supply branch result

The saved-surface `phaseB_topk` mass and frontload line is now closed.

Closure read:

- frontload depth stayed active but did not beat the reorder controls
- the quota family was already structurally satisfied on most cases
- when quota was not already satisfied, there were still zero eligible
  non-selected retained `phaseB_topk` challengers
- the `phaseB_topk`-only replacement family was structurally blocked for the
  same reason

That means the next active mechanism question moves upstream:

- can wider or deeper Phase-B saved challenger supply create real spare
  non-selected `phaseB_topk` challengers for downstream Phase-C use?

Operational status:

- the original `phaseb_challenger_supply_matrix_v1` serial matrix is now closed
  as an operational failure of batch sizing
- rescued valid data from the completed `611/search7002` canary are retained
- the one-job retake microbatch is now also complete:
  - `1111/search7002`
  - `phaseb_supply_selected24_saved64_stage3only_v1`
  - extracted readout:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260421T145900Z__phaseb_challenger_supply_retake_microbatch_v1/`

Microbatch read:

- real spare non-selected retained `phaseB_topk` challengers:
  - `14`
- duplicate non-selected retained `phaseB_topk` challengers:
  - `0`
- replacement engageable:
  - `1`
- quota engageable:
  - `0`
- top-line best-match delta versus retained:
  - `-0.004`
- elapsed runtime:
  - about `18.82h`

Branch interpretation:

- the upstream supply suspicion is validated on this richer pool
- the result is scientifically useful but too expensive to justify another
  immediate deeper supply retry
- the next active line therefore moves to a richer-pool downstream replacement
  reopen on the saved-surface exact lane

### Required pre-run block

Before any overnight batch in this solver-development line, write all of these:

- Question
- Suspicion
- Main alternative
- If suspicion is true, expect
- If alternative is true, expect
- Tomorrow's decision rule

Also write one explicit mechanism-layer claim:

- supply
- selection
- ordering
- allocation
- or local search / rescue

### Runtime v1 shape

The full conceptual runtime grid is not an honest one-night serial batch on
this machine.

So the active `v1` runtime slice is explicitly bounded:

- fixed-panel slice:
  - primary trio only
  - `611`
  - `1111`
  - `1511`
  - retained search seeds:
    - `7002`
    - `7004`
- Stage 3.5:
  - off
- downstream Phase-C policy:
  - unchanged control lane
- active presets:
  - `phaseb_supply_selected24_saved16_stage3only_v1`
  - `phaseb_supply_selected24_saved64_stage3only_v1`
  - `phaseb_supply_selected48_saved96_stage3only_v1`

### Runtime batch contract

This runtime batch must answer:

- whether any config creates spare non-selected retained `phaseB_topk`
  challengers
- whether quota or `phaseB_topk`-only replacement would now become genuinely
  engageable
- whether wider supply mostly adds new unique material or only archives more
  duplicates

Required outputs:

- one machine-readable per-config summary table
- one machine-readable per-case per-config table
- one short human readout
- one explicit promote / refine / close recommendation

### Operational gate

Before treating an overnight matrix as scientifically readable, verify all of
these:

- expected job count is explicit in the plan
- the first progress event appears in the run events log
- matrix run state increments beyond `0` completed jobs
- at least one child run leaves `running` and writes normal completion artifacts

If these gates are not met, the run is still in operational closure rather than
scientific branching.

### Most recent runtime canary

The richer-pool downstream replacement reopen is now closed:

- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260422T015033Z__phasec_richer_pool_phaseb_replacement_reopen_v1/`
- result:
  - `close`
- floor read:
  - `phaseb_topk_frontload_all_v1` reached `0.754`
- replacement read:
  - widths `1-3` all stayed at `0.750`
  - active surface changes without winner change

That means the held next branch had opened as:

- fixed-cell Stage-3 entry allocation canary
- preserve bounded Stage 3.5
- change only Stage-3 entry allocation

Scientific-method role:

- downstream ordering and richer-pool replacement have already been closed
- the next honest falsification step therefore moves one mechanism layer
  upstream:
  - `allocation`
- preserve the bounded late stack as the trusted baseline
- change only Stage-3 entry allocation so the live result is interpretable as a
  one-layer mechanism test rather than a mixed-runtime package

Current repo-state runtime status:

- no active multi-hour no-WLI runtime is currently confirmed
- current active branch is offline:
  - upstream representative-selection diagnosis from frozen fixed-panel evidence

Most recent runtime target:

- `1111/search7004`

Rule used for the closed paired canary:

- do not treat `1111/search7002` as the cheap default follow-up cell
- keep the first new-family session to a same-cell two-job compare
- stop after the first completed job if the projected two-job total already
  overruns the intended `~8h` session budget materially

Paired-canary presets:

- control:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- candidate:
  - bounded baseline carry-forward with:
    - `force_stage3_init_keys_cap = 288`
    - `force_stage3_entry_allocation_policy = "constant_local_depth"`
    - `force_stage3_entry_mutations_per_promoted = 1`

Why this cell:

- retained fixed `1111/search7004` runtime is about `2.36h`
- it keeps the focus on the main `1111` conversion-failure family
- it avoids the now-heavy `1111/search7002` timing class

What that paired canary had been expected to teach:

- whether `1111` still looks entry-budget-starved even after preserving the
  bounded Stage 3.5 late stack
- whether widening Stage-3 entry can create a better late-route outcome on a
  stable fixed lane
- whether the candidate really widens executed entry counts rather than only
  changing configured intent

Operational outcome:

- experiment id:
  - `tune_v76_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_compare_2job`
- the live process was killed intentionally after the run had already failed the
  intended two-job session shape
- the matrix wrapper never advanced beyond:
  - `job_started`
  - `completed_jobs = 0 / 2`
- no completed-job artifacts were written
- the candidate never ran

Rescued partial evidence:

- child run dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T024910116301Z__bench_solve_pipeline_no_wli__ee62083/`
- completed Phase-C starts before kill:
  - `5 / 6`
- watcher-log last line before kill:
  - Phase C start `6 / 6`, step `73 / 96`
- best rescued control read:
  - source:
    - `stage3_best_phaseA`
  - final match:
    - `0.432`
  - final score:
    - `0.17955717672334726`
- partial scientific read:
  - control fidelity looked good against the retained `1111/search7004`
    anchor family
  - but the two-job canary shape did not complete honestly enough to act as a
    branch decision unit
- operational closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_fixed_canary_operational_closure_note_2026-04-22.md`

Contingent queued follow-on:

- closed non-launch target:
  - fixed `1111/search7005`
- queue watcher log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_queue_2026-04-22.log`
- final queue read:
  - `queue_aborted reason=cutoff_reached_before_current_completed`
- result:
  - `1111/search7005` did not launch

Current branch rule after the kill:

- do not relaunch the same two-job live canary shape
- do not call the allocation hypothesis negative from this session, because the
  candidate never ran
- carry forward the rescued partial control evidence only
- rescope the next live unit to an independently complete one-job probe, or
  step cheaper first with offline / saved-surface / shadow gates

### Current upstream selector result

The upstream promoted-family audit is now complete.

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/`

Result:

- `advance`

Main read:

- primary family view:
  - `prefix_hamming_le_24`
- `1111` mean `stage2_topk` within-family gap:
  - `0.070`
- `1111` mean `stage2_promoted` within-family gap:
  - `0.070`
- `1111` mean `stage2_promoted` between-family gap:
  - `0.014`
- control means on promoted within-family gap:
  - `611`:
    - `0.000`
  - `1511`:
    - `0.000`

Interpretation:

- the current `1111` upstream issue is not mainly missing family diversity
- the current `1111` upstream issue is representative selection inside an
  already-present family region
- the next branch should be a small upstream representative-selection
  microprobe

Operational rule from this point:

- do not schedule another generic family-diversity or entry-allocation runtime
  before the representative-selection microprobe is specified

### Current concrete selector audit result

The first concrete `stage2_topk` representative-policy audit is now complete.

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/`

Result:

- `advance`

Policy:

- `selected_family_low_edge_eps_0p020_v1`

Main read:

- `1111` candidate active runs:
  - `5 / 5`
- `1111` oracle-match runs:
  - `5 / 5`
- `1111` mean candidate truth delta vs baseline:
  - `+0.070`
- controls stayed inert:
  - `611`
  - `1411`
  - `1511`

Interpretation:

- the representative-selection story is now concrete, not just diagnostic
- the remaining issue is whether the selector is narrow and robust enough to
  carry into a microprobe

### Current selector sensitivity result

The family-view and score-band sensitivity sweep is now complete.

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/`

Result:

- `advance`

Chosen next branch:

- `stage2_topk_selected_family_low_edge_eps_0p016_microprobe`

Chosen policy:

- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

Main read:

- only `prefix_hamming_le_24` yields a clean `1111`-only activation window
- under that view:
  - `eps = 0.015`
    - harmful on `1111`
    - mean delta `-0.023`
  - `eps = 0.016`
    - smallest clean positive
    - mean delta `+0.070`
  - `eps = 0.020`
    - still clean positive
    - mean delta `+0.070`
  - `eps = 0.025`
    - over-widens and attenuates
    - mean delta `+0.005`
- controls stay inert through the whole sweep

Operational rule from this point:

- do not describe the next branch vaguely as "representative selection"
- do not widen back to generic family-diversity or entry-allocation work
- carry forward the concrete selector only:
  - `prefix_hamming_le_24`
  - `selected_family_low_edge_eps_0p016_v1`

### Current selected-family handoff audit result

The saved handoff audit for the narrowed selector is now complete.

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T031321Z__stage2_topk_selected_family_low_edge_handoff_audit_v1/`

Result:

- `advance`

Main read:

- `1111`:
  - `best2_key_changed_run_count = 5`
  - `init3_changed_run_count = 5`
  - mean `init3_edit_count = 7.8`
  - mean `stage3_promoted_keys_edit_count = 7.8`
- controls:
  - `611`: all zero
  - `1411`: all zero
  - `1511`: all zero

Interpretation:

- the concrete selector is not a saved-handoff no-op
- another offline selector sweep was lower-value than an execution test
- that first execution test is now complete below

### Current exact selector execution microprobe result

The first exact replay for the narrowed selector is now complete.

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`

Result:

- `close`

Main read:

- completion:
  - `attempt_status.json`
  - `status = "completed"`
  - `elapsed = "01:07:53"`
- run summary:
  - `baseline_best_match_ratio = 0.423`
  - `retained_stage3_reference_match_ratio = 0.432`
  - `resume_best_match_ratio = 0.420`
  - `match_delta_vs_baseline = -0.003`
  - `match_delta_vs_retained_stage3_reference = -0.012`
- selector handoff gain:
  - baseline row truth `0.091`
  - candidate row truth `0.161`
  - delta `+0.070`
- strongest challenger lane:
  - start `2`
  - source:
    - `phaseA_selected`
  - init `0.415`
  - final `0.420`
  - `became_global_best = 1`
  - `overtook_anchor = 1`

Interpretation:

- the selector is execution-active, not inert
- the selector can create a strong challenger lane
- the exact replay still did not beat either comparison floor
- this first exact gate is therefore a clean negative, not an ambiguous stall

Repo-native logging read:

- the replay now persists enough in-app progress to inspect or stop from IDE
  runs without an external launcher
- verified files:
  - `attempt_status.json`
  - `resume_bundle/stage3_resume_status.json`
  - `resume_bundle/stage3_resume_progress.jsonl`
  - `resume_bundle/phasec_start_checkpoints.jsonl`

Next honest move:

- that first exact gate justified the bounded exact-family matrix rather than a
  live runtime
- that matrix is now complete below

### Current exact selector family-matrix result

The fixed `1111/search7001-7005` exact replay matrix is now complete.

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/`

Result:

- `refine`

Main read:

- completion:
  - `matrix_run_state.json`
  - `status = "completed"`
  - `completed_jobs = 5`
  - `elapsed = "01:52:14"`
- summary:
  - `selected_family_low_edge_exact_replay_1111_matrix_summary.json`
  - `clean_win_count = 1`
  - `baseline_win_count = 2`
  - `family_mean_delta_vs_baseline = -0.121`
  - `best_search_seed = 7003`
  - `best_delta_vs_baseline = 0.068`
  - `best_delta_vs_retained_stage3_reference = 0.153`
- per-seed rows:
  - `selected_family_low_edge_exact_replay_1111_matrix_rows.csv`
  - `7003`
    - baseline `0.408`
    - retained `0.323`
    - replay `0.476`
    - clean exact win
  - `7005`
    - baseline `0.372`
    - retained `0.416`
    - replay `0.413`
    - baseline-positive near win
  - `7004`
    - baseline `0.423`
    - retained `0.432`
    - replay `0.420`
    - slight local loss
  - `7001`
    - replay `0.161`
    - delta vs baseline `-0.267`
    - severe collapse
  - `7002`
    - replay `0.310`
    - delta vs baseline `-0.444`
    - severe collapse

Interpretation:

- the selector is not uniformly exact-negative across the fixed `1111` family
- the selector is also not usable as an unconditional solver rule
- the same saved-row truth gain can produce:
  - a clean exact win
  - a near win
  - or a catastrophic collapse

Next honest move:

- do not launch a live runtime on the raw selector line
- do not rerun another unconditioned replay family by habit
- the explanatory audit is now complete below

### Current Phase-A competitiveness audit result

The early Phase-A competitiveness audit is now complete.

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/`

Result:

- `advance`

Main read:

- recommendation payload:
  - `stage2_topk_selected_family_low_edge_phasea_competitiveness_summary.json`
  - best gate:
    - `rank1_init_ge_0p30`
  - metric:
    - `phasea_rank1_init_match`
  - next branch:
    - `stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe`
- per-seed split:
  - `7001`
    - `phasea_rank1_init_match = 0.254`
    - `local_search_collapse_after_phasea`
  - `7002`
    - `phasea_rank1_init_match = 0.289`
    - `phasea_competitiveness_below_floor`
  - `7003`
    - `phasea_rank1_init_match = 0.490`
    - `clean_exact_positive`
  - `7004`
    - `phasea_rank1_init_match = 0.415`
    - `competitive_near_floor`
  - `7005`
    - `phasea_rank1_init_match = 0.395`
    - `baseline_positive_near_retained`
- best threshold row:
  - kept seeds:
    - `7003,7004,7005`
  - filtered seeds:
    - `7001,7002`
  - kept mean delta vs baseline:
    - `+0.035`
  - counterfactual family mean delta vs baseline:
    - `+0.021`
  - `filters_all_hard_collapses = 1`
  - `keeps_all_noncatastrophic = 1`

Interpretation:

- the selector split is already partly visible from an early Phase-A signal
- the two worst lanes are not the same failure mode:
  - `7001` is weak at Phase A and then collapses further in local search
  - `7002` is already below a usable competitiveness floor
- that gate microprobe is now complete below

### Current Phase-A rank-1 gate microprobe result

The operational gate microprobe is now complete.

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T023226Z__stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1/`

Result:

- `advance`

Main read:

- summary payload:
  - `stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_summary.json`
  - gate:
    - `rank1_init_ge_0p30`
  - next branch:
    - `stage2_topk_selected_family_low_edge_phasea_rank1_gate_persistence_microprobe`
  - counterfactual family mean delta vs baseline:
    - `+0.021`
  - counterfactual family mean delta vs retained:
    - `+0.030`
  - filtered saved attempt minutes total:
    - `42.3`
  - filtered saved attempt share:
    - `0.961`
  - mean gate proxy elapsed:
    - `52.8s`
- counterfactual kept / filtered split:
  - filtered:
    - `7001`
    - `7002`
  - kept:
    - `7003`
    - `7004`
    - `7005`

Interpretation:

- the gate is not just explanatory
- on the known bad lanes it would have avoided most of the paid exact-replay
  wallclock
- the next honest branch is now to make the gate inspectable and actionable
  during real runs, not to launch another replay family

### Closed one-job probe

The one-job `1111/search7004` allocation probe is now closed.

Closed experiment:

- experiment id:
  - `tune_v78_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_probe_1job`
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1.py`
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1.py`
- launchers:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_launch_2026-04-22.ps1`
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_open_terminal_2026-04-22.ps1`
- child run dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T154043010456Z__bench_solve_pipeline_no_wli__ee62083/`

Result:

- process stopped after the written `~8h` stop rule had been exceeded
- no normal completion artifacts were written
- completed Phase-C starts before stop:
  - `4 / 6`
- best completed start:
  - final match `0.432`
  - final score `0.17955717672334726`
- retained mapped-family max on fixed `1111/search7004`:
  - final match `0.432`

Scientific read:

- the probe reproduced the retained anchor-family best
- it did not show a new top-line lift
- the other completed starts were weaker:
  - `0.413`
  - `0.399`
  - `0.411`
- the partial bundle was already low-information:
  - `3 / 4` completed starts had `shadow_stop_v1.plateau_would_stop = 1`

Structural read:

- this exact config could widen Stage-3 entry by at most:
  - `+2` keys over legacy
- so the configured cap `288` was irrelevant
- this was not an honest strong test of entry-budget starvation on this cell

Decision:

- close this exact probe shape
- do not rerun the same `constant_local_depth` runtime on `1111/search7004`
- do not preserve the contingent `1111/search7005` replication gate from this
  branch
- require a written structural-activation proof before any future allocation
  runtime

### Runtime budgeting reference

Before sizing any new multi-hour no-WLI runtime launch, look here first:

- `planning/projects/no_wli/20_active_plans/no_wli_runtime_budgeting_reference_note_2026-04-20.md`

That note points to:

- the broad runtime history ledger
- the fixed-panel wallclock reference

and it must be refreshed when newly completed multi-hour runs materially change
the retained timing picture.

Current timing caution:

- `1111/search7002` is no longer a safe "cheap" default cell once the config
  family changes
- the widened-supply retake stretched that exact cell to about `18.81h`
- do not schedule a new `search7002` runtime follow-up if the real target is
  about `8h`

### Required outputs for every overnight batch

Every overnight batch must produce:

- one machine-readable summary table
- one case-level delta table
- one short human readout
- one explicit promote / refine / close recommendation

## Immediate work order

1. Baseline digest complete.
   - output bundle:
     - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160503Z__fixed_instance_solver_development_v1/`
2. `1111` conversion-failure audit complete.
   - required outputs:
     - `1111_conversion_compare_rows.csv`
     - `1111_conversion_failure_audit.md`
3. `1511` positive-control audit complete.
   - generated outputs:
     - `1511_positive_control_compare_rows.csv`
     - `1511_positive_control_audit.md`
4. `611` middle-case audit complete.
   - generated outputs:
     - `611_middle_case_compare_rows.csv`
     - `611_middle_case_audit.md`
5. `1411` caveat note complete.
   - generated output:
     - `1411_caveat_and_use_note.md`
6. Controlled solver-change shortlist complete.
   - generated output:
      - `candidate_solver_change_shortlist.md`
7. Candidate 1 retained replay complete.
   - verification output:
     - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160357Z__candidate1_guard_accept_611_search7005_replay_v1/`
   - readout:
     - stage35-only accepted row replays to `0.572`, below original run best
       `0.585`
     - run-level no-harm projection keeps the final best at retained
       `stage3_full_refine / 0.585`
     - `projected_stage35_used_for_final_best = 0`
8. Candidate 1 review cleanup complete.
   - `NaN` stage35 truth does not auto-promote stage35 to final best
   - selector-rescued accepts are explicit in telemetry
9. Candidate 2 core hook started.
   - runtime proxy:
     - `reinforce_top_family_v1`
   - preset:
     - `stage3_phaseb_top_family_reinforce_p9`
   - current status:
      - synthetic Phase-B reallocation tests pass
      - runtime-contract canaries pass
      - saved-pool retained shadow verification complete
10. Candidate 2 current line closed in two forms.
    - first form exact-retained read:
      - longer-timeout exact retained replays now exist on `611/search7005` and
        `1111/search7004`
      - `phaseB_family_reservation_applied = 0` on both tested candidate runs
      - matched exact control on `611/search7005` also lands at `0.535`
      - whole-panel selected-surface diagnostic:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T064934Z__candidate2_phaseb_selected_surface_v1/`
        - `20/20` retained runs show `32` selected rows and `32` preserved
          families
        - engageable retained runs under the current lever: `0`
    - replacement form shadow read:
      - policy:
        - `anchor_family_reserved_v1`
      - preset:
        - `stage3_phasec_anchor_family_reserved_p9`
      - whole-panel shadow bundle:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T145401Z__candidate2_anchor_family_reserved_shadow_v1/`
      - retained panel read:
        - `19/20` runs have saved Phase-C candidate-pool surface
        - runs with saved anchor-family room: `0`
        - replacement candidate2 shadow live on panel: `0`
    - do not start any live runtime changes on candidate 2 in either current
      form
    - choose a new narrow candidate instead of extending the blocked
      candidate2 line
11. Candidate 3 whole-panel shadow, exact coverage, local follow-up sweeps, and closure review complete.
    - closed line:
      - `phaseb_topk_anchor_swap_v1`
    - current whole-panel shadow bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T151927Z__candidate3_phasec_phaseb_topk_anchor_shadow_v1/`
      - `19/20` runs engageable
      - `11` favor first actual `phaseB_topk` start
      - `7` favor retained anchor
      - `1` equal
    - full supported exact matrix:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T042939Z__candidate3_saved_surface_exact_matrix_v1/`
      - usable-gate read:
        - positives `3`
        - neutrals `6`
        - negatives `1`
        - drifted context lanes `9`
    - local policy-variant matrix:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T043706Z__phasec_saved_surface_policy_variants_v1/`
      - strongest nearby local variant:
        - `phaseb_topk_frontload_all_v1`
    - retained-seed sweep:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T052352Z__phasec_saved_surface_policy_seed_sweep_v1/`
      - mean deltas vs control:
        - anchor-swap `-0.002`
        - frontload-all `+0.001`
        - frontload-two `-0.003`
    - closure read:
      - candidate3 is mixed, narrow, and not promotable
      - candidate3 is operationally closed without promotion
      - do not run another broad overnight replay batch or a final narrow
        confirmation run
      - decision note:
        - `planning/projects/no_wli/40_review_summaries/no_wli_candidate3_closure_decision_note_2026-04-18.md`
      - carry forward the saved-surface exact-lane lesson into the next
        paradigm rather than extending candidate3 as an open runtime line
12. Stage 3.5 resume-from-handoff local-rescue branch is active.
    - broad shallow frontier harvest:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/`
      - completed `136 / 136` cells in `721.112s`
      - found `73` accepted positives and `18` accepted regressions
      - rank-6 slice is the current promising target:
        - `19 / 22` positives
        - `0 / 22` negatives
        - best delta `+0.458`
    - completed next run:
      - focused deepening harvest over strongest shallow-positive cells
      - runner:
        - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_selector_frontier_deepening_harvest_v1.py`
      - console log:
        - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_selector_frontier_deepening_harvest_2026-04-29.log`
      - budget:
        - `8h`, `36` max cells, `1800s` per-cell cap
      - stop:
        - queue exhausted, wallclock cap reached, or first-cell projection
          over budget
    - current recommendation:
      - do not promote unfiltered guard-selector
      - use focused deepening to decide whether the rank-6/local-rescue slice
        deserves a narrower policy branch
    - completed deepening result:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/`
      - completed `15 / 15` cells in `1919.390s`
      - `12 / 15` better than shallow
      - `3 / 15` worse than shallow
      - mean delta versus shallow `+0.007533`
      - mean delta versus retained anchor `+0.004533`
    - updated recommendation:
      - do not rerun the same broad deepening shape immediately
      - build an offline shallow-plus-deepening join/dedup extractor and
        characterize safe rank-6 conditions before any more runtime
    - completed join/dedup extractor:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/`
      - `14` unique joined rows
      - `11 / 14` better than shallow
      - `3 / 14` worse than shallow
      - rank `6`: `10 / 12` better, `2 / 12` worse
      - best posthoc non-seed gate:
        - `rank6_selected_start_ge_0p437`
        - `6 / 6` better
        - `0 / 6` worse
    - current instruction:
      - no broad runtime
      - design the rank-6 selected-start safety rule offline first
    - completed selected-start safety extractor:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T014439Z__stage35_rank6_selected_start_gate_safety_v1/`
      - rank `6` plus `selected_start_match_ratio >= 0.437`
      - kept deep rows: `6`
      - kept better/worse: `6 / 0`
      - rejected better/worse: `4 / 2`
      - removed observed rank-6 deepening regressions: `2 / 2`
      - rejected real deepening positives: `4`
    - updated instruction:
      - do not canary this exact gate as-is
      - write a predeclared softened or combined policy sketch offline first
      - carry the prediction ledger forward and compare against it in chat
        when the analysis branch closes
    - completed policy sketch:
      - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_local_rescue_policy_sketch_2026-04-30.md`
      - candidate:
        - rank `6`
        - `selected_start_match_ratio >= 0.437`
        - or `shallow_resume_minus_selected >= 0.400`
      - observed dedup result:
        - kept `7`
        - kept better/worse `7 / 0`
        - rejected better/worse `3 / 2`
      - next action:
        - write a canary design note before any runtime
    - completed canary design:
      - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_local_rescue_canary_design_2026-04-30.md`
      - four cells:
        - `1511/search7004 rank 6 51b7dab086e94186`
        - `1111/search7002 rank 6 74dfe3cb559629f7`
        - `1111/search7004 rank 6 511a29668b8c44d1`
        - `1411/search7005 rank 6 b47e22bc63e7c189`
      - budget if approved:
        - `45m`, hard cap `2700s`, per-cell rescue cap `600s`
      - current instruction:
        - no runtime launched
        - implement/run only with explicit approval
    - approved canary launch:
      - runner:
        - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_local_rescue_canary_v1.py`
      - console log:
        - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_canary_2026-04-30.log`
      - budget:
        - `45m`, hard cap `2700s`, per-cell rescue cap `600s`
      - progress/partials:
        - after every cell
      - result:
        - completed `4 / 4` cells in `183.535s`
        - executed rescue cells `2`
        - policy skips `2`
        - errors `0`
        - policy decision mismatches `0`
        - executed cells nonnegative versus shallow `2 / 2`
      - current recommendation:
        - do not broaden directly
        - next runtime, if any, should be a small same-rule recall/audit
          microbatch around rejected-positive boundary behavior
    - current recall/audit launch:
      - runner:
        - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_local_rescue_recall_audit_v1.py`
      - console log:
        - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_recall_audit_2026-04-30.log`
      - budget:
        - `45m`, hard cap `2700s`, per-cell rescue cap `600s`
      - progress/partials:
        - after every cell
      - result:
        - completed `5 / 5` cells in `354.964s`
        - errors `0`
        - audit positives versus shallow `3`
        - audit regressions versus shallow `2`
        - reproduced prior deepening exactly `5 / 5`
      - current recommendation:
        - stop runtime
        - run an offline boundary-feature extractor before changing policy or
          launching more cells
    - completed boundary-feature audit:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T032952Z__stage35_rank6_boundary_feature_audit_v1/`
      - revision note:
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_boundary_rule_revision_note_2026-04-30.md`
      - result:
        - `0` perfect one-feature separators across `27` numeric features
      - current instruction:
        - stop runtime on this branch
        - do not promote the softened rule
        - only continue with offline feature expansion
    - completed route-lineage boundary audit:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T033637Z__stage35_rank6_route_lineage_boundary_audit_v1/`
      - review note:
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_boundary_review_note_2026-04-30.md`
      - result:
        - `0` perfect single-feature separators
        - `141` perfect two-feature separators on the five-row boundary set
      - preferred hypothesis:
        - candidate source rank `1`
        - high route novelty, e.g.
          `candidate_novelty_distance_to_anchor >= 173.5`
      - current instruction:
        - wait for external review
        - do not launch runtime
        - do not promote the route-lineage separator
        - if review accepts the mechanism, write a tiny
          held-out/disagreement confirmation design first
      - review pack:
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_review_pack_2026-04-30/`
      - zipped review pack:
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_review_pack_2026-04-30.zip`
      - paired source bundle:
        - `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260430T041152Z.zip`
    - review action completed:
      - moved review draft:
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_final_dev_review_draft_2026-04-30.md`
      - action note:
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_review_action_note_2026-04-30.md`
      - strict confirmation-prep output:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T151237Z__stage35_rank6_route_lineage_confirmation_prep_v1/`
      - result:
        - valid rows:
          - `21`
        - invalid rows:
          - `1`
        - group A old reject / route keep:
          - `4`
        - group B old keep / route reject:
          - `5`
      - current instruction:
        - inspect group A and B against existing shallow/deep evidence
        - if coherent, write a fixed-rule tiny confirmation design
        - do not launch runtime without explicit approval
    - route-lineage additive confirmation completed:
      - design note:
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_additive_confirmation_design_2026-04-30.md`
      - closeout:
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_additive_confirmation_closeout_2026-04-30.md`
      - runner:
        - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_route_lineage_additive_confirmation_v1.py`
      - console log:
        - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_route_lineage_additive_confirmation_2026-04-30.log`
      - output:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153119Z__stage35_rank6_route_lineage_additive_confirmation_v1/`
      - result:
        - `4 / 4` cells completed
        - `0` errors
        - `3 / 4` nonnegative versus shallow
        - `1 / 4` regressed versus shallow
      - failed safety cell:
        - `1111/search7001 rank 6 d94845511e181f7c`
        - shallow `0.038`
        - confirmation `0.037`
        - delta `-0.001`
      - instruction:
        - do not launch a wider union-policy runtime
        - close source-rank plus route-novelty as policy-negative
        - carry route-lineage forward only as mechanism evidence
    - constant-local-depth handoff activation completed:
      - output:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022336Z__stage3_entry_const_local_depth_handoff_activation_v1/`
      - result:
        - `3 / 3` saved `1111` handoffs structurally active
        - `3 / 3` mechanism-widened
        - legacy init3 `64`
        - candidate init3 `288`
        - candidate new init3 keys `80`
        - candidate missing legacy keys `0`
      - instruction:
        - launch only one handoff cell first, not a matrix
    - constant-local-depth handoff 7005 launch:
      - plan:
        - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_handoff_resume_plan_2026-05-01.md`
      - runner:
        - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_handoff_7005_v1.py`
      - launch script:
        - `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_handoff_7005_launch_2026-05-01.ps1`
      - console log:
        - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_handoff_7005_2026-05-01.log`
      - budget:
        - `16h` watchdog cap
      - active output:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/`
      - status file:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/cell_0001_1111_search7005_const_local_depth/stage3_resume_status.json`
      - result:
        - completed small-positive:
          - retained `0.372`
          - candidate `0.374`
          - delta `+0.002`
          - elapsed `7139.745s`
    - constant-local-depth handoff 7004 launch:
      - runner:
        - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_handoff_7004_v1.py`
      - launch script:
        - `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_handoff_7004_launch_2026-05-01.ps1`
      - console log:
        - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_handoff_7004_2026-05-01.log`
      - budget:
        - `6h` watchdog cap
      - output:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/`
      - result:
        - completed negative:
          - retained `0.423`
          - candidate `0.406`
          - delta `-0.017`
          - elapsed `7755.439s`
      - closeout:
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_handoff_closeout_2026-05-01.md`
      - instruction:
        - close this exact constant-local-depth handoff-resume shape
        - do not launch `1111/search7002` for this branch
        - downstream-selection audit completed:
          - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T155731Z__stage3_entry_const_local_depth_downstream_selection_audit_v1/`
        - posthoc Stage 3.5 accept-pass fallback gate kept `7005` and rejected
          `7004`, but this was only an offline lead
        - broader offline gate audit completed:
          - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T160206Z__stage35_accept_gate_broader_offline_audit_v1/`
          - `151` rows
          - `75` negatives versus retained
          - `18` negatives versus selected start
        - close Stage 3.5 accept-pass as a general safety gate
        - no runtime from this line

    - completed bounded frontier-space robustness harvest:
      - plan:
        - `planning/projects/no_wli/20_active_plans/no_wli_stage35_frontier_space_robustness_harvest_plan_2026-05-01.md`
      - runner:
        - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_frontier_space_robustness_harvest_v1.py`
      - launch script:
        - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_frontier_space_robustness_harvest_launch_2026-05-01.ps1`
      - console log:
        - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_frontier_space_robustness_harvest_2026-05-01.log`
      - budget:
        - `8h` wallclock
        - `1800s` per-cell cap
        - `48` max cells
      - output:
        - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T161846Z__stage35_frontier_space_robustness_harvest_v1/`
      - result:
        - `48 / 48` cells completed
        - `0` errors
        - elapsed `12602.918s`
        - selected rows `32 / 48`
        - selected rows better/worse than shallow `27 / 3`
        - selected rows nonnegative/negative versus selected start `28 / 4`
      - decision:
        - do not promote a policy directly from this harvest
        - do not launch another broad local-rescue runtime batch immediately
      - current recommendation:
        - offline acceptance-boundary extractor completed:
          - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T235632Z__stage35_frontier_space_acceptance_boundary_audit_v1/`
        - `0` perfect single-rule separators
        - `0` perfect two-feature separators
        - close broad local-rescue policy widening for now
        - next work should move up a level unless a genuinely held-out
          validation design is written first

    - current external-review handoff:
      - synthesis:
        - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_synthesis_2026-05-02.md`
      - review pack:
        - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_review_pack_2026-05-02/`
      - sendable zip:
        - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_review_pack_2026-05-02.zip`
      - source bundle is included inside the pack at:
        - `90_source_bundle/get_src_extended_review_bundle__20260502T022329Z.zip`
      - instruction:
        - do not launch another broad runtime batch from the current
          local-rescue evidence
        - next recommended implementation branch is an experiment ledger /
          oracle-gap tool, unless review first selects a held-out Stage-2
          checkpoint validation harness

## Fixed interpretation rules

- `focus family` means:
  - family of the top stage35-admitted row in that run
- keep these three counts separate:
  - `archive_seed_row_count`
  - `best_stage35_seed_row_count`
  - `space_map_stage35_row_count`
- do not substitute vague "trust score" wording once the implementation becomes
  concrete:
  - use the actual retained field names from the current outputs
- do not silently drop runs that have partial family mapping or archive-only
  stage35 rows

## Non-goals for this phase

- no new broad panel
- no live seeds
- no stop-rule changes
- no promoted family-quality head
- no benchmark expansion
- no blended stage35 headline metric
- no benchmark widening while the next solver paradigm is still being chosen

## Output location rule

The v1 outputs should land under:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/<timestamp>__fixed_instance_solver_development_v1/`

Use fixed, hardcoded repo-relative inputs.
Do not auto-discover a latest bundle.

## Lane 2 gated diagnostic scoring evidence

Lane 1 is closed for the order-2/order-3 FWD normal/strict language asset tranche.

## Lane 2 runtime asset preparation - 2026-06-01

The accepted Lane 1 full raw shard payload is provenance/rebuild input.

The accepted small git-facing asset index lives at:

- `assets/ngram_hamming/phaseB_full_raw_v1`

The old `phrase_index_v1` is sample-mode and must not be used as the final
runtime phrase lookup asset.

The next runtime path is:

1. full raw local payload validation
2. compact full raw phrase lookup asset
3. fast runtime index
4. Lane 2 diagnostic rerun using the new asset source

Active command-free automation surfaces:

- local payload validator:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/validate_phaseB_ngram_hamming_full_raw_local_payload_copy_v1.py`
- compact lookup builder:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1.py`
- compact lookup validator:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/validate_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1.py`
- fast runtime index builder:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_fast_runtime_lookup_index_v1.py`
- fast runtime index validator:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/validate_phaseB_ngram_hamming_fast_runtime_lookup_index_v1.py`

Current DJ-MINI validation log:

- `planning/projects/no_wli/50_console_and_watch_logs/djmini_full_raw_local_payload_validation_2026-06-01.log`

Current compact-build state:

- DJ-MINI full payload validation completed `pass`.
- The first monolithic compact build attempt was stopped during the first
  `fwd/order=2/cut=normal` group because observed throughput projected beyond
  the declared `12h` watchdog budget. That partial output was removed.
- The current accepted compact strategy is the partitioned DuckDB builder with
  `DUCKDB_PARTITION_SOURCE_FILES = 5`.
- The first completed compact group is
  `direction=fwd/order=2/cut=normal`, with `100,107,793` rows after dedup,
  `0` duplicate identities, and `6338.39s` elapsed.
- The resumed build completed the second compact group,
  `direction=fwd/order=2/cut=strict`, with `34,812,511` rows after dedup and
  `2061.6s` elapsed.
- The active compact group after that checkpoint is
  `direction=fwd/order=3/cut=normal`.
- The current DJ-MINI resume launch is:
  `planning/projects/no_wli/60_launch_scripts/djmini_phaseB_full_raw_compact_lookup_resume_36h_2026-06-01.ps1`.
- The current DJ-MINI resume log is:
  `planning/projects/no_wli/50_console_and_watch_logs/djmini_full_raw_compact_lookup_duckdb_partitioned5_resume_36h_2026-06-01.log`.
- This resumed build has a declared `129600s` budget and stop condition
  `finish_or_operator_stop_at_wallclock_budget`.
- After compact build completion, run the compact validator before building the
  fast runtime `.npz` index. Do not run Lane 2 from full raw shards or the old
  sample `phrase_index_v1`.
- The prepared post-compact hard-stop launcher is:
  `planning/projects/no_wli/60_launch_scripts/djmini_phaseB_post_compact_to_review_gate_2026-06-01.ps1`.
- It runs compact validation, fast runtime index build, runtime validation,
  Lane 2 diagnostic rerun, and review-pack build in that order. It stops on the
  first failed gate and logs to:
  `planning/projects/no_wli/50_console_and_watch_logs/djmini_phaseB_post_compact_to_review_gate_2026-06-01.log`.
- 2026-06-01 correction: DJ-MINI is no longer the active build target.
  Completed order-2 compact outputs were copied into the local repo and
  hash-verified. Continue asset building locally only unless explicitly
  redirected.
- Current local compact launcher:
  `planning/projects/no_wli/60_launch_scripts/local_phaseB_full_raw_compact_lookup_resume_36h_2026-06-01.ps1`.
- Current local compact log:
  `planning/projects/no_wli/50_console_and_watch_logs/local_full_raw_compact_lookup_duckdb_partitioned5_resume_36h_2026-06-01.log`.
- If local disk fills, stop and tidy local storage; do not silently resume on
  DJ-MINI.
- 2026-06-02 local compact lookup build completed:
  - status: `built`
  - exit code: `0`
  - elapsed seconds: `95412`
  - local free space at finish: `172.09 GB`
  - row count after dedup: `1,115,443,486`
  - duplicate identity count: `0`
- Completed compact group sizes:
  - `fwd/order=2/cut=normal`: `100,107,793` rows, `7,231,028,751` bytes.
  - `fwd/order=2/cut=strict`: `34,812,511` rows, `2,551,739,985` bytes.
  - `fwd/order=3/cut=normal`: `614,144,142` rows, `43,573,129,550` bytes.
  - `fwd/order=3/cut=strict`: `366,379,040` rows, `26,084,568,434` bytes.
- The compact build did not collapse normal/strict, did not use the old
  `phrase_index_v1`, did not use a sample asset, and did not change production
  scoring.
- The next local gate launcher is:
  `planning/projects/no_wli/60_launch_scripts/local_phaseB_post_compact_to_review_gate_2026-06-02.ps1`.
- It must stop on the first failed gate. The intended order is:
  compact validation, fast runtime `.npz` index build, runtime validation,
  Lane 2 diagnostic rerun, then review-pack build.
- 2026-06-02 preflight: common compact row shapes can be very large, so the
  fast runtime index builder is chunked at `1,000,000` rows per `.npz` file.
  Do not revert this to whole-group buffering unless a replacement memory
  bound is added and tested.
- Runtime validation must enforce the chunk cap and row-count match before the
  Lane 2 diagnostic runner is allowed to load `ASSET_SOURCE_MODE =
  "fast_runtime_index"`.
- Compact validation must report progress during both hash and row-validation
  passes. A one-line-per-file validator is not acceptable for these multi-GB
  compact files.
- Compact validation must stay memory-bounded. Use sorted-adjacency duplicate
  checks for compact rows; do not retain all phrase IDs or identities in memory
  for the full local asset.
- 2026-06-03 asset/runtime gate result:
  - compact validation passed all `1,115,443,486` rows with `0` failures
  - runtime index built `2,222` bounded `.npz` chunks covering all
    `1,115,443,486` rows
  - runtime index validation passed with `0` failures
  - these completed asset gates do not need to be rerun for the current Lane 2
    diagnostic-selection correction
- Current Lane 2 review block:
  - the bounded runtime loader filled each order/cut cap from the shortest
    runtime groups
  - selected order-2 entries were all phrase length `3`; selected order-3
    entries were all phrase length `5`
  - every active profile requires minimum phrase length `7`, `8`, or `10`
  - the resulting `0` hits are invalid evidence because every scan considered
    `0` eligible phrase entries
- Before the next Lane 2 rerun:
  - select eligible entries per profile/order/cut or otherwise ensure coverage
    above every active profile minimum
  - emit selected phrase-length coverage in the run manifest/readout
  - hard-stop if any active profile/order/cut has zero eligible entries
  - rerun only Lane 2 diagnostic evidence and review-pack build after tests pass

## Current review gate

- The profile-aware Lane 2 rerun is complete; do not rerun compact validation
  or rebuild the runtime index for this review.
- Lane 2 evidence status: `diagnostic_evidence_ready_for_review`.
- Selection and opportunity contracts: `pass`.
- Review pack status: `packed_review_ready`.
- Current review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_selection_fixed_review_pack_2026-06-03.zip`
- Do not upload the superseded `2026-06-01.zip`; it caused the external
  reviewer to receive the older blocked evidence state.
- The current pack builder enforces a hard `50,000,000`-byte compressed-size
  limit and includes the exact bounded Lane 2 input data plus complete hit
  evidence.
- The next action is full review of the diagnostic evidence.
- Keep production ranking, profile thresholds, score authority, normal/strict
  separation, and cluster scope semantics unchanged until that review decides
  the next branch.

## Approved post-review work

- First clean the current external pack and evidence wording; do not rebuild
  compact or runtime assets.
- Then run a separate Lane 2B stratified diagnostic microbatch. Do not
  overwrite or reinterpret the accepted Lane 2 selection-fixed evidence.
- Implement only isolated, opt-in N3C-normal-equivalent report telemetry with
  no production rank effect.
- Start order-4 sizing/planning only; do not start a full order-4 build without
  a declared size/runtime budget and separate approval.

## Current post-review gate

- Lane 2B stratified evidence was accepted by external review.
- The isolated N3C-normal report telemetry contract is implemented and wired
  into retained-candidate reports and scorer-report JSONL exports only.
- The report wiring remains opt-in, runs after scoring, and has test coverage
  proving candidate scores and ordering are unchanged.
- Review-pack packaging closure is complete:
  - full relevant repo verification: `107 passed`
  - focused verification: `35 passed`
  - fresh extracted portable subset: `81 passed, 15 skipped`
  - full-repo-dependent included tests are explicitly identified
- Do not launch the order-4 full compact build. Its current retained compact
  work is about `72.12 GB` at only `50/800` partitions; establish a bounded
  temporary-storage strategy first.
- Machine-readable order-4 readiness/hold evidence:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_order4_build_readiness_hold_v1/`
- Stop at the current review gate:
  `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_report_wiring_order4_readiness_packaging_closed_review_pack_2026-06-04.zip`
- Never send the superseded ambiguous old filename again:
  `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_report_wiring_order4_readiness_review_pack_2026-06-04.zip`
- Do not connect the report-only telemetry contract to solver/ranking behavior
  or resume order-4 compaction without separate review approval.

This work does not approve production scoring.

## Failed-decryption fixture tranche

- Inventory and fixture recovery are complete and validated.
- Use:
  `assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/fixture/phaseB_failed_decryption_retained_candidate_fixture_v1/`
- Current fixture: `40` trials, `734` candidates/chunks, `2,594` pairs.
- Candidate ranks are not present in the recovered sources; do not invent them.
- Matched-null generation is blocked until an upstream anchor manifest exists.
- The bounded N3C-normal report-only telemetry run is complete:
  - `734/734` candidates
  - `2,594` offline pair comparisons
  - `48` selected Lane 2B phrase entries
  - full fast runtime index queried: `false`
  - zero hits and `2,594` report-only pair ties
  - scores and baseline ordering preserved
  - production rank effect `none`
- Treat this as a bounded wiring canary only. The zero-hit result does not
  assess full-runtime N3C coverage.
- Next action: review the fixture and bounded-canary outputs, then decide
  whether to implement and size a full-fast-runtime fixture query.
- Readiness assessment now blocks the naive scan: the eligible N3C-normal
  scope exceeds `500 million` phrase rows and `100 trillion` raw
  phrase-position checks.
- Implement a candidate-keyed Hamming-neighbour query, then run one small,
  timed, independently complete full-group canary.
- Do not launch an unsized broad scan or widen into ranking/order-4
  integration.
- First length-aware canary complete:
  - `40` candidates, one per trial
  - `5` rare-shape full runtime groups across all length buckets
  - `250` verified N3C hits and `92` verified clusters
  - `1,023` N3C groups explicitly unsearched
  - order-2 seeded regions missed `163` N3C hits and `40` N3C clusters
- Order 2 is approved only as query priority for the next study, never as a
  candidate-region filter.
- Next implementation gate: memory-bounded partition index plus peak-memory
  telemetry before medium/common shape groups or an `80`-candidate diverse
  microbatch.
- Do not build the review pack yet; the current study covers only rare shapes
  and one candidate stratum.
- Memory-bounded medium-shape evidence now covers `80` candidates and all five
  length buckets:
  - `11,783` verified hits
  - `2,830` verified clusters
  - about `599.4 MB` peak memory
  - about `366.5` seconds total
- The medium microbatch is fail-closed at `blocked_budget_exceeded`: its
  `10-11` group took about `181.656` seconds against the declared `180`-second
  group limit.
- The vectorized exact verifier resolved the `10-11` budget block while
  preserving exact semantics.
- The requested first stratified query-planning study is complete:
  - `40` complete groups: `2` rare, `3` medium, and `3` common in each of five
    length buckets
  - `80` retained candidates
  - `195,975` verified hits and `20,481` clusters
  - about `718.4 MB` peak memory
  - consolidated status `review_gate_ready`
- Current consolidated evidence:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_stratified_query_study_summary_v1/`
- Stop at external review before wider/full N3C, score-bearing integration, or
  any use of order 2 as a filter.
- Send only:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_stratified_query_portable_closed_review_pack_2026-06-04.zip`
- Fresh extracted portable scope: `13 passed` without `PYTHONPATH`.
- External review accepted this pack and approved a complete full-runtime N3C
  query over the same `80` candidates only.
- Full-80 run boundaries:
  - runner:
    `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_full80_query_evidence_v1.py`
  - output:
    `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_full80_query_evidence_v1/`
  - scope: `1,028` chunks, `702` logical groups, `613,280,613` phrase rows,
    `80` candidates
  - intended wallclock budget: `12,600` seconds
  - memory ceiling: `2,048 MB`
  - emit global candidate clusters, pairwise gold ledger, full hit HD fields,
    and logical-group/chunk accounting
- First monolithic full-80 attempt stopped after `3/1,028` chunks because the
  first chunks projected beyond the declared budget. Do not resume it as a
  monolithic run by inertia.
- Current execution step is the independently complete `8-9` bucket budget
  anchor:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_full80_bucket_8_9_query_evidence_v1.py`
  with output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_full80_bucket_8_9_query_evidence_v1/`
  and a `3,600` second cap.
- Completed bucket anchors:
  - `8-9`: pass, `2,384.875s`, `1,373,314` hits, `291` global candidate clusters
  - `10-11`: pass, `2,177.859s`, `258,892` hits, `1,451` global candidate clusters
- Pairwise report-only ledgers still show break risk for simple hit/cluster
  counts. Do not promote scoring.
- Next visible run:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_full80_bucket_12_14_query_evidence_v1.py`
  with output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_full80_bucket_12_14_query_evidence_v1/`
  and a `7,200` second cap.
- User approved running all remaining buckets as visible independently complete
  serial jobs. Stop condition: if any bucket exits nonzero, do not launch the
  next bucket. Remaining scopes:
  - `12-14`: `272` chunks, `143` logical groups, `195,100,675` phrase rows,
    cap `7,200s`
  - `15-17`: `317` chunks, `181` logical groups, `212,748,370` phrase rows,
    cap `7,200s`
  - `18+`: `293` chunks, `272` logical groups, `133,301,790` phrase rows,
    cap `5,400s`
- Visible serial run completed all remaining buckets:
  - `12-14`: `33,439` hits, `1,632` bucket-local global clusters,
    `4,542.6s`
  - `15-17`: `1,922` hits, `314` bucket-local global clusters, `3,202.8s`
  - `18+`: `150` hits, `41` bucket-local global clusters, `2,329.8s`
- Full approved chunk scope is now covered by bucket outputs. Do not interpret
  the bucket cluster counts by summing them; recompute global candidate
  clusters across all bucket hit rows.
- Consolidated full80 evidence and review pack are complete:
  - consolidated evidence:
    `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_full80_consolidated_evidence_v1/`
  - review pack:
    `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_full80_consolidated_packaging_closed_review_pack_2026-06-05.zip`
  - entries: `91`
  - ZIP size: `806,518` bytes, under `50 MB`
  - backslash ZIP entries: `0`
  - extracted portable smoke: `2 passed`
  - superseded same-day full80 review-pack variants without the
    `packaging_closed` name were removed after validation.
- Stop at external review. Do not expand to all `734` candidates and do not
  design score-bearing use until this pack is reviewed.
- Hold the full `734`-candidate fixture until the full-80 run is reviewed.
- Score-bearing use remains not approved.
- Preserve baseline scores and ordering exactly.
- Do not use fixture telemetry to prune, select, tie-break, override, or change
  production ranking.
This work does not approve broad candidate scans.
This work does not promote order 2 to score-bearing.
This work does not reject order 4 or order 5.

Lane 2B has run a small post-review diagnostic microbatch and is stopped at review.

This is not production scoring.

This is not a production ranking change.

This is not a broad candidate search.

This is an evidence run over controlled positives, deterministic damage tiers, and matched nulls.

The goal is to decide whether the n-gram Hamming phrase-coherence evidence is strong enough to proceed to report-only scorer integration.

Order 4 remains part of the canonical scorer plan but is outside the current Lane 1 asset tranche.

Order 5 remains optional diagnostic future scope.

S34C_main cannot be fully tested until order 4 is available.

Counts/log-counts remain diagnostic only.

Raw hit counts remain diagnostic only.

Order-2 support remains diagnostic unless it clears a later higher proof burden.

Current command-free repo automation targets:

- diagnostic evidence runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1.py`
- diagnostic evidence output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1/`
- review pack builder:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_v1.py`
- review pack target:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_2026-06-01.zip`

## 2026-06-05 v2 active runbook: corrected normal then S3 strict

Authoritative handoff:

`planning/temp_files/n3c_normal_correction_strict_full80_v2/00_authoritative_v2_handoff.md`

The previous normal full80 pack is superseded for corrected-normal reference
use. Do not treat its exact-span component count as an exact-containing
ordinary cluster count, and do not treat raw pair rows as independent
scientific pairs.

Corrected normal reference is complete:

- output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_evidence_v1/`
- pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_review_pack_2026-06-05.zip`
- portable extracted tests: `8 passed`
- ordinary global clusters: `275`
- exact-containing global clusters: `225`
- raw pair rows: `16`
- unique semantic pairs: `8`

S3 strict full80 scripts:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_8_9_query_evidence_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_10_11_query_evidence_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_12_14_query_evidence_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_15_17_query_evidence_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_18_plus_query_evidence_v1.py`

Run sequentially in visible PowerShell windows with repo-relative tee logs.
Budgets:

- `8-9`: `3,600s`
- `10-11`: `7,200s`
- `12-14`: `7,200s`
- `15-17`: `7,200s`
- `18+`: `5,400s`

Stop condition: if any strict bucket exits nonzero, do not launch the next
bucket. Do not use hidden PowerShell for these long runs. Do not expand to all
`734` candidates or change scoring/ranking authority.

S3 strict run completion:

- all five strict buckets completed
- strict consolidated evidence:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_full80_corrected_consolidated_evidence_v1/`
- strict-vs-normal comparison:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_vs_normal_full80_comparison_v1/`
- review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_strict_vs_normal_full80_review_pack_2026-06-06.zip`
- pack validation: fresh extracted portable tests `11 passed`

Current stop: main external review. Do not launch all-`734`, score-bearing,
or production-ranking work before review.

## 2026-06-06 current stop: strict 320 all-data review

The selected-80 strict review pack has been superseded as the main review
bundle by the strict 320 all-data review pack.

- all `20` strict bucket outputs are complete
- combined strict 320 evidence:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_320_corrected_consolidated_evidence_v1/`
- review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_strict_320_all_data_review_pack_2026-06-06.zip`
- pack contents:
  - corrected normal evidence
  - original selected-80 strict evidence
  - selected-80 strict-vs-normal comparison
  - strict 320 consolidation
  - all 20 strict bucket summaries/manifests
  - runtime logs
  - hit-file row counts, byte counts, SHA-256 hashes, and sampled hit rows
- pack facts:
  - entries: `199`
  - ZIP size: `1,135,215` bytes
  - fresh extracted portable tests: `13 passed`

Strict 320 headline results:

- candidates: `320`
- phrase rows queried: `1,462,064,928`
- verified hits: `6,415,767`
- global candidate clusters: `1,115`
- exact-containing global candidate clusters: `893`
- unique semantic pairs: `590`
- rescue-capable unique semantic pairs: `0`

Current stop remains external review. Do not launch all-`734`, score-bearing,
production-ranking, raw-hit-authority, or simple-cluster-authority work before
review.

