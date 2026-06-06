# Current state

## 2026-05-30 n-gram scorer canon/bridge update

The discussion draft in
`planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_v3_2_canon_review.md`
is accepted as the current coordination basis for the no-WLI n-gram phrase
coherence scorer discussion.

Key decision:

- preserve the deep-research canonical scorer ladder as the destination:
  - diagnostics: `B2R`, `N3S_diag`, `F5D`
  - score-candidate families: `N3C`, `S3W`, `N4L`, `S34C_main`
- treat current order-2/order-3 work as a staged bridge/probe, not as silent
  scope reduction and not as the final scorer direction
- keep `S34C_main` at min phrase token length `10`; any length-8 S34C variant
  must be separately labelled diagnostic/broader-than-canon
- require every bridge/canonical/probe profile to declare:
  - `profile_origin`
  - `canonical_profile_id`
  - `parameter_status`
  - `score_authority`
- do not let diagnostic profiles shape score-candidate clusters unless the
  cluster scope explicitly says so
- do not start broad bridge scans, order-4/order-5 expansion, full hard-pair
  reporting, or production scorer changes before full raw order-2/order-3
  provenance is complete and reviewed

Current data-plane gate:

- full raw FWD order-2/order-3 normal/strict shard build has completed
  successfully
- restart check on 2026-05-31 after runner crash:
  - previous worker was no longer running
  - manifest at restart showed `641 / 1118` completed shards
  - resumed worker PID: `12928`
  - resume log line: `resume_completed_shards=641/1118`
  - restarted at: `shard_start=642/1118 order=3 shard=442`
  - final watch log line: `status=pass completed_shards=1118/1118`
  - live watch log:
    `planning/projects/no_wli/50_console_and_watch_logs/phaseB_ngram_hamming_full_raw_asset_shards_resume_2026-05-31.log`
  - run root unchanged:
    `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/20260530T120414Z__phaseB_ngram_hamming_full_raw_asset_shards_v1`

Lane 1 closure status:

- Lane 1 is not closed merely because shard provenance passes. It closes only
  with a permanent asset contract, passing asset validation, and a
  `review_ready` provenance review pack.
- permanent asset home:
  - `assets/ngram_hamming/phaseB_full_raw_v1`
  - payload storage mode:
    `manifest_index_external_payload_due_large_size`
  - reason: retained shard payload is about `71GB` compressed, so the asset
    home records repo-relative payload paths and SHA256 hashes instead of
    copying payloads into git-tracked assets
- permanent asset manifest:
  - `assets/ngram_hamming/phaseB_full_raw_v1/asset_manifest.json`
  - asset status: `review_ready_candidate`
  - listed payload files: `2236`
  - provenance files: `7`
- asset validation:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_language_asset_validation_v1/validation_manifest.json`
  - status: `pass`
  - listed files: `2236`
  - hash failures: `0`
  - missing files: `0`
- Lane 1 closure review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane1_full_raw_language_asset_closure_review_pack_2026-06-01.zip`
  - status: `packed_review_ready`
  - entry count: `42`
  - backslash entries: `0`
  - missing files: `0`
  - `50_asset_index` now mirrors the permanent asset manifest, README, and
    permanent asset provenance files for cleaner handoff
- length-partition parse counters:
  - source output files: `2236`
  - parsed output files: `1728`
  - unparsed output files: `508`
  - source aggregate rows: `1115443486`
  - parsed aggregate rows: `1115443486`
  - unparsed aggregate rows: `0`
- closure-pack safety state is now derived from component manifests:
  - no production scorer change state: `true`
  - no real scan state: `true`
  - Lane 2 launch decision remains `blocked`
- Lane 1 closure does not approve Lane 2 launch, does not approve production
  scorer changes, does not reject order 4, and does not delete future order 5
  diagnostic scope. Counts/log-counts remain diagnostic only.

Allowed preparation while the shard build runs:

- prepare bridge diagnostic schemas, profile manifests, and synthetic tests
- prepare the full raw provenance review checklist
- prepare the order-2/order-3 bridge diagnostic plan

Lane 2 preparation completed so far:

- bridge profile/spec and cluster helper module:
  - `src/rune_decrypter_prime/scoring/ngram_hamming/bridge.py`
- synthetic authority/cluster tests:
  - `tests/scoring/ngram_hamming/test_bridge_profiles_and_clusters.py`
  - verification:
    - `python -m py_compile src\rune_decrypter_prime\scoring\ngram_hamming\bridge.py`
    - `python -m pytest tests/scoring/ngram_hamming/test_bridge_profiles_and_clusters.py tests/scoring/ngram_hamming/test_reference_ngram_hamming.py -q`
  - latest focused Lane 2 verification:
    `41 passed in 0.99s`
- full raw shard provenance helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/summarise_phaseB_ngram_hamming_full_raw_asset_shards_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1`
  - status: `pass`
  - completed shards at latest provenance extraction: `1118 / 1118`
  - missing shards at latest provenance extraction: `0`
  - failed shards: `0`
  - missing output files: `0`
  - full raw confirmed: `true`
- full raw provenance review pack:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_provenance_review_pack_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1`
  - status: `review_ready`
  - copied evidence/context/source files with manifest hashes
  - phrase length distribution rows: `98`
  - word length distribution rows: `140`
  - pending required review checks: none
- Lane 2 launch decision record:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1`
  - status: `blocked`
  - provenance review status after Lane 1 closure: `review_ready`
  - launch blocker: hardcoded real bridge scan approval switch remains `false`
  - hardcoded real bridge scan approval switch remains `false`
  - intended first launch scope: `post-review microbatch only`
- Lane 2 external review pack:
  - builder:
    `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_external_review_pack_v1.py`
  - folder:
    `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane1_lane2_full_review_pack_2026-05-31`
  - zip:
    `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane1_lane2_full_review_pack_2026-05-31.zip`
  - status: superseded by the Lane 1 closure pack above
  - review position: pre-launch blocked preparation review; do not approve real
    bridge scans from this pack
  - includes research/canon planning docs, no-WLI planning state, Lane 1
    provenance CSV summaries, Lane 2 component outputs, source, and tests
  - dependency closure remains present:
    `reference.py`, `fast_backend.py`, `bridge.py`, and `__init__.py`
  - rebuilt zip contains `84` entries and no missing files
  - supersedes the earlier non-closure zip:
    `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_bridge_lane2_prep_external_review_pack_2026-05-31.zip`
  - also supersedes the dependency-closure-only zip:
    `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_bridge_lane2_prep_external_review_pack_dependency_closure_2026-05-31.zip`
- Lane 2 schema/contract pack:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_contract_pack_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1`
  - profile manifest hash: `bc48b348d6afa6f0402514f6055cbe4ec33fb328e1b658144c67d4f812b85e28`
  - canonical profiles: `7`
  - bridge profiles: `5`
  - broad scan launched: `false`
  - production scorer changes: `false`
- Lane 2 readiness checker:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/check_phaseB_ngram_hamming_bridge_lane2_readiness_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1`
  - status: `pass`
  - bridge broad scan ready: `true`
  - full raw provenance is complete, but real bridge scan launch still requires
    separate review and hardcoded approval switch change
- Lane 2 synthetic contract smoke:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1`
  - status: `pass`
  - no real candidate scan: `true`
  - no production scorer changes: `true`
  - row coverage: `3` hits, `2` all-clusters, `2` score-clusters, `3`
    all-profile candidate summaries, `2` score-candidate summaries, `1`
    pair-ledger row, `1` zero-hit row
- Lane 2 prep status index:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1`
  - status: `blocked`
  - contract pack: `pass`
  - synthetic contract smoke: `pass`
  - shard provenance: `pass`
  - full raw provenance review pack: `review_ready`
  - launch decision record: `blocked`
  - readiness gate: `pass`
- Lane 2 gated diagnostic scaffold:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1`
  - status: `blocked`
  - real candidate scan started: `false`
  - hardcoded scan approval: `false`
- Lane 2 input contract:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_input_contract_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1`
  - status: `pass`
  - no real candidate scan: `true`
  - candidate chunk fields: `10`
  - pair input fields: `6`
  - run config fields: `9`
- Lane 2 prep bundle:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1`
  - status: `pass`
  - copied files: `31 / 31`
  - broad scan ready: `true`

Lane 2 preparation plan:

- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md`

Not allowed yet:

- broad bridge scan launch
- order-4/order-5 expansion
- treating order-2 as score-bearing
- direct additive P2/current-score fusion
- controlled `20-50%` damage-ladder claims from candidate-comparability runs
- production scoring changes

## 2026-05-14 scorer-development overlay

Update on 2026-05-29:

- Microsoft C++ Build Tools are now available locally.
- C++ Slice 1 optional extension build passed:
  - `src/rune_decrypter_prime/scoring/ngram_hamming/_ngram_hamming_fast.cp311-win_amd64.pyd`
- Import verification passed for `_ngram_hamming_fast`.
- Synthetic parity/reference/tool verification now runs without skips:
  - `41 passed in 54.58s`
- C++ Slice 2 tiny real-index smoke now passes with no Python fallback:
  - `backend_impl=cpp_fast`
  - `parity_match=True`
  - `elapsed_seconds=0.957`
  - `positive-control fast hits=2`
  - `real-candidate fast hits=0`
- Full bounded n-gram Hamming verification:
  - `44 passed in 56.71s`
- Review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_fast_real_index_smoke_review_pack_2026-05-29.zip`
- Exact no-cap pilot design is now review-ready:
  - `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_exact_no_cap_pilot_design_plan_2026-05-29.md`
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_exact_no_cap_pilot_design_review_pack_2026-05-29.zip`
- Design decision:
  - candidate-source comparability is a hard preflight gate
  - current `candidate_full_texts.jsonl.gz` does not contain full controlled
    damage-stream fingerprint fields by itself
- No pilot runner and no full hard-pair report has started.
- Current next gate is design review before any exact no-cap pilot runner.

The active PhaseB scorer-development plan is now:

- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_plan_2026-05-14.md`
- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_implementation_start_plan_2026-05-14.md`

Start-plan review pack:

- `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_start_review_pack_2026-05-14.zip`
- review verdict:
  - approved with amendments before coding

The exact filtered n-gram hard-pair report is closed as a valid negative for
exact joined phrase scanning on damaged no-WLI candidate streams:

- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_hard_pair_report_v1`
- `N4_normal_2_4_combined_core`:
  - truth preference `2 / 2594`
  - rescues `0`
  - breaks `0`
  - net `0`
- `N6_normal_plus_strict_support`:
  - truth preference `2 / 2594`
  - rescues `0`
  - breaks `0`
  - net `0`

The next live scorer question is word-structured phrase Hamming: can damaged
word-like spans form plausible filtered n-gram phrases when Hamming damage is
allowed at the word/phrase level? The approved plan is FWD-only, no-WLI,
no-production-weight-change, no-hit-cap, and gate-driven. Full hard-pair
reporting is not first; asset validation, phrase index construction, Python
reference tests, independent C++ backend parity, and exact pilots must happen
before the full report.

The implementation start plan recommends placing reusable scorer code under
`src/rune_decrypter_prime/scoring/ngram_hamming/` and no-WLI runners under
`tools/benchmarks/periodic_sub_trans/no_wli/analysis/`, pending review.

The review amendments require a Slice 0 damage-source audit before any
controlled `20-50%` damage-ladder pilot, canonical nested `word_token_ids`,
explicit backend implementation manifests, no silent Python/C++ fallback, and
separate `phrase_hits_per_opportunity` versus
`positive_start_offset_fraction` metrics.

Implementation progress on 2026-05-14:

- Slice 0 damage-source audit: `pass`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_damage_source_audit_v1`
- Slice 1 asset validation: `pass`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_asset_validation_v1`
- Slice 2 phrase index: `pass`, `196680` phrase entries
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_phrase_index_v1`
- Slice 3 Python reference matcher:
  - `src/rune_decrypter_prime/scoring/ngram_hamming/`
- Current gate:
  - reference/tool tests are passing for the implemented slices
  - C++ Slice 1 source is implemented
  - C++ Slice 1 build and synthetic parity now pass locally
  - C++ Slice 2 tiny real-index smoke now passes locally
  - pilots and full hard-pair report are still not started
- Implementation review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_impl_review_pack_2026-05-14.zip`
- Pack-level review result:
  - pass with amendments
  - code-level review blocked because the first implementation pack did not
    include actual source/test contents
- Pre-C++ amendments now implemented:
  - exact damaged-stream sharing marked `unverified`
  - stream-fingerprint fields recorded for later pilot proof
  - parser/token contract and token bounds recorded
  - asset word-length, token-length, duplicate, and example outputs emitted
  - phrase profile eligibility summary emitted
  - tiny Python reference smoke passed using `python_reference`, not a broad
    Python pilot
