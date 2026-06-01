# No-WLI Next-Phase Implementation Plan

Date: 2026-03-27

Purpose:
- convert the locked review position into a concrete next-stage implementation plan
- keep the next work solve-first and evidence-driven
- define the smallest code surfaces, canaries, short-run readouts, and stop/go gates

Scope:
- no runtime code changes in this document
- this is a plan for the next stage after the current Study 1 boundary fix and canary

Sources used for this plan:
- `planning/working/March27_2026_review v2.txt`
- `planning/working/no_wli_science_run_log_2026-03-26.md`
- `planning/working/no_wli_solve_integrity_plan_2026-03-21.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_seeding.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_topk.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/audit_basin_family_diversity_alignment.py`

## 1. Locked Working Position

The current working version stays:

1. Study 1: constant local-depth Stage-3 entry
2. Study 3: Phase-C start balancing
3. Study 2: family-aware Phase-B preservation

Why this order remains correct:
- Study 1 has the strongest direct evidence for `211`-like upstream reach failure.
- Study 3 has the cleanest explicit downstream bias in current code and the best live support from `411`-like runs.
- Study 2 still matters, but it is more policy-heavy because it needs a family definition.

Important nuance:
- the live `seed411` compare supports a broader exploited-variety bottleneck
- it does not isolate Phase-C start ordering alone as the sole marginal cause
- the next phase should therefore isolate Phase-C start selection itself before widening further

## 2. Current Code-State Summary

### Study 1 status

Study 1 entry policy now exists as a clean explicit surface:
- runtime state:
  - `STAGE3_ENTRY_ALLOCATION_POLICY`
  - `STAGE3_ENTRY_MUTATIONS_PER_PROMOTED`
- config outputs:
  - `stage3.entry`
  - `stage3_search.entry`
- Stage-3 prep output:
  - `stage3_entry_allocation_policy`
  - `stage3_entry_target_before_cap`
  - `stage3_entry_mutation_calls_per_promoted`

This is now backed by the short canary:
- `tests/tools/test_no_wli_stage3_entry_canary.py`

Short proof status:
- focused slice:
  - `83 passed`
- evidence:
  - `planning/working/no_wli_science_run_log_2026-03-26.md`

Operational meaning:
- the next user-run long compare is scientifically worth reading again
- the failed v37 runs should remain classified as invalid boundary failures

### Phase-C start-selection status

The current Phase-C candidate pool and start selection are still source-ordered in:
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`

Current behavior, from code:
- candidate pool assembly order:
  - `stage3_best`
  - `phaseB_topk`
  - `phaseA_selected`
- actual starts are consumed in that same source order until `stage3_phasec_start_keys` fills

Relevant current telemetry already exists:
- `phaseC_candidate_pool_count`
- `phaseC_candidate_pool_unique_keys`
- `phaseC_candidate_pool_unique_end_hash`
- `phaseC_candidate_pool_source_counts`
- `phaseC_start_keys_used`
- `phaseC_start_source_counts`
- `phaseC_start_unique_end_hash`

This is the smallest practical rewrite surface for Study 3.

### Phase-B preservation status

Current Phase-B narrowing still happens mainly in:
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`

Current behavior, from code:
- rows ranked pct-first through `_phaseb_rank_key(...)`
- exact dedupe by `(start_hash, end_hash)`
- top-n / tie-band widening still around the same `end_score_pct` surface

This remains important, but it is a broader policy intervention than Study 3.

## 3. Next-Phase Goals

The next phase should produce three things:

1. a clean scientific readout of Study 1 on `211`
2. a narrowly isolated Study 3 implementation for `411`-like downstream exploitation failure
3. short-run evidence that distinguishes:
   - carried variety
   - explored variety
   - final solve improvement

Non-goals for the next phase:
- no Stage-3.5-led push
- no broad scorer unification
- no family-preservation rewrite yet
- no broad refactor of Stage-3 internals beyond the exact surfaces needed for Study 3

## 4. Implementation Sequence

### Phase A. Close Study 1 Readout

Objective:
- decide whether constant local-depth entry improved upstream reach on `211`

Required evidence:
- run config / lock payload show:
  - `entry_allocation_policy = constant_local_depth`
  - intended cap applied
- output artifacts show:
  - `stage3_entry_target_before_cap`
  - `init3_n`
  - `stage2_to_stage3.stage3_init3_count`
