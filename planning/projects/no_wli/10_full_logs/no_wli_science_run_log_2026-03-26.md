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

### 2026-04-04 planning baseline migration

Outcome:

- promoted the No-WLI planning baseline into the stable repo home:
  `planning/projects/no_wli/`
- preserved the dated refactor snapshot under:
  `planning/archive/no_wli_planning_refactor_20260404/`
- migrated the previous flat `planning/working/` no-WLI material into the new
  bucketed structure
- moved imported refactor packs, external review packs, and the pre-migration
  flat working snapshot under:
  `planning/old/no_wli_legacy_migration_2026-04-04/`

Notes:

- `planning/working/` was intentionally left in place as a deprecated staging
  area so older log/watch paths do not break immediately
- top-level planning navigation now lives in:
  `planning/projects/no_wli/README.md`,
  `planning/projects/no_wli/00_CURRENT_STATE.md`,
  `planning/projects/no_wli/01_EXPERIMENT_INDEX.md`,
  `planning/projects/no_wli/02_OPEN_QUESTIONS.md`,
  `planning/projects/no_wli/03_DOCUMENT_MAP.md`,
  `planning/projects/no_wli/04_ACTIVE_RUNBOOK.md`

### 2026-04-05 v62 fresh hard-seed map result

Run:

- experiment:
  `tune_v62_p9c3_seed611_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`
- artifact root:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/20260404T214925941101Z__bench_solve_pipeline_no_wli__37dc435/`

Outcome:

- `p9/c3 seed611` completed in `11745.19s` wallclock for the full job
- final `best_stage = stage35_substitution_only`
- final `best_match_ratio = 0.635`
- final `best_score = 0.2515235002311922`
- Stage 3.5 accepted and completed:
  - `stage35_accept_reason = accepted`
  - `stage35_runtime_seconds = 1227.11`
  - `stage35_evals = 1300`
  - `stage35_best_candidate_hash = 4bba54177206dd7f`

Important comparison against fresh `seed411`:

- `seed411` remains the selector-override mechanism proof:
  - `stage35_baseline_differs_from_phasec_score_winner = 1`
  - baseline candidate hash `9002ee09917e5a0d`
  - baseline source `phaseA_selected`
  - final `best_match_ratio = 0.487`
- `seed611` is a distinct hard-seed win shape:
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline candidate hash `fe7a4d2798b221e4`
  - baseline source `phaseB_topk`
  - final `best_match_ratio = 0.635`

So:

- `v62` widens the hard-seed late-stage evidence
- `v62` does **not** by itself widen the specific selector-override claim

Fresh atlas outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260405T010917Z__space_map_v1_atlas/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260405T011039Z__space_map_v1_audit/`

Map read:

- `stage2_promoted` and `stage3_prep` look structurally similar between
  `seed411` and `seed611`
- both runs keep broad multi-hill structure through `phaseC_pool`
- the clearest divergence is late:
  - `seed411 stage35_seed`: `2` rows, `2` families, largest-family share `0.5`
  - `seed611 stage35_seed`: `6` rows, `2` families, largest-family share
    `0.8333`

Interpretation:

- there are now at least two distinct hard-seed Stage 3.5 win shapes in the
  programme
- `seed611` supports bounded Stage 3.5 utility beyond the exact `411` family
- but selector generality still needs a narrower proof, because `seed611` did
  not require a Phase C score-winner override

Remaining measurement caution:

- at `stage35_seed`, the reviewer-visible pool summary still reports
  `selected_row_count = 0`, while the more useful late continuation evidence is
  carried in `next_stage_started_count` and the row-level data
- that is usable for now, but it should be tightened before stronger
  selected-versus-available claims are made at that boundary

### 2026-04-05 v63 prepared: seed611 bounded legacy control

Reason:

- `v62` established a real second hard-seed Stage 3.5 live win, but did not
  widen the specific selector-override claim because
  `stage35_baseline_differs_from_phasec_score_winner = 0`
- the highest-value next discriminator is therefore one direct bounded
  no-selector / legacy control on the same `p9/c3 seed611` case

Prepared run:

- compare mode:
  `candidate_single_p9_seed611_legacy`
- preset:
  `stage35_baseline_legacy_live_bounded_p9`
- experiment:
  `tune_v63_p9c3_seed611_stage35_baseline_selector_legacy_control_live_bounded_space_map_v1_single_1job`

Config note:

- this uses the same bounded Stage 3.5 budget shape as `v62`
- only the baseline selector is changed back to `legacy`
- that keeps the discriminator narrow and interpretable

### 2026-04-05 v63 completed: seed611 bounded legacy control

Run:

- experiment:
  `tune_v63_p9c3_seed611_stage35_baseline_selector_legacy_control_live_bounded_space_map_v1_single_1job`
- artifact root:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/20260405T020334839969Z__bench_solve_pipeline_no_wli__37dc435/`

Outcome:

- full job wallclock `13651.68s`
- final `best_stage = stage35_substitution_only`
- final `best_match_ratio = 0.635`
- final `best_score = 0.2515235002311922`
- Stage 3.5 accepted and completed:
  - `stage35_runtime_seconds = 1186.83`
  - `stage35_evals = 1300`
  - `stage35_best_candidate_hash = 4bba54177206dd7f`

Direct comparison against `v62`:

- same final `best_match_ratio = 0.635`
- same baseline candidate hash `fe7a4d2798b221e4`
- same baseline source `phaseB_topk`
- same Stage 3.5 best candidate hash `4bba54177206dd7f`
- same `1300` evals and `1` round
- only a small runtime difference:
  - `v62` Stage 3.5 runtime `1227.11s`
  - `v63` Stage 3.5 runtime `1186.83s`

Interpretation:

- selector choice did not matter on `seed611`
- `seed611` is therefore a bounded late-lane success, not a selector-sensitive
  success like `seed411`
- this broadens evidence for bounded Stage 3.5 utility on hard seeds
- it does **not** broaden the specific selector-override claim beyond the
  `411` family

Fresh analysis refresh:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260405T071758Z__space_map_v1_atlas/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260405T071758Z__space_map_v1_audit/`

Programme effect:

- the selector-generality discriminator on `seed611` is now closed
- the highest-value next live science question is taxonomy beyond `411` and
  `611`, not another selector-vs-legacy contrast on `seed611`

### 2026-04-05 stage35_seed reviewer-summary semantics tightened

Problem:

- `stage35_seed` reviewer-facing pool summaries were easy to misread because
  the strict `selected_row_count` field did not always reflect the actual
  late-lane started-versus-available story
- the useful continuation evidence was already present in
  `next_stage_started_count`, but not surfaced as the primary reviewer-facing
  count

Fix:

- `space_map_v1.pool_summaries` now carry explicit reviewer-facing fields:
  - `review_primary_row_count`
  - `review_primary_row_count_kind`
  - `review_primary_relation`
- for most boundaries, these remain:
  - `review_primary_row_count_kind = selected_row_count`
  - `review_primary_relation = selected_vs_available`
- for `stage35_seed`, they now become:
  - `review_primary_row_count_kind = next_stage_started_count`
  - `review_primary_relation = started_vs_available`

Interpretation rule:

- keep `selected_row_count` strict
- use the new reviewer-facing primary-count fields when writing late-pool
  summaries for `stage35_seed`

Fresh analysis refresh after this semantics change:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260405T175711Z__space_map_v1_atlas/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260405T175711Z__space_map_v1_audit/`

### 2026-04-05 v64 prepared: third hard-seed taxonomy sample

Prepared run:

- compare mode:
  `candidate_single_p9_seed711`
- preset:
  `stage35_baseline_score_plus_novelty_live_bounded_p9`
- experiment:
  `tune_v64_p9c3_seed711_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`

Reason:

- `seed411` is the selector-sensitive override case
- `seed611` is the selector-neutral bounded late-lane case
- the next high-value question is whether a third hard seed resembles either
  one or forms a third distinct shape

### 2026-04-05 v65 prepared: one-shot post-v64 hard-seed follow-up

Prepared run:

- compare mode:
  `candidate_single_p9_seed811`
- preset:
  `stage35_baseline_score_plus_novelty_live_bounded_p9`
- experiment:
  `tune_v65_p9c3_seed811_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`

Operational rule:

- `v65` should start only if `v64` completes cleanly
- watcher script:
  `planning/projects/no_wli/60_launch_scripts/no_wli_v64_watch_and_launch_v65_2026-04-05.ps1`
- launch script:
  `planning/projects/no_wli/60_launch_scripts/no_wli_v65_launch_seed811_2026-04-05.ps1`
- no auto-chain beyond `v65`

### 2026-04-06 v66 prepared: one-shot post-v65 hard-seed follow-up

Prepared run:

- compare mode:
  `candidate_single_p9_seed911`
- preset:
  `stage35_baseline_score_plus_novelty_live_bounded_p9`
- experiment:
  `tune_v66_p9c3_seed911_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`

Operational rule:

- `v66` should start only if `v65` completes cleanly
- watcher script:
  `planning/projects/no_wli/60_launch_scripts/no_wli_v65_watch_and_launch_v66_2026-04-05.ps1`
- launch script:
  `planning/projects/no_wli/60_launch_scripts/no_wli_v66_launch_seed911_2026-04-05.ps1`
- no auto-chain beyond `v66`

### 2026-04-05 v64 watcher result: clean completion, v65 launched

- watcher log:
  - planning/projects/no_wli/50_console_and_watch_logs/no_wli_v64_watch_and_launch_v65_2026-04-05.log
- completed_jobs = 1
- planned_job_count = 1
- remaining_jobs = 0
- stopped_early = 0
- next run:
  - tune_v65_p9c3_seed811_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job
- launch script:
  - planning/projects/no_wli/60_launch_scripts/no_wli_v65_launch_seed811_2026-04-05.ps1

Scope note:

- this is a one-shot v64 -> v65 handoff only
- no auto-chain beyond v65

### 2026-04-05 v64 watcher result: clean completion, v65 launched

- watcher log:
  - planning/projects/no_wli/50_console_and_watch_logs/no_wli_v64_watch_and_launch_v65_2026-04-05.log
- completed_jobs = 1
- planned_job_count = 1
- remaining_jobs = 0
- stopped_early = 0
- next run:
  - tune_v65_p9c3_seed811_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job
- launch script:
  - planning/projects/no_wli/60_launch_scripts/no_wli_v65_launch_seed811_2026-04-05.ps1

Scope note:

- this is a one-shot v64 -> v65 handoff only
- no auto-chain beyond v65

### 2026-04-05 v65 watcher result: clean completion, v66 launched

- watcher log:
  - planning/projects/no_wli/50_console_and_watch_logs/no_wli_v65_watch_and_launch_v66_2026-04-05.log
- completed_jobs = 1
- planned_job_count = 1
- remaining_jobs = 0
- stopped_early = 0
- next run:
  - tune_v66_p9c3_seed911_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job
- launch script:
  - planning/projects/no_wli/60_launch_scripts/no_wli_v66_launch_seed911_2026-04-05.ps1

Scope note:

- this is a one-shot v65 -> v66 handoff only
- no auto-chain beyond v66

### 2026-04-06 v64 completed: third hard-seed taxonomy sample

Run:

- experiment:
  `tune_v64_p9c3_seed711_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`
- artifact root:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/20260405T180042640894Z__bench_solve_pipeline_no_wli__37dc435/`

Outcome:

- full job wallclock `19933.35s`
- final `best_stage = stage35_substitution_only`
- final `best_match_ratio = 0.761`
- Stage 3.5 accepted and completed:
  - `stage35_accept_reason = accepted`
  - `stage35_runtime_seconds = 1500.86`
  - `stage35_evals = 1062`
  - `stage35_best_candidate_hash = 0afd5ec3d0f8c51a`
- baseline stayed on the Phase C score winner:
  - `stage35_baseline_candidate_hash = fbf3708f524de0bf`
  - `stage35_baseline_candidate_source = phaseB_topk`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`

Interpretation:

- `seed711` looks closer to `seed611` than to `seed411`
- this is a second selector-neutral bounded Stage 3.5 hard-seed win
- bounded Stage 3.5 utility is now broader than a single fresh hard seed beyond
  `411`

Fresh map read:

- refreshed atlas outputs:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260406T053854Z__space_map_v1_atlas/`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260406T053854Z__space_map_v1_audit/`
- `phaseC_start`:
  - `row_count = 6`
  - `family_count = 2`
  - `largest_family_share = 0.8333`
- `stage35_seed`:
  - `row_count = 6`
  - `family_count = 1`
  - `review_primary_relation = started_vs_available`
- `stage35_archive`:
  - `family_count = 1`

Map interpretation:

- by the time `seed711` enters Stage 3.5, the late frontier is already
  concentrated into one dominant continuation family
- that reinforces the similarity to `seed611`, which also did not need a
  selector override to win

### 2026-04-06 v65 completed: fourth hard-seed taxonomy sample

Run:

- experiment:
  `tune_v65_p9c3_seed811_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`
- artifact root:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/20260405T233329083455Z__bench_solve_pipeline_no_wli__37dc435/`

Outcome:

- full job wallclock `15582.03s`
- final `best_stage = stage3_full_refine`
- final `best_match_ratio = 0.475`
- Stage 3.5 completed but rejected:
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_runtime_seconds = 5052.13`
  - `stage35_evals = 3812`
  - `stage35_best_candidate_hash = 82e5ab842699e5c2`
- selector override still fired:
  - `stage35_baseline_candidate_hash = 9f03e7a2f593df81`
  - `stage35_baseline_candidate_source = phaseA_selected`
  - `stage35_baseline_differs_from_phasec_score_winner = 1`

Interpretation:

- `seed811` is the first fresh post-`411` case where selector-sensitive late
  divergence recurs but still does not produce a Stage 3.5 win
- that makes it a useful contrast family, not a failure of the entire bounded
  late lane
- the emerging hard-seed taxonomy is now at least:
  - override-sensitive win (`411`)
  - selector-neutral bounded late win (`611`, `711`)
  - override-sensitive reject / no-lift (`811`)

Fresh map read:

- refreshed atlas outputs:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260406T053854Z__space_map_v1_atlas/`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260406T053854Z__space_map_v1_audit/`
- `phaseC_start`:
  - `row_count = 6`
  - `family_count = 6`
  - `largest_family_share = 0.1667`
- `stage35_seed`:
  - `row_count = 6`
  - `family_count = 2`
  - `largest_family_share = 0.8333`
  - `review_primary_relation = started_vs_available`
- `stage35_archive`:
  - `family_count = 1`

Map interpretation:

- unlike `seed711`, `seed811` enters late continuation from a much wider
  six-family Phase C start pool
- the late pool then compresses aggressively, but that compression does not
  convert into an accepted Stage 3.5 continuation
- that makes `seed811` a useful false-friend / unstable-override contrast case

### 2026-04-06 v67 prepared: one-shot post-v66 hard-seed follow-up

Prepared run:

- compare mode:
  `candidate_single_p9_seed1011`
- preset:
  `stage35_baseline_score_plus_novelty_live_bounded_p9`
- experiment:
  `tune_v67_p9c3_seed1011_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`

Operational rule:

- `v67` should start only if `v66` completes cleanly
- no auto-chain beyond `v67`

Watcher armed:

- watcher script:
  `planning/projects/no_wli/60_launch_scripts/no_wli_v66_watch_and_launch_v67_2026-04-06.ps1`
- watcher log:
  `planning/projects/no_wli/50_console_and_watch_logs/no_wli_v66_watch_and_launch_v67_2026-04-06.log`

### 2026-04-06 v66 watcher result: clean completion, v67 launched

- watcher log:
  - planning/projects/no_wli/50_console_and_watch_logs/no_wli_v66_watch_and_launch_v67_2026-04-06.log
- completed_jobs = 1
- planned_job_count = 1
- remaining_jobs = 0
- stopped_early = 0
- next run:
  - tune_v67_p9c3_seed1011_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job
- launch script:
  - planning/projects/no_wli/60_launch_scripts/no_wli_v67_launch_seed1011_2026-04-06.ps1

Scope note:

- this is a one-shot v66 -> v67 handoff only
- no auto-chain beyond v67

### 2026-04-06 v66 completed: fifth hard-seed taxonomy sample

Run:

- experiment:
  `tune_v66_p9c3_seed911_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`
- artifact root:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/20260406T035330001693Z__bench_solve_pipeline_no_wli__37dc435/`

Outcome:

- full job wallclock `11728.51s`
- final `best_stage = stage2_search`
- final `best_match_ratio = 0.176`
- Stage 3.5 completed but rejected:
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_runtime_seconds = 1189.36`
  - `stage35_evals = 1225`
  - `stage35_best_candidate_hash = 0414298ec5a81157`
- selector override did **not** fire:
  - `stage35_baseline_candidate_hash = 4542626236953375`
  - `stage35_baseline_candidate_source = phaseB_topk`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`

Interpretation:

- `seed911` is a useful hard negative
- unlike `seed811`, it does not need a selector override to become a reject
- this strengthens the reading that there is more than one reject shape in the
  hard-seed space

Fresh map read:

- refreshed atlas outputs:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260406T144043Z__space_map_v1_atlas/`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260406T144043Z__space_map_v1_audit/`
- `phaseC_start`:
  - `row_count = 6`
  - `family_count = 6`
  - `largest_family_share = 0.1667`
- `stage35_seed`:
  - `row_count = 6`
  - `family_count = 2`
  - `largest_family_share = 0.8333`
  - `review_primary_relation = started_vs_available`
- `stage35_archive`:
  - `family_count = 1`

Map interpretation:

- like `seed811`, `seed911` reaches Stage 3.5 from a wide six-family Phase C
  start pool and then compresses late without converting into an accepted
  continuation
- unlike `seed811`, that path stays selector-neutral

### 2026-04-06 v67 completed: sixth hard-seed taxonomy sample

Run:

- experiment:
  `tune_v67_p9c3_seed1011_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`
- artifact root:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/20260406T070921069771Z__bench_solve_pipeline_no_wli__37dc435/`

Outcome:

- full job wallclock `9582.25s`
- final `best_stage = stage35_substitution_only`
- final `best_match_ratio = 0.737`
- Stage 3.5 accepted and completed:
  - `stage35_accept_reason = accepted`
  - `stage35_runtime_seconds = 909.49`
  - `stage35_evals = 1212`
  - `stage35_best_candidate_hash = aa2bb5f45e506142`
- selector override did **not** fire:
  - `stage35_baseline_candidate_hash = 327ffa7413117b35`
  - `stage35_baseline_candidate_source = phaseB_topk`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`

Interpretation:

- `seed1011` reinforces the selector-neutral bounded late-win pattern already
  seen on `seed611` and `seed711`
- bounded Stage 3.5 utility is now supported on multiple fresh hard seeds even
  without selector override

Fresh map read:

- refreshed atlas outputs:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260406T144043Z__space_map_v1_atlas/`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260406T144043Z__space_map_v1_audit/`
- `phaseC_start`:
  - `row_count = 6`
  - `family_count = 3`
  - `largest_family_share = 0.6667`
- `stage35_seed`:
  - `row_count = 6`
  - `family_count = 1`
  - `largest_family_share = 1.0`
  - `review_primary_relation = started_vs_available`
- `stage35_archive`:
  - `family_count = 1`

Map interpretation:

- `seed1011` reaches late continuation with more diversity than `seed711`, but
  still compresses to one dominant Stage 3.5 seed family before accepting
- that makes it a useful bridge case between the very concentrated `seed711`
  shape and the broader `seed611` win

### 2026-04-06 `score_stop_shadow_v2` first tiny family-panel readout

Code/docs updated:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/SPEC.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/EXPERIMENT_PLAN.md`
- `tests/tools/test_no_wli_score_stop_shadow_v2.py`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_score_stop_shadow_v2.py -q`
- result:
  - `10 passed`

Run:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260406T151959Z__score_stop_shadow_v2/`

Panel:

- solved control: `p5/c1 seed511`
- selector-sensitive hard win: `p9/c3 seed411`
- selector-neutral hard win: `p9/c3 seed1011`
- selector-sensitive reject / no-lift: `p9/c3 seed811`
- selector-neutral reject / no-lift: `p9/c3 seed911`

Top readout:

- analyzed runs: `5`
- analyzed rows: `52`
- only one dump rule fired:
  - `trust0.30_xent24.00_margin0.00_support1`
- that rule fired on:
  - solved control `seed511`
  - selector-neutral hard win `seed1011`
- it did **not** fire on:
  - selector-sensitive hard win `seed411`
  - selector-sensitive reject `seed811`
  - selector-neutral reject `seed911`
- no shadow stop fired on any run
- no replay data-gap flags were raised on this modern panel

Row-level contrast:

- `seed411` best late rows stayed at very low trust:
  - top `phaseC_start` / `stage35_seed` challenger rows around
    `replay_word_ngram_trust_score ~= 0.083`
  - `replay_word_ngram_report_xent ~= 20.0`
- `seed1011` winning late rows reached:
  - `replay_word_ngram_trust_score ~= 0.321`
  - `replay_word_ngram_report_xent ~= 17.498`
- `seed811` reject rows came close on trust but stayed below the current floor:
  - best observed trust around `0.292`
- `seed911` stayed far below the trust floor

Interpretation:

- this first family-aware dump rule is conservative and promising
- it cleanly separates the obvious reject cases on this panel
- but it is **not yet** a general hard-win dump rule because it misses the
  selector-sensitive `411` success
- the current failure mode looks more like a trust/score-axis miss than a
  family-stability miss:
  - `411` never entered a high-trust late region under the current replay
    scorer
  - no stop fired because dump itself only fired on two runs

Maintained next step:

- inspect the `411` miss against the `1011` hit at row level
- refine dump first, not stop
- keep stop shadow-only and stricter than dump

### 2026-04-06 `score_stop_shadow_v2` miss-analysis hardening

Code/docs updated:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/SPEC.md`
- `tests/tools/test_no_wli_score_stop_shadow_v2.py`

What changed:

- non-firing rows now persist base diagnostic fields instead of dropping them:
  - `shadow_best_rival_family_margin`
  - `shadow_family_support_count`
  - `shadow_anchor_margin`
  - base threshold fields
  - pass/fail flags
  - `shadow_diag_blockers`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_score_stop_shadow_v2.py -q`
- result:
  - `11 passed`

Rerun:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260406T155658Z__score_stop_shadow_v2/`

Sharper blocker read:

- `seed411` top late rows:
  - trust about `0.083`
  - xent about `20.0`
  - positive rival-family margin (`0.017` to `0.025`)
  - `shadow_family_support_count = 0`
  - blockers:
    - `trust_below_floor`
    - `family_support_below_floor`
- `seed1011` winning late row:
  - trust about `0.321`
  - xent about `17.498`
  - `shadow_family_support_count = 1`
  - no blockers
- `seed811` best reject rows:
  - trust about `0.292`
  - xent about `20.0`
  - positive rival-family margin (`0.058` to `0.061`)
  - `shadow_family_support_count = 0`
  - blockers:
    - `trust_below_floor`
    - `family_support_below_floor`

Interpretation:

- the `411` miss is now clearer:
  - it is not failing because of a bad rival-family margin
  - it is failing because it never becomes a high-trust, supported family under
    the current replay scorer
- this also means a simple trust-floor reduction is probably the wrong next
  move:
  - `seed811` already sits much closer to the current trust floor than `411`
  - so lowering trust alone would likely wake a reject before rescuing `411`

Maintained next step:

- refine dump with another non-oracle axis if justified
- do not widen trust alone
- keep stop shadow-only and stricter than dump

### 2026-04-06 `score_stop_shadow_v2` persistence-axis pass

Code/docs updated:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/SPEC.md`
- `tests/tools/test_no_wli_score_stop_shadow_v2.py`

What changed:

- every row now persists late-family persistence diagnostics across:
  - `phaseC_start`
  - `stage35_seed`
  - `stage35_archive`
- saved fields now include:
  - `shadow_late_family_persistence_count`
  - `shadow_late_family_persistence_boundaries`
  - `shadow_late_family_persistence_pass`
  - `shadow_late_family_reaches_archive`
  - `shadow_late_family_first_boundary`
  - `shadow_late_family_last_boundary`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_score_stop_shadow_v2.py -q`
- result:
  - `12 passed`

Rerun:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260406T161448Z__score_stop_shadow_v2/`

Readout:

- simple late-family persistence does **not** solve the `411` miss
- dominant-family persistence is broad:
  - `411`, `811`, `911`, and `1011` all show a family that persists across
    `phaseC_start -> stage35_seed -> stage35_archive`
- non-anchor override-family persistence is also not enough:
  - `411` rescue family `f1` persists across `phaseC_start -> stage35_seed`
  - `811` override family `f1` also persists across `phaseC_start -> stage35_seed`

Interpretation:

- persistence is useful as a diagnostic field
- but a simple persistence rule would not rescue `411` without also waking
  `811`
- this means persistence alone should **not** be the next dump rule
- the next candidate axis should be something narrower, such as a structural
  challenger or continuation-promise signal, rather than a plain persistence
  threshold

### 2026-04-06 `v68` prepared: two fresh hard-seed extension run

Configured next fixture-matrix slice:

- compare mode:
  - `candidate_pair_p9_seed1111_1211`
- experiment:
  - `tune_v68_p9c3_seed1111_1211_stage35_baseline_selector_candidate_live_bounded_space_map_v1_2job`
- jobs:
  - `p9/c3 seed1111`
  - `p9/c3 seed1211`
- preset:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`

Intent:

- collect two more fresh hard-seed artifacts under the same bounded candidate
  Stage 3.5 lane
- extend the hard-seed taxonomy without changing solver semantics
- keep this as data collection only, not a new promotion claim

Verification:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
- result:
  - `21 passed`

### 2026-04-06 `v68` completed: two-seed hard extension readout

Run:

- experiment:
  - `tune_v68_p9c3_seed1111_1211_stage35_baseline_selector_candidate_live_bounded_space_map_v1_2job`
- artifacts:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260406T161236795849Z__bench_solve_pipeline_no_wli__37dc435/`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260406T192204424492Z__bench_solve_pipeline_no_wli__37dc435/`

Outcome summary:

- `seed1111`:
  - `best_stage = stage35_substitution_only`
  - `best_match_ratio = 0.519`
  - `stage35_accept_reason = accepted`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline source `phaseB_topk`
  - `stage35_runtime_seconds = 1135.50`
  - `stage35_evals = 1454`
- `seed1211`:
  - `best_stage = stage3_full_refine`
  - `best_match_ratio = 0.304`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline source `phaseA_selected`
  - `stage35_runtime_seconds = 3449.32`
  - `stage35_evals = 4530`

Refreshed map outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260407T005632Z__space_map_v1_atlas/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260407T005632Z__space_map_v1_audit/`

Late-boundary map read:

- `seed1111`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - `stage35_archive family_count = 1`
  - accepted late win
- `seed1211`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - `stage35_archive family_count = 1`
  - rejected late continuation

Interpretation:

- `seed1111` reinforces the selector-neutral bounded late-win family
- but it also shows that coarse late family-count compression alone is not
  enough to explain win versus reject:
  - `seed1111` and `seed911` both look like `6 -> 2 -> 1` at the late family
    counts, but `1111` accepts and `911` rejects
- `seed1211` broadens the reject side:
  - it is selector-neutral like `911`
  - but unlike `911`, its baseline winner comes from `phaseA_selected`
  - so it may be a distinct phaseA-led reject subshape rather than just a
    repeat of the phaseB-led `911` negative

Maintained programme read:

- bounded Stage 3.5 utility is broader than `411`
- selector override is still only clearly causal on `411`
- the hard-seed taxonomy now has at least:
  - selector-sensitive win
  - selector-neutral bounded late win
  - selector-sensitive reject / no-lift
  - selector-neutral reject / no-lift
- and `1211` may justify a fifth reject subshape if it repeats

### 2026-04-07 eight-seed panel cross-check and reviewer summary

Cross-check:

- the finished eight-seed panel now supports a stable taxonomy read:
  - selector-sensitive win (`411`)
  - selector-neutral bounded late wins (`611`, `711`, `1011`, `1111`)
  - selector-sensitive reject / no-lift (`811`)
  - selector-neutral reject / no-lift (`911`)
  - selector-neutral reject / no-lift with `phaseA_selected` baseline
    (`1211`, provisional as a distinct subtype)
- bounded Stage 3.5 utility clearly broadened again
- selector generality still did not broaden beyond `411`
- coarse late family-count compression alone is still not enough to explain
  outcome:
  - `1111` and `911` both look broadly like `6 -> 2 -> 1`
  - but `1111` accepts and `911` rejects

Reviewer-facing summary written:

- `planning/projects/no_wli/40_review_summaries/no_wli_eight_seed_panel_review_summary_2026-04-07.md`

Maintained next step:

- keep the atlas/taxonomy panel as the main review set
- use `score_stop_shadow_v2` as the focused next slice
- do not reopen live seed collection until the next dump-gate read is sharper

### 2026-04-07 `score_stop_shadow_v2` archive-uplift dump pass

Code/docs updated:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/SPEC.md`
- `tests/tools/test_no_wli_score_stop_shadow_v2.py`

What changed:

- kept the existing trust-led dump rule
- added a second offline dump axis for the tiny family panel only:
  - `archive_search_uplift0.15`
- this new rule only fires at `stage35_archive`
- it measures same-family search-score uplift versus the family's
  `phaseC_start` baseline
- it is dump-only and does not affect shadow stop

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_score_stop_shadow_v2.py -q`
- result:
  - `15 passed`

Rerun:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260407T011029Z__score_stop_shadow_v2/`

Readout:

- trust-led dump still fires on:
  - solved control `seed511`
  - selector-neutral hard win `seed1011`
- new archive-uplift fallback now also fires on:
  - selector-sensitive hard win `seed411`
- dump still does **not** fire on:
  - selector-sensitive reject `seed811`
  - selector-neutral reject `seed911`
- no shadow stop fires

Important detail:

- `411` rescue now looks detectable without lowering trust:
  - archive family `f0`
  - same-family search uplift from `phaseC_start` to `stage35_archive`
    about `+0.234`
  - trust still low (`~0.06`)
- `1011` remains a cleaner high-trust late win:
  - trust about `0.321`
  - archive search uplift near zero / slightly negative
  - so it is still mainly explained by the trust-led rule
- `811` and `911` remain quiet:
  - no archive-uplift trigger
  - no stop trigger

Interpretation:

- this is the first useful non-oracle rescue-style dump axis beyond raw trust
- it helps `411` without waking the current reject cases
- but it is intentionally narrow:
  - archive-only
  - dump-only
  - still unverified beyond the five-case panel

Maintained next step:

- do not reopen live seed collection yet
- check the new archive-uplift dump axis on the broader existing hard panel
- only then decide whether the stop science is ready for a wider offline sweep

Broader existing hard-panel check (no new live runs):

- checked seeds:
  - `411`
  - `611`
  - `711`
  - `811`
  - `911`
  - `1011`
  - `1111`
  - `1211`
- result:
  - dump fires on wins:
    - `411` via `archive_search_uplift0.15`
    - `611` via trust-led dump
    - `711` via trust-led dump
    - `1011` via trust-led dump
  - dump stays quiet on rejects:
    - `811`
    - `911`
    - `1211`
  - accepted win `1111` still misses

Interpretation:

- this is now stronger than the tiny-panel read:
  - the current dump layer catches `4/5` mapped hard wins
  - and `0/3` mapped hard rejects
- the next clear stop-science question is no longer `411`
- it is `1111`:
  - why does that accepted win still sit outside the current dump layer?

`1111` row-level comparison versus caught selector-neutral wins:

- compared against `611`, `711`, and `1011`, the `1111` late winning family
  stays weak on all currently-used dump axes:
  - best late trust only about `0.167`
  - xent stays at `20.0`
  - family support stays `0`
  - archive same-family search uplift is negative:
    - about `-0.038`
- by contrast:
  - `611` trust about `0.35` with positive support and mild positive uplift
  - `711` trust about `0.333` with positive support
  - `1011` trust about `0.321`

Interpretation:

- `1111` is not a near-threshold false negative like the old `411` miss
- it is a different accepted-win shape that the current non-oracle dump layer
  does not know how to see yet
- so the next widening should only happen if a genuinely new axis can explain
  `1111` without waking the reject set

Quick structural / continuation read:

- no clean structural-challenger signal emerged
- no clean continuation-promise signal emerged for the winning family:
  - the winning `1111` family has negative archive search uplift
  - the strongest positive uplift belongs to a lower-truth family that does not
    convert

Reviewer-prep conclusion:

- the only clearly plausible next candidate from the current numbers is a
  narrow archive full-score branch
- but that is close enough to a raw-score-like axis that it should be reviewed
  before implementation

Reviewer-prep summary written:

- `planning/projects/no_wli/40_review_summaries/no_wli_external_review_prep_summary_2026-04-07.md`

### 2026-04-07 score_stop_shadow_v2 harness expanded from five-case to solved-control-plus-eight-hard-seed panel

The stop harness is now evidence-cleaner.

Changed:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
  - expanded `FAMILY_PANEL_TARGETS` to:
    - solved control `511`
    - hard seeds `411`, `611`, `711`, `811`, `911`, `1011`, `1111`, `1211`
  - tightened target matching with:
    - `require_best_stage`
    - `require_baseline_source`
- `tests/tools/test_no_wli_score_stop_shadow_v2.py`
  - locked the default target seed set
  - added target-matching coverage for best-stage and baseline-source filters

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_score_stop_shadow_v2.py -q`
  - `17 passed`

Rerun:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260407T023505Z__score_stop_shadow_v2/`

Harness-backed readout:

- analyzed runs: `9`
- dump fires on:
  - solved control `511`
  - selector-sensitive hard win `411`
  - selector-neutral hard wins `611`, `711`, `1011`
- dump stays quiet on:
  - selector-sensitive reject `811`
  - selector-neutral rejects `911`, `1211`
- accepted hard win `1111` still misses
- no shadow stop fires

Rule split:

- `trust0.30_xent24.00_margin0.00_support1`
  - `4` runs
  - solved controls: `1`
  - Stage 3.5 live wins: `3`
- `archive_search_uplift0.15`
  - `1` run
  - Stage 3.5 live wins: `1`

Interpretation:

- the broader stop claim is now harness-backed rather than partly manual
- the dump layer is meaningfully better than the earlier five-case read:
  - it covers `411`, `611`, `711`, and `1011`
  - it still stays quiet on the mapped reject set
- `1111` remains the clear discriminator miss
- no live stop policy change is justified

Follow-up:

- update the stop docs to separate:
  - harness-backed result
  - possible future dump-axis ideas
- prepare the next external review from the harness-backed panel, not the older
  mixed manual read

### 2026-04-07 `v69` launched: three fresh hard seeds for post-eight-seed map widening

Purpose:

- collect three more unique bounded Stage 3.5 hard-seed artifacts before
  revisiting the next taxonomy update:
  - `seed1311`
  - `seed1411`
  - `seed1511`

Config:

- compare mode:
  - `candidate_triple_p9_seed1311_1411_1511`
- experiment id:
  - `tune_v69_p9c3_seed1311_1411_1511_stage35_baseline_selector_candidate_live_bounded_space_map_v1_3job`
- preset:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- cap:
  - `MAX_JOBS = 3`
  - `MAX_WALLCLOCK_SECONDS = 12h`

Files changed:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`
- `planning/projects/no_wli/00_CURRENT_STATE.md`
- `planning/projects/no_wli/01_EXPERIMENT_INDEX.md`
- `planning/projects/no_wli/04_ACTIVE_RUNBOOK.md`
- `planning/projects/no_wli/60_launch_scripts/no_wli_v69_launch_seed1311_1411_1511_2026-04-07.cmd`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `21 passed`
- `C:\Python\Python311\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

Launch:

- launched under `cmd.exe`
- launcher:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_v69_launch_seed1311_1411_1511_2026-04-07.cmd`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_v69_seed1311_1411_1511_console_2026-04-07.log`

Startup confirmation:

- process alive after launch
- state file created:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v69_p9c3_seed1311_1411_1511_stage35_baseline_selector_candidate_live_bounded_space_map_v1_3job.json`
- events file created:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v69_p9c3_seed1311_1411_1511_stage35_baseline_selector_candidate_live_bounded_space_map_v1_3job.jsonl`
- first job started cleanly:
  - `p9/c3 seed1311`

### 2026-04-07 `v69` completed: three-seed hard extension plus fresh atlas / stop cross-check

`v69` finished all three jobs cleanly.

State:

- experiment:
  - `tune_v69_p9c3_seed1311_1411_1511_stage35_baseline_selector_candidate_live_bounded_space_map_v1_3job`
- completed jobs:
  - `3 / 3`
- no active `run_fixture_matrix.py` worker remains

Core seed results:

- `seed1311`
  - `best_stage = stage3_full_refine`
  - `best_match_ratio = 0.570`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline source = `phaseB_topk`
  - `stage35_best_match = 0.576`
- `seed1411`
  - `best_stage = stage3_full_refine`
  - `best_match_ratio = 0.264`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline source = `phaseA_selected`
  - `stage35_best_match = 0.264`
- `seed1511`
  - `best_stage = stage3_full_refine`
  - `best_match_ratio = 0.583`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline source = `phaseB_topk`
  - `stage35_best_match = 0.598`

Interpretation:

- all three new seeds widen the reject side, not the win side
- `seed1411` looks like a second current-code repeat of the selector-neutral
  `phaseA_selected` reject subtype first seen on `1211`
- `seed1311` and `seed1511` look like a new selector-neutral `phaseB_topk`
  moderate-truth reject subtype:
  - both reject after bounded Stage 3.5
  - both find slightly stronger internal Stage 3.5 rows
  - neither converts to an accepted late win

Fresh atlas / audit recompute:

- atlas:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260407T235219Z__space_map_v1_atlas/`
- audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260407T235219Z__space_map_v1_audit/`

Atlas summary read:

- artifacts scanned:
  - `380`
- row atlas rows:
  - `4506`
- pool atlas rows:
  - `129`
- transition atlas rows:
  - `2380`
- run type counts:
  - `solved_control = 53`
  - `stage35_guard_reject = 12`
  - `stage35_live_win = 9`

Useful pool reads on the new seeds:

- `seed1311`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
- `seed1411`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
- `seed1511`
  - `phaseC_start family_count = 2`
  - `stage35_seed family_count = 1`

Interpretation:

- coarse late family-count compression still does not explain the outcome by
  itself:
  - `seed1511` compresses as hard as some wins, yet still rejects

Stop cross-check using the current `score_stop_shadow_v2` logic on the three
new artifacts:

- `seed1311`
  - `shadow_rule_id = trust0.30_xent24.00_margin0.00_support1`
  - `would_dump = 1`
- `seed1411`
  - `shadow_rule_id = archive_search_uplift0.15`
  - `would_dump = 1`
- `seed1511`
  - `shadow_rule_id = ''`
  - `would_dump = 0`

Interpretation:

- the locked harness-backed stop result remains valid on its target set
- but the current dump layer does **not** generalize cleanly to the widened
  fresh-seed panel
- this is the first clear broader false-positive pressure against:
  - the trust-led branch (`seed1311`)
  - the archive-uplift rescue branch (`seed1411`)
- so stop science remains firmly:
  - offline-only
  - dump-calibration only
  - not ready for any policy-style promotion

Follow-up completed:

- current-state / runbook / experiment index updated to the eleven-seed
  taxonomy
- fresh review summaries written:
  - `planning/projects/no_wli/40_review_summaries/no_wli_eleven_seed_panel_review_summary_2026-04-07.md`
  - `planning/projects/no_wli/40_review_summaries/no_wli_external_review_prep_summary_2026-04-07.md`

Current recommendation:

- take external review before widening the stop harness again or adding another
  dump axis

### 2026-04-07 post-review direction: formalize core versus pressure stop panels

The next stop-science step should not be "just widen the locked harness."

Instead:

- keep the current nine-run set frozen as the core benchmark panel
- formalize `1311`, `1411`, and `1511` as a separate frozen pressure panel
- then do the no-drift transparency hardening pass on top of that split

Why:

- it preserves continuity on the core benchmark
- it makes falsification pressure first-class rather than a planning side note
- it avoids benchmark drift every time a fresh seed appears

Implementation target:

- `planning/projects/no_wli/20_active_plans/no_wli_score_stop_core_pressure_transparency_plan_2026-04-07.md`

### 2026-04-08 score_stop_shadow_v2 core/pressure split implemented

Implemented the first structural stop-harness refactor:

- split the old implicit family panel into:
  - frozen core benchmark panel
  - frozen pressure falsification panel
- threaded panel metadata through row/run outputs:
  - `target_panel_name`
  - `target_panel_role`
  - `target_label`
  - `target_order`
- kept the actual gate logic unchanged
- updated `summary.md` to report:
  - core benchmark panel
  - pressure falsification panel
  - combined caution note

Code/tests:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- `tests/tools/test_no_wli_score_stop_shadow_v2.py`

Validation:

- `tests/tools/test_no_wli_score_stop_shadow_v2.py`
  - `23 passed`
- `py_compile` clean

Fresh extractor output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T020004Z__score_stop_shadow_v2/`

Readout from the new split:

- core panel:
  - dumps on `511`, `411`, `611`, `711`, `1011`
  - stays quiet on `811`, `911`, `1111`, `1211`
- pressure panel:
  - `1311` still dumps under the trust-led branch
  - `1411` still dumps under the archive-uplift branch
  - `1511` stays quiet

Interpretation:

- the new structure fixes evidence hygiene
- it does **not** improve stop generalization by itself
- next step remains the no-drift transparency pass on top of this split

### 2026-04-08 score_stop_shadow_v2 first no-drift helper layer landed

Implemented the first low-risk transparency slice on top of the core/pressure
split:

- explicit dump-rule iterator
- explicit continuation-rule iterator
- signed margin helpers
- explicit no-drift test for first-hit rule ordering

What did **not** change:

- threshold tuples
- dump/stop semantics
- first-hit rule selection order
- core panel verdicts
- pressure panel verdicts

Validation:

- `tests/tools/test_no_wli_score_stop_shadow_v2.py`
  - `27 passed`
- `py_compile` clean

Fresh extractor output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T020632Z__score_stop_shadow_v2/`

Readout:

- core panel still shows:
  - dumps on `511`, `411`, `611`, `711`, `1011`
  - quiet on `811`, `911`, `1111`, `1211`
- pressure panel still shows:
  - `1311` dump under trust
  - `1411` dump under archive uplift
  - `1511` quiet

Interpretation:

- no-drift helper extraction succeeded
- evidence split remains clean
- next step is still:
  - explicit gate evaluation helpers
  - threshold matrix rows
  - nearest-pass diagnostics

### 2026-04-08 score_stop_shadow_v2 explicit evaluation and matrix outputs landed

Implemented the next transparency slice on top of the core/pressure split:

- explicit dump-rule evaluation helper
- explicit continuation-rule evaluation helper
- threshold-matrix row builder
- nearest-pass picker
- public gate-margin export
- threshold-matrix summary export

Code/tests:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- `tests/tools/test_no_wli_score_stop_shadow_v2.py`

Validation:

- `tests/tools/test_no_wli_score_stop_shadow_v2.py`
  - `31 passed`
- `py_compile` clean

Fresh extractor output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T024804Z__score_stop_shadow_v2/`

New outputs now present:

- `threshold_matrix_rows.jsonl`
- `threshold_matrix_summary.json`
- `gate_margin_rows.jsonl`

Readout:

- core panel verdicts unchanged:
  - dumps on `511`, `411`, `611`, `711`, `1011`
  - quiet on `811`, `911`, `1111`, `1211`
- pressure panel verdicts unchanged:
  - `1311` trust-led false positive
  - `1411` archive-uplift false positive
  - `1511` quiet

Interpretation:

- transparency improved without verdict drift
- the stop project is now much easier to inspect row-by-row
- the next question is explanatory, not structural:
  - why exactly `1111` misses
  - why exactly `1311` and `1411` false-fire

### 2026-04-08 score_stop_shadow_v2 case explanation layer landed

Implemented the explanation-only pass on top of the frozen core/pressure
panels and the already-landed transparency outputs.

Code/tests:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- `tests/tools/test_no_wli_score_stop_shadow_v2.py`

What landed:

- fixed case-study seed contract:
  - `1111`
  - `1311`
  - `1411`
- deterministic selectors for:
  - best truth row
  - best trust row
  - best uplift row
  - best archive uplift row
  - current firing row
- new outputs:
  - `case_explanations.jsonl`
  - `case_explanation_summary.json`
  - `case_explanations.md`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_score_stop_shadow_v2.py -q`
  - `42 passed`
- `C:\Python\Python311\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py tests/tools/test_no_wli_score_stop_shadow_v2.py`
  - clean
- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T041415Z__score_stop_shadow_v2/`

Readout:

- core panel verdicts stayed unchanged:
  - dumps:
    - `511`
    - `411`
    - `611`
    - `711`
    - `1011`
  - quiet:
    - `811`
    - `911`
    - `1111`
    - `1211`
- pressure panel verdicts stayed unchanged:
  - `1311`
    - trust false-fire
  - `1411`
    - archive-uplift false-fire
  - `1511`
    - quiet

Case explanations from the new bundle:

- `1111`
  - `accepted_miss_outside_current_model`
  - best truth stays on the late winning family
  - but that family is neither trust-led nor archive-rescue-led under the
    current non-oracle axes
- `1311`
  - `trust_false_fire`
  - current trust-led dump still admits a reject-side seed under pressure
- `1411`
  - `archive_false_fire`
  - current archive fallback can prefer a lower-truth archive row while the
    best-truth row sits elsewhere

Interpretation:

- this pass improved explanation quality without changing behaviour
- the stop project is now in a better review state
- but it still remains:
  - offline only
  - dump-led
  - not a stop-policy benchmark
- next step should be external review of the new explanation bundle before any
  new dump-axis work

### 2026-04-08 score_stop_shadow_v2 nearest-pass contract cleanup

Applied one tiny clarity fix to the stop harness without changing verdicts.

Code/tests:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- `tests/tools/test_no_wli_score_stop_shadow_v2.py`

What changed:

- kept the existing nearest-pass selection logic unchanged
- clarified the public output contract:
  - `shadow_nearest_pass_margin` is now genuinely signed
  - `shadow_nearest_pass_deficit` is now exported as the positive failure
    amount
- `case_explanations.md` now prints:
  - `signed_margin`
  - `deficit`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_score_stop_shadow_v2.py -q`
  - `43 passed`
- `C:\Python\Python311\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py tests/tools/test_no_wli_score_stop_shadow_v2.py`
  - clean
- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T142942Z__score_stop_shadow_v2/`

Readout:

- core panel verdicts unchanged
- pressure panel verdicts unchanged
- explanation labels unchanged:
  - `1111`
    - `accepted_miss_outside_current_model`
  - `1311`
    - `trust_false_fire`
  - `1411`
    - `archive_false_fire`

Interpretation:

- this was the right final stop-harness cleanup for now
- it improves interpretability without creating more stop-side churn

### 2026-04-08 late_family_quality_v1 first frozen-bundle family-level read

Built a new offline-only family-level study branch on top of the frozen
`score_stop_shadow_v2` bundle rather than mutating the stop harness again.

Files added:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/SPEC.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/EXPERIMENT_PLAN.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/__init__.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/extract_late_family_quality_v1.py`
- `tests/tools/test_no_wli_late_family_quality_v1.py`

Frozen input contract:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T041415Z__score_stop_shadow_v2/`
- exact study seeds:
  - `1111`
  - `1311`
  - `1411`
  - `411`
  - `611`
  - `1011`
- fixed late boundaries:
  - `phaseC_start`
  - `stage35_seed`
  - `stage35_archive`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_family_quality_v1.py -q`
  - `19 passed`
- `C:\Python\Python311\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/extract_late_family_quality_v1.py tests/tools/test_no_wli_late_family_quality_v1.py`
  - clean
- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/extract_late_family_quality_v1.py`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T145436Z__late_family_quality_v1/`

Outputs:

- `family_quality_rows.jsonl`
- `family_quality_case_digest.jsonl`
- `family_quality_summary.json`
- `family_quality_cases.md`

First read:

- `1111`
  - truth/trust/full-uplift/persistence all point at family `f0`
  - archive uplift points at challenger family `f1`
  - `family_quality_read_label = accepted_miss_family_looks_real`
- `1311`
  - truth/full-uplift/persistence point at family `f0`
  - trust/archive uplift point at family `f1`
  - `family_quality_read_label = trust_false_fire_family_looks_weak`
- `1411`
  - truth and archive uplift agree on family `f1`
  - trust/full-uplift/persistence sit on `f0`
  - the truth/archive winner family is still weak in absolute truth terms
  - `family_quality_read_label = archive_false_fire_family_looks_weak`
- reference wins remain split:
  - `411`
    - `truth_trust_split`
  - `611`
    - `truth_uplift_split`
  - `1011`
    - `truth_trust_split`

Interpretation:

- the family-level study is already more useful than the row-level stop harness
  alone on the fixed discriminator trio
- but the reference wins still split across family winners more than a simple
  promoted family-quality head would like
- so the right next move is external review of this new family-level bundle,
  not more live seeds and not more stop-rule churn

### 2026-04-08 late_family_quality_v1 v1.1 reporting-contract cleanup

Applied one small v1.1 cleanup after review feedback.

Files changed:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/SPEC.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/extract_late_family_quality_v1.py`
- `tests/tools/test_no_wli_late_family_quality_v1.py`

What changed:

- `family_quality_cases.md` winner tables now show metric-appropriate
  `best value` and trend fields:
  - truth -> `best_truth`, `truth_trend_label`
  - trust -> `best_trust`, `trust_trend_label`
  - archive uplift -> `best_archive_uplift`, `archive_uplift_trend_label`
  - full uplift -> `best_full_uplift`, `full_uplift_trend_label`
  - persistence -> `family_persistence_count`, `na`
- branch-local `SPEC.md` now points explicitly at the full planning spec
- optional threshold-matrix loading is now explicitly documented as future-use
  scaffolding, not active v1 analysis logic

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_family_quality_v1.py -q`
  - `20 passed`
- `C:\Python\Python311\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/extract_late_family_quality_v1.py tests/tools/test_no_wli_late_family_quality_v1.py`
  - clean
- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/extract_late_family_quality_v1.py`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`

Readout:

- no family-level verdict drift
- `family_quality_summary.json` remains:
  - `1111 -> accepted_miss_family_looks_real`
  - `1311 -> trust_false_fire_family_looks_weak`
  - `1411 -> archive_false_fire_family_looks_weak`
  - `411`, `1011 -> truth_trust_split`
  - `611 -> truth_uplift_split`

Interpretation:

- this was the right final v1 cleanup
- it fixes the main reviewer-facing markdown contract miss without changing the
  study result

### 2026-04-08 late_family_quality_v2 first agreement/disagreement pass

Built a seed-level agreement/disagreement study on top of the cleaned frozen
`late_family_quality_v1` bundle.

Files added:

- `planning/projects/no_wli/30_analysis_specs/no_wli_late_family_quality_v2_spec_2026-04-08.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/SPEC.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/EXPERIMENT_PLAN.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/__init__.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/extract_late_family_quality_v2.py`
- `tests/tools/test_no_wli_late_family_quality_v2.py`

Frozen input:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`

Study seeds:

- discriminators:
  - `1111`
  - `1311`
  - `1411`
- reference wins:
  - `411`
  - `611`
  - `1011`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_family_quality_v2.py -q`
  - `8 passed`
- `C:\Python\Python311\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/extract_late_family_quality_v2.py tests/tools/test_no_wli_late_family_quality_v2.py`
  - clean
- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/extract_late_family_quality_v2.py`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/20260408T154637Z__late_family_quality_v2/`

Outputs:

- `seed_agreement_rows.jsonl`
- `winner_pairwise_rows.jsonl`
- `agreement_summary.json`
- `agreement_cases.md`

Main read:

- shared acceptable pattern:
  - `A-A-B-A-A`
    - `611`
    - `1111`
- discriminator-only suspicious patterns:
  - `A-B-B-A-A`
    - `1311`
  - `A-B-A-B-B`
    - `1411`
- reference-only acceptable patterns:
  - `A-B-A-A-A`
    - `411`
  - `A-B-B-B-B`
    - `1011`

Interpretation:

- this strengthens the family-quality story substantially
- `1111` is now not only a “family looks real” case; it matches one real-win
  split pattern exactly
- the two false-fire seeds now have explicit discriminator-only mismatch
  patterns
- but the acceptable win side still spans three distinct patterns, so there is
  still no basis for a single simple promoted family-quality head

### 2026-04-08 late_family_quality_v3 pattern-plus-strength reconciliation pass

Built a new frozen-input reconciliation study on top of the cleaned v1 bundle
and the v2 agreement bundle.

Files added:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/SPEC.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/EXPERIMENT_PLAN.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/__init__.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/extract_late_family_quality_v3.py`
- `tests/tools/test_no_wli_late_family_quality_v3.py`

Frozen inputs:

- v1:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`
- v2:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/20260408T154637Z__late_family_quality_v2/`

Study seeds:

- discriminators:
  - `1111`
  - `1311`
  - `1411`
- reference wins:
  - `411`
  - `611`
  - `1011`

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_late_family_quality_v3.py -q`
  - `20 passed`
- `C:\Python\Python311\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/extract_late_family_quality_v3.py tests/tools/test_no_wli_late_family_quality_v3.py`
  - clean
- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/extract_late_family_quality_v3.py`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/20260408T162219Z__late_family_quality_v3/`

Outputs:

- `pattern_strength_rows.jsonl`
- `truth_relative_pair_rows.jsonl`
- `pattern_strength_summary.json`
- `pattern_strength_cases.md`

Main read from `pattern_strength_summary.json`:

- `accepted_miss_reference_like`
  - `1111`
- `reference_like_strong`
  - `411`
  - `611`
- `pattern_only_reference_like_but_strength_weak`
  - `1011`
- `inconclusive`
  - `1311`
  - `1411`

Cross-checked row-level evidence:

- `1111`
  - fields:
    - `winner_pattern_key = "A-A-B-A-A"`
    - `truth_winner_strength_label = "strong"`
    - `truth_minus_archive_winner_best_truth = 0.039`
    - `pattern_strength_read_label = "accepted_miss_reference_like"`
- `1311`
  - fields:
    - `winner_pattern_key = "A-B-B-A-A"`
    - `truth_winner_strength_label = "strong"`
    - `truth_minus_trust_winner_best_truth = 0.02`
    - `truth_minus_trust_winner_persistence_count = 1`
    - `pattern_strength_read_label = "inconclusive"`
- `1411`
  - fields:
    - `winner_pattern_key = "A-B-A-B-B"`
    - `truth_winner_strength_label = "partial"`
    - `truth_minus_archive_winner_best_truth = 0.0`
    - `pattern_strength_read_label = "inconclusive"`
- `1011`
  - fields:
    - `winner_pattern_key = "A-B-B-B-B"`
    - `truth_winner_strength_label = "weak"`
    - `pattern_strength_read_label = "pattern_only_reference_like_but_strength_weak"`

Interpretation:

- v3 is useful, but not a clean promotion result
- it materially sharpens `1111`:
  - `1111` is no longer only pattern-reference-like
  - it is also strength-compatible with the win side
- it also complicates the reference-win side:
  - `1011` keeps a reference-win pattern
  - but its truth-winning family is weak under the explicit v3 strength rule
- the false-fire side does **not** sharpen cleanly enough:
  - `1311` stays below the `CLEAR_TRUTH_GAP` requirement despite a persistence
    advantage
  - `1411` stays outside the archive-suspicious rule because its truth and
    archive winners do not separate the way that rule expects
- so the combined pattern-plus-strength line is now:
  - stronger on the accepted-miss side
  - more cautionary on the reference-win side
  - still not decisive on the false-fire side

Current recommendation:

- freeze `late_family_quality_v3` after this first pass
- take external review on the combined v1 / v2 / v3 family-quality stack
- do **not** promote a family-quality head or launch more live seeds before
  that review

### 2026-04-08 seed_family_triage_shadow_v1 first frozen-input shadow allocator

Built a new offline-only seed/family triage branch on top of the frozen:

- `score_stop_shadow_v2`
- `late_family_quality_v1`
- `late_family_quality_v2`
- `late_family_quality_v3`

Files added:

- `planning/projects/no_wli/30_analysis_specs/no_wli_seed_family_triage_shadow_v1_spec_2026-04-08.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/seed_family_triage_shadow_v1/SPEC.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/seed_family_triage_shadow_v1/EXPERIMENT_PLAN.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/seed_family_triage_shadow_v1/extract_seed_family_triage_shadow_v1.py`
- `tests/tools/test_no_wli_seed_family_triage_shadow_v1.py`

Frozen inputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T142942Z__score_stop_shadow_v2/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/20260408T154637Z__late_family_quality_v2/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/20260408T162219Z__late_family_quality_v3/`

Scope:

- all 12 review seeds get `seed_triage_rows.jsonl`
- the 6 enriched seeds:
  - `1111`
  - `1311`
  - `1411`
  - `411`
  - `611`
  - `1011`
  also get:
  - `family_priority_rows.jsonl`
  - `budget_recommendation_rows.jsonl`

Validation:

- `python -m pytest tests/tools/test_no_wli_seed_family_triage_shadow_v1.py -q`
  - `22 passed`
- `python -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/analysis/seed_family_triage_shadow_v1/extract_seed_family_triage_shadow_v1.py tests/tools/test_no_wli_seed_family_triage_shadow_v1.py`
  - clean
- `python tools/benchmarks/periodic_sub_trans/no_wli/analysis/seed_family_triage_shadow_v1/extract_seed_family_triage_shadow_v1.py`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/seed_family_triage_shadow_v1/20260408T172151Z__seed_family_triage_shadow_v1/`

Outputs:

- `seed_triage_rows.jsonl`
- `family_priority_rows.jsonl`
- `budget_recommendation_rows.jsonl`
- `triage_summary.json`
- `triage_cases.md`

Seed-level read from `triage_summary.json`:

- `high`
  - `411`
  - `511`
  - `611`
  - `711`
  - `1111`
- `medium`
  - `1011`
- `unclear`
  - `1311`
  - `1411`
- `low`
  - `811`
  - `911`
  - `1211`
  - `1511`

Budget-policy read:

- `focus_with_exploration`
  - `411`
  - `511`
  - `611`
  - `711`
  - `1111`
- `balanced_portfolio`
  - `1011`
- `exploration_heavy`
  - `1311`
  - `1411`
- `observe_only`
  - `811`
  - `911`
  - `1211`
  - `1511`

Family-level read:

- `1111`
  - primary family `f0`
  - secondary family `f1`
  - exploration family `f2`
- `1311`
  - primary family `f0`
  - secondary family `f1`
  - exploration family `f2`
- `1411`
  - primary family `f1`
  - secondary family `f0`
  - exploration family `f2`
- `411`
  - primary family `f0`
  - secondary family `f1`
  - exploration family `f2`
- `611`
  - primary family `f0`
  - secondary family `f1`
  - exploration family `f2`
- `1011`
  - primary family `f1`
  - no secondary family under the current policy
  - exploration family `f0`

Interpretation:

- this is a real new layer, not a relabelled stop bundle
- it turns the frozen stop/family stack into explicit shadow prioritisation:
  - high-confidence focus
  - balanced but still active
  - exploration-heavy
  - observe-only
- it also makes the current line more practical:
  - `1111` now gets focused follow-up budget despite the stop harness miss
  - `1011` is explicitly downgraded to balanced rather than focused because
    the v3 truth-family read is weak
  - `1311` and `1411` stay exploration-heavy rather than being forced into
    premature reject or accept buckets
- but it is still not promotable:
  - the allocator remains strongly truth-winner-led
  - the current first pass does not yet show that this shadow budget layer
    would materially improve downstream search if wired into the solver

Current recommendation:

- keep `seed_family_triage_shadow_v1` offline-only
- use it as the next combined external-review target alongside the stop and
  family-quality bundles
- do **not** promote it into pipeline control or launch more live seeds before
  that review is absorbed

### 2026-04-08 fixed-instance mode v1 patch 3 landed

Landed the runtime branch:

- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_runtime.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_pre_stage3.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_iteration_bridge.py`
- `tests/tools/test_no_wli_fixed_instance_mode.py`

Question:

- can generated mode remain unchanged while fixed mode uses stored
  ciphertext/plaintext/true key and treats `search_seed` as solver randomness?

Outcome:

- yes
- patch 3 is now complete and validated

Cross-checked evidence:

- fixed-mode runtime now returns:
  - `instance_input_mode`
  - `instance_fixture_id`
  - `instance_source_key_seed`
  - `search_seed`
  - stored `pt_idx`
  - stored `wli`
- fixed-mode runtime now verifies:
  - decrypt(`ciphertext_idx`, `true_key_idx`) equals stored
    `target_plaintext_idx`
  - encrypt(`target_plaintext_idx`, `true_key_idx`) equals stored
    `ciphertext_idx`
- pre-stage3 flow now forwards fixed-mode runtime inputs and switches
  oracle/stage12 calls to the effective `search_seed`
- targeted validation:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixed_instance_mode.py tests/tools/test_no_wli_iteration_runtime_word_ngram_sidechannel.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_stage_engine_parity_smoke.py -q`
  - `27 passed`

Interpretation:

- generated mode stays intact
- fixed mode is now a real runtime branch rather than only a config/schema
  sketch
- the next missing honesty boundary is identity/output/resume, not ciphertext
  integrity

### 2026-04-08 fixed-instance mode v1 patch 4 landed

Landed the fixed-instance iteration-loop branch:

- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
- `tests/tools/test_no_wli_fixed_instance_mode.py`

Question:

- can the loop iterate frozen instances x search seeds directly without slicing
  plaintext on the fly or regenerating ciphertext?

Outcome:

- yes
- patch 4 is now complete and validated

Cross-checked evidence:

- `run_iteration_matrix(...)` now accepts:
  - `instance_input_mode`
  - `fixed_instance_specs`
  - `search_seeds`
- generated mode keeps the legacy:
  - `tiers -> text_offsets -> key_seeds`
  loop
- fixed mode now uses:
  - `tiers -> fixed_instance_specs -> search_seeds`
- fixed-mode stage-engine state now carries:
  - `instance_input_mode`
  - `fixed_instance_spec`
  - `instance_fixture_id`
  - `instance_source_key_seed`
  - `search_seed`
- fixed-mode autoskip is explicitly rejected until patch 5 lands:
  - error text:
    - `autoskip_effective is not supported for fixed_ciphertext mode before identity/resume plumbing lands`
- targeted validation:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixed_instance_mode.py tests/tools/test_no_wli_iteration_runtime_word_ngram_sidechannel.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_stage_engine_parity_smoke.py -q`
  - `27 passed`

Interpretation:

- the fixed-mode loop contract is now real enough for the next identity patch
- but it is still intentionally fenced:
  - no autoskip in fixed mode yet
  - no resume/proven identity honesty yet
  - no fixture-matrix execution path yet

### 2026-04-08 fixed-instance mode v1 patch 5 landed

Landed the identity/output/resume/proven patch:

- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_identity.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_payload.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_finalize.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/autoskip_proven.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_summary.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_commit.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_completion.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
- `tests/tools/test_no_wli_fixed_instance_mode.py`

Question:

- can fixed mode now be named, indexed, resumed, and autoskipped honestly as:
  - `(instance_fixture_id, search_seed)`
- while generated mode stays:
  - `(fixture, text_id, key_seed)`?

Outcome:

- yes
- patch 5 is now complete and validated

Cross-checked evidence:

- centralized identity helper now exists:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_identity.py`
  - generated identity fields:
    - `instance_input_mode = "generated"`
    - `identity_key = (generated, tier_name, text_id, key_seed)`
  - fixed identity fields:
    - `instance_input_mode = "fixed_ciphertext"`
    - `identity_key = (fixed_ciphertext, instance_fixture_id, search_seed)`
    - fixed artifact basename shape:
      - `fixture_001__p9_c3_l1000__text0__seed611__search7001.json`
- payload/history/audit rows now carry fixed-mode identity fields:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_payload.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_commit.py`
  - fields now include:
    - `instance_input_mode`
    - `instance_fixture_id`
    - `instance_source_key_seed`
    - `search_seed`
- best-artifact lookup now uses the same mode-aware basename contract:
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_completion.py`
- proven solved indexing is now mode-aware:
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_summary.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
  - generated and fixed rows now key through the same explicit helper instead
    of colliding on generated-only tuples
- fixed-mode autoskip is no longer blocked:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
  - fixed mode now uses the same proven lookup with the fixed identity key
- resume preservation now keeps the new fixed identity fields:
  - `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - fixed resume outputs now include:
    - `instance_input_mode`
    - `instance_fixture_id`
    - `instance_source_key_seed`
    - `search_seed`
- focused validation slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixed_instance_mode.py tests/tools/test_no_wli_run_completion.py tests/tools/test_no_wli_stage_iteration_commit.py tests/tools/test_no_wli_resume_handoff_artifacts.py -q`
  - `34 passed`
- broader mixed validation slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixed_instance_mode.py tests/tools/test_no_wli_iteration_runtime_word_ngram_sidechannel.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_stage_engine_parity_smoke.py tests/tools/test_no_wli_artifact_resume.py -q`
  - `47 passed`

Interpretation:

- the fixed-mode honesty boundary is now real:
  - payload rows
  - history rows
  - audit rows
  - best-artifact lookup
  - proven solved indexing
  - autoskip
  - resume bundles
  all preserve the split between:
  - `source_key_seed` provenance
  - `search_seed` solver randomness
- generated mode stays compatible with the legacy identity contract
- the next remaining infrastructure step is now patch 6 only:
  - first honest fixed-instance execution through the fixture-matrix path

### 2026-04-08 fixed-instance mode v1 authoritative contract adopted

After the stop / family-quality / triage review stream, the next engineering
direction is now a fixed-instance infrastructure branch rather than more
analysis-side tuning.

Cross-checked code facts:

- current runtime still generates the instance from `key_seed`:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_runtime.py`
- current fixture metadata is too thin for frozen ciphertext mode:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`
- output artifacts contain enough metadata to export fixed fixtures, but the
  frozen fixture contract must add:
  - `true_key_idx`
  - `target_wli`
  - honest provenance / identity fields

Authoritative planning contract:

- `planning/projects/no_wli/30_analysis_specs/no_wli_fixed_instance_mode_v1_spec_2026-04-08.md`

Active implementation plan:

- `planning/projects/no_wli/20_active_plans/no_wli_fixed_instance_mode_infrastructure_plan_2026-04-08.md`

First fixed panel:

- `611`
- `1111`
- `1411`
- `1511`

Required patch order:

1. exporter + schema + panel manifest
2. state/config plumbing
3. runtime branch
4. iteration-loop branch
5. identity/output/resume/proven plumbing
6. first fixture-matrix execution path

Non-negotiable constraints carried into the new stream:

- do not overload `FixtureSpec`
- do not overload `KEY_SEEDS`
- do not postpone identity/output/resume/proven work
- do not land fixed mode without `true_key_idx`
- do not start solver experiments before the infrastructure branch is solid

### 2026-04-08 fixed-instance mode v1 patch 1 landed

Landed the first infrastructure patch only:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_models.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_io.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/export_fixed_instance_fixtures.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1.json`
- `tests/tools/test_no_wli_fixed_instance_mode.py`

Generated frozen fixtures:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances/fixture_001__p9_c3_l1000__text0__seed611.json`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances/fixture_001__p9_c3_l1000__text0__seed1111.json`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances/fixture_001__p9_c3_l1000__text0__seed1411.json`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances/fixture_001__p9_c3_l1000__text0__seed1511.json`

Question:

- can the exporter reconstruct a real frozen-instance contract from existing
  artifacts without guessing the true key or WLI?

Outcome:

- yes
- patch 1 is now complete and validated
- the four exported fixtures carry:
  - repo-relative source artifact provenance
  - `true_key_idx`
  - reconstructed `target_wli`
  - stored ciphertext/plaintext slices

Cross-checked evidence:

- exporter execution:
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_fixed_instance_fixtures.py`
  - console output:
    - `exported=4`
    - `output_dir=tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances`
- one exported fixture example:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances/fixture_001__p9_c3_l1000__text0__seed611.json`
  - fields:
    - `fixture_schema_version = "no_wli_fixed_instance_v1"`
    - `source_artifact_rel_path = "output/tools/benchmarks/periodic_sub_trans/no_wli/20260405T020334839969Z__bench_solve_pipeline_no_wli__37dc435/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed611.json"`
    - `source_run_id = "20260405T020334839969Z__bench_solve_pipeline_no_wli__37dc435"`
    - `source_fixture_id = "fixture_001"`
    - `source_key_seed = 611`
    - `length = 1000`
    - `len(ciphertext_idx) = 1000`
    - `len(target_plaintext_idx) = 1000`
    - `len(target_wli) = 1000`
    - `len(true_key_idx) = 264`
- panel manifest:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1.json`
  - fields:
    - `panel_id = "p9_c3_solver_panel_v1"`
    - ordered instances:
      - `seed611`
      - `seed1111`
      - `seed1411`
      - `seed1511`
    - ordered `search_seeds = [7001, 7002, 7003, 7004, 7005]`
- tests:
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - result:
    - `6 passed`
- compile check:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_models.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_io.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_fixed_instance_fixtures.py`
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - result:
    - clean

Interpretation:

- the exporter/schema/manifest contract is now real enough to support the
  fixed-mode runtime branch
- the next patch should now move to state/config plumbing
- patch 2 must still keep generated mode unchanged and must not overload
  `KEY_SEEDS`

### 2026-04-08 fixed-instance mode v1 patch 2 landed

Landed the state/config plumbing only:

- `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_mode_apply.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
- `tests/tools/test_no_wli_fixed_instance_mode.py`

Question:

- can the runtime state and saved run config distinguish generated mode from
  fixed mode honestly before any runtime behavior changes?

Outcome:

- yes
- patch 2 is now complete and validated
- generated mode still carries generated seeds
- fixed mode now has explicit config fields for frozen instance ids and search
  seeds

Cross-checked evidence:

- runtime-state defaults now include:
  - `INSTANCE_INPUT_MODE = "generated"`
  - `INSTANCE_FIXTURE_IDS = []`
  - `SEARCH_SEEDS = []`
- run-mode overrides now accept:
  - `INSTANCE_INPUT_MODE`
  - `INSTANCE_FIXTURE_IDS`
  - `SEARCH_SEEDS`
- saved run config now emits:
  - `instance_input_mode`
  - `instance_fixture_ids`
  - `search_seeds`
  - `generated_key_seeds`
  - `text_offsets`
- explicit test coverage:
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - result:
    - `10 passed`
  - includes:
    - generated-mode run-config serialization
    - fixed-mode run-config serialization
    - fixed-instance override application
- compile check:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_mode_apply.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - result:
    - clean

Interpretation:

- this lands the config-side honesty boundary without pretending fixed mode can
  run yet
- generated mode remains the only executable path today
- patch 3 should now add the actual runtime branch in
  `iteration_runtime.py`

### 2026-04-08 fixed-instance mode v1 patch 6 landed

Landed the first fixture-matrix execution path for fixed mode:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_runtime.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
- `tools/benchmarks/periodic_sub_trans/common/campaign_run_config.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_entrypoints.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/campaign_config_apply.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_pipeline_execution.py`
- `tests/tools/test_no_wli_fixed_instance_mode.py`
- `tests/tools/test_no_wli_fixture_matrix.py`
- `tests/tools/test_no_wli_fixture_matrix_mainflow.py`
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`