- Replacement source-inclusive implementation review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_impl_review_pack_2026-05-15.zip`
- Source-level review result:
  - pass with pre-C++ amendments
- Pre-C++ contract amendments now implemented:
  - profile direction added and enforced
  - strict `rune_lengths`
  - strict candidate tokens
  - core FWD invalid builder rows block phrase-index status
  - explicit `sum_count`, `max_count`, and `max_log_count`
- Updated pre-C++ review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_pre_cpp_contract_review_pack_2026-05-15.zip`
- C++ Slice 1 source implemented:
  - independent in-memory backend source and pybind wrapper
  - synthetic parity tests added
  - no real-data loading or benchmark runner
- Local build status:
  - build blocker cleared on 2026-05-29 after Microsoft C++ Build Tools became
    available
  - optional backend tests now execute and pass
- C++ Slice 1 source review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_cpp_slice1_source_review_pack_2026-05-15.zip`

Date baseline for this summary: 2026-04-29. The selector-checkpoint subtopic remains review-ready after provenance reconciliation, with live runtime still blocked as a production/general policy. The Phase-C multi-thread saved-surface harvest is now complete and closes broad frontload-depth / quota / replacement reshuffling. The Stage-3 entry constant-local-depth full-pipeline panel capped after one completed control job, so the paired candidate comparison remains unanswered. The late-stage-only handoff/archive rescue branch has now completed its first two short selected-row guard-selector cells: `1111/search7005` is a strict accepted positive, while `1111/search7004` is blocked by the search-score guard despite a truth-positive archive row.

## Immediate current read

- Do not launch another six-job full-pipeline Stage-3 entry panel as-is.
- Do not run another broad saved-surface frontload-depth / quota / replacement atlas.
- Do not launch an hour-plus or overnight runtime without an explicit wallclock estimate, stop condition, and user approval.
- Current highest-value branch:
  - `stage35_resume_from_handoff_focus_family_rescue_v1`
- Primary target order:
  - `1111/search7005`
  - `1111/search7004`
  - `1111/search7002` as control / proof-of-runner
- Planning note:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage35_resume_from_handoff_focus_family_rescue_plan_2026-04-29.md`
- Static handoff/archive inventory:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T043455Z__stage35_resume_from_handoff_focus_family_rescue_v1/`
  - result:
    - `3 / 3` targets late-stage feasible
    - selected-row material complete:
      - `17 / 17` archive seed rows
    - existing late-stage entry point:
      - `artifact_resume.run_stage35_from_selected_trial_row`
    - upstream recompute required:
      - `0`
    - selected-row headroom:
      - `1111/search7005`:
        - `0.416` versus retained `0.372`
      - `1111/search7004`:
        - `0.432` versus retained `0.423`
      - `1111/search7002`:
        - `0.752` versus retained `0.754`
    - runtime launched:
      - `0`
- Smoke preflight:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T044610Z__stage35_resume_from_handoff_focus_family_rescue_v1__smoke_preflight/`
  - target:
    - `1111/search7005`
  - selected row:
    - `c9e69b90b779e318`
  - config:
    - `rounds = 0`
  - result:
    - retained `0.372`
    - selected start `0.416`
    - smoke resume `0.416`
    - elapsed `1.485s`
    - progress events written `3`
    - partial dumps written `3`
    - real science runtime launched `0`
- Recommended next:
  - make an explicit launch decision for the real `1111/search7005`
    selected-best-frontier micro-canary
  - timing anchor:
    - retained same-lane Stage 3.5 took `1996.242s` (`33m16s`)
  - proposed cap:
    - `3600s`
  - because the estimate is close to the one-hour guard, do not auto-launch
    without explicit confirmation
- First real selected-row run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T060445Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_v1__real_selected_best_frontier_one_round/`
  - target:
    - `1111/search7005`
  - selected row:
    - `c9e69b90b779e318`
  - natural stop:
    - one bounded Stage 3.5 round completed
  - cap:
    - none (`max_runtime_seconds = 0`)
  - result:
    - retained `0.372`
    - selected start `0.416`
    - resume best `0.416`
    - delta versus retained `+0.044`
    - delta versus selected start `+0.000`
    - accept reason `search_score_drop_guard_failed`
    - elapsed `2.991s`
    - evals `1470`
    - progress events `16`
    - partial dumps `4`
- Recommended next:
  - do not deepen the same broad `7005` selected-row rescue shape immediately
  - posthoc archive analysis found a guard-passing, truth-positive rank-2
    alternate:
    - `7068135ec036da03`
    - truth match `0.422`
    - `+0.006` versus selected-row start
    - score delta `+0.002984`
    - search-score delta `+0.016851`
  - the completed run used `accept_guard_passing_selector_mode = off`, so it
    did not fall through after rank 1 failed `search_score_drop_guard_failed`
  - next should be a small same-target guard-passing-selector follow-up before
    any `7004` confirmation or deeper rescue
- Guard-selector follow-up:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T145906Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/`
  - result:
    - retained `0.372`
    - selected start `0.416`
    - accepted resume best `0.422`
    - delta versus retained `+0.050`
    - delta versus selected start `+0.006`
    - accept reason `accepted_via_guard_passing_selector`
    - selected archive rank `2`
    - selected candidate `7068135ec036da03`
    - elapsed `6.361s`
  - carried conclusion:
    - the posthoc archive read was actionable
    - `7005` now has a real accepted local-rescue improvement
    - next decision is whether to run the same guard-selector shape on
      `1111/search7004`, where static headroom is smaller
- `7004` guard-selector secondary confirmation:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T150415Z__stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/`
  - result:
    - retained `0.423`
    - selected start `0.432`
    - reported local top resume `0.425`
    - delta versus retained `+0.002`
    - delta versus selected start `-0.007`
    - accept reason `search_score_drop_guard_failed`
    - selected `0`
    - elapsed `10.620s`
  - posthoc archive read:
    - rank 6 `3b5b0ca607c51fbe` was truth-positive at `0.438`
      (`+0.006` versus selected start) but failed the search-score guard
    - no non-no-op row passed both nonnegative score and search-score guards
  - carried conclusion:
    - strict guard-selector result is mixed, not uniformly repeatable
    - stop this exact runtime shape now
    - next useful work is an offline guard-relaxation/policy audit over saved
      archives, if we want to pursue the rank-6-like misses
- Offline guard-selector archive policy audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T151026Z__stage35_guard_selector_archive_policy_audit_v1/`
  - scope:
    - `2` cases
    - `24` archive rows
  - result:
    - accepted-positive cases `1 / 2`
    - cases with blocked truth-positive rows `1 / 2`
    - `7005` best truth row rank `2`, `7068135ec036da03`, `0.422`
    - `7004` best truth row rank `6`, `3b5b0ca607c51fbe`, `0.438`, blocked by search-score decline
  - carried conclusion:
    - stop strict guard-selector runtime for now
    - next work, if any, should be broader offline guard-relaxation/policy
      analysis before runtime
- Broader guard-relaxation archive data-taking run is being launched:
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_relaxation_archive_policy_long_audit_v1.py`
  - console log:
    - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_relaxation_archive_policy_long_audit_2026-04-29.log`
  - budget:
    - `8h` / `28800s`
  - stop condition:
    - all discovered Stage 3.5 archive sources processed or wallclock budget
      reached
  - progress:
    - completed-versus-total, elapsed, and ETA every `5` sources
- Archive data-taking completed quickly:
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T152347Z__stage35_guard_relaxation_archive_policy_long_audit_v1/`
  - `264 / 264` sources, `931` archive rows, `8.084s`
  - strict search-score guard remains best default from this audit
- Broader runtime harvest is being launched to use the remaining session:
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_selector_frontier_runtime_harvest_v1.py`
  - console log:
    - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_selector_frontier_runtime_harvest_2026-04-29.log`
  - budget:
    - `8h` / `28800s`
  - per-cell cap:
    - `900s`
  - stop conditions:
    - queue exhausted, wallclock reached, or first-cell projection exceeds
      budget
- Runtime budget references are refreshed through:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T011225Z__no_wli_runtime_history_reference_v1/`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T011225Z__fixed_runtime_wallclock_reference_v1/`

## Recent closed results

### Phase-C multi-thread long harvest

- Runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_phasec_multi_thread_long_harvest_v1.py`
- Completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260427T020956Z__phasec_multi_thread_long_harvest_v1/`
- Completed:
  - `1539 / 1539` units
  - `19` cases
  - `27` policies
  - `3` passes
  - `19:21:02`
- Result:
  - no frontload-depth, quota, or replacement family beat reorder-only controls
  - repeated exact replay rows were stable:
    - score:
      - `513 / 513`
    - delta:
      - `513 / 513`
    - winner:
      - `513 / 513`
    - surface class:
      - `513 / 513`
- Carry forward:
  - exact saved-surface replay was deterministic for result values in this run family
  - runtime varied, but result values did not
  - only `phaseb_topk_anchor_swap_v1` and `phaseb_topk_frontload_all_v1` carried useful movement
  - broad saved-surface reshuffling is closed in this exact form

### Stage-3 entry constant-local-depth reorder-signal panel

- Runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_reorder_signal_panel_v1.py`
- Parent matrix files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v79_fixed_p9c3_1111_reorder_signal_stage35_entry_const_local_depth_panel_6job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v79_fixed_p9c3_1111_reorder_signal_stage35_entry_const_local_depth_panel_6job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v79_fixed_p9c3_1111_reorder_signal_stage35_entry_const_local_depth_panel_6job.jsonl`
- Completed child bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260428T035424021944Z__bench_solve_pipeline_no_wli__ee62083/`
- Completed:
  - `1 / 6` jobs
  - `1111/search7002`
  - about `13:32:47`
- Preset verified:
  - completed job was `stage35_baseline_score_plus_novelty_live_bounded_p9`
  - `stage3.entry.allocation_policy = legacy_fixed_budget`
  - candidate `constant_local_depth` did not complete
- Result:
  - best match:
    - `0.754`
  - best stage:
    - `stage35_substitution_only`
  - status:
    - `unsolved`
- Provenance caveat:
  - child `run_manifest.json` has git dirty flag set
- Carry forward:
  - useful single-job data:
    - yes
  - answered intended candidate-vs-control comparison:
    - no
  - full-pipeline panel shape is too expensive as configured
  - use saved handoff/archive artefacts for a late-stage-only comparison

## Trusted conclusions

### Fixed-instance infrastructure and retained panel

- Fixed-instance mode v1 infrastructure is complete and validated.
- The first fixed `20`-job `p9/c3/l1000/no-WLI` panel is fully retained across:
  - `v71`
  - `v72a`
  - `v72b`
  - `v73`
- Retained completed-job coverage is present for all `20` completed jobs:
  - each retained completed bundle has:
    - `run_manifest.json`
    - `final_instances`
    - `best/best_instance.json`
- Two non-panel residues remain and should stay caveated:
  - interrupted local `v71` job-4 residue without `best/best_instance.json`
  - one stale `v72b` log reference to a non-retained path

### Fixed-instance solver-development analysis pack

- Workstreams `1-6` are now complete.
- Current combined analysis bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160503Z__fixed_instance_solver_development_v1/`
- Generated outputs:
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
- The combined analysis pack now encodes:
  - the primary trio:
    - `1511`
    - `611`
    - `1111`
  - `1411` as a caveated cross-check
  - separate stage35 count fields:
    - `archive_seed_row_count`
    - `best_stage35_seed_row_count`
    - `space_map_stage35_row_count`
  - retained trust-related field names from copied `best_instance.json`

### Current upstream branch read

- The first fixed-panel upstream promoted-family audit is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/`
- Under primary family view `prefix_hamming_le_24`, `1111` is now the only
  primary-trio seed family with a persistent upstream within-family
  representative gap:
  - mean `stage2_topk` within-family gap:
    - `0.070`
  - mean `stage2_promoted` within-family gap:
    - `0.070`
  - mean `stage2_promoted` between-family gap:
    - `0.014`
- Controls stay near zero on the same promoted within-family metric:
  - `611`:
    - `0.000`
  - `1511`:
    - `0.000`
- Current interpretation:
  - the next honest branch is upstream representative selection inside an
    already-present family region
  - the next honest branch is not another generic family-diversity or
    entry-allocation rerun
- A first concrete `stage2_topk` representative-selector audit is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/`
- Concrete selector read:
  - policy:
    - `selected_family_low_edge_eps_0p020_v1`
  - `1111`:
    - candidate active runs:
      - `5 / 5`
    - oracle-match runs:
      - `5 / 5`
    - mean candidate truth delta vs baseline:
      - `+0.070`
  - controls:
    - `611`:
      - inactive
    - `1411`:
      - inactive
    - `1511`:
      - inactive
- The follow-on family-view / score-band sensitivity sweep is also complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/`
- Sensitivity read:
  - only `prefix_hamming_le_24` produces a clean `1111`-only activation window
  - under that view:
    - `eps = 0.015` is harmful on `1111`:
      - mean delta `-0.023`
    - `eps = 0.016` is the smallest clean positive:
      - mean delta `+0.070`
    - `eps = 0.020` stays equally positive:
      - mean delta `+0.070`
    - `eps = 0.025` attenuates sharply:
      - mean delta `+0.005`
