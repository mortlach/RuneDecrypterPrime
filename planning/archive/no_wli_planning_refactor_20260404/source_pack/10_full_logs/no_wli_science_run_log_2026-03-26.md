# No-WLI Science Run Log

Purpose:

- record hypotheses, run setups, outcomes, and next actions in one verifiable place
- keep each claim tied to concrete evidence in repo-relative run artifacts
- separate "pipeline plumbing worked" from "solve quality improved"

Verification rule:

- every result claim below names at least one concrete artifact path and the field or log line that supports it
- if a claim is only an inference, it is labelled as an inference

## 2026-03-26 backfilled evidence

### Entry A: live handoff emission canary on seed211

Question:

- did the live commit / handoff path finish cleanly and emit a real live Stage-2 to Stage-3 handoff bundle?

Run:

- live canary run directory:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260326T012915418495Z__bench_solve_pipeline_no_wli__55b7159`

Outcome:

- yes, the live handoff path completed and emitted a handoff bundle
- no, solve quality did not improve

Cross-checked evidence:

- handoff emitted from live pipeline:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260326T012915418495Z__bench_solve_pipeline_no_wli__55b7159/resume_handoffs/fixture_fixture_001_p9_c3_l1000__text0__seed211/manifest.json`
  - field: `stage2_to_stage3.source = "live_stage3_pipeline"`
- live result stayed weak:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260326T012915418495Z__bench_solve_pipeline_no_wli__55b7159/instances.json`
  - fields:
    - `best_match_ratio = 0.574`
    - `stage2_match_ratio = 0.209`
    - `stage3_match_ratio = 0.574`
    - `best_stage = "stage3_full_refine"`
- run finished normally:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/ops_logs/run_fixture_matrix_seed211_v34_bridge_contract_20260325T182911.stdout.log`
  - tail contains:
    - `completed in 5h56m`
    - `[no_wli_fixture_matrix] completed session_completed_jobs=1 total_completed_jobs=1`

Conclusion:

- the live handoff-emission bug class is fixed on the real path
- this was a reliability win, not a solve-quality win

### Entry B: seed411 fixed-handoff ranking probe

Question:

- can small lexical-gate / tie-window changes promote the truth-better challenger family on the saved weak seed411 handoff?

Run:

- resume probe report:
  - `tools/benchmarks/periodic_sub_trans/no_wli/output/tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume/20260325T145319Z_seed411_phasec_ranking_probe/report.md`
- machine summary:
  - `tools/benchmarks/periodic_sub_trans/no_wli/output/tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume/20260325T145319Z_seed411_phasec_ranking_probe/summary.json`

Outcome:

- no
- all three variants ended at the same resumed best match

Cross-checked evidence:

- report table in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/output/tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume/20260325T145319Z_seed411_phasec_ranking_probe/report.md`
  - rows show:
    - `baseline_phasec_ranking -> Resume Match 0.032`
    - `lexical_gate_035_tie_025 -> Resume Match 0.032`
    - `lexical_gate_030_tie_050 -> Resume Match 0.032`
    - `Best Truth Start 0.099`
    - `Truth Gap 0.067`
    - `Stop Reason stalled_no_improve`
- summary details in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/output/tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume/20260325T145319Z_seed411_phasec_ranking_probe/summary.json`
  - per-variant fields show:
    - `resume_best_match_ratio = 0.032`
    - `checkpoint_summary.best_truth_match = 0.099`
    - `between_family_truth_gap = 0.067`

Conclusion:

- small lexical-gate widening was not enough on fixed seed411 downstream state
- next seed411 candidate should be meaningfully broader than a small gate tweak

### Entry C: 10-job weak-seed overnight live matrix, jobs 1-3 only

Question:

- can weak-seed live performance be lifted by preservation changes or by Stage-3.5, and can this be learned from a broad overnight matrix?

Run control files:

- run state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v35_p9c3_weakseed_overnight_10h.json`
- run events:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v35_p9c3_weakseed_overnight_10h.jsonl`

Outcome:

- only the first three jobs completed before the between-jobs wallclock stop
- all three completed jobs were `seed211`
- none improved beyond `0.574`
- Stage-3.5 executed for the proof lane but did not win

Cross-checked evidence:

- run stopped early after job 3:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v35_p9c3_weakseed_overnight_10h.json`
  - fields:
    - `completed_jobs = 3`
    - `remaining_jobs = 7`
    - `stopped_early = 1`
- event log confirms completed jobs and runtimes:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v35_p9c3_weakseed_overnight_10h.jsonl`
  - rows show:
    - job 1 `stage3_preserve_tieband_probe_p9` elapsed `13193.243979...`
    - job 2 `stage3_recovery_p9_8h` elapsed `11181.895447...`
    - job 3 `stage35_proof_p9_8h` elapsed `51995.484903...`
- job 1 result:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260326T054251138284Z__bench_solve_pipeline_no_wli__55b7159/instances.json`
  - fields:
    - `best_match_ratio = 0.574`
    - `stage35_requested_cfg = 0`
- job 2 result:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260326T092244385214Z__bench_solve_pipeline_no_wli__55b7159/instances.json`
  - fields:
    - `best_match_ratio = 0.574`
    - `stage35_requested_cfg = 0`
- job 3 result:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260326T122906196863Z__bench_solve_pipeline_no_wli__55b7159/instances.json`
  - fields:
    - `best_match_ratio = 0.574`
    - `stage35_requested_cfg = 1`
    - `stage35_selected = false`
    - `stage35_archive_count = 16`
    - `stage35_rounds_completed = 3`
- job 3 Stage-3.5 rejection reason:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260326T122906196863Z__bench_solve_pipeline_no_wli__55b7159/best/best_instance.json`
  - field:
    - `stage35_accept_reason = "search_score_drop_guard_failed"`
- all three completed runs emitted live handoff bundles:
  - each run dir contains:
    - `resume_handoffs/fixture_fixture_001_p9_c3_l1000__text0__seed211/manifest.json`
  - field:
    - `stage2_to_stage3.source = "live_stage3_pipeline"`

Conclusion:

- broad live matrices were too slow for fast iteration
- on seed211:
  - preservation baseline did not improve
  - wider recovery did not improve
  - Stage-3.5 was real and auditable, but too expensive and still lost to Stage-3

Inference:

- Stage-3.5 should not be in the default short comparison lane unless a run is explicitly about Stage-3.5 acceptance behavior

## v36 short seed411 comparison

Question:

- on live `seed411`, does the broader downstream package
  `lexical_phasec_rescue_wide_finish` materially beat the preserved control
  `stage3_preserve_tieband_probe_p9`?

Setup:

- seed:
  - `411`
- presets:
  - `stage3_preserve_tieband_probe_p9`
  - `lexical_phasec_rescue_wide_finish`
- control files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v36_p9c3_seed411_phasec_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v36_p9c3_seed411_phasec_compare_2job.jsonl`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v36_p9c3_seed411_phasec_compare_2job.json`

Outcome:

- the broader candidate beat the control, but only weakly:
  - control:
    - `best_match_ratio = 0.041`
    - `best_stage = "stage2_search"`
  - broader candidate:
    - `best_match_ratio = 0.046`
    - `best_stage = "stage3_full_refine"`
- both runs finished cleanly and emitted live handoff bundles
- the explicit Phase-C rescue lane in the broader candidate was enabled but did
  not actually run

Cross-checked evidence:

- matrix completed cleanly:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v36_p9c3_seed411_phasec_compare_2job.json`
  - fields:
    - `completed_jobs = 2`
    - `remaining_jobs = 0`
    - `stopped_early = 0`
- job order and runtimes:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v36_p9c3_seed411_phasec_compare_2job.jsonl`
  - job 1 preserve completed in `16628.888...` seconds
  - job 2 broader candidate completed in `25767.437...` seconds
- control run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T044057282813Z__bench_solve_pipeline_no_wli__55b7159/instances.json`
  - fields:
    - `best_stage = "stage2_search"`
    - `best_match_ratio = 0.041`
    - `stage2_match_ratio = 0.041`
    - `stage3_match_ratio = 0.039`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T044057282813Z__bench_solve_pipeline_no_wli__55b7159/resume_handoffs/fixture_fixture_001_p9_c3_l1000__text0__seed411/manifest.json`
  - field:
    - `stage2_to_stage3.source = "live_stage3_pipeline"`
- broader candidate run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T091806220616Z__bench_solve_pipeline_no_wli__55b7159/instances.json`
  - fields:
    - `best_stage = "stage3_full_refine"`
    - `best_match_ratio = 0.046`
    - `stage2_match_ratio = 0.041`
    - `stage3_match_ratio = 0.046`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T091806220616Z__bench_solve_pipeline_no_wli__55b7159/resume_handoffs/fixture_fixture_001_p9_c3_l1000__text0__seed411/manifest.json`
  - field:
    - `stage2_to_stage3.source = "live_stage3_pipeline"`
- broader internal width really changed:
  - control best artifact:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T044057282813Z__bench_solve_pipeline_no_wli__55b7159/best/best_instance.json`
    - fields:
      - `phaseB_top_n_used = 8`
      - `phaseB_selected_unique_end_hash = 8`
      - `phaseC_start_keys_used = 6`
      - `phaseC_candidate_pool_unique_end_hash = 8`
  - broader candidate best artifact:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T091806220616Z__bench_solve_pipeline_no_wli__55b7159/best/best_instance.json`
    - fields:
      - `phaseB_top_n_used = 32`
      - `phaseB_selected_unique_end_hash = 32`
      - `phaseC_start_keys_used = 8`
      - `phaseC_candidate_pool_unique_end_hash = 32`
- rescue did not actually activate in the broader candidate:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T091806220616Z__bench_solve_pipeline_no_wli__55b7159/stages.json`
  - fields:
    - `phaseC_rescue_enabled = 1`
    - `phaseC_rescue_ran = 0`
    - `phaseC_rescue_eligible_starts = 0`
    - `phaseC_final_winner_source = "phaseB_topk"`
- control Phase-C slightly worsened the Phase-B winner:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T044057282813Z__bench_solve_pipeline_no_wli__55b7159/stages.json`
  - fields:
    - `phaseB_top_n_used = 8`
    - `phaseB_selected_unique_end_hash = 8`
    - `phaseC_rescue_enabled = 0`
    - `phaseC_final_winner_source = "stage3_best_phaseB"`
    - Phase-B `match_ratio = 0.04`
    - Phase-C `match_ratio = 0.039`

Conclusion:

- the broader downstream package produced a real but very small gain on live
  `seed411`: `0.041 -> 0.046`
- that is enough to say the wider Phase-B / Phase-C package was not a complete
  dead end
- it is not enough to say downstream rescue is "working" in any meaningful
  solve sense
- the observed improvement came from broader Phase-B / Phase-C family breadth,
  not from the explicit rescue lane, because rescue never became eligible

Inference:

- this result fits the current structural suspicion better than the earlier
  "one more rescue tweak" story:
  - more family width helped a little
  - explicit rescue logic did not actually engage
- the next best questions should now be more about family survival and objective
  alignment than about yet another small rescue tweak

## External review pack assembled

Purpose:

- package the current state, recent evidence, active hypotheses, and review
  questions into one review-first folder for outside help

Pack location:

- `planning/working/no_wli_external_review_pack_2026-03-26/`

Key reviewer-facing files:

- `planning/working/no_wli_external_review_pack_2026-03-26/README.md`
- `planning/working/no_wli_external_review_pack_2026-03-26/01_current_state.md`
- `planning/working/no_wli_external_review_pack_2026-03-26/02_recent_experiments_and_observations.md`
- `planning/working/no_wli_external_review_pack_2026-03-26/03_pipeline_reliability_and_methodology.md`
- `planning/working/no_wli_external_review_pack_2026-03-26/04_hypotheses_and_next_decisions.md`
- `planning/working/no_wli_external_review_pack_2026-03-26/05_questions_for_external_review.md`
- `planning/working/no_wli_external_review_pack_2026-03-26/06_evidence_index.md`

## 2026-03-27 reviewer-driven code cross-check on Stage-3 family selection

Question:

- do the reviewer concerns about Stage-3 entry dilution, objective mismatch, and
  early family collapse hold up against the actual code and saved artifacts?

Confirmed from code:

- Stage-3 entry dilution mechanism is real:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_seeding.py`
  - lines `50-95`
  - `init3_n` is fixed first, `promoted_keys` is built, `per_seed = ceil(init3_n / len(promoted_keys))`,
    then each promoted seed is mutated `per_seed` times and truncated back to `init3_n`
- Phase-A basin-judge pool is search-first before judged pct scoring:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - lines `330-355`
  - `judge_ranked` is ordered by:
    - `end_score_search`
    - `end_match`
    - `end_score_raw`
    - restart index
- Phase-B family selection is pct-first:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - lines `754-817`
  - `_phaseb_rank_key(...)` starts with `end_score_pct`
  - `end_score_raw` is later in the key
  - dedupe is by `(start_hash, end_hash)`
  - tie-band widening is still around `end_score_pct`
- The active avg/full-text profile really does set raw-score-led Stage-3 solve
  defaults and wider profile budgets:
  - `tools/benchmarks/config/no_wli_pipeline_profiles.py`
  - lines `242-306`
  - fields:
    - `stage3_initial_keys = 64`
    - `stage12_archive_keep = 192`
    - `stage12_promote_top = 96`
    - `solver_stage3["use_raw_score"] = True`
- The current live compare is not a single-variable test:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  - `stage3_preserve_tieband_probe_p9` at lines `153-197`
  - `lexical_phasec_rescue_wide_finish` at lines `524-568`
  - the candidate changes multiple knobs at once:
    - `force_stage3_initial_keys`
    - `force_stage3_span_basin_judge_tie_max_seeds`
    - Phase-A steps
    - Phase-B `top_n`
    - Phase-B steps / gate floors
    - Phase-C start keys / proposals
- The single saved Phase-B top-k row case is explainable by current solver
  telemetry semantics, not automatically by a save bug:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_topk.py`
  - lines `10-60`
  - `src/rune_decrypter_prime/solvers/kaeding_periodic_structured.py`
  - lines `317-338`, `601-605`
  - Kaeding `top_candidates` is only extended on new global raw-score bests via
    `_record_top(...)`, then `top_keys/top_raw/top_pct` are emitted from that
    list
  - a run can therefore have a broad Phase-B selected set but only one saved
    `phaseB_topk` row

Saved-artifact cross-checks:

- one-row Phase-B top-k case:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260322T192204224097Z__bench_solve_pipeline_no_wli__55b7159/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed211.json`
  - fields:
    - `phaseB_top_n_used = 8`
    - `phaseB_selected_unique_end_hash = 8`
    - `phaseB_topk_saved_count = 1`
- same weak run appears in the catalog audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/partial_state_signal_audit_summary.json`
  - one row records `stage3_topk_rows = 1`

Important caveats:

- the profile-level raw-score / widened-budget point is confirmed at the profile
  definition layer, but active live presets can override some of those budget
  fields
- the current v36 comparison is therefore evidence about a multi-knob live
  package, not a pure readout of the base avg/full-text profile defaults
- none of the code checks above proves causality by itself; they confirm that
  the reviewer's proposed mechanisms are plausible and materially present in the
  implementation

Working conclusion:

- the reviewer concern is materially supported by code:
  - Stage-3 inner search can be raw-score-led
  - Phase-B family selection remains pct-led
  - wider preservation can reduce local mutation depth per promoted family if
    `init3_n` does not scale with family count
- this is now one of the strongest code-backed explanations for why weak-seed
  families may be underfed at entry and then collapsed too early downstream

Still not fully verified:

- exact survival of distinct Phase-B families into Phase-C starts and Stage-3.5
  seed construction
- whether the decisive weak-seed failures are mostly:
  - entry dilution
  - objective mismatch
  - early family collapse
  - or a combination

Raw working-doc snapshots included in the same pack:

- `planning/working/no_wli_external_review_pack_2026-03-26/appendix_science_run_log_2026-03-26.md`
- `planning/working/no_wli_external_review_pack_2026-03-26/appendix_pipeline_hardening_review_2026-03-25.md`
- `planning/working/no_wli_external_review_pack_2026-03-26/appendix_solve_integrity_plan_2026-03-21.md`
- `planning/working/no_wli_external_review_pack_2026-03-26/appendix_deep_research_report.md`
- `planning/working/no_wli_external_review_pack_2026-03-26/deep_research_pack_snapshot/`

Current live status included in the pack:

- active short run control files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v36_p9c3_seed411_phasec_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v36_p9c3_seed411_phasec_compare_2job.jsonl`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v36_p9c3_seed411_phasec_compare_2job.json`

## 2026-03-27 Study 1 implementation: explicit constant-local-depth Stage-3 entry

Question:

- can Study 1 be implemented as an explicit, auditable Stage-3 entry policy
  while preserving legacy behavior by default and preparing a clean two-job
  live compare on `seed211`?

Implemented code surface:

- Stage-3 entry policy and telemetry:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_seeding.py`
- Stage-3 stop-line and diagnostics propagation:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- explicit default config:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runtime_defaults.py`
  - `tools/benchmarks/config/no_wli_pipeline_profiles.py`
- preset/cap forwarding:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
- next live compare lane:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

What changed:

- legacy Stage-3 entry remains the default policy:
  - `entry_allocation_policy = "legacy_fixed_budget"`
- new explicit Study 1 policy added:
  - `entry_allocation_policy = "constant_local_depth"`
- the new policy uses:
  - explicit `entry_mutations_per_promoted`
  - round-robin family allocation after seeding each promoted family once
  - explicit cap reporting through:
    - `stage3_entry_base_budget`
    - `stage3_entry_target_before_cap`
    - `stage3_entry_cap`
    - `stage3_entry_cap_applied`
    - `stage3_entry_mutation_calls_per_promoted`
- fixture-matrix presets can now override:
  - `STAGE3_ENTRY_ALLOCATION_POLICY` via
    `force_stage3_entry_allocation_policy`
  - `STAGE3_ENTRY_MUTATIONS_PER_PROMOTED` via
    `force_stage3_entry_mutations_per_promoted`
  - real Kaeding solver fields via `force_solver_stage3_overrides`
  - `STAGE3_INIT_KEYS_CAP` via `force_stage3_init_keys_cap`

Prepared live compare:

- active matrix config now targets the first Study 1 live comparison:
  - seed:
    - `211`
  - presets:
    - `stage3_preserve_tieband_probe_p9`
    - `stage3_entry_const_local_depth_p9`
  - control files:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v37_p9c3_seed211_stage3_entry_compare_2job.jsonl`
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`

Candidate semantics:

- preset:
  - `stage3_entry_const_local_depth_p9`
- key overrides in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- intended behavior:
  - keep the same narrow preserved lane as control
  - keep `force_stage3_initial_keys = 64`
  - raise `force_stage3_init_keys_cap = 288`
  - set:
    - `entry_allocation_policy = "constant_local_depth"`
    - `entry_mutations_per_promoted = 1`
- interpretation:
  - on large promoted pools, aim to give each promoted family one explicit local
    mutation before truncation/cap, rather than letting the old fixed-budget
    math collapse the family set down toward the legacy target

Short validation:

- focused regression slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_seeding.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py tests/tools/test_no_wli_resume_handoff_artifacts.py -q`
  - outcome:
    - `78 passed`
- config materialization check:
  - inline module load against `run_fixture_matrix`
  - result:
    - `job_count = 2`
    - `run_seeds = [211, 211]`
    - `preset_ids = ["stage3_preserve_tieband_probe_p9", "stage3_entry_const_local_depth_p9"]`
    - `run_state_path = output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`

Meaningful new test coverage:

- `tests/tools/test_no_wli_stage3_seeding.py`
  - legacy fixed-budget behavior stays stable
  - constant-local-depth scales target budget
  - cap application is explicit and auditable
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - active config materializes the intended Study 1 two-job lane
  - new preset forwards `force_stage3_init_keys_cap`
  - new preset forwards the explicit Stage-3 entry controls
  - direct `apply_job(...)` wiring updates:
    - `STAGE3_INIT_KEYS_CAP`
    - `STAGE3_ENTRY_ALLOCATION_POLICY`
    - `STAGE3_ENTRY_MUTATIONS_PER_PROMOTED`
    - without contaminating `SOLVER_STAGE3`
- `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py`
  - stop-line diagnostics now assert:
    - `entry_policy=`
    - `entry_target_before_cap=`
    - `entry_mutation_calls_per_promoted=`

Conclusion:

- Study 1 is now implemented as an explicit, testable policy rather than an
  implicit tuning change
- baseline semantics remain available under the legacy mode
- the next long run should now be the prepared `seed211` control vs
  `stage3_entry_const_local_depth_p9` compare
- no live outcome is claimed yet; only implementation and short validation are
  complete

### 2026-03-27 Study 1 live run started and readout checklist prepared

Run-start evidence:

- state file:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`
  - current start snapshot:
    - `completed_jobs = 0`
    - `remaining_jobs = 2`
    - `started_utc = 2026-03-28T00:50:34.858013+00:00`
- event log:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v37_p9c3_seed211_stage3_entry_compare_2job.jsonl`
  - first event confirms:
    - job 1 preset = `stage3_preserve_tieband_probe_p9`
    - total jobs = `2`

Prepared post-run readout:

- `planning/working/no_wli_study1_readout_checklist_2026-03-27.md`

Purpose of the checklist:

- verify that the candidate really exercised:
  - `entry_allocation_policy = "constant_local_depth"`
  - `entry_mutations_per_promoted = 1`
  - `stage3_init_keys_cap = 288`
- verify whether the candidate actually widened:
  - `stage3_entry_target_before_cap`
  - `init3_n`
  - `stage2_to_stage3.stage3_init3_count`
- separate "policy executed" from "policy helped"

### 2026-03-27 Study 1 first launch exposed runtime-config boundary leak

Failure evidence:

- state file after first launch:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`
  - shows:
    - `completed_jobs = 0`
    - `remaining_jobs = 2`
    - `stopped_early = 1`
    - `last_error.error_type = "ValueError"`
    - `last_error.error = "Unknown kaeding parameter(s): entry_allocation_policy, entry_mutations_per_promoted ..."`
