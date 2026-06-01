# no_wli Solve-Integrity Plan

Date: 2026-03-21
Status: Active working plan
Scope: `tools/benchmarks/periodic_sub_trans/no_wli`

## Purpose

This is the active plan for the no-WLI hard-solve programme.

It is deliberately **not** a broad repo tidy-up plan and **not** a new late-solver invention plan.
The immediate goal is to restore trustworthy learning by fixing proof integrity first and then identifying where the stronger old hard-case basin was lost.

This file should be treated as the working checklist for the branch and updated in place as phases complete.

## Companion Decision Pack

For the narrower deep-research decision layer that sits above this execution checklist, see:

- `planning/working/no_wli_deep_research_pack_2026-03-21/README.md`
- `planning/working/no_wli_deep_research_pack_2026-03-21/capability_ladder_no_wli_periodic_sub_trans_2026-03-21.md`
- `planning/working/no_wli_deep_research_pack_2026-03-21/method_families_next_capability_jump_2026-03-21.md`
- `planning/working/no_wli_deep_research_pack_2026-03-21/evidence_gaps_no_wli_periodic_sub_trans_2026-03-21.md`
- `planning/working/no_wli_deep_research_pack_2026-03-21/tactical_refactor_filter_solve_first_2026-03-21.md`

Use that pack for capability positioning, method ordering, evidence confidence, and solve-first refactor discipline.
Keep this file as the active gate and execution tracker.

## Current evidence snapshot

Canonical references:

- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/inventory_summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/best_p9_c3_runs.csv`
- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/solve_status_report.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/basin_regression_summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/selector_ladder_audit_summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/partial_state_signal_audit_summary.json`

Key artifacts:

- recovered Stage-3 baseline:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260321T190828084704Z__bench_solve_pipeline_no_wli__55b7159/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json`
- clean Stage-3.5 win:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260322T001521766633Z__bench_solve_pipeline_no_wli__55b7159/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json`
- failed cross-seed confirmation:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260322T192204224097Z__bench_solve_pipeline_no_wli__55b7159/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed211.json`

Evidence summary:

- best `p9/c3/l1000` run is now the clean Stage-3.5 proof at `0.794`
- recovered Stage-3 baseline reached `0.771`
- cross-seed confirmation on `seed = 211` only reached `0.574`
- the strongest recovered Stage-3 family is back for `seed = 511`
- Stage-3.5 has been proven to add value on top of that strong basin
- cross-seed reliability is still weak because some hard seeds do not reach a comparable Stage-3 basin first
- the new partial-state signal audit shows:
  - Stage-2 partial-state signals are weak discriminators across selected hard runs
  - Stage-3 top-k and later signals become informative once the search reaches a useful family
  - the general failure now looks like weak early/mid basin signal plus seed-sensitive search reach

Current interpretation:

1. Proof integrity is no longer the main blocker.
2. The core reliability problem is now **cross-seed basin reach before late refinement**, not late-solver validity.
3. If stronger partial-state signals are absent before Stage 3, further Stage-3 promotion tuning alone is unlikely to scale.

## Scope and non-goals

### In scope

- proof-integrity hardening
- hard-case basin-regression analysis
- selector/scorer audit on a small real ladder
- one bounded recovery proof after the above gates

### Out of scope for now

- broad v1 repo tidy-up
- new solver invention before regression is understood
- broad run sweeps / wide matrices
- `p11` / `p13` as the main decision ladder

## Baseline ladder

This ladder is frozen for near-term evaluation.

### Easy controls

- `fixture_fixture_001_p5_c1_l1000`
- `fixture_fixture_001_p5_c3_l1000`
- `fixture_fixture_001_p7_c1_l1000`
- `fixture_fixture_001_p7_c5_l1000`

### Medium-ish control

- `fixture_fixture_001_p9_c1_l1000`

### Hard target

- `fixture_fixture_001_p9_c3_l1000`

Rule:
- no new major claim should be made without checking behaviour against this ladder

## Phase status board

- Phase 0: Freeze baseline ladder and active plan
  - Status: completed
- Phase 1: Proof-integrity hardening
  - Status: completed
- Phase 2: Basin-regression A/B analysis
  - Status: completed
- Phase 3: Selector/scorer audit on the real ladder
  - Status: completed
- Phase 4: One bounded recovery proof
  - Status: completed
- Phase 5: One clean bounded Stage-3.5 proof
  - Status: completed
- Phase 6: Offline cross-seed basin-family diversity and score-truth alignment audit
  - Status: completed
- Phase 7: Targeted resumed experiments split by failure mode
  - Status: in progress

## Phase 1: Proof-integrity hardening

### Goal

Prevent a requested Stage-3.5 proof from silently completing as a nominal result when Stage-3.5 did not actually run.

### Expected files

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage35_substitution_solver.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
- if needed:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`

### Required behaviour

- Final outputs must distinguish:
  - Stage-3.5 requested
  - Stage-3.5 effectively enabled in the live path
  - Stage-3.5 ran
  - proof validity / invalid reason
- A proof with `stage35 requested = true` but `stage35_ran = 0` must be marked invalid and must not be treated as a normal proof result.

### Meaningful tests

- strengthen `tests/tools/test_no_wli_stage35_substitution_solver.py`
- strengthen `tests/tools/test_no_wli_fixture_matrix_runtime.py`
- add one integration-style proof-validity test if current coverage is not enough

Minimum assertions:

- requested Stage-3.5 cannot end with `ran = 0` and no invalid marker
- disabled Stage-3.5 stays cleanly disabled
- the specific `run_config enabled / final artifact ran=0` mismatch is reproducible as a regression test and then blocked

### Gate 1

No new proof run until:

- a requested Stage-3.5 proof cannot silently finish with `stage35_ran = 0`

### 2026-03-21 update

Gate 1 cleared.

Implemented:

- threaded `STAGE35_ENABLED` / `STAGE35_CFG` through the iteration-matrix and stage-engine bridge path
- added explicit proof markers:
  - `stage35_requested_cfg`
  - `stage35_proof_valid`
  - `stage35_proof_invalid_reason`
- exposed those markers in final Stage-3 diagnostics and top-level final outputs
- added a flow-level regression test for the old invalid shape:
  - requested Stage-3.5
  - `ran = 0`
  - explicit invalid-proof marker instead of silent nominal result

Validated with:

- `tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py`
- `tests/tools/test_no_wli_truth_diagnostics.py`
- `tests/tools/test_no_wli_stage35_substitution_solver.py`
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`
- `tests/tools/test_no_wli_stage_engine_iteration_bridge.py`
- `tests/tools/test_no_wli_run_completion.py`
- `tests/tools/test_no_wli_iteration_finalize_word_ngram.py`

Next action:

- Phase 2 basin-regression A/B analysis

## Phase 2: Basin-regression A/B analysis

### Goal

Find where the old stronger `p9/c3` basin is lost.

### Comparison set

Primary:

- `20260312T002501438386Z__bench_solve_pipeline_no_wli__5961d3e`
- `20260321T005721635958Z__bench_solve_pipeline_no_wli__55b7159`

Secondary:

- `20260315T001203236783Z__bench_solve_pipeline_no_wli__5961d3e`
- `20260315T215112716215Z__bench_solve_pipeline_no_wli__5961d3e`

### Inputs to compare

- `run_config.json`
- `stages.json`
- `final_instances/*.json`
- `phasec_start_checkpoints.jsonl` when present

### Questions to answer

- Did the regression happen before Stage 3?
- Did it happen inside Stage-3 basin generation?
- Did it happen at late handoff into refinement?

### Required deliverable

This phase must end with exactly:

- one primary culprit:
  - `pre_stage3_regression`
  - `inside_stage3_basin_generation`
  - `late_handoff_regression`
- optional secondary contributors ranked below it
- one short evidence table backing the ranking

This phase is not complete without naming one primary culprit.

### Meaningful tests

- deterministic artifact-parser tests for the March and March 21 comparison set
- stable comparison-summary tests if a helper is added

### Gate 2

No new late-solver design or proof run until:

- Phase 2 names one primary culprit with explicit evidence

### 2026-03-21 update

Gate 2 cleared.

Canonical outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/basin_regression_report.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/basin_regression_summary.json`

Primary culprit:

- `inside_stage3_basin_generation`

Ranked conclusion:

1. `inside_stage3_basin_generation`
2. no strong secondary contributor named yet

Short evidence table:

- `stage2_topk` top-5 mean match:
  - old `0.0958`
  - current `0.0958`
  - delta `0.0000`
- `stage3_topk` top-5 mean match:
  - old `0.7678`
  - current `0.6378`
  - delta `-0.1300`
- final best match:
  - old `0.773`
  - current `0.668`
  - delta `-0.105`

Interpretation:

- the regression is not primarily pre-Stage-3, because the Stage-2 top-k family is effectively unchanged
- the regression is not primarily late handoff, because the weaker family is already visible in `stage3_topk`
- the strongest evidence points to Stage-3 basin generation itself

Next action:

- Phase 3 selector/scorer audit on the frozen ladder

## Phase 3: Selector/scorer audit on the real ladder

### Goal

Check whether current live-visible ranking signals separate better and worse basins across easy, medium, and hard tiers.

### Likely code surface

- `tools/benchmarks/periodic_sub_trans/no_wli/replay_phasec_rescue_sweep.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/replay_stage35_substitution_solver.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage35_ranking.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/phasec_rescue_selector.py`

### Questions

- On easy solved controls, do current selectors preserve good outcomes?
- On `p9/c1`, do selectors separate stronger basins from weaker ones?
- On `p9/c3`, what selector regret remains on close candidates?
- Do current score/search-led signals actually rank the better basin above the worse basin?

### Meaningful tests

- deterministic replay summary tests on a fixed artifact subset
- stable ladder-audit output on the same inputs
- no-oracle safety remains covered

### Gate 3

No selector/ranking change should proceed unless it:

- does not break easy controls
- helps at least the medium/hard side of the ladder
- improves candidate choice, not just diagnostics

### 2026-03-21 update

Phase 3 audit completed.

Canonical outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/selector_ladder_audit_report.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/selector_ladder_audit_summary.json`

Key findings:

- easy controls remain stable with zero observed top-k truth regret
- `p9/c1` shows non-zero within-run selector regret:
  - mean `0.0034`
  - top-is-best rate `0.444`
- `p9/c3` also shows selector imperfection, but it is smaller than the Stage-3 basin drop:
  - mean top-k regret `0.0007`
  - top-is-best rate `0.825`
  - final score/match correlation across runs `0.915`

Interpretation:

- current score-led ranking is imperfect and not fully robust
- but the audit does not support “totally broken scorer” as the primary explanation
- the Phase 2 conclusion still stands:
  - the dominant regression is inside Stage-3 basin generation

Next action:

- Phase 4 bounded recovery proof setup using the older narrow Stage-3 regime that already reached the strong `0.761` family

## Phase 4: One bounded recovery proof

### 2026-03-21 update

Phase 4 setup is in progress.

Chosen recovery target:

- the Phase-C-enabled March 15 `0.761` family, not the newer wide/deep proof preset

Recovery preset shape:

- `init_keys = 64`
- `span_basin_judge.k / tie_max_seeds = 64`
- `phase_a.steps = 800`
- `phase_b.steps = 2200`
- `phase_b_top_n = 8`
- `gate_delta_floor = 0.003`
- `gate_end_gain_floor = 0.001`
- `phase_c.enabled = true`
- `phase_c.start_keys = 6`
- `phase_c.cfg.steps = 96`
- `stage35.enabled = false`

Reason:

- this older narrow Stage-3 regime already produced a strong hard-family run (`0.761`) with Phase-C enabled
- it is a cleaner recovery target than the newer wide/deep proof preset
- it keeps the next run focused on basin recovery rather than mixing in a fresh Stage-3.5 claim

Local validation added:

- fixture-matrix preset forwarding test for `stage3_recovery_p9_8h`
- recovery finalize-path smoke test using the real payload builder bridge

What this now guarantees before the live run:

- the active recovery preset reaches the runtime apply path with the intended narrow Stage-3 overrides
- the bounded recovery artifact path preserves:
  - Phase-C checkpoint markers
  - Stage-3 diagnostics
  - explicit Stage-3.5-disabled validity markers

### Goal

Recover the stronger hard-case basin before asking Stage-3.5 to prove anything.

### Run shape

- one bounded `p9/c3/l1000` run
- one seed
- one preset
- no matrix sweep

### Success bar

At least one of:

- final result materially above `0.668`
- `stage3_topk` family materially closer to the old `0.77x` cluster
- clear evidence that the regression point named in Phase 2 was actually fixed

### Gate 4

If the recovery proof still lands in the `0.63x / 0.64x` family, stop and reassess upstream search rather than piling on more late logic.

### 2026-03-21 update

Gate 4 cleared.

Canonical recovery artifact:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260321T190828084704Z__bench_solve_pipeline_no_wli__55b7159/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json`

Recovery result:

- final `best_match_ratio = 0.771`
- final `best_score = 0.33803928316311727`
- `best_stage = stage3_full_refine`
- `stage3_topk` top-5 cluster:
  - `0.757, 0.754, 0.754, 0.754, 0.754`

Checkpoint evidence:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260321T190828084704Z__bench_solve_pipeline_no_wli__55b7159/phasec_start_checkpoints.jsonl`
- anchor Phase-C start reached `0.761`
- challenger `source_rank = 2` overtook the anchor and finished at `0.771`

Interpretation:

- the older narrow Stage-3 regime does recover the stronger hard-case basin family
- the project is no longer blocked on the specific `0.638 / 0.640` regressed family
- the next question is now the intended Phase 5 question:
  - can clean live Stage-3.5 beat this recovered Phase-C baseline?

Next action:

- switch the active bounded proof preset to a Stage-3.5 proof that keeps the recovered Stage-3 regime intact
- run one bounded `p9/c3/l1000` proof with Stage-3.5 enabled and proof-validity markers required

## Phase 5: One clean bounded Stage-3.5 proof

### 2026-03-21 update

Phase 5 setup is now in progress.

Active proof shape:

- keep the recovered Stage-3 regime from Phase 4:
  - `init_keys = 64`
  - `phase_b.steps = 2200`
  - `phase_b_top_n = 8`
  - `phase_c.enabled = true`
  - `phase_c.start_keys = 6`
  - `phase_c.cfg.steps = 96`
- re-enable Stage-3.5 with the bounded proof config used in the earlier proof-integrity work:
  - `seed_keep = 4`
  - `beam_width = 4`
  - `archive_keep = 16`
  - `rounds = 3`
  - `mini_search_keep_all_rows = 1`
  - `accept_score_min_gain = 0`
  - `accept_search_score_max_drop = 0`

Reason:

- the earlier Stage-3.5 proof attempt was invalid and also sat on a regressed basin
- Phase 4 recovered the strong basin cleanly
- the right next proof is therefore a narrow rerun of Stage-3.5 on top of the recovered basin, not a new solver branch or a wider matrix

### Goal

Answer the real question:

- can live Stage-3.5 beat the stable Phase-C baseline on a credible `p9` run?

### Proof requirements

A valid proof must show:

- `run_config` requested Stage-3.5
- final artifact records Stage-3.5 as effectively enabled
- `stage35_ran = 1`
- `stage35_archive_count > 0`
- proof validity passes
- result is auditable against the preserved baseline

### Success bar

Strong:

- Stage-3.5 runs
- archive is non-empty
- proof is valid
- final result beats the recovered baseline

Weak but still useful:

- Stage-3.5 runs cleanly and produces a coherent archive even if it does not yet beat the recovered baseline

### Gate 5

Only after a clean `p9` proof should `p11` be considered.
`p13` remains out of scope until then.

### 2026-03-22 update

Gate 5 cleared.

Canonical proof artifact:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260322T001521766633Z__bench_solve_pipeline_no_wli__55b7159/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json`

Proof result:

- final `best_match_ratio = 0.794`
- final `best_score = 0.3534210925874578`
- `best_stage = stage35_substitution_only`

Stage-3.5 proof markers:

- `stage35_requested_cfg = 1`
- `stage35_enabled_cfg = 1`
- `stage35_ran = 1`
- `stage35_selected = 1`
- `stage35_proof_valid = 1`
- `stage35_archive_count = 16`
- `stage35_seed_count = 6`

Recovered-baseline comparison:

- Phase 4 recovered baseline:
  - `best_match_ratio = 0.771`
  - `best_score = 0.33803928316311727`
- Phase 5 proof result:
  - `best_match_ratio = 0.794`
  - `best_score = 0.3534210925874578`
- gain:
  - match `+0.023`
  - score `+0.01538180942434053`

Interpretation:

- this is the first clean live proof that Stage-3.5 can beat the recovered `p9/c3` Phase-C baseline
- the solve programme is no longer blocked on proof integrity, Stage-3 regression, or the question of whether Stage-3.5 has real value on top of a strong basin
- the immediate next step should be confirmation and generalisation, not a fresh solver redesign

Next action:

- freeze this proof result as the new `p9/c3` best evidence
- run one narrow confirmation step before broadening:
  - either one additional `p9/c3` seed with the same preset
  - or one adjacent control-tier proof using the same Stage-3.5 shape

### 2026-03-22 next-step note

Chosen confirmation step:

- one additional `p9/c3/l1000` bounded proof on `seed = 211`
- keep the same recovered Stage-3 plus Stage-3.5 preset shape from the successful `seed = 511` proof

Reason:

- `seed = 211` is the strongest non-`511` historical `p9/c3` seed in the current archive
- best archived `seed = 211` result is `0.637`, which makes it a meaningful confirmation target without broadening the problem ladder yet

Catalog note:

- after the `0.794` proof, the catalog builder was updated to read `stage35_selected` and `seed` from nested diagnostics / `key_seed` fallback when those fields are absent at the artifact top level
- this keeps `best_p9_c3_runs.csv` and `inventory_summary.json` honest for Stage-3.5 proof tracking

### 2026-03-23 confirmation note

First confirmation attempt:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260322T192204224097Z__bench_solve_pipeline_no_wli__55b7159/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed211.json`

Result:

- final `best_match_ratio = 0.574`
- final `best_score = 0.23689607961472836`
- `best_stage = stage3_full_refine`

Stage-3.5 proof markers stayed valid:

- `stage35_requested_cfg = 1`
- `stage35_enabled_cfg = 1`
- `stage35_ran = 1`
- `stage35_proof_valid = 1`
- `stage35_archive_count = 16`
- `stage35_seed_count = 2`
- `stage35_selected = 0`
- `stage35_accept_reason = search_score_drop_guard_failed`

Interpretation:

- this is not a proof-integrity failure
- it is a seed-generalisation failure
- the recovered Stage-3 regime that worked for `seed = 511` did not recover a comparably strong basin for `seed = 211`
- Stage-3.5 therefore had too little useful basin quality to work with and was correctly rejected by the live acceptance guard

Immediate next question:

- how much of the remaining reliability problem is due to Stage-3 seed fragility across `p9/c3` seeds, versus the specific acceptance/ranking shape inside Stage-3.5 once the basin is weak?

### 2026-03-23 partial-state signal audit note

Audit outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/partial_state_signal_audit_summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/partial_state_signal_audit_report.md`

Comparison set:

- strong runs:
  - `seed511_old_best`
  - `seed511_recovery`
  - `seed511_stage35_win`
- weak runs:
  - `seed211_old_best`
  - `seed211_stage35_fail`
  - `seed411_old_best`

State kinds compared:

- `stage2_topk`
- `stage3_topk`
- `phasec_start`
- `stage35_seed`
- `stage35_archive`

Headline results:

- Stage-2 partial-state scores remain weak as basin discriminators across the selected hard runs:
  - `stage2_topk.score_stage2` run-max/final-match correlation `0.265`
  - strong-vs-weak separation gap `-0.004827`
  - top-by-signal truth-best rate `0.167`
- Stage-3 top-k scores carry much stronger basin signal once the search reaches a useful family:
  - `stage3_topk.score_judge` run-max/final-match correlation `0.880`
  - strong-vs-weak separation gap `0.050475`
  - top-by-signal truth-best rate `0.667`
- Late Stage-3.5 archive ranking is not the main problem on weak seeds:
  - archive `search_score` remains more truth-aligned than raw archive `score`
  - the `seed = 211` rejection therefore looks consistent with weak basin quality rather than a broken acceptance rule

Interpretation:

- current live-visible signals do not separate strong from dead states well enough before Stage 3
- they do become informative inside Stage-3 top-k and later
- the general failure mode therefore looks like weak early/mid basin signal plus seed-sensitive Stage-3 search reach, not a completely broken late-stage scorer

Decision implication:

- if no stronger pre-Stage-3 partial-state signals are available, further optimisation of current Stage-3 promotion logic alone is unlikely to scale reliably across seeds
- the next design work should therefore prioritise stronger early/mid partial-state signals or a search regime that can preserve more candidate diversity until the later informative signals appear

### 2026-03-23 Stage-3 preservation probe setup note

Implementation intent:

- take the most conservative next step first
- do not invent a new Stage-3 selector yet
- instead widen and expose the existing Phase-B tie-band preservation mechanism so it can be tested explicitly on a fixed hard-seed set

Code changes:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
  - fixture-matrix now supports forcing `STAGE3_SPAN_BASIN_JUDGE_TIE_EPS`
  - two-phase default syncing now also carries tie-band defaults
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - preset resolution and application now forward `force_stage3_span_basin_judge_tie_eps`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/profile_defaults.py`
  - tie-band defaults are now stored and restored explicitly rather than drifting across runs
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  - active next-step preset is now `stage3_preserve_tieband_probe_p9`

Active preservation probe shape:

- fixture family:
  - `p9 / c3 / l1000`
- fixed seed set:
  - `511`
  - `211`
  - `411`
- recovered narrow Stage-3 regime kept:
  - `init_keys = 64`
  - `phaseB_top_n = 8`
  - `phaseB.steps = 2200`
  - `Phase-C enabled`
- Stage-3.5 disabled
- widened Phase-B tie-band:
  - `tie_eps = 0.005`
  - `tie_max_seeds = 16`
- wallclock cap removed for this probe:
  - `MAX_WALLCLOCK_SECONDS = None`

Reasoning:

- the partial-state audit says current live-visible signal is still weak before Stage 3
- the first bounded next step should therefore preserve more candidate families until the stronger Stage-3 signal appears
- using the existing tie-band route first is lower risk and easier to interpret than inventing a new promotion heuristic immediately

Tests added:

- `tests/tools/test_no_wli_stage3_phasec.py`
  - tie-band can expand Phase-B seed preservation beyond the nominal `top_n`
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - the new `stage3_preserve_tieband_probe_p9` preset really forwards the widened tie-band overrides

Validation:

- `22 passed` on focused Stage-3 / fixture-matrix / audit / diagnostics tests

Open question this probe is meant to answer:

- does a wider Phase-B preservation band lift weak hard seeds such as `211` and `411` without giving back the recovered strong `511` basin?

### 2026-03-23 preservation-probe correction and resume-handoff note

Important correction:

- the finished `v31` preservation probe was **not** the intended three-seed comparison
- the executed plan and state files were:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v31_p9c3_stage3_preserve_probe.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v31_p9c3_stage3_preserve_probe.json`
- those files materialized only **one job**, for `seed = 511`
- so the `v31` result should be interpreted only as:
  - widened tie-band preservation does not break the known strong `511` basin
- it does **not** answer the cross-seed question for `211` / `411`

What was found:

- `MAX_JOBS` in fixture-matrix config is a **total job truncation**, not merely a parallelism control
- that is why the previous intended multi-seed probe collapsed to one executed seed

Fix now in place:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  - `RUN_SEEDS = (211, 411)`
  - fresh state/event/plan paths on `v32`
  - `MAX_JOBS = 2` so both weak-seed jobs materialize
- plan smoke cross-check now confirms:
  - `job_count = 2`
  - `job_seeds = [211, 411]`

Resume-handoff saving normalized:

- completed runs now also write:
  - `run_dir/resume_handoffs/<artifact_stem>/manifest.json`
  - `run_dir/resume_handoffs/<artifact_stem>/stage2_resume.json`
  - `run_dir/resume_handoffs/<artifact_stem>/stage3_prep.json`
  - `run_dir/resume_handoffs/<artifact_stem>/stage35_seed_archive.json`
- this is enabled by default through:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/resume_handoff_artifacts.py`

Why this is worth making normal:

- it is cheap compared with the solve runtime
- it makes later-stage reruns explicit and easier to discover
- it preserves the gate-ready subsets we can already reconstruct reliably
- it does not attempt full in-flight solver checkpointing

Current limitation remains:

- `stage2_to_stage3` handoff is reconstructed from saved `stage2_topk`
- this is a pragmatic experiment-time resume bundle, not a bit-perfect full solver-state resume

Validation:

- focused test sweep after the fix and new handoff writer:
  - `tests/tools/test_no_wli_resume_handoff_artifacts.py`
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - `tests/tools/test_no_wli_stage3_phasec.py`
  - `tests/tools/test_no_wli_artifact_resume.py`
  - `tests/tools/test_no_wli_truth_diagnostics.py`
  - result: `26 passed`

### 2026-03-23 artifact-based Stage-2 / Stage-3 resume tooling note

Implementation intent:

- reduce time-to-learn for downstream experiments
- avoid rerunning the full pipeline when the experiment only needs a saved Stage-2 or late Stage-3 handoff
- keep the scope narrow and local to `tools/benchmarks/periodic_sub_trans/no_wli`

New files:

- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/resume_from_artifact.py`
- `tests/tools/test_no_wli_artifact_resume.py`

Supported resume modes:

- `stage2_to_stage3`
  - reconstruct Stage-2 handoff from saved `stage2_topk`
  - rebuild scorer/cipher runtime from the saved artifact and its `run_config.json`
  - rerun Stage 3 onward without rerunning Stage 1 / Stage 2
- `stage3_to_stage35`
  - reuse saved late-stage artifact state
  - rerun Stage-3.5 from a saved artifact without rerunning Stage 1 / Stage 2 / Stage 3

Entry workflow:

- hardcoded entry script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/resume_from_artifact.py`
- no CLI surface added
- outputs written under:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume/...`

What is saved in a resume bundle:

- `summary.json`
- for `stage2_to_stage3`:
  - `stage2_resume.json`
  - `stage3_prep.json`
  - `stage3_flow.json`
  - `outcome.json`
- for `stage3_to_stage35`:
  - `stage35_summary.json`
  - `stage35_archive.json`
  - `stage35_seed_rows.json`

Validation:

- deterministic tests:
  - `tests/tools/test_no_wli_artifact_resume.py`
    - reconstruct Stage-2 resume inputs from saved `stage2_topk`
    - build Stage-3 prep from reconstructed handoff
    - rerun Stage-3.5 from saved late artifact state
    - call Stage 3 flow from reconstructed Stage-2 handoff
- focused regression sweep:
  - `tests/tools/test_no_wli_artifact_resume.py`
  - `tests/tools/test_no_wli_stage35_substitution_solver.py`
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - `tests/tools/test_no_wli_truth_diagnostics.py`
  - result: `24 passed`

Real-artifact smoke:

- source artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260321T190828084704Z__bench_solve_pipeline_no_wli__55b7159/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json`
- reconstructed quickly from saved state:
  - `stage2_topk_row_count = 12`
  - `stage2_promote_top_cfg = 160`
  - `stage2_promoted_from_topk_count = 12`
  - `best2_match = 0.209`
  - `stage3_init3_count = 64`

Important limitation:

- the `stage2_to_stage3` resume path reconstructs the Stage-2 promoted pool from saved `stage2_topk`
- it does **not** restore the exact original in-memory Stage-2 archive/promoted pool
- so this is a high-value handoff-resume harness for experimentation, not a bit-perfect full solver-state checkpoint/resume system

## Required meaningful test set

These are the branch-anchor tests this plan expects:

1. proof-integrity integration test
   - requested Stage-3.5 cannot silently end as a nominal result with `ran = 0`
2. config-propagation regression test
   - proof preset reaches final artifact state correctly
3. basin comparison parser test
   - March and March 21 artifacts compare deterministically
4. selector/scorer ladder audit test
   - fixed artifact subset produces stable audit output
5. no-oracle Stage-3.5 safety test
   - live seed/ranking path remains truth-free
6. recovery-proof smoke test
   - bounded proof path emits expected late artifacts and validity markers
7. artifact-resume handoff tests
   - saved `stage2_topk` can reconstruct a usable Stage-3 handoff
   - saved late artifact state can rerun Stage-3.5 without the earlier pipeline stages

## Update protocol

When work progresses, update this file in place:

- change the phase status line
- add a dated note under the phase if a gate is cleared
- if a gate fails, record the failure explicitly rather than rewriting history

Do not replace this file with a fresh summary. Keep it as the running record.

## Phase 6: Offline cross-seed basin-family diversity and score-truth alignment audit

### Goal

Use saved handoff bundles and existing hard-seed artifacts to determine which failure mode is dominant across weak and strong `p9/c3` runs:

- promising families absent early
- promising families present but collapsed during promotion/preservation
- promising families present and preserved but undervalued by live score
- promising families selected but not exploited by later refinement

This phase is measurement only.
It must not change live solver behaviour.

### Why this phase is now next

The finished weak-seed preservation probe did not support the simple “preserve more and weak seeds recover” story.

Observed outcomes:

- `seed211` preservation probe:
  - final `best_match_ratio = 0.574`
  - identical to the earlier failed Stage-3.5 confirmation on the same seed
  - widened tie-band preservation did not help
- `seed411` preservation probe:
  - final `best_match_ratio = 0.041`
  - final `best_stage = stage2_search`
  - yet `phasec_start_checkpoints.jsonl` contains challengers with truth matches around `0.402` to `0.418`
  - those challengers still lost under live score and were not adopted

Interpretation:

- `211` suggests “useful family absent or too weak before preservation matters”
- `411` suggests “truth-better challenger family can exist but still be undervalued or stranded”
- therefore more than one failure mode likely exists
- the next audit must distinguish those modes rather than forcing one single explanation

### Comparison set

Required hard-case runs:

- strong:
  - `seed511` recovery run (`0.771`)
  - `seed511` Stage-3.5 proof run (`0.794`)
- weak:
  - current `seed211` preservation run (`0.574`)
  - older stronger `seed211` run (`0.637`)
  - current `seed411` preservation run (`0.041`)
  - older stronger `seed411` run (`0.596`)

Optional controls:

- one easy solved case
- one `p9/c1` control

### Preferred inputs

Use saved artifacts and handoff bundles only where possible:

- `final_instances/*.json`
- `stage2_topk`
- `stage3_topk`
- `phasec_start_checkpoints.jsonl`
- `resume_handoffs/.../stage2_resume.json`
- `resume_handoffs/.../stage3_prep.json`
- `stage35_seed_rows`
- `stage35_archive`
- truth diagnostics already present in saved outputs

The audit must degrade gracefully when older artifacts do not contain richer checkpoint or truth-diagnostic fields.

### Family views for first pass

Predefine a small fixed set of family views and do not tune them per seed:

- exact key identity
- exact tail identity
- near-tail family under a fixed tail-Hamming rule
- broader full-key family under a fixed full-key Hamming rule

The first pass should keep these thresholds simple, hardcoded in one place, and shared across all analysed runs.

### Required measurements

For each relevant stage pool:

- raw structural uniqueness
- family/cluster count
- effective family count
- largest-family share
- top-band family count
- top-band family mass
- available diversity versus selected diversity

For score-truth alignment within and across families:

- live search score versus truth
- judge/full score versus truth where available
- selected family truth versus best-family truth
- family regret relative to best family in the run
- whether misranking is mainly within-family or between-family

### Required classification output

Each analysed run should end with one of:

- `good_family_absent`
- `good_family_collapsed`
- `good_family_undervalued`
- `good_family_not_exploited`

The phase-level report should then summarize which labels dominate across the comparison set.

### Deliverables

Code:

- one new offline audit script under `tools/benchmarks/periodic_sub_trans/no_wli`
- prefer a name that reflects both diversity and score-truth alignment, not diversity alone
- keep it separate from live solve code

Tests:

- family clustering under fixed thresholds
- available-versus-selected diversity summary
- family regret calculations
- deterministic handling of missing optional artifacts

Outputs:

- one machine-readable JSON summary
- one short markdown report

### Gate 6

Do not start another long live proof run until this audit answers, with evidence, whether the main weak-seed failures are:

- absence
- collapse
- undervaluation
- or non-exploitation

### Phase 6 staged implementation checklist

- Phase 6A: Define fixed inputs and family views
  - Status: completed
  - Requirements:
    - hardcode the first comparison set
    - define fixed family views and fixed thresholds in one place
    - define `best_family_truth` explicitly up front
- Phase 6B: Build stage-pool extraction and diversity bundle
  - Status: completed
  - Requirements:
    - implement stage-wise pool loading from saved artifacts and handoff bundles
    - emit selected-vs-available diversity as a first-class output block
    - degrade deterministically when optional artifacts are missing
- Phase 6C: Add family-level score/truth alignment and classification
  - Status: completed
  - Requirements:
    - compute family regret and selected-vs-best family comparison
    - classify each run with:
      - `primary_failure_mode`
      - optional `secondary_failure_mode`
      - `classification_confidence`
- Phase 6D: Tests and outputs
  - Status: completed
  - Requirements:
    - focused unit tests for clustering, diversity summaries, regret, and missing artifacts
    - output one JSON summary and one short markdown report under `no_wli_catalog`
    - keep first pass simple and fixed-threshold; no live policy changes

### 2026-03-24 update

Gate 6 cleared for the first-pass audit.

Implemented:

- offline audit script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/audit_basin_family_diversity_alignment.py`
- focused tests:
  - `tests/tools/test_no_wli_basin_family_diversity_alignment_audit.py`

Generated outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/basin_family_diversity_audit_summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog/basin_family_diversity_audit_report.md`

What the audit established on the fixed hard-seed comparison set:

- `seed211_current_preserve`
  - primary failure mode: `good_family_absent`
  - classification confidence: `0.75`
  - interpretation:
    - the run never reaches a family close enough to the stronger historical `seed211` reference
- `seed411_current_preserve`
  - primary failure mode: `good_family_undervalued`
  - secondary contributor: `good_family_absent`
  - classification confidence: `0.99`
  - interpretation:
    - a truth-better challenger family appears in `phasec_start`
    - but live score still backs the wrong family and the final artifact falls back to `stage2_search`

Aggregate first-pass result:

- failure-mode counts on the comparison set:
  - `good_family_absent = 1`
  - `good_family_undervalued = 1`
- this supports the earlier concern that more than one weak-seed failure mode is active
- it also means another generic long live proof is still not the right next move

Validation:

- `C:\\Python\\Python311\\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/audit_basin_family_diversity_alignment.py tests/tools/test_no_wli_basin_family_diversity_alignment_audit.py`
- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_basin_family_diversity_alignment_audit.py -q`
  - `5 passed`
- `C:\\Python\\Python311\\python.exe tools/benchmarks/periodic_sub_trans/no_wli/audit_basin_family_diversity_alignment.py`

## Current next action

Immediate next action:

- do not start another long live proof run yet
- use the saved `resume_handoffs` bundles for targeted resumed experiments, split by failure mode:
  - `seed211`
    - test whether the saved Stage-2 handoff can be lifted by Stage-3 policy changes at all
    - if not, the next work shifts upstream or toward stronger early/mid signals
  - `seed411`
    - test family-level ranking / selection changes on the saved downstream handoff
    - the key question is whether the truth-better challenger family can be promoted when the handoff is held fixed
- only after those targeted resumed experiments decide whether the next full run should target:
  - upstream search/generation
  - family-level scoring/ranking
  - or later within-family refinement

## Phase 7: Targeted resumed experiments split by failure mode

### Goal

Use the saved artifact-handoff resume path to separate:

- `seed211` as a Stage-3 basin reach / policy question
- `seed411` as a downstream family-ranking / selection question

This phase is still intentionally narrower than a new live proof run.
The purpose is to use fixed saved handoffs to learn faster about which downstream changes are actually worth a new expensive run.

### Phase 7 staged implementation checklist

- Phase 7A: Resume override surface
  - Status: completed
  - Requirements:
    - allow hardcoded Stage-3 / Phase-C config overrides on saved handoffs
    - keep this local to artifact-resume tooling; do not add CLI args
- Phase 7B: `seed211` fixed-handoff Stage-3 policy probe
  - Status: in progress
  - Requirements:
    - use the saved `seed211` weak-handoff artifact
    - compare a small fixed Stage-3 policy grid
    - report whether the saved handoff can be lifted at all
- Phase 7C: `seed411` fixed-handoff Phase-C ranking probe
  - Status: pending
  - Requirements:
    - use the saved `seed411` weak-handoff artifact
    - compare a small fixed family-ranking / lexical-gate grid
    - report whether the truth-better challenger family can be promoted on the same handoff
- Phase 7D: Focused tests and reports
  - Status: pending
  - Requirements:
    - artifact-resume tests prove override propagation
    - probe outputs produce one machine-readable summary and one short markdown report per seed

### 2026-03-24 resume-fidelity update

Phase 7A is now complete.

Implemented:

- artifact-resume override surface accepts hardcoded `run_config_override` mapping merges for:
  - Stage-3 policy probes
  - Stage-3.5 / Phase-C ranking probes
- normal completed runs now prefer writing the **actual live Stage-2/Stage-3 handoff** into:
  - `resume_handoffs/.../stage2_resume.json`
  - `resume_handoffs/.../stage3_prep.json`
- artifact resume now prefers a saved handoff bundle when it exists and only falls back to reconstructing from `stage2_topk` when the bundle is missing

Why this pivot was necessary:

- the first resumed `seed211` baseline built from reconstructed `stage2_topk` only reached `0.268`
- the real live weak-seed baseline for the same seed is `0.574`
- that made the reconstructed handoff too weak to trust for downstream Stage-3 policy science

Important limitation:

- the existing weak-seed bundles from:
  - `20260324T004559684950Z__bench_solve_pipeline_no_wli__55b7159`
  - `20260324T040609368464Z__bench_solve_pipeline_no_wli__55b7159`
  were written **before** the live-handoff fidelity fix
- their manifests therefore do not yet carry a live-source marker and should be treated as reconstructed-bundle outputs

Validation:

- focused tests:
  - `tests/tools/test_no_wli_artifact_resume.py`
  - `tests/tools/test_no_wli_resume_handoff_artifacts.py`
  - `tests/tools/test_no_wli_truth_diagnostics.py`
  - result: `11 passed`

Next action:

- run one fresh single-seed `seed211` preservation pass with the new bundle writer enabled
- use that fresh live bundle as the baseline source for the resumed Stage-3 policy probe

### 2026-03-24 resumed-probe entrypoint hardening

Phase 7 setup tightened while the fresh `seed211` live-bundle refresh run is active.

Implemented:

- shared probe source-selection helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/resume_probe_utils.py`
- updated Phase 7 entrypoints:
  - `tools/benchmarks/periodic_sub_trans/no_wli/resume_seed211_stage3_policy_probe.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/resume_seed411_phasec_ranking_probe.py`

What changed:

- resumed probe scripts now prefer the latest artifact for the target seed whose resume manifest records:
  - `stage2_to_stage3.source = "live_stage3_pipeline"`
- if no live bundle exists yet, they fall back to the explicit historical artifact path already frozen in the script
- probe summaries now record:
  - source selection reason
  - selected bundle source
  - selected manifest relpath
  - live-bundle candidate count
  - per-variant resume source / bundle dir relpath
- shared checkpoint summarization now reports:
  - best-truth row
  - best-score row
  - anchor row
  - lexical request / threshold-skip / tiebreak totals

Focused tests added:

- `tests/tools/test_no_wli_resume_probe_scripts.py`

Validated with:

- `C:\\Python\\Python311\\python.exe -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/resume_probe_utils.py tools/benchmarks/periodic_sub_trans/no_wli/resume_seed211_stage3_policy_probe.py tools/benchmarks/periodic_sub_trans/no_wli/resume_seed411_phasec_ranking_probe.py tests/tools/test_no_wli_resume_probe_scripts.py`
- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_truth_diagnostics.py -q`
  - `16 passed`

Current state:

- the fresh `v33` live `seed211` refresh run is still active
- therefore:
  - Phase 7B remains in progress pending the new live bundle
  - Phase 7C entrypoint is ready and tested, but no new probe output should be claimed yet

### 2026-03-24 live handoff commit-path fix

The fresh `v33` `seed211` refresh run finished at the same weak `0.574`, but its
resume manifest still reported:

- `stage2_to_stage3.source = "reconstructed_stage2_topk"`

That proved the earlier "live handoff" work had not actually survived the real
iteration commit path.

Root cause:

- `stage3_iteration_flow` was correctly producing:
  - `stage2_resume_live`
  - `stage3_prep_live`
- but the commit bridge was reading the original runner state instead of the
  per-iteration state produced by the matrix flow
- so `write_resume_handoff_artifacts(...)` never saw the live handoff payloads
  and always fell back to reconstruction

Implemented:

- threaded an optional `bridge_state` through the real commit callback chain:
  - `run_manifest_setup.py`
  - `run_progress.py`
  - `run_pipeline_execution.py`
  - `iteration_finalize.py`
  - `iteration_post_stage3.py`
- kept backward compatibility for simple finalize-time stub callbacks that do
  not accept `bridge_state`

Meaningful regression coverage:

- extended `tests/tools/test_no_wli_resume_handoff_artifacts.py` with a real
  callback-path test that exercises:
  - `build_commit_iteration_callback(...)`
  - `commit_iteration_with_checkpoint(...)`
  - `commit_iteration_outputs_bridge(...)`
- the test proves a live per-iteration handoff reaches the emitted bundle
  manifest and writes:
  - `stage2_to_stage3.source = "live_stage3_pipeline"`

Validated with:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_runner_bindings_commit_bridge.py -q`
  - `27 passed`

Current next action:

- rerun one fresh single-seed `seed211` preservation job to confirm a real
  emitted bundle now records:
  - `stage2_to_stage3.source = "live_stage3_pipeline"`
- only after that should the resumed `seed211` Stage-3 policy probe be treated
  as faithful to the live weak-seed handoff

### 2026-03-24 `v34` live refresh setup and resumed scorer path fix

Prepared the next fresh single-seed live confirmation session:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  - `RUN_SEEDS = (211,)`
  - same `stage3_preserve_tieband_probe_p9` preset
  - fresh session files:
    - `fixture_matrix_run_state_tune_v34_p9c3_stage3_preserve_seed211_livebundle.json`
    - `fixture_matrix_run_events_tune_v34_p9c3_stage3_preserve_seed211_livebundle.jsonl`
    - `fixture_matrix_plan_tune_v34_p9c3_stage3_preserve_seed211_livebundle.json`

Also fixed the resumed `seed411` ranking probe failure:

- root cause:
  - replay/resume scorer construction was passing
    `span_hamming_assets_dir = "assets/scoring/..."`
    through without resolving it against the repo root
  - that made resumed probes look under
    `tools/benchmarks/periodic_sub_trans/no_wli/assets/...`
    instead of the actual repo assets directory
- fix:
  - `tools/benchmarks/periodic_sub_trans/no_wli/replay_phasec_rescue_sweep.py`
  - `_build_stage3_scorer_runtime(...)` now resolves
    `span_hamming_assets_dir` with the same repo-root semantics used elsewhere

Meaningful regression added:

- `tests/tools/test_no_wli_artifact_resume.py`
  - verifies `_build_stage3_scorer_runtime(...)` resolves repo-relative
    span-hamming assets before calling `build_scorer(...)`

Validation:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_resume_probe_scripts.py -q`
  - `23 passed`

Operational note:

- an interrupted `seed411` resumed ranking probe process was stopped cleanly
- it left no completed summary output and should be treated as not run

### 2026-03-24 resumed scorer path follow-up and proactive sweep

The first resumed `seed411` IDE-path fix only covered the primary Stage-3 scorer
runtime. A second immediate failure then exposed the same repo-relative-path
problem inside the word-ngram report scorer construction.

Implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/replay_phasec_rescue_sweep.py`
  - `_build_stage3_word_ngram_report_runtime(...)` now resolves:
    - `judge_scorer.span_hamming_assets_dir`
    - word-ngram sqlite paths via the existing repo-root resolver path
- `tools/benchmarks/periodic_sub_trans/no_wli/analyze_phasec_slice_signals.py`
  - `_build_scorer_runtime(...)` now resolves repo-relative
    `span_hamming_assets_dir` before constructing `ScoringConfig(...)`

Meaningful regression coverage:

- `tests/tools/test_no_wli_artifact_resume.py`
  - added a word-ngram runtime path-resolution regression
- `tests/tools/test_no_wli_phasec_slice_signal_analysis.py`
  - added a slice-signal scorer-runtime path-resolution regression

Validated with:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `27 passed`

Operational confirmation:

- a short-start smoke of:
  - `tools/benchmarks/periodic_sub_trans/no_wli/resume_seed411_phasec_ranking_probe.py`
- no longer crashes immediately on startup from IDE-style launch context
- after 20 seconds it was still running and had to be stopped manually, which is
  the expected healthy shape for a real resumed probe rather than an immediate
  repo-relative asset-path failure

### 2026-03-25 resumed Stage-3 scorer leak and commit-bridge crash fixes

Two new real failures were exposed by the fresh resumed/live reruns:

1. `resume_seed411_phasec_ranking_probe.py` still crashed later in the resumed
   Stage-3 path after Phase A / Phase B started running
   - root cause:
     - `artifact_resume.run_stage3_resume_from_artifact(...)` was still handing
       raw repo-relative scorer configs back into the live Stage-3 flow state
     - those configs later reached `run(...)` inside `stage3_two_phase.py`, and
       the scorer builder then looked under
       `tools/benchmarks/periodic_sub_trans/no_wli/assets/...`
2. the fresh live `seed211` rerun crashed at finalize/commit time with:
   - `KeyError: 'base'`
   - root cause:
     - `runner_bridges.commit_iteration_outputs_bridge(...)` still required
       `state["base"]` only to format elapsed time
     - that assumption does not hold on the modern commit-bridge callback path

Implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - added repo-root resolution for scorer-config path fields before pushing
    configs into the resumed Stage-3 flow state:
    - `span_hamming_assets_dir`
    - `word_ngram_judge_sqlite_path`
    - `word_ngram_report_sqlite_path`
    - `sqlite_path`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py`
  - removed the hard dependency on `state["base"]` from
    `commit_iteration_outputs_bridge(...)`
  - added a local time-format fallback for commit/heartbeat logging

Meaningful regression coverage:

- `tests/tools/test_no_wli_artifact_resume.py`
  - resumed Stage-3 flow now proves repo-relative scorer cfg paths are resolved
    before `run_stage3_iteration_flow(...)` sees them
- `tests/tools/test_no_wli_resume_handoff_artifacts.py`
  - commit bridge now proves it can execute without `state["base"]`
    and still format elapsed time correctly

Validated with:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `29 passed`

Operational confirmation:

- the old fresh `seed211` preservation rerun under
  `output/tools/benchmarks/periodic_sub_trans/no_wli/20260325T031806162834Z__bench_solve_pipeline_no_wli__55b7159`
  did complete the live solve path before failing
  - weak result remained unchanged:
    - `stage3_phaseB best_match = 0.581`
    - `stage3_phaseC best_match = 0.574`
  - the failure was at finalize/commit only:
    - `KeyError: 'base'`
- after the `commit_iteration_outputs_bridge(...)` fallback fix, that crash
  class is now covered directly by a regression test
- the currently running repaired `seed411` resumed ranking probe
  (`resume_seed411_phasec_ranking_probe.py`) is still active under load
  - process observed alive after startup with substantial CPU / memory use
  - no completed variant output has been emitted yet, so no new result should
    be claimed until it exits cleanly

### 2026-03-25 cwd-relative offline output-root hardening

While monitoring the live resumed `seed411` probe, a second IDE-only bug class
showed up:

- several offline / replay no-WLI scripts still defined `OUTPUT_ROOT` as a bare
  `Path("output/...")`
- when launched from an IDE with a script-local working directory, those runs
  wrote under:
  - `tools/benchmarks/periodic_sub_trans/no_wli/output/...`
  - instead of the intended repo-root output tree
- this is why the active repaired `seed411` probe first appeared to have no
  output under `output/tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume`

Implemented:

- repo-root anchored `OUTPUT_ROOT` for:
  - `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/analyze_phasec_slice_signals.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/profile_word_ngram_tiebreak.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/replay_phasec_rescue_sweep.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/replay_stage35_substitution_solver.py`

Meaningful regression coverage:

- `tests/tools/test_no_wli_artifact_resume.py`
  - now proves `artifact_resume.OUTPUT_ROOT` is repo-anchored
- `tests/tools/test_no_wli_output_root_paths.py`
  - sweeps the offline no-WLI replay / profiling scripts and proves their
    `OUTPUT_ROOT` values are absolute repo-root paths

Validated with:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_output_root_paths.py -q`
  - `15 passed`

Operational note:

- the currently running `seed411` resumed probe started before this hardening,
  so its live output root is still the mislocated tree:
  - `tools/benchmarks/periodic_sub_trans/no_wli/output/tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume/20260325T145319Z_seed411_phasec_ranking_probe`
- future IDE launches should now land under the correct repo-root output tree

### 2026-03-25 holistic commit-state overlay fix

The next live `seed211` rerun exposed that the commit callback path was still
structurally wrong even after the earlier point fixes:

- first failure:
  - `KeyError: 'base'`
- second failure after that:
  - `KeyError: 'write_json'`

Root cause:

- the commit callback in
  `tools/benchmarks/periodic_sub_trans/no_wli/run_pipeline_execution.py`
  was replacing the full runner state with the sparse per-iteration
  `bridge_state`
- that sparse state is only meant to carry live iteration overlays like:
  - `stage2_resume_live`
  - `stage3_prep_live`
- it is not supposed to replace the runner-wide helpers and services such as:
  - `base`
  - `write_json`
  - summary / hashing / snapshot writers

Implemented:

- added `_resolve_commit_bridge_state(...)` in
  `tools/benchmarks/periodic_sub_trans/no_wli/run_pipeline_execution.py`
- commit-time state now merges:
  - full `runner_state`
  - plus sparse `bridge_state` overrides
- this fixes the bug class holistically instead of chasing missing keys one by
  one inside the bridge

Meaningful regression coverage:

- `tests/tools/test_no_wli_resume_handoff_artifacts.py`
  - the real commit-callback integration test now passes a truly sparse
    per-iteration `bridge_state` and still proves live handoff emission works
  - added a direct merged-state regression for the callback overlay contract

Validated with:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `12 passed`
- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_output_root_paths.py -q`
  - `32 passed`

### 2026-03-25 pipeline hardening review and explicit bridge contract

Hardening follow-up from the recurring live commit failures:

- the merge fix alone still left one structural problem:
  - `iteration_post_stage3.py` was passing the whole mutable iteration
    `state` as `bridge_state`
- that kept the bridge contract too loose and risked future shadowing of runner
  services even after the merge fix

Implemented:

- added explicit bridge helpers in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/commit_bridge_state.py`
- `run_pipeline_execution.py`
  - `_resolve_commit_bridge_state(...)` now delegates to the explicit helper
  - unexpected bridge override keys now fail fast instead of silently
    shadowing runner services
- `iteration_post_stage3.py`
  - now extracts and passes only the live handoff payloads:
    - `stage2_resume_live`
    - `stage3_prep_live`

Meaningful regression coverage:

- `tests/tools/test_no_wli_resume_handoff_artifacts.py`
  - added regression that unexpected bridge override keys are rejected
  - added regression that bridge extraction keeps only the live handoff payloads
  - existing real callback-path live-handoff test remains in place

Validated with:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `14 passed`
- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_output_root_paths.py -q`
  - `34 passed`

Review artifact:

- detailed findings and next-step hardening notes captured in:
  - `planning/working/no_wli_pipeline_hardening_review_2026-03-25.md`

### 2026-03-25 continued pipeline hardening: stage-engine contract, commit services, and batch-scoring contract

Manual pipeline trace continued after the explicit commit-bridge fix.

Additional structural issues found:

- the stage-engine route was still relying on broad state copying
  - `iteration_matrix_flow.py` had already been tightened earlier in the day
  - review continued through the stage-engine / finalize / commit route to
    look for the same bug class elsewhere
- the commit bridge still assumed required runner services existed and were
  callable
  - that meant the next bad state-shape regression would still surface late as
    an opaque `KeyError`
- `iteration_post_stage3.py` still had one last silent fallback:
  - `state.get("REQUIRE_BATCH_SCORING", True)`
  - that was no longer appropriate once the explicit finalize-state builder was
    guaranteed to provide the field

Implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/commit_bridge_state.py`
  - added required commit runner-service validation
  - bridge resolution now fails early if required services are missing or
    non-callable
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - removed the silent default for `REQUIRE_BATCH_SCORING`
  - finalize now treats it as an explicit live-path contract value
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_finalize.py`
  - removed runtime signature inspection around `bridge_state` forwarding
  - callback forwarding is now explicit when a bridge payload is present
- `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_contract.py`
  - narrowed the profile overlay state to the exact stage-spec keys that
    builder needs
  - removed the lower-risk whole-state copy from that path

Meaningful regression coverage added:

- `tests/tools/test_no_wli_resume_handoff_artifacts.py`
  - missing commit runner-service rejection
  - non-callable commit runner-service rejection
- `tests/tools/test_no_wli_iteration_finalize_word_ngram.py`
  - still passes after explicit callback forwarding removed the old reflection
    path
- `tests/tools/test_no_wli_stage_engine_contract.py`
  - added regression that stage2/stage3 override values survive the narrowed
    profile overlay without carrying unrelated state
- existing stage-engine and iteration-matrix contract tests kept in the
  targeted slice

Validated with:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_stage_engine_parity_smoke.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `30 passed`
- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_output_root_paths.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_stage_engine_parity_smoke.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py -q`
  - `50 passed`
- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_output_root_paths.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_stage_engine_parity_smoke.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py -q`
  - `52 passed`
- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_output_root_paths.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_stage_engine_parity_smoke.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_stage_engine_contract.py -q`
  - `57 passed`

Current state at this checkpoint:

- handoff/commit reliability is better defended than before
- the most important remaining live blocker is still fresh end-to-end
  confirmation that the single-seed `seed211` run clears commit and writes the
  live handoff manifest
- solve quality is unchanged; this work is pipeline-hardening, not solve
  improvement

### 2026-03-25 continued pipeline hardening: Stage1/Stage2 contract validation and late-path fail-open removal

Manual review continued through the remaining main live-route layers after the
commit/state fixes.

Additional structural issues found:

- `stage12_pipeline.py` still accepted Stage1/Stage2 return payloads through
  `.get(...)` defaults
  - that meant a missing key could silently degrade into a plausible-looking
    empty value and only fail much later
- `iteration_pre_stage3.py` mirrored the same permissive defaults after
  Stage1/Stage2 had already completed
- `run_progress.py` silently ignored unknown `status_key` values during manifest
  checkpointing
- `stage_iteration_commit.py` still tolerated missing late-path fields by using
  `.get(...)` fallbacks on required instance/artifact payload values

Implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage12_pipeline.py`
  - added explicit required-key validation for:
    - `run_stage1_substitution_fn`
    - `run_stage2_search_fn`
    - `finalize_stage2_archive_fn`
  - added basic shape validation for required list/mapping payload fields
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_pre_stage3.py`
  - removed mirrored Stage1/Stage2 `.get(...)` fallbacks
  - pre-stage3 now consumes the validated Stage12 payload by explicit keys
- `tools/benchmarks/periodic_sub_trans/no_wli/run_progress.py`
  - unknown status keys now raise early instead of being dropped silently
- `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_commit.py`
  - required artifact and instance fields now use explicit key access

Meaningful regression coverage added:

- `tests/tools/test_no_wli_stage12_pipeline.py`
  - happy-path Stage12 contract
  - missing Stage1 key rejection
  - missing Stage2 search key rejection
  - wrong Stage2 search archive shape rejection
  - missing Stage2 finalize key rejection
- `tests/tools/test_no_wli_stage_iteration_commit.py`
  - missing `profile_id` rejection in the late commit path
- `tests/tools/test_no_wli_oracle_contract.py`
  - unknown status-key rejection in checkpoint manifest accounting

Validated with:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_stage12_pipeline.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_output_root_paths.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_stage_engine_parity_smoke.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_stage_engine_contract.py -q`
  - `62 passed`
- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_stage12_pipeline.py tests/tools/test_no_wli_stage_iteration_commit.py tests/tools/test_no_wli_oracle_contract.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_output_root_paths.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_stage_engine_parity_smoke.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_stage_engine_contract.py tests/tools/test_no_wli_run_completion.py -q`
  - `70 passed`

Current state at this checkpoint:

- main live-route review now covers:
  - startup
  - pre-stage3
  - Stage1 / Stage2
  - Stage3
  - finalize
  - commit
  - handoff emission
- not every sidecar helper in the tree has been exhaustively reviewed yet
- the remaining decisive proof step is still a fresh live canary run started
  after the newest hardening edits are loaded

### 2026-03-25 continued pipeline hardening: preset validation and summary/completion contracts

Manual review continued beyond the main live stage route into orchestration and
reporting layers.

Additional structural issues found:

- `fixture_matrix_api.py` silently treated an unknown non-`base`
  `stage3_tuning_preset_id` as an empty preset
  - this could waste a whole matrix run while looking valid
- `run_summary.py` still summarized live instance rows through permissive
  `.get(...)` access even though instance rows are now strongly shaped
- `run_completion.py` still treated live best-row fields and status-count keys
  as optional even though they are part of the in-process contract

Implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - unknown non-`base` Stage-3 tuning preset IDs now raise early in both:
    - `resolve_stage3_tuning_preset_ids()`
    - `_resolve_stage3_tuning_overrides_for_job(...)`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_summary.py`
  - live summary rows now use explicit required fields
- `tools/benchmarks/periodic_sub_trans/no_wli/run_completion.py`
  - completion path now treats live best-row fields and status-count keys as
    required

Meaningful regression coverage added:

- `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - unknown preset-id rejection
- `tests/tools/test_no_wli_run_summary.py`
  - internal live summary contract
- `tests/tools/test_no_wli_run_completion.py`
  - incomplete status-count rejection

Validated with:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_run_summary.py tests/tools/test_no_wli_run_completion.py tests/tools/test_no_wli_stage12_pipeline.py tests/tools/test_no_wli_stage_iteration_commit.py tests/tools/test_no_wli_oracle_contract.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_resume_probe_scripts.py tests/tools/test_no_wli_phasec_slice_signal_analysis.py tests/tools/test_no_wli_output_root_paths.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_stage_engine_parity_smoke.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_stage_engine_contract.py -q`
  - `75 passed`

Current state at this checkpoint:

- the main live route is covered
- several major sidecar/orchestration fail-open paths are now covered too
- the currently running live canary is still useful operationally, but it still
  does not validate the newest hardening batch because it started earlier

### 2026-03-25 continued pipeline hardening: runner-service contract and defaulted Stage-3 config removal

Cross-checking continued through the runner/binding layer and the remaining
central config materialization paths.

Additional structural issues found:

- commit formatting still relied on a hidden fallback inside
  `runner_bridges.py` if `_format_seconds` was absent
- several central live-path config readers still used permissive `.get(...)`
  defaults even though those keys are installed by runner defaults and should be
  treated as part of the state contract:
  - Phase-C config
  - Stage35 config
  - word-ngram decision/report config
  - span-aux config
  - resume-handoff enablement at commit

Implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/runner_bindings.py`
  - `_format_seconds` is now installed explicitly as a runner service
- `tools/benchmarks/periodic_sub_trans/no_wli/commit_bridge_state.py`
  - commit validation now requires:
    - callable `_format_seconds`
    - explicit `SAVE_RESUME_HANDOFFS`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py`
  - removed the last internal formatting fallback
  - Phase-C runtime call-context keys now use explicit runner-state access
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_builder.py`
  - span-aux / Stage35 config now uses explicit runner-state access
- `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
  - run-config emission no longer silently fabricates Phase-C / Stage35 /
    word-ngram / span-aux values
- `tools/benchmarks/periodic_sub_trans/no_wli/setup_logging_payload.py`
  - setup logging payload now uses explicit Phase-C / Stage35 keys
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  - Stage35 enablement/config now uses explicit state access on the live path

Meaningful regression coverage added:

- `tests/tools/test_no_wli_runner_bindings_commit_bridge.py`
  - `_format_seconds` binding is installed on the real runner module
- `tests/tools/test_no_wli_resume_handoff_artifacts.py`
  - commit bridge uses the runner formatting service
  - missing commit runner-value rejection
- `tests/tools/test_no_wli_run_config_span_aux.py`
  - run-config builder now fails fast when required span-aux / Phase-C keys are
    absent

Validated with:

- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_runner_bindings_commit_bridge.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_setup_logging.py -q`
  - `15 passed`
- `C:\\Python\\Python311\\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_setup_logging.py tests/tools/test_no_wli_resume_handoff_artifacts.py tests/tools/test_no_wli_runner_bindings_commit_bridge.py -q`
  - `49 passed`

Current state at this checkpoint:

- the runner/binding layer is stricter than before and less likely to hide a
  broken state shape behind fallback behavior
- the main remaining soft contract is inside `stage3_iteration_flow.py` helper
  return payloads (`stage3_prep`, `two_phase_followup`, `stage35_followup`)
- the already-running live canary is still active and still not a proof of this
  latest batch because it started earlier

### 2026-03-25 overnight live matrix setup: weak-seed downstream comparison

Prepared the next live overnight matrix in:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

Bounded design:

- keep `p9/c3` only
- weak hard seeds only:
  - `211`
  - `411`
- targeted preset lanes:
  - `stage3_preserve_tieband_probe_p9`
  - `stage3_recovery_p9_8h`
  - `stage35_proof_p9_8h`
  - `lexical_phasec_proof_wide`
  - `lexical_phasec_rescue_wide_finish`
- `STOP_ON_ERROR = False`
- `MAX_JOBS = None`
- `MAX_WALLCLOCK_SECONDS = 36000.0`

Expected materialized scope:

- `1 fixture x 1 period x 1 columns x 2 seeds x 5 presets x 1 schedule = 10 jobs`

Fresh run-state artifacts configured:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v35_p9c3_weakseed_overnight_10h.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v35_p9c3_weakseed_overnight_10h.jsonl`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v35_p9c3_weakseed_overnight_10h.json`

Cheap materialization validation passed:

- `job_count = 10`
- `seeds = [211, 411]`
- preset ids resolved as configured

### 2026-03-26 science log and short follow-up lane

Created canonical science log:

- `planning/working/no_wli_science_run_log_2026-03-26.md`

Created external review pack:

- `planning/working/no_wli_external_review_pack_2026-03-26/`

The science log backfills, with concrete artifact evidence:

- the successful live handoff-emission canary
- the negative fixed-handoff `seed411` lexical ranking probe
- the first three completed jobs from the broad weak-seed overnight matrix

Next live follow-up lane is intentionally reduced to two jobs:

- seed:
  - `411`
- presets:
  - `stage3_preserve_tieband_probe_p9`
  - `lexical_phasec_rescue_wide_finish`

The external review pack packages the current state, the recent evidence
timeline, the reliability work, and the explicit outside-review questions into
one review-first folder while also snapshotting the current working docs.

Why this reduction was made:

- the broad overnight batch proved too slow for useful iteration
- the batch stopped after three `seed211` jobs and never reached `seed411`
- `seed211` already ruled out the practical value of:
  - preserve-only lift
  - wider recovery as configured
  - Stage-3.5 as a short-cycle default lane

### 2026-03-27 reviewer-driven Stage-3 cross-check

The latest reviewer pass did not identify one trivial bug. The strongest
verified addition is a structural concern around how Stage-3 families are
entered, ranked, and collapsed.

Confirmed from code:

- Stage-3 entry dilution mechanism is real:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_seeding.py`
  - lines `50-95`
  - `per_seed = ceil(init3_n / len(promoted_keys))`, then all mutated descendants
    are deduped and truncated back to `init3_n`
- Phase-A basin-judge pool is pre-ranked on search-side metrics before judged pct
  scoring:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - lines `330-355`
- Phase-B family selection is still pct-first:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - lines `754-817`
  - `end_score_pct` leads the ranking key
  - `end_score_raw` is later in the key
  - tie-band widening is also around `end_score_pct`
- The avg/full-text profile defaults do pair wider Stage-3 / Stage-2 promotion
  budgets with raw-score-led Stage-3 solve:
  - `tools/benchmarks/config/no_wli_pipeline_profiles.py`
  - lines `242-306`
  - fields:
    - `stage3_initial_keys = 64`
    - `stage12_archive_keep = 192`
    - `stage12_promote_top = 96`
    - `solver_stage3["use_raw_score"] = True`

Important nuance:

- those widened profile defaults are real, but live preset configs can override
  some of them
- the active v36 compare should therefore be interpreted as a multi-knob live
  package, not as a pure readout of base profile defaults

Telemetry/save-path clarification:

- the one-row `phaseB_topk_saved_count` weak-run case is not yet evidence of a
  summary/save bug by itself
- current Kaeding top-k telemetry records only candidates that become new global
  raw-score bests:
  - `src/rune_decrypter_prime/solvers/kaeding_periodic_structured.py`
  - lines `317-338`, `601-605`
- the saved weak-run artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260322T192204224097Z__bench_solve_pipeline_no_wli__55b7159/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed211.json`
  - shows:
    - `phaseB_top_n_used = 8`
    - `phaseB_selected_unique_end_hash = 8`
    - `phaseB_topk_saved_count = 1`

Working implication:

- the current best-supported design-risk hypothesis is now:
  - weak-seed families may be underfed at Stage-3 entry
  - then collapsed too early by Phase-B selection on a score surface that is not
    fully aligned with the inner Stage-3 solve objective

Still unverified:

- exact survival of distinct Phase-B families into Phase-C starts and Stage-3.5
  seed construction

### 2026-03-27 v36 short `seed411` compare result

The reduced two-job live compare is now complete.

Verified from run control files:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v36_p9c3_seed411_phasec_compare_2job.json`
  - `completed_jobs = 2`
  - `remaining_jobs = 0`
  - `stopped_early = 0`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v36_p9c3_seed411_phasec_compare_2job.jsonl`
  - control runtime about `16628.888` seconds
  - broader candidate runtime about `25767.437` seconds

Results:

- control run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T044057282813Z__bench_solve_pipeline_no_wli__55b7159/instances.json`
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`
- broader candidate run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T091806220616Z__bench_solve_pipeline_no_wli__55b7159/instances.json`
  - `best_stage = "stage3_full_refine"`
  - `best_match_ratio = 0.046`
  - `stage3_match_ratio = 0.046`

Important interpretation detail:

- the broader candidate did improve on live `seed411`, but only slightly
- that candidate also widened late-family breadth materially:
  - control best artifact:
    - `phaseB_selected_unique_end_hash = 8`
    - `phaseC_candidate_pool_unique_end_hash = 8`
  - broader candidate best artifact:
    - `phaseB_selected_unique_end_hash = 32`
    - `phaseC_candidate_pool_unique_end_hash = 32`
- however, explicit rescue did not actually activate:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260327T091806220616Z__bench_solve_pipeline_no_wli__55b7159/stages.json`
  - `phaseC_rescue_enabled = 1`
  - `phaseC_rescue_ran = 0`
  - `phaseC_rescue_eligible_starts = 0`

Working implication:

- downstream breadth is not a total dead end on `seed411`
- but the result is too weak to justify a "keep widening rescue" strategy by
  default
- the better interpretation is that family width / family survival still looks
  more promising than rescue activation itself

### 2026-03-27 Study 1 implementation: explicit constant-local-depth Stage-3 entry

Work completed:

- implemented explicit Stage-3 entry policy selection in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_seeding.py`
- propagated new entry diagnostics into the live stop-line and final Stage-3
  diagnostics in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- added explicit defaults in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runtime_defaults.py`
  - `tools/benchmarks/config/no_wli_pipeline_profiles.py`
- added preset forwarding for:
  - `force_stage3_init_keys_cap`
  - explicit Stage-3 entry controls:
    - `force_stage3_entry_allocation_policy`
    - `force_stage3_entry_mutations_per_promoted`
  - real Kaeding solver overrides via `force_solver_stage3_overrides`
  in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`

Implemented policy surface:

- legacy baseline remains default:
  - `entry_allocation_policy = "legacy_fixed_budget"`
- Study 1 policy added:
  - `entry_allocation_policy = "constant_local_depth"`
- explicit local-depth knob:
  - `entry_mutations_per_promoted`
- explicit telemetry now emitted:
  - `stage3_entry_allocation_policy`
  - `stage3_entry_base_budget`
  - `stage3_entry_target_before_cap`
  - `stage3_entry_cap`
  - `stage3_entry_cap_applied`
  - `stage3_entry_mutations_per_promoted_cfg`
  - `stage3_entry_mutation_calls_per_promoted`

Interpretation of the new policy:

- legacy mode keeps the old fixed-budget clustered expansion path
- constant-local-depth mode:
  - preserves one seed row per promoted family first
  - adds mutations in round-robin family order
  - scales target Stage-3 entry width up before cap so broader promoted pools
    do not silently collapse back toward the old narrow entry target

Prepared next live compare:

- active matrix config is now:
  - `seed = 211`
  - presets:
    - `stage3_preserve_tieband_probe_p9`
    - `stage3_entry_const_local_depth_p9`
- control files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v37_p9c3_seed211_stage3_entry_compare_2job.jsonl`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`

Candidate preset intent:

- preset:
  - `stage3_entry_const_local_depth_p9`
- keep baseline lane otherwise stable
- only meaningful entry-side changes:
  - `force_stage3_init_keys_cap = 288`
  - `force_stage3_entry_allocation_policy = "constant_local_depth"`
  - `force_stage3_entry_mutations_per_promoted = 1`

Short validation completed:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_seeding.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py tests/tools/test_no_wli_resume_handoff_artifacts.py -q`
  - `78 passed`
- materialized active config confirms:
  - `job_count = 2`
  - `run_seeds = [211, 211]`
  - `preset_ids = ["stage3_preserve_tieband_probe_p9", "stage3_entry_const_local_depth_p9"]`

Meaningful coverage added:

- `tests/tools/test_no_wli_stage3_seeding.py`
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`
- `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py`

Current status:

- Study 1 implementation is ready for user-run live evaluation
- no live solve claim is made yet
- next decision depends on the long-run `seed211` control vs constant-local-depth
  compare

### 2026-03-27 Study 1 live run started and readout plan

Run-start evidence:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`
  - `completed_jobs = 0`
  - `remaining_jobs = 2`
  - `started_utc = 2026-03-28T00:50:34.858013+00:00`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v37_p9c3_seed211_stage3_entry_compare_2job.jsonl`
  - first `job_started` event confirms:
    - preset `stage3_preserve_tieband_probe_p9`
    - `total = 2`

Readout plan prepared:

- `planning/working/no_wli_study1_readout_checklist_2026-03-27.md`

Why the checklist exists:

- avoid hand-wavy interpretation once the run finishes
- force explicit verification that Study 1 actually widened Stage-3 entry
- keep the final decision tied to:
  - `stage3_entry_target_before_cap`
  - `init3_n`
  - `stage2_to_stage3.stage3_init3_count`
  - `best_match_ratio`
  - `stage3_match_ratio`

### 2026-03-27 Study 1 first launch failed fast on runtime-config leakage

Observed failure:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`
  - `completed_jobs = 0`
  - `stopped_early = 1`
  - `last_error.error_type = "ValueError"`
  - `last_error.error = "Unknown kaeding parameter(s): entry_allocation_policy, entry_mutations_per_promoted ..."`
- matching event row in:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v37_p9c3_seed211_stage3_entry_compare_2job.jsonl`

Root cause:

- Study 1 introduced two new Stage-3 seeding controls:
  - `entry_allocation_policy`
  - `entry_mutations_per_promoted`
- those controls were being parsed correctly by the Stage-3 seeding layer
- but they were also leaking into the downstream Kaeding runtime solver config,
  which validates its allowed parameter set strictly

Fix:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_seeding.py`
  now strips Stage-3 entry-only keys before returning `solver_stage3_cfg`
  downstream
- the scientific telemetry stays intact via separate Stage-3 entry fields

Meaningful validation:

- `tests/tools/test_no_wli_stage3_seeding.py`
  now proves the emitted `solver_stage3_cfg` is accepted by
  `SolverSpec.kaeding(...)`
- focused slice after the fix:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_seeding.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py -q`
  - `68 passed`

Operational note:

- the failed first launch is not evidence for or against Study 1 scientifically
- rerunning the same matrix command is valid because
  `fixture_matrix_runtime.py` only resumes from `completed_job_keys`, which are
  still empty in this failed-start case

### 2026-03-27 Study 1 runtime-config split completed and canary now proves the path

Cross-checked rerun evidence:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v37_p9c3_seed211_stage3_entry_compare_2job.json`
  - `completed_jobs = 0`
  - `remaining_jobs = 0`
  - `stopped_early = 0`
  - `completed_utc = 2026-03-28T00:57:26.311066+00:00`
  - `last_error.error_type = "ValueError"`
  - `last_error.error = "Unknown kaeding parameter(s): entry_allocation_policy, entry_mutations_per_promoted ..."`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v37_p9c3_seed211_stage3_entry_compare_2job.jsonl`
  - job 1 control failed with the same unknown-parameter error
  - job 2 candidate failed with the same unknown-parameter error

Revised root cause:

- the first patch was incomplete
- Study 1 entry controls were still stored inside the canonical
  `SOLVER_STAGE3` runtime config surface
- this meant the control path could fail too, proving the leak was structural
  rather than candidate-only

Architectural correction:

- split Study 1 entry controls out of `SOLVER_STAGE3` entirely
- explicit runtime state now carries:
  - `STAGE3_ENTRY_ALLOCATION_POLICY`
  - `STAGE3_ENTRY_MUTATIONS_PER_PROMOTED`
- live and resume config surfaces now carry:
  - `stage3.entry`
  - `stage3_search.entry`
- `SOLVER_STAGE3` is again reserved for real Kaeding runtime parameters only

Files updated in the correction:

- `tools/benchmarks/periodic_sub_trans/no_wli/runtime_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/profile_defaults.py`
- `tools/benchmarks/config/no_wli_pipeline_profiles.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_seeding.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_lock_payload.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

Meaningful canary now added:

- `tests/tools/test_no_wli_stage3_entry_canary.py`
  - preset resolution
  - job application
  - run-config build
  - non-scoring lock payload
  - Stage-3 prep bridge
  - real `SolverSpec.kaeding(...)` acceptance check on emitted
    `solver_stage3_cfg`

Focused proof slice:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_entry_canary.py tests/tools/test_no_wli_stage3_seeding.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py -q`
  - `83 passed`

Current decision:

- do not interpret the failed v37 reruns scientifically
- treat the new canary as the required short proof before the next user-run
  long compare

Planning follow-up:

- next-stage implementation plan recorded in:
  - `planning/working/no_wli_next_phase_implementation_plan_2026-03-27.md`
- implementation order remains:
  1. Study 1 readout closure
  2. isolated Study 3 Phase-C start balancing
  3. Study 2 Phase-B family preservation only after Study 3

### 2026-03-28 Study 1 readout closed: widened entry, no solve movement

Completed live runs:

- control:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T013131043374Z__bench_solve_pipeline_no_wli__55b7159`
- candidate:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T050751414997Z__bench_solve_pipeline_no_wli__55b7159`

Execution proof:

- control Stage-3 prep:
  - `stage3_entry_allocation_policy = "legacy_fixed_budget"`
  - `stage3_entry_target_before_cap = 64`
  - `init3_n = 64`
- candidate Stage-3 prep:
  - `stage3_entry_allocation_policy = "constant_local_depth"`
  - `stage3_entry_target_before_cap = 288`
  - `init3_n = 288`

Live handoff counts:

- control:
  - `stage2_promoted_from_topk_count = 144`
  - `stage3_init3_count = 64`
- candidate:
  - `stage2_promoted_from_topk_count = 144`
  - `stage3_init3_count = 144`

Outcome:

- control:
  - `best_stage = "stage3_full_refine"`
  - `best_match_ratio = 0.574`
  - `stage3_match_ratio = 0.574`
- candidate:
  - `best_stage = "stage3_full_refine"`
  - `best_match_ratio = 0.574`
  - `stage3_match_ratio = 0.574`

Downstream counters also stayed unchanged:

- `phaseB_selected_unique_end_hash = 8`
- `phaseC_candidate_pool_unique_end_hash = 8`
- `phaseC_start_keys_used = 6`
- identical `phaseC_candidate_pool_source_counts`
- identical `phaseC_start_source_counts`

Decision:

- Study 1 is now closed as a valid negative result on `seed211`
- constant-local-depth entry is proven to execute correctly
- but widening Stage-3 entry alone did not move solve quality here
- this strengthens the current `211` interpretation:
  - likely more `good_family_absent` than simple entry-depth starvation
- next implementation priority remains:
  - isolated Study 3 Phase-C start balancing

### 2026-03-28 Study 3 implementation ready: isolated Phase-C start balancing

Why this is the next study:

- Study 1 completed correctly and returned a valid negative on `seed211`
- current working split remains:
  - `211`:
    - mainly upstream reach / `good_family_absent`
  - `411`:
    - mainly downstream exploitation / `good_family_undervalued`
- Study 3 is the narrowest next intervention that targets the currently
  observed late-family-width / exploited-variety bottleneck without rewriting
  Phase-B policy

Exact hypothesis:

- if the `seed411` Phase-C candidate pool already contains more useful
  variety than is actually explored, then balancing Phase-C starts across
  surviving sources should improve exploited variety and may improve
  `best_match_ratio` without changing Phase-B ranking or rescue logic

Implementation boundary now in code:

- new runtime/config surface:
  - `STAGE3_PHASEC_START_POLICY`
- supported policies:
  - `source_order`
  - `balanced_sources_v1`
- v1 scope:
  - candidate pool unchanged
  - only `start_records` ordering / selection changes
  - anchor remains first
  - then remaining starts are balanced across `phaseB_topk` and
    `phaseA_selected` while preserving within-source order

Evidence-backed proof before user long run:

- deterministic behavior test:
  - `tests/tools/test_no_wli_stage3_phasec.py`
- config / bridge / lock canary:
  - `tests/tools/test_no_wli_phasec_start_policy_canary.py`
- focused proof slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_artifact_resume.py -q`
  - outcome:
    - `42 passed`
- combined guard slice with prior Study 1 canary:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_entry_canary.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_artifact_resume.py -q`
  - outcome:
    - `43 passed`

Prepared live compare for the user:

- seed:
  - `411`
- control:
  - `stage3_preserve_tieband_probe_p9`
- candidate:
  - `stage3_phasec_start_balanced_p9`
- matrix control files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v38_p9c3_seed411_phasec_start_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v38_p9c3_seed411_phasec_start_compare_2job.jsonl`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v38_p9c3_seed411_phasec_start_compare_2job.json`

Primary readouts to inspect after the user run:

- `phaseC_start_policy`
- `phaseC_candidate_pool_source_counts`
- `phaseC_start_source_counts`
- `phaseC_start_keys_used`
- `phaseC_start_unique_end_hash`
- `phaseC_final_winner_source`
- `best_match_ratio`
- `stage3_match_ratio`

Interpretation guide:

- valid positive:
  - `phaseC_start_source_counts` rebalance
  - exploited variety rises
  - solve improves
- valid negative:
  - starts rebalance as intended
  - pool stays constant
  - solve does not improve
- invalid result:
  - candidate pool changed unexpectedly
  - rescue behavior changed unexpectedly
  - Phase-B ranking changed unexpectedly

### 2026-03-28 Study 3 readout closed: valid negative on `seed411`

Execution validity:

- control run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T174120032623Z__bench_solve_pipeline_no_wli__55b7159`
- candidate run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260328T211041031812Z__bench_solve_pipeline_no_wli__55b7159`
- run-config diff confirms the only intended semantic change was:
  - `stage3.two_phase.phase_c.start_policy`
    - `source_order` -> `balanced_sources_v1`

Outcome:

- top-level solve result unchanged:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`
- Phase-C pool stayed the same, as intended:
  - `phaseC_candidate_pool_count = 10`
  - `phaseC_candidate_pool_unique_end_hash = 8`
  - `phaseC_candidate_pool_source_counts = { "stage3_best_phaseB": 1, "phaseB_topk": 1, "phaseA_selected": 8 }`
- Phase-C starts also stayed the same:
  - `phaseC_start_keys_used = 6`
  - `phaseC_start_unique_end_hash = 6`
  - `phaseC_start_source_counts = { "stage3_best_phaseB": 1, "phaseA_selected": 5 }`
  - same six `candidate_hash` values in both `phasec_start_checkpoints.jsonl`

Conclusion:

- this closes Study 3 as a valid negative on `seed411`
- Phase-C start balancing alone is not enough under the current Phase-B output
- more specifically:
  - the candidate pool nominally carried a `phaseB_topk` source row
  - but no additional distinct `phaseB_topk` start survived into the actual
    Phase-C starts
- so the next bottleneck is now better localized:
  - not Phase-C ordering by itself
  - but earlier downstream preservation of distinct families before / into
    Phase-C starts

Updated next priority:

- Study 2 should now move up as the next implementation target:
  - Phase-B family preservation / family-aware downstream slot retention on
    `seed411`
- current recommended order becomes:
  1. Study 1 closed as valid negative on `211`
  2. Study 3 closed as valid negative on `411`
  3. implement Study 2 next
  4. only then consider more upstream basin-generation work for `411`
- Study 2 implementation brief:
  - `planning/working/no_wli_study2_phaseb_preservation_plan_2026-03-28.md`
- locked experiment specs:
  - `planning/working/no_wli_locked_experiment_specs_2026-03-28.md`

### 2026-03-28 Study 2 implementation and canary status

Study 2 is now implemented as an isolated downstream carry-forward policy.

What is intentionally unchanged:

- ordinary Phase-B ranking order
- ordinary Phase-B selected row count
- Phase-B run seeds
- Phase-C rescue logic

What is new:

- explicit Study 2 runtime/config surface:
  - `phaseb_family_preservation_policy`
  - `phaseb_family_view_id`
  - `phaseb_family_reserved_slots`
- shared family-view helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/family_views.py`
- v1 policy:
  - `reserve_by_family_v1`
  - `prefix_hamming_le_24`
  - `reserved_slots = 2`

Canary standard met before any long run:

- focused slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - outcome:
    - `30 passed`
- broader meaningful slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py -q`
  - outcome:
    - `95 passed`

Important proof note:

- the first Study 2 proof attempt surfaced:
  - one real runner import omission
  - one synthetic test family-view mistake
- both were fixed before this status was accepted

Next long compare to hand off:

- seed:
  - `411`
- control:
  - `stage3_preserve_tieband_probe_p9`
- candidate:
  - `stage3_phaseb_family_preserve_p9`
- control files:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v39_p9c3_seed411_phaseb_family_compare_2job.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v39_p9c3_seed411_phaseb_family_compare_2job.jsonl`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v39_p9c3_seed411_phaseb_family_compare_2job.json`

Readout target:

- decide whether preserving more distinct Phase-B families actually increases:
  - downstream family telemetry
  - Phase-C candidate/start diversity
  - `best_match_ratio` on `seed411`

### 2026-03-29 Study 2 live readout status: provisional negative, persistence gap found

The first v39 Study 2 compare completed cleanly but exposed a telemetry
integrity gap.

What the completed run showed:

- control run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T020350857797Z__bench_solve_pipeline_no_wli__55b7159`
- candidate run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T060445115113Z__bench_solve_pipeline_no_wli__55b7159`
- config delta was correct:
  - control family preservation:
    - `policy = "off"`
  - candidate family preservation:
    - `policy = "reserve_by_family_v1"`
    - `family_view_id = "prefix_hamming_le_24"`
    - `reserved_slots = 2`
- visible outcome was unchanged:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`
  - identical visible Phase-C pool and start counts
  - identical `phasec_start_checkpoints.jsonl` start hashes and ordering

Why this is not fully lockable yet:

- the Study 2 family-preservation telemetry did not persist into:
  - `best/best_instance.json`
  - `stages.json`
- so the record cannot yet prove whether:
  - reservation never applied
  - or reservation applied but later collapsed before the visible Phase-C
    readouts

Current status:

- operationally:
  - looks negative
- scientifically:
  - still incomplete under the repository's current evidence standard

Updated next step:

1. patch persistence of Study 2 family telemetry into the saved artifact path
2. rerun the same v39 `seed411` compare
3. only then decide whether Study 2 is a valid negative or a valid positive

### 2026-03-29 Study 2 telemetry persistence patch complete

The missing-telemetry suspicion was correct.

Confirmed bug:

- Study 2 family-preservation fields were returned by the Stage-3 two-phase
  runtime but were not preserved through the iteration-state ->
  diagnostics -> saved-artifact path

Patched files:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`

Regression proof added:

- `tests/tools/test_no_wli_truth_diagnostics.py`
- `tests/tools/test_no_wli_stage35_substitution_solver.py`

Post-fix proof slice:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_stage35_substitution_solver.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_artifact_resume.py -q`
  - `56 passed`

Operational consequence:

- rerun the same v39 `seed411` compare
- do not change the science configuration
- only after that rerun should Study 2 be judged

### 2026-03-29 Study 2 rerun re-armed on fresh control files

The first post-fix rerun attempt resumed immediately because the active
fixture-matrix config still referenced the completed v39 state/event/plan
files.

Current rerun target is unchanged:

- seed:
  - `411`
- control preset:
  - `stage3_preserve_tieband_probe_p9`
- candidate preset:
  - `stage3_phaseb_family_preserve_p9`

Only the control-file paths were refreshed:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v40_p9c3_seed411_phaseb_family_compare_2job_rerun.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v40_p9c3_seed411_phaseb_family_compare_2job_rerun.jsonl`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v40_p9c3_seed411_phaseb_family_compare_2job_rerun.json`

Intent:

- rerun the exact same Study 2 live compare after the telemetry persistence fix
- keep the science configuration unchanged
- use the rerun as the final Study 2 judgment point

### 2026-03-29 Study 2 closed as a valid negative

The v40 rerun locked the Study 2 judgment.

Evidence:

- control run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T155853670179Z__bench_solve_pipeline_no_wli__55b7159`
- candidate run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260329T204310438057Z__bench_solve_pipeline_no_wli__55b7159`
- top-level result was unchanged:
  - `best_stage = "stage2_search"`
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`
- persisted family-preservation telemetry showed:
  - control:
    - `policy = "off"`
    - `phaseB_family_count_in_top_band = 8`
    - `phaseB_downstream_selected_count = 8`
    - `phaseB_downstream_selected_unique_end_hash = 8`
  - candidate:
    - `policy = "reserve_by_family_v1"`
    - `phaseB_family_reserved_slots = 2`
    - `phaseB_family_reservation_applied = 1`
    - `phaseB_family_count_in_top_band = 8`
    - `phaseB_downstream_selected_count = 8`
    - `phaseB_downstream_selected_unique_end_hash = 8`
- visible late-stage outputs also remained unchanged:
  - `phaseB_selected_unique_end_hash = 8`
  - `phaseC_candidate_pool_unique_end_hash = 8`
  - `phaseC_start_keys_used = 6`
  - identical `phasec_start_checkpoints.jsonl`

Current reading:

- the Study 2 policy fired
- but it was a no-op on the carried downstream set
- therefore preserving families inside the current top-8 band is not the
  active bottleneck on `seed411`
- the next clean target is the width or valuation of the Phase-B band itself

Next prepared test:

- v41 `seed411` control-vs-candidate compare
- control preset:
  - `stage3_preserve_tieband_probe_p9`
- candidate preset:
  - `stage3_phaseb_width_probe_p9`
- intended semantic change:
  - widen `force_stage3_phaseb_top_n` from `8` to `32`

### 2026-03-30 v41 width probe invalidated by accelerator failure

The first width-probe long run did not yield a candidate readout.

Evidence:

- state file:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v41_p9c3_seed411_phaseb_width_compare_2job.json`
- events file:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v41_p9c3_seed411_phaseb_width_compare_2job.jsonl`
- control run completed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260330T034031451631Z__bench_solve_pipeline_no_wli__55b7159`
- candidate run failed after about `58.9s`:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260330T085228874213Z__bench_solve_pipeline_no_wli__55b7159`
  - `error_type = "AcceleratorError"`
  - `error = "CUDA error: unknown error"`

Why this is not a science result:

- the candidate never wrote pipeline progress
- no `instances.json`, `stages.json`, or Phase-C checkpoints were produced
- the failure happened before evidence collection began

Additional sanity check:

- immediate local CUDA smoke test succeeded after the failure
- current working assumption is runtime/accelerator loss rather than a proven
  semantic width-policy bug

Next action:

- rerun the exact same width compare on fresh control files
- active rerun files are now:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v42_p9c3_seed411_phaseb_width_compare_2job_rerun.json`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v42_p9c3_seed411_phaseb_width_compare_2job_rerun.jsonl`
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v42_p9c3_seed411_phaseb_width_compare_2job_rerun.json`

### 2026-03-30 pipeline hardening backlog added

While the v42 width compare is running, a concrete hardening backlog has been
added:

- `planning/working/no_wli_pipeline_hardening_backlog_2026-03-30.md`

Why this matters:

- recent science work produced valid negatives, but also exposed recurring
  reliability classes:
  - shared mutable config/state bags
  - incomplete telemetry persistence
  - stale rerun control files
  - runtime/accelerator invalidations

Locked hardening direction:

- do not try to fix "all bugs" at once
- first harden the experiment loop so finished long runs are trustworthy
- preferred architecture is several typed layers, not one mega-dataclass:
  - matrix config
  - control-file identity object
  - typed Stage-3 tuning preset
  - resolved run config
  - runner services
  - narrow stage-boundary payloads

Highest-priority phases:

1. runtime preflight
2. matrix config spine
3. rerun hygiene
4. preset typing
5. stage-boundary payload hardening
6. diagnostics persistence unification

This is planning-only for now and does not alter the active v42 run.

### 2026-03-30 hardening progress: first slice landed

The first backlog slice is now implemented and proven.

Implemented:

- runtime preflight boundary
- matrix config spine entry cleanup
- single experiment-id derived control files
- experiment identity persistence into:
  - plan payload
  - run-state metadata

Concrete code surfaces:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runtime_preflight.py`

Meaningful proof:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_runtime_preflight.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `25 passed`
- broader guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_runtime_preflight.py -q`
  - `35 passed`

Integrity consequence:

- future long compares will no longer rely on `globals()` as the matrix-entry
  config bag
- future control files are tied to one explicit experiment id instead of three
  separate path literals
- a poisoned torch/CUDA path can now fail before job execution rather than only
  after spending time inside a candidate run

Still open from the backlog:

- typed tuning preset schema
- resolved runtime-config object
- broader boundary-payload typing
- diagnostics persistence unification
- stronger stale-rerun detection beyond single-id path derivation

### 2026-03-30 v42 width probe interpretation

The v42 rerun finished correctly and is a valid science readout.

Evidence:

- state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v42_p9c3_seed411_phaseb_width_compare_2job_rerun.json`
- events:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v42_p9c3_seed411_phaseb_width_compare_2job_rerun.jsonl`
- control:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260330T150529396668Z__bench_solve_pipeline_no_wli__55b7159`
- candidate:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260330T175546232525Z__bench_solve_pipeline_no_wli__55b7159`

Locked reading:

- control `phase_b_top_n = 8`
- candidate `phase_b_top_n = 32`
- top-level solve did not move:
  - `best_match_ratio = 0.041`
  - `stage3_match_ratio = 0.039`
- carried downstream variety did move strongly:
  - `phaseB_selected_unique_end_hash: 8 -> 32`
  - `phaseB_downstream_selected_unique_end_hash: 8 -> 32`
  - `phaseC_candidate_pool_unique_end_hash: 8 -> 32`
- exploited downstream variety did not move:
  - `phaseC_start_keys_used = 6`
  - `phaseC_start_unique_end_hash = 6`
  - identical `phasec_start_checkpoints.jsonl`

Integrity consequence:

- the result is valid and should not be discarded as another pipeline failure
- width alone is not sufficient on `seed411`
- the next science lever is no longer "widen the band"
- the next science lever, if pursued, should target how starts are chosen from
  the widened downstream pool, especially inside the enlarged
  `phaseA_selected` set

Recommended immediate action:

- do not queue another pure width long run
- carry the v42 result forward into next-study design
- continue hardening work in parallel, because the hardening backlog remains
  justified regardless of this valid negative

### 2026-03-30 hardening progress: second slice landed

The next hardening slice is now implemented and proven.

Closed in this slice:

- typed Stage-3 tuning preset normalization
- rejection of unknown preset fields
- stronger stale-rerun/run-state identity checks
- explicit persistence of:
  - `planned_job_count`
  - `planned_job_keys_signature`
  - `run_state_version = "v2"`
- event-row identity persistence via `experiment_run_id`

Concrete code surfaces:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_runtime.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan.py`
- `tests/tools/test_no_wli_fixture_matrix_hardening.py`

Meaningful proof:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_hardening.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix.py -q`
  - `38 passed`
- broader guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_hardening.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix.py tests/tools/test_no_wli_runtime_preflight.py tests/tools/test_no_wli_stage3_entry_canary.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `45 passed`

Integrity consequence:

- future matrix reruns should now fail loudly instead of silently skipping into
  a stale or mismatched plan
- future preset mistakes should now fail at normalization time instead of later
  inside ad hoc override plumbing
- this closes another major source of "was that a negative or just a bad run?"
  ambiguity

Still open after this slice:

- resolved runtime-config object
- broader stage-boundary payload typing
- diagnostics persistence unification
- lower-priority cleanup of non-hot-path mutable state surfaces

### 2026-03-30 hardening progress: finalize-path persistence slice landed

Another hot-path hardening slice is now implemented and proven.

Closed in this slice:

- finalize-path persistence consolidation via one
  `IterationPersistencePayload`
- removal of the remaining manual finalize-path enrichment threading for:
  - truth diagnostics
  - word-ngram report payloads
  - Stage-3.5 archive/seed rows
  - Stage-3.5 summary fields
  - target-key payload fields

Concrete code surfaces:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_payload.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_finalize.py`
- `tests/tools/test_no_wli_iteration_persistence_payload.py`

Meaningful proof:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_run_completion.py -q`
  - `7 passed`
- combined guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_hardening.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix.py tests/tools/test_no_wli_runtime_preflight.py tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_run_completion.py tests/tools/test_no_wli_stage3_entry_canary.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `52 passed`

Integrity consequence:

- the finalize path now has one shared persistence serializer for the
  reviewer-facing enrichment fields that previously had to be manually mirrored
- this reduces the chance that a new telemetry field lands in memory but is
  omitted from one of the saved review artifacts

Still open after this slice:

- resolved runtime-config object
- broader stage-boundary payload typing
- full persistence unification across non-finalize paths
- lower-priority cleanup of non-hot-path mutable state surfaces

### 2026-03-30 review-pack refresh

The current review baseline and copied evidence are now bundled in:

- `planning/working/no_wli_external_review_pack_2026-03-30`

This refreshed pack is intended to be the current reviewer handoff set for:

- the locked seed split:
  - `211`-like upstream reach / `good_family_absent`
  - `411`-like downstream exploitation / `good_family_undervalued`
- the four completed live studies
- the earlier `v36` precursor compare
- the current pipeline-hardening state

The pack also includes:

- copied planning logs
- copied matrix control files
- copied run directories for the key studies
- ancillary catalog and ranking-probe evidence
- a small appendix of invalid or incomplete runs for operational context

### 2026-03-30 pack review follow-up: sharpened seed split and next-study shape

After a second cross-check of the new review pack against the copied run
directories and `stage3_diagnostics`, the most useful refinement is:

- `211` is now even more clearly an upstream reach / wrong-neighborhood case
- `411` is now more specifically a carried-to-exploited variety conversion case

Most important downstream refinement:

- for `411`, the next useful science target is not:
  - generic Phase-C source balancing
  - generic late width
  - or family reservation inside the current narrow band
- instead it is:
  - novel-start carry-through from the widened late pool

Meaning:

- the widened downstream pool should be preserved
- but at least one or two genuinely distinct non-anchor challengers from that
  pool should be forced into the actual explored Phase-C start set

Most important upstream refinement:

- for `211`, the next useful science target should move earlier than Stage-3
  entry depth:
  - Stage-2 to Stage-3 promoted-family generation
  - promotion diversity / homogeneity logic
  - or broader basin-generation intervention

### 2026-03-30 `411` novel-start carry-through implementation complete

Implemented:

- `novel_challenger_v1` Phase-C start-selection policy
- explicit persistence of new novelty telemetry into `stage3_diagnostics`
- widened-late baseline vs novel-start candidate live compare config

Key files:

- `tools/benchmarks/periodic_sub_trans/no_wli/family_views.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

Meaningful proof:

- deterministic and persistence slice:
  - `17 passed`
- config/runtime/canary slice:
  - `36 passed`
- broader guard slice:
  - `97 passed`

Prepared next compare:

- experiment id:
  - `tune_v43_p9c3_seed411_novel_start_compare_2job`
- control:
  - `stage3_phaseb_width_probe_p9`
- candidate:
  - `stage3_phasec_novel_challenger_p9`

Integrity note:

- this step also closed a reviewer-facing trust gap:
  - `phaseC_start_policy` is now persisted explicitly in `stage3_diagnostics`
  - the new novelty counters are also persisted explicitly
  - no bundled change was made to Phase-B ranking, rescue, or Stage-3.5

### 2026-03-30 v43 integrity hardening follow-up: Phase-C diagnostics contract enforced

Reason:

- the `v43` study now relies on explicit novelty telemetry
- without a contract, missing late-stage keys could still degrade to zeros or
  empty strings inside `iteration_post_stage3.py`
- that would risk another scientifically ambiguous negative

Implemented:

- explicit required-key contract:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_diagnostics_contract.py`
- contract enforcement when reading two-phase follow-up:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- contract enforcement before building persisted diagnostics:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
- finalize-path integration proof:
  - `tests/tools/test_no_wli_iteration_finalize_word_ngram.py`
- direct contract tests:
  - `tests/tools/test_no_wli_phasec_diagnostics_contract.py`

Meaningful proof:

- focused integrity slice:
  - `41 passed`
- broader guard slice:
  - `101 passed`

Effect:

- if Phase-C ran, the required Phase-C diagnostics must now exist
- if `novel_challenger_v1` ran, the novelty counters and start-summary fields
  must now exist
- the next `v43` long compare remains the correct next science run, but it no
  longer depends on fail-open defaults in the late artifact path

### 2026-03-30 v43 long compare invalidated by Stage-3 live-state bridge bug

The first `v43` long compare did not yield a science readout.

Evidence:

- run state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v43_p9c3_seed411_novel_start_compare_2job.json`
- event log:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v43_p9c3_seed411_novel_start_compare_2job.jsonl`
- both jobs failed with:
  - `KeyError: 'STAGE3_PHASEC_START_POLICY'`
- `completed_jobs = 0`
- `completed_job_keys = []`

Cross-check:

- saved run config for control was already correct:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T033734663702Z__bench_solve_pipeline_no_wli__55b7159/run_config.json`
  - `phase_c.start_policy = "source_order"`
- saved run config for candidate was already correct:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T034501424369Z__bench_solve_pipeline_no_wli__55b7159/run_config.json`
  - `phase_c.start_policy = "novel_challenger_v1"`

Interpretation:

- the study configuration itself was not wrong
- the live Stage-3 runtime bridge was dropping the policy before Stage-3
  execution

Root cause and fix:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_iteration_bridge.py`
  was not forwarding `STAGE3_PHASEC_START_POLICY` into `stage3_state`
- that forwarding is now explicit
- bridge regression coverage was extended in:
  - `tests/tools/test_no_wli_stage_engine_iteration_bridge.py`

Meaningful proof:

- focused:
  - `26 passed`
- broader guard:
  - `108 passed`

Decision:

- `v43` is invalid and should not be read scientifically
- rerun the exact same study configuration on fresh control files only
- do not mutate the science question while fixing this bug

### 2026-03-30 v44 rerun correction: actual live bug was in iteration-matrix config/state

The fresh `v44` rerun also failed with the same `KeyError`, so the first
bridge fix did not yet reach the true fixture-matrix live path.

Evidence:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v44_p9c3_seed411_novel_start_compare_2job_rerun.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v44_p9c3_seed411_novel_start_compare_2job_rerun.jsonl`
- both jobs again failed with:
  - `KeyError: 'STAGE3_PHASEC_START_POLICY'`

Corrected root cause:

- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_builder.py`
  did not include `stage3_phasec_start_policy` in `IterationMatrixConfig`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
  therefore built live stage-engine iteration state without that key

Fix:

- `IterationMatrixConfig` now carries `stage3_phasec_start_policy`
- matrix builder now copies it from live state
- matrix flow now forwards it into the Stage-3 runtime state
- shared contract added in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_state_contract.py`

Proof:

- focused live-path proof:
  - `34 passed`
- broader guard:
  - `116 passed`

Decision:

- `v44` is invalid and should not be interpreted
- the exact same study is re-armed again after the actual matrix-path fix

### 2026-03-31 v45 long compare finished cleanly: study valid, result negative

Evidence:

- state:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v45_p9c3_seed411_novel_start_compare_2job_rerun2.json`
- control:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T053053469532Z__bench_solve_pipeline_no_wli__55b7159`
- candidate:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T075915341627Z__bench_solve_pipeline_no_wli__55b7159`

What is now settled:

- the run finished cleanly with `completed_jobs = 2`
- the policy executed:
  - `phaseC_start_policy = "novel_challenger_v1"`
  - `phaseC_selected_novel_challenger_count = 2`
- the actual explored start set did not change relative to the widened-late
  control
- the study is therefore a valid negative, not another instrumentation failure

Important interpretability clarification:

- `phasec_start_checkpoints.jsonl` `final_match` fields are true per-start
  truth-match values
- but the saved top-level winner remains score-selected
- therefore high-truth Phase-C challenger paths can exist without changing
  top-level `best_match_ratio`

Integrity consequence:

- pipeline correctness for this study is now adequate
- reviewer-facing scientific visibility is still incomplete because score-losing
  but truth-strong challenger paths are not surfaced prominently in top-level
  summaries

### 2026-03-31 integrity follow-up: benchmark disagreement reporting and replay-fixture capture added

To address the visibility gap exposed by `v45`, the pipeline now persists
benchmark-focused disagreement reporting for explored Phase-C starts and
supports frozen frontier export for later selector/scorer replay.

Implemented:

- disagreement reporting:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_reporting.py`
- truth-gap dataset/export:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_gap_dataset.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_phasec_truth_gap_dataset.py`
- replay-fixture export:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_frontier_fixture.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_frontier_fixture.py`

Integrity value:

- benchmark runs can now expose both:
  - score-selected winner
  - best explored truth challenger
- future late-stage scorer experiments no longer have to scrape ad-hoc frontier
  rows from mixed artifacts
- replay-material completeness is now explicit instead of implicit

Current limitation:

- historical `v45` evidence remains strong enough for analysis and spec writing
- but it predates the new replay-capture fields, so a fresh comparable run is
  still required before frozen frontier replay is complete enough for direct
  trial-key testing

### 2026-03-31 integrity note: Stage A selector harness is benchmark-only and preserves live semantics

The new late-stage selector harness is intentionally isolated from the live
pipeline.

Added:

- `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_benchmark.py`
- `tests/fixtures/no_wli/v45_seed411_late_frontier_fixture.json`

Integrity value:

- selector experiments can now run on a frozen real frontier without silently
  altering live winner selection
- the known `v45` disagreement is now a stable regression target inside tests
- future scorer work can be staged as:
  - benchmark-only design first
  - replay validation second

Guardrail:

- do not route this benchmark-only selector module into live run selection until
  a replayable frontier case has been validated

### 2026-03-31 integrity follow-up: Stage A pattern audit now proves the repeated disagreement family is real

The benchmark-only selector/report path now audits disagreement cases against
their real saved frontier artifacts and collapses them into repeated
winner/challenger pattern families.

Added reporting outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/disagreement_frontier_row_audit.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/disagreement_frontier_pattern_audit.json`

Integrity value:

- the late-stage selector story is no longer just one frozen `v45` anecdote
- the dominant repeated disagreement family is now shown explicitly across real
  saved frontiers
- both benchmark-only rerankers rescue that dominant family without changing
  live solver behavior
- the current rescue explanation remains auditable as:
  - structural / novelty signals, not score-only rescue
- the new rescued-vs-unrecovered contrast keeps the current selector limit
  explicit in reviewer-facing artifacts:
  - rescued `9002...` gets enough novelty support to overcome a small score gap
  - unrecovered `e45...` does not
- the new feature-audit and ablation exports now make it explicit whether a
  current Stage A failure is:
  - present-but-underweighted on live-visible fields
  - or absent because the needed lexical/semantic signals are not yet captured
- the one-at-a-time numeric-field sweep now makes one more boundary explicit:
  - the tested present-but-unused numeric live fields do not change the current
    rescue set
  - so future claims about missing lift should not keep re-trying the same
    numeric-field family without a new reason
- the new robustness sweep adds one more trust point:
  - the dominant `9002...` rescue is stable under small weight perturbations
  - so it is not currently a knife-edge artifact of one exact baseline weight
    choice

Guardrail:

- keep treating this as benchmark-only evidence until a replay-ready frontier is
  available from `v46` or a comparable fresh run

### 2026-03-31 integrity follow-up: replay-capture run re-armed without changing the science compare

To support Stage B, the active matrix config now re-arms the same known
`seed411` widened-late vs novel-start compare under a fresh experiment id:

- `tune_v46_p9c3_seed411_novel_start_replay_capture_2job`

Integrity value:

- the next long run is explicitly for replay capture, not a silent semantic
  science change
- control files are fresh, so there is no stale-resume ambiguity
- compare semantics stay aligned with the known `v45` disagreement case

### 2026-03-31 integrity follow-up: Stage B now uses one shared frontier-source contract

The fresh replay-ready `v46` frontier is now consumed through one shared loader
instead of a mix of local assumptions about where Phase-C rows live.

Added:

- `tools/benchmarks/periodic_sub_trans/no_wli/phasec_frontier_rows.py`

Consumers hardened:

- `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_frontier_fixture.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/replay_phasec_rescue_sweep.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_gap_dataset.py`

Integrity value:

- Stage B exporter, replay helper, resume flow, and disagreement dataset now
  all agree on the same late-frontier source
- the pipeline no longer relies on ad hoc local fallbacks for whether
  `phaseC_start_summaries` lives in the condensed artifact or the run-level
  checkpoint file
- the Stage B comparison bundle is now built from the same normalized frontier
  shape that the replay path will use

Guardrail:

- keep using the normalized frontier export / selected-trial-material path for
  the first direct replay comparison rather than introducing one-off local
  fixture readers

### 2026-03-31 integrity follow-up: Stage B selected-row continuation is now a real end-to-end path

The first Stage B continuation comparison now runs from the exported selected
trial rows through the real Stage 3.5 continuation codepath.

Added:

- `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_stageb_continuation.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stageb_continuation_report.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`

Integrity value:

- the scorer/reranker story is no longer limited to:
  - frozen frontier ranking
- it now covers:
  - normalized frontier export
  - selected-row handoff
  - real Stage 3.5 continuation from saved key/plaintext material
- the first replay-ready `v46` case proves that the better-ranked challenger is
  not just cosmetically better in reporting; it continues to a materially better
  downstream truth result

Additional hardening:

- `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_frontier_fixture.py`
  now emits repo-relative:
  - `source_artifact_path`
  - `phasec_checkpoint_path`

This removes local absolute-path leakage from the shared Stage B handoff
artifacts and keeps generated review outputs aligned with repo path rules.

Guardrail:

- keep any further Stage B work routed through these shared frontier/selected-row
  contracts rather than adding local continuation inputs or one-off replay
  shims

### 2026-03-31 integrity follow-up: live Stage 3.5 selector work is locked to one explicit config boundary

The next live scorer-facing change is now constrained to one explicit runtime
field:

- `STAGE35_BASELINE_SELECTOR`

Integrity requirement:

- do not infer the selector mode from local call-site state
- do not wire the benchmark harness directly into live flow
- do not bypass the existing runtime/config/lock plumbing

The selector mode must stay explicit through:

- runtime defaults
- runner state initialization
- fixture-matrix preset overrides
- iteration matrix config
- Stage 3 runtime contract
- run config and lock payload
- persisted `stage3_diagnostics`

Required persisted evidence:

- selected Stage 3.5 baseline row identity
- Phase-C score-winner identity for comparison
- whether the selected baseline differs from the Phase-C score winner
- Stage 3.5 acceptance / rejection outcome
- downstream continuation result

Guardrail:

- keep the upcoming canary and overnight run as a Stage 3.5 baseline-selector
  compare only
- do not mix in width/start-policy/feature-family changes at the same time

Implementation/proof status:

- shared selector core implemented in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_core.py`
- live flow now records both:
  - the Phase-C score winner
  - the actual Stage 3.5 baseline row
- fixture-matrix presets now support:
  - canary compare
  - overnight compare
- guard slice after the narrow selector integration:
  - `83 passed`

Canary hardening follow-up:

- the first live canary exposed a missing setup-logging boundary:
  - `emit_setup_logging()` was not yet updated for
    `stage35_baseline_selector`
- fixed in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/setup_logging.py`
- guarded in:
  - `tests/tools/test_no_wli_setup_logging.py`
- updated proof:
  - `84 passed`

### 2026-04-01 integrity note: silent Stage 3.5 runtime is not acceptable

The `v47` canary showed that a run can pass Phase C and then burn CPU for hours
without advancing saved artifacts.

Integrity consequence:

- a Stage 3.5-enabled lane must not rely on end-of-stage logging only
- live followup needs explicit progress evidence so canaries can distinguish:
  - healthy long work
  - unexpectedly heavy work
  - real wedges

Hardening applied:

- live Stage 3.5 now emits:
  - `stage35-start`
  - `stage35-heartbeat`
  - `stage35-finish`
- the reduced canary config is now separated from the overnight config
- a fresh canary experiment id is used after the stall:
  - `tune_v49_p9c3_seed411_stage35_baseline_selector_canary_reduced_2job`

Guardrail:

- do not treat a wallclock-only canary cap as sufficient proof of bounded work
- keep boundary-specific progress logging whenever a stage can run for minutes+
  without touching persisted artifacts

Operational guardrail:

- automated promotion from canary to overnight must key off saved run state and
  events, not just process exit
- the detached `v49` watcher now follows that rule before launching `v48`

### 2026-04-02 integrity guardrail after the partial overnight compare

The next live Stage 3.5 selector run should be the missing candidate lane only.

Guardrail:

- do not spend another long run reproducing the already-completed legacy lane
- keep the completed `v48` legacy result as the locked baseline
- run only:
  - `stage35_baseline_score_plus_novelty_live_p9`

Integrity readout for that run:

1. baseline row identity changed or not
2. Stage 3.5 admission changed or not
3. downstream continuation stronger or weaker than the locked legacy long lane

### 2026-04-02 integrity note: Stage 3.5 runtime itself is now a first-class constraint

The current live candidate lane indicates that a stronger Stage 3.5 baseline
row can trigger a much heavier Stage 3.5 search path.

Integrity consequence:

- do not treat Stage 3.5 runtime as a secondary implementation detail
- a candidate path that is theoretically better but practically unbounded is not
  yet a viable live improvement

So future Stage 3.5 work should require:

- bounded runtime or explicit capped outcomes
- persisted partial state during long Stage 3.5 runs
- enough telemetry to distinguish:
  - slow but healthy
  - expensive but bounded
  - truly wedged
