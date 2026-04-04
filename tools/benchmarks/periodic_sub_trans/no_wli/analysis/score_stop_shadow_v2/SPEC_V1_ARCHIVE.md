# `score_stop_shadow_v1` offline analysis spec

## Purpose

This analysis tests **non-oracle early-stop and dump-for-inspection signals**
from saved No-WLI benchmark artifacts, without changing solver decisions.

The question is not “can we stop as soon as one score is high on one case?”.
The question is:

**Do near-solved rows occupy a score/report region that is separable from
high-score false friends strongly enough to justify a shadow stop or a safe
candidate dump trigger?**

This is a replay/offline science pass only. Any rule explored here must be
reported as `would_stop` / `would_dump`, not applied to live search.

## Non-goals

- Do not modify the solver’s ranking, admission, or continuation behavior.
- Do not add a live score cutoff in this slice.
- Do not infer truth on unknown-answer runs.
- Do not use ad hoc CLI arguments; all script inputs and thresholds must live
  in hardcoded constants in the analysis script.

## Proposed folder

- Spec:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v1/SPEC.md`
- Future no-CLI analysis script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v1/extract_score_stop_shadow_v1.py`
- Future default output root:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v1/`

## Inputs and what they can provide today

### 1. Final artifacts

Input pattern:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/*__bench_solve_pipeline_no_wli__*/final_instances/*.json`

Useful fields already present:

- run identity / fixture metadata:
  - `tier`, `period`, `columns`, `text_id`, `key_seed`, `mode`,
    `profile_id`, `outcome_code`
- final labels:
  - `best_stage`, `best_match_ratio`, `best_score`, `final_best_key_idx`,
    `final_best_plaintext_idx`, `status`, `stop_reason`
- oracle truth for fixture runs:
  - `target_plaintext_idx`, `target_key_idx`, `truth_diagnostics`
- persisted score reports:
  - `word_ngram_report`
  - `stage2_topk_word_ngram_report`
  - `stage3_topk_word_ngram_report`
- stage diagnostics:
  - `stage3_diagnostics.phaseC_start_summaries`
  - `stage3_diagnostics.phaseC_candidate_pool_rows`
  - `stage3_diagnostics.stage35_*`
  - `stage3_diagnostics.space_map_v1.partial_state_rows`
  - `stage3_diagnostics.space_map_v1.pool_summaries`
- late replay rows:
  - `stage35_seed_rows`
  - `stage35_archive`

### 2. Phase C checkpoints