- event log:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v37_p9c3_seed211_stage3_entry_compare_2job.jsonl`
  - shows:
    - `job_started` for control preset
    - then `job_error` with the same unknown-parameter message

Interpretation:

- the new Study 1 keys were correctly introduced as Stage-3 entry controls
- but they were still leaking into the downstream Kaeding runtime solver config
- this is a boundary bug, not a negative scientific result
- no completed run from this first launch should be interpreted

Fix applied:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_seeding.py`
  - added explicit stripping of Stage-3 entry-only keys before emitting
    `solver_stage3_cfg` downstream
- Stage-3 entry metadata still remains separately observable via:
  - `stage3_entry_allocation_policy`
  - `stage3_entry_target_before_cap`
  - `stage3_entry_mutations_per_promoted_cfg`
  - `stage3_entry_mutation_calls_per_promoted`

Regression coverage added:

- `tests/tools/test_no_wli_stage3_seeding.py`
  - now asserts:
    - `entry_allocation_policy` is absent from emitted `solver_stage3_cfg`
    - `entry_mutations_per_promoted` is absent from emitted `solver_stage3_cfg`
    - the emitted `solver_stage3_cfg` is accepted by the real
      `SolverSpec.kaeding(...)` validator

Short validation after the fix:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_seeding.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py -q`
  - outcome:
    - `68 passed`

Rerun note:

- rerunning the same matrix command is the expected next step
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_runtime.py`
  rebuilds the run-state header each session and only skips jobs listed in
  `completed_job_keys`
- since `completed_job_keys = []`, the Study 1 lane can be rerun without a code
  change to the state file path

### 2026-03-27 Study 1 second failed rerun clarified the real root cause and the canary now passes

Cross-checked failed rerun evidence:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`
  - `completed_jobs = 0`
  - `remaining_jobs = 0`
  - `stopped_early = 0`
  - `completed_utc = 2026-03-28T00:57:26.311066+00:00`
  - `last_error.error_type = "ValueError"`
  - `last_error.error = "Unknown kaeding parameter(s): entry_allocation_policy, entry_mutations_per_promoted ..."`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v37_p9c3_seed211_stage3_entry_compare_2job.jsonl`
  - job 1 control preset `stage3_preserve_tieband_probe_p9` failed with the
    same unknown-parameter error
  - job 2 candidate preset `stage3_entry_const_local_depth_p9` failed with the
    same unknown-parameter error

Corrected root cause:

- the first fix was too narrow
- the Study 1 entry controls were incorrectly living inside the canonical
  `SOLVER_STAGE3` runtime config surface
- because of that, both the unchanged control path and the candidate path could
  still leak non-Kaeding keys into `SolverSpec.kaeding(...)`

Architectural fix completed:

- `tools/benchmarks/periodic_sub_trans/no_wli/runtime_defaults.py`
  - removed Study 1 entry controls from `DEFAULT_SOLVER_STAGE3`
  - added:
    - `DEFAULT_STAGE3_ENTRY_ALLOCATION_POLICY`
    - `DEFAULT_STAGE3_ENTRY_MUTATIONS_PER_PROMOTED`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
  - added explicit runtime state:
    - `STAGE3_ENTRY_ALLOCATION_POLICY`
    - `STAGE3_ENTRY_MUTATIONS_PER_PROMOTED`
- `tools/benchmarks/periodic_sub_trans/no_wli/profile_defaults.py`
  - now splits Stage-3 entry controls out of profile `solver_stage3`
  - keeps `SOLVER_STAGE3` clean
- `tools/benchmarks/config/no_wli_pipeline_profiles.py`
  - removed Study 1 entry controls from the profile `solver_stage3` dict
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - extracts legacy Study 1 keys out of `force_solver_stage3_overrides`
  - forwards explicit entry-control overrides separately
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
  - applies the entry controls to explicit runtime state
  - keeps `SOLVER_STAGE3` restricted to real Kaeding fields
- `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
  - now writes a separate `stage3.entry` block
- `tools/benchmarks/periodic_sub_trans/no_wli/run_lock_payload.py`
  - now writes a separate `stage3_search.entry` block
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py`
  - passes Study 1 entry controls explicitly into Stage-3 prep
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - resume/live Stage-3 prep now read the same explicit `entry` block

Meaningful canary added:

- `tests/tools/test_no_wli_stage3_entry_canary.py`
  - resolves the live Study 1 preset
  - applies it to a live-like no-WLI state
  - proves:
    - `SOLVER_STAGE3` stays clean
    - run config writes `stage3.entry`
    - non-scoring lock writes `stage3_search.entry`
    - Stage-3 prep bridge emits a clean `solver_stage3_cfg`
    - the emitted solver config is accepted by the real
      `SolverSpec.kaeding(...)` validator

Focused validation after the architectural fix:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_entry_canary.py tests/tools/test_no_wli_stage3_seeding.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py -q`
  - outcome:
    - `83 passed`

Updated interpretation:

- the failed Study 1 reruns remain invalid scientifically
- but the boundary bug is now fixed at the correct architectural level rather
  than patched only in one downstream payload
- the new canary is the short proof required before the next long rerun

Planning follow-up:

- next-stage implementation plan written in:
  - `planning/working/no_wli_next_phase_implementation_plan_2026-03-27.md`
- current planned order remains:
  1. close Study 1 readout
  2. implement isolated Study 3 Phase-C start balancing
  3. defer Study 2 Phase-B family preservation until after Study 3 readout

### 2026-03-28 Study 1 `seed211` live compare finished: policy executed, no solve gain

Completed runs:

- control preserve run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T013131043374Z__bench_solve_pipeline_no_wli__55b7159`
  - matrix event elapsed:
    - `12980.378674268723s`
- candidate constant-local-depth run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T050751414997Z__bench_solve_pipeline_no_wli__55b7159`
  - matrix event elapsed:
    - `13750.395778656006s`

Execution proof:

- control Stage-3 prep:
  - `resume_handoffs/fixture_fixture_001_p9_c3_l1000__text0__seed211/stage3_prep.json`
  - `stage3_entry_allocation_policy = "legacy_fixed_budget"`
  - `stage3_entry_base_budget = 64`
  - `stage3_entry_target_before_cap = 64`
  - `init3_n = 64`
- candidate Stage-3 prep:
  - `resume_handoffs/fixture_fixture_001_p9_c3_l1000__text0__seed211/stage3_prep.json`
  - `stage3_entry_allocation_policy = "constant_local_depth"`
  - `stage3_entry_base_budget = 64`
  - `stage3_entry_target_before_cap = 288`
  - `stage3_entry_cap = 288`
  - `init3_n = 288`

Live handoff counts:

- control manifest:
  - `stage2_promoted_from_topk_count = 144`
  - `stage3_init3_count = 64`
- candidate manifest:
  - `stage2_promoted_from_topk_count = 144`
  - `stage3_init3_count = 144`

So Study 1 did execute the intended widening:
- same promoted pool size
- materially larger Stage-3 target
- materially larger realized Stage-3 init set

Solve outcome:

- control:
  - `best_stage = "stage3_full_refine"`
  - `best_match_ratio = 0.574`
  - `stage3_match_ratio = 0.574`
- candidate:
  - `best_stage = "stage3_full_refine"`
  - `best_match_ratio = 0.574`
  - `stage3_match_ratio = 0.574`

Downstream comparison:

- both runs show:
  - `phaseB_selected_unique_end_hash = 8`
  - `phaseC_candidate_pool_unique_end_hash = 8`
  - `phaseC_start_keys_used = 6`
  - `phaseC_candidate_pool_source_counts = { stage3_best_phaseB: 1, phaseB_topk: 1, phaseA_selected: 8 }`
  - `phaseC_start_source_counts = { stage3_best_phaseB: 1, phaseA_selected: 5 }`

Interpretation:

- this is a valid negative result, not an execution failure
- constant local-depth Stage-3 entry widened upstream entry substantially on
  `211`
- but that widening alone did not improve solve quality or downstream family
  diversity metrics
- current best reading remains:
  - `211` looks more like a `good_family_absent` case than a simple
    entry-budget starvation case
- Study 1 should therefore be treated as:
  - successful implementation
  - successful execution proof
  - negative scientific result on this seed

### 2026-03-28 Study 3 implementation complete: isolated Phase-C start balancing

Implementation boundary:

- objective:
  - test whether downstream exploited variety improves if Phase-C start slots
    are balanced across surviving sources on `seed411`
- changed:
  - Phase-C `start_records` selection policy only
- explicitly unchanged:
  - Phase-C candidate-pool composition
  - Phase-B ranking and tie-band logic
  - rescue eligibility and rescue policy
  - Phase-B family-preservation policy

Code paths changed:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - new `stage3_phasec_start_policy` surface
  - new balanced source-order implementation:
    - `balanced_sources_v1`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_calls.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runtime_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/profile_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_lock_payload.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`

Meaningful Study 3 canary and deterministic proof:

- `tests/tools/test_no_wli_phasec_start_policy_canary.py`
  - proves preset resolution, job application, run-config emission,
    non-scoring lock emission, and Stage-3 runtime-call bridge propagation of
    `STAGE3_PHASEC_START_POLICY`
- `tests/tools/test_no_wli_stage3_phasec.py`
  - deterministic synthetic test proves:
    - same Phase-C pool
    - same start budget
    - different start ordering under `balanced_sources_v1`

Focused short validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_artifact_resume.py -q`
  - outcome:
    - `42 passed`
- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_entry_canary.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_artifact_resume.py -q`
  - outcome:
    - `43 passed`

Config materialization cross-check:

- active matrix config now resolves exactly:
  - `job_count = 2`
  - `run_seeds = [411, 411]`
  - presets:
    - `stage3_preserve_tieband_probe_p9`
    - `stage3_phasec_start_balanced_p9`

User long-run handoff prepared:

- active compare target:
  - `seed411`
- control preset:
  - `stage3_preserve_tieband_probe_p9`
- candidate preset:
  - `stage3_phasec_start_balanced_p9`
- active matrix control files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v38_p9c3_seed411_phasec_start_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v38_p9c3_seed411_phasec_start_compare_2job.jsonl`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v38_p9c3_seed411_phasec_start_compare_2job.json`

Current interpretation:

- Study 1 closed as a valid negative on `seed211`
- Study 3 is now isolated cleanly enough to test the downstream
  exploited-variety bottleneck on `seed411`
- if Study 3 is also negative, the next best move becomes more clearly:
  - upstream basin-generation work for `211`-like cases
  - then Phase-B family-preservation policy for `411`-like cases

### 2026-03-28 Study 3 `seed411` live compare finished: policy executed, no distinct new starts

Completed runs:

- control preserve run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T174120032623Z__bench_solve_pipeline_no_wli__55b7159`
  - matrix event elapsed:
    - `12561.021997451782s`
- candidate balanced-start run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T211041031812Z__bench_solve_pipeline_no_wli__55b7159`
  - matrix event elapsed:
    - `10083.177921056747s`

Isolation check:

- `git diff --no-index -- output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T174120032623Z__bench_solve_pipeline_no_wli__55b7159/run_config.json output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T211041031812Z__bench_solve_pipeline_no_wli__55b7159/run_config.json`
  - meaningful semantic difference:
    - `stage3.two_phase.phase_c.start_policy`
      - control:
        - `source_order`
      - candidate:
        - `balanced_sources_v1`
  - other differences were expected lock hashes / normalized float formatting only

Execution proof:

- control run config:
  - `stage3.two_phase.phase_c.start_policy = "source_order"`
- candidate run config:
  - `stage3.two_phase.phase_c.start_policy = "balanced_sources_v1"`
- both runs emitted live handoffs:
  - `resume_handoffs/fixture_fixture_001_p9_c3_l1000__text0__seed411/manifest.json`
  - `stage2_to_stage3.source = "live_stage3_pipeline"`

Top-level solve outcome:

- control:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`
- candidate:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`

Phase-C pool vs starts:

- control Stage-3 summary:
  - `phaseC_candidate_pool_count = 10`
  - `phaseC_candidate_pool_unique_end_hash = 8`
  - `phaseC_candidate_pool_source_counts = { "stage3_best_phaseB": 1, "phaseB_topk": 1, "phaseA_selected": 8 }`
  - `phaseC_start_keys_used = 6`
  - `phaseC_start_unique_end_hash = 6`
  - `phaseC_start_source_counts = { "stage3_best_phaseB": 1, "phaseA_selected": 5 }`
- candidate Stage-3 summary:
  - `phaseC_candidate_pool_count = 10`
  - `phaseC_candidate_pool_unique_end_hash = 8`
  - `phaseC_candidate_pool_source_counts = { "stage3_best_phaseB": 1, "phaseB_topk": 1, "phaseA_selected": 8 }`
  - `phaseC_start_keys_used = 6`
  - `phaseC_start_unique_end_hash = 6`
  - `phaseC_start_source_counts = { "stage3_best_phaseB": 1, "phaseA_selected": 5 }`

Start-level checkpoint comparison:

- control:
  - `phasec_start_checkpoints.jsonl`
- candidate:
  - `phasec_start_checkpoints.jsonl`
- observed:
  - same six `candidate_hash` values in the same order
  - no `phaseB_topk` start in either run
  - both runs started:
    - anchor `stage3_best_phaseB`
    - then five `phaseA_selected` challengers

Interpretation:

- this is a valid negative result for the implemented Study 3 intervention
- the new Phase-C start policy executed correctly
- but it did not produce any new distinct Phase-C starts on `seed411`
- the strongest current reading is:
  - by the time Phase-C starts are chosen, the single carried `phaseB_topk`
    row is not contributing an additional distinct startable key beyond the
    anchor / `phaseA_selected` pool
- so Phase-C start balancing alone is not the marginal lever here

Programme effect:

- Study 3 should now be treated as:
  - successful implementation
  - successful execution proof
  - negative scientific result on this seed / current pool shape
- this shifts the next meaningful intervention downstream-but-earlier:
  - Phase-B family preservation / family-aware downstream slot retention
- next implementation brief:
  - `planning/working/no_wli_study2_phaseb_preservation_plan_2026-03-28.md`
- locked experiment specs:
  - `planning/working/no_wli_locked_experiment_specs_2026-03-28.md`

### 2026-03-28 Study 2 implementation ready: isolated Phase-B family preservation with robust canary

Locked implementation boundary:

- preserve more distinct families only in the downstream carry-forward path
- leave ordinary Phase-B ranking unchanged
- leave Phase-B run seeds unchanged
- leave Phase-C rescue logic unchanged

Implemented policy surface:

- `phaseb_family_preservation_policy = reserve_by_family_v1`
- `phaseb_family_view_id = prefix_hamming_le_24`
- `phaseb_family_reserved_slots = 2`

Implementation surfaces:

- shared family-view helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/family_views.py`
- audit helper now imports the shared family view definitions:
  - `tools/benchmarks/periodic_sub_trans/no_wli/audit_basin_family_diversity_alignment.py`
- runtime/config/bridge/plumbing:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runtime_defaults.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/profile_defaults.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_calls.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_lock_payload.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- core downstream preservation logic:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`

New proof assets:

- deterministic policy test:
  - `tests/tools/test_no_wli_stage3_phasec.py`
    - proves the Study 2 policy changes downstream carry-forward composition
      while leaving ordinary Phase-B selected count unchanged
- dedicated Study 2 canary:
  - `tests/tools/test_no_wli_phaseb_family_preservation_canary.py`
    - proves preset resolution, live state, `run_config`, lock payload,
      runtime bridge, and resume parsing all carry the new Study 2 fields
- fixture runtime coverage:
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
    - proves the active v39 compare materializes as the intended 2-job
      `seed411` control-vs-candidate lane

Short proof history:

- initial focused Study 2 slice surfaced two real correctness issues before
  any long run:
  - missing default imports in `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
  - synthetic deterministic test keys that were still transitively connected
    under the real `prefix_hamming_le_24` family view
- both were corrected before final proof was accepted

Focused proof slice after fixes:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - outcome:
    - `30 passed`

Broader meaningful confirmation slice:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py -q`
  - outcome:
    - `95 passed`

Prepared live compare for the user:

- seed:
  - `411`
- control:
  - `stage3_preserve_tieband_probe_p9`
- candidate:
  - `stage3_phaseb_family_preserve_p9`
- active matrix control files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v39_p9c3_seed411_phaseb_family_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v39_p9c3_seed411_phaseb_family_compare_2job.jsonl`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v39_p9c3_seed411_phaseb_family_compare_2job.json`

Interpretation lock before the long run:

- Study 1:
  - valid negative on `211`
- Study 3:
  - valid negative on `411`
- Study 2:
  - now isolated cleanly enough for the next meaningful `seed411` live compare

### 2026-03-29 Study 2 `seed411` live compare finished: visible outcome negative, persistence telemetry incomplete

Completed runs:

- control preserve run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T020350857797Z__bench_solve_pipeline_no_wli__55b7159`
  - matrix event elapsed:
    - `14454.284437179565s`
- candidate family-preserve run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T060445115113Z__bench_solve_pipeline_no_wli__55b7159`
  - matrix event elapsed:
    - `14831.120589017868s`

Validity checks that passed:

- matrix state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v39_p9c3_seed411_phaseb_family_compare_2job.json`
  - `completed_jobs = 2`
  - `stopped_early = 0`
- intended config delta present:
  - control `run_config.json`
    - `stage3.two_phase.family_preservation.policy = "off"`
    - `stage3.two_phase.family_preservation.family_view_id = "prefix_hamming_le_24"`
    - `stage3.two_phase.family_preservation.reserved_slots = 0`
  - candidate `run_config.json`
    - `stage3.two_phase.family_preservation.policy = "reserve_by_family_v1"`
    - `stage3.two_phase.family_preservation.family_view_id = "prefix_hamming_le_24"`
    - `stage3.two_phase.family_preservation.reserved_slots = 2`
- unchanged guard field:
  - both runs kept:
    - `stage3.two_phase.phase_c.start_policy = "source_order"`
- both runs emitted live handoffs:
  - `resume_handoffs/fixture_fixture_001_p9_c3_l1000__text0__seed411/manifest.json`
  - `stage2_to_stage3.source = "live_stage3_pipeline"`

Visible top-level outcome:

- control:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`
- candidate:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`

Visible downstream outcome:

- control:
  - `phaseB_selected_unique_end_hash = 8`
  - `phaseC_candidate_pool_unique_end_hash = 8`
  - `phaseC_candidate_pool_source_counts = { "stage3_best_phaseB": 1, "phaseB_topk": 1, "phaseA_selected": 8 }`
  - `phaseC_start_keys_used = 6`
  - `phaseC_start_unique_end_hash = 6`
  - `phaseC_start_source_counts = { "stage3_best_phaseB": 1, "phaseA_selected": 5 }`
- candidate:
  - `phaseB_selected_unique_end_hash = 8`
  - `phaseC_candidate_pool_unique_end_hash = 8`
  - `phaseC_candidate_pool_source_counts = { "stage3_best_phaseB": 1, "phaseB_topk": 1, "phaseA_selected": 8 }`
  - `phaseC_start_keys_used = 6`
  - `phaseC_start_unique_end_hash = 6`
  - `phaseC_start_source_counts = { "stage3_best_phaseB": 1, "phaseA_selected": 5 }`

Checkpoint comparison:

- control:
  - `phasec_start_checkpoints.jsonl`
- candidate:
  - `phasec_start_checkpoints.jsonl`
- observed:
  - same six `candidate_hash` values
  - same order
  - same sources:
    - anchor `stage3_best_phaseB`
    - then five `phaseA_selected` challengers

Important limitation:

- the new Study 2 family telemetry did not persist into the saved readout
  artifacts:
  - not present in `best/best_instance.json`
  - not present in `stages.json`
- missing persisted fields include:
  - `phaseB_family_count_in_top_band`
  - `phaseB_family_preserved_count`
  - `phaseB_family_reservation_applied`
  - `phaseB_downstream_selected_count`
  - `phaseB_downstream_selected_unique_end_hash`

Interpretation:

- the run is operationally negative on all visible downstream and solve outputs
- but it is not yet a fully locked scientific negative under the current
  standard, because the policy-specific preservation telemetry was not saved
- that means the exact question remains open:
  - did the policy truly have no downstream effect
  - or did it apply but later collapse back to the same observable Phase-C pool

Next action:

- do not move to a new science phase yet
- first fix persistence of the Study 2 family telemetry into the saved artifact
  path
- then rerun the same v39 `seed411` control-vs-candidate compare

### 2026-03-29 Study 2 persistence bug confirmed and fixed before rerun

Root cause:

- the Study 2 family-preservation fields were produced in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- but they were dropped before saved artifact emission because:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
    did not carry them into iteration state
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
    did not pass them into `build_stage3_diagnostics(...)`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
    did not serialize them into `stage3_diagnostics`

Code changes:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  - now propagates:
    - `phaseB_family_preservation_policy`
    - `phaseB_family_view_id`
    - `phaseB_family_reserved_slots`
    - `phaseB_family_count_in_top_band`
    - `phaseB_family_preserved_count`
    - `phaseB_family_reservation_applied`
    - `phaseB_downstream_selected_count`
    - `phaseB_downstream_selected_unique_end_hash`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - now passes those fields into `build_stage3_diagnostics(...)`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
  - now serializes those fields into `stage3_diagnostics`

New regression coverage:

- `tests/tools/test_no_wli_truth_diagnostics.py`
  - extended to prove the new Study 2 fields survive diagnostics building
- `tests/tools/test_no_wli_stage35_substitution_solver.py`
  - added a focused `stage3_iteration_flow` propagation test for the new
    Study 2 fields

Meaningful proof slice after fix:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_stage35_substitution_solver.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_artifact_resume.py -q`
  - outcome:
    - `56 passed`

Decision:

- the next run should be the same v39 Study 2 compare
- interpret the previous completed v39 run as invalid for final science
  lock, because the saved artifact path was incomplete

### 2026-03-29 Study 2 rerun re-armed on fresh control files

The first post-fix rerun attempt resumed immediately because the matrix still
pointed at the already-completed v39 control files.