- Current selector branch interpretation:
  - the branch is now narrow enough to specify one concrete selector
  - the next honest microprobe is not generic representative selection
  - the next honest microprobe is:
    - family view:
      - `prefix_hamming_le_24`
    - policy:
      - `selected_family_low_edge_eps_0p016_v1`
- The saved handoff audit for that concrete selector is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T031321Z__stage2_topk_selected_family_low_edge_handoff_audit_v1/`
- Handoff read:
  - `1111`:
    - `best2_key_changed_run_count = 5`
    - `init3_changed_run_count = 5`
    - mean `init3_edit_count = 7.8`
    - mean `stage3_promoted_keys_edit_count = 7.8`
  - controls:
  - `611`: all zero
  - `1411`: all zero
  - `1511`: all zero
- The first exact replay for that concrete selector is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- Exact replay read:
  - saved-row truth:
    - baseline `0.091`
    - candidate `0.161`
    - delta `+0.070`
  - final replay match:
    - candidate `0.420`
    - artifact baseline `0.423`
    - retained Stage-3 reference `0.432`
  - strongest challenger lane:
    - start `2`
    - init `0.415`
    - final `0.420`
    - `became_global_best = 1`
- The exact selector family matrix is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/`
- Exact-family matrix read:
  - runtime:
    - `01:52:14`
  - recommendation:
    - `refine`
  - clean exact win:
    - `7003`
    - replay `0.476`
    - delta vs baseline `+0.068`
    - delta vs retained Stage-3 reference `+0.153`
  - baseline-only supporting win:
    - `7005`
    - replay `0.413`
    - delta vs baseline `+0.041`
    - delta vs retained Stage-3 reference `-0.003`
  - local slight loss:
    - `7004`
    - delta vs baseline `-0.003`
  - severe collapses:
    - `7001`
      - delta vs baseline `-0.267`
    - `7002`
      - delta vs baseline `-0.444`
  - family mean delta vs baseline:
    - `-0.121`
- The Phase-A competitiveness audit for that exact family is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/`
- Phase-A competitiveness read:
  - recommendation:
    - `advance`
  - best gate:
    - `rank1_init_ge_0p30`
  - metric:
    - `phasea_rank1_init_match`
  - kept seeds:
    - `7003,7004,7005`
  - filtered seeds:
    - `7001,7002`
  - kept mean delta vs baseline:
    - `+0.035`
  - counterfactual family mean delta vs baseline:
    - `+0.021`
- The Phase-A rank-1 gate microprobe is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T023226Z__stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1/`
- Phase-A rank-1 gate microprobe read:
  - recommendation:
    - `advance`
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
  - mean Phase-A gate proxy elapsed:
    - `52.8s`
- The Phase-A gate persistence microprobe is now complete:
  - replay bundle instrumentation now writes:
    - `resume_bundle/phasea_gate_snapshot.json`
  - the replay progress log now emits:
    - `stage3_phasea_gate_snapshot`
  - the exact replay wrapper now surfaces:
    - `phasea_gate_snapshot_json_relpath`
      - in `attempt_status.json`
  - focused verification:
    - `40 passed`
- The first exact live-read canary is now preserved as the schema-gap finding:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T034213Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
  - completion:
    - `01:00:17`
  - result:
    - `refine`
  - live-read outcome:
    - `resume_bundle/phasea_gate_snapshot.json` existed
    - but the gate fields needed for a live verdict were still `null`
    - snapshot share of total runtime was about `0.891`
- The patched `7004` live-read canary is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061020Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
  - completion:
    - `00:23:56`
  - replay result stayed the same local negative:
    - baseline `0.423`
    - retained Stage-3 reference `0.432`
    - replay `0.420`
    - delta vs baseline `-0.003`
  - live-read outcome:
    - `phaseA_rank1_init_match = 0.415`
    - `phaseA_best_init_match = 0.415`
    - `phaseA_best_final_match = 0.415`
    - gate verdict:
      - `keep`
    - snapshot elapsed:
      - `1261.0s`
    - snapshot share:
      - `0.878`
- The longer follow-on family run is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1/`
  - completion:
    - `02:03:21`
  - family coverage:
    - `5 / 5`
  - machine recommendation:
    - `advance`
  - live-read family outcome:
    - snapshot present on `5 / 5`
    - snapshot usable on `5 / 5`
    - verdict matched expected split on `5 / 5`
    - keep:
      - `7003,7004,7005`
    - filter:
      - `7001,7002`
    - mean snapshot elapsed:
      - `1303.4s`
    - mean snapshot share:
      - `0.881`
- The snapshot backfill fix is now landed in code:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - focused verification:
    - `45 passed`
- The first explicit both-action microprobe is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T161225Z__stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1/`
  - filtered child canary:
    - `7002`
  - kept child canary:
    - not launched
  - filtered canary semantic read:
    - observed gate verdict:
      - `filter`
    - action applied:
      - yes
    - fallback landed at retained baseline:
      - `0.754`
  - filtered canary timing read:
    - prior exact replay elapsed:
      - `00:22:13`
    - current filtered action canary elapsed:
      - `01:09:52`
    - snapshot elapsed share:
      - `0.9996`
    - saved attempt seconds versus trusted prior replay:
      - `-2858.6`
  - microbatch status:
    - `stopped_over_budget`
  - projected two-canary total after the first completed row:
    - `01:31:46`
- The raw provisional earlier-emission microprobe is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1/`
  - machine result:
    - `hold`
  - branch closure:
    - raw provisional `rank1` is not enough
  - key read:
    - `7002` matches `filter` at restart `16`
    - `7003` still misfires as `filter` through restart `64`
    - the same provisional `7003` snapshots already contain:
      - `phaseA_best_init_match = 0.490`
- The checkpoint-refinement audit is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T192446Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1/`
  - machine result:
    - `advance`
  - selected refined rule:
    - `rank1_ge_0p30_or_best_ge_0p44`
  - trusted-family fit:
    - `5 / 5`
  - selected shared checkpoint:
    - restart `16`
  - mean checkpoint elapsed share:
    - `0.212`
  - mean share improvement versus late live-read:
    - `0.674`
- The refined checkpoint confirmation microprobe is now closed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1/`
  - result:
    - `hold`
  - key read:
    - `7001`
      - provisional `best_init`:
        - `0.378`
      - expected verdict:
        - `filter`
      - observed verdict:
        - `filter`
    - `7005`
      - provisional `best_init`:
        - `0.395`
      - expected verdict:
        - `keep`
      - observed verdict:
        - `filter`
    - the mismatch persisted across checkpoints:
      - `16 / 32 / 48 / 64`
- The strict field-persistence audit is now closed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210520Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1/`
  - result:
    - `hold`
  - key read:
    - filtered `7002` was still moving between restart `16` and restart `32`
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
- The restart-32 best-init action microprobe is now closed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T211444Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1/`
  - result:
    - `advance`
  - key read:
    - `7001`
      - verdict:
        - `filter`
      - checkpoint:
        - restart `32`
      - saved attempt share:
        - `0.562`
    - `7005`
      - verdict:
        - `keep`
      - checkpoint:
        - restart `32`
      - delta vs prior exact replay:
        - `0.000`
- The restart32 best-init remaining-family microbatch is now complete:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`
  - result:
    - `advance`
  - family-contract read:
    - verdict match:
      - `3 / 3`
    - filtered `7002`:
      - checkpoint:
        - restart `32`
      - saved attempt seconds:
        - `759.7`
      - saved attempt share:
        - `0.570`
      - landed at retained baseline:
        - `0.754`
    - kept no-harm count:
      - `2 / 2`
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
  - key read:
    - `7003` stays timing-stable under the same action wiring
    - `7004` first decides `keep` early at restart `32`
    - `7004` slowdown is already visible by restart `64`
    - `7004` slowdown stays visible deep in Phase B
  - interpretation:
    - the anomaly does not read like a gate-logic failure
    - the selector checkpoint science still looks provisionally defensible
    - live runtime still is not reopened from this audit alone
  - external-review and provenance reconciliation close-out:
    - status:
      - review-ready after provenance reconciliation
    - prior blocker:
      - the original decisive remaining-family microbatch bundle had a stale
        role-label reporting mismatch on `7002`
    - resolved by:
      - shared role-contract fix for `filtered_family`
      - focused regression coverage
      - reconciled derived family bundle
      - hardened provenance audit
    - final audit:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T190612Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1/`
      - recommendation `advance`
      - row mismatch count `0`
      - all five recommendation layers present and set to `advance`
    - handoff artefacts:
      - review pack:
        - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25.zip`
      - paired source bundle:
        - `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260425T191004Z.zip`
- Current execution-read interpretation:
  - the concrete selector is not a saved-handoff no-op
  - the selector is not uniformly exact-negative across the fixed `1111`
    family
  - the raw selector is also not solver-usable yet as a general rule
  - the split is now partly explainable from an early Phase-A competitiveness
    signal
  - the gate remains semantically meaningful as a stop / fallback candidate
  - the gate artifact is now persisted during a replay
  - the live gate payload is now usable and family-correct on fixed
    `1111/search7001-7005`
  - the first explicit both-action canary now shows the timing issue is worse
    than the earlier live-read family suggested:
    - on filtered `7002`, the current gate fires essentially at the end of the
      replay rather than early enough to save wallclock
  - the raw provisional checkpoint branch is now also closed:
    - checkpoint `rank1` alone cannot reproduce the trusted split
  - the current refinement branch is now closed:
    - `rank1>=0.30 or best>=0.44` fit the retained audit set but failed the
      second kept confirmation lane
  - the current branch is now:
    - closed on live-read correctness
    - closed on the first narrow action-choice microprobe
    - closed on raw provisional `rank1`
    - closed on refined checkpoint confirmation
    - closed on strict field persistence
    - advanced through the restart-32 best-init action canary
    - advanced through the remaining-family restart32 best-init microbatch
    - review-ready after provenance reconciliation
- the fixed `1111` family generalization question is now semantically complete
- the selector checkpoint science is provisionally supported on fixed
  `1111/search7001-7005`
- packaging / provenance is clean enough for external review
- narrow live-canary preparation is complete:
  - filtered `7002` passed with fallback plus early stop and material runtime
    saving
  - kept `7003` passed semantically and provenance-clean
  - kept/no-action live throughput varied enough that runtime-saving claims
    should not be made from kept lanes
- no production/general policy is claimed from this subtopic
- live runtime remains blocked generally
- completed live-canary preparation:
  - plan:
    - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_plan_2026-04-25.md`
  - Day 2 preflight:
    - passed
    - bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T220602Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_preflight_v1/`
    - recommendation:
      - `advance`
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
    - result:
      - `advance`
    - row mismatch count:
      - `0`
    - saved runtime:
      - `519.954s`
      - `0.390` share
  - runtime remains blocked generally; no further checkpoint canary should
    launch from this branch
  - complementary kept/no-harm canary:
    - passed semantically and provenance-clean
    - source:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T014422Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1/`
    - audit:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T021629Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1/`
    - result:
      - `advance`
    - row mismatch count:
      - `0`
    - timing caveat:
      - `+537.015s` versus retained exact replay reference
  - live-canary reconciliation:
    - complete
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_reconciliation_note_2026-04-26.md`
  - current next step:
    - do not launch more checkpoint canaries from this branch
    - if continuing, open a separate throughput follow-up focused on kept
      no-action wallclock variation
  - timing-risk follow-up plan:
    - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_followup_plan_2026-04-26.md`
    - closed after one throughput-caveat probe
  - throughput existing-log audit:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T073234Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_audit_v1/`
    - localized the slowdown to the live kept/no-action runtime surface
    - live kept/no-action `7003` ratio versus retained exact replay:
      - `1.409x`
  - throughput probe:
    - source:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T073609Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1/`
    - audit:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T084800Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_provenance_audit_v1/`
    - review note:
      - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_review_note_2026-04-26.md`
    - result:
      - semantic/provenance pass
      - valid long-run evidence saved
      - kept-lane throughput caveat confirmed
      - elapsed:
        - `01:07:01`
      - repeat versus retained exact replay:
        - `3.059x`
      - repeat versus family action replay:
        - `3.039x`
      - repeat versus prior live kept/no-action:
        - `2.172x`
      - row mismatch count:
        - `0`
      - recommendation layers:
        - all `advance`
  - refreshed runtime references:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T084830Z__no_wli_runtime_history_reference_v1/`
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260426T084830Z__fixed_runtime_wallclock_reference_v1/`
  - current decision:
    - no further runtime approved from this branch
    - no matrix approved
    - next work can move back to science experiments; only investigate
      throughput separately if a future claim depends on exact live wallclock
  - longer-run setup for the next science branch:
    - `planning/projects/no_wli/20_active_plans/no_wli_longer_run_setup_next_science_branch_2026-04-26.md`
    - use generous caps and end-of-run audits
    - do not launch without a named science hypothesis and target cell

### First controlled solver-change candidate