- final result comparison:
  - `stage3_match_ratio`
  - `best_match_ratio`
  - `best_stage`

Decision rule:
- if Study 1 does not widen actual Stage-3 entry, treat the run as execution failure
- if it widens entry but solve does not move, treat it as a valid negative result
- if it widens entry and improves `211`, keep it as a retained candidate branch for future higher-period work

Outputs to update:
- `planning/working/no_wli_science_run_log_2026-03-26.md`
- `planning/working/no_wli_solve_integrity_plan_2026-03-21.md`
- `planning/working/no_wli_study1_readout_checklist_2026-03-27.md`

### Phase B. Implement Study 3

Objective:
- isolate whether Phase-C start allocation is bottlenecking downstream exploitation on `411`

Implementation target:
- change only how `start_records` are chosen from an already-built candidate pool
- do not change:
  - Phase-A generation
  - Phase-B ranking
  - candidate-pool construction
  - rescue logic

Primary code surface:
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`

Supporting config surfaces:
- `tools/benchmarks/periodic_sub_trans/no_wli/runtime_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_lock_payload.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

Recommended minimal policy shape:
- keep legacy default:
  - `source_order`
- add one explicit candidate policy:
  - `balanced_sources_v1`

Recommended `balanced_sources_v1` behavior:
1. reserve anchor best row first if present
2. build source buckets exactly as now
3. consume challenger starts by round-robin across:
   - `phaseB_topk`
   - `phaseA_selected`
4. preserve uniqueness by exact key as today
5. stop at the same `stage3_phasec_start_keys`

Reason for this choice:
- smallest isolating change
- directly tests exploited-variety squeeze
- avoids premature commitment to a family definition
- preserves current candidate pool and rescue surfaces for comparability

Explicitly avoid in Study 3 v1:
- family clustering
- additional score mixing
- source-specific quota tuning beyond anchor-first plus round-robin
- changing `phaseC_start_keys`
- changing rescue thresholds

### Phase C. Evaluate Study 3 with Short Live Compare

Target seed:
- `411`

Recommended two-job compare:
1. control:
   - current preserved control
2. candidate:
   - same preserved control plus `phasec_start_policy = balanced_sources_v1`

Interpretation rule:
- do not mix this with wider rescue or broader Phase-B carry-forward at first
- first Study 3 run must isolate start selection

Primary readouts:
- `phaseC_candidate_pool_source_counts`
- `phaseC_start_source_counts`
- `phaseC_start_keys_used`
- `phaseC_start_unique_end_hash`
- `best_match_ratio`
- `stage3_match_ratio`
- `phaseC_final_winner_source`

Success patterns:
- more balanced `phaseC_start_source_counts`
- equal or higher `phaseC_start_unique_end_hash`
- improved `best_match_ratio` or `stage3_match_ratio`

Valid negative pattern:
- starts rebalance as intended, but solve does not improve
- this still falsifies Phase-C start order as the main lever

### Phase D. Reassess Study 2

Only begin after:
- Study 1 readout is closed
- Study 3 isolated run is complete

Why delay:
- Study 2 needs a family definition
- current audit tooling offers options, but the implementation surface is larger
- Phase-C balancing is cheaper to isolate first

Likely design direction when reached:
- reserve some Phase-B / downstream slots by family view
- family definition should be chosen from already reviewed audit views, not invented ad hoc

Preferred starting family view candidates:
- `prefix_hamming_le_24`
- `near_tail_h1`

Reference file:
- `tools/benchmarks/periodic_sub_trans/no_wli/audit_basin_family_diversity_alignment.py`

## 5. Required Canaries and Test Discipline

The next phase must keep the current rule:
- no long handoff until a short proof exists for the changed boundary

### Study 3 canary requirements

Add one dedicated canary that proves:
- preset resolution carries the new Phase-C start policy cleanly
- run config writes the policy explicitly
- non-scoring lock writes the policy explicitly
- the Phase-C candidate pool stays unchanged under the new policy
- only `start_records` differ

Also add one deterministic unit test on synthetic candidate buckets:
- same pool
- same start budget
- legacy `source_order` produces current order
- `balanced_sources_v1` produces anchor-first then source-balanced order

Meaningful short slice before live test:
- config / preset / lock payload tests
- Phase-C deterministic start-selection tests
- one smoke test through the two-phase function if possible without expensive runtime

### Guardrails