Science configuration remains unchanged:

- seed:
  - `411`
- control preset:
  - `stage3_preserve_tieband_probe_p9`
- candidate preset:
  - `stage3_phaseb_family_preserve_p9`

Only the control-file paths were advanced to a fresh rerun set:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v40_p9c3_seed411_phaseb_family_compare_2job_rerun.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v40_p9c3_seed411_phaseb_family_compare_2job_rerun.jsonl`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v40_p9c3_seed411_phaseb_family_compare_2job_rerun.json`

Purpose:

- rerun the same Study 2 compare unchanged
- capture the newly persisted family-preservation telemetry
- only then decide whether Study 2 is a valid negative or not

### 2026-03-29 Study 2 rerun result: valid negative on seed 411

Completed rerun:

- control run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T155853670179Z__bench_solve_pipeline_no_wli__55b7159`
- candidate run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T204310438057Z__bench_solve_pipeline_no_wli__55b7159`
- matrix control files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v40_p9c3_seed411_phaseb_family_compare_2job_rerun.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v40_p9c3_seed411_phaseb_family_compare_2job_rerun.jsonl`

Top-level result:

- control:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`
- candidate:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`

Persisted Study 2 telemetry recovered from:

- control:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T155853670179Z__bench_solve_pipeline_no_wli__55b7159/best/best_instance.json`
- candidate:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T204310438057Z__bench_solve_pipeline_no_wli__55b7159/best/best_instance.json`

Observed Study 2 telemetry:

- control:
  - `phaseB_family_preservation_policy = "off"`
  - `phaseB_family_view_id = "prefix_hamming_le_24"`
  - `phaseB_family_reserved_slots = 0`
  - `phaseB_family_count_in_top_band = 8`
  - `phaseB_family_preserved_count = 8`
  - `phaseB_family_reservation_applied = 0`
  - `phaseB_downstream_selected_count = 8`
  - `phaseB_downstream_selected_unique_end_hash = 8`
- candidate:
  - `phaseB_family_preservation_policy = "reserve_by_family_v1"`
  - `phaseB_family_view_id = "prefix_hamming_le_24"`
  - `phaseB_family_reserved_slots = 2`
  - `phaseB_family_count_in_top_band = 8`
  - `phaseB_family_preserved_count = 8`
  - `phaseB_family_reservation_applied = 1`
  - `phaseB_downstream_selected_count = 8`
  - `phaseB_downstream_selected_unique_end_hash = 8`

Visible downstream outcome remained unchanged:

- `phaseB_selected_unique_end_hash = 8`
- `phaseC_candidate_pool_unique_end_hash = 8`
- `phaseC_start_keys_used = 6`
- `phaseC_start_source_counts = { "stage3_best_phaseB": 1, "phaseA_selected": 5 }`
- `phasec_start_checkpoints.jsonl` was identical between runs

Interpretation:

- the Study 2 policy did execute
- it did not change the downstream selected set
- the cleanest reading is that Phase-B family reservation inside the current
  top-8 band is not the bottleneck on `seed411`
- the bottleneck is now more likely the width or valuation of the band that is
  being carried forward, not preservation inside that band

Next test prepared:

- v41 isolated Phase-B carry-forward-width probe
- control preset:
  - `stage3_preserve_tieband_probe_p9`
- candidate preset:
  - `stage3_phaseb_width_probe_p9`
- only intended semantic change:
  - `force_stage3_phaseb_top_n = 32`

### 2026-03-30 v41 width probe status: invalid due accelerator failure

The first width-probe long run did not produce a candidate science result.

Evidence:

- matrix state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v41_p9c3_seed411_phaseb_width_compare_2job.json`
- matrix events:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v41_p9c3_seed411_phaseb_width_compare_2job.jsonl`

Observed outcome:

- control job completed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260330T034031451631Z__bench_solve_pipeline_no_wli__55b7159`
- candidate job started, then failed after about `58.9s` with:
  - `error_type = "AcceleratorError"`
  - `error = "CUDA error: unknown error"`
- partial candidate run dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260330T085228874213Z__bench_solve_pipeline_no_wli__55b7159`

Why this run is invalid for science:

- the candidate run never wrote any progress units
- `run_manifest.json` stayed at:
  - `run_status = "running"`
  - `done_units = 0`
  - `history_rows_written = 0`
- no `instances.json`, `stages.json`, or Phase-C checkpoints were produced

Follow-up sanity check:

- immediate CUDA smoke check succeeded on the same machine:
  - `cuda_available = True`
  - matrix multiply completed successfully

Current interpretation:

- treat v41 as an accelerator/runtime failure, not as a negative width result
- rerun the exact same width compare on fresh control files

Rerun re-armed:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v42_p9c3_seed411_phaseb_width_compare_2job_rerun.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v42_p9c3_seed411_phaseb_width_compare_2job_rerun.jsonl`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v42_p9c3_seed411_phaseb_width_compare_2job_rerun.json`

### 2026-03-30 hardening backlog recorded while v42 is running

A concrete pipeline-hardening backlog has been written while the v42 width
compare is in flight:

- `planning/working/no_wli_pipeline_hardening_backlog_2026-03-30.md`

Purpose:

- turn the recent reliability discussion into a concrete file-level plan
- separate science-blocking bug classes from lower-priority cleanup
- define the minimum canaries needed before future long compares

Main conclusions recorded there:

- the central config/state smell is real:
  - `run_fixture_matrix.py` still passes `globals()` into the matrix mainflow
  - `fixture_matrix_mainflow.py` still consumes a broad mutable `state` bag
  - `runner_state_defaults.py` still mirrors active values into many
    `_..._DEFAULT` shadow keys
- the recommended target is not one giant config object but several smaller
  typed layers:
  - matrix config
  - matrix control files
  - typed tuning presets
  - resolved run config
  - runner services
  - narrow stage-boundary payloads
- the highest-priority hardening phases are:
  - runtime preflight
  - matrix config spine
  - rerun hygiene
  - preset typing
  - stage-boundary payloads
  - diagnostics persistence unification

This is planning only; it does not change the currently running v42 science
configuration.

### 2026-03-30 first hardening slice implemented

The first concrete slice of the hardening backlog is now implemented.

Files changed:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runtime_preflight.py`

What changed:

- fixture-matrix entry no longer passes `globals()` into mainflow
- matrix entry now goes through a typed `FixtureMatrixMainflowConfig`
- state/event/plan control files now derive from a single
  `EXPERIMENT_RUN_ID`
- experiment identity is now recorded in:
  - matrix-entry state
  - plan payload
  - run-state metadata
- a torch/CUDA runtime preflight boundary now exists and fails early if the
  smoke test itself fails

Evidence:

- focused proof:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_runtime_preflight.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `25 passed`
- broader guard slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_runtime_preflight.py -q`
  - `35 passed`

Important scope note:

- this is a completed hardening slice, not the full backlog
- it closes:
  - matrix-entry `globals()` usage
  - control-file derivation drift
  - missing experiment id metadata
  - absence of runtime preflight
- it does not yet close:
  - typed preset migration
  - resolved run-config object
  - diagnostics persistence unification

### 2026-03-30 v42 width probe closed as a valid negative with a useful structural signal

The v42 rerun completed cleanly and is scientifically valid.

Evidence:

- matrix state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v42_p9c3_seed411_phaseb_width_compare_2job_rerun.json`
- matrix events:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v42_p9c3_seed411_phaseb_width_compare_2job_rerun.jsonl`
- control run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260330T150529396668Z__bench_solve_pipeline_no_wli__55b7159`
- candidate run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260330T175546232525Z__bench_solve_pipeline_no_wli__55b7159`

Correctness/validity:

- `completed_jobs = 2`
- `stopped_early = 0`
- no `job_error` row
- intended config delta present:
  - control:
    - `run_config.json -> stage3.two_phase.phase_b_top_n = 8`
  - candidate:
    - `run_config.json -> stage3.two_phase.phase_b_top_n = 32`
- other late knobs stayed stable:
  - `phase_c.start_policy = "source_order"`
  - `family_preservation.policy = "off"`
  - `phase_c.start_keys = 6`

Top-level outcome:

- control:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`
- candidate:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`

What changed materially:

- control `best/best_instance.json -> stage3_diagnostics`:
  - `phaseB_top_n_used = 8`
  - `phaseB_selected_unique_end_hash = 8`
  - `phaseB_downstream_selected_unique_end_hash = 8`
  - `phaseC_candidate_pool_count = 10`
  - `phaseC_candidate_pool_unique_end_hash = 8`
  - `phaseC_candidate_pool_source_counts = {"stage3_best_phaseB":1,"phaseB_topk":1,"phaseA_selected":8}`
- candidate `best/best_instance.json -> stage3_diagnostics`:
  - `phaseB_top_n_used = 32`
  - `phaseB_selected_unique_end_hash = 32`
  - `phaseB_downstream_selected_unique_end_hash = 32`
  - `phaseC_candidate_pool_count = 34`
  - `phaseC_candidate_pool_unique_end_hash = 32`
  - `phaseC_candidate_pool_source_counts = {"stage3_best_phaseB":1,"phaseB_topk":1,"phaseA_selected":32}`

What did not change:

- actual Phase-C starts were identical:
  - `phaseC_start_keys_used = 6`
  - `phaseC_start_unique_end_hash = 6`
  - `phaseC_start_source_counts = {"stage3_best_phaseB":1,"phaseA_selected":5}`
- `phasec_start_checkpoints.jsonl` had the same six `candidate_hash` values in
  the same order in both runs

Interpretation:

- widening the Phase-B carry-forward band from `8` to `32` clearly increased
  carried variety
- that extra variety still did not become exploited variety
- width alone is therefore not the marginal lever on `seed411`

Sharpened next-study reading:

- the bottleneck now appears later than simple band width and later than family
  reservation inside the top band
- but it is also sharper than the original Phase-C source-order hypothesis:
  the widened variety is mostly in `phaseA_selected`, not in a distinct
  `phaseB_topk` row that later balancing could trivially rescue
- the next science study, if resumed, should be about how starts are chosen
  within the widened downstream pool, especially inside the larger
  `phaseA_selected` carry-forward set

Practical consequence:

- this is not a reason to run another pure width compare
- current best use of the result is to fold it into the next exploitation study
  design while continuing pipeline hardening

### 2026-03-30 second hardening slice: preset typing and stale-rerun rejection

While carrying the valid v42 width result forward, the next pipeline-hardening
slice has also been implemented and proven.

What changed:

- typed `Stage3TuningPreset` normalization now exists at the fixture-matrix
  boundary
- unknown preset fields now fail at normalization time instead of being silently
  tolerated
- `run_fixture_matrix.py` now materializes normalized presets into mainflow
  state instead of passing raw preset dicts through
- rerun/run-state identity is now explicit:
  - `experiment_run_id`
  - `planned_job_count`
  - `planned_job_keys_signature`
  - `run_state_version = "v2"`
- stale run-state files are now rejected if:
  - the `experiment_run_id` does not match
  - the planned job-key signature does not match
  - identity fields are missing from an existing run-state file
- duplicate materialized job keys are now rejected before checkpoint execution

Evidence:

- code:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_runtime.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan.py`
- proof tests:
  - `tests/tools/test_no_wli_fixture_matrix_hardening.py`
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - `tests/tools/test_no_wli_fixture_matrix_mainflow.py`

Meaningful proof:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_hardening.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix.py -q`
  - `38 passed`
- broader guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_hardening.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix.py tests/tools/test_no_wli_runtime_preflight.py tests/tools/test_no_wli_stage3_entry_canary.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `45 passed`

Interpretation:

- this does not produce a new science result by itself
- it does materially improve trust in future long compares
- especially for the bug classes that have already wasted runs:
  - malformed preset/config payloads
  - accidental stale reruns
  - ambiguous control-file identity

### 2026-03-30 finalize-path persistence hardening

The next hardening slice is now in place on the artifact/instance finalize path.

What changed:

- one shared `IterationPersistencePayload` now builds the finalize-path
  reviewer-facing enrichment fields instead of `iteration_finalize.py`
  hand-threading them piecemeal
- this now centralizes:
  - truth diagnostics
  - word-ngram report payloads
  - Stage-3.5 archive/seed rows
  - Stage-3.5 summary flags/fields
  - target-key payload fields

Evidence:

- code:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_payload.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_finalize.py`
- proof tests:
  - `tests/tools/test_no_wli_iteration_persistence_payload.py`
  - `tests/tools/test_no_wli_iteration_finalize_word_ngram.py`
  - `tests/tools/test_no_wli_truth_diagnostics.py`
  - `tests/tools/test_no_wli_run_completion.py`

Meaningful proof:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_run_completion.py -q`
  - `7 passed`
- combined guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_hardening.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix.py tests/tools/test_no_wli_runtime_preflight.py tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_run_completion.py tests/tools/test_no_wli_stage3_entry_canary.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `52 passed`

Interpretation:

- this is another trust-improving hardening step, not a new science result
- it closes more of the exact bug class that previously made Study 2
  persistence scientifically incomplete on the first pass

### 2026-03-30 external review pack refreshed

A new self-contained external review bundle has been prepared at:

- `planning/working/no_wli_external_review_pack_2026-03-30`

What it includes:

- the current planning logs
- the locked four live studies plus the earlier `v36` precursor compare
- copied fixture-matrix state/event/plan files
- copied run directories for the key compares
- ancillary catalog and ranking-probe evidence
- an appendix with the previous review pack zip

Reviewer-facing summary docs added in the pack root:

- `README.md`
- `01_summary_for_reviewers.md`
- `02_four_live_tests_and_results.md`
- `03_pipeline_hardening_status.md`
- `04_open_questions_and_blockers.md`
- `05_evidence_index.md`

Purpose:

- freeze the current review baseline after:
  - Study 1 valid negative
  - Study 3 valid negative
  - Study 2 valid negative
  - v42 width valid negative with strong carried-versus-exploited variety signal
- make the current science and hardening state reviewable without digging back
  through the live repo tree

### 2026-03-30 pack review cross-check: sharper post-v42 interpretation

The new pack has now been cross-checked again against the copied run
directories and the `stage3_diagnostics` fields for the main compares:

- precursor `v36`
- Study 1 `v37`
- Study 3 `v38`
- Study 2 rerun `v40`
- width probe `v42`

Refined reading:

- the "all negative" top-level story is real, but it is not arbitrary
- each study hit a plausible compression point and came back negative in a
  coherent way
- the later negatives are therefore more useful than they first appear

Sharper seed split:

- `211`:
  - still best read as an upstream reach / wrong-neighborhood problem
  - Study 1 widened Stage-3 entry materially but still fed the same effective
    neighborhood
  - current best wording is:
    - the right family is not surfacing strongly enough before or at Stage-3
      entry
- `411`:
  - now best read as a carried-to-exploited variety conversion problem
  - widening the late pool does create much more carried variety
  - but the pipeline is still failing to convert that widened pool into a
    genuinely new explored challenger

Most important new operational insight:

- the `411` bottleneck now looks more specific than:
  - generic Phase-C source balancing
  - generic late width
  - family reservation inside the current narrow top-8 band
- best current wording is:
  - the next useful `411` science study should target novel-start
    carry-through from the widened late pool
  - i.e. force at least one genuinely distinct non-anchor challenger from the
    widened downstream pool into the actual explored start set

Practical consequence:

- do not repeat Studies 1/2/3 in near-identical form
- for `211`, the next science move should shift further upstream:
  - Stage-2 to Stage-3 promoted-family generation
  - promotion homogeneity / family-diversity logic
  - or a more structural basin-generation intervention
- for `411`, the next science move should be narrower and more specific:
  - novel-start carry-through from the widened late pool

### 2026-03-30 broader interpretation: why progress has been slow

Current best broad answer:

- this is genuinely hard
- and the current pipeline is also still making some suboptimal
  search-and-selection decisions
- but those decisions are not best understood as obviously foolish mistakes

What the evidence does *not* support:

- broad engineering collapse as the main explanation
- "the tools are useless" as the main explanation
- one trivial missing trick as the explanation

What the evidence *does* support:

- there is real signal
- the pipeline can move when it finds a real lever
  - example: precursor `v36` on `seed411`
- but the solver is still brittle at several compression points:
  - upstream reach into the right family
  - preservation of promising families
  - conversion of carried variety into actually explored starts

Best current plain-English framing:

- we are not mainly failing because there is no signal
- we are failing because on hard seeds the system may:
  - fail to get near the right family at all
  - get near it but not preserve it strongly enough
  - carry more variety forward but still not actually explore it
  - rank the wrong family highly enough that the better one never gets enough
    chance to prove itself

General consequence:

- the current work should not be read as "nothing worked"
- it should be read as:
  - the negative studies narrowed the search space
  - the next solver improvements should target robustness of family recognition,
    preservation, and exploitation

### 2026-03-30 next-study implementation plan locked: `411` novel-start carry-through

The next `411`-track implementation plan is now written and locked in:

- `planning/working/no_wli_study411_novel_start_carrythrough_plan_2026-03-30.md`

Why this study is next:

- generic Phase-C balancing was a valid negative
- narrow-band family reservation was a valid negative
- widened late width was a valid negative on solve outcome but a strong
  positive on carried variety
- therefore the next downstream question is no longer "more width" or
  "more balancing"
- it is:
  - can one or two eligible novel non-anchor challengers from the widened late
    pool be carried through into the actual explored Phase-C starts?

Locked design choices:

- control is the widened-late baseline, not the narrow baseline
- novelty reuses existing repo language:
  - distinct `end_hash`
  - plus `prefix_hamming_le_24`
- the study must record:
  - eligible novel challenger count
  - selected novel challenger count
  - eligible-but-not-selected challenger count

Anti-drift rule:

- this remains a start-selection study only
- no bundled changes to:
  - Phase-B ranking
  - tie-band widening
  - rescue
  - Stage-3.5

### 2026-03-30 `411` novel-start carry-through implemented and v43 compare prepared

Implementation evidence:

- study policy and selection logic:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- shared novelty/family-view support:
  - `tools/benchmarks/periodic_sub_trans/no_wli/family_views.py`
- explicit diagnostics persistence:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
- new live compare preset/config:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

What the implementation changed:

- added Phase-C start policy:
  - `novel_challenger_v1`
- reused existing novelty language:
  - distinct `end_hash`
  - `prefix_hamming_le_24`
- persisted the new study telemetry all the way into `stage3_diagnostics`

What it intentionally did not change:

- Phase-B ranking semantics
- candidate-pool construction
- rescue semantics
- Stage-3.5

Meaningful proof:

- deterministic policy and persistence slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py -q`
  - `17 passed`
- config/runtime/canary slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py -q`
  - `36 passed`
- broader guard slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `97 passed`

Prepared live compare:

- experiment id:
  - `tune_v43_p9c3_seed411_novel_start_compare_2job`
- control:
  - `stage3_phaseb_width_probe_p9`
- candidate:
  - `stage3_phasec_novel_challenger_p9`
- control files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v43_p9c3_seed411_novel_start_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v43_p9c3_seed411_novel_start_compare_2job.jsonl`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v43_p9c3_seed411_novel_start_compare_2job.json`

Current scientific status:

- no live result claimed yet
- implementation and proof are complete
- next meaningful long run is now the v43 widened-late baseline vs
  `novel_challenger_v1` compare

### 2026-03-30 v43 pre-run hardening: explicit Phase-C diagnostics contract and finalize-path proof

Why this was needed:

- the `v43` study depends on new Phase-C novelty diagnostics
- the builder-level persistence tests were already green
- but there was still a fail-open risk:
  - `iteration_post_stage3.py` could silently default dropped Phase-C telemetry
    to zeros / empty strings
  - and the real finalize-path artifact build had not yet been proven with the
    new novelty fields end to end

Implemented:

- new explicit contract helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_diagnostics_contract.py`
- contract enforced when consuming two-phase follow-up:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- contract enforced before building reviewer-facing diagnostics:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
- finalize-path persistence proof extended:
  - `tests/tools/test_no_wli_iteration_finalize_word_ngram.py`
- direct contract tests added:
  - `tests/tools/test_no_wli_phasec_diagnostics_contract.py`

What this hardening guarantees:

- if Phase-C ran, required Phase-C diagnostics must exist before later
  serialization
- if `novel_challenger_v1` ran, the required novelty counters and start-summary
  fields must exist before later serialization
- the real finalize/commit artifact payload now has explicit proof coverage for:
  - `phaseC_start_policy`
  - `phaseC_novel_view_id`
  - `phaseC_anchor_candidate_hash`
  - `phaseC_candidate_pool_eligible_novel_count`
  - `phaseC_selected_novel_challenger_count`
  - `phaseC_selected_novel_challenger_hashes`
  - per-start `selection_bucket` / `selected_by_novel_policy`

Meaningful proof:

- focused slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `41 passed`
- broader guard slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `101 passed`

Operational status after this slice:

- no live result claimed yet for `v43`
- the next meaningful long compare is still:
  - widened-late baseline `stage3_phaseb_width_probe_p9`
  - vs `stage3_phasec_novel_challenger_p9`
- but the artifact path is now better protected against silent telemetry loss

### 2026-03-30 v43 invalidated by live Stage-3 bridge-state bug

The prepared `v43` novel-start compare is not a science result.

What happened:

- both jobs failed with the same live error:
  - `KeyError: 'STAGE3_PHASEC_START_POLICY'`
- control failed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T033734663702Z__bench_solve_pipeline_no_wli__55b7159`
- candidate failed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T034501424369Z__bench_solve_pipeline_no_wli__55b7159`
- state / event evidence:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v43_p9c3_seed411_novel_start_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v43_p9c3_seed411_novel_start_compare_2job.jsonl`

Why this is not a science readout:

- `completed_jobs = 0`
- `completed_job_keys = []`
- both jobs ended in `job_error`
- neither run produced final reviewer-facing instance artifacts

Important cross-check:

- both `run_config.json` files were already correct before the crash:
  - control:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T033734663702Z__bench_solve_pipeline_no_wli__55b7159/run_config.json`
    - `stage3.two_phase.phase_c.start_policy = "source_order"`
  - candidate:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T034501424369Z__bench_solve_pipeline_no_wli__55b7159/run_config.json`
    - `stage3.two_phase.phase_c.start_policy = "novel_challenger_v1"`

Root cause:

- the failure was not preset resolution or lock/config emission
- it was a live per-iteration bridge-state drop in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_iteration_bridge.py`
- `_build_stage3_state(...)` was not forwarding:
  - `STAGE3_PHASEC_START_POLICY`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  later requires:
  - `state["STAGE3_PHASEC_START_POLICY"]`