Question:

- can the fixed-instance panel now execute honestly through the fixture-matrix
  path without falling back to the old generated-mode seed identity?

Outcome:

- yes, at the code-path and test-validation level
- fixed-mode fixture-matrix jobs now carry:
  - `instance_input_mode`
  - `instance_fixture_id`
  - `instance_source_key_seed`
  - `search_seed`
- fixed-mode job keys, plan payloads, run-state base fields, runtime console
  identity, and runner config emission are now mode-aware
- fixed mode now clears `KEY_SEEDS` and uses:
  - `INSTANCE_INPUT_MODE`
  - `INSTANCE_FIXTURE_IDS`
  - `SEARCH_SEEDS`
  through the runner/config bridge
- runner execution now loads exported fixed specs from
  `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances/` and passes
  them into `run_iteration_matrix(...)`

Cross-checked evidence:

- focused fixture-matrix slice:
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - `tests/tools/test_no_wli_fixture_matrix.py`
  - `tests/tools/test_no_wli_fixture_matrix_mainflow.py`
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - `60 passed`
- broader compatibility slice:
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - `tests/tools/test_no_wli_fixture_matrix.py`
  - `tests/tools/test_no_wli_fixture_matrix_mainflow.py`
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - `tests/tools/test_no_wli_fixture_matrix_hardening.py`
  - `tests/tools/test_periodic_sub_trans_campaign_run_config.py`
  - `tests/tools/test_no_wli_artifact_resume.py`
  - `84 passed`

Interpretation:

- patch 6 is now landed and validated under fixture-matrix tests
- the remaining engineering gap is no longer missing plumbing; it is one small
  real fixed-mode canary
- no long live fixed-mode fixture-matrix campaign was launched in this patch

### 2026-04-08 fixed-instance mode hardening pass landed before broader use

The fixed-instance stream received the requested hardening pass before any
broader fixed-mode run was treated as valid infrastructure evidence.

Landed hardening files:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_runtime.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_io.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
- `tests/tools/test_no_wli_fixed_instance_mode.py`
- `tests/tools/test_no_wli_fixture_matrix_mainflow.py`
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`

What changed:

- checked-in fixture-matrix defaults are safe again:
  - fixed canary no longer remains the active default
  - fixed-mode execution now requires an explicit source switch
- fixed mode no longer loads campaign config unnecessarily inside
  `fixture_matrix_mainflow.py`
- mapping-based fixed-instance payloads now route through shared validation in
  `iteration_runtime.py`
- fixed-mode tier mismatch no longer silently builds zero iteration inputs:
  - `iteration_matrix_flow.py` now raises loudly if no fixed fixtures match the
    intended tier
- fixed-mode resume identity in `artifact_resume.py` is now strict:
  - no fallback from missing fixed identity fields back to `key_seed`
- `fixed_instance_io.py` now deduplicates repeated fixture paths
- `fixture_matrix_jobs.py` now documents that:
  - `run_seed` is only a compatibility mirror of `search_seed` in fixed mode
  - `text_offsets` is provenance only in fixed mode

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixed_instance_mode.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix.py -q`
- result:
  - `67 passed`

Operational status:

- the already-started canary remains the only live fixed-mode run:
  - `tune_v70_fixed_p9c3_fixture611_search7001_stage35_baseline_selector_score_plus_novelty_canary_1job`
- checked-in config is now back to safe generated defaults, so no new fixed
  canary is launched accidentally by default

### 2026-04-08 fixed long run queued behind the live canary

The next fixed-instance long run is now queued as a one-shot follow-up behind
the still-running `v70` canary, without leaving the repo checked in to an
active fixed-mode default.

Queued next run:

- `tune_v71_fixed_p9c3_panelv1_search7001_7005_stage35_baseline_selector_score_plus_novelty_live_bounded_20job`

Queued launcher:

- `planning/projects/no_wli/60_launch_scripts/no_wli_fixed_v71_wait_for_v70_then_launch_panel_v1_long_2026-04-08.ps1`

Watcher log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_fixed_v70_watch_and_launch_v71_2026-04-08.log`

Console log target:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_fixed_v71_panel_v1_long_2026-04-08.log`

Supporting config change:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  now recognizes:
  - `FIXED_INSTANCE_EXECUTION_PROFILE = "panel_v1_long"`
  - `fixed_instance_panel_v1_long`

Panel shape:

- panel:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1.json`
- frozen instances:
  - `611`
  - `1111`
  - `1411`
  - `1511`
- search seeds:
  - `7001`
  - `7002`
  - `7003`
  - `7004`
  - `7005`
- expected total jobs:
  - `20`

Validation before queueing:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixed_instance_mode.py tests/tools/test_no_wli_fixture_matrix.py -q`
- result:
  - `68 passed`

Important operational note:

- `v70` was not restarted
- the watcher leaves checked-in config on the safe generated default and only
  flips to `panel_v1_long` inside the watcher-run launch window

### 2026-04-09 fixed long-run status cross-check and explicit handoff slicing

Cross-check question:

- after the watcher-fired launch, what is the real live status of `v70` and
  `v71`, and how should the remaining `v71` work be handed off without
  redefining the panel loosely?

Observed status:

- `v70` is complete:
  - `tune_v70_fixed_p9c3_fixture611_search7001_stage35_baseline_selector_score_plus_novelty_canary_1job`
- `v71` is active:
  - `tune_v71_fixed_p9c3_panelv1_search7001_7005_stage35_baseline_selector_score_plus_novelty_live_bounded_20job`
- current completed jobs:
  - job 1:
    - `fixture_001__p9_c3_l1000__text0__seed611`
    - `search7001`
  - job 2:
    - `fixture_001__p9_c3_l1000__text0__seed611`
    - `search7002`
- current in-flight local job:
  - job 3:
    - `fixture_001__p9_c3_l1000__text0__seed611`
    - `search7003`

Exact original `v71` ordering:

- jobs `1-5`:
  - frozen instance `611`
  - search seeds `7001-7005`
- jobs `6-10`:
  - frozen instance `1111`
  - search seeds `7001-7005`
- jobs `11-15`:
  - frozen instance `1411`
  - search seeds `7001-7005`
- jobs `16-20`:
  - frozen instance `1511`
  - search seeds `7001-7005`

Interpretation:

- the desired PC2 handoff for original jobs `4-10` is exact, but it cannot be
  represented as one single Cartesian fixed panel under the current schema
- the honest representation is two explicit slices:
  - `v72a`:
    - original jobs `4-5`
    - `611` with `search7004-7005`
  - `v72b`:
    - original jobs `6-10`
    - `1111` with `search7001-7005`
- the remaining original jobs `11-20` *can* be preserved as one clean deferred
  Cartesian tail:
  - `v73`
  - `1411/1511` with `search7001-7005`

Landed setup:

- new exact handoff manifests:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1_jobs04_05.json`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1_jobs06_10.json`
- new deferred tail manifest:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1_jobs11_20.json`
- new exact handoff launcher:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_fixed_v72_jobs04_10_handoff_2026-04-09.ps1`
- new deferred tail launcher:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_fixed_v73_jobs11_20_deferred_2026-04-09.ps1`

Config cleanup:

- checked-in `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  is restored to:
  - `FIXED_INSTANCE_EXECUTION_PROFILE = "off"`
- new fixed profiles are now defined but inactive by default:
  - `panel_v1_jobs04_05`
  - `panel_v1_jobs06_10`
  - `panel_v1_jobs11_20`

Validation:

- `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - new exact-slice manifest coverage added
- combined fixed-mode matrix slice:
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - `tests/tools/test_no_wli_fixture_matrix_mainflow.py`
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - `tests/tools/test_no_wli_fixture_matrix.py`

Outcome:

- planning/state/logging is now aligned with the real live status
- the PC2 handoff package for original jobs `4-10` is explicit and exact
- original jobs `11-20` are preserved as a concrete deferred package rather
  than a vague reminder

### 2026-04-09 local `v71` stop confirmed after job 3

Question:

- did local `v71` actually stop at the intended handoff point, or was job 3
  still incomplete?

Observed status:

- local process is gone
- `v71` run-state now shows:
  - `completed_jobs = 3`
  - `remaining_jobs = 17`
  - last completed:
    - original job `3`
    - `611/search7003`
    - elapsed `21058.197s`
- event log also shows:
  - job `3` completed
  - job `4` started:
    - `611/search7004`
  - but there is no completed event for job `4`

Interpretation:

- the clean completed handoff point is:
  - original jobs `1-3` done
  - original jobs `4-20` still outstanding
- the exact handoff/deferred staging from the previous entry remains correct:
  - `v72a/v72b` cover original jobs `4-10`
  - `v73` preserves original jobs `11-20`

Outcome:

- planning should no longer say that job `3` is merely expected to finish
- planning should now say that local `v71` is stopped after job `3`, with job
  `4` only started, not completed

### 2026-04-14 fixed `v72a` / `v72b` / `v73` completion audit

Question:

- do the completed follow-on slices now give retained data coverage for the
  full original 20-job fixed panel?

Observed status:

- local `v71` still remains the stopped handoff run:
  - `completed_jobs = 3`
  - original jobs `1-3` retained
  - original job `4` was started locally but not completed
- `v72a` run-state now shows:
  - `completed_jobs = 2`
  - `total_jobs = 2`
  - `completed_utc = 2026-04-11T05:09:42.273156+00:00`
- `v72b` run-state now shows:
  - `completed_jobs = 5`
  - `total_jobs = 5`
  - `completed_utc = 2026-04-12T08:04:07.281875+00:00`
- `v73` run-state now shows:
  - `completed_jobs = 10`
  - `total_jobs = 10`
  - `completed_utc = 2026-04-14T08:42:39.295087+00:00`
- completed-job bundle audit:
  - `v71` contributes `3` retained completed-job bundles
  - `v72a` contributes `2` retained completed-job bundles
  - `v72b` contributes `5` retained completed-job bundles
  - `v73` contributes `10` retained completed-job bundles
  - total retained completed-job bundles with `run_manifest.json`,
    `final_instances`, and `best/best_instance.json`: `20`
- extra non-completion residues also exist:
  - interrupted local `v71` job-4 bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260410T005938215863Z__bench_solve_pipeline_no_wli__9bea116`
    - `run_manifest.json` and `final_instances` exist
    - `best/best_instance.json` does not exist
  - stale `v72b` log reference:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260411T050946168397Z__bench_solve_pipeline_no_wli__9557c0f`
    - no retained bundle exists at that path

Interpretation:

- the original 20-job fixed panel is now fully covered across
  `v71 + v72a + v72b + v73`
- the retained completed-job data is present for all `20` completed jobs
- the two extra paths are interruption / restart residue, not missing
  completed-job evidence

Outcome:

- active planning should now say the full 20-job fixed panel is complete
- no further fixed follow-on launch is pending for this panel
- next planning should focus on how to use the completed panel rather than how
  to launch the remaining jobs

### 2026-04-14 integrated fixed-panel review and next-phase adoption

Question:

- after the fixed `20`-job panel and the two follow-up supplements, what does
  the benchmark now support, and what should happen next?

Reviewed inputs:

- main fixed-panel review pack:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- `1111` stage35-family supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`
- cross-seed plus `1111` focus-family supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`

Outcome:

- the fixed panel is now treated as a real structured benchmark basis rather
  than one more exploratory run pack
- the best current read is:
  - `1511`
    - strongest positive reference case
  - `611`
    - best middle unsolved case
  - `1111`
    - clearest fragmented late-region conversion-failure case
  - `1411`
    - mixed solvable case with a solved-run family-mapping caveat
- the two solved runs remain:
  - `1511/search7001`
  - `1411/search7003`
- both are stage-3 solves, not stage35 conversions
- the next active phase is now:
  - `fixed_instance_solver_development_v1`
- the recommended order is:
  - freeze the panel and supplements as the benchmark basis
  - build the baseline digest
  - write the `1111`, `1511`, `611`, and `1411` audit notes
  - only then shortlist one or two solver-change candidates
- explicitly not recommended now:
  - a new broad fixed panel
  - more live seeds
  - stop-rule promotion
  - a promoted family-quality head

Cross-checked evidence:

- main pack summary:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/01_summary_for_reviewers.md`
  - retained completed-job coverage:
    - `20` completed jobs
    - `2` solved
    - `1` stalled
    - `17` unsolved
  - per-seed first read:
    - `1511` average best match `0.7786`
    - `611` average best match `0.5144`
    - `1111` average best match `0.4770`
    - `1411` average best match `0.5770`
- cross-seed family supplement summary:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/01_summary_for_reviewers.md`
  - key lines:
    - `1111` is the most fragmented seed by family-mapped stage35 rows
    - `1511` is the tightest non-solved late-family case in the pack
    - solved runs `1411/7003` and `1511/7001` retain archive-side stage35 rows
      but no family-mapped stage35 rows on the `best / space_map` side
- `1111` focus-family summary:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/20_option_b_1111_focus_family_context/00_1111_focus_family_run_summary.csv`
  - fields:
    - focus family is `f0` in all five runs
    - dominant mapped family differs across runs
    - `7002` is the cleanest `f0` case
    - `7003` and `7005` remain `f0`-dominant but much weaker
    - `7004` fragments across `f0/f1/f2`
    - `7001` is dominated by `f1` despite `f0` focus family

Interpretation:

- the benchmark now supports a real `instance x search-seed` read strongly
  enough to freeze the panel as the basis for the next phase
- it does not justify a new broad panel or a new stop/family-quality promotion
  pass yet
- the next useful leverage should come from targeted fixed-instance
  solver-development analysis on the frozen panel

### 2026-04-14 fixed-instance solver-development v1 baseline digest generated

Question:

- can the frozen fixed panel now be turned into one authoritative baseline
  digest before any case-level audit or solver retuning starts?

Inputs:

- main fixed-panel review pack:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- cross-seed plus `1111` focus-family supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`
- `1111` raw supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`

Generated output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T052315Z__fixed_instance_solver_development_v1/`

Generated files:

- `panel_baseline_rows.jsonl`
- `instance_summary_rows.jsonl`
- `instance_search_matrix.csv`
- `fixed_instance_solver_baseline_cases.md`

Outcome:

- yes
- Workstream 1 baseline digest now exists
- the frozen baseline bundle keeps:
  - the primary trio:
    - `1511`
    - `611`
    - `1111`
  - `1411` as a caveated cross-check
  - the three stage35 count fields kept separate:
    - `archive_seed_row_count`
    - `best_stage35_seed_row_count`
    - `space_map_stage35_row_count`
  - retained trust-related field names copied from retained
    `best/best_instance.json`

Cross-checked evidence:

- generated per-instance summary rows:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T052315Z__fixed_instance_solver_development_v1/instance_summary_rows.jsonl`
  - fields confirm:
    - `1511`
      - `benchmark_case_role = "positive_control"`
      - `mean_best_match_ratio = 0.7786`
      - `searches_with_zero_family_mapped_stage35_rows = [7001]`
    - `611`
      - `benchmark_case_role = "middle_unsolved_case"`
      - `mean_best_match_ratio = 0.5144`
    - `1111`
      - `benchmark_case_role = "conversion_failure_case"`
      - `stalled_run_count = 1`
      - `max_best_match_ratio = 0.754`
      - `max_best_match_search_seed = 7002`
    - `1411`
      - `benchmark_case_role = "caveated_cross_check"`
      - `searches_with_zero_family_mapped_stage35_rows = [7003]`
- generated baseline markdown:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T052315Z__fixed_instance_solver_development_v1/fixed_instance_solver_baseline_cases.md`
  - explicit sections:
    - `Primary tuning trio`
    - `Cross-check case`
    - solved-run caveat for:
      - `1411/search7003`
      - `1511/search7001`
- generated run matrix:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T052315Z__fixed_instance_solver_development_v1/instance_search_matrix.csv`
  - per-run columns now preserve:
    - `archive_seed_row_count`
    - `best_stage35_seed_row_count`
    - `space_map_stage35_row_count`
    - `focus_family_id`
    - `dominant_stage35_family_id`
    - `caveat_flags`
- generated baseline rows:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T052315Z__fixed_instance_solver_development_v1/panel_baseline_rows.jsonl`
  - retained trust-related fields present per row:
    - `word_ngram_judge_trust_score`
    - `word_ngram_judge_trust_tier`
    - `word_ngram_judge_report_xent`
    - `word_ngram_judge_n_positions`
    - `word_ngram_judge_active`

Interpretation:

- the fixed panel no longer has to be re-read through multiple review packs just
  to recover the basic baseline state
- the current benchmark basis is now frozen in one machine-readable output
  bundle before the case-level audits begin
- the next active work should now move to the `1111` conversion-failure audit,
  not to solver/runtime changes

### 2026-04-14 `1111` conversion-failure audit generated

Question:

- can the retained `1111` evidence now sharpen the read beyond
  "late promise fails to convert" without drifting the fixed definitions?

Inputs:

- baseline bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T052315Z__fixed_instance_solver_development_v1/`
- `1111` raw supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14/`
- cross-seed plus `1111` focus-family supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`

Generated combined output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T054021Z__fixed_instance_solver_development_v1/`

New files:

- `1111_conversion_compare_rows.csv`
- `1111_conversion_failure_audit.md`

Outcome:

- yes
- the `1111` read is now sharper than "repeated late promise without
  conversion"
- best current read:
  - `7002`
    - the clean aligned `f0` case
  - `7001`
    - focus/final-best stay `f0`, but mapped stage35 rows are dominated by `f1`
  - `7004`
    - focus/final-best stay `f0`, but the mapped stage35 region fragments across
      `f0/f1/f2` and is dominated by `f2`
  - `7003` and `7005`
    - mapped stage35 rows stay `f0`-dominant
    - but the final-best stage35 seed family flips to `f1`

Cross-checked evidence:

- comparison table:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T054021Z__fixed_instance_solver_development_v1/1111_conversion_compare_rows.csv`
  - per-run fields confirm:
    - `7002`
      - `focus_family_id = f0`
      - `dominant_mapped_stage35_family_id = f0`
      - `final_best_stage35_seed_family_id = f0`
      - `family_alignment_label = all_aligned`
      - `focus_family_max_final_match = 0.752`
      - `baseline_candidate_source = phaseB_topk`
      - `baseline_candidate_lane = challenger`
    - `7001`
      - `focus_family_id = f0`
      - `dominant_mapped_stage35_family_id = f1`
      - `final_best_stage35_seed_family_id = f0`
      - `family_alignment_label = focus_and_final_best_aligned`
      - `stage35_family_counts = f0:1, f1:5`
    - `7004`
      - `focus_family_id = f0`
      - `dominant_mapped_stage35_family_id = f2`
      - `final_best_stage35_seed_family_id = f0`
      - `family_alignment_label = focus_and_final_best_aligned`
      - `stage35_family_counts = f0:1, f1:1, f2:3`
    - `7003`
      - `status = stalled`
      - `focus_family_id = f0`
      - `dominant_mapped_stage35_family_id = f0`
      - `final_best_stage35_seed_family_id = f1`
      - `max_mapped_family_by_final_match_id = f5`
      - `focus_family_max_final_match = 0.161`
      - `baseline_candidate_source = phaseA_selected`
    - `7005`
      - `focus_family_id = f0`
      - `dominant_mapped_stage35_family_id = f0`
      - `final_best_stage35_seed_family_id = f1`
      - `focus_family_max_final_match = 0.416`
      - `baseline_candidate_source = phaseA_selected`
- audit memo:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T054021Z__fixed_instance_solver_development_v1/1111_conversion_failure_audit.md`
  - locked definitions stated explicitly:
    - `focus family = family of the top stage35-admitted row in that run`
    - `final-best family = family of the joined stage35 seed row with best_seed_source = final_best`

Interpretation:

- `1111` is still not well read as simply weak or dead
- the strongest retained route is the case where focus family, dominant mapped
  stage35 family, and final-best stage35 seed family all align on `f0`
- weaker retained outcomes appear in two different ways:
  - the mapped late region becomes rival-dominant:
    - `7001`
    - `7004`
- the mapped late region stays `f0`-centred, but the final-best stage35 seed
    route escapes to `f1`:
    - `7003`
    - `7005`
- the next active work should now move to the `1511` positive-control audit,
  not to solver/runtime changes yet

### 2026-04-14 `1511` positive-control audit generated

Question:

- can the positive reference case now be stated explicitly enough to compare it
  against `611` and `1111` without blurring stage-3 solves and stage35 routes?

Inputs:

- combined baseline plus `1111` bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T054021Z__fixed_instance_solver_development_v1/`
- cross-seed family supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`

Generated combined output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T055624Z__fixed_instance_solver_development_v1/`

New files:

- `1511_positive_control_compare_rows.csv`
- `1511_positive_control_audit.md`

Outcome:

- yes
- `1511` is now documented as the strongest positive reference case
- the solved run remains:
  - `1511/search7001`
  - true stage-3 solve
  - archive-side stage35 rows present
  - no family-mapped stage35 rows on the `best / space_map` side
- strongest non-solved references now read as:
  - `7002`
    - accepted
    - single-family `f0`
    - `0.829`
  - `7003`
    - accepted
    - single-family `f0`
    - `0.845`
  - `7004`
    - single-family `f0`
    - but rejected on `search_score_drop_guard_failed`
  - `7005`
    - mostly `f0`
    - small `f1` tail
    - weaker `0.692`

Cross-checked evidence:

- comparison table:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T055624Z__fixed_instance_solver_development_v1/1511_positive_control_compare_rows.csv`
  - key rows:
    - `7001`
      - `status = solved`
      - `solved_run_stage3_caveat = 1`
      - `archive_seed_row_count = 5`
      - `space_map_stage35_row_count = 0`
    - `7002`
      - `mapped_family_shape_label = single_family`
      - `dominant_mapped_stage35_family_id = f0`
      - `followup_accept_reason = accepted`
    - `7003`
      - `mapped_family_shape_label = single_family`
      - `dominant_mapped_stage35_family_id = f0`
      - `followup_accept_reason = accepted`
    - `7004`
      - `mapped_family_shape_label = single_family`
      - `followup_accept_reason = search_score_drop_guard_failed`
    - `7005`
      - `mapped_family_shape_label = dominant_family_with_minor_tail`
      - `stage35_family_counts = f0:5, f1:1`
- audit memo:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T055624Z__fixed_instance_solver_development_v1/1511_positive_control_audit.md`
  - top read explicitly states:
    - `1511/7001` is the true solve but not family-comparable in the same way
      as the non-solved runs
    - `7002` and `7003` are the strongest non-solved references

Interpretation:

- `1511` is now strong enough to use as the positive control in the frozen
  benchmark trio
- the positive pattern is not "stage35 solves"; it is:
  - stage-3 solve exists
  - strongest non-solved late region stays unusually tight on `f0`
- the next active work should compare that positive reference against the
  middle unsolved `611` case

### 2026-04-14 `611` middle-case audit, `1411` caveat note, and shortlist generated

Question:

- after the baseline, `1111`, and `1511` reads, can the remaining analysis
  outputs now close the pre-tuning phase cleanly?

Inputs:

- combined bundle with baseline, `1111`, and `1511` outputs:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T055624Z__fixed_instance_solver_development_v1/`
- main fixed-panel review pack:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- cross-seed family supplement:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/`

New files in the same combined output bundle:

- `611_middle_case_compare_rows.csv`
- `611_middle_case_audit.md`
- `1411_caveat_and_use_note.md`
- `candidate_solver_change_shortlist.md`

Outcome:

- yes
- `611` is now documented as the main middle unsolved tuning case
- `1411` is now documented explicitly as a useful but caveated cross-check
  rather than an equal first-line tuning target
- the analysis phase now closes with a narrow two-candidate solver-change
  shortlist instead of a broad tuning sweep

Cross-checked evidence:

- `611` comparison table:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T055624Z__fixed_instance_solver_development_v1/611_middle_case_compare_rows.csv`
  - key rows:
    - `7004`
      - `best_match_ratio = 0.762`
      - `mapped_family_shape_label = single_family`
      - `dominant_mapped_stage35_family_id = f0`
      - `followup_accept_reason = accepted`
    - `7005`
      - `best_match_ratio = 0.585`
      - `mapped_family_shape_label = single_family`
      - `dominant_mapped_stage35_family_id = f0`
      - `followup_accept_reason = search_score_drop_guard_failed`
    - `7003`
      - `best_match_ratio = 0.466`
      - `mapped_family_shape_label = dominant_family_with_minor_tail`
      - `dominant_mapped_stage35_family_id = f1`
- `611` audit memo:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T055624Z__fixed_instance_solver_development_v1/611_middle_case_audit.md`
  - key comparison states:
    - `7004` and `7005` are the most useful pair
    - same tight `f0` family shape
    - different acceptance and final quality
- `1411` caveat note:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T055624Z__fixed_instance_solver_development_v1/1411_caveat_and_use_note.md`
  - explicit fields:
    - `1411/7003`
      - `archive_seed_row_count = 6`
      - `best_stage35_seed_row_count = 0`
      - `space_map_stage35_row_count = 0`
    - guidance:
      - keep `1411` as context and cross-check
      - do not treat it as an equal first-line tuning target
- shortlist memo:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T055624Z__fixed_instance_solver_development_v1/candidate_solver_change_shortlist.md`
  - candidate areas:
    - continuation selection and acceptance around coherent late routes
    - family-aware budget allocation once a coherent focal family appears

Interpretation:

- the pre-tuning analysis phase is now complete in one frozen bundle
- the benchmark basis is still:
  - primary trio:
    - `1511`
    - `611`
    - `1111`
  - caveated cross-check:
    - `1411`
- the next decision is no longer "what audit should be written?"
- the next decision is:
  - which one narrow shortlist candidate should become the first controlled
    solver-change test?

### 2026-04-15 candidate 1 retained replay on `611/search7005`

Question:

- does the first controlled solver-change candidate survive a retained replay on
  the strongest motivating case, `611/search7005`?

Candidate under test:

- guard-aware stage35 followup acceptance
- implementation surface:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage35_substitution_solver.py`
- opt-in cfg:
  - `accept_guard_passing_selector_mode = "top_score_then_search"`
  - `accept_guard_passing_score_band_eps = 0.001`

Retained source case:

- artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260411T014510194326Z__bench_solve_pipeline_no_wli__9557c0f/final_instances/fixture_001__p9_c3_l1000__text0__seed611__search7005.json`
- retained run dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260411T014510194326Z__bench_solve_pipeline_no_wli__9557c0f/`

Verification bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T062129Z__candidate1_guard_accept_611_search7005_replay_v1/`

Outcome:

- the candidate does fire on retained replay
- it is not promotable in the current form

Cross-checked evidence:

- original retained stage35 rejection:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260411T014510194326Z__bench_solve_pipeline_no_wli__9557c0f/stages.json`
  - stage row `stage35_substitution_only` fields:
    - `stage35_accept_passed = 0`
    - `stage35_accept_reason = "search_score_drop_guard_failed"`
    - `stage35_best_score = 0.23357093889279312`
    - `stage35_best_search_score = -12.01193032221665`
- original retained followup preview:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14/10_option_a_cross_seed_stage35_family/seed611/20_raw_stage35_seed_artifacts/search7005/stage35_progress.jsonl`
  - final `followup_finish` row preview shows:
    - rank 1 `f21811d60407068a` score `0.23357093889279312` search `-12.01193032221665`
    - rank 2 `f4a2ce03c2a6728d` score `0.2327406552195851` search `-11.993596530367164`
    - rank 3 `3338e69afb08d86d` score `0.23208570989859933` search `-11.97131602288249`
- replay comparison:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T062129Z__candidate1_guard_accept_611_search7005_replay_v1/candidate1_replay_comparison.json`
  - fields:
    - `candidate_accept_passed = 1`
    - `candidate_accept_reason = "accepted"`
    - `candidate_selected_archive_rank = 3`
    - `candidate_selected_via_guard_passing_selector = 1`
    - `candidate_best_candidate_hash = "3338e69afb08d86d"`
    - `candidate_best_score = 0.2320857098985992`
    - `candidate_best_search_score = -11.97131602288249`
    - `candidate_resume_best_match_ratio = 0.572`
    - `original_run_best_match_ratio = 0.585`
    - `candidate_resume_best_match_minus_original_run_best_match = -0.013000000000000012`
- replay stage35 payload:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T062129Z__candidate1_guard_accept_611_search7005_replay_v1/candidate1_replay/stage35_summary.json`
  - confirms:
    - `baseline_score = 0.23171454932072244`
    - `baseline_search_score = -12.00737629491563`
    - archive rank `2` also passes the guards
    - `top_score_then_search` still picks rank `3` because it has the strongest
      search score within the score band shortlist

Interpretation:

- the retained motivating read was directionally right:
  - the top row was not the only guard-passing option
- but the simple current selector is not good enough:
  - within the score band it moves to the strongest-search row
  - on this case that row does not improve truth over the selected stage-3
    baseline
  - and it is worse than the original run best
- so candidate 1, as currently implemented, fails the retained no-harm check

Next action:

- keep candidate 1 code opt-in only
- do not attach a live run to it in the current form
- decide whether to refine candidate 1 with a stronger no-harm selector or move
  to candidate 2

### 2026-04-15 candidate 1 no-harm refinement and retained run-level projection

What changed:

- the stage3 outcome path now keeps the retained stage3 best state intact
- `resolve_iteration_outcome(...)` now only lets stage35 become the final best
  when it is at least as strong as the current best-known outcome
- stage35 telemetry still records selection and retained truth fields even when
  the final best stays stage3

Verification bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T071422Z__candidate1_guard_accept_611_search7005_replay_v1/`

Run-level projection readout:

- `candidate1_replay_comparison.json` still shows the stage35-only retained
  negative:
  - `candidate_accept_passed = 1`
  - `candidate_selected_archive_rank = 3`
  - `candidate_resume_best_match_ratio = 0.572`
  - `candidate_resume_best_match_minus_original_run_best_match = -0.013000000000000012`
- `candidate1_no_harm_projection_comparison.json` shows the run-level retained
  no-harm containment:
  - `projected_best_stage = "stage3_full_refine"`
  - `projected_best_match_ratio = 0.585`
  - `projected_stage35_selected = 1`
  - `projected_stage35_best_match = 0.572`
  - `projected_stage35_used_for_final_best = 0`
  - `projected_match_delta_vs_original_run_best = 0.0`

Interpretation:

- candidate 1 still does not create a useful better row on retained
  `611/search7005`
- but the run-level no-harm issue is now contained:
  - a weaker selected stage35 row no longer overwrites a stronger retained
    `stage3_full_refine` result
- this changes the decision shape:
  - the next question is utility, not basic no-harm containment

Next action:

- keep candidate 1 code opt-in only
- do not attach a live run to it in the current form
- decide whether to refine candidate 1 for utility or move to candidate 2

### 2026-04-15 candidate 1 review cleanup landed and candidate 2 core hook started

Question:

- after the candidate 1 code review, can the required cleanup land cleanly, and
  can candidate 2 start on an existing runtime hook instead of a new branch?

What changed:

- candidate 1 review cleanup landed:
  - `NaN` `stage35_match` no longer auto-promotes stage35 to final best
  - selector-rescued accepts now report
    `accepted_via_guard_passing_selector`
- the fixed-instance extractor now validates its frozen input contracts and
  writes machine-readable caveat flags for `1411`
- candidate 2 started as a minimal opt-in runtime hook on the existing
  Phase-B family-preservation surface:
  - policy:
    - `reinforce_top_family_v1`
  - preset:
    - `stage3_phaseb_top_family_reinforce_p9`

Cross-checked evidence:

- latest candidate 1 retained verification bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160357Z__candidate1_guard_accept_611_search7005_replay_v1/`
  - `run_summary.json` confirms:
    - `candidate_resume_best_match_ratio = 0.572`
    - `original_run_best_match_ratio = 0.585`
    - `projected_best_stage = "stage3_full_refine"`
    - `projected_best_match_ratio = 0.585`
    - `projected_stage35_used_for_final_best = 0`
- refreshed combined analysis bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160503Z__fixed_instance_solver_development_v1/`
- candidate 2 runtime hook implementation surface:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- candidate 2 canary / unit evidence:
  - `tests/tools/test_no_wli_stage3_phasec.py`
  - `tests/tools/test_no_wli_phaseb_family_preservation_canary.py`
- test run:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_stage35_substitution_solver.py tests/tools/test_no_wli_fixed_instance_solver_development_v1.py -q`
  - result:
    - `104 passed`

Interpretation:

- candidate 1 is now in the cleaner reviewed state:
  - contained
  - explicit
  - still utility-negative on retained `611/search7005`
- candidate 2 is now grounded on a real existing runtime hook rather than a
  speculative new branch
- candidate 2 is still only canary / synthetic verified:
  - no retained fixed-panel verification has happened yet

Next action:

- keep candidate 1 opt-in only as a contained retained-negative reference
- build the candidate 2 retained verification path on frozen fixed-panel cases
- do not attach any live run to candidate 2 until that retained verification
  exists

### 2026-04-15 candidate 2 shadow verification completed

Question:

- before attempting an exact retained replay, does the saved fixed-panel
  candidate-pool surface show any real room for candidate 2 top-family
  reinforcement to act on?

What changed:

- added a saved-pool shadow verifier:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate2_top_family_reinforce_shadow.py`
- added focused helper coverage:
  - `tests/tools/test_no_wli_candidate2_top_family_shadow.py`
- ran the candidate 2 shadow bundle at `2026-04-16T03:15:27Z`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T031527Z__candidate2_top_family_reinforce_shadow_v1/`

Cross-checked evidence:

- cases checked:
  - `611/search7005`
  - `1111/search7002`
  - `1111/search7004`
  - `1511/search7002`
- `run_summary.json` confirms:
  - `case_count = 4`
  - `cases_with_saved_room = 4`
  - `cases_without_saved_room = 0`
- the per-case CSV shows:
  - every checked case has extra anchor-family hashes outside the baseline
    Phase-A selected pool
  - `shadow_materializable_extra_anchor_rows = 2` on all four checked cases
  - `1111/search7004` stays the awkward mixed case:
    - shadow anchor family resolves to `f1`, not `f0`, because the retained
      anchor row comes from `phaseB_topk`
- test run:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_candidate2_top_family_shadow.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixed_instance_solver_development_v1.py -q`
  - result:
    - `42 passed`

Interpretation:

- candidate 2 now has real retained support beyond synthetic canaries
- the saved `phaseC_candidate_pool_rows` surface does contain room for
  top-family reinforcement on the checked retained cases
- this is still not exact replay evidence:
  - the shadow verifier reasons over saved candidate-pool rows
  - it does not replay the full retained Stage-3 path end-to-end

Next action:

- keep candidate 2 off live runtime
- build the exact retained replay path next
- keep the fixed panel frozen while candidate 2 remains shadow-supported only

### 2026-04-15 candidate 2 first exact replay probe timed out

Question:

- can the new exact retained replay path for candidate 2 actually complete on a
  real fixed-panel case, or is the current stage2-to-stage3 replay surface too
  expensive to use directly?

What changed:

- added the first exact retained replay verifier:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate2_top_family_reinforce_exact_replay.py`
- added focused summary coverage:
  - `tests/tools/test_no_wli_candidate2_top_family_exact_replay.py`
- launched the first exact retained pass at `2026-04-16T03:23:05Z` against:
  - `611/search7005`
  - stage35 disabled to isolate the candidate2 Stage-3 mechanism