Do not accept a Study 3 implementation if:
- it silently changes candidate-pool composition
- it silently changes rescue eligibility
- it silently changes score ranking or tie-band logic
- the new policy is not visible in config and lock outputs

## 6. Logging Requirements

Each implementation step should append evidence-backed notes to:
- `planning/working/no_wli_science_run_log_2026-03-26.md`
- `planning/working/no_wli_solve_integrity_plan_2026-03-21.md`

Minimum evidence per claim:
- code path
- test command
- test result
- artifact path for live evidence

Claims to avoid:
- “probably better”
- “seems wider”
- “looks fixed”

Claims to prefer:
- config surface changed at these files
- canary proves this exact boundary
- live output shows these counters changed
- solve improved or did not improve

## 7. Immediate Working Plan

Immediate next steps from this document:

1. wait for or read the corrected Study 1 long rerun
2. close the Study 1 checklist
3. if boundary is clean, implement Study 3 as `phasec_start_policy = balanced_sources_v1`
4. add Study 3 canary and deterministic tests
5. run only short confirmation tests locally
6. hand off the next isolated `411` long compare to the user

## 8. Bottom Line

The next phase should stay narrow.

Best next implementation order:
1. close Study 1 readout on `211`
2. implement isolated Phase-C start balancing on `411`
3. only then consider family-aware Phase-B preservation

That keeps the work aligned with the locked review, minimizes silent drift, and
ensures each long run answers a specific question rather than bundling multiple
late-stage changes together.

## 9. Status Update: Study 3 Implemented

Study 3 is now implemented.

What is complete:

- explicit Phase-C start policy surface:
  - `source_order`
  - `balanced_sources_v1`
- isolated runtime change in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- config / lock / resume / runtime-call plumbing
- dedicated Study 3 canary
- deterministic Phase-C ordering test
- prepared `seed411` 2-job live compare

What remains:

- user long-run readout only

Active live compare prepared:

- control:
  - `stage3_preserve_tieband_probe_p9`
- candidate:
  - `stage3_phasec_start_balanced_p9`
- seed:
  - `411`

Decision after implementation:

- Study 2 should remain deferred until the Study 3 live readout is complete
- if Study 3 is negative despite confirmed start rebalancing, that will further
  strengthen the case for moving next toward Phase-B preservation or more
  upstream basin-generation work rather than more Phase-C policy tuning

## 10. Status Update: Study 3 Readout Complete

Study 3 is now closed as a valid negative on `seed411`.

What the run showed:

- the new `balanced_sources_v1` policy executed correctly
- the Phase-C candidate pool stayed unchanged, as intended
- the actual Phase-C starts also stayed unchanged
- the solve result stayed unchanged

Most important evidence:

- control run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T174120032623Z__bench_solve_pipeline_no_wli__55b7159`
- candidate run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T211041031812Z__bench_solve_pipeline_no_wli__55b7159`
- identical effective Phase-C start usage:
  - `phaseC_start_source_counts = { "stage3_best_phaseB": 1, "phaseA_selected": 5 }`
  - same six `candidate_hash` values in `phasec_start_checkpoints.jsonl`

Interpretation:

- the implemented Phase-C start rebalancing policy was too late to help on
  this seed / current pool shape
- by Phase-C start time, there is no additional distinct `phaseB_topk` start
  to exploit

Next implementation target:

- Study 2:
  - family-aware Phase-B preservation / downstream slot retention
- concrete brief:
  - `planning/working/no_wli_study2_phaseb_preservation_plan_2026-03-28.md`

Practical consequence:

- do not schedule another Phase-C-only long compare
- the next meaningful long run should happen only after a Study 2
  implementation exists

## 11. Status Update: Study 2 Implemented

Study 2 is now implemented and locally proven.

Locked implementation shape:

- downstream carry-forward preservation only
- no Phase-B ranking rewrite
- no new rescue behavior
- no new Phase-C balancing changes bundled into the same compare

Chosen v1 policy:

- `phaseb_family_preservation_policy = reserve_by_family_v1`
- `phaseb_family_view_id = prefix_hamming_le_24`
- `phaseb_family_reserved_slots = 2`

Proof state:

- deterministic Study 2 policy test exists and passes
- dedicated preset/config/lock/runtime/resume canary exists and passes
- fixture runtime materialization for the active compare exists and passes

Evidence:

- focused proof:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `30 passed`
- broader confirmation:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py -q`
  - `95 passed`

Active handoff compare:

- seed:
  - `411`
- control:
  - `stage3_preserve_tieband_probe_p9`
- candidate:
  - `stage3_phaseb_family_preserve_p9`

Decision:

- the next meaningful long run is now the Study 2 `seed411` compare
- no additional implementation is required before handing that run to the user

## 12. Status Update: Study 2 First Live Readout Was Not Fully Auditable

The first v39 Study 2 compare completed, but it did not close the science
question yet.

What is already known from the live run:

- the intended config delta was present
- visible solve outcome did not improve
- visible Phase-C pool and start counters did not move

What prevented a locked conclusion:

- the new Study 2 family-preservation telemetry was not persisted into the
  saved artifact path used for review

So the next implementation step is narrower than a new science phase:

1. persist Study 2 family telemetry into saved artifacts
2. rerun the same v39 `seed411` compare
3. only then decide whether Study 2 is a valid negative or whether the saved
   telemetry reveals a more subtle downstream collapse

## 13. Post-v42 Review Update: Next Science Targets Have Split Further

The later pack cross-check sharpened the next-science reading again.

The main point is not merely that Studies 1, 2, and 3 were negative.
It is that they were negative at different compression points.

Current best split:

- `211`:
  - upstream reach / wrong-neighborhood problem
- `411`:
  - carried-to-exploited variety conversion problem

What this means for future science work:

### `211`

Do not repeat another simple entry-depth study.

The next useful study should move earlier, for example:

- Stage-2 to Stage-3 promoted-family generation
- promotion diversity / homogeneity logic
- or a more structural basin-generation intervention

Reason:

- Study 1 already showed that materially wider Stage-3 entry did not move the
  outcome, so the marginal lever is probably upstream of that point

### `411`

Do not repeat generic Phase-C balancing or generic width-only probes.

The next useful study should target:

- novel-start carry-through from the widened late pool

Best current formulation:

- keep the widened downstream pool
- guarantee at least one or two genuinely distinct non-anchor challengers from
  that widened pool become actual explored starts
- define distinctness against the anchor and already-selected starts, not only
  by broad source label

Reason:

- Study 3 showed that Phase-C source balancing alone had nothing new to work
  with
- v42 showed that late width alone created much more carried variety but still
  did not create a new explored challenger

Operational consequence:

- the next science phase should now split explicitly by seed type instead of
  assuming one shared weak-seed bottleneck

## 14. General Robustness Objective

The next planning step should stay tied to the real programme goal:

- derive a more general robust way to solve, not just a local fix for one
  benchmark seed

What the current seed studies are now good for:

- they expose different failure classes
- they show which compression points matter on which seeds
- they help define what "promising seed properties" or "promising basin
  properties" should mean in a more general solver

Best current generalization lens:

- good seeds are not just "lucky"
- they are cases where the pipeline:
  - recognizes a promising basin family early enough
  - preserves it strongly enough
  - and actually exploits it through a real explored path

So the next science phases should increasingly ask:

1. what seed or basin properties predict that a run will develop into a good
   downstream candidate?
2. how can those properties be recognized earlier and more reliably?
3. how can the solver preserve and exploit those properties without collapsing
   them away too early?

Immediate consequence for study design:

- `211` studies should now be used to learn about upstream basin reach and the
  properties of promoted families that later fail to mature
- `411` studies should now be used to learn about downstream conversion:
  - which widened-pool challengers are genuinely novel
  - which ones are startable
  - and which properties separate challengers that can become real winners from
    those that remain nominal diversity only

This keeps the seed-specific work aligned with the higher goal of a solver that
is more robust in general, not just over-tuned to one local case.

## 15. Active Next Implementation Plan: `411` Novel-Start Carry-Through

The next `411` implementation target is now locked as:

- `novel_challenger_v1`

Purpose:

- given a widened late pool, test whether one or two eligible novel
  non-anchor challengers can be forced into the actual explored Phase-C start
  set

Why this is next:

- Study 3 showed generic Phase-C balancing alone was too weak
- Study 2 showed family reservation inside the current narrow top band was too
  weak
- `v42` showed widened late width increased carried variety strongly but did
  not increase exploited starts at all

The formal implementation plan is:

- `planning/working/no_wli_study411_novel_start_carrythrough_plan_2026-03-30.md`

Non-drift rule:

- do not bundle this study with any new Phase-B ranking, tie-band, rescue, or
  Stage-3.5 changes

### 2026-03-30 Study 411 novel-start carry-through implemented

Status:

- implemented and short-proofed
- no long run started from this step

What changed:

- `novel_challenger_v1` added as a Phase-C start-selection policy
- novelty rule reuses:
  - distinct `end_hash`
  - `prefix_hamming_le_24`
- explicit study telemetry now persists through `stage3_diagnostics`

What did not change:

- Phase-B ranking
- candidate-pool construction
- rescue semantics
- Stage-3.5

Proof status:

- deterministic policy / persistence slice:
  - `17 passed`
- config/runtime/canary slice:
  - `36 passed`
- broader guard slice:
  - `97 passed`

Prepared next live compare:

- control:
  - `stage3_phaseb_width_probe_p9`
- candidate:
  - `stage3_phasec_novel_challenger_p9`
- experiment id:
  - `tune_v43_p9c3_seed411_novel_start_compare_2job`

### 2026-03-30 implementation follow-up: first novel-start live compare invalidated

The first live compare for the `411` novel-start study did not yield a science
result.

Why:

- both jobs failed with:
  - `KeyError: 'STAGE3_PHASEC_START_POLICY'`
- the saved run-configs were already correct, so the failure was in the live
  Stage-3 bridge, not in the compare definition

Root cause:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_iteration_bridge.py`
  narrowed the Stage-3 iteration state too aggressively