Fix:

- added explicit Stage-3 config forwarding in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_iteration_bridge.py`
- strengthened the real bridge regression in:
  - `tests/tools/test_no_wli_stage_engine_iteration_bridge.py`
  - now proves `novel_challenger_v1` survives the live stage-engine bridge into
    Stage-3 runtime state

Meaningful proof:

- exact regression slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `26 passed`
- broader guard slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `108 passed`

Scientific consequence:

- `v43` is invalid and should not be interpreted
- the next meaningful long compare is the exact same study question re-armed on
  fresh control files after the explicit bridge fix

### 2026-03-30 v44 invalidated again: real live failure was earlier in iteration-matrix config/state

The fresh `v44` rerun also failed and is also not a science result.

What happened:

- both jobs failed again with:
  - `KeyError: 'STAGE3_PHASEC_START_POLICY'`
- state / event evidence:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v44_p9c3_seed411_novel_start_compare_2job_rerun.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v44_p9c3_seed411_novel_start_compare_2job_rerun.jsonl`
- both jobs still ended with:
  - `completed_jobs = 0`
  - `completed_job_keys = []`

What this corrected:

- the first bridge fix in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_iteration_bridge.py`
  was real, but it was not the live failure site for fixture-matrix runs
- the actual runtime path still builds an `IterationMatrixConfig` and then
  reconstructs stage-engine state in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_builder.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
- that path was still omitting:
  - `STAGE3_PHASEC_START_POLICY`

Actual root cause:

- `IterationMatrixConfig` did not carry `stage3_phasec_start_policy`
- `_build_stage_engine_iteration_state(...)` in
  `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
  therefore could not forward it into the live Stage-3 state

Fix:

- added `stage3_phasec_start_policy` to `IterationMatrixConfig`
- threaded it through:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_builder.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
- extracted a shared Stage-3 runtime-state contract in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_state_contract.py`
- both live paths now use that contract:
  - `stage_engine_iteration_bridge.py`
  - `iteration_matrix_flow.py`

Meaningful proof:

- focused live-path slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `34 passed`
- broader guard slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `116 passed`

Scientific consequence:

- `v44` is invalid and should not be interpreted
- the first bridge fix remains valid but was insufficient for the actual live
  matrix path
- the same `411` novel-start compare is now re-armed again after the actual
  matrix-path fix

### 2026-03-31 v45 valid negative: novel-start carry-through executed but did not change the actual explored set

The fresh `v45` rerun is a valid science result.

Evidence:

- control run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T053053469532Z__bench_solve_pipeline_no_wli__55b7159`
- candidate run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T075915341627Z__bench_solve_pipeline_no_wli__55b7159`
- run state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v45_p9c3_seed411_novel_start_compare_2job_rerun2.json`
- event log:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v45_p9c3_seed411_novel_start_compare_2job_rerun2.jsonl`

Validity:

- `completed_jobs = 2`
- `stopped_early = 0`
- no `job_error`
- both jobs wrote full reviewer-facing artifacts

Top-level result:

- control:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`
- candidate:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`

What changed structurally:

- widened late-pool shape stayed the same in both runs:
  - `phaseB_top_n_used = 32`
  - `phaseB_selected_unique_end_hash = 32`
  - `phaseC_candidate_pool_count = 34`
  - `phaseC_candidate_pool_unique_end_hash = 32`
- the candidate really did execute the new policy:
  - `phaseC_start_policy = "novel_challenger_v1"`
  - `phaseC_candidate_pool_eligible_novel_count = 31`
  - `phaseC_selected_novel_challenger_count = 2`
  - `phaseC_selected_novel_challenger_hashes = ["9002ee09917e5a0d", "0e963798c8017f96"]`
- but the actual explored start set did not change relative to the widened-late
  control:
  - `phaseC_start_keys_used = 6`
  - `phaseC_start_unique_end_hash = 6`
  - `phaseC_start_source_counts = { "stage3_best_phaseB": 1, "phaseA_selected": 5 }`
  - the same six `candidate_hash` values appear in
    `phaseC_start_summaries` and `phasec_start_checkpoints.jsonl`

Most important interpretation:

- this is a valid negative for `novel_challenger_v1`
- the policy did not fail open
- it reserved two novel challengers, but those two rows were already inside the
  widened-late legacy six-start set
- so the policy changed the *selection label* (`novel_reserved` vs
  `legacy_fill`) without changing the *actual explored start set*

Important metric clarification:

- `phasec_start_checkpoints.jsonl` `init_match` / `final_match` fields are real
  per-start truth-match ratios in this live path
- they are written from `match_ratio_fn(...)`, and in the live runner that is
  `base._match_ratio(...)`, i.e. full plaintext-vs-target char match
- however the saved run winner remains score-selected through
  `_phasec_is_better(...)`
- so a Phase-C challenger can reach much higher truth than the saved stage
  winner without changing top-level `best_match_ratio`
- concrete `v45` evidence:
  - anchor start:
    - `candidate_hash = 73eee2bf84b7c07f`
    - `final_match = 0.039`
    - `final_score = 0.19101667350788198`
    - `became_global_best = 1`
  - challenger start:
    - `candidate_hash = 9002ee09917e5a0d`
    - `final_match = 0.418`
    - `final_score = 0.17284542866740327`
    - `became_global_best = 0`

Scientific consequence:

- this study rules out the simple story that merely reserving novel challengers
  from the widened late pool is enough
- the next `411` question is more precise:
  - can we force one or two novel challengers that are *not already selected by
    legacy widened-late fill* into the actual explored Phase-C starts?
- this also exposes an important downstream adequacy issue:
  - top-level run summaries currently hide high-truth challenger paths if they
    lose on score

### 2026-03-31 late-stage scorer data-prep slice: truth-gap reporting/dataset plus replay-fixture export scaffold

Purpose:

- prepare the next late-stage scorer experiment with real explored-frontier
  evidence instead of toy examples
- harden reviewer-facing reporting so benchmark runs stop hiding strong
  score-losing challengers
- capture enough per-start material that a future run can be replayed with
  trial late-stage selectors or scorers

Implemented:

- reviewer-facing Phase-C truth disagreement reporting:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_reporting.py`
  - threaded into:
    - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
- truth-gap dataset/export support:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_gap_dataset.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_phasec_truth_gap_dataset.py`
- replay-fixture capture/export support:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_frontier_fixture.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_frontier_fixture.py`
- Phase-C start summaries now persist replay-oriented material:
  - `init_key_idx`
  - `init_plaintext_idx`
  - `final_key_idx`
  - `final_plaintext_idx`
  in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- replay-material completeness is now part of the Phase-C diagnostics contract:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_diagnostics_contract.py`

Meaningful proof:

- truth-gap reporting/dataset slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_stage35_substitution_solver.py -q`
  - `25 passed`
- replay-fixture / Phase-C capture slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_late_stage_frontier_fixture.py -q`
  - `25 passed`
- broader guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_phasec_rescue_replay.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_stage35_substitution_solver.py -q`
  - `59 passed`

Evidence generated:

- truth-gap dataset:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/summary.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.csv`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/summary.md`
- frozen `v45` late frontier export:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v45_seed411_late_frontier.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v45_seed411_late_frontier.md`

What the current exported data already proves:

- the benchmark-exposed late-stage selection failure in `v45` is real and
  recurrent enough to support a dataset:
  - the filtered truth-gap export currently contains `14` rows
- the canonical `seed411` disagreement remains:
  - score-selected winner hash `73eee2bf84b7c07f`
  - best explored challenger hash `9002ee09917e5a0d`
  - winner truth about `0.039`
  - challenger truth about `0.418`
  - truth gap about `0.379`

Current limitation:

- the historical `v45` run predates the new replay-capture fields
- so the exported frozen frontier is telemetry-rich but not yet replay-material
  complete:
  - `frontier_key_material_complete = 0`
  - current candidate rows do not yet carry populated:
    - `init_key_idx`
    - `init_plaintext_idx`
    - `final_key_idx`
    - `final_plaintext_idx`

Scientific consequence:

- we now have enough real late-frontier evidence to write a stronger
  late-stage scorer spec
- but one post-hardening comparable run is still needed before we have a fully
  replayable scorer-fixture frontier for trial-key / trial-selector testing
- this should be treated as data-prep and hardening, not yet a new scorer
  result

### 2026-03-31 Stage A scaffold landed: benchmark-only late-stage selector harness on frozen `v45`

Purpose:

- start the scorer experiment loop on real exported data without changing live
  solver behavior
- freeze the known `v45` late-stage disagreement as a cheap regression fixture
- make it easy to benchmark late-stage selector ideas before a replayable
  frontier run exists

Implemented:

- frozen fixture:
  - `tests/fixtures/no_wli/v45_seed411_late_frontier_fixture.json`
- benchmark-only selector harness:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_benchmark.py`
- Stage A plan note:
  - `planning/working/no_wli_late_stage_selector_stageA_plan_2026-03-31.md`

What the harness now does:

- load frozen late-stage frontier fixtures
- summarize truth-gap dataset rows
- build a candidate feature table
- build frontier trial-material rows for future replay/key tests
- reproduce legacy score-led frontier winner selection
- run a small weighted reranker without using truth at selection time
- evaluate whether the reranker rescues the known bad `v45` choice

Meaningful proof:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_selector_benchmark.py tests/tools/test_no_wli_truth_diagnostics.py -q`
  - `8 passed`
- supporting guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_selector_benchmark.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_phasec_diagnostics_contract.py -q`
  - `15 passed`

Scientific consequence:

- Stage A scorer work can now proceed immediately on frozen real frontiers
- the current prototype proves the harness can beat the legacy `v45` loser on
  the real explored frontier
- this is still benchmark-only evidence; no live scorer semantics changed

### 2026-03-31 Stage A refinement and Stage B replay-capture prep

Implemented:

- second benchmark-only selector shape:
  - pairwise linear challenger reranker
- Stage A export/report path:
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stagea_report.py`
- fresh replay-capture run identity prepared:
  - `tune_v46_p9c3_seed411_novel_start_replay_capture_2job`
- dedicated run note:
  - `planning/working/no_wli_stageb_replay_capture_run_plan_2026-03-31.md`

What Stage A now produces:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/summary.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/v45_feature_rows.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/v45_trial_material_rows.json`

Current Stage A result:

- disagreement rows in dataset: `14`
- distinct disagreement patterns: `5`
- both benchmark-only prototypes currently rescue the legacy `v45` loser:
  - weighted candidate: `9002ee09917e5a0d`
  - pairwise candidate: `9002ee09917e5a0d`
- both lift truth from:
  - `0.039 -> 0.418`

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_selector_benchmark.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
- `36 passed`

Scientific consequence:

- Stage A is now beyond a single hand-picked fixture reproduction and has a
  repeatable report/export loop
- the next long run should not be a new science branch; it should be the fresh
  replay-capture `v46` compare so Stage B can validate replay-ready frontiers

### 2026-03-31 Stage A refinement: score-only ablation and feature-group rescue story

Implemented:

- weighted score-only ablation config
- weighted margin explanation against the legacy winner
- pairwise margin explanation against the legacy winner
- Stage A data-realism summary
- generated decision note:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/decision_note.md`

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_selector_benchmark.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_phasec_diagnostics_contract.py -q`
- `24 passed`

Current Stage A reading:

- `v45` is still clearly rescued by both benchmark-only rerankers
- score-only weighting still chooses the legacy loser:
  - `73eee2bf84b7c07f`
- both full rerankers choose:
  - `9002ee09917e5a0d`
- the dominant positive rescue group is currently:
  - `structural_features`
- current lexical feature group remains inactive in this Stage A pass
- broader evidence remains thin:
  - `14` disagreement rows
  - `5` distinct patterns
  - dominant pattern count `10`
  - dominant pattern fraction about `0.714`

Scientific consequence:

- the current evidence supports the claim that `v45` is not being rescued by
  score-only features
- it also supports keeping Stage A narrow until `v46` provides a replay-ready
  frontier, because current broader lift is still too pattern-concentrated for
  stronger claims

### 2026-03-31 Stage A operating rule locked while `v46` runs

New planning reference:

- `planning/working/no_wli_stagea_decision_checklist_2026-03-31.md`

Locked guidance:

- treat late-stage scorer work as a small ranking research programme
- keep Stage A benchmark-only
- treat `v45` as the must-pass adversarial fixture
- treat the disagreement dataset as a sanity check, not a training corpus
- evaluate both row-level and pattern-level lift
- do not move toward live integration until `v46` yields a replay-ready frontier
  and Stage A shows believable lift beyond one row

Live status at the time this checklist was recorded:

- `v46` replay-capture compare is running
- state file still shows:
  - `completed_jobs = 0`
  - `remaining_jobs = 2`
- event log shows job 1 active:
  - `stage3_phaseb_width_probe_p9`
- runtime preflight is still clean and there are no job-error rows yet

### 2026-03-31 Stage A refinement: dominant repeated disagreement pattern audit

Implemented:

- disagreement frontier row audit against real saved artifact frontiers
- disagreement frontier pattern audit collapsed by repeated winner/challenger
  pattern
- Stage A report export now persists:
  - `disagreement_frontier_row_audit.json`
  - `disagreement_frontier_pattern_audit.json`
- Stage A tests now cover the new row/pattern audit path

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_selector_benchmark.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_phasec_diagnostics_contract.py -q`
- `26 passed`

Refreshed export:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stagea_report.py`

Current Stage A reading:

- the dominant repeated disagreement pattern remains:
  - winner `73eee2bf84b7c07f`
  - challenger `9002ee09917e5a0d`
  - winner source `stage3_best_phaseB`
  - challenger source `phaseA_selected`
- dominant repeated pattern count is still:
  - `10`
- both benchmark-only rerankers rescue all `10` rows in that dominant repeated
  pattern family
- the dominant positive rescue group for both rerankers across that repeated
  pattern family is:
  - `structural_features`
- score-only weighting still stays on the legacy loser for those cases
- one minority disagreement pattern remains unrecovered and is currently read as
  score-led:
  - challenger `e45c25ba171877fd`
  - dominant group `score_features`

Scientific consequence:

- Stage A is now stronger than a single adversarial-fixture story
- the same structural / novelty rescue explanation recurs across the dominant
  repeated disagreement family in the current audited rows
- broader evidence is still too thin for strong generalization because the
  disagreement dataset remains small and heavily concentrated in that same
  family
- therefore the current operating rule remains correct:
  - keep Stage A small and benchmark-only
  - wait for `v46` before semantic/replay-heavy scorer work

### 2026-03-31 Stage A refinement: rescued-vs-unrecovered challenger contrast

Implemented:

- representative rescued-vs-unrecovered challenger contrast export:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/rescued_vs_unrecovered_contrast.json`
- Stage A report now includes a plain-language contrast section showing why the
  current simple reranker rescues the recurring `9002...` case but not the
  minority `e45...` case

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_selector_benchmark.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_phasec_diagnostics_contract.py -q`
- `28 passed`

Refreshed export:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stagea_report.py`

Plain-language reading:

- rescued case:
  - challenger `9002ee09917e5a0d`
  - score is slightly worse than the current winner:
    - `0.1728` vs `0.1910`
  - truth is much better:
    - `0.418` vs `0.039`
  - it is marked as an eligible novel challenger
  - it has a strong novelty distance to anchor:
    - `164`
  - source rank is relatively early:
    - `2`
  - result:
    - structural / novelty bonuses outweigh the small score deficit

- unrecovered case:
  - challenger `e45c25ba171877fd`
  - score is much worse than the current winner:
    - `0.1668` vs `0.2032`
  - truth is still much better:
    - `0.417` vs `0.046`
  - it is not marked as an eligible novel challenger
  - it has no recorded novelty distance to anchor
  - source rank is much later:
    - `8`
  - result:
    - both score and structural groups stay negative, so the current simple
      reranker keeps the legacy winner

Scientific consequence:

- current Stage A evidence is now clearer in plain language:
  - the simple reranker can rescue truth-strong challengers when they are both
    close enough on score and clearly novel
  - it does not yet rescue truth-strong challengers that are both further
    behind on score and lack novelty support in the current feature set
- that points the next small Stage A question toward:
  - which live-available non-truth features could make `e45...`-like
    under-valued challengers visible without overfitting `v45`

### 2026-03-31 Stage A refinement: unrecovered-case feature audit and small ablation sweep

Implemented:

- unrecovered-case live-feature audit export:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/unrecovered_case_feature_audit.json`
- small weighted ablation sweep export:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/weighted_ablation_sweep.json`
- Stage A decision note now records:
  - present-and-used vs present-but-unused vs absent-today feature counts
  - score-only vs novelty vs lexical ablation counts

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_selector_benchmark.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_phasec_diagnostics_contract.py -q`
- `31 passed`

Refreshed export:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stagea_report.py`

Current Stage A reading:

- rescued class:
  - `9002...`
  - current simple reranker can save this class
  - it is close enough on score and carries novelty support
- unrecovered class:
  - `e45...`
  - current simple reranker still cannot save this class
  - it is further behind on score and has no current novelty support
- feature-availability audit now shows:
  - rescued case:
    - present+used `7`
    - present-but-unused `8`
    - absent-today `6`
  - unrecovered case:
    - present+used `6`
    - present-but-unused `8`
    - absent-today `7`
- weighted ablations now show:
  - score-only:
    - rescued rows/patterns `0 / 0`
  - score+novelty:
    - rescued rows/patterns `13 / 4`
  - score+lexical:
    - rescued rows/patterns `0 / 0`
  - score+novelty+lexical:
    - rescued rows/patterns `13 / 4`

Scientific consequence:

- current Stage A evidence now says more precisely:
  - novelty/structure is the live lever that rescues the dominant repeated
    disagreement family
  - lexical fields are not currently the lever on these frozen frontiers
  - unrecovered `e45...`-like cases are the next important target because they
    remain invisible to both score-only and the current novelty-based rescue
- therefore the next disciplined Stage A question is:
  - which present-but-unused live-visible fields, if any, can help the
    unrecovered class before `v46` semantic/plaintext capture is available

### 2026-03-31 Stage A refinement: one-at-a-time numeric live-field ablation

Implemented:

- one-at-a-time numeric live-field sweep on top of the current
  `score + novelty` baseline:
  - `+ score_gap_to_winner`
  - `+ score_gap_to_anchor`
  - `+ init_score`
  - `+ init_search_score`
- export:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/numeric_field_ablation_sweep.json`

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_selector_benchmark.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_phasec_diagnostics_contract.py -q`
- `33 passed`

Refreshed export:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stagea_report.py`

Result:

- baseline `score + novelty`:
  - rescued rows/patterns `13 / 4`
  - unrecovered-class rescue `0`
- `+ score_gap_to_winner`:
  - rescued rows/patterns `13 / 4`
  - unrecovered-class rescue `0`
- `+ score_gap_to_anchor`:
  - rescued rows/patterns `13 / 4`
  - unrecovered-class rescue `0`
- `+ init_score`:
  - rescued rows/patterns `13 / 4`
  - unrecovered-class rescue `0`
- `+ init_search_score`:
  - rescued rows/patterns `13 / 4`
  - unrecovered-class rescue `0`

Scientific consequence:

- the present-but-unused numeric live fields tested here do not currently add
  lift beyond the `score + novelty` baseline
- they do not rescue the unrecovered `e45...` class
- so the current live-visible numeric field set now looks close to exhausted for
  this Stage A frontier family
- that strengthens the current decision boundary:
  - either a different already-present non-numeric live feature is needed
  - or the next real lift likely waits for richer replay-ready
    semantic/plaintext capture from `v46`

### 2026-03-31 Stage A refinement: one last safe categorical-field pass and robustness sweep

Implemented:

- one last safe source-only categorical-field pass:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/categorical_field_ablation_sweep.json`
- weighted robustness sweep around the current `score + novelty` baseline:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/weighted_robustness_sweep.json`
- Stage B first replay-ready frontier checklist:
  - `planning/working/no_wli_stageb_first_replay_ready_frontier_checklist_2026-03-31.md`

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_selector_benchmark.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_phasec_diagnostics_contract.py -q`
- `36 passed`

Refreshed export:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stagea_report.py`

Categorical-field result:

- baseline `score + novelty`:
  - rescued rows/patterns `13 / 14`
  - unrecovered-class rescue `0`
- `+ phaseB_topk` source penalty:
  - rescued rows/patterns `14 / 14`
  - unrecovered-class rescue `1`
- `+ stage3_best_phaseB` source penalty:
  - rescued rows/patterns `13 / 14`
  - unrecovered-class rescue `0`
- `+ combined safe source penalties`:
  - rescued rows/patterns `14 / 14`
  - unrecovered-class rescue `1`

Important nuance:

- the safe source-penalty pass does improve the last unrecovered pattern
- but it does **not** select the oracle-best `e45...`
- instead it selects:
  - `7391f8d462115a5b`
  - with truth `0.058`
  - over legacy `73eee...` truth `0.046`
- so this is a real but modest rescue, not a full oracle-like correction

Robustness result:

- total perturbation configs checked:
  - `81`
- dominant repeated `9002...` family rescued in all configs:
  - `1`
- unrecovered `e45...` class rescued in any config:
  - `0`

Scientific consequence:

- the current `score + novelty` rescue story is not knife-edge:
  - the dominant repeated `9002...` family is stable under small weight changes
- the unrecovered `e45...` class does not become recoverable under small
  perturbations of the current baseline
- the one last safe source-only pass does add benchmark lift, but in a cautious
  way:
  - it improves the last unrecovered pattern only to a modestly better
    challenger, not to the oracle-best one
- therefore the pre-`v46` baseline should stay frozen as:
  - `score + novelty`