- Candidate 1 is now selected and implemented in code:
  - guard-aware stage35 followup acceptance for coherent late routes
- Current implementation surface:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage35_substitution_solver.py`
- Opt-in cfg keys:
  - `accept_guard_passing_selector_mode`
  - `accept_guard_passing_score_band_eps`
- Current candidate mode:
  - `top_score_then_search`
- Default remains:
  - off
- Evidence basis for the choice:
  - retained `611/search7005` stage35 logs show the top archive row failed the
    search guard, but a lower preview row still beat the baseline full score
    and the baseline search score
- Status:
  - implemented and unit-tested
  - retained replay run complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160357Z__candidate1_guard_accept_611_search7005_replay_v1/`
  - retained replay result is negative in the current form:
    - accept fires, but `top_score_then_search` picks archive rank `3` inside
      the score band
    - replay best match is `0.572`
    - that is below the original run best `0.585`
  - review cleanup is now landed:
    - `NaN` stage35 truth does not auto-promote stage35 to final best
    - selector-rescued accepts are explicit in telemetry
  - no live run yet

### Second controlled solver-change candidate

- Candidate 2 family-aware budget line is now implemented in two blocked forms:
  - first form:
    - Phase-B top-family reinforcement
  - replacement form:
    - Phase-C anchor-family reserved starts
- Current implementation surface:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- Current runtime proxies:
  - Phase-B policy:
    - `reinforce_top_family_v1`
  - Phase-B canary preset:
    - `stage3_phaseb_top_family_reinforce_p9`
  - Phase-C start policy:
    - `anchor_family_reserved_v1`
  - Phase-C canary preset:
    - `stage3_phasec_anchor_family_reserved_p9`
- Status:
  - synthetic Phase-B reallocation tests pass
  - focused Phase-C start-policy tests pass
  - runtime-contract canaries pass
  - first saved-pool retained shadow verification complete
  - exact retained replays complete on `611/search7005` and `1111/search7004`
  - `phaseB_family_reservation_applied = 0` on both tested retained Phase-B cases
  - matched exact control on `611/search7005` also lands at `0.535`
  - whole-panel Phase-B selected-surface diagnostic closed the first form
  - whole-panel Phase-C anchor-family shadow diagnostic closed the replacement form
  - no live run yet

### Third controlled solver-change candidate

- Candidate 3 is now selected as the next narrow solver-change line:
  - Phase-C first-actual-`phaseB_topk` anchor swap
- Current implementation surface:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- Current runtime proxy:
  - `phaseb_topk_anchor_swap_v1`
- Current canary preset:
  - `stage3_phasec_phaseb_topk_anchor_swap_p9`
- Status:
  - focused Phase-C tests pass
  - whole-panel saved-start shadow verification complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T151927Z__candidate3_phasec_phaseb_topk_anchor_shadow_v1/`
  - shadow read:
    - `19/20` retained runs can engage the anchor-swap rule
    - `11` engageable runs favor the first actual `phaseB_topk` start
    - `7` engageable runs favor the retained anchor
    - `1` engageable run is equal
  - exact-verifier cleanup now landed:
    - stage3-only exact replays compare against the retained Stage-3 reference,
      not just the artifact-level overall best
    - the timed-out one-hour `611/search7004` control attempt is now preserved
      explicitly as insufficient rather than treated as evidence
  - first cleaned exact control is now complete:
    - matched exact control on `1511/search7004`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T163546Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`
    - result:
      - retained Stage-3 reference `0.571`
      - replay best `0.435`
      - delta `-0.136`
    - current interpretation:
      - the exact replay path is not yet stable enough on this case to use as a
        candidate3 decision gate
  - replay-fidelity audit now exists:
    - latest bundle:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T153730Z__candidate3_exact_control_replay_fidelity_1511_search7004_v1/`
    - first unavailable retained surface:
      - none
    - first actual persisted mismatch:
      - `phaseB_downstream_selected_ordered_hashes`
    - ordered-identity replay contract rows now persist explicitly for:
      - `phaseB_downstream_selected_ordered_hashes`
      - `phaseB_topk_saved_ordered_hashes`
      - `phaseC_start_ordered_identities`
    - current control-lane contract read:
      - `ordered_identity_contract_all_match = 0`
  - rerun exact control with the patched replay surface is also complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T015030Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`
    - result:
      - retained Stage-3 reference `0.571`
      - replay best `0.435`
      - delta `-0.136`
      - replay-side ordered surfaces now persist:
        - `phaseB_downstream_selected_summaries = 32`
        - `phaseB_topk_saved_summaries = 1`
    - current interpretation:
      - the blocker is now explicit Phase-B surface drift before candidate3
        acts, not a missing replay-side audit surface
  - saved-surface verifier now exists for the same case:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T052238Z__candidate3_phasec_saved_surface_1511_search7004_v1/`
    - stable saved-surface read:
      - candidate3 can engage on the exact saved Phase-C start surface
      - first distinct `phaseB_topk` start is rank `2`
      - saved-surface `phaseB_topk` minus anchor final match is `0.005`
    - scope:
      - stable ordering reference only
      - not a fresh candidate replay
  - saved-surface exact replay helper is now complete for the same case:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T054445Z__candidate3_phasec_saved_surface_exact_1511_search7004_v1/`
    - result:
      - saved-surface control reproduces retained `0.571`
      - candidate3 lands at `0.569`
      - candidate minus control is `-0.002`
      - control winner stays on retained `phaseB_topk` rank `2`
      - candidate winner shifts to `phaseB_topk` rank `3`
    - interpretation:
      - the narrowed Phase-C-only replay lane is now stable enough to judge
        candidate3 honestly on `1511/search7004`
      - on that exact saved-surface lane, candidate3 is a small clean negative
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
      - interpretation:
        - small control-relative gain only
        - saved-surface control still misses the retained Stage-3 winner
          materially, so this is not a clean utility decision gate
    - `611/search7005`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T014639Z__candidate3_phasec_saved_surface_exact_611_search7005_v1/`
      - control `0.585`
      - candidate `0.589`
      - retained Stage-3 reference `0.615`
      - candidate minus control `+0.004`
      - interpretation:
        - drifted middle-case lane
        - small control-relative gain only
        - not a clean decision gate because the control lane itself still sits
          well below retained
    - `1111/search7002`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055755Z__candidate3_phasec_saved_surface_exact_1111_search7002_v1/`
      - control `0.750`
      - candidate `0.754`
      - retained Stage-3 reference `0.752`
      - candidate minus control `+0.004`
    - `1111/search7001`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T010939Z__candidate3_phasec_saved_surface_exact_1111_search7001_v1/`
      - control `0.420`
      - candidate `0.420`
      - retained Stage-3 reference `0.420`
      - candidate minus control `0.000`
      - interpretation:
        - stable conversion-failure lane
        - candidate3 is neutral here
    - `1111/search7003`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T011123Z__candidate3_phasec_saved_surface_exact_1111_search7003_v1/`
      - control `0.041`
      - candidate `0.041`
      - retained Stage-3 reference `0.323`
      - candidate minus control `0.000`
      - interpretation:
        - drifted conversion-failure lane
        - candidate3 is neutral here, but not on a clean decision gate
    - `1111/search7004`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T011226Z__candidate3_phasec_saved_surface_exact_1111_search7004_v1/`
      - control `0.432`
      - candidate `0.434`
      - retained Stage-3 reference `0.432`
      - candidate minus control `+0.002`
      - interpretation:
        - stable conversion-failure lane
        - candidate3 shows a second small positive on `1111`
    - `1111/search7005`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T010749Z__candidate3_phasec_saved_surface_exact_1111_search7005_v1/`
      - control `0.366`
      - candidate `0.366`
      - retained Stage-3 reference `0.416`
      - candidate minus control `0.000`
      - interpretation:
        - drifted conversion-failure lane
        - candidate3 is neutral here
    - `1511/search7005`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T153047Z__candidate3_phasec_saved_surface_exact_1511_search7005_v1/`
      - control `0.686`
      - candidate `0.686`
      - retained Stage-3 reference `0.691`
      - candidate minus control `0.000`
      - interpretation:
        - near-stable positive-control lane
        - candidate3 is neutral on this case
    - `1511/search7002`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7002_v1/`
      - control `0.842`
      - candidate `0.842`
      - retained Stage-3 reference `0.842`
      - candidate minus control `0.000`
      - interpretation:
        - stable positive-control lane
        - candidate3 is neutral here
    - `1511/search7003`:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7003_v1/`
      - control `0.844`
      - candidate `0.844`
      - retained Stage-3 reference `0.845`
      - candidate minus control `0.000`
      - interpretation:
        - near-stable positive-control lane
        - candidate3 is neutral here
  - current exact-lane matrix bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T014734Z__candidate3_saved_surface_exact_matrix_v1/`
    - matrix read:
      - total exact cases `12`
      - usable decision gates `8`
      - drifted context lanes `4`
      - usable-gate read:
        - positives `2`
        - neutrals `5`
        - negatives `1`
      - per-instance usable-gate read:
        - `611`: `1` neutral, `2` context-only
        - `1111`: `2` positives, `1` neutral
        - `1511`: `3` neutrals, `1` negative
  - current interpretation:
    - candidate3 is no longer blocked mainly by replay fidelity on the narrowed
      saved-surface lane
    - candidate3 exact saved-surface evidence is mixed and small-effect
    - stable or near-stable saved-surface cases now read:
      - `1511/search7002`: neutral
      - `1511/search7003`: neutral
      - `1511/search7004`: small negative
      - `1511/search7005`: neutral
      - `611/search7004`: neutral
      - `1111/search7001`: neutral
      - `1111/search7002`: small positive
      - `1111/search7004`: small positive
    - drifted-lane context cases now read:
      - `611/search7001`: small positive versus control
      - `611/search7005`: small positive versus control
      - `1111/search7003`: neutral
      - `1111/search7005`: neutral
    - the exact `1111` family read is now:
      - stable or near-stable lanes:
        - `7001`: neutral
        - `7002`: small positive
        - `7004`: small positive
      - drifted lanes:
        - `7003`: neutral
        - `7005`: neutral
    - candidate3 now looks more specific to some `1111` conversion-failure
      lanes than to the panel broadly:
      - the only usable positive reads are on `1111`
      - the added usable `1511` lanes are neutral rather than positive
    - candidate3 remains a narrow positional reorder probe rather than an
      established solver improvement
  - candidate3 exact-lane coverage is now complete for the full supported fixed
    panel:
    - full supported exact matrix:
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
      - but the total panel read is still mixed and not strong enough for live
        promotion
  - candidate3 local policy-variant exploration is now complete on the exact
    saved-surface lane:
    - policy-variant matrix:
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
    - current one-seed interpretation:
      - `phaseb_topk_frontload_all_v1` is the strongest nearby local variant
      - it beats anchor-swap on `4` usable gates and loses on `2`
      - it especially improves `1511/search7002`, `1511/search7005`, and
        `1111/search7004`
      - it clearly hurts `611/search7003` and `611/search7004`
  - candidate3 retained-seed robustness sweep is now complete on the most
    informative usable lanes:
    - seed-sweep bundle:
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
  - no live run yet

### Panel-level integrated read

- The fixed panel shows real `instance x search-seed` structure.
- The panel is not behaving like one homogeneous block.
- The two solves are stage-3 solves, not stage35 conversions:
  - `1511/search7001`
  - `1411/search7003`
- Current best benchmark read:
  - `1511`
    - strongest positive reference case
  - `611`
    - best middle unsolved case
  - `1111`
    - clearest fragmented late-region conversion-failure case
  - `1411`
    - mixed solvable case with a solved-run family-mapping caveat

### Fixed interpretation rules

- `focus family` means:
  - family of the top stage35-admitted row in that run
- Keep these stage35 count fields separate everywhere:
  - `archive_seed_row_count`
  - `best_stage35_seed_row_count`
  - `space_map_stage35_row_count`
- Do not collapse those three counts into one generic stage35 count.
- The solved-run family-mapping caveat is real and must stay explicit:
  - `1411/search7003`
    - `archive_seed_row_count = 6`
    - `best_stage35_seed_row_count = 0`
    - `space_map_stage35_row_count = 0`
  - `1511/search7001`
    - `archive_seed_row_count = 5`
    - `best_stage35_seed_row_count = 0`
    - `space_map_stage35_row_count = 0`

### Background analysis status

- `score_stop_shadow_v2` is frozen review-ready background.
- `late_family_quality_v1/v2/v3` are frozen review-ready background.
- `seed_family_triage_shadow_v1` is frozen review-ready background.
- Those branches remain useful context, but they are no longer the active
  coding stream.

## Current active focus