- preserved the timed-out attempt directory with explicit status:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T032305Z__candidate2_top_family_reinforce_611_search7005_exact_stage3_replay_v1/attempt_status.json`

Cross-checked evidence:

- exact probe bundle root:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T032305Z__candidate2_top_family_reinforce_611_search7005_exact_stage3_replay_v1/`
- probe status:
  - timed out after `1800` seconds
  - no completed resume bundle was written
  - the probe left only the empty `resume_bundle/` directory before timeout
- retained replay helper tests:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_candidate2_top_family_exact_replay.py -q`
  - result:
    - `2 passed`
- candidate2 retained shadow and surrounding branch tests remain green:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_candidate2_top_family_shadow.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixed_instance_solver_development_v1.py tests/tools/test_no_wli_candidate2_top_family_exact_replay.py -q`
  - result:
    - `44 passed`

Interpretation:

- candidate 2 still has real retained shadow support
- but the current exact stage2-to-stage3 replay surface is too expensive to use
  directly for a practical retained verification loop
- candidate 2 therefore remains shadow-supported only:
  - not exact-replay verified
  - not live-ready

Next action:

- keep candidate 2 off live runtime
- build a cheaper or earlier-checkpointed exact replay path next
- keep the fixed panel frozen while that replay-path blocker remains open

### 2026-04-15 candidate 2 longer-timeout exact replays completed but did not engage

Question:

- after allowing longer runtimes, does candidate 2 actually engage on retained
  fixed-panel cases, or was the earlier blocker mostly replay cost?

What changed:

- completed a longer-timeout candidate exact replay on `611/search7005`:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate2_top_family_reinforce_exact_replay.py`
  - bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T044904Z__candidate2_top_family_reinforce_611_search7005_exact_stage3_replay_v1/`
- completed a matched exact control replay on `611/search7005`:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate2_top_family_exact_control_611_7005.py`
  - bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T053515Z__candidate2_top_family_exact_control_611_search7005_stage3_replay_v1/`
- completed a longer-timeout candidate exact replay on `1111/search7004`:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate2_top_family_reinforce_exact_replay_1111_7004.py`
  - bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T060743Z__candidate2_top_family_reinforce_1111_search7004_exact_stage3_replay_v1/`

Cross-checked evidence:

- candidate exact `611/search7005` summary:
  - replay best `0.535` versus retained baseline `0.585`
  - `phaseB_family_reservation_applied = 0`
  - `phaseB_family_count_in_top_band = 32`
  - `phaseB_family_preserved_count = 32`
- exact control `611/search7005` summary:
  - same replay best `0.535`
  - policy `off`
  - this makes the `611` delta replay drift, not a candidate2 effect
- candidate exact `1111/search7004` summary:
  - replay best `0.406` versus retained baseline `0.423`
  - `phaseB_family_reservation_applied = 0`
  - `phaseB_family_count_in_top_band = 32`
  - `phaseB_family_preserved_count = 32`
- the Phase-B policy logic in `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  confirms why this happens:
  - `reinforce_top_family_v1` acts on the already selected Phase-B rows
  - it can only fire if that selected surface contains extra rows from the
    top-ranked family
- this explains the mismatch with the earlier shadow bundle:
  - the shadow verifier reasoned over saved `phaseC_candidate_pool_rows`
  - the exact hook acts earlier, on the selected Phase-B rows
  - on the tested exact cases that selected surface is already `32` families
    across `32` rows

Interpretation:

- the exact retained replay path now works if given a long enough runtime
- candidate 2 is no longer blocked mainly by replay cost
- the current `reinforce_top_family_v1` lever is exact-probed but non-engaging
  on the tested retained cases
- the earlier saved-pool shadow result was useful for narrowing, but it was not
  aligned with the surface the live hook actually controls

Next action:

- keep candidate 2 off live runtime
- stop treating replay-cost reduction as the primary blocker
- re-spec the candidate2 lever against the actual Phase-B selected-row surface,
  or add cheaper diagnostics on that surface before spending more long exact
  runs
- keep the fixed panel frozen while that re-spec decision is open

### 2026-04-15 candidate 2 whole-panel selected-surface diagnostic closed the current lever

Question:

- is the current candidate2 lever only non-engaging on the two exact probe
  cases, or is it structurally blocked across the full frozen `20`-job panel?

What changed:

- added a cheaper selected-surface extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_candidate2_phaseb_selected_surface_v1.py`
- added focused coverage:
  - `tests/tools/test_no_wli_candidate2_phaseb_selected_surface.py`
- ran the selected-surface bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T064934Z__candidate2_phaseb_selected_surface_v1/`

Cross-checked evidence:

- test run:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_candidate2_phaseb_selected_surface.py tests/tools/test_no_wli_candidate2_top_family_exact_replay.py tests/tools/test_no_wli_candidate2_top_family_shadow.py -q`
  - result:
    - `8 passed`
- selected-surface summary:
  - `run_count = 20`
  - `runs_with_repeat_families = 0`
  - `runs_where_current_candidate2_lever_can_engage = 0`
  - `current_candidate2_lever_structurally_blocked_on_panel = 1`
- per-seed summary is uniform:
  - `1511`: `5/5` runs have all-unique selected families
  - `611`: `5/5` runs have all-unique selected families
  - `1111`: `5/5` runs have all-unique selected families
  - `1411`: `5/5` runs have all-unique selected families
- per-run rows show the same retained Phase-B surface on the whole panel:
  - `phaseB_downstream_selected_count = 32`
  - `phaseB_family_preserved_count = 32`
  - `repeated_family_row_count = 0`

Interpretation:

- the stronger whole-panel read now matches the two exact retained probes
- the current `reinforce_top_family_v1` lever is not just non-engaging on a few
  checked runs; it is structurally blocked on the frozen panel in its current
  form
- the earlier saved-pool shadow bundle was useful for narrowing, but it is now
  conclusively the wrong practical surface for deciding whether this lever can
  act

Next action:

- keep candidate 2 off live runtime
- do not spend more long exact runs on the current candidate2 lever
- re-spec or replace the lever against the actual Phase-B selected-row surface
- keep the fixed panel frozen while the replacement choice is discussed

### 2026-04-16 candidate 2 replacement Phase-C shadow also closed

Question:

- after the Phase-B lever closed, does a simple Phase-C-start replacement,
  `anchor_family_reserved_v1`, show any real retained room on the frozen panel?

What changed:

- added a Phase-C start-policy branch:
  - `anchor_family_reserved_v1`
- added a canary preset:
  - `stage3_phasec_anchor_family_reserved_p9`
- added focused Phase-C coverage:
  - `tests/tools/test_no_wli_stage3_phasec.py`
  - `tests/tools/test_no_wli_phasec_start_policy_canary.py`
- added a whole-panel saved-surface shadow verifier:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate2_anchor_family_reserved_shadow.py`
- ran the whole-panel replacement shadow bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T145401Z__candidate2_anchor_family_reserved_shadow_v1/`

Cross-checked evidence:

- focused tests:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_fixed_instance_solver_development_v1.py -q`
  - result:
    - `43 passed`
- replacement whole-panel shadow summary:
  - `run_count = 20`
  - `runs_with_phasec_candidate_pool = 19`
  - `runs_with_saved_room = 0`
  - `replacement_candidate2_shadow_live_on_panel = 0`
- per-seed summary is uniform:
  - `1511`: `0/5` runs with saved anchor-family room
  - `611`: `0/5` runs with saved anchor-family room
  - `1111`: `0/5` runs with saved anchor-family room
  - `1411`: `0/5` runs with saved anchor-family room
- per-run rows show the same retained Phase-C read on the panel:
  - baseline Phase-C starts already include the available anchor-family rows
  - `shadow_materializable_extra_anchor_rows = 0`
    across all retained runs with saved Phase-C surface

Interpretation:

- the simple Phase-C-start replacement does not rescue candidate 2
- the family-aware-budget line is now closed in both current forms:
  - Phase-B top-family reinforcement is blocked on the selected-row surface
  - Phase-C anchor-family reservation is blocked on the saved start surface
- this is stronger than "candidate 2 needs more replay time":
  - the line does not currently show retained room to act

Next action:

- keep candidate 2 off live runtime in both current forms
- do not spend more exact replay time on candidate 2 as currently specified
- keep candidate 1 as a contained retained-negative reference only
- choose a new narrow candidate instead of extending the blocked candidate2 line

### 2026-04-16 candidate 3 anchor-swap line selected and long exact control launched

Question:

- after candidate 2 closed on the retained surfaces it actually uses, is there
  a different narrow Phase-C-start lever that still shows real room on the
  frozen panel and is worth exact verification?

What changed:

- checked and rejected a simpler "extra `phaseB_topk` reserved start" idea:
  - the apparent extra `phaseB_topk` rows on the saved surface do not add new
    unique candidate hashes beyond the retained start set
- selected candidate 3 instead:
  - Phase-C first-actual-`phaseB_topk` anchor swap
  - runtime proxy:
    - `phaseb_topk_anchor_swap_v1`
  - preset:
    - `stage3_phasec_phaseb_topk_anchor_swap_p9`
- added focused runtime and branch support:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  - `tests/tools/test_no_wli_stage3_phasec.py`
  - `tests/tools/test_no_wli_phasec_start_policy_canary.py`
- added the whole-panel saved-start shadow verifier:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_phaseb_topk_anchor_shadow.py`
- ran the whole-panel shadow bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T151927Z__candidate3_phasec_phaseb_topk_anchor_shadow_v1/`
- corrected the exact-verifier comparison rule:
  - stage3-only exact replay summaries now compare against the retained
    Stage-3 reference, not only the artifact-level overall best
- preserved the earlier one-hour `611/search7004` exact control attempt as
  explicitly insufficient:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T152246Z__candidate3_phasec_anchor_swap_exact_control_611_search7004_stage3_replay_v1/attempt_status.json`
- added a shorter positive exact target pair:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_anchor_swap_exact_control_1511_7004.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_anchor_swap_exact_replay_1511_7004.py`
- completed the long exact control on `1511/search7004`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260416T163546Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`

Cross-checked evidence:

- focused tests:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixed_instance_solver_development_v1.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phasec_start_policy_canary.py -q`
  - result:
    - `49 passed`
- whole-panel shadow summary:
  - `run_count = 20`
  - `runs_where_anchor_swap_can_engage = 19`
  - `phaseb_topk_better_count = 11`
  - `anchor_better_count = 7`
  - `equal_count = 1`
  - `candidate3_anchor_swap_shadow_live_on_panel = 1`
- target-selection read:
  - `1511/search7004` is the shortest positive case in the primary tuning trio
    whose retained best is already Stage 3:
    - retained best stage:
      - `stage3_full_refine`
    - retained best / retained Stage-3 reference:
      - `0.571`
    - saved anchor-swap shadow delta:
      - `+0.005`
- control result:
  - retained Stage-3 reference:
    - `0.571`
  - replay best:
    - `0.435`
  - delta versus retained Stage-3 reference:
    - `-0.136`
  - retained control path details:
    - `phaseC_start_policy = source_order`
    - replay anchor source:
      - `stage3_best_phaseB`
    - replay path did not retain a usable first `phaseB_topk` challenger row in
      the control summary

Interpretation:

- candidate 3 is the first post-candidate2 line that is still live on the
  whole frozen panel
- it is not exact-confirmed yet
- the prior `611/search7004` control attempt was too short to conclude
  anything:
  - the retained source run itself took about `11855` seconds
- the exact-verifier cleanup was necessary before spending more long exact time
  on `stage35_substitution_only` cases

Next action:

- do not run the matched candidate exact pass on `1511/search7004` yet
- treat replay fidelity as the immediate blocker on candidate3 exact
  verification
- inspect and tighten the exact Stage-3 replay path before spending more long
  exact time on candidate 3

2026-04-17 candidate3 replay-fidelity audit plus rerun:

- added replay-fidelity audit support:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/audit_candidate3_exact_control_replay_fidelity_1511_7004.py`
  - `tests/tools/test_no_wli_candidate3_replay_fidelity_audit.py`
- tightened replay-surface persistence for future exact controls:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  - `tests/tools/test_no_wli_stage35_substitution_solver.py`
- wrote the replay-fidelity audit bundle against the completed first control:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T015015Z__candidate3_exact_control_replay_fidelity_1511_search7004_v1/`
- audit read:
  - first unavailable retained surface:
    - `phaseB_downstream_selected_ordered_hashes`
  - first actual persisted mismatch:
    - `phaseB_topk_saved_count`
  - retained `phaseB_topk_saved_count = 5`
  - replay `phaseB_topk_saved_count = 1`
- reran the exact control on `1511/search7004` with the patched replay
  surface:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T015030Z__candidate3_phasec_anchor_swap_exact_control_1511_search7004_stage3_replay_v1/`
- rerun read:
  - retained Stage-3 reference:
    - `0.571`
  - replay best:
    - `0.435`
  - delta:
    - `-0.136`
  - replay-side ordered surfaces now persist:
    - `phaseB_downstream_selected_summaries = 32`
    - `phaseB_topk_saved_summaries = 1`
    - `phaseC_start_source_counts = {'stage3_best_phaseB': 1, 'phaseA_selected': 5}`
- tests:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_candidate3_replay_fidelity_audit.py tests/tools/test_no_wli_stage35_substitution_solver.py tests/tools/test_no_wli_fixed_instance_solver_development_v1.py -q`
  - result:
    - `55 passed`
- current interpretation:
  - candidate3 is still alive as a solver idea
  - but the immediate blocker is explicit Phase-B surface drift before
    candidate3 acts
  - do not run the matched candidate exact pass yet

## 2026-04-17 - Candidate3 replay-fidelity contract tightened and saved-surface verifier added

- tightened the candidate3 replay-fidelity readout:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/audit_candidate3_exact_control_replay_fidelity_1511_7004.py`
- added a stable saved-surface verifier for the retained `1511/search7004`
  case:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_1511_7004.py`
  - `tests/tools/test_no_wli_candidate3_saved_surface.py`
- reran the replay-fidelity audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T052238Z__candidate3_exact_control_replay_fidelity_1511_search7004_v1/`
- stronger audit read:
  - first unavailable retained surface:
    - none
  - first actual persisted mismatch:
    - `phaseB_downstream_selected_ordered_hashes`
  - interpretation:
    - retained ordered downstream Phase-B identities can now be reconstructed
      from persisted `phaseC_candidate_pool_rows` filtered to
      `phaseA_selected`
    - control-lane drift starts before the saved Phase-B top-k and Phase-C
      start surfaces
- wrote the saved-surface verifier bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T052238Z__candidate3_phasec_saved_surface_1511_search7004_v1/`
- saved-surface read:
  - candidate3 can engage on the exact saved Phase-C start surface
  - first distinct `phaseB_topk` start is rank `2`
  - saved-surface `phaseB_topk` minus anchor final match:
    - `0.005`
  - scope:
    - stable per-case ordering reference only
    - not a fresh candidate replay
- tests:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_candidate3_replay_fidelity_audit.py tests/tools/test_no_wli_candidate3_saved_surface.py tests/tools/test_no_wli_fixed_instance_solver_development_v1.py -q`
  - result:
    - `34 passed`
- current interpretation:
  - candidate3 remains alive as a saved-surface ordering idea
  - the immediate blocker is still exact control-lane replay fidelity, not
    candidate ideation
  - the saved-surface verifier is now the stable per-case reference until a
    narrower Phase-C-only replay helper exists

## 2026-04-17 - Candidate3 saved-surface exact replay helper completed

- finished the narrower Phase-C-only replay helper for retained
  `1511/search7004`:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1511_7004.py`
- added focused tests:
  - `tests/tools/test_no_wli_candidate3_saved_surface_exact_replay.py`
- verification:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_candidate3_saved_surface_exact_replay.py tests/tools/test_no_wli_candidate3_saved_surface.py tests/tools/test_no_wli_fixed_instance_solver_development_v1.py -q`
  - result:
    - `32 passed`
- exact saved-surface bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T054445Z__candidate3_phasec_saved_surface_exact_1511_search7004_v1/`
- exact saved-surface read:
  - saved-surface control reproduces the retained Stage-3 reference exactly:
    - retained `0.571`
    - control `0.571`
  - candidate3 on the same exact saved Phase-C starts is slightly worse:
    - candidate `0.569`
    - candidate minus control `-0.002`
  - control winner stays on retained `phaseB_topk` rank `2`
  - candidate winner shifts to `phaseB_topk` rank `3`
- interpretation:
  - the narrowed Phase-C-only replay lane is now stable enough to judge
    candidate3 honestly on `1511/search7004`
  - on that exact saved-surface lane, candidate3 is a small clean negative
  - this changes the local blocker on `1511/search7004`:
    - it is no longer replay fidelity on the saved-surface lane
    - it is candidate utility

## 2026-04-17 - Candidate3 saved-surface exact checks extended to middle and conversion cases

- added thin exact saved-surface wrappers for two more retained cases:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_611_7004.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1111_7002.py`
- verification:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_candidate3_saved_surface_exact_replay.py tests/tools/test_no_wli_candidate3_saved_surface.py tests/tools/test_no_wli_fixed_instance_solver_development_v1.py -q`
  - result:
    - `32 passed`
- exact saved-surface bundle on `611/search7004`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055021Z__candidate3_phasec_saved_surface_exact_611_search7004_v1/`
  - read:
    - control reproduces retained `0.758`
    - candidate3 also lands at `0.758`
    - candidate minus control `0.000`
  - interpretation:
    - candidate3 is neutral on this exact saved-surface middle-case lane
- exact saved-surface bundle on `1111/search7002`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T055755Z__candidate3_phasec_saved_surface_exact_1111_search7002_v1/`
  - read:
    - control lands at `0.750`
    - candidate3 improves to `0.754`
    - retained Stage-3 reference is `0.752`
    - candidate minus control `+0.004`
  - interpretation:
    - candidate3 is genuinely live on at least one exact saved-surface
      conversion-failure case
- combined exact saved-surface read for candidate3 is now:
  - `1511/search7004`: small negative
  - `611/search7004`: neutral
  - `1111/search7002`: positive
- current conclusion:
  - candidate3 is no longer mainly a replay-fidelity question on the narrowed
    saved-surface lane
  - candidate3 is now a real but case-dependent solver idea
  - do not promote it yet, but do not close it either

## 2026-04-17 - Shareable fixed-instance solver-development review pack assembled

- created a new planning/results review pack intended to travel alongside the
  separate src bundle:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_instance_solver_development_v1_review_pack_2026-04-17/`
  - zip:
    - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_instance_solver_development_v1_review_pack_2026-04-17.zip`
- scope:
  - copied active planning context
  - copied compact reviewer-facing readouts from the fixed-analysis bundle and
    the candidate1/2/3 bundles
  - added manifests for:
    - the code files to inspect in the separate src bundle
    - the raw output directories behind the copied readouts
- intentionally excluded:
  - source code
  - tests
  - large raw output directories
- current use:
  - share this pack with the separate src bundle generated from
    `tools/get_src_extended_review_bundle.py`

## 2026-04-17 - Candidate3 review framing tightened after code review

- external review on the shareable pack tightened the candidate3 read:
  - candidate2 closure is strongly supported by the code and retained surfaces
  - candidate3 is not well described as an established solver improvement
- wording corrections landed in:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_instance_solver_development_v1_review_pack_2026-04-17/`
  - `planning/projects/no_wli/00_CURRENT_STATE.md`
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/SPEC.md`
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/EXPERIMENT_PLAN.md`
- corrected candidate3 framing:
  - candidate3 remains alive only narrowly on the exact saved-surface lane
  - current evidence is mixed and small-effect:
    - `1511/search7004`: small negative
    - `611/search7004`: neutral
    - `1111/search7002`: small positive
  - candidate3 remains a positional reorder probe, not an established solver
    improvement
- next move remains:
  - one more targeted exact saved-surface check
  - with stronger ordered-identity replay contracts before any promotion talk

## 2026-04-17 - Candidate3 ordered-identity contract tightened and two more exact cases run

- tightened the candidate3 replay-fidelity audit so it now persists explicit
  ordered-identity contract rows for:
  - `phaseB_downstream_selected_ordered_hashes`
  - `phaseB_topk_saved_ordered_hashes`
  - `phaseC_start_ordered_identities`
- focused verification:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_candidate3_replay_fidelity_audit.py tests/tools/test_no_wli_candidate3_saved_surface.py tests/tools/test_no_wli_candidate3_saved_surface_exact_replay.py tests/tools/test_no_wli_fixed_instance_solver_development_v1.py -q`
  - result:
    - `38 passed`
- added exact saved-surface wrappers:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_611_7001.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1511_7005.py`
- exact saved-surface bundle on `611/search7001`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T152806Z__candidate3_phasec_saved_surface_exact_611_search7001_v1/`
  - read:
    - control `0.381`
    - candidate `0.383`
    - retained Stage-3 reference `0.450`
    - candidate minus control `+0.002`
  - interpretation:
    - small control-relative gain only
    - saved-surface control still misses the retained Stage-3 winner
      materially, so this is not a clean utility decision gate
- exact saved-surface bundle on `1511/search7005`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260417T153047Z__candidate3_phasec_saved_surface_exact_1511_search7005_v1/`
  - read:
    - control `0.686`
    - candidate `0.686`
    - retained Stage-3 reference `0.691`
    - candidate minus control `0.000`
  - interpretation:
    - near-stable positive-control lane
    - candidate3 is neutral here
- updated combined candidate3 read:
  - stable or near-stable exact saved-surface lanes:
    - `1511/search7004`: small negative
    - `1511/search7005`: neutral
    - `611/search7004`: neutral
    - `1111/search7002`: small positive
  - additional drifted lane:
    - `611/search7001`: small positive versus control, but not a clean
      decision gate
- current conclusion:
  - candidate3 remains alive only narrowly
  - the saved-surface exact helper is a case-qualified decision gate, not a
    globally valid shortcut
  - candidate3 should still not be promoted to live runtime

## 2026-04-18 - Candidate3 exact 1111 family extended to four and then five seeds

- added exact saved-surface wrappers:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1111_7001.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1111_7003.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1111_7004.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1111_7005.py`
- exact saved-surface bundle on `1111/search7001`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T010939Z__candidate3_phasec_saved_surface_exact_1111_search7001_v1/`
  - read:
    - control `0.420`
    - candidate `0.420`
    - retained Stage-3 reference `0.420`
    - candidate minus control `0.000`
  - interpretation:
    - stable conversion-failure lane
    - candidate3 is neutral here
- exact saved-surface bundle on `1111/search7003`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T011123Z__candidate3_phasec_saved_surface_exact_1111_search7003_v1/`
  - read:
    - control `0.041`
    - candidate `0.041`
    - retained Stage-3 reference `0.323`
    - candidate minus control `0.000`
  - interpretation:
    - drifted conversion-failure lane
    - candidate3 is neutral here, but this is not a clean decision gate
- exact saved-surface bundle on `1111/search7004`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T011226Z__candidate3_phasec_saved_surface_exact_1111_search7004_v1/`
  - read:
    - control `0.432`
    - candidate `0.434`
    - retained Stage-3 reference `0.432`
    - candidate minus control `+0.002`
  - interpretation:
    - stable conversion-failure lane
    - candidate3 shows a second small positive on `1111`
- exact saved-surface bundle on `1111/search7005`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T010749Z__candidate3_phasec_saved_surface_exact_1111_search7005_v1/`
  - read:
    - control `0.366`
    - candidate `0.366`
    - retained Stage-3 reference `0.416`
    - candidate minus control `0.000`
  - interpretation:
    - drifted conversion-failure lane
    - candidate3 is neutral here
- updated exact `1111` family read:
  - stable or near-stable lanes:
    - `7001`: neutral
    - `7002`: small positive
    - `7004`: small positive
  - drifted lanes:
    - `7003`: neutral
    - `7005`: neutral
- updated broader candidate3 read:
  - stable or near-stable panel lanes:
    - `1511/search7004`: small negative
    - `1511/search7005`: neutral
    - `611/search7004`: neutral
    - `1111/search7001`: neutral
    - `1111/search7002`: small positive
    - `1111/search7004`: small positive
  - drifted context lanes:
    - `611/search7001`: small positive
    - `1111/search7003`: neutral
    - `1111/search7005`: neutral
- current conclusion:
  - candidate3 still does not support live promotion
  - but it now looks more `1111`-specific than panel-general
  - the next sensible move is review or a small `1111`-focused refinement,
    not a broad panel-wide promotion claim

## 2026-04-18 - Candidate3 exact matrix added and two more 1511 lanes checked

- added exact saved-surface wrappers:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1511_7002.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_1511_7003.py`
- exact saved-surface bundle on `1511/search7002`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7002_v1/`
  - read:
    - control `0.842`
    - candidate `0.842`
    - retained Stage-3 reference `0.842`
    - candidate minus control `0.000`
  - interpretation:
    - stable positive-control lane
    - candidate3 is neutral here
- exact saved-surface bundle on `1511/search7003`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T012640Z__candidate3_phasec_saved_surface_exact_1511_search7003_v1/`
  - read:
    - control `0.844`
    - candidate `0.844`
    - retained Stage-3 reference `0.845`
    - candidate minus control `0.000`
  - interpretation:
    - near-stable positive-control lane
    - candidate3 is neutral here
- added exact-lane matrix extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_candidate3_saved_surface_exact_matrix_v1.py`
- exact-lane matrix bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T013222Z__candidate3_saved_surface_exact_matrix_v1/`
  - usable-gate summary:
    - total exact cases `11`
    - usable decision gates `8`
    - drifted context lanes `3`
    - usable-gate read:
      - `2` positives
      - `5` neutrals
      - `1` negative
    - per-instance usable-gate read:
      - `611`: `1` neutral
      - `1111`: `2` positives, `1` neutral
      - `1511`: `3` neutrals, `1` negative
- focused verification:
  - `c:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_candidate3_saved_surface_exact_matrix.py tests/tools/test_no_wli_candidate3_saved_surface_exact_replay.py tests/tools/test_no_wli_fixed_instance_solver_development_v1.py -q`
  - result:
    - `33 passed`
- current conclusion:
  - candidate3 still does not support live promotion
  - candidate3 now reads more like a narrow `1111` conversion-lane effect than
    a panel-wide improvement
  - the added usable `1511` lanes are neutral rather than positive

## 2026-04-18 - Candidate3 611 search7005 exact check added

- added exact saved-surface wrapper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_candidate3_phasec_saved_surface_exact_611_7005.py`
- exact saved-surface bundle on `611/search7005`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T014639Z__candidate3_phasec_saved_surface_exact_611_search7005_v1/`
  - read:
    - control `0.585`
    - candidate `0.589`
    - retained Stage-3 reference `0.615`
    - candidate minus control `+0.004`
  - interpretation:
    - drifted middle-case lane
    - small control-relative gain only
    - not a clean decision gate because the control lane itself still sits
      below retained
- refreshed exact-lane matrix bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260418T014734Z__candidate3_saved_surface_exact_matrix_v1/`
  - updated usable-gate summary:
    - total exact cases `12`
    - usable decision gates `8`
    - drifted context lanes `4`
    - usable-gate read:
      - `2` positives
      - `5` neutrals
      - `1` negative
- current conclusion:
  - candidate3 still has no clean middle-case win
  - `611` now reads as one usable neutral lane plus two drifted positive teases
  - the strongest honest read remains: candidate3 is narrow and `1111`-leaning,
    not panel-general

## 2026-04-19 to 2026-04-21 - downstream replacement stayed closed and the upstream supply retake became the branch point

- the downstream late-pool family is now settled in two stages:
  - the saved-surface replacement / eviction line closed negative
  - the saved-surface `phaseB_topk` mass / frontload line also closed
- the shared lesson from those closures was:
  - reorder-only controls could show small positive movement
  - but downstream replacement remained structurally blocked because there were
    no spare eligible non-selected retained `phaseB_topk` challengers outside
    the selected set
- that moved the active mechanism question upstream into Phase-B challenger
  supply

Operational correction:

- the original `phase-B challenger supply matrix v1` serial batch was not
  honestly sized for the machine
- the valid scientific residue from that failed batch was retained
- the project rule is now explicit:
  - treat new long no-WLI runtime families as independently complete
    microbatches until real family-specific timing evidence exists

The decisive richer-supply retake is now complete:

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260421T145900Z__phaseb_challenger_supply_retake_microbatch_v1/`
- target cell:
  - fixed `1111/search7002`
- supply preset:
  - `phaseb_supply_selected24_saved64_stage3only_v1`
- read:
  - true spare non-selected retained `phaseB_topk` challengers:
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

Branch conclusion:

- the upstream supply suspicion was scientifically real
- the richer pool really did create new spare retained challengers
- but the supply family became expensive enough that another blind deeper
  supply retry was not the honest next move
- the next active question had to be:
  - whether downstream replacement becomes solver-usable once real spare
    challengers exist on the richer pool

## 2026-04-22 - richer-pool downstream replacement reopen closed and the live branch moved to entry allocation

The richer-pool downstream replacement reopen is now complete and closed:

- completed exact-lane bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260422T015033Z__phasec_richer_pool_phaseb_replacement_reopen_v1/`
- closure note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_phasec_richer_pool_replacement_reopen_closure_note_2026-04-22.md`
- exact-lane read:
  - richer-pool `source_order`:
    - `0.750`
  - reorder floor `phaseb_topk_frontload_all_v1`:
    - `0.754`
  - replacement widths `1`, `2`, `3`:
    - all `0.750`
  - all replacement widths changed saved-start membership and order
  - none changed the winner or beat the reorder floor

Scientific lesson:

- the richer-supply retake was scientifically real
- narrow downstream `phaseB_topk`-only replacement was still not solver-usable
- so the next live step should not remain in the downstream ordering /
  replacement family

Current method step:

- preserve the bounded Stage 3.5 baseline stack
- change only one mechanism layer:
  - `allocation`
- use the smallest honest fixed-cell live falsification on the main `1111`
  conversion-failure family

Current live branch hypothesis block:

- Question:
  - on fixed `1111/search7004`, does preserving the bounded Stage 3.5 stack but
    widening Stage-3 entry with constant-local-depth beat the bounded control?
- Suspicion:
  - `1111/search7004` may still be entry-budget-starved before the bounded late
    stack gets its chance
- Main alternative:
  - the current bounded stack already captures what this lane can use, so wider
    entry will stay flat or worse
- If suspicion is true, expect:
  - larger executed entry counts and a better late-route outcome than control
- If alternative is true, expect:
  - executed widening but flat / worse outcome, or little real executed change
- Tomorrow's decision rule:
  - promote only if the candidate wins cleanly, really widens executed entry,
    and still fits budget
  - refine only if the gain is real but narrow
  - close if the candidate is flat or worse even after real widening

Live canary status:

- plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_canary_plan_2026-04-22.md`
- experiment id:
  - `tune_v76_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_compare_2job`
- target cell:
  - fixed `1111/search7004`
- runtime shape:
  - two jobs
  - control first
  - candidate second only if the first completed job still fits the intended
    `~8h` session budget
- live log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_canary_2026-04-22.log`
- live state as of `2026-04-21T20:51:20-07:00`:
  - `completed_jobs = 0 / 2`
  - control job still running
  - Phase B has finished
  - Phase C has started
  - first-job budget recalculation is still pending

Contingent replication step:

- prepared follow-on plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_plan_2026-04-22.md`
- target cell:
  - fixed `1111/search7005`
- retained exact wallclock anchor:
  - about `2.48h`
- retained two-job anchor:
  - about `4.96h`
- queue watcher log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_queue_2026-04-22.log`
- queue rule:
  - auto-launch only if the live `1111/search7004` canary completes before
    `2026-04-22 01:15` America/Los_Angeles
  - otherwise abort cleanly

Current branch discipline:

- do not run the follow-on in parallel with the live canary
- do not widen to a broader panel before the same-family replication read
- keep the science claim at one mechanism layer until this branch either:
  - promotes
  - refines
  - or closes

## 2026-04-22 - entry-allocation two-job live canary killed; rescued as partial control evidence only

The fixed `1111/search7004` entry-allocation canary did not complete as an
honest two-job branch decision unit.

Experiment:

- `tune_v76_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_compare_2job`

Planned role:

- control first
- candidate second only if the first completed job still fit the intended
  `~8h` session budget

What actually happened:

- the matrix wrapper never advanced beyond one `job_started` event
- `completed_jobs` stayed at `0 / 2`
- no completed-job artifacts were written
- the live process was later killed intentionally rather than left running by
  inertia

Rescued runtime artifact:

- child run dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T024910116301Z__bench_solve_pipeline_no_wli__ee62083/`

Rescued partial evidence:

- `phasec_start_checkpoints.jsonl` completed `5 / 6` starts before the kill
- the watcher log showed the run had already entered:
  - Phase C start `6 / 6`, step `73 / 96`
- per-start rescued best reads:
  - start `1`:
    - source `stage3_best_phaseA`
    - final match `0.432`
    - final score `0.17955717672334726`
  - start `2`:
    - `0.413`
  - start `3`:
    - `0.399`
  - start `4`:
    - `0.411`
  - start `5`:
    - `0.364`
- start `6` did not complete

Scientific read:

- the rescued control lane was still useful
- the best rescued control read matched the retained stable `1111/search7004`
  anchor family:
  - retained `max_mapped_family_by_final_match`:
    - `0.432`
  - rescued partial control best:
    - `0.432`
- so the control lane did not look badly drifted

But the intended branch decision was not reached:

- the candidate never ran
- there is no control-versus-candidate comparison
- there is no completed first-job matrix outcome to budget from honestly

Decision on this runtime shape:

- close the **two-job live canary shape** operationally
- do not call the allocation hypothesis negative from this session
- keep only the rescued partial control evidence

Operational follow-on outcome:

- the queued same-family `1111/search7005` follow-on never launched
- queue log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_queue_2026-04-22.log`
- final queue read:
  - `queue_aborted reason=cutoff_reached_before_current_completed`

Carry-forward lesson:

- a first job that can already miss the budget and fail to emit a completed-job
  artifact is not an honest canary shape
- future live units on this branch should be:
  - independently complete one-job probes
  - or preceded by cheaper offline / saved-surface / shadow gates

Repo-state refresh after kill:

- no active multi-hour no-WLI runtime is currently confirmed from repo state

## 2026-04-22 - prepared next allocation step as a one-job fixed probe on 1111/search7004

The next live step is now prepared rather than launched:

- plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_plan_2026-04-22.md`
- experiment id:
  - `tune_v78_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_probe_1job`
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1.py`
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1.py`

Why this is the next honest move:

- the paired `v76` compare is closed as a runtime shape
- the allocation hypothesis is still scientifically open
- the branch now needs the smallest independently complete live unit
- fixed `1111/search7004` already has:
  - the cheapest retained exact control anchor in the family:
    - about `2.36h`
  - rescued same-lane control fidelity from the killed canary:
    - best rescued control read `0.432`
    - retained mapped-family max final match `0.432`

Prepared hypothesis block:

- Question:
  - on fixed `1111/search7004`, can the bounded constant-local-depth candidate
    beat the retained fixed control reference inside an honest `~8h`
    single-job session?
- Suspicion:
  - `1111/search7004` is still entry-budget-starved, and one completed
    candidate job can show that without paying for same-session paired-control
    overhead.
- Main alternative:
  - the candidate stays flat or worse than retained control, or still fails to
    complete honestly enough to justify another overnight session.
- If suspicion is true, expect:
  - completed candidate
  - real executed widening
  - best match above retained `0.423`
- If alternative is true, expect:
  - flat / worse completed result
  - or no completed artifact by the written stop
- Tomorrow's decision rule:
  - advance only if the candidate completes within the `~8h` session, widens
    execution for real, and beats retained control cleanly
  - refine only for a narrow near-miss or budget-fragile positive
  - close if flat, worse, or incomplete

Prepared stop rule:

- this is a one-job probe
- if normal completion artifacts are still missing at launch `+ 8h`, kill the
  run manually and record operational incompleteness rather than letting it run
  by inertia

## 2026-04-22 - closed the fixed 1111/search7004 one-job allocation probe as over-budget and structurally underpowered

The prepared one-job `1111/search7004` entry-allocation probe was launched and
later closed without promotion.

Closed experiment:

- `tune_v78_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_probe_1job`

Child run dir:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T154043010456Z__bench_solve_pipeline_no_wli__ee62083/`