Input pattern:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/*__bench_solve_pipeline_no_wli__*/phasec_start_checkpoints.jsonl`

Use:

- reconstruct the per-start Phase C summary stream if needed
- cross-check that artifact-level `phaseC_start_summaries` was persisted
  correctly

### 3. Stage 3.5 progress / partial dumps

Input patterns:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/*__bench_solve_pipeline_no_wli__*/stage35_progress.jsonl`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/*__bench_solve_pipeline_no_wli__*/stage35_partial_state.json`

Use:

- recover late-run progress and timestamps
- test whether a candidate crossed a shadow-stop threshold long before the
  final archive was written

Scope caveat:

- these files only exist for newer artifacts written after the Stage 3.5
  partial-dump patch

### 4. Run config and resume metadata

Input paths near each artifact:

- `run_config.json`
- `stage_specs.json`
- `policy_spec.json`
- `run_manifest.json`

Use:

- recover scorer/cipher configuration and LM asset references
- rebuild the runtime scorers/cipher when replay rescoring is needed

## Candidate-row universe to collate

The first script should collect rows from these boundaries:

- `stage2_promoted`
- `stage3_prep`
- `phaseC_pool`
- `phaseC_start`
- `stage35_seed`
- `stage35_archive`

Primary source:

- `stage3_diagnostics.space_map_v1.partial_state_rows`

Fallback sources for older artifacts:

- `stage3_topk`
- `stage3_diagnostics.phaseC_start_summaries`
- `stage35_seed_rows`
- `stage35_archive`

Fallback caveat:

- old artifacts that predate `space_map_v1` do not support full family /
  parent / distance analysis, so include them only with explicit
  `data_gap_flags`

## Minimum per-row output schema

### Identity and structure

- `run_id`
- `tier_name`
- `text_id`
- `key_seed`
- `stage_boundary`
- `candidate_hash`
- `parent_candidate_hash`
- `family_view_id`
- `family_id`
- `distance_to_anchor`
- `source`
- `lane`
- `source_rank`
- `stage_rank`

### Available state

- `init_key_idx`
- `final_key_idx`
- `init_plaintext_idx`
- `final_plaintext_idx`
- `preview_text`

### Saved scores / truth

- `init_score`
- `final_score`
- `init_search_score`
- `final_search_score`
- `init_match`
- `final_match`
- `score_gain`
- `match_gain`

### Selection / continuation provenance

- `selected`
- `eligible`
- `rejected`
- `selection_policy`
- `reject_reason`
- `admitted_by_next_stage`
- `next_stage_accept_reason`
- `continued_best_candidate_hash`
- `continued_best_score`
- `continued_best_match`

### Rescored offline metrics

These must be labelled as replay-derived, separate from persisted solver
scores.

- `replay_full_score`
- `replay_search_score`
- `replay_judge_score`
- `replay_word_ngram_trust_score`
- `replay_word_ngram_report_xent`
- `replay_word_ngram_active`
- `replay_truth_match`
- `replay_score_source`
- `replay_data_gap_flags`

### Shadow-stop fields

- `shadow_high_score_rule_id`
- `shadow_high_score_would_dump`
- `shadow_high_score_would_stop`
- `shadow_high_score_margin_to_anchor`
- `shadow_high_score_margin_to_best_rival_family`
- `shadow_plateau_rule_id`
- `shadow_plateau_would_stop`
- `shadow_first_trigger_stage_boundary`
- `shadow_first_trigger_work_unit`
- `shadow_first_trigger_evals`
- `shadow_false_stop_label`

## Minimum run-level output schema

- `run_id`
- `tier_name`
- `text_id`
- `key_seed`
- `period`
- `columns`
- `best_stage`
- `best_match_ratio`
- `best_score`
- `run_type`
- `shadow_rule_id`
- `would_dump`
- `would_stop`
- `would_stop_stage_boundary`
- `would_stop_candidate_hash`
- `would_stop_family_id`
- `would_stop_replay_score`
- `would_stop_replay_word_ngram_trust_score`
- `would_stop_replay_truth_match`
- `would_stop_before_true_solution`
- `would_stop_false_positive`
- `saved_runtime_seconds_proxy`
- `potential_saved_evals_proxy`
- `data_gap_flags`

## Manual replay-rescoring plan and feasibility

This is the part that should not be guessed silently.

### A. Truth scoring

Feasible for fixture artifacts:

- `target_plaintext_idx` is persisted in final artifacts
- each `space_map_v1` row usually carries either `final_plaintext_idx` or at
  least `final_key_idx`
- therefore `replay_truth_match` can be computed offline by:
  1. comparing `final_plaintext_idx` directly to `target_plaintext_idx` when
     plaintext is present
  2. otherwise decrypting `final_key_idx` against `ciphertext_idx` and then
     comparing to `target_plaintext_idx`

Not feasible for unknown-answer runs:

- if no oracle plaintext is available, do not fabricate `replay_truth_match`
- emit `replay_data_gap_flags += ["no_target_plaintext"]`

### B. Full/search/judge rescoring

Feasible for most fresh artifacts:

- `artifact_resume.py` already rebuilds:
  - `scorer_full_runtime`
  - `scorer_stage3_search_runtime`
  - `scorer_basin_judge_runtime`
  - `scorer_word_ngram_report_runtime`
  from each artifact plus the matching `run_config.json`
- rows with plaintext can be rescored directly with
  `score_plaintexts_chunked(...)`
- rows with key but no plaintext can be decrypted first with the rebuilt
  cipher, then rescored

Known gaps from the current fresh p5 artifact:

- `stage2_promoted` rows have key material and saved full score, but often no
  saved plaintext and no saved search/judge score
- `stage3_prep` rows have key material, but often blank plaintext and blank
  scores because the prep handoff does not expose those values
- therefore the first implementation must support a **decrypt-then-score
  replay path** for these rows instead of assuming plaintext/score fields are
  already filled

Fallback behavior:

- if runtime scorer reconstruction fails because a run config or LM asset is
  unavailable, emit explicit `replay_data_gap_flags` such as:
  - `missing_run_config`
  - `missing_scorer_asset`
  - `replay_scorer_build_failed`
- do not drop the row silently

### C. Word-ngram rescoring

Partly feasible now.

Already persisted:

- final-best report:
  - `word_ngram_report`
- Stage 2 / Stage 3 top-k reports:
  - `stage2_topk_word_ngram_report`
  - `stage3_topk_word_ngram_report`

Not yet row-complete:

- most `space_map_v1.partial_state_rows[*].word_ngram_summary` entries are
  still empty placeholders
- Stage 3.5 seed/archive rows do not yet carry a full word-ngram report for
  every row

What can still be done offline:

- if a row has plaintext, call
  `score_word_ngram_report_for_plaintext(...)` with the rebuilt report scorer
- if a row has only key, decrypt first, then call the same reporter
- extract:
  - `word_ngram_judge_active`
  - `word_ngram_judge_report_xent`
  - `word_ngram_judge_trust_score`
  - `word_ngram_judge_trust_tier`

Feasibility caveats:

- if the report scorer was not configured for a run, the runtime is `None`;
  emit `word_ngram_unavailable_for_run`
- if the scorer marks a plaintext inactive, preserve the reported inactive
  reason instead of turning that into a missing-data error
- do not assume raw trust/xent thresholds are globally comparable across all
  profiles before the first calibration pass checks that

### D. Manual decryption source of truth

When plaintext is absent but key is present, use the cipher rebuilt from the
artifact/run config, not a bespoke parser.

Preferred implementation path:

- reuse `artifact_resume._build_cipher(...)`
- reuse the scorer-runtime builders already used by
  `artifact_resume.run_stage3_resume_from_artifact(...)`
- centralize this logic in one no-CLI analysis helper so the same row is never
  rescored with two incompatible runtime configurations

## First shadow-rule families to test

These rules are analysis-only. They must emit `would_stop` / `would_dump`
flags, not change search behavior.

### 1. High-score dump trigger

Candidate logic:

- if a row has:
  - high full/judge score
  - active word-ngram report
  - high `word_ngram_judge_trust_score`
  - low `word_ngram_judge_report_xent`
  - positive margin over nearby rival families
- then mark `shadow_high_score_would_dump = 1`

Goal:

- decide whether “this looks solved enough to save immediately for
  inspection” is safe before attempting a hard stop rule

### 2. High-score hard-stop proxy

Candidate logic:

- same as the dump trigger, but require stability over several checkpoints or
  work units before setting `shadow_high_score_would_stop = 1`

Goal:

- estimate false-stop risk by asking whether this trigger would have fired on a
  false friend before a better continuation appeared

### 3. Plateau hard-stop proxy

Candidate logic:

- no meaningful score improvement for `N` work units
- no new accepted rows or no new family mass entering the selected set
- optional extra guard: best score already above a floor

Goal:

- identify likely safe plateau exits and estimate how often they would have
  stopped a run too early

## How to define false-stop labels

For fixture runs only:

- a `would_stop` event is a false stop if a later row in the same run reaches a
  strictly better `replay_truth_match` by a meaningful margin, or if the final
  artifact reaches a better `best_match_ratio`
- for exact solved controls, any `would_stop` before the first true solved row
  is a false stop
- for hard unsolved runs, report `would_stop_before_best_match` and
  `would_stop_before_best_stage35_accept` separately, because best score and
  best truth can disagree

For non-fixture runs:

- do not emit a truth-based false-stop label
- emit `shadow_false_stop_label = "unknown_without_truth"`

## Calibration outputs

The first analysis pass should produce:

- `row_scores.jsonl`
  - one row per candidate-state record with saved and replay-rescored metrics
- `run_shadow_summary.jsonl`
  - one row per run and shadow rule
- `threshold_sweep_summary.json`
  - aggregate false-stop and potential-savings summaries for a hardcoded
    threshold grid
- `data_gap_report.json`
  - counts of rows/runs blocked by missing plaintext, scorer config, report
    scorer runtime, or continuity fields

## First hardcoded threshold grid

This grid is only a starting point for shadow analysis, not a promoted stop
policy.

Suggested constants:

- `HIGH_SCORE_TRUST_FLOORS = (0.90, 0.95, 0.98)`
- `HIGH_SCORE_REPORT_XENT_CEILINGS = (2.5, 2.0, 1.5)`
- `HIGH_SCORE_FULL_SCORE_FLOORS = ()`
  - leave empty in the first pass unless a stage-specific score scale is
    derived from saved runs; raw score scale is profile/objective dependent
- `HIGH_SCORE_MARGIN_TO_ANCHOR_FLOORS = (0.0, 0.01, 0.02)`
- `HIGH_SCORE_STABLE_WORK_UNITS = (1, 2, 4)`
- `PLATEAU_WORK_UNITS = (8, 16, 32)`
- `PLATEAU_SCORE_IMPROVE_EPS = (1.0e-6, 1.0e-4)`

Why no global raw-score floor yet:

- persisted scores mix objectives (`avg.logp`, `pct.logp.win10`, and
  word-ngram trust/xent), so a single global full-score cutoff would be sloppy
  until we stratify by stage/profile/objective

## Minimum acceptance checks for the first script

- reads fresh `space_map_v1` artifacts and older fallback artifacts without
  crashing
- emits explicit `data_gap_flags` instead of silently omitting blocked rows
- replay-decrypts rows with key-only state, especially `stage2_promoted` and
  `stage3_prep`
- replay-scores at least one row with rebuilt full/search/judge scorers
- replay-scores at least one row with the rebuilt word-ngram report scorer when
  that runtime is available
- computes `replay_truth_match` for fixture artifacts
- distinguishes `would_dump` from `would_stop`
- produces a run summary where a shadow trigger can be compared against the
  final artifact outcome

## Known limitations after the current serializer work

- old artifacts predate `space_map_v1`
- Stage 3 prep rows still use fallback parent-to-anchor edges when exact
  mutation origin metadata is absent
- many `space_map_v1` rows currently have empty `word_ngram_summary`
- current rows do not persist a complete checkpoint-time score margin to every
  rival family, so margin-to-rival-family may need to be recomputed from rows in
  the same pool
- Stage 3.5 progress JSONL exists only for newer runs

## Maintained implementation order

1. Review this spec.
2. Implement the no-CLI extractor under this folder.
3. Run it first on a tiny subset:
   - one solved p5/p7 control
   - one hard `411` success case
   - one hard fresh-seed p9 case if `v59` produces one
4. Inspect whether high-trust near-solved rows separate from false friends.
5. Only then decide whether to wire any shadow-stop summaries into future live
   artifacts.

## Scope statement

The output of `score_stop_shadow_v1` is evidence for **future stop policy
design**, not a policy itself.

The implementation should make it cheaper to answer:

- “Would a candidate have been worth dumping for inspection here?”
- “Would a plateau/high-score stop have fired too early?”
- “Which score/report combination appears stable across seed categories?”

It must not silently convert those answers into live termination behavior.