1. `fixed_instance_solver_development_v1`
   - primary tuning trio:
     - `1511`
     - `611`
     - `1111`
   - caveated cross-check case:
     - `1411`
   - completed outputs:
     - baseline digest
     - `1111` conversion-failure audit
     - `1511` positive-control audit
     - `611` middle-case audit
     - `1411` caveat note
     - candidate solver-change shortlist
     - candidate 1 code implementation
     - candidate 1 retained replay check
     - candidate 1 no-harm outcome refinement
     - candidate 3 whole-panel anchor-swap shadow bundle
   - current bundle:
     - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160503Z__fixed_instance_solver_development_v1/`
   - candidate verification bundle:
     - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160357Z__candidate1_guard_accept_611_search7005_replay_v1/`
   - current exact-control bundle:
     - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T163546Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`
   - prior shareable planning/results review pack:
     - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_instance_solver_development_v1_review_pack_2026-04-17/`
     - zip:
       - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_instance_solver_development_v1_review_pack_2026-04-17.zip`
   - current candidate3 closure/review pack:
     - `planning/projects/no_wli/40_review_summaries/no_wli_candidate3_review_pack_2026-04-18/`
     - zip:
       - `planning/projects/no_wli/40_review_summaries/no_wli_candidate3_review_pack_2026-04-18.zip`
   - candidate3 closure note:
     - `planning/projects/no_wli/40_review_summaries/no_wli_candidate3_closure_decision_note_2026-04-18.md`
2. Frozen benchmark basis
   - main panel pack:
     - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
   - `1111` supplement:
     - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`
   - cross-seed plus `1111` focus-family supplement:
     - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`
3. Completed infrastructure branch preserved as baseline
   - frozen plan:
     - `planning/projects/no_wli/20_active_plans/no_wli_fixed_instance_mode_infrastructure_plan_2026-04-08.md`
   - frozen contract:
     - `planning/projects/no_wli/30_analysis_specs/no_wli_fixed_instance_mode_v1_spec_2026-04-08.md`

### Next active solver-development line

The richer-pool downstream replacement reopen is now complete and closed:

- completed exact-lane bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260422T015033Z__phasec_richer_pool_phaseb_replacement_reopen_v1/`
- closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_phasec_richer_pool_replacement_reopen_closure_note_2026-04-22.md`

Closure read:

- richer-pool `source_order` stayed at `0.750`
- reorder floor `phaseb_topk_frontload_all_v1` reached `0.754`
- replacement widths `1`, `2`, and `3` all stayed at `0.750`
- all replacement widths changed saved-start membership and order
- none changed the winner or beat the reorder floor

So the branch-point lesson is now explicit:

- the richer supply retake was scientifically real
- narrow downstream `phaseB_topk`-only replacement was still not solver-usable
- downstream replacement is now closed on this richer pool

The rescaled one-job entry-allocation probe is now also closed:

- latest closed probe plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_plan_2026-04-22.md`
- latest probe closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_closure_note_2026-04-22.md`
- prior paired-canary closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_fixed_canary_operational_closure_note_2026-04-22.md`
- mechanism layer:
  - `allocation`
- closed probe cell:
  - `1111/search7004`

Closed probe read:

- experiment id:
  - `tune_v78_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_probe_1job`
- child run dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T154043010456Z__bench_solve_pipeline_no_wli__ee62083/`
- process outcome:
  - manually stopped after running past the written `~8h` stop rule
- completed Phase-C starts before stop:
  - `4 / 6`
- best completed start:
  - final match `0.432`
  - final score `0.17955717672334726`
- retained fixed `1111/search7004` mapped-family max:
  - final match `0.432`
- interpretation:
  - the probe reproduced the retained anchor-family best
  - it did not show a new top-line lift
  - the completed non-anchor starts were weaker

Structural lesson:

- this exact config was too weak to test the suspicion honestly
- with:
  - base entry budget `64`
  - `phase_b_top_n = 32`
  - `mutations_per_promoted = 1`
- the maximum theoretical Stage-3 entry target was only:
  - `66`
- so the configured cap `288` never mattered
- the exact probe shape could widen entry by at most:
  - `+2` keys over legacy

Scientific-method role:

- the branch did learn a useful methods correction
- stop decisions can rely on partial evidence here
- future allocation studies must prove structural activation before launch
- if that proof cannot be made cheaply, the next branch should move earlier
  than entry allocation

Closed candidate config:

- bounded baseline carry-forward with only these entry changes:
  - `force_stage3_init_keys_cap = 288`
  - `force_stage3_entry_allocation_policy = "constant_local_depth"`
  - `force_stage3_entry_mutations_per_promoted = 1`

Why this cell:

- `1111` remains the main conversion-failure family
- retained fixed `1111/search7004` has an exact wallclock anchor of about
  `2.36h`
- `1111/search7002` is no longer allowed as the default cheap follow-up cell
  because the richer-supply family stretched that seed to about `18.81h`

Runtime budgeting reference:

- `planning/projects/no_wli/20_active_plans/no_wli_runtime_budgeting_reference_note_2026-04-20.md`

Status of the last entry-allocation canary:

- experiment id:
  - `tune_v76_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_compare_2job`
- current read:
  - the live process was killed intentionally
  - no active multi-hour no-WLI runtime is currently confirmed from repo state
  - the matrix wrapper never advanced beyond `job_started`
  - no completed-job artifacts were written
  - so the candidate never ran
- rescued partial control evidence:
  - child run dir:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T024910116301Z__bench_solve_pipeline_no_wli__ee62083/`
  - completed Phase-C starts before kill:
    - `5 / 6`
  - watcher-log last line before kill:
    - Phase C start `6 / 6`, step `73 / 96`
  - best rescued control read:
    - source `stage3_best_phaseA`
    - final match `0.432`
    - final score `0.17955717672334726`
  - current interpretation:
    - control fidelity looked good
    - the two-job live canary shape did not

Closed probe implementation surface:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1.py`
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1.py`
- launchers:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_launch_2026-04-22.ps1`
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_open_terminal_2026-04-22.ps1`

Contingent same-family follow-on:

- closed plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_plan_2026-04-22.md`
- closed target:
  - fixed `1111/search7005`
- queue watcher log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_queue_2026-04-22.log`
- final queue outcome:
  - queue aborted at the cutoff because `v76` never completed the first job
  - `1111/search7005` never launched
- current branch read:
  - this follow-on is now closed as a non-launch
  - once the `7004` probe closed as an underpowered non-signal, there was no
    honest replication gate left to preserve

Next honest move:

- keep the killed `v76` session as rescued partial control evidence only
- keep the one-job `v78` probe closed as an over-budget, structurally
  underpowered shape
- do not rerun this exact `constant_local_depth` probe configuration
- require a written structural-activation proof before any further allocation
  runtime
- keep generic family-diversity and entry-allocation runtime closed for now
- keep the upstream selector line narrowed and now gated after the Phase-A
  competitiveness audit and operational gate microprobe
- the current next concrete branch should be:
  - a selector-checkpoint synthesis / review note
  - or, if experimentation resumes after review, one separately budgeted live
    canary decision

## Current non-claims

- No new broad fixed panel should start yet.
- No new live-seed sweep is active.
- No stop-rule promotion is implied by the fixed-panel review.
- Candidate 3 is operationally closed without promotion.
- Candidate 3 exact saved-surface evidence is now mixed rather than blocked:
  - full supported panel exact coverage:
    - `10` usable decision gates:
      - `3` positives
      - `6` neutrals
      - `1` negative
    - `9` drifted context lanes remain non-decision-gates
- Candidate 3 now reads as a mixed, case-dependent Phase-C ordering family:
  - there is one clean middle-case usable positive on `611/search7003`
  - the strongest nearby local variant is `phaseb_topk_frontload_all_v1`
  - but the retained-seed sweep still shows case- and seed-dependent
    preferences rather than a promotable general rule
- Candidate 3 should not receive another broad overnight replay batch or a
  final narrow confirmation run from the current evidence.
- Candidate 3 should not be described as an established solver improvement.
- Candidate 3 saved-surface decision gates are not equally strong across cases:
  - require control-lane fidelity, not just candidate-minus-control deltas
- Candidate 3 code and exact-lane tooling stay as analysis reference only.
- No family-quality head is promoted.
- No benchmark expansion is active.
- No blended stage35 count should be used as a headline metric.

## Immediate next move

- Keep the current fixed panel and supplements frozen as the benchmark basis.
- Candidate 1 is now the chosen first controlled change:
  - guard-aware stage35 followup acceptance
- Candidate 1 retained verification on `611/search7005` is now split cleanly:
  - stage35-only replay stays negative at `0.572`
  - run-level no-harm projection keeps the final best at retained
    `stage3_full_refine / 0.585`
- review cleanup is now landed:
  - `NaN` stage35 truth does not auto-promote stage35 to final best
  - selector-rescued accepts are explicit
- Do not run candidate 1 live in the current form.
- Candidate 2 first-form retained evidence:
  - shadow bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T031527Z__candidate2_top_family_reinforce_shadow_v1/`
    - useful narrowing only; not the decisive practical surface
  - exact replay probes:
  - `611/search7005` candidate exact:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T044904Z__candidate2_top_family_reinforce_611_search7005_exact_stage3_replay_v1/`
    - replay best `0.535`; `phaseB_family_reservation_applied = 0`
  - `611/search7005` exact control:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T053515Z__candidate2_top_family_exact_control_611_search7005_stage3_replay_v1/`
    - same replay best `0.535`
  - `1111/search7004` candidate exact:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T060743Z__candidate2_top_family_reinforce_1111_search7004_exact_stage3_replay_v1/`
    - replay best `0.406`; `phaseB_family_reservation_applied = 0`
- Current exact read:
  - the exact replay path works with longer runtime
  - the current candidate2 hook has not engaged on the retained cases tested so
    far
  - the mismatch is now clearer:
    - the saved-pool shadow check looked at `phaseC_candidate_pool_rows`
    - the live Phase-B hook acts on the already selected Phase-B rows
    - on the tested exact replays that selected surface is `32` families across
      `32` rows, so there is nothing for `reinforce_top_family_v1` to
      reallocate
  - the cheaper whole-panel selected-surface diagnostic now agrees:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T064934Z__candidate2_phaseb_selected_surface_v1/`
    - all `20` retained runs have `32` selected Phase-B rows and `32`
      preserved families
    - engageable runs under the current lever: `0`
- Candidate 2 replacement-form retained evidence:
  - whole-panel anchor-family shadow bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T145401Z__candidate2_anchor_family_reserved_shadow_v1/`
  - retained panel read:
    - `19/20` runs have saved Phase-C candidate-pool surface
    - runs with saved anchor-family room: `0`
    - replacement candidate2 shadow live on panel: `0`
    - baseline Phase-C starts already include the available anchor-family rows
      on the frozen panel
- Do not run candidate 2 live in either current form.
- Do not spend more exact replay time on the candidate2 family-aware-budget line
  as currently specified.
- Candidate 3 is now operationally closed:
  - decision note:
    - `planning/projects/no_wli/40_review_summaries/no_wli_candidate3_closure_decision_note_2026-04-18.md`
  - review pack:
    - `planning/projects/no_wli/40_review_summaries/no_wli_candidate3_review_pack_2026-04-18/`
  - do not promote either anchor-swap or frontload-all to live runtime from the
    current evidence
  - do not run another broad overnight replay batch
  - do not schedule a final narrow confirmation run
  - carry forward the methodological lesson:
    - saved-surface exact lanes are useful when full replay drift blocks fair
      judgment
    - future follow-on rules should be explicit, conditioned, and built around
      stable decision gates
  - move to the next paradigm or a consciously designed conditioned rule rather
    than extending candidate3 as an open line

## 2026-04-29 current active runtime

- Current branch:
  - Stage 3.5 resume-from-handoff local rescue
- Completed broad shallow data-taking:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/`
  - `136 / 136` cells completed in `721.112s`
  - `73` accepted positives versus selected-row start
  - `18` accepted regressions
  - rank-6 slice:
    - `19 / 22` positives
    - `0 / 22` negatives
    - best delta `+0.458`
- Latest completed run:
  - focused deepening harvest on strongest shallow-positive cells
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_selector_frontier_deepening_harvest_v1.py`
  - console log:
    - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_selector_frontier_deepening_harvest_2026-04-29.log`
  - budget:
    - `8h` wallclock
    - `1800s` per-cell cap
    - `36` max cells
  - result:
    - completed normally before the wallclock cap
- Current recommendation:
  - use the deepening harvest to decide whether rank-6/local-rescue is worth a
    narrower policy design
  - do not promote unfiltered guard-selector, because the shallow broad harvest
    admitted regressions

Completed result:

- deepening output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/`
- closeout:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/stage35_guard_selector_frontier_deepening_closeout.md`
- completed:
  - `15 / 15` cells
- elapsed:
  - `1919.390s`
- better than shallow:
  - `12 / 15`
- worse than shallow:
  - `3 / 15`
- mean delta versus shallow:
  - `+0.007533`
- carried conclusion:
  - deepening is a real but modest positive
  - next work should be offline join/dedup and rank-6 safety characterization,
    not another broad runtime batch
- Completed offline join/dedup:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/`
  - `14` unique joined rows after removing `1` duplicate key
  - `11 / 14` better than shallow
  - `3 / 14` worse than shallow
  - rank `6`: `10 / 12` better, `2 / 12` worse
  - posthoc candidate gate:
    - `rank6_selected_start_ge_0p437`
    - `6 / 6` better
    - `0 / 6` worse