- it was not forwarding:
  - `STAGE3_PHASEC_START_POLICY`

Fix:

- explicit forwarding added in the stage-engine bridge
- regression proof strengthened in:
  - `tests/tools/test_no_wli_stage_engine_iteration_bridge.py`

Decision:

- keep the same control/candidate compare
- refresh control-file identity only
- rerun the same novel-start study once the bridge fix is proven

### 2026-03-30 implementation correction: fixture-matrix live path needed matrix-config fix too

The fresh `v44` rerun showed that the first bridge fix was insufficient for
the actual fixture-matrix live path.

Corrected finding:

- the matrix runtime still constructs a typed `IterationMatrixConfig`
- that config did not include `stage3_phasec_start_policy`
- so `iteration_matrix_flow.py` was still building live Stage-3 state without
  the policy, even though run config and the lower bridge were fixed

Now fixed:

- `IterationMatrixConfig` includes `stage3_phasec_start_policy`
- `iteration_matrix_builder.py` populates it from live state
- `iteration_matrix_flow.py` forwards it into live Stage-3 state
- shared contract extracted in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_state_contract.py`

Meaning:

- the same `411` novel-start compare remains the correct next science run
- but it needed one more matrix-path hardening slice before it became
  trustworthy again

### 2026-03-31 Study 411 result update: valid negative with stronger downstream signal

`v45` finished cleanly and closes the first `411` novel-start carry-through
study as a valid negative.

Interpretation:

- the widened late pool still contained many eligible novel challengers
- the policy successfully reserved two challengers
- but those rows were already part of the widened-late baseline start set
- so the policy changed labels, not the actual explored set

Updated downstream lesson:

- the `411` bottleneck is now even narrower than “generic novel-start carry-through”
- the next `411`-track intervention should require at least one or two novel
  challengers that are not already selected by widened-late legacy order

Important adequacy blocker now visible:

- Phase-C can explore a challenger with much higher truth-match than the
  score-selected winner
- but current top-level run summaries still surface only the score-selected
  winning path
- this is not a pipeline correctness failure, but it is a scientific-visibility
  limitation that should be addressed in the hardening track

### Late-stage scorer prep update

The next scorer-oriented work should now assume two preparatory pieces are in
place:

- benchmark disagreement reporting is implemented
- replay-fixture export scaffolding for explored late-stage frontiers is
  implemented

Reference plan:

- `planning/working/no_wli_late_stage_scorer_data_prep_plan_2026-03-31.md`

What is ready now:

- `v45` can already be exported as a frozen late-stage frontier telemetry
  bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v45_seed411_late_frontier.json`