- and the source-penalty variant should be carried forward only as an optional
  candidate for Stage B replay comparison, not as the locked new baseline

### 2026-03-31 `v46` replay-capture compare finished cleanly and is scorer-ready

Matrix result:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v46_p9c3_seed411_novel_start_replay_capture_2job.json`
  shows:
  - `completed_jobs = 2`
  - `remaining_jobs = 0`
  - `stopped_early = 0`
  - `last_error = null`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v46_p9c3_seed411_novel_start_replay_capture_2job.jsonl`
  contains only:
  - job 1 started/completed
  - job 2 started/completed
  - no `job_error`

Run directories:

- control:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T161234912270Z__bench_solve_pipeline_no_wli__55b7159`
- candidate:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T195317037506Z__bench_solve_pipeline_no_wli__37689eb`

Replay/scorer readiness:

- both runs contain `6` late-frontier rows in
  `stage3_diagnostics.phaseC_start_summaries`
- both runs also wrote run-level `phasec_start_checkpoints.jsonl`
- all `6 / 6` frontier rows in both runs carry complete:
  - `init_key_idx`
  - `init_plaintext_idx`
  - `final_key_idx`
  - `final_plaintext_idx`
- row lengths are the expected:
  - key idx length `264`
  - plaintext idx length `1000`

Important scorer facts confirmed in both runs:

- score-selected winner:
  - `73eee2bf84b7c07f`
  - `final_score = 0.19101667350788198`
  - `final_match = 0.039`
- oracle-best explored challenger:
  - `9002ee09917e5a0d`
  - `final_score = 0.17284542866740327`
  - `final_match = 0.418`

Artifact nuance:

- the replay-complete frontier is available in both places:
  - `stage3_diagnostics.phaseC_start_summaries`
  - run-level `phasec_start_checkpoints.jsonl`
- `stage3_diagnostics.phaseC_start_policy` is present and correct:
  - control: `source_order`
  - candidate: `novel_challenger_v1`
- the new shared frontier loader still matters because it keeps late-frontier
  export/replay/truth-gap consumers robust to either storage shape

Scientific consequence:

- `v46` is the first clean post-hardening replay-capture compare that is ready
  for Stage B replay validation
- Stage B can now use the normalized frontier export path directly

### 2026-03-31 Stage B first replay-ready frontier export and selector comparison

Implemented:

- shared frontier-row loader:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_frontier_rows.py`
- replay/export consumers hardened to use the shared loader:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_frontier_fixture.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/replay_phasec_rescue_sweep.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_gap_dataset.py`
- fresh Stage B export scripts:
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_stageb_replay_ready_frontiers.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stageb_report.py`
- Stage B comparison helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_stageb.py`

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_rescue_replay.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_late_stage_selector_stageb.py tests/tools/test_no_wli_late_stage_selector_benchmark.py -q`
- `58 passed`

Exported outputs:

- replay-ready frontier fixtures:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v46_seed411_control_replay_frontier.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v46_seed411_candidate_replay_frontier.json`
- first Stage B comparison bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/summary.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/summary.md`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/selected_trial_material_rows.json`

Comparison result:

- both replay-ready `v46` frontiers are complete:
  - control `frontier_key_material_complete = 1`
  - candidate `frontier_key_material_complete = 1`
- both control and candidate selected-candidate bundles are replay-ready:
  - `replay_ready_selected_candidates = 1`
- legacy still selects:
  - `73eee2bf84b7c07f`
  - truth `0.039`
- frozen Stage A baseline `score + novelty` selects:
  - `9002ee09917e5a0d`
  - truth `0.418`
- optional source-penalty variant also selects:
  - `9002ee09917e5a0d`
  - truth `0.418`

Scientific consequence:

- the replay-ready `v46` frontier confirms the same late-stage selection
  failure on fully captured material
- the frozen `score + novelty` baseline already matches the oracle-best
  explored challenger on both replay-ready runs
- the optional source-penalty variant adds no extra lift on this frontier
- `selected_trial_material_rows.json` is now the direct handoff artifact for the
  first true replay / continuation comparison

### 2026-03-31 Stage B first direct continuation result from replay-ready `v46`

Implemented:

- direct continuation helper on selected replay rows:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_stageb_continuation.py`
- export/report entrypoint:
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stageb_continuation_report.py`
- selected-row resume support:
  - `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_late_stage_frontier_fixture.py tests/tools/test_no_wli_phasec_rescue_replay.py tests/tools/test_no_wli_phasec_truth_gap_dataset.py tests/tools/test_no_wli_late_stage_selector_stageb.py tests/tools/test_no_wli_late_stage_selector_stageb_continuation.py tests/tools/test_no_wli_late_stage_selector_benchmark.py -q`
- `61 passed`

Generated continuation bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46_continuation/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46_continuation/summary.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46_continuation/continuation_results.json`

Result on both replay-ready `v46` runs:

- legacy:
  - selected `73eee2bf84b7c07f`
  - selected truth `0.039`
  - Stage 3.5 selected `0`
  - accept reason `search_score_drop_guard_failed`
  - best continued truth `0.038`
- `score + novelty`:
  - selected `9002ee09917e5a0d`
  - selected truth `0.418`
  - Stage 3.5 selected `1`
  - accept reason `accepted`
  - best continued candidate `d9430723f54e973e`
  - best continued truth `0.496`
  - truth gain vs selected challenger `+0.078`
- source-penalty variant:
  - selected the same challenger as `score + novelty`
  - produced the same `0.496` continuation result

Scientific consequence:

- this is the first direct replay-ready evidence that late-stage selector choice
  is a real marginal lever on this `411` frontier
- the result is no longer only:
  - better frozen ranking
- it is now:
  - better selected challenger
  - accepted real Stage 3.5 continuation
  - materially better downstream truth result
- important nuance:
  - the best continued row is still labeled `final_best` / `stage3_best_phaseB`
    / `anchor`
  - so the current positive should be read as:
    - the better challenger choice admits a better downstream continuation path
    - not yet as proof that the exact challenger row stays champion unchanged

Path-hygiene follow-up:

- `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_frontier_fixture.py`
  now emits repo-relative:
  - `source_artifact_path`
  - `phasec_checkpoint_path`
- Stage B selected-row handoff artifacts are now repo-relative by default

### 2026-03-31 next live scorer experiment locked to the Stage 3.5 baseline-selector boundary

The next live scorer-facing experiment is now explicitly narrowed to one
boundary:

- which already-explored Phase-C row becomes the Stage 3.5 baseline

Maintained mechanism from the locked evidence:

- `v45`:
  - frozen frontier ranking failure
- `v46`:
  - replay-ready continuation win
  - legacy-selected row fails Stage 3.5 admission
  - `score + novelty` selected row is admitted
  - admitted path reaches materially better downstream truth

So the next live question is:

- does changing only the Stage 3.5 baseline row from `legacy` to
  `score_plus_novelty` improve live continuation on the same `411`-style case?

Locked experiment rules:

- baseline:
  - `legacy`
- candidate:
  - `score_plus_novelty`
- keep fixed:
  - upstream search
  - Phase-B width
  - Phase-C start policy
  - Stage 3.5 search semantics
- do not mix in:
  - new width probes
  - new balancing changes
  - new semantic feature work

Execution order:

1. implement the explicit live Stage 3.5 baseline-selector hook
2. persist the baseline-selection reporting fields in `stage3_diagnostics`
3. run one short canary pair
4. only if the canary is clean, switch to the overnight 2-job compare

Reference plan:

- `planning/working/no_wli_stage35_baseline_selector_live_compare_plan_2026-03-31.md`

Implementation/proof status:

- live-safe selector hook implemented for:
  - `legacy`
  - `score_plus_novelty`
- Stage 3.5 baseline-selection reporting now persists in `stage3_diagnostics`
- fixture-matrix compare prepared in two modes:
  - canary
  - overnight
- current active mode:
  - canary
- current active canary pair:
  - `stage35_baseline_legacy_canary_p9`
  - `stage35_baseline_score_plus_novelty_canary_p9`
- prepared overnight pair:
  - `stage35_baseline_legacy_live_p9`
  - `stage35_baseline_score_plus_novelty_live_p9`

Meaningful proof:

- `83 passed`

Canary follow-up:

- the first live canary launch failed before science execution on:
  - `TypeError: emit_setup_logging() got an unexpected keyword argument 'stage35_baseline_selector'`
- this confirms the canary was worthwhile:
  - it caught a real omitted live-path contract before the overnight compare

Fix:

- `tools/benchmarks/periodic_sub_trans/no_wli/setup_logging.py`
  now accepts and prints `stage35_baseline_selector`
- `tests/tools/test_no_wli_setup_logging.py`
  now guards that signature explicitly

Updated proof:

- `84 passed`

Operational follow-up:

- the repaired canary rerun is still in flight and has already crossed the
  Phase-C frontier boundary
- the overnight compare is pre-armed on disk and a detached watcher will launch
  it automatically if the canary completes cleanly
- watcher log:
  - `planning/working/no_wli_stage35_canary_watch_2026-03-31.log`

### 2026-04-01 `v47` canary reclassified: invalid silent Stage 3.5 burn

The repaired `v47` Stage 3.5 baseline-selector canary is not a valid pass and
not a science result.

Evidence:

- it finished Phase C cleanly and printed the full `stage3-phaseC` summary
- after that point the active run dir stopped writing artifacts
- the Python process continued consuming CPU for hours

Interpretation:

- the stall boundary is after Phase C
- this isolates the problem to Stage 3.5 live followup / immediate
  post-Phase-C handling
- the original canary preset was too heavy and too silent to be useful

Response:

- add Stage 3.5 start/heartbeat/finish logging
- reduce canary-only late budgets and Stage 3.5 search budget
- reset compare mode back to `canary`
- rerun on a fresh control-file id:
  - `tune_v49_p9c3_seed411_stage35_baseline_selector_canary_reduced_2job`

Meaningful proof after the reset/hardening slice:

- `76 passed`

Operational follow-up:

- `v49` job 1 completed cleanly and wrote final artifacts
- Stage 3.5 persisted valid evidence on the finished legacy canary side:
  - `stage35_ran = 1`
  - `stage35_proof_valid = 1`
  - `stage35_accept_reason = search_score_drop_guard_failed`
- job 2 is now in flight

Detached handoff armed:

- watcher script:
  - `planning/working/no_wli_stage35_v49_watch_and_launch_2026-04-01.ps1`
- watcher log:
  - `planning/working/no_wli_stage35_v49_watch_2026-04-01.log`

Handoff rule:

- if `v49` completes cleanly, the watcher switches the config to `overnight`
  and launches the real `v48` compare automatically
- if `v49` fails, the watcher does not launch the overnight run

### 2026-04-01 `v49` reduced canary result: valid plumbing pass, weak science signal

`v49` completed cleanly as a 2-job canary:

- experiment id:
  - `tune_v49_p9c3_seed411_stage35_baseline_selector_canary_reduced_2job`
- completed jobs:
  - `2 / 2`
- stopped early:
  - `0`
- last error:
  - none

What it established:

- the repaired Stage 3.5 boundary now completes cleanly on both selector modes
- the candidate lane really does select a different Stage 3.5 baseline row
- the Stage 3.5 diagnostics/reporting fields persist correctly

Legacy canary outcome:

- `stage35_baseline_selector = legacy`
- `stage35_baseline_differs_from_phasec_score_winner = 0`
- `stage35_accept_passed = 0`
- `stage35_accept_reason = search_score_drop_guard_failed`
- `stage35_best_match = 0.059`
- top-level `best_match_ratio = 0.060`

`score_plus_novelty` canary outcome:

- `stage35_baseline_selector = score_plus_novelty`
- `stage35_baseline_differs_from_phasec_score_winner = 1`
- `stage35_accept_passed = 0`
- `stage35_accept_reason = search_score_drop_guard_failed`
- `stage35_best_match = 0.061`
- `stage35_truth_gain_vs_phasec_score_winner = +0.001`
- top-level `best_match_ratio = 0.060`

Reading:

- `v49` is a valid canary pass
- it proves the live selector boundary and reporting path are working
- it does not by itself show a meaningful solve lift
- that is consistent with the canary being a reduced-budget gate, not the real
  science compare

Operational follow-through:

- the detached watcher observed the clean `v49` pass
- it switched the config to `overnight`
- and it launched:
  - `tune_v48_p9c3_seed411_stage35_baseline_selector_live_compare_2job`

### 2026-04-02 `v48` overnight status: legacy long lane completed, compare incomplete

`v48` did not finish as a 2-job live compare.

State:

- experiment id:
  - `tune_v48_p9c3_seed411_stage35_baseline_selector_live_compare_2job`
- completed jobs:
  - `1 / 2`
- remaining jobs:
  - `1`
- stopped early:
  - `1`
- reason:
  - fixture-matrix wallclock cap fired after the legacy lane

Completed long lane:

- preset:
  - `stage35_baseline_legacy_live_p9`

Persisted legacy result:

- `stage35_baseline_selector = legacy`
- `stage35_baseline_candidate_hash = 73eee2bf84b7c07f`
- `stage35_accept_passed = 0`
- `stage35_accept_reason = search_score_drop_guard_failed`
- `stage35_best_match = 0.038`
- top-level `best_stage = stage2_search`
- top-level `best_match_ratio = 0.041`

Reading:

- the live Stage 3.5 boundary now completes and emits usable telemetry
- the legacy long lane confirms the expected failure mode
- but the actual live compare is still incomplete because the
  `score_plus_novelty` long lane never started

Maintained next step:

- do not spend another night rerunning the same 2-job shape under the same cap
- run the missing full-budget `stage35_baseline_score_plus_novelty_live_p9`
  lane on its own and compare it against the completed legacy long lane

### 2026-04-02 Stage 3.5 replay hotspot benchmark: first reduced profile run is working and already isolates the runtime split

Question:

- can Stage 3.5 now be benchmarked in isolation on saved replay material, and
  if so, where is the runtime going?

Setup:

- harness:
  - `tools/benchmarks/periodic_sub_trans/no_wli/profile_stage35_replay_hotspots.py`
- selected replay rows:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/selected_trial_material_rows.json`
- output bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260402T151731Z__profile_stage35_replay_hotspots_v1/summary.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260402T151731Z__profile_stage35_replay_hotspots_v1/case_timings.csv`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260402T151731Z__profile_stage35_replay_hotspots_v1/profiles/candidate__score_plus_novelty/cprofile_top_cumulative.txt`

Reduced sample config:

- `rounds = 1`
- `seed_keep = 2`
- `beam_width = 2`
- `archive_keep = 8`
- `mini_search_steps = 1`
- `mini_search_beam_width = 2`
- `mini_search_final_keep = 1`

Outcome:

- yes, isolated Stage 3.5 replay benchmarking is now working
- yes, the replayed `score_plus_novelty` rows are already materially slower than
  legacy even under the reduced sample config
- and the reduced replay still preserves the admission split:
  - legacy rows fail `search_score_drop_guard_failed`
  - `score_plus_novelty` rows are `accepted`

Cross-checked evidence:

- aggregate timing split:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260402T151731Z__profile_stage35_replay_hotspots_v1/summary.json`
  - fields:
    - `accepted_case_count = 2`
    - `fastest_case_id = "control__legacy"`
    - `fastest_wallclock_seconds = 6.095...`
    - `slowest_case_id = "control__score_plus_novelty"`
    - `slowest_wallclock_seconds = 16.807...`
- per-case rows:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260402T151731Z__profile_stage35_replay_hotspots_v1/case_timings.csv`
  - legacy rows:
    - wallclock `6.095s` to `8.341s`
    - `2479` evals
    - `accept_reason = search_score_drop_guard_failed`
  - `score_plus_novelty` rows:
    - wallclock `16.324s` to `16.807s`
    - `8704` evals
    - `accept_reason = accepted`
- first hotspot profile:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260402T151731Z__profile_stage35_replay_hotspots_v1/profiles/candidate__score_plus_novelty/cprofile_top_cumulative.txt`
  - top cumulative stack includes:
    - `run_slice_local_mini_search`
    - `_score_key_rows`
    - `_score_rows_for_keys`
    - `score_plaintexts_chunked`
    - `torch_rune_scorer.batch_score`
    - `_lookup_logp_linear_probe`
    - `stable_key_hash`
    - selector ranking / sorting helpers

Conclusion:

- the repo now has a practical Stage 3.5-only benchmark loop
- the current bottleneck is not just "Stage 3.5 is slow" in the abstract
- it is specifically:
  - mini-search driven scorer work
  - plus a smaller but real Python-side archive/ranking overhead

Follow-up added immediately after this run:

- Stage 3.5 now emits solver-native telemetry buckets alongside replay/live
  outputs, including:
  - row scoring wallclock
  - decrypt time
  - scorer batch-score time
  - candidate-hash time
  - mini-search generation / scoring / ranking time
  - proposal materialization time
  - archive update / ranking time
  - average batch size
  - average proposals / rows scored / rows kept per mini
- the replay profile harness now surfaces those key timing buckets directly in:
  - `case_timings.csv`

Maintained next step:

- before another long live candidate run:
  - add periodic Stage 3.5 partial dumps
  - add explicit capped/unfinished persistence
  - use this replay profile harness to target speed work first

### 2026-04-02 Stage 3.5 replay config sweep: `beam_width_1` is the first real boundedness win

Question:

- when the stable replay harness is used as the main loop, which single Stage
  3.5 knob cuts cost the most while preserving the important acceptance split?

Setup:

- sweep harness:
  - `tools/benchmarks/periodic_sub_trans/no_wli/sweep_stage35_replay_configs.py`
- stable saved rows:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/selected_trial_material_rows.json`
- output bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_sweep/20260402T154929Z__sweep_stage35_replay_configs_v1/summary.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_sweep/20260402T154929Z__sweep_stage35_replay_configs_v1/variant_summary.csv`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_sweep/20260402T154929Z__sweep_stage35_replay_configs_v1/case_rows.csv`

Sweep order:

- baseline
- lower `mini_search_top_symbols`
- lower `beam_width`
- lower `mini_search_final_keep`
- lower `archive_keep`

Outcome:

- `beam_width_1` is the first clearly useful boundedness config
- it preserves the acceptance split:
  - legacy replay rows still reject
  - `score_plus_novelty` replay rows still accept
- and it cuts candidate runtime and scorer work by about half

Cross-checked evidence:

- baseline row in:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_sweep/20260402T154929Z__sweep_stage35_replay_configs_v1/variant_summary.csv`
  - candidate fields:
    - `candidate_wallclock_seconds = 15.017...`
    - `candidate_proposals_generated = 8704`
    - `candidate_row_scoring_seconds = 12.304...`
    - `candidate_accept_reason = accepted`
    - `acceptance_split_preserved = 1`
- `beam_width_1` row in the same file:
  - candidate fields:
    - `candidate_wallclock_seconds = 8.152...`
    - `candidate_proposals_generated = 4352`
    - `candidate_row_scoring_seconds = 6.219...`
    - `candidate_accept_reason = accepted`
    - `acceptance_split_preserved = 1`
    - `candidate_runtime_vs_baseline_ratio = 0.5428...`
    - `candidate_proposals_vs_baseline_ratio = 0.5`
    - `candidate_row_scoring_vs_baseline_ratio = 0.5054...`
- legacy side of the same `beam_width_1` row:
  - `legacy_accept_reason = search_score_drop_guard_failed`
  - `legacy_accept_passed = 0`

Less useful variants from the same file:

- `top_symbols_8`:
  - `candidate_runtime_vs_baseline_ratio = 1.6376...`
- `top_symbols_6`:
  - `candidate_runtime_vs_baseline_ratio = 1.4421...`
- `beam_width_2`:
  - `candidate_runtime_vs_baseline_ratio = 1.0331...`
- `final_keep_1`:
  - `candidate_runtime_vs_baseline_ratio = 0.9817...`
- `archive_keep_8`:
  - `candidate_runtime_vs_baseline_ratio = 0.9938...`

Conclusion:

- reducing Stage 3.5 beam width is the first meaningful speed lever
- reducing top-symbol branching first is counterproductive on this replay case
- `archive_keep` is not the first runtime lever, matching the earlier telemetry

Maintained next step:

- treat `beam_width_1` as the first bounded replay candidate baseline
- next add:
  - periodic partial Stage 3.5 dumps
  - explicit capped/unfinished persistence
- then rerun one fresh live candidate confirmation job only after those
  boundedness/observability pieces are in place

### 2026-04-02 Stage 3.5 persistence slice: partial dumps and capped outcomes are now live-path features

Question:

- can Stage 3.5 now persist enough partial state and explicit status to make
  long late-stage runs inspectable and auditable without pretending unfinished
  work is complete?

Implemented:

- Stage 3.5 solver and live followup:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage35_substitution_solver.py`
- live Stage 3.5 flow propagation:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- diagnostics persistence:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
- Stage 3.5 fixture-matrix cfg normalization:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`

What changed:

- solver outcomes now persist explicit status fields:
  - `outcome_status`
  - `outcome_reason`
  - `completed`
  - `capped`
- live Stage 3.5 followup now writes repo-relative partial artifacts when run
  under the live path:
  - `stage35_partial_state.json`
  - `stage35_progress.jsonl`
- persisted Stage 3.5 diagnostics now also carry:
  - partial/progress filenames
  - progress-event count
  - partial-dump write count
- fixture-matrix Stage 3.5 cfg normalization now preserves
  `max_runtime_seconds` as a float instead of truncating it

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_stage35_replay_profile.py tests/tools/test_no_wli_stage35_substitution_solver.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
- result:
  - `55 passed`

New contract coverage added:

- Stage 3.5 solver progress now proves:
  - `round_archive_snapshot` events exist
  - capped eval outcomes persist as `capped_evals`
- Stage 3.5 live followup now proves:
  - partial-state file is written
  - progress JSONL is written
  - final persisted event is `followup_finish`
- fixture-matrix apply path now proves:
  - `max_runtime_seconds` survives normalization as a float

Scientific consequence:

- the Stage 3.5 observability gap is now materially smaller
- boundedness work no longer depends only on console readout
- the next replay-based Stage 3.5 optimization slice can use:
  - `beam_width_1` as the active bounded baseline
  - explicit partial dumps / capped outcomes as the persistent contract

Maintained next step:

- keep `beam_width_1` as the active replay boundedness baseline
- use the new partial-dump / capped-outcome contract inside the Stage 3.5-only
  replay loop
- only after the bounded Stage 3.5 config is locked, run one fresh live
  candidate confirmation job

### 2026-04-02 bounded replay baseline run: `beam_width_1` now has a real artifact-producing replay result

Question:

- does the promoted `beam_width_1` replay baseline still preserve the important
  accept/reject split when run as a real artifact-producing Stage 3.5 replay,
  not just as a row in the sweep table?

Run:

- harness:
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_stage35_bounded_replay_baseline.py`
- output bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T163527Z__stage35_bounded_replay_baseline_v1/summary.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T163527Z__stage35_bounded_replay_baseline_v1/case_summary.csv`

Bounded replay cfg:

- `seed_keep = 2`
- `beam_width = 1`
- `archive_keep = 12`
- `rounds = 1`
- `mini_search_steps = 1`
- `mini_search_beam_width = 2`
- `mini_search_top_symbols = 10`
- `mini_search_final_keep = 2`
- `mini_search_keep_all_rows = 0`
- `max_runtime_seconds = 30.0`
- `partial_dump_preview_rows = 3`

Outcome:

- yes
- all four replay cases completed cleanly without capping
- the important split was preserved on both fixtures:
  - legacy replay rows still failed `search_score_drop_guard_failed`
  - `score_plus_novelty` replay rows still ended `accepted`
- and the new Stage 3.5 partial/progress files were written on disk for each
  case

Cross-checked evidence:

- aggregate split status:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T163527Z__stage35_bounded_replay_baseline_v1/summary.json`
  - fields:
    - `case_count = 4`
    - `acceptance_split_preserved_all = 1`
    - both fixture rows in `fixture_splits` show:
      - legacy `accept_passed = 0`
      - candidate `accept_passed = 1`
      - legacy `completed = 1`
      - candidate `completed = 1`
      - legacy `capped = 0`
      - candidate `capped = 0`