- Current recommendation:
  - treat `selected_start_match_ratio >= 0.437` as a posthoc safety-gate
    hypothesis, not a promoted policy
  - do offline rule design before any more runtime
- Completed rank-6 selected-start gate safety check:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T014439Z__stage35_rank6_selected_start_gate_safety_v1/`
  - gate: rank `6` and `selected_start_match_ratio >= 0.437`
  - deep kept rows: `6`
  - kept better/worse versus shallow: `6 / 0`
  - rejected better/worse versus shallow: `4 / 2`
  - observed rank-6 deepening regressions removed: `2 / 2`
  - rejected deepening positives: `4`
  - decision:
    - useful safety direction, too conservative to run as-is
    - next step is a predeclared softened/combined policy sketch, not runtime
- Prediction ledger:
  - stored for comparison only, not blame assignment
  - when this analysis branch closes, compare final outcome against the
    prediction ledger in chat
- Offline policy sketch:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_local_rescue_policy_sketch_2026-04-30.md`
  - candidate:
    - rank `6`
    - `selected_start_match_ratio >= 0.437`
    - or `shallow_resume_minus_selected >= 0.400`
  - observed dedup result:
    - kept `7`
    - kept better/worse `7 / 0`
    - rejected better/worse `3 / 2`
  - no runtime is authorized from this sketch alone
- Canary design:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_local_rescue_canary_design_2026-04-30.md`
  - exact four-cell design is written
  - budget if approved later:
    - `45m` intended wallclock
    - `2700s` hard cap
    - `600s` per-cell rescue cap
  - current state:
    - no runtime launched
    - next step requires explicit approval to implement/run the canary
- Approved launch:
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_local_rescue_canary_v1.py`
  - console log:
    - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_canary_2026-04-30.log`
  - budget:
    - `45m` intended wallclock
    - `2700s` hard cap
    - `600s` per-cell rescue cap
  - status:
    - completed
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T015732Z__stage35_rank6_local_rescue_canary_v1/`
  - result:
    - `4 / 4` cells completed
    - `2` executed rescue cells
    - `2` policy skips
    - `0` errors
    - `0` policy decision mismatches
    - `2 / 2` executed cells nonnegative versus shallow
    - elapsed `183.535s`
  - current recommendation:
    - no broad runtime
    - next runtime, if any, should be a small same-rule recall/audit microbatch
      around rejected-positive boundary behavior
- Current launch:
  - same-rule rank-6 local-rescue recall/audit microbatch
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_local_rescue_recall_audit_v1.py`
  - console log:
    - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_recall_audit_2026-04-30.log`
  - budget:
    - `45m` intended wallclock
    - `2700s` hard cap
    - `600s` per-cell rescue cap
  - status:
    - completed
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T021919Z__stage35_rank6_local_rescue_recall_audit_v1/`
  - result:
    - `5 / 5` completed
    - `0` errors
    - `3` audit positives versus shallow
    - `2` audit regressions versus shallow
    - `5 / 5` reproduced prior deepening exactly
  - current recommendation:
    - no more runtime until an offline boundary-feature extractor compares the
      three rejected positives against the two rejected regressions
- Completed boundary-feature audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T032952Z__stage35_rank6_boundary_feature_audit_v1/`
  - revision note:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_boundary_rule_revision_note_2026-04-30.md`
  - result:
    - `27` numeric features scanned
    - `172` threshold sketches scanned
    - `0` perfect one-feature separators
  - current decision:
    - stop runtime on this branch
    - no policy promotion
    - next work, if any, is offline feature expansion with route-composition or
      family/lineage context
- Completed route-lineage boundary audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T033637Z__stage35_rank6_route_lineage_boundary_audit_v1/`
  - review note:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_boundary_review_note_2026-04-30.md`
  - result:
    - `5` boundary rows
    - `3` positives
    - `2` regressions
    - `0` perfect single-feature separators
    - `141` perfect two-feature separators
  - most interpretable separator family:
    - source rank `1`
    - and high route novelty, e.g.
      `candidate_novelty_distance_to_anchor >= 173.5`
  - current decision:
    - wait for external review
    - no runtime running
    - no policy promotion
  - current recommendation:
    - if review accepts the lineage signal, write a tiny held-out/disagreement
      confirmation design before any runtime
    - otherwise close the rank-6 policy line as mechanism insight
  - review pack:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_review_pack_2026-04-30/`
  - zipped review pack:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_review_pack_2026-04-30.zip`
  - paired source bundle:
    - `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260430T041152Z.zip`
- Review action completed:
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
    - rule disagreements:
      - `9`
    - group A old reject / route keep:
      - `4`
    - group B old keep / route reject:
      - `5`
  - current recommendation:
    - inspect group A and B against existing shallow/deep evidence
    - if coherent, write a fixed-rule tiny confirmation design
    - no runtime without explicit approval

- Route-lineage additive confirmation:
  - design note:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_additive_confirmation_design_2026-04-30.md`
  - closeout:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_additive_confirmation_closeout_2026-04-30.md`
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_route_lineage_additive_confirmation_v1.py`
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153119Z__stage35_rank6_route_lineage_additive_confirmation_v1/`
  - result:
    - `4 / 4` cells completed
    - `0` errors
    - elapsed `287.159s`
    - `3 / 4` nonnegative versus shallow
    - `1 / 4` regressed versus shallow
  - key safety failure:
    - `1111/search7001 rank 6 d94845511e181f7c`
    - shallow `0.038`
    - confirmation `0.037`
    - delta `-0.001`
  - current decision:
    - close current source-rank plus route-novelty rule as a policy candidate
    - do not launch a wider union-policy runtime
    - carry route-lineage forward only as mechanism evidence

- Latest branch closed:
  - branch:
    - `stage3_entry_const_local_depth_handoff_resume`
  - reason:
    - constant-local-depth remains unanswered because the prior full-pipeline
      panel completed only a control job
    - saved handoff artefacts allow one-cell Stage-3 resume without full
      pipeline recompute
  - activation output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022336Z__stage3_entry_const_local_depth_handoff_activation_v1/`
  - activation result:
    - `3 / 3` target handoffs structurally active
    - `3 / 3` mechanism-widened
    - legacy init3 `64`
    - candidate init3 `288`
    - candidate new init3 keys `80`
    - candidate missing legacy keys `0`
  - launch/closeout plan:
    - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_handoff_resume_plan_2026-05-01.md`
  - closeout:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_handoff_closeout_2026-05-01.md`
  - first runtime cell:
    - `1111/search7005`
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_handoff_7005_v1.py`
  - console log:
    - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_handoff_7005_2026-05-01.log`
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/`
  - first result:
    - retained `0.372`
    - candidate `0.374`
    - delta `+0.002`
    - elapsed `7139.745s`
  - second runtime cell:
    - `1111/search7004`
  - second output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/`
  - second result:
    - retained `0.423`
    - candidate `0.406`
    - delta `-0.017`
    - elapsed `7755.439s`
  - current decision:
    - close this exact constant-local-depth handoff-resume shape as a policy
      candidate
    - do not launch `1111/search7002` for this exact branch
  - current recommendation:
    - downstream-selection audit completed:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T155731Z__stage3_entry_const_local_depth_downstream_selection_audit_v1/`
    - posthoc Stage 3.5 accept-pass fallback gate is clean on `7005/7004`
      but failed a broader offline stress test:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T160206Z__stage35_accept_gate_broader_offline_audit_v1/`
      - `151` rows
      - `75` negatives versus retained
      - `18` negatives versus selected start
    - current recommendation:
      - close Stage 3.5 accept-pass as a general safety gate
      - no runtime from this line

- Latest completed run:
  - branch:
    - `stage35_frontier_space_robustness_harvest_v1`
  - mechanism:
    - local search / rescue
  - plan:
    - `planning/projects/no_wli/20_active_plans/no_wli_stage35_frontier_space_robustness_harvest_plan_2026-05-01.md`
  - runner:
    - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_frontier_space_robustness_harvest_v1.py`
  - console log:
    - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_frontier_space_robustness_harvest_2026-05-01.log`
  - budget:
    - `8h` wallclock
    - `1800s` per-cell cap
    - `48` max cells
  - stop condition:
    - queue exhausted, wallclock cap reached, or first-cell projection over
      budget
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T161846Z__stage35_frontier_space_robustness_harvest_v1/`
  - closeout:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_frontier_space_robustness_harvest_closeout_2026-05-01.md`
  - result:
    - `48 / 48` cells completed
    - `0` errors
    - elapsed `12602.918s`
    - selected rows `32 / 48`
    - selected rows better/worse than shallow:
      - `27 / 3`
    - selected rows nonnegative/negative versus selected start:
      - `28 / 4`
  - prediction comparison:
    - rank-6 held-out positives mostly remained useful among accepted rows
    - shallow-negative and shallow-neutral strata stayed mixed
    - rank `1-5` moderate positives were cleaner than expected among accepted
      rows, but still had guard failures
  - current recommendation:
    - promote no policy directly from this harvest
    - do not launch another broad local-rescue runtime batch immediately
    - offline acceptance-boundary extractor completed:
      - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T235632Z__stage35_frontier_space_acceptance_boundary_audit_v1/`
      - accepted positives:
        - `28`
      - accepted regressions:
        - `4`
      - guard failures:
        - `16`
      - perfect single-rule separators:
        - `0`
      - perfect two-feature separators:
        - `0`
    - close broad local-rescue policy widening for now
    - next work should move up a level unless a genuinely held-out validation
      design is written first

- Current external-review handoff:
  - synthesis:
    - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_synthesis_2026-05-02.md`
  - review pack folder:
    - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_review_pack_2026-05-02/`
  - nested source bundle inside pack:
    - `90_source_bundle/get_src_extended_review_bundle__20260502T022329Z.zip`
  - sendable zip:
    - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_review_pack_2026-05-02.zip`
  - carried recommendation:
    - do not start another broad runtime batch from the current local-rescue
      surface
    - next best work is an experiment ledger / oracle-gap layer, or a held-out
      validation harness for the Stage-2 checkpoint line

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

Current implementation status:

- local full raw payload validation script exists and the local copy validated
  `pass` with `2236 / 2236` payload files checked, `0` missing files,
  `0` hash mismatches, and `0` byte-count mismatches.
- compact full raw phrase lookup builder and validator exist with focused
  synthetic tests.
- fast runtime index builder and validator now use grouped `.npz` files by
  direction/order/cut/phrase length/word length shape, not the old
  sample-mode phrase index.
- Lane 2 now blocks unless the requested `fast_runtime_index` exists and
  validates; it does not silently fall back to `phrase_index_v1` or raw shards.
- DJ-MINI full payload validation is running from the remote repo copy with log:
  `planning/projects/no_wli/50_console_and_watch_logs/djmini_full_raw_local_payload_validation_2026-06-01.log`
- DJ-MINI full payload validation completed `pass` with `2236 / 2236`
  payload files checked and zero missing/hash/byte mismatches.
- The first monolithic compact build attempt was stopped during the first
  `fwd/order=2/cut=normal` group after early throughput projected the full
  `1,115,443,486`-row aggregation beyond the declared `12h` watchdog budget.
  Partial compact output was removed. The next implementation step is a
  bounded or partitioned compact-build strategy with extractable partial state,
  not a silent day-long monolithic run.
- A partitioned DuckDB compact build with `5` source files per partition
  completed the first persisted group:
  `direction=fwd/order=2/cut=normal`.
  It wrote `100,107,793` compact rows, found `0` duplicate identities, and
  took `6338.39s`.
- The resumed compact build has also completed:
  `direction=fwd/order=2/cut=strict`.
  It wrote `34,812,511` compact rows after dedup and took `2061.6s`.
- Current active compact group is `direction=fwd/order=3/cut=normal`.
- That completed group is retained and is the timing anchor for the resumed
  build. The resumed DJ-MINI launch is:
  `planning/projects/no_wli/60_launch_scripts/djmini_phaseB_full_raw_compact_lookup_resume_36h_2026-06-01.ps1`.
- The resumed build log is:
  `planning/projects/no_wli/50_console_and_watch_logs/djmini_full_raw_compact_lookup_duckdb_partitioned5_resume_36h_2026-06-01.log`.
- The resumed build has a declared `129600s` budget and stop condition
  `finish_or_operator_stop_at_wallclock_budget`. It must continue to emit
  partition-level progress and must not silently restart completed groups.
- The post-compact follow-on launcher is prepared but must only be run after
  compact completion:
  `planning/projects/no_wli/60_launch_scripts/djmini_phaseB_post_compact_to_review_gate_2026-06-01.ps1`.
  It stops on the first failed gate across compact validation, fast runtime
  index build, runtime validation, Lane 2 rerun, and review-pack build.
