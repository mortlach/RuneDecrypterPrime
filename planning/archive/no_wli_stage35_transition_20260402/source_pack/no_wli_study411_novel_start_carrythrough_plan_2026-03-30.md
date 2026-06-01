# `411` Novel-Start Carry-Through Implementation Plan

Date:
- 2026-03-30

Purpose:
- define the next `411`-track science implementation cleanly after the locked
  negatives from Studies 2 and 3 and the valid `v42` width result
- keep the intervention narrow enough to be interpretable
- prevent drift by fixing the hypothesis, boundary, control, logging standard,
  and proof steps before implementation begins

This document is meant to be the implementation-side companion to the broader
strategy notes in:
- `planning/working/no_wli_next_phase_implementation_plan_2026-03-27.md`
- `planning/working/no_wli_locked_experiment_specs_2026-03-28.md`
- `planning/working/no_wli_science_run_log_2026-03-26.md`

## 1. Locked Baseline

Current maintained downstream reading for `411`:

- generic Phase-C source balancing was a valid negative
- family reservation inside the current narrow top band was a valid negative
- widening the late Phase-B carry-forward band was also a valid negative on
  final solve outcome
- but the widened late-pool study showed a strong structural signal:
  - carried variety increased a lot
  - exploited starts did not increase at all

Best current wording:

- `411` is mainly a carried-to-exploited variety conversion problem

That means the next `411` study should not ask:

- "should we carry more?"
- "should we balance sources more?"

It should ask:

- given a widened late pool, can we carry through one or two *eligible novel
  challengers* into the actual explored Phase-C starts?

## 2. Core Hypothesis

The marginal bottleneck on `411` is not generic late width and not generic
Phase-C balancing by themselves.

The stronger hypothesis is:

- the widened late pool may already contain a more promising or at least
  meaningfully different challenger
- but the current start-fill logic still fails to convert that challenger into
  a real explored Phase-C start

So the study hypothesis is:

> For `411`-like cases, forcing one or two eligible novel non-anchor
> challengers from the widened late pool into the actual explored Phase-C
> starts will change the explored downstream path in a way that generic
> balancing did not.

## 3. What This Study Must Distinguish

The study is not trying to prove in advance that a good challenger already
exists.

It is trying to separate these cases:

1. no genuinely novel promising challenger exists in the widened pool
2. one exists, but current start selection fails to carry it through
3. one becomes a start, but it still is not actually better

This is the main scientific value of the study.

## 4. Intervention Boundary

The boundary must stay narrow.

Keep fixed:

- seed
- overall eval budget
- Stage-3 search scorer
- Phase-A and Phase-B search behavior
- late width settings
- rescue settings
- Stage-3.5 settings
- Phase-B ranking order
- Phase-B tie-band widening
- candidate-pool construction

Change only:

- the policy that maps the already-built widened late candidate pool into the
  actual Phase-C starts

This must remain a start-selection study, not a mixed late-stage intervention.

## 5. Control And Candidate

The control must be the widened-late baseline, not the narrow control.

Control:

- widened late pool
- legacy Phase-C start policy

Candidate:

- same widened late pool
- only start policy changed to:
  - `novel_challenger_v1`

Why:

- the whole purpose is to test whether the widened late pool already contains
  something useful that the current start selection is failing to explore

## 6. Candidate Policy Concept

Proposed new Phase-C start policy:

- `novel_challenger_v1`

Minimal behavior:

1. keep the anchor / best row exactly as today
2. search the widened late pool for one or two eligible challengers that are:
   - not the anchor
   - distinct from the anchor
   - distinct from each other
3. reserve start slots for those challengers
4. fill remaining slots by legacy order

This is deliberately narrower than a general Phase-C policy framework.

## 7. Novelty Rule For v1

Do not invent a new custom distance notion for the first pass.

Reuse existing family-view machinery already present in:

- `tools/benchmarks/periodic_sub_trans/no_wli/family_views.py`

Novelty should be defined by:

- distinct `end_hash` from the anchor
- plus `prefix_hamming_le_24` relative to:
  - the anchor
  - and any already selected challenger

Why:

- this keeps the study aligned with current repo vocabulary
- it avoids policy sprawl
- it gives a fixed structural rule that is already used in the surrounding
  analysis language

## 8. Candidate Pool Source

The challenger-selection source must be explicitly documented as:

- the widened late pool already built under the widened-baseline configuration

Do not narrow back down to the top-8 band for this study.

Otherwise the study would stop testing the main post-`v42` question.

## 9. Likely Code Surface

Primary target:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`

Current helpful fact:

- the file already has an explicit Phase-C start-policy hook
- current implemented policies are:
  - `source_order`
  - `balanced_sources_v1`

Expected implementation shape:

- keep current policy logic intact
- add one new policy branch:
  - `novel_challenger_v1`
- extract only minimal helper logic if it materially improves clarity

Avoid:

- broad policy-framework expansion unless the local code structure truly
  requires it

## 10. Required Instrumentation

This study will not be acceptable if the result is only operationally negative
but scientifically ambiguous.

Persist at least the following.

### Candidate-pool level

- candidate-pool row count
- candidate-pool unique end-hash count
- candidate-pool source counts
- candidate-pool eligible novel challenger count relative to the anchor
- candidate-pool eligible-but-not-selected challenger count

### Selected-start level

- actual start count
- actual start unique end-hash count
- actual start source counts
- which starts were selected under the novel-challenger rule
- anchor row id / candidate hash
- chosen challenger row ids / candidate hashes
- novelty distances for the chosen challengers

### Truth-linked where available

- best truth in candidate pool
- best truth among actual starts
- whether the selected novel challengers had better truth than the anchor
- whether the final winner came from anchor or challenger path

## 11. Primary Readouts

Judge the study on three levels.

### Level 1: operational

- did the policy actually select different starts?

### Level 2: structural

- did the actual explored start set become more novel than baseline?
- were there eligible novel challengers in the pool?
- were eligible challengers selected?

### Level 3: solve effect

- did downstream behavior change?
- did the checkpoint path change?
- did final winner source change?
- did Stage-3 or final match improve?

The study should not be judged on final match alone.

## 12. Success Criteria

Strong success:

- the start set genuinely changes
- at least one chosen challenger is structurally distinct from the anchor
- downstream checkpoints or winner path change materially
- final result improves

Useful partial success:

- the start set genuinely changes
- the challenger path is clearly explored
- final match does not improve

That still teaches us the bottleneck is later than start carry-through.

## 13. Falsification Criteria

Case 1: no structural change

- actual start set is effectively the same as baseline

Interpretation:

- the policy is too weak
- or the widened pool contains no eligible challengers

Case 2: structural change but no downstream path change

Interpretation:

- the bottleneck is later than start carry-through
- or the challengers are genuinely different but still not promising

Case 3: structural and downstream change, but still no better result

Interpretation:

- the study succeeded in changing the explored path
- but the carried challenger was not actually better

All three outcomes are still scientifically useful if they are well
instrumented.

## 14. Anti-Drift Rules

These rules are mandatory for this implementation.

1. One main hypothesis only:
   - novel-start carry-through from the widened late pool
2. One intervention boundary only:
   - actual Phase-C start selection
3. No bundled changes to:
   - Phase-B ranking
   - tie-band widening
   - rescue
   - scorer semantics
   - Stage-3.5
4. Reuse existing family-view language for novelty
5. Keep the widened-late baseline explicit in both code comments and planning
   notes
6. Do not call the study "balanced" or "family-preserved" in code paths or log
   labels; call it what it is:
   - `novel_challenger_v1`

## 15. Logging Requirements

Two logs must be maintained during implementation.

### Planning log requirements

Update:

- `planning/working/no_wli_next_phase_implementation_plan_2026-03-27.md`

Record:

- why this study is next
- exact intervention boundary
- exact control/candidate framing
- anti-drift rules
- canary requirements

### Science log requirements

Update:

- `planning/working/no_wli_science_run_log_2026-03-26.md`

Record:

- why this study exists
- what it is trying to distinguish
- what code surfaces changed
- what meaningful proof tests passed
- what the eventual long-run readout means

Rule:

- every major implementation step should add a short evidence-backed note to
  the science log
- do not wait until the end to backfill all changes

## 16. Meaningful Proof Before Any Long Run

The minimum pre-run proof standard is:

1. deterministic unit test for novelty selection
   - legacy policy keeps the current behavior
   - `novel_challenger_v1` selects one or two distinct challengers when
     eligible
2. preset/config/lock/runtime canary
   - proves the new policy appears in runtime state and saved config
3. integration-style test on a synthetic candidate pool
   - proves the candidate pool is unchanged
   - proves only the actual start selection differs
4. persistence test
   - proves the new novelty telemetry reaches reviewer-facing artifacts

If these are not green, do not hand off a long run.

## 17. Implementation Stages

### Stage A: lock the config and telemetry surface

Goal:

- define the new policy name and its required telemetry fields

Done when:

- the config surface is explicit
- the telemetry schema is listed in code and planning docs

### Stage B: implement the start-selection policy only

Goal:

- add `novel_challenger_v1` without changing candidate-pool construction or
  ranking

Done when:

- legacy policy still behaves identically
- the new policy selects different starts only when eligible challengers exist

### Stage C: thread persistence and diagnostics

Goal:

- ensure novelty telemetry is visible in:
  - `stage3_diagnostics`
  - `best/best_instance.json`
  - `stages.json`
  - `final_instances/...json`

Done when:

- a negative result would still be scientifically interpretable

### Stage D: run short proof slices only

Goal:

- prove the study is wired correctly

Done when:

- canary and guard tests pass
- no long run has been started yet

### Stage E: hand off the long compare

Goal:

- user runs one clean control-vs-candidate long compare

Compare should be:

- same `411` seed
- same widened-late baseline
- only start policy changed

## 18. Bottom Line

This is the right next `411`-track study because it is more precise than:

- generic width
- generic source balancing
- narrow-band family reservation

It directly tests the strongest current downstream question:

- when widened late diversity exists, can we convert one or two eligible novel
  challengers into actual explored starts?

That is the cleanest next step toward learning what downstream basin-family
properties actually turn nominal diversity into a real solution path.

## 19. Status Update: Implemented And Ready For Live Compare

Implementation is now complete for the first-pass `411` novel-start study.

What landed:

- shared novelty/family-view support in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/family_views.py`
- new Phase-C start policy branch in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - policy name:
    - `novel_challenger_v1`