- per-case bounded runtimes and artifact paths:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T163527Z__stage35_bounded_replay_baseline_v1/case_summary.csv`
  - rows show:
    - candidate legacy:
      - `runtime_seconds = 2.001...`
      - `accept_reason = search_score_drop_guard_failed`
      - `progress_events_written = 16`
      - `partial_dump_write_count = 4`
    - candidate `score_plus_novelty`:
      - `runtime_seconds = 6.328...`
      - `accept_reason = accepted`
      - `progress_events_written = 16`
      - `partial_dump_write_count = 4`
    - control legacy:
      - `runtime_seconds = 2.274...`
      - `accept_reason = search_score_drop_guard_failed`
    - control `score_plus_novelty`:
      - `runtime_seconds = 7.287...`
      - `accept_reason = accepted`
- example persisted partial state for the candidate accepted row:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T163527Z__stage35_bounded_replay_baseline_v1/cases/candidate__score_plus_novelty/stage35_partial_state.json`
  - fields:
    - `baseline_selector = "score_plus_novelty"`
    - `baseline_candidate_hash = "9002ee09917e5a0d"`
    - `accept_reason = "accepted"`
    - `outcome_status = "completed"`
    - `completed = 1`
    - `capped = 0`
- example persisted progress tail for the same row:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T163527Z__stage35_bounded_replay_baseline_v1/cases/candidate__score_plus_novelty/stage35_progress.jsonl`
  - tail rows include:
    - `round_archive_snapshot`
    - `finish`
    - `followup_finish`

Meaningful proof after the replay-wrapper promotion:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_stage35_bounded_replay_baseline.py tests/tools/test_no_wli_stage35_replay_profile.py tests/tools/test_no_wli_stage35_replay_sweep.py tests/tools/test_no_wli_stage35_substitution_solver.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
- result:
  - `60 passed`

Conclusion:

- `beam_width_1` is now the maintained Stage 3.5 replay baseline
- it is bounded enough to finish comfortably on the stable replay rows
- it preserves the key behavior split
- and it produces concrete per-case Stage 3.5 artifacts, not just summary CSVs

Maintained next step:

- keep `beam_width_1` fixed as the active replay baseline
- do only narrow replay timing/tuning around that baseline if needed
- then move to one fresh live 1-job candidate confirmation run, not a broader
  live compare

### 2026-04-02 bounded replay rerun stayed stable; bounded live candidate lane promoted to `v51`

Question:

- before paying for another live confirmation job, does the bounded
  `beam_width_1` replay baseline still preserve the split on a fresh rerun?

Run:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T171133Z__stage35_bounded_replay_baseline_v1/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T171133Z__stage35_bounded_replay_baseline_v1/case_summary.csv`

Outcome:

- yes
- the rerun preserved the same acceptance split:
  - legacy rows still failed `search_score_drop_guard_failed`
  - `score_plus_novelty` rows still ended `accepted`
- all `4 / 4` replay cases completed without capping

Cross-checked evidence:

- aggregate split:
  - `summary.json`
  - fields:
    - `acceptance_split_preserved_all = 1`
    - both fixture rows show:
      - legacy `completed = 1`
      - candidate `completed = 1`
      - legacy `capped = 0`
      - candidate `capped = 0`
- per-case runtimes:
  - `case_summary.csv`
  - rows show:
    - candidate legacy:
      - `runtime_seconds = 1.0306...`
      - `accept_reason = search_score_drop_guard_failed`
    - candidate `score_plus_novelty`:
      - `runtime_seconds = 3.0431...`
      - `accept_reason = accepted`
    - control legacy:
      - `runtime_seconds = 0.9766...`
      - `accept_reason = search_score_drop_guard_failed`
    - control `score_plus_novelty`:
      - `runtime_seconds = 4.0940...`
      - `accept_reason = accepted`

Conclusion:

- the bounded replay baseline is stable enough to promote into one fresh live
  candidate confirmation run

Promotion:

- the live matrix is now pointed at a fresh bounded 1-job candidate preset in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- preset:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- experiment id:
  - `tune_v51_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`

Bounded live Stage 3.5 cfg:

- `seed_keep = 2`
- `beam_width = 1`
- `archive_keep = 12`
- `rounds = 1`
- `mini_search_steps = 1`
- `mini_search_beam_width = 2`
- `mini_search_top_symbols = 10`
- `mini_search_final_keep = 2`
- `mini_search_keep_all_rows = 0`
- `max_runtime_seconds = 14400.0`

Maintained next step:

- launch the fresh bounded live 1-job candidate confirmation run
- then read only:
  - baseline row changed?
  - Stage 3.5 admission changed?
  - downstream continuation beat the locked `v48` legacy long lane?

### 2026-04-02 `v51` bounded live candidate confirmation: replay-proven mechanism transferred into the real job

Question:

- after promoting the bounded `beam_width_1` Stage 3.5 config into a fresh
  1-job live candidate lane, does the candidate row still differ, does Stage
  3.5 admission flip, and does downstream continuation beat the locked `v48`
  legacy lane?

Run:

- experiment id:
  - `tune_v51_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`
- run state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v51_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job.json`
- run events:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v51_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job.jsonl`
- run artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260402T171534470152Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed411.json`
- console log:
  - `planning/working/no_wli_stage35_v51_live_console_2026-04-02.log`

Outcome:

- yes on all three questions
- the candidate lane selected `9002ee09917e5a0d` instead of the Phase-C score
  winner `73eee2bf84b7c07f`
- Stage 3.5 accepted that baseline row
- the final run-level best improved to `0.487`, beating the locked `v48` legacy
  lane at `0.041`

Cross-checked completion evidence:

- `v51` state:
  - `completed_jobs = 1`
  - `remaining_jobs = 0`
  - `stopped_early = 0`
- `v51` events:
  - `job_started`
  - `job_completed`
  - elapsed seconds:
    - `11948.520...`

Cross-checked mechanism evidence from the `v51` final artifact:

- baseline row differed:
  - `stage35_baseline_selector = "score_plus_novelty"`
  - `stage35_baseline_candidate_hash = "9002ee09917e5a0d"`
  - `stage35_baseline_candidate_source = "phaseA_selected"`
  - `stage35_baseline_candidate_lane = "challenger"`
  - `stage35_baseline_differs_from_phasec_score_winner = 1`
  - `stage35_phasec_score_winner_candidate_hash = "73eee2bf84b7c07f"`
  - `stage35_baseline_candidate_final_match = 0.418`
  - `stage35_phasec_score_winner_candidate_final_match = 0.039`
- Stage 3.5 admission flipped:
  - `stage35_accept_passed = 1`
  - `stage35_accept_reason = "accepted"`
  - `stage35_outcome_status = "completed"`
  - `stage35_completed = 1`
  - `stage35_capped = 0`
- downstream continuation won:
  - `best_stage = "stage35_substitution_only"`
  - `best_match_ratio = 0.487`
  - `stage35_best_candidate_hash = "1fdc6d7d88e80a2b"`
  - `stage35_best_match = 0.487`
  - `stage35_best_score = 0.18130345628397204`
  - `stage35_truth_gain_vs_selected_row = 0.069`
  - `stage35_truth_gain_vs_phasec_score_winner = 0.448`

Comparison against the locked `v48` legacy long lane:

- `v48` legacy artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260401T171546625377Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed411.json`
- persisted `v48` legacy fields:
  - `stage35_baseline_selector = "legacy"`
  - `stage35_baseline_candidate_hash = "73eee2bf84b7c07f"`
  - `stage35_baseline_candidate_source = "stage3_best_phaseB"`
  - `stage35_baseline_candidate_lane = "anchor"`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - `stage35_accept_passed = 0`
  - `stage35_accept_reason = "search_score_drop_guard_failed"`
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage35_best_match = 0.038`
  - `stage35_runtime_seconds = 27080.953...`
  - `stage35_rounds_completed = 3`
  - `stage35_evals = 30726`

Boundedness / observability evidence from `v51`:

- Stage 3.5 runtime:
  - `stage35_runtime_seconds = 3286.700...`
- Stage 3.5 work:
  - `stage35_rounds_completed = 1`
  - `stage35_evals = 4352`
- partial/progress files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260402T171534470152Z__bench_solve_pipeline_no_wli__048e35c/stage35_partial_state.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260402T171534470152Z__bench_solve_pipeline_no_wli__048e35c/stage35_progress.jsonl`
- persisted counters:
  - `stage35_partial_state_name = "stage35_partial_state.json"`
  - `stage35_progress_jsonl_name = "stage35_progress.jsonl"`
  - `stage35_progress_event_count = 16`
  - `stage35_partial_dump_write_count = 4`

Interpretation:

- this is the first clean full live confirmation that the late selector plus a
  bounded Stage 3.5 continuation is a real solve-facing lever on this
  `seed411` case
- the mechanism is now live-confirmed:
  - better baseline row selection
  - Stage 3.5 admission
  - better downstream continuation
- the best final row is not the original `9002...` row itself:
  - `9002...` is the admitted start row
  - `1fdc6d7d88e80a2b` is the best continued row
  - this is consistent with the maintained "admission into a better
    continuation path" story

Caution:

- this is still one full live confirmation case, not a broad cross-fixture
  proof
- the bounded `v51` candidate lane is materially better than the locked
  legacy lane on this case, but not solved

Maintained next step:

- inspect the `v51` Stage 3.5 progress/partial dumps to identify where the
  one-round bounded path still spends ~55 minutes
- then decide whether to:
  - do one more replay-first speed pass around the bounded config
  - or prepare a guarded promotion / broader confirmation plan for this lane

### 2026-04-02 `v51` Stage 3.5 artifact inspection: one-round runtime is almost entirely row scoring

Question:

- where does the one-round bounded `v51` Stage 3.5 pass still spend ~55 minutes?

Artifacts:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260402T171534470152Z__bench_solve_pipeline_no_wli__048e35c/stage35_progress.jsonl`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260402T171534470152Z__bench_solve_pipeline_no_wli__048e35c/stage35_partial_state.json`

Outcome:

- the runtime is almost entirely in the slice-local row-scoring path
- archive update cost is negligible
- all `9` mini-searches were spawned from the same parent row

Cross-checked evidence:

- per-mini wallclock from `stage35_progress.jsonl`:
  - `9` serial mini-searches
  - all with `parent_candidate_hash = 82bc15ae884d34f6`
  - per-mini durations:
    - `417.389s`
    - `286.708s`
    - `317.315s`
    - `416.312s`
    - `348.828s`
    - `317.839s`
    - `416.248s`
    - `347.875s`
    - `416.462s`
  - mean mini-search duration:
    - `364.997s`
  - total mini-search span:
    - `3284.976s`
- final `finish` event in the same JSONL:
  - `telemetry_summary.row_scoring_seconds = 3286.330567400204`
  - `telemetry_summary.archive_update_seconds = 0.00017620017752051353`
  - `telemetry_summary.mini_search_count = 9`
- final partial state:
  - `baseline_candidate_hash = "9002ee09917e5a0d"`
  - `archive_preview_rows[0].candidate_hash = "1fdc6d7d88e80a2b"`
  - `archive_preview_rows[0].seed_source = "stage3_topk_phaseb"`
  - `archive_preview_rows[0].stage3_source = "phaseB_topk"`
  - `archive_preview_rows[0].target_slice = 2`

Interpretation:

- the bounded config already fixed the worst archive-width behavior
- the remaining speed problem is repeated scoring work inside
  `run_slice_local_mini_search`
- the next Stage 3.5 replay optimization pass should focus there first, not on
  archive update / ranking

Small persistence fix landed:

- `stage3_diagnostics` now includes `stage35_telemetry_summary`
- code surface:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- regression test:
  - `tests/tools/test_no_wli_truth_diagnostics.py`
- focused proof:
  - `41 passed`

Maintained next step:

- run one replay-first speed pass specifically on the row-scoring path under
  `run_slice_local_mini_search`

### 2026-04-02 replay duplicate-key audit: exact duplicate rescoring is not the current bottleneck

Question:

- are we wasting Stage 3.5 mini-search time by repeatedly scoring duplicate keys
  or keys that only become duplicate after frozen-tail normalization?

Changes:

- `tools/benchmarks/periodic_sub_trans/no_wli/phasec_rescue_search.py`
  - counts exact duplicate proposals skipped by the pre-scoring `seen` set
- `tools/benchmarks/periodic_sub_trans/no_wli/stage35_substitution_solver.py`
  - dedupes normalized keys inside the scoring callback before calling the
    scorer
  - preserves one returned row per original proposal, so mini-search metadata
    alignment stays intact
  - records normalized-input / unique-key / duplicate-key telemetry
- `tools/benchmarks/periodic_sub_trans/no_wli/profile_stage35_replay_hotspots.py`
  - surfaces the new duplicate counters in `case_timings.csv`

Validation:

- `37 passed`:
  - `tests/tools/test_no_wli_stage35_substitution_solver.py`
  - `tests/tools/test_no_wli_stage35_replay_profile.py`
  - `tests/tools/test_no_wli_artifact_resume.py`

Replay result:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260403T001129Z__profile_stage35_replay_hotspots_v1/case_timings.csv`
- all four replay cases had:
  - `telemetry_mini_search_duplicate_proposals_skipped = 0`
  - `telemetry_row_scoring_normalized_duplicate_keys_total = 0`
- acceptance split was unchanged:
  - legacy rows still rejected with `search_score_drop_guard_failed`
  - `score_plus_novelty` rows still accepted

Interpretation:

- duplicate rescoring is not why the candidate Stage 3.5 path is slower
- the heavier candidate path is slower because it generates and scores many
  more genuinely unique slice-local proposals
- the next replay-only speed pass should therefore look for generic ways to
  make scoring large batches of unique local proposals cheaper, not one-seed
  dedupe heuristics

### 2026-04-02 replay chunk-size sweep: larger scorer batches are a useful generic lever under `beam_width_1`

Question:

- given that duplicate rescoring is not the problem, can we make the unique
  proposal scoring path cheaper by using larger chunked batch sizes in the
  replay Stage 3.5 scorer/decrypt path?

Changes:

- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - added function-level `batch_eval_chunk_size` overrides for Stage 3.5
    replay entry points
- `tools/benchmarks/periodic_sub_trans/no_wli/profile_stage35_replay_hotspots.py`
  - chunk sweep now runs under the maintained bounded `beam_width_1` replay
    config
  - hardcoded batch chunk candidates: `256`, `512`, `1024`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_stage35_bounded_replay_baseline.py`
  - replay-only bounded baseline now uses
    `BATCH_EVAL_CHUNK_SIZE = 1024`

Validation:

- `18 passed`:
  - `tests/tools/test_no_wli_stage35_replay_profile.py`
  - `tests/tools/test_no_wli_artifact_resume.py`
- `39 passed`:
  - `tests/tools/test_no_wli_stage35_bounded_replay_baseline.py`
  - `tests/tools/test_no_wli_stage35_replay_profile.py`
  - `tests/tools/test_no_wli_artifact_resume.py`
  - `tests/tools/test_no_wli_stage35_substitution_solver.py`

Replay results:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260403T002414Z__profile_stage35_replay_hotspots_v1/case_timings.csv`
- candidate fixture, `score_plus_novelty`:
  - chunk `256` -> `8.438587199896574s`
  - chunk `512` -> `7.348186699906364s`
  - chunk `1024` -> `6.539424399845302s`
- control fixture, `score_plus_novelty`:
  - chunk `256` -> `7.665857300162315s`
  - chunk `512` -> `6.691823699977249s`
  - chunk `1024` -> `6.550577500136569s`
- accept/reject split remained unchanged for all chunk sizes:
  - legacy still rejected with `search_score_drop_guard_failed`
  - `score_plus_novelty` still accepted

Interpretation:

- under the current bounded Stage 3.5 replay shape, larger chunked scorer
  batches are a real generic speed improvement for the heavier accepted
  candidate path
- legacy rows are roughly neutral, and no duplicate-key shortcut is involved
- maintained replay baseline candidate is now:
  - `beam_width_1`
  - chunk size `1024`

Caution:

- do not promote this to a broad live default from replay alone
- one more replay sanity pass or a guarded live confirmation should happen
  before any wider claim

### 2026-04-02 frozen-ladder gate setup: fresh small live candidate ladder

Artifact availability check:

- there are replay-ready hard `p9/c3` Phase-C frontiers in saved outputs,
  including:
  - `seed211`
  - `seed411`
  - `seed511`
- but the sampled easy/medium final artifacts do not persist usable
  `stage3_diagnostics.phaseC_start_summaries`, so there are no replay-ready
  Phase-C rows for:
  - `fixture_fixture_001_p5_c1_l1000`
  - `fixture_fixture_001_p9_c1_l1000`

Conclusion:

- the next generality gate cannot be replay-only with the current artifact pool
- to test whether the bounded candidate lane is not just a one-seed win, the
  next step is a small **live** candidate ladder run on a compact frozen slice

Prepared config:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- active matrix mode:
  - `candidate_ladder_small`
- grid:
  - `p5/c1`
  - `p9/c1`
  - `p9/c3`
  - seeds `411` and `511`
- preset:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- experiment id:
  - `tune_v52_ladder_small_stage35_baseline_selector_candidate_live_bounded_6job`

What this should answer:

- does the bounded candidate lane keep the known `p9/c3 seed411` benefit?
- does it avoid harming easy/medium controls?
- does it behave sanely on one hard case outside the dominant `9002...` family?

Guard proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
- result:
  - `20 passed`

### 2026-04-02 `space_map_v1` data contract: canonical partial-state rows and pool summaries

Purpose:

- start mapping late-stage search space structure from saved artifacts
- make Phase C and Stage 3.5 rows comparable under one canonical schema
- keep this as a data/measurement layer only; do not change solver decisions

Changes:

- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - new shared serializer for:
    - canonical partial-state rows
    - canonical pool-summary rows
    - one combined late-stage payload builder
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - final artifacts now store:
    - `stage3_diagnostics.space_map_v1`
- `tests/tools/test_no_wli_partial_state_space_map.py`
  - guards the canonical mapper and key pool-summary counters

Initial coverage in `space_map_v1`:

- `phaseC_start` rows
- `stage35_seed` rows
- `stage35_archive` rows
- pool summaries for those same three boundaries

Current known limitations:

- Stage 2 promoted and Stage 3 init/prep pools are not yet represented in
  this canonical layer
- Phase C available-vs-selected pool rows are still incomplete because current
  artifacts mainly persist actual starts, not the full candidate pool
- family ids and anchor distances use current row fields when present, with a
  fallback to candidate-hash identity; richer family descriptors still need a
  later pass
- `run_id` is left blank unless the caller state provides one

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_stage35_substitution_solver.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
- result:
  - `43 passed`

### 2026-04-02 one-job p5 lane + `space_map_v1` audit script

Purpose:

- continue testing on easier `p5` cases, but one run at a time only
- harden reviewer-facing inspection for the new canonical space-map payload

Config:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- active matrix mode:
  - `candidate_single_p5`
- resulting one-job grid:
  - `fixture_001`
  - `p5/c1`
  - `seed411`
- preset:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- experiment id:
  - `tune_v53_p5c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`

Hardening:

- `tools/benchmarks/periodic_sub_trans/no_wli/audit_space_map_v1_summary.py`
  - scans final artifacts with `stage3_diagnostics.space_map_v1`
  - writes reviewer-facing `pool_summaries.csv`
- `tests/tools/test_no_wli_audit_space_map_v1_summary.py`
  - guards artifact-row extraction and empty-CSV behavior

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_audit_space_map_v1_summary.py -q`
- result:
  - `23 passed`

Operational constraint:

- no long ladder run is active
- the matrix is set to a single p5 job only

### 2026-04-02 `v53` p5 one-job run: fast contract failure, fixed before rerun