- 2026-06-01 local-build correction: DJ-MINI is not the active asset build
  target. Completed order-2 compact artifacts were copied back into the local
  repo and hash-verified against their complete markers:
  `direction=fwd/order=2/cut=normal` and
  `direction=fwd/order=2/cut=strict`.
- The active compact build now runs from the local repo and writes local output:
  `planning/projects/no_wli/60_launch_scripts/local_phaseB_full_raw_compact_lookup_resume_36h_2026-06-01.ps1`.
- Local launch log:
  `planning/projects/no_wli/50_console_and_watch_logs/local_full_raw_compact_lookup_duckdb_partitioned5_resume_36h_2026-06-01.log`.
- Local free space at launch was about `36.51 GB`; if the local disk fills,
  stop and tidy local storage rather than falling back to DJ-MINI.
- 2026-06-02 compact lookup completion: the local compact build finished with
  status `built`, exit code `0`, and total elapsed `95412s`.
- Compact lookup manifest:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1/compact_asset_manifest.json`.
- Total compact rows before dedup: `1,115,443,486`.
- Total compact rows after dedup: `1,115,443,486`.
- Duplicate identity count: `0`.
- Completed compact group sizes:
  - `fwd/order=2/cut=normal`: `100,107,793` rows, `7,231,028,751` bytes.
  - `fwd/order=2/cut=strict`: `34,812,511` rows, `2,551,739,985` bytes.
  - `fwd/order=3/cut=normal`: `614,144,142` rows, `43,573,129,550` bytes.
  - `fwd/order=3/cut=strict`: `366,379,040` rows, `26,084,568,434` bytes.
- The compact builder removed temporary partition CSVs; only group completion
  marker JSON files remain under the compact `work/` directory.
- Next local gate launcher:
  `planning/projects/no_wli/60_launch_scripts/local_phaseB_post_compact_to_review_gate_2026-06-02.ps1`.
  It runs compact validation, fast runtime index build, runtime validation,
  Lane 2 diagnostic rerun, and review-pack build in order.
- 2026-06-02 runtime-index preflight: the fast runtime `.npz` builder now
  writes bounded chunks with `MAX_RUNTIME_ROWS_PER_FILE = 1,000,000`.
  This avoids holding very large phrase-length/word-shape groups in memory.
  The runtime validator enforces that cap before Lane 2 can use the index.
- Focused tests passed after the chunking update:
  `tests/tools/test_phaseB_ngram_hamming_fast_runtime_lookup_index_v1.py`,
  `tests/tools/test_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_validation_v1.py`,
  and `tests/tools/test_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1.py`.
- Compact validation now also reports hash-pass progress every `512 MiB`;
  the original gate launch was stopped before completion because that hash
  pass was too silent for a long validation run.
- Compact validation duplicate checks are now constant-memory: because compact
  rows are deterministically sorted by the canonical identity fields, duplicate
  phrase IDs and canonical identities are checked by adjacency rather than by
  retaining billion-row seen sets.
- 2026-06-03 post-compact gated run completed:
  - launcher status: `review_gate_ready_or_review_pack_blocked_by_manifest`
  - total elapsed: `75,342s`
  - local free space at finish: `103.28 GB`
  - compact validation: `pass`, `4` files and `1,115,443,486` rows checked,
    `0` failures
  - fast runtime index build: `built`, `2,222` bounded `.npz` chunks and
    `1,115,443,486` phrase rows indexed
  - fast runtime index validation: `pass`, `0` failures
  - runtime payload size: about `71.30 GB`
  - compact payload size: about `79.44 GB`
- Lane 2 diagnostic rerun completed safely from `fast_runtime_index`, but its
  evidence is blocked and must not be interpreted as scorer failure:
  - `388` cases, `128` selected phrase entries, `0` raw hits
  - runtime loader selected only phrase length `3` for both order-2 cuts and
    phrase length `5` for both order-3 cuts
  - active profiles require minimum phrase lengths `7`, `8`, or `10`
  - therefore every profile had `0` allowed/considered phrase entries
  - review pack status: `packed_with_blocks`
- Required next step: correct the bounded diagnostic selection so every active
  profile/order/cut receives eligible entries at or above its minimum phrase
  length, add a fail-closed assertion against zero eligible entries, rerun
  Lane 2 diagnostics, and rebuild the review pack. Do not rebuild compact or
  runtime assets.

## 2026-06-03 Lane 2 profile-aware rerun and review gate

- The profile-aware runtime selector is implemented and fail-closed.
- All `10` active profile/order/cut buckets met their requested selection count
  and minimum phrase length.
- Selected runtime entries: `144`.
- Lane 2 rerun status: `diagnostic_evidence_ready_for_review`.
- Selection contract: `pass`.
- Opportunity contract: `pass`.
- Controlled corpus: `580` cases, including `36` clean positives, `144`
  positives including damage tiers, `432` matched nulls, and `1` standalone
  hard-negative surrogate.
- Raw diagnostic hits: `1,576`.
- Profile-specific summary populations now include only each profile bucket's
  own positives and matched nulls; unrelated positives no longer dilute the
  medians.
- Canonical order-3 normal candidate evidence:
  - clean: median `4` clusters versus null median `0`
  - `20%` damage: median `3` clusters versus null median `0`
  - `35%` damage: median `2` clusters versus null median `0`, but overlap and
    false-positive rate at the positive threshold are both `1.0`
  - `50%` damage: no separation
- Current review pack status: `packed_review_ready`, compact validation `pass`,
  runtime validation `pass`.
- Review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_selection_fixed_review_pack_2026-06-03.zip`
- The older `phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_2026-06-01.zip`
  filename is superseded and must not be sent for the current review.
- Current comprehensive pack: `73` entries, `755,608` compressed bytes,
  all `144` selected input phrases, all `1,576` hit rows, relevant source,
  tests, compact/runtime manifests and validation evidence, and zero missing
  files.
- Next decision belongs at review: proceed to report-only integration, revise
  diagnostics/cluster definitions, wait for order 4, collect more evidence, or
  redesign. No production scoring change is approved.

## 2026-06-03 external review decision

- The selection-fixed Lane 2 evidence, compact asset, runtime index, selection
  contract, and opportunity contract are accepted.
- Approved next implementation: narrow opt-in N3C-normal-equivalent
  report-only telemetry with `production_rank_effect = none`.
- Approved next diagnostic: separate Lane 2B length/shape-stratified evidence.
- Approved planning work: order-4 size/readiness assessment.
- Not approved: production ranking, score blending, tie-break, bounded
  override, broad scan, order-2 scoring, threshold changes, or S3W claims.
- Current external pack needs pack-only/evidence-clarity cleanup before further
  distribution; no compact/runtime rebuild is required.
- Review decision record:
  `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane2_selection_fixed_external_review_decision_2026-06-03.md`

## 2026-06-03 post-review implementation

- Current external pack cleanup completed:
  - stale blocked gate log removed
  - complete and sampled hit rows distinguished
  - complete diagnostic and boundary case views added
  - portable optional-extension test wording added
  - threshold status now distinguishes usable, fragile, and no-separation
- Lane 2B length/shape-stratified diagnostic completed:
  - selection buckets: `10/10` pass
  - selected entries: `208` unique, covering three length strata per bucket
  - cases: `964`
  - clean positives: `60`
  - positives including damage tiers: `240`
  - matched nulls: `720`
  - raw hits: `2,942`
  - canonical N3C-normal clean and 20% thresholds remain usable
  - 35% is fragile; 50% is no-separation
- Isolated N3C-normal report-only telemetry contract implemented:
  - defaults disabled
  - validated fast-runtime source required
  - old/sample/raw-shard runtime sources fail closed
  - `production_rank_effect = none`
  - no score blending, tie-break, override, or solver integration
- Order-4 sizing completed from DJ-MINI retained evidence:
  - validated raw asset: `1,037,043,475` rows
  - compact canary: pass
  - full compact prep: `50/800` partitions and about `72.12 GB` retained
  - full build blocked pending temporary-space and incremental-cleanup strategy
- Order-4 sizing plan:
  `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_order4_size_and_readiness_plan_2026-06-03.md`
- Next review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane2b_stratified_telemetry_order4_sizing_review_pack_2026-06-03.zip`
- Next review pack status: `packed_review_ready`, `102` entries, about
  `1.13 MB`, no stale blocked gate log.
- Relevant post-review closure: `92 passed` with the optional fast extension;
  expected portable result is `77 passed, 15 skipped` without it.

This work does not approve production scoring.
This work does not approve broad candidate scans.
This work does not promote order 2 to score-bearing.
This work does not reject order 4 or order 5.

Lane 2B has run a small post-review diagnostic microbatch and is stopped at review.

## 2026-06-04 external-review implementation

- External review accepted Lane 2B and approved actual report/export wiring for
  opt-in N3C-normal telemetry with zero rank effect.
- The report-only telemetry is now wired into:
  - retained-candidate scorer reports
  - benchmark scorer-report JSONL sidecar exports
- The wiring runs only after the candidate score exists, remains absent unless
  an explicit report config is supplied, and preserves the dedicated
  `production_rank_effect = none` report section.
- Focused report/export and order-4 hold closure: `35 passed`, including real retained-candidate
  fixtures, JSONL export, and identical score/order assertions with telemetry
  disabled and enabled.
- Full relevant repo closure: `107 passed`.
- Fresh extracted reduced-pack reproduction: `81 passed, 15 skipped`; all
  skips are the optional C++ extension tests.
- The two included retained-state/sidecar integration tests are explicitly
  labelled full-repo-dependent; the portable subset is duplicated under
  `30_source/tests` for normal pytest discovery without `PYTHONPATH`.
- Report telemetry now states
  `report_authority = report_only_telemetry`.
- Separate order-4 machine-readable readiness evidence is available at:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_order4_build_readiness_hold_v1/`
- Order-4 evidence status remains `hold_not_approved`; full build, production
  scoring, and production ranking changes remain unapproved.
- Current review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_report_wiring_order4_readiness_packaging_closed_review_pack_2026-06-04.zip`
- Current review pack status: `packed_review_ready`, `134` entries, about
  `1.19 MB`, zero missing files.
- Do not send or reuse the superseded ambiguous filename:
  `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_report_wiring_order4_readiness_review_pack_2026-06-04.zip`
- External review decision record:
  `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane2b_external_review_decision_2026-06-04.md`

This is not production scoring.

## 2026-06-04 failed-decryption retained-candidate fixture

- The missing historical partial-text review-pack wrapper was not found.
- Compact underlying outputs were recovered read-only from
  `F:/legacy/ready_for_archive/2026-06-01_repo_cleanup` and promoted into the
  canonical first-class local asset:
  `assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/`
- The asset is about `30 MB`, is no longer stored under cleanup-prone
  generated output, and contains preserved source plus the validated fixture.
- `assets/` remains intentionally Git-ignored; synchronize the complete
  versioned asset directory to other workstations.
- Inventory status: `pass`; `930` artifacts inspected, `637` candidate-like,
  and `2` compact structured source artifacts selected.
- Stable fixture status: `pass`:
  - `40` historical trials
  - `734` trial-specific retained candidates
  - `734` scoreable token chunks
  - `2,594` source-backed pairs
  - `604` distinct recovered token streams
- Fixture validation status: `pass`, `0` failures.
- Bounded N3C-normal report-only telemetry run status: `pass`:
  - `734/734` candidates reported
  - `2,594` source-backed pairs compared offline
  - phrase-entry scope: `48` Lane 2B selected bounded entries
  - full fast runtime index queried: `false`
  - candidates with hits: `0`
  - report-only pair preferences: `0`; ties: `2,594`
  - baseline scores preserved: `true`
  - baseline ordering preserved: `true`
  - production rank effect: `none`
  - validated fast runtime provenance required, but the full runtime index was
    not queried
- The zero-hit result is a bounded-canary coverage limitation. It is not
  evidence against N3C and must not be given ranking meaning.
- Before any full-runtime fixture scan, implement and size an efficient
  full-fast-runtime query path. Do not launch it as an unsized broad scan.
- First length-aware full-group canary:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1/`
  - searched `5` complete rare-shape groups across all five length buckets
  - searched `40` candidates, one per historical trial
  - found `250` fully verified N3C hits in `92` clusters
  - explicitly left `1,023` N3C groups unsearched
  - order-2 seeded regions missed `163` hits and `40` clusters
- Order 2 may prioritize query work but cannot filter/veto candidate regions.
- The next gate is a memory-bounded partition index with peak-memory
  measurement before medium/common groups. No review pack yet.
- Memory-bounded sorted-block index: parity pass.
- Largest selected medium group: `974,784` phrases, about `39.4` seconds over
  `40` candidates, about `373.9 MB` peak working set.
- Five-medium-group diverse-candidate microbatch:
  - `80` candidates across highest/middle baseline strata
  - `11,783` verified N3C hits and `2,830` clusters
  - about `366.5` seconds total and `599.4 MB` peak memory
  - status `blocked_budget_exceeded` because the `10-11` group took about
    `181.656` seconds against the declared `180`-second limit