Closure note:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_closure_note_2026-04-22.md`

What happened:

- the process ran past the written `~8h` stop rule and was then stopped
- no normal completion artifacts were written
- the rescued partial bundle completed only `4 / 6` Phase-C starts

Best partial read:

- start `1`
- source:
  - `stage3_best_phaseA`
- final match:
  - `0.432`
- final score:
  - `0.17955717672334726`

Retained comparison:

- retained run-level best match:
  - `0.423`
- retained mapped-family max final match:
  - `0.432`
- retained focus-family max final score:
  - `0.17955717672334737`

So the partial run taught two real things:

- partial evidence was already enough to stop
- the probe reproduced the retained anchor-family best rather than improving it

More important structural lesson:

- with:
  - base entry budget `64`
  - `phase_b_top_n = 32`
  - `mutations_per_promoted = 1`
- the exact config could widen Stage-3 entry by at most:
  - `+2` keys over legacy
- so the configured cap `288` never mattered

Decision:

- close the exact `constant_local_depth` fixed `1111/search7004` probe shape
- close the contingent `1111/search7005` replication gate from this branch
- require a written structural-activation proof before any future allocation
  runtime
- if no such proof can be made cheaply, move the next branch upstream from
  entry allocation

## 2026-04-22 - completed the upstream fixed-panel promoted-family audit and changed the next branch

After the closed allocation probe, the next step was an offline upstream audit
on the frozen fixed primary trio.

Question:

- does `1111` fail because upstream promoted-family supply is missing the right
  family, or because it already carries a better family but surfaces a weak
  representative inside it before Stage 3 starts?

Study bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/`

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_stage3_promoted_family_audit_v1.py`

Primary family view:

- `prefix_hamming_le_24`

Coverage:

- fixed `611/search7001-7005`
- fixed `1111/search7001-7005`
- fixed `1511/search7001-7005`

Main read from the fixture summary table:

- `stage2_stage3_promoted_family_audit_fixture_summary_rows.csv`
- `1111`:
  - `mean_stage2_topk_within_family_gap = 0.070`
  - `mean_stage2_promoted_within_family_gap = 0.070`
  - `mean_stage2_promoted_between_family_gap = 0.014`
  - `dominant_upstream_pattern = persistent_within_family_representative_gap`
- `611`:
  - `mean_stage2_promoted_within_family_gap = 0.000`
- `1511`:
  - `mean_stage2_promoted_within_family_gap = 0.000`

Recommendation payload:

- `stage2_stage3_promoted_family_audit_recommendation.json`
- fields:
  - `recommendation = "advance"`
  - `next_branch_label = "stage2_stage3_within_family_representative_selection_microprobe"`
  - `mechanism_layer = "selection"`

Interpretation:

- the current `1111` upstream issue does not mainly look like missing family
  diversity
- it looks like a representative-selection problem inside an already-present
  upstream family region
- the next honest branch is therefore:
  - a small upstream representative-selection microprobe

Decision:

- advance upstream, but not to a new multi-hour runtime yet
- do not spend the next run on generic family-diversity or entry-allocation
  work
- write the next microprobe around upstream representative selection inside the
  promoted family surface

## 2026-04-22 to 2026-04-23 - turned the upstream representative-selection diagnosis into one concrete selector

After the promoted-family audit, the next question was whether the diagnosis
could be turned into one concrete policy instead of staying vague.

Question:

- after the upstream audit, can one simple selector on the saved `stage2_topk`
  surface recover the hidden stronger `1111` representative without moving the
  controls?

Study bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/`

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_family_representative_policy_audit_v1.py`

Candidate policy:

- `selected_family_low_edge_eps_0p020_v1`

Coverage:

- fixed `611/search7001-7005`
- fixed `1111/search7001-7005`
- fixed `1411/search7001-7005`
- fixed `1511/search7001-7005`

Cross-checked evidence:

- fixture summary table:
  - `stage2_topk_family_representative_policy_fixture_summary_rows.csv`
- `1111` row:
  - `candidate_active_run_count = 5`
  - `candidate_oracle_match_run_count = 5`
  - `mean_candidate_truth_delta_vs_baseline = 0.070`
- `611` row:
  - `candidate_active_run_count = 0`
  - `mean_candidate_truth_delta_vs_baseline = 0.0`
- `1411` row:
  - `candidate_active_run_count = 0`
  - `mean_candidate_truth_delta_vs_baseline = 0.0`
- `1511` row:
  - `candidate_active_run_count = 0`
  - `mean_candidate_truth_delta_vs_baseline = 0.0`
- recommendation payload:
  - `stage2_topk_family_representative_policy_recommendation.json`
  - fields:
    - `recommendation = "advance"`
    - `next_branch_label = "stage2_topk_selected_family_low_edge_microprobe"`
    - `candidate_policy_id = "selected_family_low_edge_eps_0p020_v1"`

Conclusion:

- the upstream representative-selection story is no longer only diagnostic
- one simple selector exists that is active on all five retained `1111` lanes
  and inert on the controls
- the next honest issue is now selector narrowing, not selector existence

## 2026-04-23 - narrowed the selector to one minimal viable family-view / score-band setting

The next short study asked whether the concrete selector was robust enough to
specify one exact policy.

Question:

- is the `1111` selector real enough to specify one concrete family view and
  score band, or is it just a lucky combination?

Study bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/`

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_family_representative_policy_sensitivity_v1.py`

Swept settings:

- family views:
  - `exact_key`
  - `exact_tail`
  - `near_tail_h1`
  - `prefix_hamming_le_24`
- score bands:
  - `0.010`
  - `0.015`
  - `0.016`
  - `0.020`
  - `0.025`

Cross-checked evidence:

- setting summary table:
  - `stage2_topk_family_representative_policy_sensitivity_setting_summary_rows.csv`
- key `1111` rows under `prefix_hamming_le_24`:
  - `eps = 0.010`
    - inactive
    - mean delta `0.000`
  - `eps = 0.015`
    - active on all `5 / 5` lanes
    - mean delta `-0.023`
    - negative deltas present
  - `eps = 0.016`
    - active on all `5 / 5` lanes
    - mean delta `+0.070`
    - no negative deltas
  - `eps = 0.020`
    - active on all `5 / 5` lanes
    - mean delta `+0.070`
    - no negative deltas
  - `eps = 0.025`
    - active on all `5 / 5` lanes
    - mean delta `+0.005`
    - no negative deltas
- all non-`prefix_hamming_le_24` views stayed inert across the sweep
- recommendation payload:
  - `stage2_topk_family_representative_policy_sensitivity_recommendation.json`
  - fields:
    - `recommendation = "advance"`
    - `next_branch_label = "stage2_topk_selected_family_low_edge_eps_0p016_microprobe"`
    - `candidate_policy_id = "selected_family_low_edge_eps_0p016_v1"`
    - `family_view_id = "prefix_hamming_le_24"`
    - `score_band_eps = 0.016`

Conclusion:

- the selector is not a loose cross-view artifact
- the useful window is narrow and asymmetric
- the smallest clean viable setting is now explicit:
  - family view:
    - `prefix_hamming_le_24`
  - selector:
    - `selected_family_low_edge_eps_0p016_v1`
- the next honest branch should use that exact selector id, not a vague
  representative-selection description

## 2026-04-23 - verified that the narrowed selector materially changes the saved Stage-3 handoff

After the selector was narrowed, the last cheap non-execution question was
whether it actually changed the saved Stage-3 handoff.

Question:

- after narrowing the selector to `selected_family_low_edge_eps_0p016_v1`,
  does it materially change the saved Stage-2 to Stage-3 handoff on `1111`, or
  is it effectively a no-op before Stage 3 starts?

Study bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T031321Z__stage2_topk_selected_family_low_edge_handoff_audit_v1/`

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_handoff_audit_v1.py`

Tracked handoff fields:

- `best2_key`
- `promoted_keys`
- `init3`

Cross-checked evidence:

- fixture summary table:
  - `stage2_topk_selected_family_low_edge_handoff_audit_fixture_summary_rows.csv`
- `1111` row:
  - `candidate_active_run_count = 5`
  - `best2_key_changed_run_count = 5`
  - `init3_changed_run_count = 5`
  - `mean_candidate_truth_delta_vs_baseline = 0.070`
  - `mean_init3_edit_count = 7.8`
  - `mean_stage3_promoted_keys_edit_count = 7.8`
- `611` row:
  - `best2_key_changed_run_count = 0`
  - `init3_changed_run_count = 0`
- `1411` row:
  - `best2_key_changed_run_count = 0`
  - `init3_changed_run_count = 0`
- `1511` row:
  - `best2_key_changed_run_count = 0`
  - `init3_changed_run_count = 0`
- recommendation payload:
  - `stage2_topk_selected_family_low_edge_handoff_audit_recommendation.json`
  - fields:
    - `recommendation = "advance"`
    - `next_branch_label = "stage2_topk_selected_family_low_edge_eps_0p016_microprobe"`
    - `candidate_policy_id = "selected_family_low_edge_eps_0p016_v1"`

Conclusion:

- the narrowed selector is not just a row-level curiosity
- it changes the real saved Stage-3 input surface on all five retained `1111`
  lanes
- it stays completely inert on the controls
- the next honest branch is now an execution-level microprobe, not another
  offline selector refinement

## 2026-04-23 - first exact execution gate for the narrowed selector closed negative on fixed 1111/search7004

Question:

- after the saved handoff gate passed, does the concrete selector
  `selected_family_low_edge_eps_0p016_v1` actually improve executed Stage-3
  replay on a fixed `1111` lane?

Why this study existed:

- the selector branch had already passed the cheap offline gates
- we needed the smallest honest execution test before spending more runtime
- the method goal was to see whether saved handoff truth gain survives exact
  execution or collapses there

Hypothesis block:

- Suspicion:
  - `1111/search7004` is a real upstream representative-selection miss and the
    saved handoff gain can survive execution
- Main alternative:
  - the selector improves saved handoff but the execution lane stays flat or
    worse
- Decision rule:
  - advance only if the replay completes honestly and beats retained baseline
    cleanly
  - refine only for a narrow gain or budget-fragile positive
  - close if flat or worse

Run:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`

Outcome:

- completed honestly in:
  - `01:07:53`
- closed as a clean exact negative

Cross-checked evidence:

- completion state:
  - `attempt_status.json`
  - fields:
    - `status = "completed"`
    - `elapsed = "01:07:53"`
    - `resume_bundle_written = 1`
- main replay result:
  - `run_summary.json`
  - fields:
    - `baseline_best_match_ratio = 0.423`
    - `retained_stage3_reference_match_ratio = 0.432`
    - `resume_best_match_ratio = 0.420`
    - `match_delta_vs_baseline = -0.003`
    - `match_delta_vs_retained_stage3_reference = -0.012`
- selector-specific handoff read:
  - `selected_family_low_edge_exact_replay_summary.json`
  - fields:
    - `baseline_row_truth_match = 0.091`
    - `candidate_row_truth_match = 0.161`
    - `candidate_truth_delta_vs_baseline_row = 0.070`
    - `candidate_stage3_promoted_keys_count = 144`
- per-start execution read:
  - `resume_bundle/phasec_start_checkpoints.jsonl`
  - strongest challenger:
    - start `2`
    - source:
      - `phaseA_selected`
    - init `0.415`
    - final `0.420`
    - `became_global_best = 1`
    - `overtook_anchor = 1`
- in-app progress persistence now verified:
  - `resume_bundle/stage3_resume_status.json`
  - `resume_bundle/stage3_resume_progress.jsonl`
  - `resume_bundle/phasec_start_checkpoints.jsonl`

Conclusion:

- the selector was real at the saved handoff
- the selector was also real in execution because it created a strong
  challenger lane
- that gain still failed to convert into a replay win
- this closes the first exact execution gate for the selector as a clean
  negative

Carry-forward lesson:

- do not spend a second replay or live runtime on habit
- the next honest step is a cheap execution-collapse / postmortem audit to
  explain where the saved handoff advantage is being lost

## 2026-04-23 - exact selector family matrix across fixed 1111/search7001-7005 finished mixed and remains in refine state

Question:

- after the first exact negative on fixed `1111/search7004`, is the narrowed
  selector uniformly bad across fixed `1111/search7001-7005`, or is the exact
  family read mixed?

Why this study existed:

- the first exact gate had already shown the selector was:
  - real at the saved handoff
  - real enough to create a strong challenger lane in execution
- but one local negative was not enough to say whether the branch should:
  - close
  - refine
  - or earn any larger runtime

Hypothesis block:

- Suspicion:
  - `7004` may be only one local negative, and at least one more fixed `1111`
    lane may convert the saved handoff gain into a real exact replay win
- Main alternative:
  - the selector line is exact-negative enough across the family that it should
    close before any live runtime
- Decision rule:
  - advance only if the family produces at least two clean wins versus both the
    artifact baseline and the retained Stage-3 reference
  - refine only for a mixed family with at least one clean win
  - close if the family remains flat or worse overall

Run:

- matrix runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1.py`
- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_2026-04-23.log`

Outcome:

- completed honestly in:
  - `01:52:14`
- result:
  - `refine`

Cross-checked evidence:

- matrix state:
  - `matrix_run_state.json`
  - fields:
    - `status = "completed"`
    - `completed_jobs = 5`
    - `elapsed = "01:52:14"`
- matrix summary:
  - `selected_family_low_edge_exact_replay_1111_matrix_summary.json`
  - fields:
    - `recommendation = "refine"`
    - `clean_win_count = 1`
    - `baseline_win_count = 2`
    - `best_search_seed = 7003`
    - `best_delta_vs_baseline = 0.068`
    - `best_delta_vs_retained_stage3_reference = 0.153`
    - `family_mean_delta_vs_baseline = -0.121`
- per-seed rows:
  - `selected_family_low_edge_exact_replay_1111_matrix_rows.csv`
  - `7004`:
    - baseline `0.423`
    - retained `0.432`
    - replay `0.420`
    - delta vs baseline `-0.003`
  - `7001`:
    - baseline `0.428`
    - retained `0.420`
    - replay `0.161`
    - delta vs baseline `-0.267`
  - `7003`:
    - baseline `0.408`
    - retained `0.323`
    - replay `0.476`
    - delta vs baseline `+0.068`
    - delta vs retained `+0.153`
  - `7005`:
    - baseline `0.372`
    - retained `0.416`
    - replay `0.413`
    - delta vs baseline `+0.041`
    - delta vs retained `-0.003`
  - `7002`:
    - baseline `0.754`
    - retained `0.752`
    - replay `0.310`
    - delta vs baseline `-0.444`
- one stable saved-handoff fact across the family:
  - every row still shows:
    - `candidate_truth_delta_vs_baseline_row = 0.070`

Conclusion:

- the selector is not uniformly exact-negative across the fixed `1111` family
- one lane is a real clean exact positive:
  - `7003`
- one second lane is at least baseline-positive and almost retained-neutral:
  - `7005`
- but the family is still not stable enough to promote:
  - `7001` and `7002` collapse too hard
  - family mean delta vs baseline remains negative

Carry-forward lesson:

- do not promote the raw selector line to live runtime
- do not describe the selector as fully closed either
- the next honest step is a conditioned selector postmortem / refinement audit
  focused on why the same saved handoff gain produces:
  - a clean exact win on `7003`
  - a near win on `7005`
  - but severe collapses on `7001` and `7002`

## 2026-04-23 - Phase-A competitiveness audit found a concrete early gate for the mixed selector family

Question:

- after the mixed exact-family replay result, do simple early Phase-A
  competitiveness signals separate the `1111` wins / near wins from the hard
  collapses cheaply enough to justify a conditioned selector rule?

Why this study existed:

- the exact family matrix had already shown the raw selector was:
  - real
  - mixed
  - and not live-promotable
- we needed the cheapest next step that could:
  - explain the split
  - narrow the branch honestly
  - and contribute to faster stop / fallback discipline

Hypothesis block:

- Suspicion:
  - the two hard collapse lanes should already look weak by an early Phase-A
    competitiveness signal
- Main alternative:
  - the split is only visible late, so no cheap conditioned gate exists
- Decision rule:
  - advance only if one early Phase-A threshold filters both hard collapse
    lanes, keeps all three non-catastrophic lanes, and turns the
    counterfactual family mean delta versus baseline positive
  - refine if the split is only partial
  - close if no cheap early gate exists

Run:

- script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1.py`
- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/`

Outcome:

- completed as a short offline audit
- result:
  - `advance`

Cross-checked evidence:

- summary payload:
  - `stage2_topk_selected_family_low_edge_phasea_competitiveness_summary.json`
  - fields:
    - `recommendation.recommendation = "advance"`
    - `recommendation.best_gate_id = "rank1_init_ge_0p30"`
    - `recommendation.best_metric_name = "phasea_rank1_init_match"`
    - `recommendation.best_threshold = 0.3`
    - `recommendation.next_branch_label = "stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe"`
- per-seed case rows:
  - `stage2_topk_selected_family_low_edge_phasea_competitiveness_case_rows.csv`
  - `7001`
    - `phasea_rank1_init_match = 0.254`
    - `case_category = local_search_collapse_after_phasea`
    - `phasea_best_to_stage3_conversion_delta = -0.227`
  - `7002`
    - `phasea_rank1_init_match = 0.289`
    - `case_category = phasea_competitiveness_below_floor`
    - `phasea_best_to_stage3_conversion_delta = +0.001`
  - `7003`
    - `phasea_rank1_init_match = 0.490`
    - `case_category = clean_exact_positive`
  - `7004`
    - `phasea_rank1_init_match = 0.415`
    - `case_category = competitive_near_floor`
  - `7005`
    - `phasea_rank1_init_match = 0.395`
    - `case_category = baseline_positive_near_retained`
- threshold summary:
  - `stage2_topk_selected_family_low_edge_phasea_competitiveness_threshold_summary_rows.csv`
  - best row:
    - `gate_id = rank1_init_ge_0p30`
    - kept seeds:
      - `7003,7004,7005`
    - filtered seeds:
      - `7001,7002`
    - kept mean delta vs baseline:
      - `+0.035`
    - filtered mean delta vs baseline:
      - `-0.356`
    - counterfactual family mean delta vs baseline:
      - `+0.021`
    - counterfactual family mean delta vs retained:
      - `+0.028`
    - `filters_all_hard_collapses = 1`
    - `keeps_all_noncatastrophic = 1`

Conclusion:

- the mixed selector family result is no longer just an unexplained split
- an early Phase-A signal already separates both hard collapses from the three
  non-catastrophic lanes
- the simplest current gate is:
  - `phasea_rank1_init_match >= 0.30`
- the next honest branch is now a concrete gated microprobe, not another raw
  replay family and not a live runtime

## 2026-04-23 - Phase-A rank-1 gate microprobe showed the gate would also save most bad-lane wallclock

Question:

- if we condition the concrete selector on `phasea_rank1_init_match >= 0.30`
  and fall back immediately on filtered lanes, does the fixed `1111`
  exact-family read become both safer and cheaper?

Why this study existed:

- the previous audit had already shown the gate was real
- we still needed to know whether it mattered operationally
- the method goal here was:
  - do not implement gate plumbing by intuition
  - first prove the gate would actually avoid bad spend on the known collapse
    lanes

Hypothesis block:

- Suspicion:
  - the concrete gate should keep the family counterfactual positive while
    saving most of the filtered lanes' exact-replay wallclock
- Main alternative:
  - the gate may look explanatory but save too little runtime to justify
    persistence work
- Decision rule:
  - advance only if the gate keeps the family counterfactual positive, avoids
    catastrophic kept-lane harm, and saves a large majority of filtered-lane
    wallclock

Run:

- script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1.py`
- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T023226Z__stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_v1/`

Outcome:

- completed as a short offline operational microprobe
- result:
  - `advance`

Cross-checked evidence:

- summary payload:
  - `stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_summary.json`
  - fields:
    - `recommendation.recommendation = "advance"`
    - `recommendation.next_branch_label = "stage2_topk_selected_family_low_edge_phasea_rank1_gate_persistence_microprobe"`
    - `summary_row.counterfactual_family_mean_delta_vs_baseline = 0.0212`
    - `summary_row.counterfactual_family_mean_delta_vs_retained_stage3_reference = 0.0296`
    - `summary_row.counterfactual_family_worst_delta_vs_baseline = -0.003`
    - `summary_row.filtered_estimated_saved_attempt_minutes_total = 42.31`
    - `summary_row.filtered_estimated_saved_attempt_share = 0.9607`
    - `summary_row.mean_phasea_gate_proxy_elapsed_seconds = 52.76`
- per-seed counterfactual rows:
  - `stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe_rows.csv`
  - `7001`
    - mode:
      - `baseline_fallback_after_phasea`
    - counterfactual delta vs baseline:
      - `0.000`
    - counterfactual delta vs retained:
      - `+0.008`
    - saved attempt seconds:
      - `1256.5`
  - `7002`
    - mode:
      - `baseline_fallback_after_phasea`
    - counterfactual delta vs baseline:
      - `0.000`
    - counterfactual delta vs retained:
      - `+0.002`
    - saved attempt seconds:
      - `1282.0`
  - kept lanes:
    - `7003`
      - `+0.068` vs baseline
    - `7004`
      - `-0.003` vs baseline
    - `7005`
      - `+0.041` vs baseline

Conclusion:

- the gate is not just explanatory
- on the known bad lanes it would have avoided about:
  - `42.3` minutes of exact-replay attempt wallclock
  - `96.1%` of filtered-lane attempt time
- the next honest branch is no longer another replay family
- the next honest branch is now a gate persistence / actionability microprobe

## 2026-04-23 - Phase-A gate persistence landed inside the replay resume bundle

Question:

- can the selector branch make the current Phase-A gate inspectable during a
  real replay, inside the Python-run artifacts, before the expensive
  continuation spends most of the attempt?

Why this study existed:

- the gate itself was already proven:
  - `phasea_rank1_init_match >= 0.30`
- and its operational value was already proven:
  - about `42.3` filtered saved minutes
- but the branch still lacked one mid-run artifact that a real replay could
  inspect without bespoke launcher logic

Hypothesis block:

- Suspicion:
  - the gate can be persisted immediately after Phase-A selected rows are
    fixed, and the replay wrapper can surface that artifact cleanly
- Main alternative:
  - the gate is still only reconstructable after completion, or the plumbing
    would require awkward interface churn
- Decision rule:
  - advance only if the replay path writes one explicit Phase-A gate snapshot,
    emits one matching progress event, and exposes the snapshot relpath in the
    replay wrapper status surface

Run:

- core files:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_calls.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
- wrapper update:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
- focused proof:
  - `tests/tools/test_no_wli_artifact_resume.py`
  - `tests/tools/test_no_wli_stage3_phasec.py`
  - `tests/tools/test_no_wli_selected_family_low_edge_exact_replay_1111_7004.py`

Outcome:

- completed as a short implementation microprobe
- result:
  - `advance`

Cross-checked evidence:

- new replay artifact:
  - `resume_bundle/phasea_gate_snapshot.json`
- new progress event:
  - `stage3_phasea_gate_snapshot`
- new wrapper relpath exposure:
  - `phasea_gate_snapshot_json_relpath`
- focused verification:
  - `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_selected_family_low_edge_exact_replay_1111_7004.py -q`
  - result:
    - `40 passed`

Conclusion:

- the gate is no longer only an offline reconstruction
- a real replay bundle can now expose the Phase-A gate surface while the run is
  still in flight
- the next honest branch is no longer more persistence work
- the next honest branch is one cheap live-read canary that decides whether the
  first automated action should be:
  - fallback
  - early stop
  - or both

## 2026-04-23 - prepared the 8-hour family follow-on behind the active 7004 live-read canary

Question:

- after the active `1111/search7004` live-read canary completes, can the rest
  of the fixed `1111` family reproduce the new Phase-A gate snapshot cleanly
  enough to choose the first automated action contract?

Why this setup exists:

- the persistence patch already proved the new snapshot can be written
- the first remaining science-method step is not another new runtime family
- it is one bounded family read on:
  - snapshot presence
  - snapshot timing
  - verdict agreement with the known keep/filter split

Hypothesis block:

- Suspicion:
  - the live snapshot should persist on all five fixed `1111` cells and match
    the current split:
    - keep `7003,7004,7005`
    - filter `7001,7002`
- Main alternative:
  - one or more cells will fail to expose a usable snapshot or disagree with
    the current split
- Decision rule:
  - advance only if the predecessor canary completes with a real snapshot, all
    follow-on cells expose the same surface, and the live verdict matches the
    known split on every completed cell
  - refine for any partial artifact or verdict mismatch

Prepared session:

- single follow-on runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1.py`
- plan note:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_plan_2026-04-23.md`
- active predecessor canary at setup time:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T034213Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- focused proof:
  - `tests/tools/test_no_wli_phasea_gate_live_read_followon_1111_v1.py`

Runtime budgeting proof:

- retained exact-replay anchor:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
  - elapsed:
    - `01:07:53`
- session shape:
  - active predecessor canary:
    - `7004`
  - queued follow-on cells:
    - `7001`
    - `7003`
    - `7005`
    - `7002`
- anchored budget read:
  - five-cell family total:
    - about `5.66h`
  - queued follow-on only:
    - about `4.53h`
  - intended session budget:
    - `8.0h`

Operational rule:

- do not rerun `7004`
- do not launch this follow-on in parallel with the active canary
- let the single follow-on runner wait on the active canary
- if the predecessor finishes without `phasea_gate_snapshot.json`, abort rather
  than continue by inertia
- after each completed follow-on cell, recompute the projected five-cell total
  and stop before launching another cell if the session projects over `8h`

Conclusion:

- the next longer no-WLI data-taking run is now prepared in one Python file
- it is justified from retained timing rather than intuition
- it is scoped to the smallest family session that can answer the current
  actionability question without paying to rerun `7004`

## 2026-04-24 - first live-read canary completed but did not yet validate a usable action surface

Question:

- does one real IDE-style replay on fixed `1111/search7004` make the new
  `phasea_gate_snapshot` artifact both present and actually usable for a live
  keep / filter verdict?

Why this study existed:

- the gate itself was already supported offline
- the gate-saving logic was already supported operationally
- the persistence patch had landed
- the remaining honest question was whether one real replay would expose a
  usable action surface before the expensive continuation had mostly finished

Run:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T034213Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`

Outcome:

- completed honestly in:
  - `01:00:17`
- replay result stayed the same small local negative:
  - baseline `0.423`
  - retained Stage-3 reference `0.432`
  - replay `0.420`
  - delta vs baseline `-0.003`
- the snapshot file did exist:
  - `resume_bundle/phasea_gate_snapshot.json`
- but the live gate payload was not yet usable:
  - `phaseA_rank1_init_match = null`
  - `phaseA_best_init_match = null`
  - `phaseA_rank1_final_match = null`
- snapshot timing was also late:
  - attempt start:
    - `2026-04-24T03:42:13Z`
  - snapshot timestamp:
    - `2026-04-24T04:35:55Z`
  - snapshot elapsed:
    - about `3222s`
    - about `53m42s`
  - snapshot share of total elapsed:
    - about `0.891`

Cross-checked evidence:

- completion surface:
  - `attempt_status.json`
  - fields:
    - `status = "completed"`
    - `elapsed = "01:00:17"`
    - `resume_bundle_written = 1`
- replay summary:
  - `run_summary.json`
  - fields:
    - `baseline_best_match_ratio = 0.423`
    - `retained_stage3_reference_match_ratio = 0.432`
    - `resume_best_match_ratio = 0.420`
    - `match_delta_vs_baseline = -0.003`
- snapshot payload:
  - `resume_bundle/phasea_gate_snapshot.json`
  - fields:
    - `phaseA_rank1_init_match = null`
    - `phaseA_best_init_match = null`
    - `phaseA_rank1_final_match = null`
    - `phaseB_ready_reason = "passed"`
- progress event:
  - `resume_bundle/stage3_resume_progress.jsonl`
  - contains:
    - `event = "stage3_phasea_gate_snapshot"`

Conclusion:

- this was a real persistence smoke pass
- it was not yet a real actionability pass
- the snapshot builder was reading the wrong row schema for the gate metric
- the planned 8-hour family follow-on should not be launched from this
  predecessor canary

Immediate repair:

- patch landed in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- it now backfills the snapshot from the real Phase-A row schema:
  - `end_match`
  - `best_delta_pct`
  - `phaseb_rank`
  - `selection_bucket`
- focused verification after the patch:
  - `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_selected_family_low_edge_exact_replay_1111_7004.py tests/tools/test_no_wli_phasea_gate_live_read_followon_1111_v1.py -q`
  - result:
    - `45 passed`

Next action:

- rerun the single `7004` live-read canary once with the patched snapshot
- only if that rerun writes a usable live gate metric should the prepared
  `7001/7003/7005/7002` family follow-on be treated as launch-ready

## 2026-04-24 - patched `7004` canary validated the live gate payload, then the bounded family follow-on completed with full verdict agreement

Question:

- after the snapshot backfill fix, does a patched `1111/search7004` live-read
  canary finally expose a usable live gate payload?
- if so, does the completed fixed `1111` family then reproduce the known
  keep/filter split cleanly enough to close the live-read validation branch?

Why this study existed:

- the first live-read canary had already found a real schema gap
- the persistence path itself was real
- the missing piece was whether the corrected payload would be:
  - usable on one patched canary
  - and family-correct on the bounded follow-on

Hypothesis block:

- Suspicion:
  - the patched `7004` canary would expose a usable gate payload
  - the completed fixed `1111` family would match the known split:
    - keep `7003,7004,7005`
    - filter `7001,7002`
- Main alternative:
  - one or more cells would still expose a missing or unusable snapshot
  - or the live verdict would disagree with the offline split
- Decision rule:
  - advance only if the patched predecessor canary completed with a usable
    live gate payload and the family follow-on reproduced the known split on
    every completed cell
  - refine for any usability failure or verdict mismatch

Runs:

- patched predecessor canary:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
  - bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061020Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- family follow-on:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1.py`
  - bundle:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1/`

Outcome:

- patched `7004` canary:
  - completed in:
    - `00:23:56`
  - replay result stayed the same local negative:
    - baseline `0.423`
    - retained Stage-3 reference `0.432`
    - replay `0.420`
    - delta vs baseline `-0.003`
  - snapshot payload became usable:
    - `phaseA_rank1_init_match = 0.415`
    - `phaseA_best_init_match = 0.415`
    - `phaseA_best_final_match = 0.415`
    - gate verdict:
      - `keep`
  - snapshot timing:
    - `1261.0s`
    - share `0.878`
- full family follow-on:
  - completed in:
    - `02:03:21`
  - completed coverage:
    - `5 / 5`
  - machine recommendation:
    - `advance`
  - snapshot present:
    - `5 / 5`
  - snapshot usable:
    - `5 / 5`
  - verdict agreement:
    - `5 / 5`
  - reproduced split:
    - keep:
      - `7003`
      - `7004`
      - `7005`
    - filter:
      - `7001`
      - `7002`
  - mean snapshot elapsed:
    - `1303.4s`
  - mean snapshot share:
    - `0.881`

Per-seed read:

- `7004`
  - `phasea_rank1_init_match = 0.415`
  - verdict:
    - `keep`
  - replay delta vs baseline:
    - `-0.003`
- `7001`
  - `phasea_rank1_init_match = 0.254`
  - verdict:
    - `filter`
  - replay delta vs baseline:
    - `-0.267`
- `7003`
  - `phasea_rank1_init_match = 0.490`
  - verdict:
    - `keep`
  - replay delta vs baseline:
    - `+0.068`
- `7005`
  - `phasea_rank1_init_match = 0.395`
  - verdict:
    - `keep`
  - replay delta vs baseline:
    - `+0.041`
- `7002`
  - `phasea_rank1_init_match = 0.289`
  - verdict:
    - `filter`
  - replay delta vs baseline:
    - `-0.444`

Timing interpretation:

- the live-read family now passes on semantic correctness
- but the emitted snapshot is still late relative to total replay elapsed:
  - patched `7004` share:
    - `0.878`
  - family mean share:
    - `0.881`
- so this branch now proves the live gate is:
  - real
  - usable
  - and family-correct
- it does not yet prove that the current emitted snapshot is early enough to
  recover the previously estimated filtered-lane wallclock savings in a real
  action wrapper

Conclusion:

- close the live-read validation branch as a semantic pass
- do not reopen the older question of whether the persisted gate exists or
  matches the family split
- carry forward the remaining open branch question instead:
  - should the first automated action be:
    - fallback
    - early stop
    - or both
- and carry forward the remaining timing question:
  - can the gate verdict be emitted at the real decision point rather than at
    about `0.88` of total replay elapsed

## 2026-04-24 - the first explicit both-action microprobe answered the action-choice question narrowly and showed that timing, not action choice, is the blocker

Question:

- if the validated gate is wired as both fallback and early stop, does one
  filtered `1111` lane save real wallclock while one kept `1111` lane preserves
  the prior exact replay read?

Why this study existed:

- the gate semantics were already validated on the fixed `1111` family
- the remaining branch question was whether the first real action should be:
  - fallback
  - early stop
  - or both
- the chosen first contract for this microprobe was:
  - both

Hypothesis block:

- Suspicion:
  - filtered `7002` would emit `filter`, apply the both-action contract, fall
    back to the retained baseline, and finish faster than the prior exact
    replay
  - kept `7003` would emit `keep`, continue cleanly, and preserve the prior
    exact positive
- Main alternative:
  - timing would still be too late to save useful wallclock
  - or the kept path would disturb the prior positive replay
- Decision rule:
  - advance only if the filtered canary applied the contract cleanly and the
    kept canary stayed no-harm relative to the prior exact replay
  - refine toward earlier emission if correctness passed but savings stayed
    small because the verdict arrived late
  - hold if either canary failed the first correctness contract

Runs:

- microbatch runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1.py`
- microbatch bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T161225Z__stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1/`
- filtered child canary:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T161225Z__stage2_topk_selected_family_low_edge_phasea_gate_both_action_exact_replay_1111_search7002_v1/`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_2026-04-24.log`

Budget proof before launch:

- retained exact replay anchor:
  - `7002`
    - `00:22:13`
  - `7003`
    - `00:21:54`
- anchored two-canary total:
  - `00:44:08`
- intended session budget:
  - `01:00:00`

Outcome:

- the filtered canary `7002` answered the branch before `7003` was worth
  launching
- semantic read on `7002`:
  - observed gate verdict:
    - `filter`
  - action contract:
    - `phasea_rank1_gate_both_v1`
  - action applied:
    - yes
  - fallback landed at retained baseline:
    - stage:
      - `stage35_substitution_only`
    - match:
      - `0.754`
  - delta vs baseline:
    - `0.000`
- timing read on `7002`:
  - current canary elapsed:
    - `01:09:52`
    - `4191.9s`
  - prior trusted exact replay elapsed:
    - `00:22:13`
    - `1333.3s`
  - actual saved attempt seconds versus the trusted prior replay:
    - `-2858.6`
  - snapshot elapsed:
    - `4190.0s`
  - snapshot share of total elapsed:
    - `0.9996`

Budget enforcement:

- after the first completed canary:
  - projected two-canary total:
    - `01:31:46`
- the stop rule fired correctly
- microbatch status:
  - `stopped_over_budget`
- kept canary:
  - not launched

Interpretation:

- the current both-action contract is semantically correct on the filtered lane
- the first action-choice question is therefore not the blocker
- the blocker is timing
- the current emitted gate fires essentially at the end of the replay, so it
  cannot recover real wallclock and should not be widened

Conclusion:

- close the first action-choice question narrowly:
  - `both` is not disproven on semantics
  - but it is unusable at the current emitted gate point
- do not spend another kept-lane no-harm canary on the current emitted gate
  surface
- move the next branch upstream to earlier emission or an earlier gate surface
  rather than another action-choice canary or a live runtime

## 2026-04-24 - raw provisional earlier-emission closed, checkpoint refinement advanced, and the second-pair confirmation microprobe was launched

Question:

- after the first both-action canary showed timing failure, can a materially
  earlier provisional Phase-A checkpoint recover the trusted keep/filter split
  before the late live-read surface?

Why this branch existed:

- the live-read family had already closed on semantic correctness
- the first explicit both-action canary had already closed the narrow action
  choice:
  - `both` was semantically fine
  - timing was the blocker
- so the next honest move was not another action contract
- it was to move the branch upstream to a materially earlier checkpoint

Hypothesis block for the raw provisional microprobe:

- Suspicion:
  - a raw provisional checkpoint on partial Phase-A would recover the trusted
    split early enough to justify a new action canary
- Main alternative:
  - the raw provisional surface would fail on at least one kept lane even if it
    looked promising on filtered lanes
- Decision rule:
  - advance only if the provisional surface matched both a filtered and a kept
    canary materially earlier than the late gate
  - otherwise hold and either refine the rule or persist richer provisional
    fields

Raw provisional microprobe:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1.py`
- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1/`
- filtered child:
  - `1111/search7002`
- kept child:
  - `1111/search7003`
- result:
  - `hold`

Raw provisional read:

- `7002`:
  - provisional verdict:
    - `filter`
  - first shared success:
    - restart `16`
- `7003`:
  - provisional verdict at restarts `16/32/48/64`:
    - `filter`
  - but the same provisional snapshots already carried:
    - `phaseA_best_init_match = 0.490`
    - `phaseA_best_final_match = 0.490`

Conclusion from the raw provisional branch:

- close checkpoint `rank1` alone
- do not widen that exact provisional rule to more runtime canaries
- the kept-lane failure is a ranking-surface problem, not just a timing problem
- the next honest move is checkpoint refinement rather than another generic
  earlier-emission run

Checkpoint-refinement audit:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1.py`
- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T192446Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1/`
- result:
  - `advance`
- selected refined rule:
  - `rank1_ge_0p30_or_best_ge_0p44`
- trusted fixed-family fit:
  - `5 / 5`
- earlier provisional pair fit:
  - `7002/7003`
- selected shared checkpoint:
  - restart `16`
- mean checkpoint elapsed share:
  - `0.212`
- mean share improvement versus the late live-read gate:
  - `0.674`

Why the audit matters:

- this branch is no longer vaguely "earlier emission"
- it now has one concrete refined rule tied to a concrete checkpoint
- the refined rule must still earn trust on a second filtered / kept pair
  before any new action canary

Refined confirmation microprobe launch:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1.py`
- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1/`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_2026-04-24.log`
- canaries:
  - filtered `7001`
  - kept `7005`