- explicit persistence of the new study telemetry through:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`

Telemetry now persisted explicitly:

- `phaseC_start_policy`
- `phaseC_novel_view_id`
- `phaseC_anchor_candidate_hash`
- `phaseC_candidate_pool_eligible_novel_count`
- `phaseC_candidate_pool_eligible_novel_row_count`
- `phaseC_candidate_pool_eligible_novel_source_counts`
- `phaseC_start_eligible_novel_count`
- `phaseC_selected_novel_challenger_count`
- `phaseC_eligible_novel_not_selected_count`
- `phaseC_selected_novel_challenger_hashes`
- per-start summary fields:
  - `selection_bucket`
  - `selected_by_novel_policy`
  - `eligible_novel_challenger`
  - `novelty_distance_to_anchor`
  - `novelty_min_distance_to_selected_challenger`

Meaningful proof completed:

- deterministic and persistence slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py -q`
  - result:
    - `17 passed`
- config/runtime/canary slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py -q`
  - result:
    - `36 passed`
- broader guard slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - result:
    - `97 passed`

Live compare prepared:

- control:
  - `stage3_phaseb_width_probe_p9`
- candidate:
  - `stage3_phasec_novel_challenger_p9`
- experiment id:
  - `tune_v43_p9c3_seed411_novel_start_compare_2job`
- control files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v43_p9c3_seed411_novel_start_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v43_p9c3_seed411_novel_start_compare_2job.jsonl`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v43_p9c3_seed411_novel_start_compare_2job.json`

Anti-drift note:

- no Phase-B ranking change was bundled
- no candidate-pool construction change was bundled
- no rescue change was bundled
- no Stage-3.5 change was bundled
- the only study-semantic change is the Phase-C start-selection policy

## 20. Status Update: First Live Compare Invalidated, Same Study Re-Armed

The first live compare for this study did not produce a science result.

What happened:

- both prepared `v43` jobs failed with:
  - `KeyError: 'STAGE3_PHASEC_START_POLICY'`
- evidence:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v43_p9c3_seed411_novel_start_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v43_p9c3_seed411_novel_start_compare_2job.jsonl`