Observed run state:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v53_p5c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job.json`
- result:
  - `completed_jobs = 0`
  - `remaining_jobs = 0`
  - `last_error.error_type = "KeyError"`
  - missing diagnostics keys:
    - `phaseC_start_policy`
    - `phaseC_final_winner_lane`
    - `phaseC_final_winner_source`
    - `phaseC_start_summaries`

Interpretation:

- this was not a solver-quality result
- the p5/c1 path exposed a real contract gap where the Stage 3 followup payload
  can omit Phase C diagnostics fields before finalization

Fix:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  - fills explicit empty/default Phase C fields on the followup payload before
    re-running `require_phasec_diagnostics_contract(...)`
  - keeps the contract check active; this is not a bypass

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_audit_space_map_v1_summary.py -q`
- result:
  - `26 passed`

Next step:

- rerun the same one-job `v53` p5/c1 lane
- only after one p5 control passes should we queue the next one-at-a-time
  quick control run

### 2026-04-03 `v53` rerun: easy p5/c1 control pass, then `space_map_v1` hardening and `v54` setup

Result:

- rerun artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260403T023655435018Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p5_c1_l1000__text0__seed411.json`
- `best_stage = "stage3_full_refine"`
- `best_match_ratio = 1.0`
- `stage35_baseline_selector = "score_plus_novelty"`
- `stage35_baseline_differs_from_phasec_score_winner = 0`
- `stage35_accept_passed = 0`
- `stage35_accept_reason = "top_candidate_matches_baseline"`
- `stage35_best_match = 1.0`
- matrix elapsed for the successful rerun:
  - `378.1998929977417s`

Interpretation:

- this is a clean easy-control pass, not a new mechanism win
- `p5/c1` was expected to be easy, and the bounded candidate lane did not
  damage it
- Stage 3.5 behaved as a no-op because the selector baseline and Phase C score
  winner were the same row

Hardening from this artifact:

- `tools/benchmarks/periodic_sub_trans/no_wli/run_pipeline_execution.py`
  - threads `run_id = run_dir.name` into runner state so `space_map_v1` can
    persist a non-empty run id
- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - adds `pool_status`
  - marks empty `phaseC_start` as `not_run` when `phaseC_ran != 1`
  - marks non-run empty pools as `empty` otherwise
- `tools/benchmarks/periodic_sub_trans/no_wli/audit_space_map_v1_summary.py`
  - exposes `pool_status` in reviewer-facing CSV rows

Next one-job setup:

- active mode remains:
  - `candidate_single_p5`
- next control seed:
  - `RUN_SEEDS = (511,)`
- fresh experiment id:
  - `tune_v54_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_single_1job`

Intent:

- run one more easy `p5/c1` control with `seed511`
- keep this strictly one job at a time
- use the resulting artifact to verify that `space_map_v1.run_id` and
  `pool_status` are now populated as intended

Prepared next one-job lane if `v54` passes:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- dormant mode:
  - `candidate_single_p7`
- one-job grid:
  - `p7/c1`
  - `seed411`
- fresh experiment id:
  - `tune_v55_p7c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`

Activation rule:

- do not switch the active mode while `v54` is still the run under test
- if `v54` passes and `space_map_v1.run_id/pool_status` look correct, flip
  `STAGE35_BASELINE_SELECTOR_COMPARE_MODE` from `candidate_single_p5` to
  `candidate_single_p7`
- then run exactly one new job

### 2026-04-03 `v54` p5/c1 seed511 result: solver pass, `pool_status` pass, `run_id` still blank

Result:

- run state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v54_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_single_1job.json`
- artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260403T031323700336Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p5_c1_l1000__text0__seed511.json`
- matrix result:
  - `completed_jobs = 1`
  - `remaining_jobs = 0`
  - `last_error = null`
  - `elapsed_seconds = 1752.867368221283`
- final artifact result:
  - `best_stage = "stage3_full_refine"`
  - `best_match_ratio = 1.0`
  - `stage35_accept_reason = "top_candidate_matches_baseline"`
  - `stage35_outcome_status = "completed"`

Interpretation:

- second easy `p5/c1` control passed cleanly on solver quality
- this is still an expected easy-path no-harm check, not a new promotion signal
- `space_map_v1.pool_status` is now meaningful:
  - `phaseC_start:not_run:0`
  - `stage35_seed:available:2`
  - `stage35_archive:available:11`
- but `space_map_v1.run_id` was still blank because the per-iteration state
  was rebuilt in `iteration_matrix_flow` without that field

Fix:

- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
  - `run_iteration_matrix(...)` now accepts `run_id`
  - `_build_stage_engine_iteration_state(...)` stores `run_id`
  - `_build_finalize_iteration_state(...)` stores `run_id`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_pipeline_execution.py`
  - passes `run_id = run_dir.name` into `run_iteration_matrix(...)`
- `tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py`
  - regression test for run-id propagation to finalize state

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_audit_space_map_v1_summary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_truth_diagnostics.py -q`
- result:
  - `37 passed`

### 2026-04-03 `v55 -> v57` one-shot handoff prepared

Current run:

- `v55` one-job `p7/c1 seed411`
- run state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v55_p7c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job.json`
- current status at setup time:
  - `completed_jobs = 0`
  - `remaining_jobs = 1`
  - `last_error = null`
  - Python PID `9300` active

Fresh p9 one-shot target:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  - `candidate_single` now maps to:
    - `tune_v57_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`

Automation:

- `planning/working/no_wli_v55_watch_and_launch_v57_2026-04-02.ps1`
  - polls `v55`
  - validates `best_match_ratio = 1.0`
  - validates `space_map_v1.run_id` is non-empty
  - validates `phaseC_start.pool_status` is populated
  - switches config from `candidate_single_p7` to `candidate_single`
  - launches exactly one `v57` p9 run
- `planning/working/no_wli_v57_launch_p9_2026-04-02.ps1`
  - runs `run_fixture_matrix.py`
  - tees console output to:
    - `planning/working/no_wli_v57_p9_console_2026-04-02.log`

Scope rule:

- this consumes the one-time user permission for one p9 run after `v55`
- no further long runs should be launched automatically after `v57`

Fresh rerun setup:

- active mode remains:
  - `candidate_single_p5`
- fresh one-job rerun id with the same `p5/c1 seed511` config:
  - `tune_v56_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_single_1job`

Next step:

- run the current `candidate_single_p5` / `v56` one-job lane once
- inspect the new artifact only for:
  - `best_match_ratio = 1.0`
  - `space_map_v1.run_id` non-empty
  - `phaseC_start.pool_status = "not_run"`
- only then flip to the dormant `candidate_single_p7` / `v55` mode

### 2026-04-03 `v56` p5/c1 seed511 rerun: easy-control pass, row/pool `run_id` pass, `v55` prepared

Result:

- run state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v56_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_single_1job.json`
- artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260403T035541257636Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p5_c1_l1000__text0__seed511.json`
- `completed_jobs = 1`
- `remaining_jobs = 0`
- `last_error = null`
- `elapsed_seconds = 1767.9336149692535`
- `best_stage = "stage3_full_refine"`
- `best_match_ratio = 1.0`
- `stage35_accept_reason = "top_candidate_matches_baseline"`

Data-contract readout:

- `space_map_v1.partial_state_rows[*].run_id` is populated
- `space_map_v1.pool_summaries[*].run_id` is populated
- pool-status semantics are correct:
  - `phaseC_start:not_run:0`
  - `stage35_seed:available:2`
  - `stage35_archive:available:11`

Follow-up patch before the next artifact:

- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - `space_map_v1.run_id` now exists at the top-level envelope too
- `tests/tools/test_no_wli_partial_state_space_map.py`
  - guards top-level payload `run_id`

Prepared next run:

- active mode is now:
  - `candidate_single_p7`
- one-job grid:
  - `p7/c1`
  - `seed411`
- experiment id:
  - `tune_v55_p7c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_audit_space_map_v1_summary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_truth_diagnostics.py -q`
- result:
  - `37 passed`

### 2026-04-03 v56 watcher result: pass, v55 prepared

- artifact:
  - output/tools/benchmarks/periodic_sub_trans/no_wli/20260403T035541257636Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p5_c1_l1000__text0__seed511.json
- best_match_ratio = 1
- stage35_accept_reason = "top_candidate_matches_baseline"
- space_map_v1.phaseC_start.pool_status = "not_run"
- pool run ids:
  - 20260403T035541257636Z__bench_solve_pipeline_no_wli__048e35c
- partial-row run ids:
  - 20260403T035541257636Z__bench_solve_pipeline_no_wli__048e35c
- config switched to:
  - STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p7"
- next prepared run:
  - tune_v55_p7c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job

Next action:

- run tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py

### 2026-04-03 v55 watcher result: p7 pass, v57 p9 one-shot launched

- artifact:
  - output/tools/benchmarks/periodic_sub_trans/no_wli/20260403T043758133492Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p7_c1_l1000__text0__seed411.json
- best_stage = stage35_substitution_only
- best_match_ratio = 1
- stage35_accept_reason = "accepted"
- space_map_v1.run_id = 20260403T043758133492Z__bench_solve_pipeline_no_wli__048e35c
- space_map_v1.phaseC_start.pool_status = "available"
- config switched to:
  - STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single"
- launched one-shot p9 run:
  - tune_v57_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job

Scope note:

- this uses the one-time permission for a single p9 run after v55

### 2026-04-03 `v55` p7 control and `v57` p9 hard-case confirmation

`v55` p7/c1 seed411 control:

- run state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v55_p7c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job.json`
- artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260403T043758133492Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p7_c1_l1000__text0__seed411.json`
- `completed_jobs = 1`
- `remaining_jobs = 0`
- `last_error = null`
- `elapsed_seconds = 12137.381100654602`
- `best_stage = "stage35_substitution_only"`
- `best_match_ratio = 1.0`
- Stage 3.5:
  - `stage35_baseline_selector = "score_plus_novelty"`
  - `stage35_baseline_candidate_hash = "07ce4687410f3e96"`
  - `stage35_phasec_score_winner_candidate_hash = "cc398c92417b08db"`
  - `stage35_baseline_differs_from_phasec_score_winner = 1`
  - `stage35_accept_passed = 1`
  - `stage35_accept_reason = "accepted"`
  - `stage35_rounds_completed = 1`
  - `stage35_evals = 575`
  - `stage35_runtime_seconds = 483.7016396999825`
  - `stage35_outcome_status = "completed"`
- space-map data contract:
  - `space_map_v1.run_id = "20260403T043758133492Z__bench_solve_pipeline_no_wli__048e35c"`
  - `phaseC_start.pool_status = "available"`
  - `phaseC_start.row_count = 6`
  - `stage35_seed.row_count = 5`
  - `stage35_archive.row_count = 12`

`v55` interpretation:

- this is a clean no-harm p7 control pass under the bounded candidate lane
- it is not a new hard-case science win, because the run already had a solved
  Phase C anchor:
  - `phaseC_score_selected_winner_summary.init_match = 1.0`
  - `phaseC_score_selected_winner_summary.final_match = 1.0`
  - `phaseC_improved_best = 0`
  - `phaseC_final_winner_lane = "anchor"`
- therefore the main engineering lesson from `v55` is the same Phase C stop
  omission seen in console output:
  - if truth is available
  - `continue_after_solve = 0`
  - and the current Phase C anchor already has `match >= solve threshold`
  - then Phase C and Stage 3.5 should be skipped immediately instead of
    spending another `9216` Phase C evals and one Stage 3.5 round

`v57` p9/c3 seed411 one-shot confirmation:

- run state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v57_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job.json`
- artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260403T080049428735Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed411.json`
- `completed_jobs = 1`
- `remaining_jobs = 0`
- `last_error = null`
- `elapsed_seconds = 11870.78020787239`
- `best_stage = "stage35_substitution_only"`
- `best_match_ratio = 0.487`
- Stage 3.5:
  - `stage35_baseline_selector = "score_plus_novelty"`
  - `stage35_baseline_candidate_hash = "9002ee09917e5a0d"`
  - `stage35_baseline_candidate_source = "phaseA_selected"`
  - `stage35_baseline_candidate_lane = "challenger"`
  - `stage35_baseline_candidate_source_rank = 2`
  - `stage35_baseline_differs_from_phasec_score_winner = 1`
  - `stage35_accept_passed = 1`
  - `stage35_accept_reason = "accepted"`
  - `stage35_best_match = 0.487`
  - `stage35_best_score = 0.18130345628397204`
  - `stage35_truth_gain_vs_selected_row = 0.069`
  - `stage35_truth_gain_vs_phasec_score_winner = 0.448`
  - `stage35_rounds_completed = 1`
  - `stage35_evals = 4352`
  - `stage35_runtime_seconds = 3295.0344342000317`
  - `stage35_outcome_status = "completed"`
- space-map data contract:
  - `space_map_v1.run_id = "20260403T080049428735Z__bench_solve_pipeline_no_wli__048e35c"`
  - `phaseC_start.pool_status = "available"`
  - `phaseC_start.row_count = 6`
  - `stage35_seed.row_count = 2`
  - `stage35_archive.row_count = 12`

`v57` interpretation:

- this is a reproducibility pass for the bounded hard-case mechanism
- `v57` reproduces the earlier `v51` result on the same `p9/c3 seed411`
  case under the same bounded candidate lane:
  - different Stage 3.5 baseline row
  - Stage 3.5 admission flips to `accepted`
  - continuation reaches `best_match_ratio = 0.487`
- it still strongly beats the locked `v48` legacy lane on the same case:
  - `v48` legacy:
    - baseline hash `73eee2bf84b7c07f`
    - `stage35_accept_reason = "search_score_drop_guard_failed"`
    - `best_match_ratio = 0.041`
  - `v57` candidate:
    - baseline hash `9002ee09917e5a0d`
    - `stage35_accept_reason = "accepted"`
    - `best_match_ratio = 0.487`
- this strengthens the claim that `v51` was not a one-off artifact, but it
  still does not prove broad promotion because the hard-case confirmation is
  the same `411` seed family

Immediate next implementation step:

- add a truth-based solved-state stop gate at the Phase C / Stage 3.5 handoff
  for benchmark runs:
  - if `continue_after_solve = 0`
  - truth is available
  - and the current best row is already at or above the solve threshold
  - skip Phase C and Stage 3.5 immediately
- keep score-based early stopping as a separate measured study; do not hardcode
  a raw score threshold from `0.501111`

Data-contract follow-up:

- the Stage 3.5 progress/partial files are written on disk:
  - `stage35_progress.jsonl`
  - `stage35_partial_state.json`
- final diagnostics currently store the file-name fields:
  - `stage35_progress_jsonl_name`
  - `stage35_partial_state_name`
- if reviewer-facing consumers need direct repo-relative paths, add explicit
  relative-path fields next instead of relying on file-name + run-dir inference

Scope note:

- the one-time permission for one p9 run after `v55` has now been consumed by
  `v57`
- no further long runs should be auto-launched without a fresh user decision

### 2026-04-03 `space_map_v1` classifier / atlas extractor slice

Landed:

- `planning/working/no_wli_space_map_v1_classifier_spec_2026-04-03.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
- `tests/tools/test_no_wli_extract_space_map_v1_atlas.py`

What this gives:

- deterministic first-pass row labels
- deterministic first-pass pool labels
- deterministic first-pass run labels
- explicit data-gap flags when `space_map_v1` does not yet contain enough
  information
- a hardcoded no-CLI offline extractor that emits row / pool / transition /
  run atlas CSVs plus `summary.json`

Classifier scope:

- this is a science/reporting layer only
- no solver decisions changed

First atlas run:

- command:
  - `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260403T143429Z__space_map_v1_atlas/summary.json`
- scan summary:
  - `artifacts_scanned = 361`
  - `row_atlas_rows = 81`
  - `pool_atlas_rows = 15`
  - `transition_atlas_rows = 53`
  - `run_atlas_rows = 361`
- run labels:
  - `solved_control = 47`
  - `stage35_guard_reject = 5`
  - `stage35_live_win = 3`
  - `unclassified_run = 306`
- row labels:
  - `false_friend = 3`
  - `weak_family_survivor = 2`
  - `unclassified_row = 76`
- strongest data-gap flags:
  - `missing_space_map_v1 = 356`
  - `missing_distance_to_anchor = 71`
  - `missing_parent_candidate_hash = 28`
  - `phasec_pool_not_row_complete = 2`

Immediate reading:

- this gives a real first reviewer-facing atlas table set
- it also confirms that most older artifacts predate `space_map_v1`, so a broad
  historical hill-map claim is not yet available from current data
- the highest-value next data-contract improvements are parent links, anchor
  distances, and richer family IDs at the saved-row boundary

### 2026-04-03 `space_map_v1` saved-row boundary hardening

Landed:

- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - parent fallback for non-root Phase C starts and Stage 3.5 rows
  - family-view anchor-distance derivation
  - cluster-based `family_id` assignment under the run's
    `phaseC_novel_view_id`
  - continuation links on the baseline Stage 3.5 seed row
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - passes `tier.columns` into `build_late_space_map_payload(...)`
- `tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
  - root rows are no longer marked as missing-parent gaps

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_extract_space_map_v1_atlas.py tests/tools/test_no_wli_audit_space_map_v1_summary.py -q`
- result:
  - `7 passed`

Atlas smoke check:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260403T144434Z__space_map_v1_atlas`

Important caveat:

- this patch improves the serializer for future artifacts only
- old `v55` / `v57` final artifacts are not retroactively backfilled
- if we want reviewer-facing examples of the new fields, run one fresh short
  p5/p7 control artifact under the current code

### 2026-04-03 `space_map_v1` Stage 2 / Stage 3 prep pool extension

Landed:

- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - serializes `stage2_promoted` rows/pools
  - serializes `stage3_prep` rows/pools from `stage3_prep_live.init3`
  - serializes row-complete `phaseC_pool` rows/pools from
    `phaseC_candidate_pool_rows`
  - preserves canonical row/pool schema without changing solver decisions
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - returns Phase C candidate-pool rows as diagnostics-only data
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  - threads Phase C candidate-pool rows through Stage 3 finalize state
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
  - stores those rows in `stage3_diagnostics`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - threads `stage2_promoted` and `stage3_prep_live` into the space-map payload
- `tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
  - root-row parent-gap detection now understands `stage2_promoted` and the
    Stage 3 prep anchor row
  - Phase C row-completeness checks now prefer `phaseC_pool`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_extract_space_map_v1_atlas.py tests/tools/test_no_wli_audit_space_map_v1_summary.py -q`
- result:
  - `7 passed`

Maintained next order:

- run one fresh short smoke artifact under the new serializer
- inspect the atlas on that fresh artifact before collecting more comparison
  runs

Remaining known limitation:

- Stage 3 prep mutated-row parent links still use a fallback parent-to-anchor
  edge because exact mutation-origin metadata is not present in
  `stage3_prep_live`

### 2026-04-03 `v58` p5 smoke lane prepared

Purpose:

- produce one fresh short p5 artifact under the new `space_map_v1` serializer
- verify Stage 2 promoted / Stage 3 prep / Phase C pool rows populate cleanly
  in a real artifact before collecting more runs

Config:

- `STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p5"`
- period / columns / seed:
  - `p5/c1`
  - `seed511`
- experiment id:
  - `tune_v58_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_space_map_v1_smoke_single_1job`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_partial_state_space_map.py -q`
- result:
  - `22 passed`

Post-run readout:

- confirm p5 remains solved/no-harm
- inspect `stage3_diagnostics.space_map_v1.pool_summaries` for the six mapped
  boundaries
- run the offline atlas extractor and check whether the new `phaseC_pool` rows
  eliminate the `phasec_pool_not_row_complete` warning on the fresh artifact

### 2026-04-03 `v58` watcher and `v59` fresh-seed ladder handoff

Prepared:

- watcher:
  - `planning/working/no_wli_v58_watch_and_launch_v59_2026-04-03.ps1`
- launch script:
  - `planning/working/no_wli_v59_launch_ladder_small_2026-04-03.ps1`
- watch log:
  - `planning/working/no_wli_v58_watch_and_launch_v59_2026-04-03.log`

Handoff rule:

- monitor the current `v58` p5 smoke run
- if `best_match_ratio = 1.0` and all six `space_map_v1` pool summaries are
  present with non-empty `pool_status`, run the atlas extractor, switch the
  fixture-matrix mode to `candidate_ladder_small`, and launch one `v59` ladder
  run
- if the smoke artifact fails that contract, do not launch `v59`

Fresh-seed ladder config:

- `RUN_SEEDS = (611, 711)`
- `MAX_WALLCLOCK_SECONDS = 28800`
- experiment id:
  - `tune_v59_ladder_small_seed611_711_stage35_baseline_selector_candidate_live_bounded_space_map_v1_6job`

Scope note:

- this is one unattended `v58 -> v59` handoff only
- do not auto-chain beyond `v59`

### 2026-04-03 `v58` p5 smoke result

Artifact:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260403T151917509031Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p5_c1_l1000__text0__seed511.json`

Result:

- `best_stage = stage3_full_refine`
- `best_match_ratio = 1.0`
- `stage35_accept_reason = "top_candidate_matches_baseline"`
- elapsed:
  - `2031.532s`

`space_map_v1` smoke contract:

- `run_id = 20260403T151917509031Z__bench_solve_pipeline_no_wli__048e35c`
- pool summaries:
  - `stage2_promoted:available:43`
  - `stage3_prep:available:96`
  - `phaseC_pool:not_run:0`
  - `phaseC_start:not_run:0`
  - `stage35_seed:available:2`
  - `stage35_archive:available:11`
- partial-state rows:
  - `152`

Atlas smoke:

- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260403T155429Z__space_map_v1_atlas`
- fresh `v58` artifact is correctly classified as `solved_control`
- the remaining `missing_space_map_v1` warnings are expected historical debt from
  pre-serializer artifacts, not a blocker for fresh runs

Next prepared run:

- `STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_ladder_small"`
- fresh seeds:
  - `611`
  - `711`
- experiment id:
  - `tune_v59_ladder_small_seed611_711_stage35_baseline_selector_candidate_live_bounded_space_map_v1_6job`

### 2026-04-03 seed-taxonomy rule for `v59` and the next ladder passes

Purpose:

- use a few fresh seeds to test whether the late search geometry forms repeated
  seed categories, not just one-off anecdotes
- keep `411` as the fixed anchor hard case for comparability to the known
  `9002...` continuation mechanism