- budget proof before launch:
  - `7001` completed-family anchor:
    - `00:23:41`
  - `7005` completed-family anchor:
    - `00:24:23`
  - anchored total:
    - `00:48:04`
  - intended session budget:
    - `01:00:00`
- stop condition:
  - after the first completed canary, recompute the projected two-canary total
    from the observed row plus the remaining anchor
  - stop before the second canary if projection exceeds `01:00:00`

Refined confirmation microprobe result:

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1/`
- result:
  - `hold`
- elapsed:
  - `00:45:35`
- filtered `7001`:
  - provisional `best_init`:
    - `0.378`
  - observed verdict at checkpoints `16 / 32 / 48 / 64`:
    - `filter`
  - expected:
    - `filter`
- kept `7005`:
  - provisional `best_init`:
    - `0.395`
  - observed verdict at checkpoints `16 / 32 / 48 / 64`:
    - `filter`
  - expected:
    - `keep`
- machine next branch:
  - `stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_field_persistence`

Immediate branch state:

- raw provisional `rank1` is now closed
- composite refined checkpoint confirmation is now also closed
- no live runtime is justified yet
- the next honest move is a short checkpoint field-persistence audit on the
  full retained `1111` family, filling the missing provisional `7004` lane if
  required

## 2026-04-24 - strict field persistence held, restart32 stabilization advanced, and the first best-init action contract passed the hard pair

Question:

- once the composite refined checkpoint rule failed on kept `7005`, is the
  real early signal a simpler `phaseA_best_init_match` threshold, and if so
  can that simpler restart32 rule act as a real stop/fallback contract?

Why this branch existed:

- raw provisional `rank1` was already closed
- the composite refined rule `rank1>=0.30 or best>=0.44` fit the retained
  audit set but failed the second kept confirmation lane
- so the next honest move was not another action canary on the same rule
- it was to inspect whether a simpler best-init field stabilized later and was
  still early enough to matter

Missing-lane completion canary:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T203709Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- purpose:
  - fill the missing provisional checkpoint lane for `7004`

Completion-canary read:

- `7004`
  - `phaseA_best_init_match = 0.415`
  - stable at checkpoints:
    - `16 / 32 / 48 / 64`
  - exact replay completion:
    - `00:22:52`
  - final `resume_best_match_ratio`:
    - `0.420`

Strict field-persistence audit:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1.py`
- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210520Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1/`
- result:
  - `hold`

Strict-persistence read:

- apparent best-init gap on the retained family:
  - filtered max:
    - `0.378`
  - kept min:
    - `0.395`
- strict persistence failed at restart `16` because filtered `7002` still moved:
  - restart `16`:
    - `0.289`
  - restart `32`:
    - `0.329`

Interpretation:

- the retained family really did expose a best-init gap
- but restart `16` was too early to treat that gap as stable
- the next honest move was a stabilization-window audit, not another rule
  search by intuition

Stabilization-window audit:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1.py`
- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210839Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_stabilization_window_audit_v1/`
- result:
  - `advance`

Selected stabilized rule:

- field:
  - `phaseA_best_init_match`
- earliest stable separating window:
  - restart `32`
- filtered max:
  - `0.378`
- kept min:
  - `0.395`
- threshold midpoint:
  - `0.3865`
- mean elapsed share at restart `32`:
  - about `0.426`
- mean share improvement versus the late live-read gate:
  - about `0.455`

Interpretation:

- the branch no longer needed a composite checkpoint rule
- it now had one concrete stabilized provisional rule:
  - restart `32`
  - `phaseA_best_init_match >= 0.3865`
- that rule still needed one real action-contract proof before any wider
  family claim

Best-init action microprobe:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1.py`
- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T211444Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1/`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_2026-04-24.log`
- canaries:
  - filtered `7001`
  - kept `7005`
- budget proof before launch:
  - `7001` anchor:
    - `00:22:43`
  - `7005` anchor:
    - `00:22:37`
  - anchored total:
    - `00:45:20`
  - intended session budget:
    - `01:00:00`

Outcome:

- result:
  - `advance`
- total elapsed:
  - `00:32:09`

Per-canary read:

- filtered `7001`
  - observed gate verdict:
    - `filter`
  - action applied:
    - `1`
  - first checkpoint:
    - restart `32`
  - elapsed:
    - `00:09:33`
  - saved attempt seconds:
    - `736.0`
  - saved attempt share:
    - `0.562`
  - landed at retained baseline:
    - `0.428`
- kept `7005`
  - observed gate verdict:
    - `keep`
  - action applied:
    - `0`
  - first checkpoint:
    - restart `32`
  - elapsed:
    - `00:22:32`
  - delta vs prior exact replay:
    - `0.000`
  - final best match:
    - `0.413`

Interpretation:

- the restart32 best-init rule is a real action contract, not just an audit
  threshold
- it solved both halves of the hard pair:
  - filtered lane saved real wallclock
  - kept lane stayed no-harm
- that justified one wider remaining-family microbatch before any review or
  live-runtime discussion

Conclusion:

- strict restart16 persistence is closed
- restart32 best-init stabilization is the carried rule
- the hard-pair action contract is now passed
- the next honest move is the remaining-family microbatch on:
  - filtered `7002`
  - kept `7003`
  - kept `7004`

## 2026-04-24 - remaining-family restart32 best-init microbatch prepared and launched

Question:

- after the hard-pair action pass, does the same restart32 best-init contract
  generalize across the remaining fixed `1111` family lanes?

Prepared runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1.py`

Prepared plan note:

- `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_plan_2026-04-24.md`

Prepared focused proof:

- `tests/tools/test_no_wli_phasea_checkpoint_best_init_window_family_microbatch_v1.py`
- `tests/tools/test_no_wli_phasea_checkpoint_best_init_window_action_microprobe_v1.py`
- result:
  - `6 passed`

Prepared launchers:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_launch_2026-04-24.ps1`
- `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_open_terminal_2026-04-24.ps1`

Budget proof before launch:

- `7002`
  - `00:22:13`
- `7003`
  - `00:21:54`
- `7004`
  - `00:24:17`
- anchored total:
  - `01:08:25`
- intended session budget:
  - `01:30:00`
- stop condition:
  - after each completed lane, recompute the projected three-lane total from
    observed elapsed plus the remaining anchors
  - stop before launching the next lane if projection exceeds `01:30:00`

Launch:

- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_2026-04-24.log`
- launch timestamp:
  - `2026-04-24T22:21:09Z`
- first lane:
  - filtered `7002`
- initial state bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`

Immediate read:

- the batch started cleanly
- the runner emitted its own `run_started` and `job_started` lines
- the `7002` child replay emitted live Phase-A heartbeats immediately
- outcome still pending at this log point

## 2026-04-24 - remaining-family restart32 best-init microbatch completed, passed semantically, and exposed one kept-lane timing caveat

Question:

- after the hard-pair action pass, does the same restart32 best-init contract
  generalize across the remaining fixed `1111` family lanes?

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1.py`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_2026-04-24.log`

Outcome:

- result:
  - `advance`
- elapsed:
  - `01:09:23`

Per-lane read:

- filtered `7002`
  - observed gate verdict:
    - `filter`
  - action applied:
    - `1`
  - first checkpoint:
    - restart `32`
  - elapsed:
    - `00:09:34`
  - saved attempt seconds:
    - `759.7`
  - saved attempt share:
    - `0.570`
  - landed at retained baseline:
    - `0.754`
- kept `7003`
  - observed gate verdict:
    - `keep`
  - action applied:
    - `0`
  - first checkpoint:
    - restart `32`
  - elapsed:
    - `00:22:03`
  - delta vs reference exact replay:
    - `0.000`
  - final best match:
    - `0.476`
- kept `7004`
  - observed gate verdict:
    - `keep`
  - action applied:
    - `0`
  - first checkpoint:
    - restart `32`
  - elapsed:
    - `00:37:37`
  - delta vs reference exact replay:
    - `0.000`
  - final best match:
    - `0.420`

Summary:

- verdict match count:
  - `3 / 3`
- kept no-harm count:
  - `2 / 2`
- family mean delta vs baseline:
  - `+0.0217`
- mean checkpoint share of reference attempts:
  - `0.421`

Integrity correction:

- the first live summary helper marked the filtered lane as not behaving as
  expected because it only treated lane role `filtered_canary` as filtered
- the saved rows were correct
- the runner was patched to score `filtered_family` and `kept_family` locally
- focused proof reran and passed:
  - `6 passed`
- the bundle summary, recommendation, and readout were then rewritten from the
  saved rows

Interpretation:

- the restart32 best-init contract now passes semantically across the full
  fixed `1111` family
- the selector checkpoint subtopic is no longer blocked on family
  generalization
- the remaining caveat is operational:
  - kept `7004` preserved exact outcome but inflated wallclock materially

Conclusion:

- close the family-generalization question as passed
- keep external review and live-runtime reopening blocked until a short timing
  / postmortem audit explains the kept-`7004` runtime anomaly

## 2026-04-25 - kept-7004 timing postmortem advanced, but the first external-review pass later blocked the package on provenance

Question:

- after the restart32 best-init family microbatch passed semantically, what
  explains the kept `7004` wallclock inflation relative to its reference exact
  replays?

Plan note:

- `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_plan_2026-04-24.md`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1.py`

Focused proof:

- `tests/tools/test_no_wli_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1.py`
- result:
  - `2 passed`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T001151Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1/`

Outcome:

- result:
  - `advance`
- review ready:
  - `1`
- live runtime reopen recommended:
  - `0`

Key read:

- `7003` stayed timing-stable under the same action wiring:
  - family elapsed / reference:
    - `1.007`
  - family Phase-B step2112 elapsed / reference:
    - `0.997`
- `7004` first decided `keep` early:
  - restart:
    - `32`
  - first keep elapsed share:
    - `0.269`
- `7004` still slowed broadly relative to its latest reference:
  - total elapsed ratio:
    - `1.646`
  - restart64 elapsed ratio:
    - `1.518`
  - Phase-B step2112 elapsed ratio:
    - `2.474`
  - Phase-B step2112 eval-rate collapse:
    - from about `32803.2`
    - to about `13257.4`

Interpretation:

- the `7004` overrun does not read like a late keep decision
- it also does not read like generic gate-action overhead, because `7003`
  stays timing-stable under the same action wiring
- the anomaly reads as broad throughput loss across late Phase A and downstream
  search while preserving the same exact result

Conclusion:

- the selector checkpoint science still looked provisionally defensible
- live runtime still did not reopen from this note alone
- first external-review pass later found the current package was not
  review-ready as assembled because the decisive remaining-family bundle still
  had unreconciled provenance/reporting mismatches
- if work continues now, it should do so first as reconciliation and
  repackaging rather than more replay-family cleanup

## 2026-04-25 - selector checkpoint external-review first pass blocked the package on provenance, not science

Question:

- after the kept-`7004` timing postmortem and the first review-pack build, is
  the selector checkpoint subtopic now clean enough for external review?

Review verdict:

- `not review-ready as packaged`

Shared conclusion:

- the checkpoint science likely survived
- the external handoff did not
- the defect is a provenance / reporting contradiction rather than a new
  empirical contradiction

Main blocker:

- decisive remaining-family bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`
- raw rows / state / final event still contain the original `hold` path:
  - filtered `7002` row:
    - `action_behaved_as_expected = 0`
  - `matrix_run_state.json`:
    - `recommendation = hold`
  - final `matrix_run_events.jsonl` event:
    - `recommendation = hold`
- later regenerated summary / recommendation / readout interpret the same
  measurements as:
  - `advance`

Likely cause:

- shared row-builder only recognized lane role:
  - `filtered_canary`
- remaining-family microbatch introduced:
  - `filtered_family`
  - `kept_family`
- so the filtered family lane was originally scored with kept-style logic in
  the derived row/control layer

Current carried claim:

- on fixed `1111/search7001-7005`, the restart32
  `phaseA_best_init_match >= 0.3865` checkpoint still appears to reproduce the
  intended keep/filter split
- filtered lanes:
  - `7001`
  - `7002`
  - fall back to baseline with material wallclock saving
- kept lanes:
  - `7003`
  - `7004`
  - `7005`
  - preserve their prior exact replay outcomes

Decision:

- do not widen the science branch
- do not reopen live runtime
- fix the shared role-contract path
- add focused regression coverage
- reconcile or rerun the decisive family bundle
- rebuild the review pack only after the evidence layers agree

## 2026-04-25 - short provenance audit machine-confirmed the remaining-family bundle mismatch

Question:

- after the external-review first pass blocked the selector checkpoint package,
  can a short repo-native provenance audit confirm the mismatch directly from
  the decisive remaining-family bundle?

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1.py`

Focused proof:

- `tests/tools/test_no_wli_phasea_checkpoint_refined_both_action_microprobe_v1.py`
- `tests/tools/test_no_wli_phasea_checkpoint_best_init_window_family_microbatch_v1.py`
- `tests/tools/test_no_wli_phasea_checkpoint_best_init_window_family_provenance_audit_v1.py`
- result:
  - `13 passed`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T081847Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1/`

Outcome:

- result:
  - `hold`
- next branch:
  - `stage2_topk_selected_family_low_edge_phasea_checkpoint_family_reconciliation_rerun`

Key read:

- recommendation values match:
  - `0`
- row mismatch count:
  - `1`
- mismatched search seeds:
  - `7002`
- state recommendation:
  - `hold`
- final event recommendation:
  - `hold`
- recommendation json recommendation:
  - `advance`
- readout recommendation:
  - `advance`

Row-level mismatch:

- `7002`
  - lane role:
    - `filtered_family`
  - saved `action_behaved_as_expected`:
    - `0`
  - recomputed shared-role value:
    - `1`

Interpretation:

- the blocker is now machine-confirmed inside the repo rather than only argued
  in review discussion
- the decisive bundle remains provenance-unclean
- the next honest move is still reconciliation and rerun, not more science

Review handoff:

- lightweight review pack:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25/`
  - zip:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25.zip`
- compact last-five summary note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_last5_experiments_summary_2026-04-25.md`

Paired src bundle:

- `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260425T082116Z.zip`
- generated from:
  - `C:\Python\Python311\python.exe tools/get_src_extended_review_bundle.py`

Method note:

- `planning/projects/no_wli/20_active_plans/no_wli_review_pack_method_note_2026-04-25.md`

## 2026-04-27 - Phase-C multi-thread long harvest closed saved-surface reshuffling

Question:

- across all candidate3 saved-surface cases, do frontload-depth, quota, or
  replacement policies ever beat the existing reorder-only controls?
- are repeated exact saved-surface replay rows stable across repeated passes?

Plan note:

- `planning/projects/no_wli/20_active_plans/no_wli_phasec_multi_thread_long_harvest_plan_2026-04-27.md`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_phasec_multi_thread_long_harvest_v1.py`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260427T020956Z__phasec_multi_thread_long_harvest_v1/`

Shape:

- cases:
  - `19`
- policies:
  - `27`
- passes:
  - `3`
- completed policy units:
  - `1539 / 1539`
- elapsed:
  - `19:21:02`
- status:
  - `completed`

Key result:

- no frontload-depth, quota, or replacement family beat the existing
  reorder-only controls on usable decision gates
- the only useful positive movements came from:
  - `phaseb_topk_anchor_swap_v1`
  - `phaseb_topk_frontload_all_v1`
- all repeated exact-replay rows were stable:
  - score consistent:
    - `513 / 513`
  - delta consistent:
    - `513 / 513`
  - winner consistent:
    - `513 / 513`
  - surface-class consistent:
    - `513 / 513`

Interpretation:

- exact saved-surface replay is deterministic for score, winner, and surface
  class in this run family
- runtime varies materially, but scores and winners did not vary across repeat
  passes
- the current width/quota/replacement saved-surface reshuffling direction is
  closed in this exact form
- the remaining useful mechanism is downstream of route choice:
  - local search / rescue after the best reorder-control surface

Preserved readout files:

- `phasec_multi_thread_long_harvest_case_rows.csv`
- `phasec_multi_thread_long_harvest_family_summary_rows.csv`
- `phasec_multi_thread_long_harvest_pass_summary_rows.csv`
- `phasec_multi_thread_long_harvest_science_thread_summary_rows.csv`
- `phasec_multi_thread_long_harvest_repeat_consistency_rows.csv`
- `phasec_multi_thread_long_harvest_readout.md`
- `phasec_multi_thread_long_harvest_summary.json`
- `phasec_multi_thread_long_harvest_recommendation.json`

Decision:

- do not rerun this matrix
- do not widen the same depth/quota/replacement atlas
- carry forward the best-reorder-surface rescue question instead

## 2026-04-28 - Stage-3 entry constant-local-depth reorder-signal panel capped after one control job

Question:

- on `1111` reorder-signal lanes, can constant-local-depth Stage-3 entry
  allocation beat the bounded Stage 3.5 control inside one honest 10-hour
  panel run?

Plan note:

- `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_reorder_signal_panel_plan_2026-04-27.md`

Runner:

- intended runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_reorder_signal_panel_v1.py`
- the scratch path mentioned in console notes is not present as a file:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/fixed_instance_solver_development_v1.py`

Generated panel:

- `planning/projects/no_wli/30_analysis_specs/generated_panels/p9_c3_solver_panel_1111_reorder_signal_stage3_entry_const_local_depth_v1.json`

Matrix control files:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v79_fixed_p9c3_1111_reorder_signal_stage35_entry_const_local_depth_panel_6job.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v79_fixed_p9c3_1111_reorder_signal_stage35_entry_const_local_depth_panel_6job.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v79_fixed_p9c3_1111_reorder_signal_stage35_entry_const_local_depth_panel_6job.jsonl`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260428T035424021944Z__bench_solve_pipeline_no_wli__ee62083/`

Outcome:

- planned jobs:
  - `6`
- completed jobs:
  - `1`
- completed lane:
  - `1111/search7002`
- matrix status:
  - capped after the first completed job
- completed job elapsed:
  - `13:32:47`
- completed job status:
  - `unsolved`
- best match:
  - `0.754`
- best stage:
  - `stage35_substitution_only`

Stage progression:

- Stage 2 exact:
  - `0.091`
- Stage 3 Phase B:
  - `0.734`
- Stage 3 Phase C:
  - `0.750`
- Stage 3.5:
  - `0.754`

Preset verification:

- the completed job key and event log used:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- the completed `run_config.json` has:
  - `stage3.entry.allocation_policy = legacy_fixed_budget`
  - `stage3.entry.mutations_per_promoted = 1`
  - `stage3.period_scaling.init_keys_cap = 192`
- the intended candidate preset in the runner has:
  - `force_stage3_init_keys_cap = 288`
  - `force_stage3_entry_allocation_policy = constant_local_depth`
  - `force_stage3_entry_mutations_per_promoted = 1`

Interpretation:

- useful single-job data:
  - yes
- answered the intended paired comparison:
  - no
- the completed job was the control / legacy-entry preset
- no constant-local-depth candidate job completed
- the full-pipeline panel is too expensive as configured

Saved handoff artefacts:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260428T035424021944Z__bench_solve_pipeline_no_wli__ee62083/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7002/manifest.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260428T035424021944Z__bench_solve_pipeline_no_wli__ee62083/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7002/stage2_resume.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260428T035424021944Z__bench_solve_pipeline_no_wli__ee62083/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7002/stage3_prep.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260428T035424021944Z__bench_solve_pipeline_no_wli__ee62083/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7002/stage35_seed_archive.json`

Decision:

- do not rerun the same six-job full-pipeline panel as-is
- use the saved handoff/archive artefacts for a late-stage-only comparison
- likely next branch:
  - `stage35_resume_from_handoff_focus_family_rescue_v1`

## 2026-04-29 - Stage35 handoff/archive focus-family rescue inventory passed

Question:

- before designing a late-stage-only rescue runner, do the priority retained
  `1111` handoff/archive roots contain the required input files?

Plan note:

- `planning/projects/no_wli/20_active_plans/no_wli_stage35_resume_from_handoff_focus_family_rescue_plan_2026-04-29.md`

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_resume_from_handoff_focus_family_rescue_v1.py`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T042821Z__stage35_resume_from_handoff_focus_family_rescue_v1/`

Target order:

- `1111/search7005`
  - primary selector/rescue headroom target
- `1111/search7004`
  - secondary fragmentation target
- `1111/search7002`
  - control / proof-of-runner target

Result:

- target rows:
  - `3`
- late-stage feasible rows:
  - `3`
- all required files present:
  - `1`
- runtime launched:
  - `0`
- recommendation:
  - `advance_to_static_archive_design`

Per-target read:

- `1111/search7005`
  - archive rows:
    - `6`
  - unique candidate hashes:
    - `6`
  - retained match:
    - `0.372`
  - best checkpoint seed match:
    - `0.398`
  - checkpoint headroom vs retained:
    - `+0.026`
- `1111/search7004`
  - archive rows:
    - `5`
  - unique candidate hashes:
    - `5`
  - retained match:
    - `0.423`
  - best checkpoint seed match:
    - `0.413`
  - checkpoint headroom vs retained:
    - `-0.010`
- `1111/search7002`
  - archive rows:
    - `6`
  - unique candidate hashes:
    - `6`
  - retained match:
    - `0.754`
  - best checkpoint seed match:
    - `0.752`
  - checkpoint headroom vs retained:
    - `-0.002`

Interpretation:

- the handoff/archive inputs are complete enough for static archive design work
- `1111/search7005` is the only target in this inventory with checkpoint seed
  headroom above retained best
- `1111/search7004` remains a fragmentation target, but this archive inventory
  does not show simple checkpoint headroom
- `1111/search7002` remains the control / proof-of-runner target
- this does not approve or launch runtime
- the next work unit should inspect the archive rows and define one narrow
  late-stage-only control/selector comparison
- if the next proposed run is expected to take about an hour or more, ask
  before launching

## 2026-04-29 - Stage35 handoff selected-row runner design refined

Question:

- after the first handoff/archive inventory, do the retained archive rows have
  enough selected-row key/plaintext material to call the existing late-stage
  Stage 3.5 resume API without recomputing upstream stages?

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_resume_from_handoff_focus_family_rescue_v1.py`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T043455Z__stage35_resume_from_handoff_focus_family_rescue_v1/`

New output tables:

- `stage35_resume_selected_candidate_material_rows.csv`
- `stage35_resume_runner_design_rows.csv`

Static result:

- target rows:
  - `3`
- selected candidate material rows:
  - `17`
- rows with runnable key/plaintext material:
  - `17`
- upstream recompute required by selected-row entry:
  - `0`
- partial outputs supported by selected-row entry:
  - `1`
- runtime launched:
  - `0`

Per-target selected-row design read:

- `1111/search7005`
  - retained:
    - `0.372`
  - best selected row:
    - `c9e69b90b779e318`
  - selected source:
    - `stage3_best_phaseB`
  - selected lane:
    - `anchor`
  - selected final match:
    - `0.416`
  - selected-row headroom:
    - `+0.044`
  - recommended next unit:
    - `selected_best_frontier_micro_canary`
- `1111/search7004`
  - retained:
    - `0.423`
  - best selected row:
    - `6858f26bdc4c4d1f`
  - selected source:
    - `stage3_best_phaseA`
  - selected lane:
    - `anchor`
  - selected final match:
    - `0.432`
  - selected-row headroom:
    - `+0.009`
  - recommended next unit:
    - `selected_best_frontier_micro_canary`
- `1111/search7002`
  - retained:
    - `0.754`
  - best selected row:
    - `36e2e7cb81dbf1bd`
  - selected source:
    - `phaseB_topk`
  - selected lane:
    - `challenger`
  - selected final match:
    - `0.752`
  - selected-row headroom:
    - `-0.002`
  - recommended next unit:
    - `control_replay_or_hold`

Interpretation:

- the first checkpoint-only archive read understated the runnable frontier
  material on `1111/search7005` and `1111/search7004`
- `1111/search7005` remains the first target because it has the larger
  selected-row headroom
- `1111/search7004` also has a small selected-row headroom row and can serve as
  a secondary confirmation target if the first micro-canary is promising
- `1111/search7002` is useful as a proof-of-runner/control case, not as the
  first expected-improvement target
- no late-stage runtime was launched by this step
- if the next proposed run is expected to take about an hour or more, ask
  before launching

Recommended Next:

- build a smoke-only selected-row runner for `1111/search7005`
- verify partial/progress writeback before any real local-rescue runtime
- then make an explicit launch decision for the real `7005` micro-canary

## 2026-04-29 - Stage35 handoff selected-row smoke preflight passed

Question:

- can the selected-row Stage 3.5 runner load the priority `1111/search7005`
  row and write progress/partial artifacts before launching a real rescue run?

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_v1.py`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T044610Z__stage35_resume_from_handoff_focus_family_rescue_v1__smoke_preflight/`

Smoke target:

- case:
  - `1111/search7005`
- selected row:
  - `c9e69b90b779e318`
- selected source:
  - `stage3_best_phaseB`
- selected lane:
  - `anchor`

Smoke config:

- `rounds = 0`
- `seed_keep = 2`
- `beam_width = 2`
- `archive_keep = 4`
- `max_runtime_seconds = 30`

Result:

- retained best:
  - `0.372`
- selected row start:
  - `0.416`
- smoke resume best:
  - `0.416`
- elapsed:
  - `1.485s`
- progress events written:
  - `3`
- partial dumps written:
  - `3`
- real science runtime launched:
  - `0`

Timing anchor for the real micro-canary:

- retained same-lane `1111/search7005` Stage 3.5 follow-up:
  - `1996.242s`
  - about `33m16s`
  - `1` completed round
  - `9` mini-searches
  - `3740` evals

Interpretation:

- selected-row loading works
- scorer construction works
- Stage 3.5 progress and partial-state writeback work
- this is not a science result because local-rescue rounds were disabled
- the real micro-canary remains unlaunched

Recommended Next:

- make an explicit launch decision for the real `1111/search7005`
  selected-best-frontier micro-canary
- proposed cap:
  - `3600s`
- proposed stop condition:
  - stop after one bounded Stage 3.5 round or `3600s`, whichever comes first
- because the projected runtime with margin is close to the one-hour guard,
  do not auto-launch without confirmation

## 2026-04-29 - Stage35 handoff real 7005 selected-row run completed

Question:

- starting from the best selected retained frontier row on `1111/search7005`,
  does one bounded Stage 3.5 rescue round improve beyond the selected row?

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_real_7005_v1.py`

Launch wrapper:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_resume_from_handoff_focus_family_rescue_real_7005_launch_2026-04-29.ps1`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_resume_from_handoff_focus_family_rescue_real_7005_2026-04-29.log`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T060445Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_v1__real_selected_best_frontier_one_round/`

Configuration:

- target:
  - `1111/search7005`
- selected row:
  - `c9e69b90b779e318`
- selected source:
  - `stage3_best_phaseB`
- selected lane:
  - `anchor`
- Stage 3.5 override:
  - `rounds = 1`
  - `seed_keep = 2`
  - `beam_width = 1`
  - `archive_keep = 12`
  - `max_runtime_seconds = 0`
  - `max_evals = 0`
- natural stop:
  - one bounded Stage 3.5 round completed

Result:

- status:
  - `completed`
- retained best:
  - `0.372`
- selected row start:
  - `0.416`
- resume best:
  - `0.416`
- delta versus retained:
  - `+0.044`
- delta versus selected start:
  - `+0.000`
- accept result:
  - `stage35_selected = 0`
  - `accept_reason = search_score_drop_guard_failed`
- rounds completed:
  - `1`
- evals:
  - `1470`
- archive rows:
  - `12`
- progress events written:
  - `16`
- partial dumps written:
  - `4`
- elapsed:
  - `2.991s`

Interpretation:

- the selected-row late-stage path completed cleanly and extractably
- the run preserved the selected-row improvement over retained best
- the accepted Stage 3.5 result did not add lift beyond the selected row
- posthoc archive analysis shows this is not a clean local-rescue-flat result:
  - rank 1 `f095bf4c31b02daf`:
    - truth match `0.416`
    - score delta versus baseline `+0.003019`
    - search-score delta versus baseline `-0.093198`
    - rejected by the search-score-drop guard
  - rank 2 `7068135ec036da03`:
    - truth match `0.422`
    - truth delta versus selected start `+0.006`
    - score delta versus baseline `+0.002984`
    - search-score delta versus baseline `+0.016851`
    - would satisfy the current nonnegative score and search-score guards
- the completed run had `accept_guard_passing_selector_mode = off`, so it did
  not fall through to the guard-passing rank-2 proposal
- the unexpectedly short elapsed time now becomes the timing anchor for this
  exact selected-row runner shape

Recommended Next:

- do not deepen the same broad `7005` selected-row rescue shape immediately
- before moving to `7004`, run a small same-target selector follow-up with:
  - `accept_guard_passing_selector_mode = top_score_then_search`
  - same selected row `c9e69b90b779e318`
  - same one-round bounded Stage 3.5 shape
- success condition:
  - accepted resume exposes the posthoc guard-passing `0.422` row, or explains
    why live selector behavior differs from the archive read

## 2026-04-29 - Stage35 handoff real 7005 guard-selector follow-up completed

Question:

- does enabling guard-passing selector fallback accept the posthoc
  guard-passing rank-2 archive row on the same `1111/search7005`
  selected-row one-round rescue?

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1.py`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T145906Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/`

Configuration:

- target:
  - `1111/search7005`
- selected row:
  - `c9e69b90b779e318`
- Stage 3.5 shape:
  - `rounds = 1`
  - `seed_keep = 2`
  - `beam_width = 1`
  - `archive_keep = 12`
  - `mini_search_steps = 1`
  - `max_runtime_seconds = 0`
- selector delta:
  - `accept_guard_passing_selector_mode = top_score_then_search`

Result:

- status:
  - `completed`
- retained best:
  - `0.372`
- selected-row start:
  - `0.416`
- accepted resume best:
  - `0.422`
- delta versus retained:
  - `+0.050`
- delta versus selected-row start:
  - `+0.006`
- accept result:
  - `stage35_selected = 1`
  - `accept_reason = accepted_via_guard_passing_selector`
  - `selected_via_guard_passing_selector = 1`
  - `selected_archive_rank = 2`
- selected candidate:
  - `7068135ec036da03`
- rounds completed:
  - `1`
- evals:
  - `1470`
- archive rows:
  - `12`
- progress events written:
  - `16`
- partial dumps written:
  - `4`
- elapsed:
  - `6.361s`

Interpretation:

- the posthoc archive read was actionable
- the same local archive becomes a real accepted improvement once
  guard-passing selector fallback is enabled
- `7005` now has two separate positive pieces:
  - selected-row route choice improved retained `0.372` to `0.416`
  - guard-selector local rescue improved `0.416` to `0.422`
- this validates the guard-selector mechanism on the strongest retained
  selected-row headroom case
- the run is short enough to keep this exact selected-row guard-selector shape
  in the sub-hour timing class for `7005`

Recommended Next:

- do not deepen `7005` immediately
- decide whether to run the same guard-selector shape on `1111/search7004`
  before closing or widening the branch
- reason to run `7004`:
  - it is the next static-positive lane, but with smaller selected-row headroom
    (`0.432` versus retained `0.423`, `+0.009`)
- reason not to run `7004`:
  - one-lane mechanism success may already be enough to move to a cleaner
    selector-policy design rather than another lane check

## 2026-04-29 - Stage35 handoff real 7004 guard-selector confirmation completed

Question:

- does the same strict guard-selector shape repeat on the smaller-headroom
  `1111/search7004` lane?

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1.py`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T150415Z__stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/`

Configuration:

- target:
  - `1111/search7004`
- selected row:
  - `6858f26bdc4c4d1f`
- selected source:
  - `stage3_best_phaseA`
- Stage 3.5 shape:
  - `rounds = 1`
  - `seed_keep = 2`
  - `beam_width = 1`
  - `archive_keep = 12`
  - `mini_search_steps = 1`
  - `max_runtime_seconds = 0`
- selector:
  - `accept_guard_passing_selector_mode = top_score_then_search`

Result:

- status:
  - `completed`
- retained best:
  - `0.423`
- selected-row start:
  - `0.432`
- reported local top resume:
  - `0.425`
- delta versus retained:
  - `+0.002`
- delta versus selected-row start:
  - `-0.007`
- accept result:
  - `stage35_selected = 0`
  - `accept_reason = search_score_drop_guard_failed`
  - `selected_via_guard_passing_selector = 0`
  - `selected_archive_rank = 1`
- rounds completed:
  - `1`
- evals:
  - `2643`
- archive rows:
  - `12`
- progress events written:
  - `16`
- partial dumps written:
  - `4`
- elapsed:
  - `10.620s`

Posthoc archive read:

- rank 1 `fc5cd98aefea1270`:
  - truth match `0.425`
  - truth delta versus selected start `-0.007`
  - score delta `+0.002976`
  - search-score delta `-0.023589`
  - rejected by search-score guard
- rank 6 `3b5b0ca607c51fbe`:
  - truth match `0.438`
  - truth delta versus selected start `+0.006`
  - score delta `+0.000731`
  - search-score delta `-0.021339`
  - truth-positive but rejected by search-score guard
- rank 12 `0e53773898ecab02`:
  - truth match `0.432`
  - score and search-score deltas `0`
  - no-op/baseline guard pass

Interpretation:

- strict guard-selector fallback does not repeat as an accepted improvement on
  `7004`
- the accepted route should be interpreted as staying at the selected-row start
  `0.432`; the `0.425` row is a rejected local top, not a better accepted
  endpoint
- the branch is now mixed:
  - `7005` accepted a strict guard-selector improvement to `0.422`
  - `7004` exposed a truth-positive local row at `0.438`, but the search-score
    guard rejected it
- the current guard protects against the rank-1 truth regression on `7004`, but
  it also blocks at least one truth-positive local row

Recommended Next:

- stop this exact strict guard-selector runtime shape
- do not launch more late-stage runtime until an offline policy audit decides
  whether search-score guard relaxation is justified
- likely next offline question:
  - across saved Stage 3.5 archives, how often do search-score-failing rows
    have positive truth movement, and is there an observable non-truth feature
    that separates rank-6-like gains from rank-1-like regressions?

## 2026-04-29 - Stage35 guard-selector archive policy audit completed

Question:

- across the completed `7005` and `7004` selected-row guard-selector archives,
  is the strict nonnegative search-score guard selecting useful rows or
  blocking truth-positive local proposals?

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_guard_selector_archive_policy_audit_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T151026Z__stage35_guard_selector_archive_policy_audit_v1/`