- The exact vectorized verifier resolved the medium-query budget block without
  changing N3C semantics:
  - the isolated `10-11` group dropped from about `181.656` seconds to about
    `18.9` seconds with identical exact-hit semantics
  - the five-medium-group vectorized rerun passed in about `45.9` seconds
  - the five-common-shape canary passed in about `91.6` seconds
- The first full stratified query-planning study is now review-gate ready:
  - `40` complete N3C runtime groups
  - every length bucket has exactly `2` rare, `3` medium, and `3` common groups
  - `80` source-backed candidates across highest/middle baseline strata
  - `195,975` fully verified hits and `20,481` clusters
  - about `510.7` summed group-seconds and `718.4 MB` peak memory
  - bucket hits: `175,004`, `20,526`, `444`, `1`, `0` from shortest to longest
- Consolidated evidence:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_stratified_query_study_summary_v1/`
- Status: `review_gate_ready`. Stop before wider/full N3C or score-bearing work
  and request external review.
- Sendable review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_stratified_query_portable_closed_review_pack_2026-06-04.zip`
- Pack closure: under `50 MB`, source and full stratified hit evidence included,
  fresh extracted portable test scope `13 passed` without `PYTHONPATH`.
- Do not send the superseded
  `phaseB_failed_decryption_n3c_stratified_query_review_pack_2026-06-04.zip` or
  `phaseB_failed_decryption_n3c_stratified_query_packaging_closed_review_pack_2026-06-04.zip`.
- This remains a partial stratified query. Zero hits in the `18+` sample do not
  prove global absence.
- External review accepted the stratified query pack as a successful
  query-engine and stratified-yield study.
- Approved next phase:
  - complete full-runtime N3C query over the same `80`-candidate
    trial-balanced sample
  - do not expand to all `734` fixture candidates until that full-80 result is
    reviewed
- Required corrections before interpreting any score-like evidence:
  - logical group means `direction/cut/order/phrase length/word shape`, not an
    individual runtime chunk
  - global candidate-level N3C clusters must be computed after combining all
    searched N3C hits per candidate
  - per-chunk and per-logical-group clusters are diagnostic only
  - pairwise/gold rescue-break ledger must be emitted for the selected sample
  - hit rows must include phrase length, word shape, total HD, max word HD,
    word-HDs, and exact flag
  - runtime index and validation manifests must be included in the next pack
- New full-80 runner:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_full80_query_evidence_v1.py`
- Full-80 approved scope: `1,028` runtime chunks, `702` logical N3C groups,
  `613,280,613` phrase rows, `80` candidates. Intended wallclock budget:
  `12,600` seconds with `2,048 MB` peak-memory ceiling.
- Monolithic full-80 launch was stopped after `3/1,028` chunks because the
  first completed chunks projected beyond the declared `12,600` second budget.
  Partial output is preserved at:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_full80_query_evidence_v1/`
- Rescoped next run:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_full80_bucket_8_9_query_evidence_v1.py`
  over the complete `8-9` bucket only, with a `3,600` second cap. This is a
  budget anchor, not the complete full-80 result.
- Completed bucket anchors:
  - `8-9`: `41` chunks, `39` logical groups, `13,105,933` phrase rows,
    `1,373,314` hits, `291` global candidate clusters, `2,384.875` seconds,
    pairwise global-cluster result `4` agree / `10` break / `2` tie
  - `10-11`: `105` chunks, `67` logical groups, `59,023,845` phrase rows,
    `258,892` hits, `1,451` global candidate clusters, `2,177.859` seconds,
    pairwise global-cluster result `6` agree / `8` break / `2` tie
- Remaining bucket jobs completed in the visible serial runner:
  - `12-14`: `272` chunks, `143` logical groups, `195,100,675` phrase rows,
    `33,439` hits, `1,632` bucket-local global candidate clusters,
    `4,542.6` seconds
  - `15-17`: `317` chunks, `181` logical groups, `212,748,370` phrase rows,
    `1,922` hits, `314` bucket-local global candidate clusters,
    `3,202.8` seconds
  - `18+`: `293` chunks, `272` logical groups, `133,301,790` phrase rows,
    `150` hits, `41` bucket-local global candidate clusters, `2,329.8`
    seconds
- All five bucket runs together cover the approved full-80 N3C chunk scope:
  `1,028` chunks, `702` logical groups, `613,280,613` phrase rows, and
  `1,667,717` verified hits before cross-bucket candidate-cluster collapse.
- Next required work: consolidate all bucket hit rows into one full80 summary,
  recompute global candidate clusters across all buckets, merge the pairwise
  ledger, then build the next review pack.
- Consolidated full80 evidence is complete:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_full80_consolidated_evidence_v1/`
  - status: `full80_consolidated_evidence_ready_for_review`
  - true all-bucket global candidate clusters: `275`
  - exact global candidate clusters: `1,648`
  - pairwise results over the `16` in-sample labelled pairs:
    - hit count: `4` agree / `12` break
    - global clusters: `4` agree / `10` break / `2` tie
    - exact global clusters: `6` agree / `10` break
- Full80 review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_full80_consolidated_packaging_closed_review_pack_2026-06-05.zip`
  - status: `packed_review_ready`
  - entries: `91`
  - ZIP size: `806,518` bytes, under `50 MB`
  - backslash ZIP entries: `0`
  - full hit CSVs are referenced by manifest paths, row counts, sizes, and
    SHA-256 hashes rather than duplicated into the ZIP
  - fresh extracted consolidated portable test: `2 passed`
- Do not send superseded same-day full80 pack filenames without
  `packaging_closed`; the superseded same-day full80 pack folders and ZIPs
  were removed after the final packaging-closed archive passed validation.
- These bucket anchors confirm the query path is runnable but also confirm that
  simple raw hit counts and simple global-cluster counts are not safe scoring
  signals.
- Score-bearing use, production scoring, and production ranking remain not
  approved.
- Candidate ranks are unavailable and remain explicitly missing.
- Upstream matched-null anchor manifest is unavailable; matched-null generation
  remains blocked rather than invented.
- Canonical fixture asset:
  `assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/fixture/phaseB_failed_decryption_retained_candidate_fixture_v1/`
- Telemetry output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_fixture_n3c_report_telemetry_v1/`
- This work changes no production score or ranking.

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

Current controlled diagnostic evidence output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1/`
- phase label:
  - `phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1`
- run scope:
  - `post_review_microbatch`
- run authority:
  - `diagnostic_only`
- real candidate scan started:
  - `false`
- broad candidate scan started:
  - `false`
- production scorer change:
  - `false`

## 2026-06-05 v2 correction and S3 strict direction

The v2 handoff in
`planning/temp_files/n3c_normal_correction_strict_full80_v2/00_authoritative_v2_handoff.md`
supersedes the prior stop-at-review instruction for the normal full80 pack.

The earlier pack remains useful broad-reference evidence, but it is now
superseded as the corrected normal reference because it used exact-span
component counts and raw pair-row counts in places that needed
exact-containing ordinary clusters and unique semantic pairs.

Corrected normal reference:

- output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_evidence_v1/`
- corrected review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_review_pack_2026-06-05.zip`
- pack facts:
  - entries: `60`
  - ZIP size: `344,857` bytes
  - fresh extracted portable tests: `8 passed`
- normal query rerun: `false`
- verified hits: `1,667,717`
- ordinary global candidate clusters: `275`
- corrected exact-containing global candidate clusters: `225`
- raw selected-sample pair rows: `16`
- unique selected-sample semantic pairs: `8`
- rescue-capable unique semantic pairs: `0`

Engineering correction gate status:

- corrected annotated cluster aggregation implemented
- semantic pair IDs and break/rescue capability labels implemented
- S3 strict RunSpec selection test locks `815` chunks, `702` groups, and
  `365,516,232` phrase rows
- strict bucket scripts are ready under
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_*_query_evidence_v1.py`
- focused correction tests: `26 passed`

Next run direction: launch the five S3 strict full80 buckets in visible
PowerShell windows, sequentially, with the approved budgets:

- `8-9`: `3,600s`
- `10-11`: `7,200s`
- `12-14`: `7,200s`
- `15-17`: `7,200s`
- `18+`: `5,400s`

Stop if any bucket exits nonzero. No all-`734` expansion, score-bearing use,
or production scoring/ranking change is approved.

S3 strict full80 completed cleanly:

- all five buckets reached `bucket_n3c_query_complete`
- strict scope: `815` chunks, `702` logical groups, `365,516,232` phrase rows
- strict verified hits: `1,546,511`
- strict global candidate clusters: `308`
- strict exact-containing global candidate clusters: `249`
- strict summed bucket runtime: `8,902.7s`
- max peak memory: `914.4 MB`
- all strict bucket runtime and memory budgets passed

Matched strict-versus-normal comparison:

- output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_vs_normal_full80_comparison_v1/`
- strict phrase-row retention versus normal: `59.6%`
- strict verified-hit retention versus normal: `92.7%`
- strict runtime retention versus normal: `60.8%`
- normal -> strict global clusters: `275` -> `308`
- normal -> strict exact-containing clusters: `225` -> `249`
- phrase-level strict subset identity is not proven; do not report shared,
  normal-only, or strict-only phrase classes.

Main review pack:

`planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_strict_vs_normal_full80_review_pack_2026-06-06.zip`

- entries: `114`
- ZIP size: `511,716` bytes
- fresh extracted portable tests: `11 passed`
- still not approved: all-`734` expansion, score-bearing use, production
  scoring/ranking changes, raw-hit authority, or simple-cluster authority

Strict 320 all-data review pack:

- tail run completed the missing `remaining_batch_03` buckets `15-17` and
  `18+`; all `20` strict bucket outputs are now complete
- combined strict output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_320_corrected_consolidated_evidence_v1/`
- candidates: `320`
- bucket outputs: `20`
- strict phrase rows queried: `1,462,064,928`
- strict verified hits: `6,415,767`
- strict global candidate clusters: `1,115`
- strict exact-containing global clusters: `893`
- unique semantic pairs in the 320-candidate sample: `590`
- rescue-capable unique semantic pairs: `0`
- all-data review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_strict_320_all_data_review_pack_2026-06-06.zip`
- pack facts:
  - entries: `199`
  - ZIP size: `1,135,215` bytes
  - fresh extracted portable tests: `13 passed`
  - full hit CSVs remain external and are represented by path, row count,
    byte count, SHA-256, and sampled rows

Strict O3 anchored-region quickcheck:

- integrated script:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1.py`
- output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1/`
- input: existing strict-320 `20` hit CSV files, `6,415,767` rows
- runtime: `156.9s`
- output rows:
  - candidate summaries: `1,882`
  - selected anchor regions: `34,337`
  - pairwise rows: `2,284`
  - margin threshold rows: `64`
- focused tests:
  `C:\Python\Python311\python.exe -m pytest tests/tools/test_phaseB_n3c_strict_320_anchor_lens_quickcheck_v1.py -q`
  -> `4 passed`
- first decision readout:
  - `hd0_len10` at margin `20`: `251` covered pairs, `227` agree,
    `24` break, break rate `0.095618`
  - `hd0_len12`: `22` covered pairs, `0` breaks at all-pair threshold,
    but coverage is small
  - `hd_le2_len12` is worse than raw-hit baseline at broad coverage:
    `213` breaks from `590` covered pairs, break rate `0.361017`

Interpretation: HD0 anchored O3 is promising at length/margin gates, especially
`hd0_len10`; broad HD<=2 support should not be promoted as a raw score channel.
This remains report-only and does not approve production scoring or ranking.

Strict O3 anchor joint-rule sweep:

- integrated script:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_320_anchor_joint_rule_sweep_v1.py`
- output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_320_anchor_joint_rule_sweep_v1/`
- input: existing anchor quickcheck pairwise output, `2,284` rows over `590`
  unique semantic pairs
- output rows:
  - joint rule summaries: `14`
  - conflict rows: `48`
- focused tests:
  `C:\Python\Python311\python.exe -m pytest tests/tools/test_phaseB_n3c_strict_320_anchor_lens_quickcheck_v1.py tests/tools/test_phaseB_n3c_strict_320_anchor_joint_rule_sweep_v1.py -q`
  -> `8 passed`
- first decision readout:
  - `hd0_len10_m20`: `251` covered, `227` agree, `24` break,
    break rate `0.095618`
  - `hd0_len10_m30`: `162` covered, `161` agree, `1` break,
    break rate `0.006173`
  - `hd0_len10_m50`: `87` covered, `87` agree, `0` break,
    break rate `0.000000`
  - `hd0_len10_m20__hd_le1_len12_agree_required`: `147` covered,
    `146` agree, `1` break, break rate `0.006803`

Interpretation: the main signal is primary `hd0_len10` margin strength, not a
secondary-conflict filter. `hd_le1_len12` agreement can form a narrower
confirmation lens, while broad HD support still remains report-only and
telemetry-only.