- the benchmark disagreement dataset now isolates real undervalued-challenger
  cases:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json`

What is not ready yet:

- the historical `v45` frontier is not replay-material complete because it
  predates the new captured:
  - `init_key_idx`
  - `init_plaintext_idx`
  - `final_key_idx`
  - `final_plaintext_idx`

Immediate implication:

- the next late-stage scorer experiment spec can now be written against real
  benchmark disagreement data
- but one post-hardening comparable run is still needed before a scorer test
  can replay trial keys / plaintexts directly from a frozen frontier fixture

### Stage A benchmark scaffold is now in place

Reference:

- `planning/working/no_wli_late_stage_selector_stageA_plan_2026-03-31.md`

Completed now:

- frozen `v45` regression fixture in `tests/fixtures`
- benchmark-only frontier feature-table builder
- truth-gap dataset summary helper
- legacy selector reproduction helper
- first weighted benchmark-only reranker prototype

Boundary remains explicit:

- no live selector/scorer behavior changed
- no replay-stage key testing added yet
- this is a benchmark harness for scorer design, not a pipeline intervention

Next use:

- inspect recurring disagreement structure from the truth-gap dataset
- refine feature choices while waiting for one fresh replayable frontier run

### Current late-stage selector execution split

Stage A now has:

- frozen `v45` fixture
- weighted benchmark-only reranker
- pairwise benchmark-only reranker
- exported Stage A summary/report artifacts

Reference outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/summary.md`

Stage B now has a completed replay-capture run plus a queued direct replay step:

- `planning/working/no_wli_stageb_replay_capture_run_plan_2026-03-31.md`
- `planning/working/no_wli_stageb_first_comparison_note_2026-03-31.md`

Current practical order:

1. treat Stage A ranking work as frozen enough for the first replay step
2. use the exported replay-ready `v46` frontiers
3. use the saved selected-trial material rows for the first direct replay /
   continuation comparison
4. only after that decide whether another scorer ranking pass is warranted

Decision gate reference:

- `planning/working/no_wli_stagea_decision_checklist_2026-03-31.md`

Current Stage A stop/go reading:

- must-pass `v45` rescue is satisfied
- score-only weighting is not sufficient
- current rescue appears to be driven by structural / novelty signals
- the same structural / novelty rescue story now recurs across the dominant
  repeated disagreement pattern family in the current audited rows:
  - dominant repeated pattern count `10`
  - weighted rescued count `10`
  - pairwise rescued count `10`
- the new rescued-vs-unrecovered contrast sharpens the current Stage A limit:
  - `9002...` can be rescued because it is near enough on score and clearly
    novel
  - `e45...` is still not rescued because it is further behind on score and has
    no novelty support in the current feature set
- the new small ablation sweep now says:
  - score-only rescues `0 / 14`
  - score+novelty rescues `13 / 14`
  - score+lexical rescues `0 / 14`
  - score+novelty+lexical remains `13 / 14`
  - therefore novelty/structure is the active current lever and lexical fields
    are not yet helping on the frozen frontiers
- the new one-at-a-time numeric-field sweep now says:
  - `+ score_gap_to_winner` stays `13 / 14`
  - `+ score_gap_to_anchor` stays `13 / 14`
  - `+ init_score` stays `13 / 14`
  - `+ init_search_score` stays `13 / 14`
  - therefore the tested present-but-unused numeric live fields do not add lift
    beyond the current `score+novelty` baseline
- the one last safe source-only categorical pass now says:
  - `+ phaseB_topk` source penalty improves to `14 / 14`
  - but it rescues the last pattern only to a modestly better challenger
    (`7391...`), not to the oracle-best `e45...`
- the robustness sweep now says:
  - the dominant repeated `9002...` family is rescued in all `81` tested
    perturbation configs
  - the unrecovered `e45...` class is rescued in `0 / 81`
- broader evidence is still marked `thin`

`v46` result and Stage B export now update that direction:

- replay-ready `v46` frontier export is complete
- frozen `score+novelty` already selects the oracle-best explored challenger
  `9002...` on both replay-ready runs
- optional source-penalty variant adds no extra lift on this frontier because
  it selects the same challenger

So the immediate practical direction is now:

- do not add more Stage A ranking complexity yet
- keep `score+novelty` as the locked baseline for the replay step
- carry the source-penalty variant only as an optional comparison candidate
- move to the first direct replay / continuation comparison using:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/selected_trial_material_rows.json`

### Stage B status after first direct continuation comparison

Reference:

- `planning/working/no_wli_stageb_first_continuation_note_2026-03-31.md`

Current maintained reading:

- the first replay-ready continuation comparison is now complete
- `score + novelty` is no longer only a ranking improvement
- on both replay-ready `v46` frontiers it:
  - selects `9002ee09917e5a0d`
  - is accepted by the real Stage 3.5 continuation path
  - continues to `d9430723f54e973e`
  - reaches truth `0.496`
- the legacy selector:
  - stays on `73eee2bf84b7c07f`
  - fails the Stage 3.5 search-score-drop guard
  - does not produce a better downstream path

Practical consequence:

- the late-stage selector/reranker direction now has one real replay-validated
  positive case
- the next scorer experiment spec should build from this state, not restart from
  frozen-ranking-only assumptions
- keep the source-penalty variant optional only, because on this replay-ready
  case it adds no lift beyond the locked `score + novelty` baseline

### 2026-03-31 implementation split updated after the first replay-ready continuation win

The next live implementation step is now narrowed to a Stage 3.5 baseline-row
selector compare.

Implementation boundary:

- add a shared live-safe selector core for:
  - `legacy`
  - `score_plus_novelty`
- thread one explicit config field:
  - `STAGE35_BASELINE_SELECTOR`
- keep the intervention limited to:
  - selecting which already-explored Phase-C row is handed to Stage 3.5

Do not broaden this into:

- a live late-selector rewrite
- a new feature-family experiment
- a new upstream search experiment

Immediate run order:

1. short canary pair:
   - `legacy`
   - `score_plus_novelty`
2. inspect persisted baseline-selection and Stage 3.5 admission fields
3. if clean, switch to the overnight 2-job compare with the same pair

Reference:

- `planning/working/no_wli_stage35_baseline_selector_live_compare_plan_2026-03-31.md`

Current implementation state:

- the shared live-safe selector core is implemented
- runtime/config/lock plumbing for `STAGE35_BASELINE_SELECTOR` is implemented
- diagnostics persistence for the Stage 3.5 baseline row is implemented
- the active fixture-matrix config is now the short canary pair
- the overnight pair is already defined and only requires flipping the config
  mode constant after a clean canary

Proof:

- focused guard slice:
  - `83 passed`

### 2026-04-01 implementation correction: make the canary a real canary

The first live Stage 3.5 baseline-selector canary exposed a planning mistake as
well as a missing observability boundary.

Observed problem:

- the run reached Phase C, printed the final Phase-C summary, then went silent
  for hours
- the canary preset was still too close to a real long run
- Stage 3.5 had no progress logging, so “slow” and “wedged” looked identical

Implementation correction now applied:

- Stage 3.5 progress logging added in the live path
- canary-only Stage 3.5 cfg reduced to:
  - `seed_keep=2`
  - `beam_width=2`
  - `archive_keep=6`
  - `rounds=1`
  - `mini_search_steps=1`
  - `mini_search_beam_width=2`
  - `mini_search_top_symbols=6`
  - `mini_search_final_keep=1`
  - `mini_search_keep_all_rows=0`
- canary-only late search budgets reduced
- fresh canary experiment id:
  - `tune_v49_p9c3_seed411_stage35_baseline_selector_canary_reduced_2job`

Current execution rule:

- rerun `v49` first
- only if `v49` shows:
  - selector mode switching
  - persisted Stage 3.5 baseline fields
  - visible Stage 3.5 heartbeat
  - clean job completion
  then return to the overnight `v48` compare

Operational note:

- because user time is intermittent, the `v49 -> v48` promotion is now wired
  through a detached watcher rather than manual handoff
- the watcher uses the canary state/events files as the source of truth and will
  not launch the overnight run on a failed canary

### 2026-04-02 next live execution narrowed to one missing candidate lane

Because `v48` stopped after the completed legacy lane, the next live run should
not repeat the same 2-job compare shape.

Active next run shape:

- one fresh full-budget 1-job run
- preset:
  - `stage35_baseline_score_plus_novelty_live_p9`
- compare target:
  - the already-completed `v48` legacy long lane

Morning readout contract:

1. did the baseline row differ?
2. did Stage 3.5 admission change?
3. did downstream continuation beat the locked legacy long lane?

### 2026-04-02 follow-up: Stage 3.5 speed-first workstream is now justified

The current `v50` candidate lane already answered the first readout question:

- yes, the baseline row differs in the full live job

What it exposed instead is a new immediate blocker:

- Stage 3.5 runtime on the stronger candidate path is far more expensive than
  on the completed legacy lane

That means the next implementation focus should move as late as possible:

- Stage 3.5 speed and observability first
- Stage 3.5 solve-quality comparison second

Preferred next iteration mode:

- artifact/replay-driven Stage 3.5 resume work
- not full end-to-end long runs by default