Scope:

- cases:
  - `2`
- archive rows:
  - `24`
- inputs:
  - `7005` guard-selector Stage 3.5 archive
  - `7004` guard-selector Stage 3.5 archive

Result:

- accepted-positive cases:
  - `1 / 2`
- cases with blocked truth-positive rows:
  - `1 / 2`
- `7005`:
  - accepted:
    - `1`
  - accepted delta versus selected:
    - `+0.006`
  - guard-passing non-noop rows:
    - `2`
  - truth-positive rows:
    - `3`
  - blocked truth-positive rows:
    - `0`
  - best truth row:
    - rank `2`
    - `7068135ec036da03`
    - truth match `0.422`
    - search-score delta `+0.016851`
- `7004`:
  - accepted:
    - `0`
  - guard-passing non-noop rows:
    - `0`
  - truth-positive rows:
    - `1`
  - blocked truth-positive rows:
    - `1`
  - best truth row:
    - rank `6`
    - `3b5b0ca607c51fbe`
    - truth match `0.438`
    - search-score delta `-0.021339`

Interpretation:

- strict guard-selector fallback works on `7005`
- strict guard-selector fallback does not repeat on `7004`
- the search-score guard blocks the `7004` truth-positive rank-6 row
- this is a policy boundary, not a runtime or plumbing issue

Recommended Next:

- stop strict guard-selector runtime for now
- if continuing this branch, run a broader offline guard-relaxation audit over
  retained Stage 3.5 archives before any more runtime
- that broader audit should look for non-truth features that separate the
  `7004` rank-6 truth-positive row from rank-1 truth regressions

## 2026-04-29 - launching broader Stage35 guard-relaxation archive policy data-taking run

Question:

- across retained Stage 3.5 archive surfaces, does relaxing the search-score
  guard recover truth-positive rows, and how often does it admit truth-negative
  rows?

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_relaxation_archive_policy_long_audit_v1.py`

Launch wrapper:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_relaxation_archive_policy_long_audit_launch_2026-04-29.ps1`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_relaxation_archive_policy_long_audit_2026-04-29.log`

Runtime budget:

- intended wallclock:
  - `8h`
- hardcoded cap:
  - `28800s`
- stop condition:
  - all discovered `stage35_summary.json` / `best_instance.json` Stage 3.5
    archive sources processed, or wallclock cap reached
- partial writeback:
  - every `5` sources
- progress:
  - completed-versus-total, elapsed, and ETA every `5` sources

Timing basis:

- retained full fixed cells remain multi-hour and are not being rerun here
- this is archive data-taking over saved Stage 3.5 surfaces, with no full
  upstream recomputation
- if the audit finishes early, treat that as complete data collection rather
  than padding runtime

Outcome:

- completed sources:
  - `264 / 264`
- usable case summaries:
  - `80`
- archive rows:
  - `931`
- skipped sources:
  - `184`
- elapsed:
  - `8.084s`
- key conclusion:
  - strict search-score guard remains the best default in this audit
  - relaxed search-score floors did not increase truth-positive selections and
    increased truth-negative selections

## 2026-04-29 - launching selected-frontier Stage35 guard-selector runtime harvest

Question:

- across retained fixed-panel artefacts and multiple saved frontier rows per
  artefact, where does one bounded strict guard-selector Stage 3.5 rescue
  actually accept useful local improvements?

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_selector_frontier_runtime_harvest_v1.py`

Launch wrapper:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_selector_frontier_runtime_harvest_launch_2026-04-29.ps1`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_selector_frontier_runtime_harvest_2026-04-29.log`

Runtime budget:

- intended wallclock:
  - `8h`
- hardcoded cap:
  - `28800s`
- per-cell cap:
  - `900s`
- selected frontier rows:
  - up to `12` per retained fixed-panel artefact
- stop condition:
  - queue exhausted, wallclock cap reached, or first-cell serial projection
    exceeds the `28800s` budget
- partial writeback:
  - after every cell
- progress:
  - completed-versus-total, elapsed, per-cell elapsed, and ETA after every cell

## 2026-05-01 - launching Stage35 frontier-space robustness harvest

Question:

- across held-out Stage 3.5 frontier strata, does deeper bounded local rescue
  stabilize useful gains or mostly amplify the shallow mixed signal?

Mechanism layer:

- local search / rescue

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_frontier_space_robustness_harvest_v1.py`

Plan:

- `planning/projects/no_wli/20_active_plans/no_wli_stage35_frontier_space_robustness_harvest_plan_2026-05-01.md`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_frontier_space_robustness_harvest_2026-05-01.log`

Runtime budget:

- intended wallclock:
  - `8h`
- hardcoded wallclock cap:
  - `28800s`
- per-cell cap:
  - `1800s`
- max cells:
  - `48`
- first-cell rule:
  - stop if the first-cell serial projection exceeds `28800s`

Prediction recorded before launch:

- suspicion:
  - rank-6 held-out positives will mostly remain useful, but shallow negatives
    and rank `1-5` neutral/positive rows will stay mixed enough to block a
    simple policy
- main alternative:
  - a deeper rescue budget may reveal a broader stable stratum outside rank 6,
    or may recover shallow regressions often enough to justify a new feature
    design branch

Decision rule:

- promote no policy directly from this harvest
- continue only if a predeclared stratum is strongly nonnegative and materially
  useful
- otherwise close local-rescue policy widening and preserve the output as
  mechanism evidence

Completed result:

- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T161846Z__stage35_frontier_space_robustness_harvest_v1/`
- closeout:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_frontier_space_robustness_harvest_closeout_2026-05-01.md`
- status:
  - `completed`
- completed cells:
  - `48 / 48`
- errors:
  - `0`
- elapsed:
  - `12602.918s`
  - `3.501h`
- first cell:
  - `443.854s`
- first-cell projection:
  - `21305.002s` versus `28800s`
- Stage 3.5 selected cells:
  - `32 / 48`
- accepted rows better/worse than shallow:
  - `27 / 3`
- accepted rows nonnegative/negative versus selected start:
  - `28 / 4`

Stratum result:

- `calibration_repeat`:
  - selected `6 / 6`
  - better/worse versus shallow `6 / 0`
  - nonnegative/negative versus start `6 / 0`
- `rank1_5_moderate_positive`:
  - selected `7 / 13`
  - better/worse versus shallow `6 / 0`
  - nonnegative/negative versus start `7 / 0`
- `rank6_heldout_positive`:
  - selected `3 / 5`
  - better/worse versus shallow `2 / 0`
  - nonnegative/negative versus start `3 / 0`
- `shallow_negative`:
  - selected `10 / 14`
  - better/worse versus shallow `8 / 2`
  - nonnegative/negative versus start `7 / 3`
- `shallow_neutral`:
  - selected `6 / 10`
  - better/worse versus shallow `5 / 1`
  - nonnegative/negative versus start `5 / 1`

Prediction comparison:

- rank-6 held-out positives mostly remained useful among accepted rows
- shallow-negative and shallow-neutral strata stayed mixed
- rank `1-5` moderate positives were cleaner than expected among accepted
  rows, but `6 / 13` in that stratum still failed the search-score guard

Decision:

- do not promote a policy directly from this harvest
- do not launch another broad local-rescue runtime batch immediately

Recommended next:

- run an offline acceptance-boundary extractor over accepted positives,
  accepted regressions, and high-local-best guard failures before any further
  runtime

Offline acceptance-boundary audit completed:

- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_frontier_space_acceptance_boundary_audit_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T235632Z__stage35_frontier_space_acceptance_boundary_audit_v1/`
- accepted positives:
  - `28`
- accepted regressions:
  - `4`
- guard failures:
  - `16`
- scanned rules:
  - single-rule sketches:
    - `1087`
  - two-feature sketches:
    - `20292`
- perfect separators:
  - single-rule:
    - `0`
  - two-feature:
    - `0`
- best no-regression single rule:
  - `shallow_resume_minus_selected >= 0.0005`
  - true positives:
    - `16 / 28`
  - false positives:
    - `0 / 4`
- best no-regression two-feature sketch:
  - `stage35_baseline_score >= 0.132556 AND stage35_accept_reason == accepted`
  - true positives:
    - `23 / 28`
  - false positives:
    - `0 / 4`

Decision:

- close broad local-rescue policy widening for now
- keep the robustness harvest as mechanism evidence
- move next work up a level unless a genuinely held-out validation design is
  written before any further local-rescue runtime

## 2026-05-01 - Stage3 entry constant-local-depth handoff 7005 live status

Active run:

- `stage3_entry_const_local_depth_handoff_7005_v1`

Active output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/`

Status file:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/cell_0001_1111_search7005_const_local_depth/stage3_resume_status.json`

Latest early heartbeat:

- checked at:
  - `2026-05-01T02:34:30Z`
- status:
  - `running`
- phase:
  - `phaseA`
- Phase-A progress:
  - `6 / 144`
- latest step:
  - `408 / 800`
- evals:
  - `444685`
- latest status update:
  - `2026-05-01T02:34:30Z`

Instruction carried forward:

- do not start a second handoff runtime while this cell is active
- after completion, analyze this one cell and refresh output/runtime logs before
  deciding whether `1111/search7004` or a control replay is justified

## 2026-05-01 - Stage3 entry constant-local-depth handoff 7005 result and 7004 follow-up

First cell:

- `1111/search7005`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/`

Result:

- status:
  - `completed`
- elapsed:
  - `7139.745s`
- retained best:
  - `0.372`
- candidate best:
  - `0.374`
- delta versus retained:
  - `+0.002`
- best stage:
  - `stage35_substitution_only`
- stop reason:
  - `unsolved`

Interpretation:

- constant-local-depth produced a real but small positive on `7005`
- this does not justify the known-heavy `7002` lane yet
- it does justify the second non-heavy activated target, `7004`, while the
  chat-approved data-taking window is still open

Second-cell setup:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_handoff_7004_v1.py`
- launch script:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_handoff_7004_launch_2026-05-01.ps1`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_handoff_7004_2026-05-01.log`
- intended cap:
  - `6h`
- watchdog:
  - `21600s`

Recommended next:

- launch `7004` now
- after `7004`, analyze both handoff cells together before deciding whether any
  heavier `7002` probe is warranted

Launch check:

- process launched:
  - yes
- visible PowerShell window:
  - yes
- active output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/`
- status file:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/cell_0001_1111_search7004_const_local_depth/stage3_resume_status.json`
- first observed status:
  - `running`
- first observed phase:
  - `phaseA`
- first observed Phase-A progress:
  - `0 / 144`
- latest status update:
  - `2026-05-01T06:47:56Z`

Runtime/catalog refresh:

- output catalog refreshed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog`
- runtime history reference refreshed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064848Z__no_wli_runtime_history_reference_v1/`
- fixed wallclock reference refreshed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064848Z__fixed_runtime_wallclock_reference_v1/`

## 2026-05-01 - Stage3 entry constant-local-depth handoff closeout

Second cell:

- `1111/search7004`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/`

Result:

- status:
  - `completed`
- elapsed:
  - `7755.439s`
- retained best:
  - `0.423`
- candidate best:
  - `0.406`
- delta versus retained:
  - `-0.017`
- candidate best stage:
  - `stage3_full_refine`
- runner errors:
  - `0`

Combined result:

- `7005`:
  - retained `0.372`
  - candidate `0.374`
  - delta `+0.002`
  - elapsed `7139.745s`
- `7004`:
  - retained `0.423`
  - candidate `0.406`
  - delta `-0.017`
  - elapsed `7755.439s`

Mechanism read:

- `7004` Phase-A best was `0.422` on candidate `6858f26bdc4c4d1f`
- Phase C moved that same candidate to `0.406`
- Stage 3.5 found an archive rank-1 row but did not accept it:
  - `search_score_drop_guard_failed`

Closeout:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_handoff_closeout_2026-05-01.md`

Decision:

- close this exact constant-local-depth handoff-resume shape as a policy
  candidate
- do not launch `1111/search7002` for this branch

Recommended next:

- offline downstream-selection audit on `7004`: compare Phase-A best, Phase-C
  winner, and Stage 3.5 baseline/guard rows, looking for a predeclared safety
  rule that would keep the `7005` small positive and reject the `7004`
  regression

## 2026-05-01 - Stage3 entry constant-local-depth downstream-selection audit

Question:

- why did constant-local-depth keep a small `7005` gain but regress on `7004`,
  and is there an offline safety gate worth carrying forward?

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage3_entry_const_local_depth_downstream_selection_audit_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T155731Z__stage3_entry_const_local_depth_downstream_selection_audit_v1/`

Result:

- cells:
  - `2`
- candidate positives:
  - `1`
- candidate negatives:
  - `1`
- `7005`:
  - Stage 3.5 accept passed
  - widened-entry result kept `+0.002`
- `7004`:
  - Stage 3.5 accept failed
  - reason `search_score_drop_guard_failed`
  - widened-entry result was `-0.017`

Posthoc gate:

- rule:
  - use widened-entry result only when Stage 3.5 accept passes; otherwise fall
    back to retained
- kept candidates:
  - `1`
- fallback cells:
  - `1`
- gated negative cells:
  - `0`

Interpretation:

- the gate is a plausible offline safety lead
- it is not enough evidence for runtime because it was derived from only the two
  completed constant-local-depth handoff cells

Recommended next:

- run a broader offline gate audit over retained handoff/frontier outputs before
  any more runtime

## 2026-05-01 - Stage35 accept-gate broader offline audit

Question:

- does the two-cell Stage 3.5 accept-pass fallback lead survive a broader
  retained Stage 3.5 frontier stress test?

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_accept_gate_broader_offline_audit_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T160206Z__stage35_accept_gate_broader_offline_audit_v1/`

Coverage:

- shallow frontier harvest:
  - `136` rows
- deepening harvest:
  - `15` rows
- total:
  - `151` rows

Result:

- Stage 3.5 accepted rows:
  - `147`
- accept-gate negatives versus retained:
  - `75`
- accept-gate negatives versus selected start:
  - `18`
- combined mean accept-gate delta versus retained:
  - `-0.018556`
- combined mean accept-gate delta versus selected:
  - `+0.050563`

Interpretation:

- the simple accept-pass fallback rule is not a general safety gate
- the earlier `7005/7004` result remains useful diagnostic evidence only
- no runtime should be launched from this gate

Recommended next:

- return to offline feature design or a different mechanism branch; avoid
  entry-allocation and simple Stage 3.5 acceptance as policy levers

Runtime/catalog refresh:

- output catalog refreshed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog`
- runtime history reference refreshed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T154027Z__no_wli_runtime_history_reference_v1/`
- fixed wallclock reference refreshed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T154027Z__fixed_runtime_wallclock_reference_v1/`

## 2026-04-30 - launching Stage35 rank-6 route-lineage additive confirmation

Question:

- can the strict route-lineage signal be used as an additive rescue rule for
  old-rejected rank-6 rows without adding a confirmed regression?

Pre-launch read:

- strict route-lineage is too lossy as a replacement because group B contains
  old-keep / route-reject rows with existing positive evidence
- the honest next test is additive:
  - retain the old softened rule
  - add route-lineage rescue for group-A rows

Design note:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_additive_confirmation_design_2026-04-30.md`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_route_lineage_additive_confirmation_v1.py`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_route_lineage_additive_confirmation_2026-04-30.log`

Cells:

- `611/search7003 rank 6 826e5c871f444486`
- `1111/search7001 rank 6 d94845511e181f7c`
- `1411/search7004 rank 6 2632e79517bf1c7c`
- `1411/search7005 rank 6 b47e22bc63e7c189`

Runtime budget:

- intended wallclock:
  - `45m`
- hard cap:
  - `2700s`
- per-cell rescue cap:
  - `600s`
- stop condition:
  - all four cells processed, wallclock cap reached, or first-cell projection
    exceeds `2700s`

Success criteria:

- `0` runtime errors
- no executed cell regresses versus shallow
- key safety cell `1111/search7001` is nonnegative versus shallow

Recommended next:

- analyze the result before any wider union-policy runtime

Outcome:

- completed cells:
  - `4 / 4`
- runtime errors:
  - `0`
- elapsed:
  - `287.159s`
- nonnegative versus shallow:
  - `3 / 4`
- regressed versus shallow:
  - `1 / 4`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153119Z__stage35_rank6_route_lineage_additive_confirmation_v1/`
- closeout:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_additive_confirmation_closeout_2026-04-30.md`

Key safety failure:

- `1111/search7001 rank 6 d94845511e181f7c`
  - shallow:
    - `0.038`
  - confirmation:
    - `0.037`
  - delta:
    - `-0.001`

Interpretation:

- route-lineage remains useful mechanism evidence
- it failed as an additive policy rule in this form
- strict route-lineage is also not a replacement rule because group B contains
  old-keep / route-reject rows with existing positive evidence

Prediction comparison:

- real late local-rescue phenomenon:
  - supported
- narrow rank/slice policy improves selected cases:
  - partly supported as mechanism, not supported as a safe route-lineage
    additive rule
- general production policy from current signal:
  - not supported
- exact `0.437` threshold survives as-is:
  - not supported

Recommended next:

- do not launch a wider union-policy runtime
- close the current route-lineage rule as a policy candidate
- move back to offline mechanism analysis or a different candidate branch

## 2026-05-01 - Stage3 entry constant-local-depth handoff activation and launch

Question:

- after closing route-lineage as policy-negative, should the unanswered
  constant-local-depth entry-allocation question be reopened through saved
  handoff artefacts rather than a full-pipeline panel?

Activation extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage3_entry_const_local_depth_handoff_activation_v1.py`

Activation output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022336Z__stage3_entry_const_local_depth_handoff_activation_v1/`

Activation result:

- target rows:
  - `3`
- structurally active rows:
  - `3`
- mechanism-widened rows:
  - `3`
- runtime launched by extractor:
  - `0`
- each target widened:
  - legacy init3 `64`
  - candidate init3 `288`
  - delta `+224`
  - candidate new init3 keys `80`
  - candidate missing legacy keys `0`

Interpretation:

- constant-local-depth is structurally active on the saved handoffs
- this clears an offline activation gate for a one-cell handoff runtime
- do not return to the six-job full-pipeline panel

Launch plan:

- `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_handoff_resume_plan_2026-05-01.md`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_handoff_7005_v1.py`

Launch script:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_handoff_7005_launch_2026-05-01.ps1`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_handoff_7005_2026-05-01.log`

Active output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/`

Runtime budget:

- one cell:
  - `1111/search7005`
- retained same-cell legacy full-pipeline anchor:
  - `2.479h`
- entry widening factor:
  - `4.5x`
- intended wallclock:
  - `16h`
- watchdog cap:
  - `57600s`
- stop condition:
  - one candidate Stage-3 resume completes, fails, or watchdog reaches `16h`

Recommended next:

- after completion, analyze the one cell before launching any second handoff
  cell

Initial launch check:

- wrapper started:
  - yes
- runner process observed:
  - yes
- stage3 resume status observed:
  - `running`
- first observed phase:
  - `phaseA`
- first observed Phase-A progress:
  - `phaseA_done = 0 / 144`

Outcome:

- completed cells:
  - `5 / 5`
- errors:
  - `0`
- elapsed:
  - `354.964s`
- first-cell projection:
  - `316.850s` versus `2700s`
- policy decision mismatches:
  - `0`
- audit positives versus shallow:
  - `3`
- audit regressions versus shallow:
  - `2`
- rows reproducing prior deepening exactly:
  - `5 / 5`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T021919Z__stage35_rank6_local_rescue_recall_audit_v1/`
- closeout:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T021919Z__stage35_rank6_local_rescue_recall_audit_v1/stage35_rank6_local_rescue_recall_audit_closeout.md`

Interpretation:

- rejected positives and rejected regressions both reproduced exactly
- current softened policy is safe on the observed boundary but too conservative
  for recall
- more runtime should wait for an offline boundary-feature separator

Prediction comparison:

- real late local-rescue phenomenon:
  - supported
- narrow rank/slice policy improves selected cases:
  - partially supported; safe but too conservative
- general production policy from current signal:
  - not supported
- exact `0.437` threshold survives as-is:
  - not supported

Recommended next:

- do an offline boundary-feature extractor before more runtime

## 2026-04-30 - Stage35 rank-6 boundary-feature audit

Question:

- what boundary features separate the three rejected positives from the two
  rejected regressions without simply widening the policy?

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_rank6_boundary_feature_audit_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T032952Z__stage35_rank6_boundary_feature_audit_v1/`

Revision note:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_boundary_rule_revision_note_2026-04-30.md`

Result:

- rows:
  - `5`
- positives:
  - `3`
- regressions:
  - `2`
- numeric features scanned:
  - `27`
- threshold sketches scanned:
  - `172`
- perfect one-feature separators:
  - `0`

Interpretation:

- current simple numeric features do not separate the boundary
- the softened rank-6 policy is safe but too conservative
- more runtime should stop until a different feature family is added offline

Recommended next:

- no more runtime on this branch now
- expand offline features with route-composition or family/lineage context
  before deciding whether this can become a policy candidate

## 2026-04-30 - Stage35 rank-6 route-lineage boundary audit

Question:

- can pre-runtime route-composition or lineage features separate the three
  rejected rank-6 positives from the two rejected rank-6 regressions?

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_rank6_route_lineage_boundary_audit_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T033637Z__stage35_rank6_route_lineage_boundary_audit_v1/`

Review note:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_boundary_review_note_2026-04-30.md`

Result:

- rows:
  - `5`
- positives:
  - `3`
- regressions:
  - `2`
- single-feature perfect separators:
  - `0`
- two-feature perfect separators:
  - `141`

Most interpretable separator family:

- candidate source rank `1`
- and high route novelty, for example:
  - `candidate_novelty_distance_to_anchor >= 173.5`

Interpretation:

- route-lineage context is the missing feature family from the prior simple
  boundary audit
- the separator is posthoc on only five rows
- do not promote and do not launch runtime from this result alone

Recommended next:

- wait for external review
- if the route-lineage mechanism survives review, write a tiny
  held-out/disagreement confirmation design before any runtime
- if no honest held-out confirmation surface exists, close the rank-6 policy
  line as mechanism insight rather than a policy candidate

Review handoff:

- review pack:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_review_pack_2026-04-30/`
- zipped review pack:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_review_pack_2026-04-30.zip`
- paired source bundle:
  - `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260430T041152Z.zip`
- included support copy:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_review_pack_2026-04-30/40_support_files/get_src_extended_review_bundle.py`

## 2026-04-30 - Stage35 rank-6 route-lineage review action

External review file moved to:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_final_dev_review_draft_2026-04-30.md`

Action note:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_review_action_note_2026-04-30.md`

Review verdict:

- score-improvement direction:
  - strong enough to continue
- mechanism:
  - credible source-rank plus anchor-novelty hypothesis
- policy readiness:
  - no
- runtime readiness:
  - no
- next step:
  - strict offline held-out / disagreement scan using pre-runtime-safe lineage
    fields

Implemented strict offline confirmation-prep extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_rank6_route_lineage_confirmation_prep_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T151237Z__stage35_rank6_route_lineage_confirmation_prep_v1/`

Result:

- valid rows:
  - `21`
- invalid rows:
  - `1`
- old softened keep/reject:
  - `10 / 12`
- route-lineage keep/reject:
  - `9 / 12`
- rule disagreements:
  - `9`
- group A old reject / route keep:
  - `4`
- group B old keep / route reject:
  - `5`
- group C both keep:
  - `5`
- group D both reject:
  - `7`
- group E invalid:
  - `1`

Verification:

- extractor compile passed
- dedicated tests passed:
  - `9 / 9`

Interpretation:

- the review-requested strict offline scan found an honest
  held-out/disagreement surface
- missing lineage is invalid, not reject
- no runtime was launched

Recommended next:

- inspect group A and B against existing shallow/deep evidence
- write a fixed-rule tiny confirmation design if the rows remain coherent
- do not launch runtime without that design and explicit approval

Timing basis:

- recent selected-row guard-selector cells completed in `6.361s` and `10.620s`
- retained full fixed cells are multi-hour, but this harvest is late-stage-only
  and extractable after every completed cell

Outcome:

- completed cells:
  - `136 / 136`
- elapsed:
  - `721.112s`
- selected cells:
  - `132`
- selected positives versus selected-row start:
  - `73`
- selected negatives versus selected-row start:
  - `18`
- rank-6 slice:
  - selected positives: `19 / 22`
  - selected negatives: `0 / 22`
  - mean delta versus selected start: `+0.164`
  - best delta versus selected start: `+0.458`
- conclusion:
  - real local-rescue opportunity exists, especially in rank-6 rows
  - unfiltered strict guard-selector is not safe as a broad policy because it
    accepted `18` regressions outside the best slice
- recommended next:
  - run a focused deeper harvest on the strongest shallow-positive cells

## 2026-04-29 - launching focused Stage35 guard-selector frontier deepening harvest

Question:

- among the best shallow accepted rescue cells, does a deeper bounded Stage 3.5
  continuation improve beyond the one-round result?

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_selector_frontier_deepening_harvest_v1.py`

Launch wrapper:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_selector_frontier_deepening_harvest_launch_2026-04-29.ps1`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_selector_frontier_deepening_harvest_2026-04-29.log`

Runtime budget:

- intended wallclock:
  - `8h`
- hardcoded cap:
  - `28800s`
- per-cell cap:
  - `1800s`
- max cells:
  - `36`
- source:
  - strongest shallow-positive rows from
    `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/stage35_guard_selector_frontier_runtime_rows.csv`
- stop condition:
  - queue exhausted, wallclock cap reached, or first-cell serial projection
    exceeds the `28800s` budget
- partial writeback:
  - after every cell
- progress:
  - completed-versus-total, elapsed, per-cell elapsed, and ETA after every cell

Timing basis:

- the shallow same-entry harvest finished `136` cells in `721.112s`
- this deepening run changes rounds, beam, archive width, and mini-search
  settings, so it is treated as a new timing class
- the first completed cell is the budget anchor; if the projection is too high,
  the run stops after that cell with extractable partial outputs

Outcome:

- completed cells:
  - `15 / 15`
- errors:
  - `0`
- elapsed:
  - `1919.390s`
- first-cell projection:
  - first cell `164.446s`
  - projected serial `2466.693s`
  - decision: continue, safely under `28800s`
- selected cells:
  - `15 / 15`
- better than shallow:
  - `12 / 15`
- worse than shallow:
  - `3 / 15`
- mean delta versus shallow:
  - `+0.007533`
- mean delta versus selected-row start:
  - `+0.254600`
- mean delta versus retained anchor:
  - `+0.004533`
- rank-6 slice:
  - `13` rows
  - `11` better than shallow
  - `2` worse than shallow
  - mean delta versus shallow `+0.008154`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/`
- closeout:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/stage35_guard_selector_frontier_deepening_closeout.md`

Interpretation:

- deeper local rescue adds real but modest lift on top of the shallow harvest
- the mechanism remains promising as a narrow rank/slice-aware local-rescue
  branch
- the data does not support promoting broad unfiltered guard-selector
  selection, because the shallow broad harvest had accepted regressions and
  this focused deeper run still regressed `3` cells versus shallow

Recommended next:

- build an offline join/dedup extractor over shallow plus deepening outputs
- characterize safe rank-6 conditions before any more runtime
- only then consider a small policy canary

Runtime-reference refresh:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T001224Z__no_wli_runtime_history_reference_v1/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T001224Z__fixed_runtime_wallclock_reference_v1/`

## 2026-04-30 - Stage35 shallow-plus-deepening join/dedup extractor

Question:

- after deduplicating the shallow and deepening frontier-rescue rows, which
  slices look safe enough to justify a narrower local-rescue policy design?

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_guard_selector_frontier_deepening_join_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/`

Coverage:

- shallow rows:
  - `136`
- deep rows:
  - `15`
- deduplicated joined rows:
  - `14`
- duplicate keys:
  - `1`

Result:

- better than shallow:
  - `11 / 14`
- worse than shallow:
  - `3 / 14`
- mean deep minus shallow:
  - `+0.007000`
- mean deep minus retained:
  - `+0.004714`
- rank `6`:
  - `12` rows
  - `10` better
  - `2` worse
  - mean deep minus shallow `+0.007583`

Posthoc gate sketch:

- `rank6_selected_start_ge_0p437`:
  - rows `6`
  - better `6`
  - worse `0`
  - mean deep minus shallow `+0.009333`
- this is only a candidate gate because it was identified after seeing the
  deepening data

Interpretation:

- rank-6 local rescue remains the strongest mechanism lead
- the cleanest observed non-seed gate is selected-row strength:
  `selected_start_match_ratio >= 0.437`
- this is not enough to justify a broad runtime launch

Recommended next:

- write or generate an offline safety-rule note around the rank-6 selected-start
  gate
- require an explicit no-regression rule before any small runtime canary

## 2026-04-30 - Stage35 rank-6 selected-start gate safety extractor

Question:

- can the posthoc `rank6_selected_start_ge_0p437` hypothesis be converted into
  a safe predeclared local-rescue gate?

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_rank6_selected_start_gate_safety_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T014439Z__stage35_rank6_selected_start_gate_safety_v1/`

Prediction ledger for later comparison:

- comparison-only, not blame assignment
- real late local-rescue phenomenon:
  - `75-85%`
- narrow rank/slice policy improves selected cases:
  - `50-65%`
- general production policy from current signal:
  - `25-40%`
- exact `0.437` threshold survives as-is:
  - `15-25%`

Chat reminder:

- when this analysis branch closes, explicitly compare the final outcome
  against the prediction ledger in chat

Result:

- deep rank-6 rows:
  - `12`
- gate-kept deep rows:
  - `6`
- kept better/worse versus shallow:
  - `6 / 0`
- rejected better/worse versus shallow:
  - `4 / 2`
- observed rank-6 deepening regressions:
  - `2`
- kept regressions:
  - `0`
- rejected deepening positives:
  - `4`
- shallow rank-6 selected rows:
  - `20`
- shallow kept positives/negatives:
  - `8 / 0`
- shallow rejected positives/negatives:
  - `9 / 1`

Interpretation:

- the gate removes all observed rank-6 deepening regressions
- the gate is too conservative to promote directly because it rejects real
  positives, including the large `1111/search7002 rank 6` row
- exact threshold `0.437` remains posthoc

Recommended next:

- do not runtime-canary this gate as-is
- write a predeclared policy sketch that either softens selected-start gating
  or combines it with a second non-seed feature

## 2026-04-30 - Stage35 rank-6 local-rescue policy sketch

Status:

- offline note complete

Note:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_local_rescue_policy_sketch_2026-04-30.md`

Candidate rule:

- candidate rank is `6`
- and either:
  - `selected_start_match_ratio >= 0.437`
  - or `shallow_resume_minus_selected >= 0.400`

Observed dedup result:

- kept rows:
  - `7`
- kept better/worse versus shallow:
  - `7 / 0`
- mean deep minus shallow:
  - `+0.010143`
- rejected rows:
  - `5`
- rejected better/worse versus shallow:
  - `3 / 2`

Interpretation:

- this softened rule recovers the largest rejected positive while preserving
  zero observed kept regressions in the dedup deepening set
- still posthoc; not a promoted policy

Recommended next:

- no runtime yet
- write a canary design note that fixes exact cells and decision rules before
  any launch

## 2026-04-30 - Stage35 rank-6 local-rescue canary design

Status:

- design note complete
- no runtime launched

Note:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_local_rescue_canary_design_2026-04-30.md`

Candidate rule:

- rank `6`
- and either:
  - `selected_start_match_ratio >= 0.437`
  - or `shallow_resume_minus_selected >= 0.400`

Proposed cells:

- hard-gate keep:
  - `1511/search7004 rank 6 51b7dab086e94186`
- shallow-delta keep:
  - `1111/search7002 rank 6 74dfe3cb559629f7`
- observed-regression reject:
  - `1111/search7004 rank 6 511a29668b8c44d1`
- rejected-positive audit/control:
  - `1411/search7005 rank 6 b47e22bc63e7c189`

Budget if approved later:

- intended wallclock:
  - `45m`
- hard cap:
  - `2700s`
- per-cell rescue cap:
  - `600s`
- first-cell projection stop:
  - required

Current recommendation:

- do not launch runtime until explicitly approved
- if approved, implement a hardcoded four-cell canary runner with policy
  decision rows and explicit skip/audit outputs

## 2026-04-30 - launching Stage35 rank-6 local-rescue canary

Question:

- does the softened rank-6 local-rescue policy execute the two expected keep
  cells safely while rejecting the known regression and recording
  rejected-positive opportunity cost?

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_local_rescue_canary_v1.py`

Launch wrapper:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_rank6_local_rescue_canary_launch_2026-04-30.ps1`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_canary_2026-04-30.log`

Runtime budget:

- intended wallclock:
  - `45m`
- hardcoded cap:
  - `2700s`
- per-cell rescue cap:
  - `600s`
- stop condition:
  - all four cells processed, wallclock cap reached, or first executed rescue
    cell projection exceeds `2700s`
- partial writeback:
  - after every cell
- progress:
  - completed-versus-total, elapsed, per-cell elapsed, and ETA after every cell

Timing basis:

- prior deepening cells in the selected design ran between about `75s` and
  `271s`
- only two cells are expected to execute rescue; two cells should be policy
  skips

Outcome:

- completed cells:
  - `4 / 4`
- executed rescue cells:
  - `2`
- policy skips:
  - `2`
- errors:
  - `0`
- elapsed:
  - `183.535s`
- first executed cell:
  - `84.198s`
- first executed projection:
  - `168.396s` versus `2700s`
- policy decision mismatches:
  - `0`
- executed cells nonnegative versus shallow:
  - `2 / 2`
- executed cells regressed versus shallow:
  - `0 / 2`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T015732Z__stage35_rank6_local_rescue_canary_v1/`