Why this does not change the study design:

- both saved `run_config.json` files were already correct:
  - widened-late control kept:
    - `phase_c.start_policy = "source_order"`
  - candidate kept:
    - `phase_c.start_policy = "novel_challenger_v1"`
- so the bug was not in preset resolution, run-config emission, or control
  study framing
- the bug was in the live Stage-3 bridge:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_iteration_bridge.py`
  - missing forwarding of:
    - `STAGE3_PHASEC_START_POLICY`

Fix and proof:

- explicit bridge forwarding added
- regression strengthened in:
  - `tests/tools/test_no_wli_stage_engine_iteration_bridge.py`
- focused proof:
  - `26 passed`
- broader guard:
  - `108 passed`

Decision:

- keep the study identical
- do not change the hypothesis, novelty rule, widened baseline, or telemetry
  schema
- only refresh the control-file identity and rerun the same compare

## 21. Status Update: v44 clarified the real live bug class

The fresh `v44` rerun also failed with the same `KeyError`.

What this changed:

- the earlier fix in `stage_engine_iteration_bridge.py` was still correct, but
  it was not the real live failure site for fixture-matrix runs
- the actual runtime path still went through:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_builder.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`

Corrected root cause:

- `IterationMatrixConfig` did not carry `stage3_phasec_start_policy`
- therefore the fixture-matrix live path still dropped
  `STAGE3_PHASEC_START_POLICY` before `stage3_iteration_flow.py`

Fix now in place:

- shared runtime-state contract:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_state_contract.py`
- matrix builder threads the policy into typed config
- matrix flow threads the policy into live Stage-3 state
- lower bridge also uses the same contract

Proof:

- focused:
  - `34 passed`
- broader guard:
  - `116 passed`

Decision:

- keep the study identical again
- do not change widened baseline, novelty rule, or telemetry
- rerun the same compare only after the actual matrix-path fix

## 22. Status Update: v45 closed as a valid negative, with an important adequacy lesson

The `v45` rerun is a real study result and closes `novel_challenger_v1` as a
valid negative.

Evidence:

- control:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T053053469532Z__bench_solve_pipeline_no_wli__55b7159`
- candidate:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T075915341627Z__bench_solve_pipeline_no_wli__55b7159`
- state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v45_p9c3_seed411_novel_start_compare_2job_rerun2.json`

What happened:

- the candidate policy executed correctly:
  - `phaseC_start_policy = "novel_challenger_v1"`
  - `phaseC_candidate_pool_eligible_novel_count = 31`
  - `phaseC_selected_novel_challenger_count = 2`
- but the actual explored start set stayed identical to the widened-late
  control:
  - same six `candidate_hash` values
  - same source mix
  - same `phaseC_start_unique_end_hash = 6`

Why this is still scientifically useful:

- the widened late pool really did contain many eligible novel challengers
- `novel_challenger_v1` really did reserve two of them
- but those two challengers were already in the legacy widened-late start set
- so the study did not force any *new* challenger into the actual explored set

Most important adequacy lesson:

- the checkpoint `final_match` values are true per-start truth-match values
- but the saved run winner remains score-selected
- therefore reviewer-facing top-level `best_match_ratio` can stay flat even when
  Phase-C explores a substantially higher-truth challenger path

Concrete `v45` example:

- score-selected anchor:
  - `candidate_hash = 73eee2bf84b7c07f`
  - `final_match = 0.039`
  - `final_score = 0.19101667350788198`
- higher-truth challenger explored but not selected:
  - `candidate_hash = 9002ee09917e5a0d`
  - `final_match = 0.418`
  - `final_score = 0.17284542866740327`

Decision:

- do not rerun `novel_challenger_v1`
- the next `411`-track study, if pursued, should be stricter:
  - force one or two novel challengers that are not already selected by the
    widened-late legacy fill
- separately, the pipeline now clearly needs better reviewer-facing exposure of
  high-truth challenger paths that lose on score