Maintained interpretation rule:

- if `611` / `711` reproduce a similar p9 hard family or a similar p5 solved
  control pattern, that supports the view that the space map is discovering
  repeated categories
- if every seed produces a seemingly unique family geometry, treat that as a
  warning sign:
  - either the search space is genuinely highly fragmented
  - or the current `family_id` / distance / lineage descriptors are still too
    weak to identify repeated hill structure

Post-`v59` readout:

- run `tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
- compare seeds by:
  - `run_type`
  - pool-level `family_count` / `largest_family_share`
  - selected-vs-available family coverage at `stage2_promoted`, `stage3_prep`,
    `phaseC_pool`, `phaseC_start`, `stage35_seed`, and `stage35_archive`
  - whether accepted Stage 3.5 rows come from a repeated family signature
  - whether best-row lineage and parent chains repeat across seeds
- choose the next 1-2 seeds deliberately:
  - one likely same-family repeat
  - one likely new hard family

Scope:

- do not treat fresh seeds as a reason to discard `411`
- do not chase random new seeds indefinitely
- the goal is a small, auditable seed taxonomy

### 2026-04-03 `score_stop_shadow_v2` offline analysis spec and extractor fixes

Requested scope:

- study non-oracle early-stop and dump-for-inspection signals from saved
  artifacts
- keep this as shadow/offline analysis only
- do not change solver decisions in this slice

Spec written for review:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/SPEC.md`
- archived v1 spec:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/SPEC_V1_ARCHIVE.md`

Feasibility findings recorded in the spec:

- fixture truth labels are available from `target_plaintext_idx`
- full/search/judge rescoring is feasible offline by rebuilding the cipher and
  scorer runtimes from the artifact plus `run_config.json`, following the same
  runtime builders already used by `artifact_resume.py`
- word-ngram replay rescoring is partly feasible now:
  - final-best and Stage 2 / Stage 3 top-k word-ngram reports are persisted
  - most `space_map_v1.partial_state_rows[*].word_ngram_summary` entries are
    still empty placeholders, so row-complete word-ngram rescoring will need
    decrypt/score replay when plaintext/key material is available
- `stage2_promoted` and `stage3_prep` rows in the fresh p5 artifact often have
  key material but no plaintext and/or blank scores, so the first extractor
  must support a decrypt-then-score path and emit explicit `data_gap_flags`
  instead of dropping rows silently

Maintained implementation order:

- review the spec first
- then implement the no-CLI extractor
- then run a tiny mixed artifact subset before using shadow-stop summaries to
  guide any live policy changes

Extractor review fixes landed in
`tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`:

- artifact discovery now sorts newest-first before applying `MAX_ARTIFACTS`
- dump-only and stop-capable rules are summarized separately, so
  `would_dump = 1` no longer implies `would_stop = 1`
- family stability labels now choose the strongest satisfied
  boundary-support threshold rather than always stopping at support 1
- repo-relative artifact paths are emitted robustly for both absolute and
  relative artifact paths
- the stale `score_stop_shadow_v1` implementation folder was removed; v2 is now
  the canonical folder name

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_score_stop_shadow_v2.py tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_extract_space_map_v1_atlas.py -q`
- result:
  - `10 passed`

First no-CLI extractor pass:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260404T015035Z__score_stop_shadow_v2`
- analyzed:
  - `144` artifacts
  - `936` row records
  - `144` run summaries

Interpretation:

- the three reviewed logic fixes are working structurally:
  - newest-first scan runs to completion
  - dump and stop summaries remain separate
  - stability support thresholds no longer collapse to support 1
- but this first sample produced **no active rule rows** in
  `threshold_sweep_summary.json`
- immediate reason from the row dump:
  - `replay_word_ngram_available = false` for all `936` rows
  - `family_id_kind` is blank for all `936` rows
- likely cause:
  - the newest artifacts in this extractor sample still predate the latest
    `space_map_v1` serializer semantics patch and do not expose row-complete
    word-ngram reports
- maintained next step:
  - do **not** tune stop thresholds from this empty summary
  - first generate one fresh artifact under the current serializer/scorer
    state, then rerun `score_stop_shadow_v2` and re-check whether dump/stop
    trigger regions become visible

### 2026-04-03 `space_map_v1` review-response semantics hardening

Review conclusion:

- current diagnostics architecture is on track
- no extra boundary coverage is needed immediately
- the main remaining risk is semantic correctness of reviewer-facing map
  fields, not solver wiring

Landed diagnostics-only fixes:

- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - `selected_family_count` now counts families in the selected subset, not the
    whole pool
  - `selected_pairwise_distance_min` / `selected_pairwise_distance_mean` are now
    computed over selected rows only
  - `top_band_family_count` is now computed from the top selected-band rows,
    rather than blindly mirroring whole-pool `family_count`
  - each row now records `parent_link_kind` as `root`, `observed`, or
    `fallback_anchor`
  - each row now records `family_id_kind` as `run_local_cluster`,
    `hash_fallback`, or `saved_row`
- `tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
  - `stage35_archive` baseline/root rows are now treated as valid roots for
    missing-parent checks
  - `missing_stage35_progress_paths` is only raised when Stage 3.5 was
    requested, ran, or Stage 3.5 rows are present
  - row atlas output now includes `parent_candidate_hash`, `parent_link_kind`,
    and `family_id_kind`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_extract_space_map_v1_atlas.py tests/tools/test_no_wli_audit_space_map_v1_summary.py -q`
- result:
  - `9 passed`

Interpretation discipline:

- `family_id` remains a run-local cluster label under the chosen family view,
  not a stable cross-run hill identifier
- fallback parent links are now explicit, but they are still scaffolding edges,
  not exact mutation ancestry

### 2026-04-04 score-stop score-panel narrowing

Decision:

- do the **score-only panel first**
- use old `0.7-ish` artifacts as mid-quality calibration cases
- do **not** mix in the family-stability track yet

Why:

- the immediate question is whether late rows that are solved / nearly solved /
  mid-quality / bad occupy distinguishable score-report regions
- old artifacts are still useful for that score calibration even when they
  predate `space_map_v1`
- fresh current-code artifacts remain more important for the later family
  track, not this first pass

Implementation state:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
  now has a bounded `score_panel_v1` mode
- hardcoded score panel settings:
  - `MAX_ARTIFACTS = 24`
  - score-band targets:
    - solved / near-perfect: `6`
    - near-solved / high-quality: `6`
    - mid-quality: `8`
    - bad / false-friend: `4`
  - only late boundaries are replay-scored:
    - `stage2_topk`
    - `stage3_topk`
    - `phaseC_start`
    - `stage35_seed`
    - `stage35_archive`
  - at most `2` rows per boundary per artifact are rescored
  - family-stability `would_stop` is disabled in this mode

Threshold interpretation:

- a fresh solved `v60` p5 row replay-scored at roughly:
  - `replay_word_ngram_trust_score = 0.479`
  - `replay_word_ngram_report_xent = 16.227`
- therefore the original strict trust/xent grid was not on the right scale for
  this scorer
- current score-panel grid:
  - `TRUST_SCORE_FLOORS = (0.30, 0.40, 0.50)`
  - `REPORT_XENT_CEILINGS = (24.0, 18.0, 12.0)`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_score_stop_shadow_v2.py -q`
- result:
  - `4 passed`
- `C:\Python\Python311\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- result:
  - clean

Maintained next step:

- run one short bounded `score_panel_v1` extractor pass
- inspect dump triggers on:
  - solved / near-perfect
  - near-solved
  - mid-quality
  - bad / false-friend
- do not claim a stop rule yet; this pass is only for late-row dump separability

### 2026-04-04 score-stop legacy fallback expansion

Goal:

- use more existing pre-`space_map_v1` artifacts before collecting fresh family
  runs

Implementation:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
  now falls back to legacy `stage2_topk` and `stage3_topk` rows when
  `space_map_v1` is absent
- `stage3_topk.end_hash` is reused as `candidate_hash` when present
- if no saved hash exists, a stable key hash is derived from `key_idx`
- score-panel row filtering now allows `stage2_topk` and `stage3_topk`
- legacy `phaseC_start` fallback rows now inherit key/plaintext state from a
  same-hash `stage3_topk` fallback row when the summary row itself omits that
  material

Validation:

- `C:\Python\Python311\python.exe -m pytest tests\tools\test_no_wli_score_stop_shadow_v2.py -q`
- result:
  - `6 passed`
- `C:\Python\Python311\python.exe -m py_compile tools\benchmarks\periodic_sub_trans\no_wli\analysis\score_stop_shadow_v2\extract_score_stop_shadow_v2.py`
- result:
  - clean

Observed effect:

- rerunning the extractor produced `47` rows across `8` artifacts in
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260404T051918Z__score_stop_shadow_v2`
- the old `p7/c3 seed111` near-solved artifact now contributes replay-scored
  `stage3_topk` rows with `truth ~= 0.997`, active word-ngram reports, and
  `would_dump = 1`
- this closes the earlier false-negative hole where that old near-solved run
  was effectively invisible to the score-panel fallback

### 2026-04-04 expanded 24-artifact score-panel readout

Extractor run:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260404T052802Z__score_stop_shadow_v2`

Summary:

- `24` artifacts
- `135` row records
- one relaxed dump rule fired:
  - `trust0.30_xent24.00_margin0.00_support1`
- run-level trigger count:
  - `9`
- false positives:
  - `0`
- solved controls among triggered runs:
  - `6`

Useful replay-score signals now recovered from old artifacts:

- old `p7/c3 seed111` near-solved `stage3_topk` rows now replay-score at roughly
  `truth ~= 0.997`, `trust ~= 0.49-0.50`, `xent ~= 16.06-16.15`, and trigger
  `would_dump = 1`
- old `p9/c3 seed211` `phaseC_start` row `cbdd1649801f34ad` now inherits state
  from a same-hash `stage3_topk` row and replay-scores at `truth ~= 0.581`
  without fabricating a dump trigger

Remaining data gaps:

- `missing_plaintext_and_key` dropped from `12` to `6`
- the surviving missing rows are still legacy fallback rows whose
  `phaseC_start.candidate_hash` values do not hash-match `stage3_topk` rows or
  any `resume_handoffs/.../stage3_prep.json` key lists under `stable_key_hash`
- `word_ngram_unavailable_for_run = 12` still appears on some legacy artifacts;
  do not silently synthesize report-scorer config for those runs

Interpretation:

- this expanded score-panel pass is now good enough to say the current relaxed
  WNG dump rule is behaving like a **near-solved / solved dump trigger**, not a
  general hard-case stop rule
- it fires on fresh p5/p7 solved controls, fresh p9/c1 `0.962`, and old p7/c3
  `0.997`, but not on known p9/c3 hard/mid rows like `0.487`, `0.581`, or
  `0.041`
- that is useful, but still only a **dump** signal; no stop-policy claim yet

Score-boundary shape in the current 24-artifact panel:

- solved / near-solved rows with active word-ngram reports cluster around:
  - `trust ~= 0.316-0.500`
  - `xent ~= 16.06-17.77`
- mid / bad rows are mostly either:
  - inactive word-ngram rows with missing or `NaN` report xent, or
  - active low-trust rows with `trust <= 0.227` and `xent = 20.0`
- in this panel, the `trust >= 0.30` and `xent <= 24.0` dump rule therefore
  separates near-solved rows from known p9/c3 mid/bad rows reasonably well
- do not overstate this: the panel is still small, old rows are fallback-heavy,
  and this is not a calibrated stop rule

### 2026-04-04 `v61` family overnight setup

Decision:

- switch from score-only analysis back to a fresh **family mapping** overnight
  collection run under current `space_map_v1`
- keep the run narrow enough to read tomorrow

Configured run:

- compare mode:
  - `candidate_family_overnight`
- preset:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- grid:
  - `p7/c1 seed411`
  - `p7/c1 seed611`
  - `p9/c3 seed411`
  - `p9/c3 seed611`
- experiment id:
  - `tune_v61_family_overnight_p7c1_p9c3_seed411_611_stage35_baseline_selector_candidate_live_bounded_space_map_v1_4job`
- cap:
  - `MAX_JOBS = 4`
  - `MAX_WALLCLOCK_SECONDS = 43200.0`

Goal:

- collect fresh current-serializer `space_map_v1` artifacts for one solved-ish
  control class and one hard class, each with an anchor seed and one fresh seed
- answer whether the same run-local family patterns repeat, and where useful
  families collapse, before broader family runs

### 2026-04-04 `v61` family overnight readout

Run status:

- `fixture_matrix_run_state_tune_v61_family_overnight_p7c1_p9c3_seed411_611_stage35_baseline_selector_candidate_live_bounded_space_map_v1_4job.json`
- completed jobs:
  - `3 / 4`
- completed:
  - `p7/c1 seed411`
  - `p7/c1 seed611`
  - `p9/c3 seed411`
- not completed:
  - `p9/c3 seed611`
- stop reason:
  - wallclock cap reached after `47420.9s` with `completed_jobs=3`

Fresh artifact roots:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260404T074732265025Z__bench_solve_pipeline_no_wli__048e35c`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260404T114639913723Z__bench_solve_pipeline_no_wli__048e35c`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260404T154911594408Z__bench_solve_pipeline_no_wli__048e35c`

Atlas / audit processing:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/extract_space_map_v1_atlas.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260404T212752Z__space_map_v1_atlas`
- summary:
  - `artifacts_scanned = 369`
  - `row_atlas_rows = 1552`
  - `pool_atlas_rows = 63`
  - `transition_atlas_rows = 1054`
  - `run_atlas_rows = 369`
- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/audit_space_map_v1_summary.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260404T212751Z__space_map_v1_audit`
- summary:
  - `artifacts_scanned = 200`
  - `pool_summary_rows = 63`

Completed-job readout:

- `p7/c1 seed411`
  - `best_stage = stage35_substitution_only`
  - `best_match_ratio = 1.000`
  - `stage35_baseline_candidate_hash = 07ce4687410f3e96`
  - `stage35_best_candidate_hash = 2496ca6590fbb91e`
  - `stage35_baseline_differs_from_phasec_score_winner = 1`
  - `stage35_accept_passed = 1`
  - `stage35_accept_reason = accepted`
  - `stage35_runtime_seconds = 721.5`
  - `phaseC_start` family count:
    - `2`
  - `phaseC_start` largest-family share:
    - `0.833`
  - `stage35_seed` family count:
    - `1`
  - `stage35_archive` family count:
    - `1`
- `p7/c1 seed611`
  - `best_stage = stage35_substitution_only`
  - `best_match_ratio = 1.000`
  - `stage35_baseline_candidate_hash = 2f7093889e1f3774`
  - `stage35_best_candidate_hash = d3ca00efc70a43db`
  - `stage35_baseline_differs_from_phasec_score_winner = 1`
  - `stage35_accept_passed = 1`
  - `stage35_accept_reason = accepted`
  - `stage35_runtime_seconds = 742.2`
  - `phaseC_start` family count:
    - `2`
  - `phaseC_start` largest-family share:
    - `0.833`
  - `stage35_seed` family count:
    - `1`
  - `stage35_archive` family count:
    - `1`
- `p9/c3 seed411`
  - `best_stage = stage35_substitution_only`
  - `best_match_ratio = 0.487`
  - `stage35_baseline_candidate_hash = 9002ee09917e5a0d`
  - `stage35_best_candidate_hash = 1fdc6d7d88e80a2b`
  - `stage35_baseline_differs_from_phasec_score_winner = 1`
  - `stage35_accept_passed = 1`
  - `stage35_accept_reason = accepted`
  - `stage35_runtime_seconds = 4383.9`
  - `phaseC_start` family count:
    - `6`
  - `phaseC_start` largest-family share:
    - `0.167`
  - `stage35_seed` family count:
    - `2`
  - `stage35_archive` family count:
    - `1`

Map interpretation:

- the two solved p7 controls show a repeatable low-diversity late shape:
  `phaseC_start` carries `2` families, but one family dominates `5 / 6` starts,
  and Stage 3.5 collapses to a single archive family
- the hard `p9/c3 seed411` anchor shows a wider late frontier:
  `phaseC_start` retains `6` distinct families, Stage 3.5 seeds from `2`
  families, and the accepted archive collapses to the `9002...` branch that
  reproduces the known `0.487` live win
- that is a real fresh-map confirmation of the hard-anchor mechanism, but not a
  family-repeatability result across hard fresh seeds, because `p9/c3 seed611`
  did not run before the wallclock cap

Immediate next plan:

- do **not** rerun the full 4-job panel in the same shape
- implement the benchmark-only oracle solved-stop gate first, so easy p7
  controls do not spend hours in Phase C / Stage 3.5 after they are already
  solved
- then run only the missing `p9/c3 seed611` one-job family collection under the
  current serializer to answer the hard fresh-seed repeatability question
- keep any stop-gate claim strictly benchmark-only until a separate non-oracle
  calibration pass exists

### 2026-04-04 no_wli directory first-pass reorg

Goal:

- make `tools/benchmarks/periodic_sub_trans/no_wli/` easier to navigate without
  moving import-heavy solver/runtime modules yet

Low-risk moves made:

- analysis/report/profiling leaf scripts moved under
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/`
- standalone launchers/harnesses moved under
  `tools/benchmarks/periodic_sub_trans/no_wli/runs/`
- stale nested package-local output initially archived under
  `tools/benchmarks/periodic_sub_trans/no_wli/old/output_legacy_nested/`

### 2026-04-04 stale nested no_wli output cleanup

Problem:

- the archived package-local output tree mirrored long
  `tools/benchmarks/periodic_sub_trans/no_wli/...` subpaths under
  `tools/benchmarks/periodic_sub_trans/no_wli/old/output_legacy_nested/`
- those stale tracked/generated paths were the source of the GitHub Desktop
  Windows `Filename too long` failure

Fix:

- removed `tools/benchmarks/periodic_sub_trans/no_wli/old/output_legacy_nested/`
  from the working tree
- confirmed the old package-local
  `tools/benchmarks/periodic_sub_trans/no_wli/output/` tree is absent locally
- added narrow `.gitignore` rules for both stale package-local generated-output
  paths
- updated `tools/benchmarks/periodic_sub_trans/no_wli/README.md` so the
  retained artifact location is unambiguous:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/`

Scope discipline:

- no current output path builders were rewritten in this pass
- this was a stale tracked-artifact cleanup, not a live-path redesign

Kept at package root for now:

- `stage*`, `phasec_*`, `iteration_*`, `runner*`, `fixture_matrix_*`,
  `runtime_*`, `run_*`, `oracle_*`, `scoring_*`, and replay modules with broader
  import fanout

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_build_output_catalog.py tests/tools/test_no_wli_extract_space_map_v1_atlas.py tests/tools/test_no_wli_audit_space_map_v1_summary.py tests/tools/test_no_wli_partial_state_signal_audit.py tests/tools/test_no_wli_basin_family_diversity_alignment_audit.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_stage35_replay_profile.py tests/tools/test_no_wli_stage35_replay_sweep.py tests/tools/test_no_wli_word_ngram_tiebreak_profile.py tests/tools/test_no_wli_span_ab_harness.py tests/tools/test_no_wli_output_root_paths.py -q`
- result:
  - `29 passed`
- `C:\Python\Python311\python.exe -m py_compile ...` on moved analysis/run
  scripts and affected replay/run modules
- result:
  - clean

### 2026-04-04 recent-file tidy pass

Scope:

- reran the small test slice that covers the recent fixture-matrix,
  `space_map_v1`, and `score_stop_shadow_v2` edits
- reran `py_compile` on the recent config / atlas / score-stop scripts
- checked `git diff --check`
- removed generated `__pycache__` folders under the new no-WLI `analysis/`
  tree

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_score_stop_shadow_v2.py tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_extract_space_map_v1_atlas.py tests/tools/test_no_wli_output_root_paths.py -q`
- result:
  - `35 passed`
- `C:\Python\Python311\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py tools/benchmarks/periodic_sub_trans/no_wli/analysis/extract_space_map_v1_atlas.py`
- result:
  - clean
- `git diff --check`
- result:
  - clean apart from the existing LF/CRLF warnings in this working tree

Notes:

- no new runtime/science bug was found in the recent scripts during this pass
- one code-hygiene issue was fixed by removing generated Python cache folders
  from `tools/benchmarks/periodic_sub_trans/no_wli/analysis/`
- one AGENTS-style path issue was fixed for future fixture-matrix runs:
  `campaign_config_path` in the run-state JSON is now serialized repo-relative
  instead of as an absolute local path

### 2026-04-04 benchmark-only solved-stop patch and v62 handoff

Problem:

- fresh `v61` p7 controls solved at `1.0`, but still spent hours in Phase C and
  Stage 3.5 because the two-phase path and the Stage 3.5 handoff did not yet
  respect the existing `STAGE3_CONTINUE_AFTER_SOLVE = 0` benchmark shortcut
  once a solved state had already been reached

Fix:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  now uses the existing `stage3_continue_after_solve` flag at the
  Phase B -> Phase C handoff:
  if the current best state is already at or above `solve_match_threshold` and
  `continue_after_solve=0`, Phase C is not started
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_calls.py`
  now threads that existing flag into the two-phase followup call
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  now records an already-solved Stage 3.5 skip as an explicit valid not-run
  outcome instead of a false proof failure:
  `stage35_outcome_status = not_run_solved_stage3`,
  `stage35_outcome_reason = continue_after_solve_disabled`,
  `stage35_accept_reason = solved_before_stage35`

Regression coverage:

- `tests/tools/test_no_wli_stage3_phasec.py`
- `tests/tools/test_no_wli_stage35_substitution_solver.py`
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`

Prepared next run:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  is now configured for a single current-code family/map job:
  `STAGE35_BASELINE_SELECTOR_COMPARE_MODE = candidate_single_p9_seed611`,
  `PERIODS_OVERRIDE = (9,)`, `COLUMNS_OVERRIDE_BY_PERIOD = {9: (3,)}`,
  `RUN_SEEDS = (611,)`, experiment id
  `tune_v62_p9c3_seed611_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`
- that run is configured but not launched in this pass