- closeout:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T015732Z__stage35_rank6_local_rescue_canary_v1/stage35_rank6_local_rescue_canary_closeout.md`

Prediction comparison:

- real late local-rescue phenomenon:
  - supported
- narrow rank/slice policy improves selected cases:
  - supported for this tiny canary, not generalized
- general production policy from current signal:
  - not supported
- exact `0.437` threshold survives as-is:
  - still unlikely

Interpretation:

- canary passed implementation and no-regression checks
- the softened rank-6 policy remains a small candidate only
- do not promote as production or broaden directly

Recommended next:

- if continuing runtime, run only a small same-rule recall/audit microbatch
  focused on the rejected-positive boundary

## 2026-04-30 - launching Stage35 rank-6 local-rescue recall/audit microbatch

Question:

- among rows rejected by the softened rank-6 policy, how much reproducible
  local-rescue opportunity cost remains, and how many rejected rows are
  necessary safety rejects?

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_local_rescue_recall_audit_v1.py`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_recall_audit_2026-04-30.log`

Runtime budget:

- intended wallclock:
  - `45m`
- hardcoded cap:
  - `2700s`
- per-cell rescue cap:
  - `600s`
- prior same-shape timing:
  - selected audit cells previously ran between about `89s` and `159s`
  - expected serial time about `526s` plus load/write overhead
- stop condition:
  - all five cells processed, wallclock cap reached, or first-cell projection
    exceeds `2700s`
- partial writeback:
  - after every cell
- progress:
  - completed-versus-total, elapsed, per-cell elapsed, and ETA after every cell

## 2026-05-02 - solver-development pivot review pack assembled

Context:

- the latest Stage 3.5 frontier-space robustness harvest found real local
  rescue signal but no policy-clean separator
- the acceptance-boundary audit found `0` perfect single-rule and `0` perfect
  two-feature separators over the completed `48`-row harvest
- broad local-rescue policy widening is closed for now

Synthesis:

- `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_synthesis_2026-05-02.md`

Review pack:

- folder:
  - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_review_pack_2026-05-02/`
- sendable zip:
  - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_review_pack_2026-05-02.zip`
- nested source bundle inside the pack:
  - `90_source_bundle/get_src_extended_review_bundle__20260502T022329Z.zip`

Method update:

- `planning/projects/no_wli/20_active_plans/no_wli_review_pack_method_note_2026-04-25.md`
- changed the default handoff rule so a sendable review pack should include the
  generated source zip inside the pack where practical
- reviewer-facing documents should use paths relative to the review zip root

Recommendation:

- do not launch another broad runtime batch from the current local-rescue
  evidence
- next work should either:
  - build an experiment ledger / oracle-gap tool over retained outputs
  - or write a held-out validation harness for the Stage-2 checkpoint line

## 2026-05-12 - launching PhaseB Runeberg NOSE Stage 3 PCB continuation

Question:

- continue the FWD no-WLI full-chunk calibration on medium/long word bands
  after combined Stage 1/2 coverage reached chunk index `12400`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_stage3_len5_14_pcb.py`

Launch note:

- `planning/working/stage3_fwd_full_len5_14_pcb_launch_20260512.md`

Console/log targets:

- runner tee log:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/logs/stage3_fwd_full_len5_14_pcb.log`
- PowerShell tee log:
  - `output/logs/stage3_fwd_full_len5_14_pcb_run.log`

Configuration:

- PCB only; do not use PCA for this stage
- run label:
  - `stage3_fwd_full_len5_14_pcb`
- chunk start / chunks:
  - `12400` / `10000`
- direction / region / start shift:
  - `fwd` / `full` / `0`
- active lengths:
  - `5..14`
- ladder profile:
  - `v0_3_plus_long_relaxed_v2_len5_14`
- dictionary cuts:
  - `phaseA14_strict_selected`
  - `phaseA14_normal_selected`
- expected samples / feature rows:
  - `370000` / `36260000`
- expected next chunk start:
  - `22400`

Runtime budget:

- same-machine Stage 2 PCB anchor:
  - `432.6328108145182` feature rows/s
  - `4.005859359393687` samples/s
- projected wallclock:
  - about `23.28h` by feature rows
  - about `25.66h` by samples
- intended wallclock budget:
  - `23-26h`
- stop condition:
  - natural completion of the configured `10000` clean chunks, or runner
    failure; do not start another stage until this result is reviewed

Preflight:

- shared runner tests:
  - `33 passed`
- exact config assertion:
  - passed

Progress checkpoint:

- as of the road-test build check:
  - checkpoint `12`
  - samples `6000 / 444000`
  - feature rows `480000 / 35520000`
  - elapsed `1093.9s`
  - median remaining estimate `74051.7s`
  - no raw `feature_rows.csv` observed
- status:
  - running; do not start another calibration continuation before Stage 4 review

## 2026-05-13 - PhaseB real no-WLI candidate span-Hamming road test v1

Purpose:

- report-only test of calibrated span-Hamming evidence against real no-WLI
  solver/scorer candidates
- no production scorer weights changed

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_span_hamming_real_candidate_road_test_v1.py`

Output:

- output folder:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_real_candidate_road_test_v1`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_real_candidate_road_test_v1_review_pack_2026-05-13.zip`
- working note:
  - `planning/working/phaseB_span_hamming_real_candidate_road_test_v1_20260513.md`

Inputs:

- active calibration:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb`
- candidate source:
  - `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/50_completed_job_runs`
- active damage reference:
  - `word_local_substitution`, level `0.20`
- active profile:
  - lengths `5..14`, strict + normal dictionary cuts, FWD/full/shift `0`

Run result:

- candidates:
  - `246`
- chunks:
  - `492`
- candidate feature comparison rows:
  - `578592`
- elapsed:
  - about `196s`
- review zip:
  - about `27.6 MB`

Main findings:

- Panel A, medium lengths `5..9`, separates labelled good from labelled bad but is
  not sufficient alone:
  - combined known/likely bad pass fraction at threshold `0.5`: `0.616`
  - known-good mean `3.665`
  - likely-good mean `2.764`
  - known-bad mean `0.591`
  - likely-bad mean `0.942`
- Panel B, longer lengths `10..14`, is weaker in this v1 run:
  - known-good mean `0.527`
  - known-bad mean `-0.003`
- Panel D, strict precision rows, gives a useful precision signal:
  - known-good mean `1.911`
  - known-bad mean `0.302`
- Panel C is absent by design in this v1 because the active Stage 3 profile is
  lengths `5..14`.
- constructed target-vs-final_best pairwise checks:
  - `20` pairs
  - Panel A preferred the known-good target in all `20`
  - caveat: these are target controls, not token-resolved historical pair rows

Caveat:

- historical pairwise scorer rows were found, but the original token artifacts were
  not fully available locally; v1 therefore uses token-resolved fixed-panel review
  candidates and records this limitation in the pack.

Follow-up interpretation note:

- `planning/working/phaseB_span_hamming_road_test_v1_review_next_actions_20260513.md`
- working conclusion:
  - span-Hamming is real and useful local damaged-word evidence
  - Panel A lengths `5..9` is strongest local evidence
  - Panel D strict evidence adds precision
  - Panel B is weaker in v1 and should be refreshed after Stage 4
  - span-Hamming alone does not solve high-scoring gibberish
  - next critical test is hard-pair rescue/break analysis using real candidate
    token streams
- scorer policy:
  - no production scorer weights, defaults, or ranking policy changes from v1

Stage 4 status during follow-up note:

- latest observed checkpoint:
  - checkpoint `40`
  - samples `20000 / 444000`
  - feature rows `1600000 / 35520000`
  - elapsed `3279.4s`
  - median remaining estimate `71402.0s`
- status:
  - still running on PCB
  - do not start another calibration stage until Stage 4 finishes and is reviewed

## 2026-05-13 - PhaseB span-Hamming hard-pair road test v1

Purpose:

- resolve the historical no-WLI pairwise rescore rows to real candidate token
  streams and run hard rescue/break accounting
- report-only; no production scorer changes

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_span_hamming_hard_pair_road_test_v1.py`

Output:

- output folder:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_hard_pair_road_test_v1_review_pack_2026-05-13.zip`
- working note:
  - `planning/working/phaseB_span_hamming_hard_pair_road_test_v1_20260513.md`

Inputs:

- pair rows:
  - `planning/projects/no_wli/40_review_summaries/no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02/historical_pairwise_rescore/historical_pairwise_rescore_pairs.csv`
- token source:
  - `planning/projects/no_wli/40_review_summaries/no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02/historical_partial_texts/unique_partial_text_rows.csv`
- active calibration:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb`

Run result:

- historical pair rows:
  - `2594`
- current-scorer misrank rows:
  - `602`
- resolved token hashes:
  - `604 / 604`
- candidates scored once:
  - `604`
- chunks:
  - `1208`
- feature comparison rows:
  - `1420608`
- elapsed:
  - about `473s`
- review zip:
  - about `66.3 MB`
- zip integrity:
  - passed

Hard-pair result:

- Panel A, lengths `5..9`:
  - truth-better preference `1904 / 2594` (`0.734`)
  - rescues `274`
  - breaks `362`
  - net `-88`
- Panel B, lengths `10..14`:
  - truth-better preference `1326 / 2594` (`0.511`)
  - rescues `168`
  - breaks `828`
  - net `-660`
- Panel D, strict precision:
  - truth-better preference `1684 / 2594` (`0.649`)
  - rescues `168`
  - breaks `476`
  - net `-308`

Margin sweep:

- Panel A best net in tested margin sweep:
  - threshold `0.4`
  - rescues `4`
  - breaks `0`
  - overrides `788`
  - net `+4`
- Panel B best net:
  - `0`
- Panel D best net:
  - `0`

Conclusion:

- Panel A is directionally useful local evidence, but not a safe standalone
  rescue/break override.
- Panel D remains useful support/precision evidence, but not a standalone chooser.
- Panel B should still be refreshed after Stage 4, but current hard-pair evidence
  does not support using it as a chooser.
- The next report-only scorer work should combine local span-Hamming evidence with
  order/phrase/ngram coherence and keep hard-pair rescue/break accounting.

Stage 4 status during hard-pair closeout:

- latest observed checkpoint:
  - checkpoint `54`
  - samples `27000 / 444000`
  - feature rows `2160000 / 35520000`
  - elapsed `4517.6s`
  - median remaining estimate `69409.9s`
- status:
  - still running on PCB
  - no later calibration stage launched

## 2026-05-13 - PhaseB candidate manual inspection pack v1

Purpose:

- make the hard-pair candidate token streams human-readable enough to inspect
  why Panel A helps or fails
- include bad candidates that span-Hamming likes, good supported candidates,
  rescues, breaks, and high-current-score bad cases
- report-only; no scoring or calibration changes

Script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_span_hamming_candidate_manual_inspection_v1.py`

Output:

- output folder:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_candidate_manual_inspection_v1_review_pack_2026-05-13.zip`
- working note:
  - `planning/working/phaseB_span_hamming_candidate_manual_inspection_v1_20260513.md`

Inputs:

- hard-pair output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1`
- token source:
  - `planning/projects/no_wli/40_review_summaries/no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02/historical_partial_texts/unique_partial_text_rows.csv`

Run result:

- candidates with readable token/latin snippets:
  - `604 / 604`
- pairs with both candidate texts resolved:
  - `2594 / 2594`
- label counts:
  - `known_bad`: `33`
  - `known_good`: `47`
  - `likely_bad`: `90`
  - `likely_good`: `269`
  - `unknown`: `165`
- snippets:
  - first/middle/last `250` tokens
- full text sidecar:
  - `candidate_full_texts.jsonl.gz`
- missing/incomplete sources:
  - none observed
- zip integrity:
  - passed

Highest Panel A known/likely bad examples:

- `hist_text_53762f26f296b010bdb8fb6f`:
  - Panel A `2.32353354606`, truth `0.041`, current `0.184461046208`
- `hist_text_039bb659d84282dc2df09377`:
  - Panel A `2.31364281988`, truth `0.041`, current `0.222691790618`
- `hist_text_67fed75e05c7225c4957a116`:
  - Panel A `2.31191441559`, truth `0.041`, current `0.223544661001`

Largest Panel A rescue examples:

- `a704860e4663b7e9bb97650a`:
  - gap `0.4348291824`, truth better `0.455`, truth worse `0.335`
- `27bbc31318d7a881876d4f31`:
  - gap `0.4348291824`, truth better `0.455`, truth worse `0.335`

Largest Panel A break examples:

- `06917810604f4512eed1b840`:
  - gap `-0.31317518882`, truth better `0.466`, truth worse `0.337`
- `dee7d3e772b14e218eac8067`:
  - gap `-0.31317518882`, truth better `0.466`, truth worse `0.337`

Automatic clue:

- repeated-3gram contrast alone does not explain the breaks:
  - breaks mean truth-worse minus truth-better repeated-3gram rate `-0.00411873`
  - rescues mean truth-worse minus truth-better repeated-3gram rate `-0.00351798`

Stage 4 status during manual-inspection closeout:

- latest observed checkpoint:
  - checkpoint `623`
  - samples `311500 / 444000`
  - feature rows `24920000 / 35520000`
  - elapsed `48813.5s`
  - median remaining estimate `20800.2s`
- status:
  - still running on PCB
  - no later calibration stage launched

## 2026-05-14 - Stage 4 FWD full len8-14 PCB closeout and review pack

Run:

- `stage4_fwd_full_len8_14_pcb`

Status:

- completed cleanly
- `run_state.json` status:
  - `complete`
- no traceback, exception, warning, native command error, or unraisable-hook hits
  found in the Stage 4 runner logs

Coverage:

- clean chunks:
  - `12000`
- samples:
  - `444000`
- feature rows:
  - `35520000`
- next chunk start:
  - `34400`
- raw `feature_rows.csv`:
  - absent as intended
- histograms / quantiles:
  - written / written

Timing:

- elapsed:
  - `69326.90s`
  - `19.26h`
- observed samples/sec:
  - `6.404`
- observed feature rows/sec:
  - `512.36`
- outcome:
  - faster than the retained `23-29h` budget

Review outputs:

- review analysis folder:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage4_fwd_full_len8_14_pcb_review_analysis`
- review pack folder:
  - `planning/projects/no_wli/40_review_summaries/stage4_fwd_full_len8_14_pcb_review_pack_2026-05-14`
- review pack zip:
  - `planning/projects/no_wli/40_review_summaries/stage4_fwd_full_len8_14_pcb_review_pack_2026-05-14.zip`
- zip integrity:
  - passed
- pack size:
  - about `12.7 MB`

Pack contents:

- completed Stage 4 run outputs:
  - `final_summary.json`
  - `run_state.json`
  - `run_manifest.json`
  - `readout.md`
  - `timing_checkpoints.csv`
  - `rolling_feature_summary.csv`
  - `final_feature_summary.csv`
  - `damaged_vs_null_summary.csv`
  - `damaged_vs_null_by_view.csv.gz`
  - `feature_histograms.csv.gz`
  - `feature_quantiles.csv.gz`
  - `dictionary_hash_manifest.csv`
- compact review analyses:
  - `stage4_review_conclusions.md`
  - `stage4_primary_signal_by_length.csv`
  - `stage4_top_local_null_rows.csv`
  - `stage4_top_block_shuffle_rows.csv`
  - `stage3_vs_stage4_by_length_rollup.csv`
  - `stage3_vs_stage4_len8_14_comparison.csv`
  - compact sample/convergence extracts
- relevant source files:
  - Stage 4 runner
  - shared ladder runner
  - road-test/manual-inspection scripts used for interpretation context
  - Stage 4 shared tests
  - `tools/get_src_extended_review_bundle.py`
- launch/planning context and logs

Main Stage 4 finding:

- Stage 4 strengthens long-span calibration, especially lengths `8..11`, but the
  signal remains length-dependent.
- For `word_local_substitution` level `0.20`, normal dictionary, local-null
  comparisons:
  - length `8` mean Cohen d `3.80`, max `6.59`
  - length `9` mean Cohen d `3.07`, max `6.23`
  - length `10` mean Cohen d `2.13`, max `3.61`
  - length `11` mean Cohen d `1.73`, max `3.44`
  - length `12` mean Cohen d `1.22`, max `2.18`
  - length `13` mean Cohen d `0.98`, max `2.11`
  - length `14` mean Cohen d `0.69`, max `1.46`

Block-shuffle finding:

- block-shuffle separation remains much weaker than local-null separation.
- This reinforces the existing interpretation:
  - span-Hamming is local word-like evidence
  - it is not an order/coherence test

Stage 3 to Stage 4 comparison:

- Stage 4 modestly improves overlapping lengths `8..14`.
- Mean Cohen d deltas for primary local-null rows:
  - length `8`: `+0.130`
  - length `9`: `+0.105`
  - length `10`: `+0.088`
  - length `11`: `+0.081`
  - length `12`: `+0.082`
  - length `13`: `+0.070`
  - length `14`: `+0.042`

Conclusion:

- Do not change production scorer weights or ranking policy from Stage 4 alone.
- Stage 4 supports refreshing/merging the calibration and rerunning Panel B road-test
  tables.
- It does not change the hard-pair conclusion:
  - span-Hamming is useful local evidence
  - it is not safe as a standalone override
  - next report-only work should combine local evidence with order/phrase/ngram
    coherence and evaluate on the hard-pair rescue/break dataset

## 2026-05-14 - pause no-WLI calibration/data-taking

Decision:

- pause new no-WLI calibration/data-taking for now
- do not launch Stage 5 calibration, PCA data collection, or another PCB continuation
  by default
- data-taking may be unpaused later only if report-only tests or reviewer questions
  identify a concrete missing data/calibration slice

Pause notes:

- pause note:
  - `planning/working/no_wli_data_taking_pause_20260514.md`
- handoff note for next agent:
  - `planning/working/no_wli_current_status_handoff_data_pause_20260514.md`

Reason:

- Stage 1-4 have produced enough calibration for the current decision point.
- Stage 4 completed cleanly and strengthened long-span calibration, especially
  lengths `8..11`.
- Hard-pair road test showed the limiting factor is not just more local
  span-Hamming calibration:
  - Panel A is directionally useful but not a safe standalone override
  - Panel D is support/precision evidence but not a standalone chooser
  - bad candidates can contain local word-like fragments
- Next scientific need is order/phrase/ngram coherence evidence and refreshed
  report-only road-test analysis, not automatic additional calibration data.

While paused:

- merge/refresh Stage 1-4 calibration for report-only use
- refresh Panel B road-test tables with Stage 4 included
- use the hard-pair dataset for rescue/break accounting
- inspect bad candidates that local span-Hamming likes via the manual inspection pack
- do not change production scorer weights/defaults/ranking policy

Unpause conditions:

- a merged Stage 1-4 road test exposes a concrete missing calibration slice
- Panel B or another panel remains unstable for a reason more data can address
- a new report-only experiment requires a narrowly scoped canary

If unpaused:

- write a new plan first
- state the scientific question
- declare exact config and stop condition
- justify runtime from retained timing evidence
- keep the run as small and independently complete as possible

Launch status:

- launched in separate PowerShell window via:
  - `planning/projects/no_wli/60_launch_scripts/stage4_fwd_full_len8_14_pcb_launch_2026-05-13.ps1`
- first checkpoint:
  - `500 / 444000` samples
  - `40000 / 35520000` feature rows
  - `93.219729s` elapsed
  - `429.093715465` feature rows/s
  - projected total about `22.99h`
- decision:
  - continue; first checkpoint is inside the feature-row-based expectation,
    and no later calibration continuation is authorized until Stage 4 is
    reviewed

Launch status:

- launched in separate PowerShell window via:
  - `planning/projects/no_wli/60_launch_scripts/stage3_fwd_full_len5_14_pcb_launch_2026-05-12.ps1`
- first checkpoint:
  - `500 / 370000` samples
  - `49000 / 36260000` feature rows
  - `126.731909s` elapsed
  - `386.642957889` feature rows/s
  - projected total about `26.05h`
- decision:
  - continue; first checkpoint is on the upper edge of the `23-26h` budget
    and no follow-on stage is authorized until this result is reviewed

Completion:

- status:
  - `complete`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb`
- elapsed:
  - `85298.1381107s`
  - `23.69h`
- actual chunks / samples / feature rows:
  - `10000` / `370000` / `36260000`
- next chunk start:
  - `22400`
- observed throughput:
  - `4.337726569363257` samples/s
  - `425.09720379759915` feature rows/s
- save check:
  - JSON outputs parse
  - `run_state.json` status is `complete`
  - raw `feature_rows.csv` is absent as configured
  - saved tee logs have no error/warning search hits for traceback,
    exception, failure, native command error, or unraisablehook text

Review pack:

- folder:
  - `planning/projects/no_wli/40_review_summaries/stage3_fwd_full_len5_14_pcb_review_pack_2026-05-13/`
- zip:
  - `planning/projects/no_wli/40_review_summaries/stage3_fwd_full_len5_14_pcb_review_pack_2026-05-13.zip`
- pack scope:
  - portable aggregate data and summaries only
  - no source-code snapshot
  - raw per-sample rows and full detailed convergence table excluded

## 2026-05-13 - launching PhaseB Runeberg NOSE Stage 4 PCB continuation

Question:

- add more FWD no-WLI full-chunk calibration coverage for longer word spans,
  where Stage 3 showed weaker and less stable evidence

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_stage4_len8_14_pcb.py`

Launch note:

- `planning/working/stage4_fwd_full_len8_14_pcb_launch_20260513.md`

Console/log targets:

- runner tee log:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/logs/stage4_fwd_full_len8_14_pcb.log`
- PowerShell tee log:
  - `output/logs/stage4_fwd_full_len8_14_pcb_run.log`

Configuration:

- PCB only; do not use PCA for this stage
- run label:
  - `stage4_fwd_full_len8_14_pcb`
- chunk start / chunks:
  - `22400` / `12000`
- direction / region / start shift:
  - `fwd` / `full` / `0`
- active lengths:
  - `8..14`
- ladder profile:
  - `v0_3_plus_long_relaxed_v2_len8_14`
- dictionary cuts:
  - `phaseA14_strict_selected`
  - `phaseA14_normal_selected`
- expected samples / feature rows:
  - `444000` / `35520000`
- expected next chunk start:
  - `34400`

Runtime budget:

- same-machine Stage 3 anchor:
  - `425.09720379759915` feature rows/s
  - `4.337726569363257` samples/s
- projected wallclock:
  - about `23.21h` by feature rows
  - about `28.43h` by samples
- intended wallclock budget:
  - `23-29h`
- stop condition:
  - natural completion of the configured `12000` clean chunks, or runner
    failure; do not start another calibration continuation until this result
    is reviewed

Preflight:

- shared runner tests:
  - `33 passed`
- exact config assertion:
  - passed


## 2026-06-04 - Failed-decryption N3C stratified query study reached review gate

- Implemented an exact memory-bounded sorted-block query path and vectorized
  full-phrase N3C verification.
- The vectorized verifier preserved exact semantics and reduced the isolated
  `10-11` medium-group runtime from about `181.656s` to about `18.9s`.
- Completed the requested `2 rare + 3 medium + 3 common` query study in every
  length bucket over `80` retained candidates.
- Consolidated result:
  - status: `review_gate_ready`
  - complete groups: `40`
  - verified hits: `195,975`
  - verified clusters: `20,481`
  - summed group runtime: about `510.7s`
  - peak memory: about `718.4 MB`
- Hit yield by bucket was `175,004`, `20,526`, `444`, `1`, and `0`.
- This remains partial stratified evidence. It does not approve full N3C,
  production scoring/ranking, or order-2 filtering.
- Next gate: external review.
- Final sendable pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_stratified_query_portable_closed_review_pack_2026-06-04.zip`
- Fresh extracted portable pack verification: `13 passed` without
  `PYTHONPATH`.

## 2026-06-04 - External review accepted N3C stratified query pack

- Verdict accepted the exact sorted-block/vectorized query path, memory/runtime
  behaviour, and partial stratified study.
- Order 2 as a hard filter was rejected; it remains priority-only.
- Wider N3C querying was approved only for the same `80`-candidate sample.
- Full `734`-candidate fixture, score-bearing use, production scoring, and
  production ranking remain not approved.
- Required corrections recorded and implemented for the next runner:
  - logical groups are no longer individual runtime chunks
  - global candidate clusters are computed after combining all N3C hits
  - pairwise/gold report-only ledger is emitted
  - hit records include HD fields and exact flag
  - runtime manifests are tracked for the next pack
- Full-80 runner:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_full80_query_evidence_v1.py`

## 2026-06-04 - Full80 monolithic launch stopped and rescoped

- Launched the approved full-80 runner in a separate PowerShell process with
  repo-relative tee logging.
- Stopped after `3/1,028` chunks because the first chunks projected beyond the
  declared `12,600` second budget.
- Preserved partial output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_full80_query_evidence_v1/`
- Rescoped to an independently complete full `8-9` bucket budget anchor:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_full80_bucket_8_9_query_evidence_v1.py`

## 2026-06-05 - Full80 bucket anchors 8-9 and 10-11 completed

- `8-9` completed in `2,384.875s`: `41` chunks, `39` logical groups,
  `1,373,314` hits, `291` global candidate clusters.
- `10-11` completed in `2,177.859s`: `105` chunks, `67` logical groups,
  `258,892` hits, `1,451` global candidate clusters.
- Both passed budget and memory gates.
- Pairwise report-only ledgers still show break risk for simple hit and simple
  cluster counts, so no score-bearing promotion is supported.
- Prepared next visible bucket runner for `12-14`.

## 2026-06-05 - Remaining full80 N3C bucket runs completed

- Visible serial runner completed:
  - `12-14`: `272` chunks, `143` logical groups, `33,439` hits,
    `1,632` bucket-local global clusters, `4,542.6s`
  - `15-17`: `317` chunks, `181` logical groups, `1,922` hits,
    `314` bucket-local global clusters, `3,202.8s`
  - `18+`: `293` chunks, `272` logical groups, `150` hits,
    `41` bucket-local global clusters, `2,329.8s`
- All approved full80 N3C chunks are now covered by bucket outputs.
- Next step is consolidation across bucket hit rows, not more runtime.

## 2026-06-05 - Full80 N3C consolidation and review pack

- Consolidated all five bucket outputs into:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_full80_consolidated_evidence_v1/`
- Full selected-80 N3C coverage:
  - `1,028` chunks
  - `702` logical groups
  - `613,280,613` phrase rows
  - `1,667,717` verified hits
  - true all-bucket global candidate clusters: `275`
  - exact global candidate clusters: `1,648`
- Pairwise in-sample labelled ledger:
  - hit count: `4` agree / `12` break
  - global cluster count: `4` agree / `10` break / `2` tie
  - exact global cluster count: `6` agree / `10` break
- Built packaging-closed review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_full80_consolidated_packaging_closed_review_pack_2026-06-05.zip`
- Final ZIP facts:
  - entries: `91`
  - size: `806,518` bytes
  - backslash entries: `0`
  - under `50 MB`: `true`
- Fresh extracted consolidated portable smoke: `2 passed`.
- Removed superseded same-day full80 review-pack variants without the
  `packaging_closed` name to prevent another stale-pack send.
- Conclusion remains report-only: no score-bearing use, no production scoring,
  no production ranking, and no `734`-candidate expansion until external
  review.

## 2026-06-05 - v2 correction gate and S3 strict setup

- Read authoritative v2 handoff:
  `planning/temp_files/n3c_normal_correction_strict_full80_v2/00_authoritative_v2_handoff.md`
- Implemented corrected annotated cluster aggregation:
  ordinary clusters are built from all hit spans, then annotated with
  `has_exact` and exact-hit counts.
- Implemented semantic pair identity:
  `trial_id + sorted(candidate_a_id, candidate_b_id)`.
- Rebuilt corrected normal consolidation from existing normal bucket hit files:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_evidence_v1/`
- No normal query rerun occurred.
- Corrected normal results:
  - verified hits: `1,667,717`
  - ordinary global candidate clusters: `275`
  - corrected exact-containing global candidate clusters: `225`
  - raw pair rows: `16`
  - unique semantic pairs: `8`
  - rescue-capable unique semantic pairs: `0`
- Built corrected normal review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_review_pack_2026-06-05.zip`
- Corrected pack facts:
  - entries: `60`
  - size: `344,857` bytes
  - fresh extracted portable tests: `8 passed`
- Added explicit S3 strict RunSpec selection and resume identity guard.
- S3 strict locked inventory test passes:
  `815` chunks, `702` logical groups, `365,516,232` phrase rows.
- Added five explicit strict full80 bucket scripts with approved budgets.
- Focused correction test set: `26 passed`.
- Next action: launch S3 strict buckets sequentially in visible PowerShell
  windows with repo-relative tee logs. Stop on first nonzero exit.
- Still not approved: all-`734` expansion, score-bearing use, production
  scoring/ranking changes.

## 2026-06-06 - Strict 320 all-data pack completed

- Completed the missing `remaining_batch_03` tail buckets:
  - `15-17`: `205` chunks, `677` hits, runtime `3,166.1s`
  - `18+`: `272` chunks, `1` hit, runtime `2,880.0s`
- All strict bucket outputs are now complete:
  - original selected 80: `5` buckets
  - remaining batch 01: `5` buckets
  - remaining batch 02: `5` buckets
  - remaining batch 03: `5` buckets
- Built combined strict 320 corrected consolidation:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_320_corrected_consolidated_evidence_v1/`
- Combined strict 320 results:
  - candidates: `320`
  - bucket outputs: `20`
  - phrase rows queried: `1,462,064,928`
  - verified hits: `6,415,767`
  - global candidate clusters: `1,115`
  - exact-containing global candidate clusters: `893`
  - unique semantic pairs: `590`
  - rescue-capable unique semantic pairs: `0`
  - summed bucket runtime: `51,880.5s`
- Built all-data review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_strict_320_all_data_review_pack_2026-06-06.zip`
- Pack facts:
  - entries: `199`
  - size: `1,135,215` bytes
  - fresh extracted portable tests: `13 passed`
- This pack includes corrected normal evidence, original selected-80
  strict-vs-normal comparison, strict 320 consolidation, all 20 strict bucket
  summaries/manifests, runtime logs, hit-file hashes, and sampled hit rows.
- Still not approved: all-`734` expansion, score-bearing use, production
  scoring/ranking changes, raw-hit authority, or simple-cluster authority.

## 2026-06-06 - Strict O3 anchored-region quickcheck

- Integrated report-only quickcheck:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1.py`
- Output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1/`
- Inputs:
  - strict-320 hit manifest:
    `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_320_corrected_consolidated_evidence_v1/hit_file_manifest_rows.csv`
  - unique semantic pairs:
    `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_320_corrected_consolidated_evidence_v1/unique_semantic_pairwise_gold_n3c_report_rows.csv`
  - `20` strict hit CSV files, `6,415,767` hit rows
- Runtime: `156.9s`
- Output rows:
  - candidate summaries: `1,882`
  - selected anchor regions: `34,337`
  - pairwise rows: `2,284`
  - margin threshold rows: `64`
- Focused tests:
  `C:\Python\Python311\python.exe -m pytest tests/tools/test_phaseB_n3c_strict_320_anchor_lens_quickcheck_v1.py -q`
  -> `4 passed`
- First decision table highlights:
  - `hd0_len8`: all-pair break rate `0.254237`, roughly raw-hit baseline
  - `hd0_len10`: all covered-pair break rate `0.202062`; at margin `20`,
    `251` covered pairs, `227` agree, `24` break, break rate `0.095618`
  - `hd0_len12`: `22` covered pairs, `0` breaks, but coverage is small
  - `hd_le1_len12`: broad all-pair break rate `0.276956`, worse than raw-hit
  - `hd_le2_len12`: broad all-pair break rate `0.361017`, clearly worse
- Interpretation: anchored exact O3 has a promising margin-gated region,
  especially `hd0_len10`. HD<=1/HD<=2 broad support should stay telemetry-only
  or constrained to already selected exact anchor regions. This remains
  report-only and does not approve score-bearing use.

## 2026-06-06 - Strict O3 anchor joint-rule sweep

- Integrated report-only joint sweep:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_320_anchor_joint_rule_sweep_v1.py`
- Output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_320_anchor_joint_rule_sweep_v1/`
- Input:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1/candidate_anchor_pairwise_rows.csv`
- Input pairwise rows: `2,284`
- Unique semantic pairs: `590`
- Output rows:
  - joint rule summaries: `14`
  - conflict rows: `48`
- Focused tests:
  `C:\Python\Python311\python.exe -m pytest tests/tools/test_phaseB_n3c_strict_320_anchor_lens_quickcheck_v1.py tests/tools/test_phaseB_n3c_strict_320_anchor_joint_rule_sweep_v1.py -q`
  -> `8 passed`
- Rule summary highlights:
  - `hd0_len10_m10`: `401` covered, `62` break, break rate `0.154613`
  - `hd0_len10_m20`: `251` covered, `24` break, break rate `0.095618`
  - `hd0_len10_m30`: `162` covered, `1` break, break rate `0.006173`
  - `hd0_len10_m50`: `87` covered, `0` break, break rate `0.000000`
  - `hd0_len10_m20__hd_le1_len12_agree_required`: `147` covered,
    `1` break, break rate `0.006803`
- Conflict readout: secondary conflicts were sparse and did not identify the
  main break-risk region in this pass. The stronger signal is primary
  `hd0_len10` margin, with `hd_le1_len12` agreement useful as a narrower
  confirmation lens.
- This remains conditional break-risk telemetry only, not calibrated
  correctness probability and not production scoring/ranking authority.

## 2026-06-06 - S3 strict full80 completed, consolidated, compared, and packed

- Visible serial S3 strict runner completed all five buckets and reached
  `finished_utc`.
- Strict consolidated output:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_full80_corrected_consolidated_evidence_v1/`
- Strict scope:
  - chunks: `815`
  - logical groups: `702`
  - phrase rows: `365,516,232`
  - verified hits: `1,546,511`
  - global candidate clusters: `308`
  - exact-containing global candidate clusters: `249`
  - summed bucket runtime: `8,902.7s`
- Matched strict-vs-normal comparison:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_vs_normal_full80_comparison_v1/`
- Comparison headline:
  - strict retained `59.6%` of normal phrase rows
  - strict retained `92.7%` of normal verified hits
  - strict used `60.8%` of the normal summed bucket runtime
  - normal -> strict global clusters: `275` -> `308`
  - normal -> strict exact-containing clusters: `225` -> `249`
- Built main review pack:
  `planning/projects/no_wli/40_review_summaries/phaseB_failed_decryption_n3c_strict_vs_normal_full80_review_pack_2026-06-06.zip`
- Pack facts:
  - entries: `114`
  - size: `511,716` bytes
  - fresh extracted portable tests: `11 passed`
- Stop at main external review. Still not approved: all-`734` expansion,
  score-bearing use, production scoring/ranking changes, raw-hit authority, or
  simple-cluster authority.

## 2026-06-06 - Overnight strict extension batches 1-3 launched

- Based on the completed strict selected-80 runtime, planned three additional
  80-candidate strict batches from the remaining fixture candidates.
- Candidate canary:
  - extra candidates: `240`
  - unique extra candidates: `240`
  - overlap with original selected 80: `0`
- Runtime estimate:
  - reference strict selected-80 summed runtime: `8,902.7s`
  - planned batches: `3`
  - estimated total: `26,708.1s`
  - intended overnight budget: `36,000s`
- Visible launcher:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/launch_phaseB_failed_decryption_n3c_strict_full80_remaining_batches_1_3_visible_v1.ps1`
- Serial runner:
  `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_remaining_batches_1_3_serial_v1.py`
- Log:
  `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_full80_remaining_batches_1_3_serial_v1/strict_full80_remaining_batches_1_3_2026-06-06.log`
- Five-minute monitor status:
  - running batch: `remaining_batch_01`
  - running bucket: `8-9`
  - progress: `9/41` chunks
  - hits so far: `448,681`
  - peak memory so far: `361.1 MB`
  - no crash or traceback observed
- Stop condition remains first nonzero bucket exit or wallclock budget reached.
- Still not approved: all-`734` expansion, score-bearing use, production
  scoring/ranking changes.
