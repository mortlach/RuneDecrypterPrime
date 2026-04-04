# `score_stop_shadow_v2` family-aware shadow stop spec

## Purpose

This is a second-pass offline analysis spec for **non-oracle dump/stop signals**
from saved No-WLI benchmark artifacts.

The main question is no longer just:

- does one row get a high score?

It is:

- does a run enter a **stable, high-trust, family-dominant region** that false
  friends usually do not occupy strongly enough to justify:
  - a safe `would_dump` inspection trigger first
  - and only later, a conservative `would_stop` shadow proxy?

This remains a **science-only** slice.
All outcomes are analysis labels only.
No live solver behaviour changes in this slice.

## Core change from v1

`v1` was row-first.

`v2` is **family-aware** and treats a convincing near-solve as something that
should usually show all of these together:

1. high text trust
2. positive margin over the best rival family in the same pool
3. support from more than one row in the same family when possible
4. stability across more than one saved boundary or work unit

This is closer to the real question:

- are we on the right hill, rather than just seeing one good-looking row?

## Non-goals

- no live stop rule
- no live dump rule
- no solver ranking/admission/continuation changes
- no oracle features in trigger logic
- no global raw-score cutoff shared across mixed objectives/profiles
- no ad hoc CLI arguments; script constants stay in-file

## Proposed folder

- Spec:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/SPEC.md`
- Experiment plan:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/EXPERIMENT_PLAN.md`
- No-CLI extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`
- Default output root:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/`

## Inputs

### 1. Final artifacts

Input pattern:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/*__bench_solve_pipeline_no_wli__*/final_instances/*.json`

Useful fields already present in current repo/output shape:

- run identity and fixture metadata
- final labels and best-stage outcome
- fixture truth for benchmark runs
- `stage3_diagnostics.space_map_v1.partial_state_rows`
- `stage3_diagnostics.space_map_v1.pool_summaries`
- `stage3_diagnostics.phaseC_start_summaries`
- `stage3_diagnostics.stage35_*`
- persisted word-ngram reports for final and some top-k surfaces

### 2. Phase C checkpoints

Input pattern:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/*__bench_solve_pipeline_no_wli__*/phasec_start_checkpoints.jsonl`

Use:

- optional cross-check that persisted Phase C summaries match the checkpoint
  stream
- optional source for older artifacts where summary persistence is incomplete

### 3. Stage 3.5 progress and partial dumps

Input patterns:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/*__bench_solve_pipeline_no_wli__*/stage35_progress.jsonl`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/*__bench_solve_pipeline_no_wli__*/stage35_partial_state.json`

Use:

- recover later-stage timing and work-unit evidence
- estimate whether a family-aware trigger would have fired materially earlier
  than the final archive/finish row

### 4. Run config and replay helpers

Use the existing repo helpers rather than bespoke rebuild logic:

- `tools/benchmarks/periodic_sub_trans/no_wli/replay_phasec_rescue_sweep.py`
  - `_build_cipher(...)`
  - `_build_stage3_scorer_runtime(...)`
  - `_build_stage3_word_ngram_report_runtime(...)`
- `tools/benchmarks/periodic_sub_trans/no_wli/word_ngram_report.py`
  - `score_word_ngram_report_for_plaintext(...)`
  - `extract_word_ngram_report_fields(...)`
- `tools/benchmarks/periodic_sub_trans/common/batch_eval.py`
  - `score_plaintexts_chunked(...)`

## Candidate-row universe

Primary source for fresh artifacts:

- `stage3_diagnostics.space_map_v1.partial_state_rows`

Boundaries to include:

- `stage2_promoted`
- `stage3_prep`
- `phaseC_pool`
- `phaseC_start`
- `stage35_seed`
- `stage35_archive`

Fallback sources for older artifacts only when `space_map_v1` is absent:

- `stage2_topk`
- `stage3_topk`
- `stage3_diagnostics.phaseC_start_summaries`
- `stage35_seed_rows`
- `stage35_archive`

Old/fallback rows must carry explicit `data_gap_flags`.

Legacy fallback join:

- if a `phaseC_start` fallback row has a `candidate_hash` but no key/plaintext
  state, the extractor may inherit that state from a same-hash `stage3_topk`
  fallback row in the same artifact
- this is a replay-state reconstruction only, not a family-graph claim

## Minimum per-row output schema

### Identity and saved structure

- `run_id`
- `artifact_path`
- `tier_name`
- `text_id`
- `key_seed`
- `stage_boundary`
- `candidate_hash`
- `parent_candidate_hash`
- `parent_link_kind`
- `family_view_id`
- `family_id`
- `family_id_kind`
- `distance_to_anchor`
- `source`
- `lane`
- `source_rank`
- `stage_rank`

### Saved state

- `init_key_idx`
- `final_key_idx`
- `init_plaintext_idx`
- `final_plaintext_idx`
- `preview_text`
- `init_score`
- `final_score`
- `init_search_score`
- `final_search_score`
- `init_match`
- `final_match`
- `score_gain`
- `match_gain`
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

### Offline replay-rescored fields

These must be labelled as replay-derived.

- `replay_full_score`
- `replay_search_score`
- `replay_judge_score`
- `replay_truth_match`
- `replay_word_ngram_available`
- `replay_word_ngram_active`
- `replay_word_ngram_report_xent`
- `replay_word_ngram_trust_score`
- `replay_word_ngram_inactive_reason`
- `replay_score_source`
- `replay_data_gap_flags`

### Family-aware shadow fields

- `shadow_primary_axis`
- `shadow_anchor_margin`
- `shadow_best_rival_family_margin`
- `shadow_family_support_count`
- `shadow_family_boundary_support_count`
- `shadow_high_score_rule_id`
- `shadow_high_score_would_dump`
- `shadow_high_score_would_stop`
- `shadow_stability_rule_id`
- `shadow_stability_would_stop`
- `shadow_first_trigger_stage_boundary`
- `shadow_first_trigger_stage_rank`
- `shadow_false_stop_label`

## Minimum run-level output schema

- `run_id`
- `artifact_path`
- `tier_name`
- `text_id`
- `key_seed`
- `period`
- `columns`
- `best_stage`
- `best_match_ratio`
- `run_type`
- `shadow_rule_id`
- `would_dump`
- `would_stop`
- `would_stop_stage_boundary`
- `would_stop_candidate_hash`
- `would_stop_family_id`
- `would_stop_primary_axis`
- `would_stop_truth_match`
- `would_stop_false_positive`
- `would_stop_before_true_solution`
- `saved_runtime_seconds_proxy`
- `potential_saved_evals_proxy`
- `data_gap_flags`

## Replay rescoring feasibility

### Truth match

Feasible for fixture artifacts when target plaintext exists.

Preferred order:

1. use persisted `final_plaintext_idx`
2. otherwise decrypt from `final_key_idx`
3. if no target plaintext exists, emit explicit `no_target_plaintext`

### Full/search/judge rescoring

Feasible for most fresh artifacts using current replay helper surfaces.

Preferred order:

1. rebuild scorers from `run_config.json`
2. if row plaintext exists, score it directly
3. otherwise decrypt first, then score
4. if scorer build fails, emit explicit replay gap flags

### Word-ngram rescoring

Feasible when the run config enables the report scorer.

Preferred order:

1. rebuild the word-ngram report runtime from run config
2. if plaintext exists, score directly
3. otherwise decrypt then score
4. keep inactive-report reasons, do not convert them to missing-data errors

## Family-aware rule families to test first

### 1. Dump-for-inspection rule

A row may trigger `would_dump` when all are true:

- active word-ngram report
- trust score above a floor
- report xent below a ceiling
- positive margin over the best rival family in the same pool
- family support count at or above a floor

This is intentionally easier to trigger than a stop.

### 2. Stability stop proxy

A row/family may trigger `would_stop` only when all are true:

- it already qualifies for the dump rule
- the same family remains trigger-positive across at least `N` saved boundaries
- the family remains ahead of the best rival family at each of those boundaries

This is the first hard-stop proxy to test.

### 3. Plateau rule deferred

Do not promote a plateau proxy in this first implementation.

Reason:

- current checkpoint density is strongest in late Stage 3.5 only
- a robust plateau rule needs more consistent work-unit cadence across stages
- implement plateau only after the family-aware dump/stability analysis is read

## False-stop labels

For fixture artifacts only:

- a `would_stop` is a false stop if the final artifact later reaches a
  strictly better truth match by a meaningful margin
- for exact solved controls, any stop before the first row with truth match at
  or above the solved threshold is a false stop
- for unsolved hard cases, report whether the stop occurred before the final
  best match and before the final best stage separately

For non-fixture artifacts:

- `shadow_false_stop_label = "unknown_without_truth"`

## Calibration outputs

The first implementation should write:

- `row_scores.jsonl`
- `run_shadow_summary.jsonl`
- `threshold_sweep_summary.json`
- `data_gap_report.json`
- optional `summary.md`

## Current score-panel mode

The extractor currently has a bounded `score_panel_v1` mode for the first
score-only calibration pass.

Scope:

- old mid-quality artifacts are allowed, even when `space_map_v1` is absent
- only late boundaries are replay-scored:
  - `stage2_topk`
  - `stage3_topk`
  - `phaseC_start`
  - `stage35_seed`
  - `stage35_archive`
- rows are capped per boundary so this remains a short analysis pass
- family-stability `would_stop` is disabled in this mode
- `would_dump` is based on active word-ngram trust / xent only, not family
  support or rival-family margin

Reason:

- the first question is whether score/report features alone separate
  solved/near-solved rows from false friends
- legacy `stage3_topk` and `stage2_topk` rows are included so pre-`space_map_v1`
  artifacts can still contribute replay-scored near-solved and mid-quality
  examples
- family-aware stability is a second track and should not be mixed into this
  first score-only panel

## First hardcoded threshold grid

These remain a starting grid, not a proposed policy.

The current `score_panel_v1` grid is widened from the original v2 spec because
a solved fresh `p5/c1 seed511` row from `v60` replay-scored at roughly:

- `replay_word_ngram_trust_score = 0.479`
- `replay_word_ngram_report_xent = 16.227`

That means the original `(0.90, 0.95, 0.98)` trust floors and
`(2.5, 2.0, 1.5)` xent ceilings were far too strict for this scorer scale.

- `TRUST_SCORE_FLOORS = (0.30, 0.40, 0.50)`
- `REPORT_XENT_CEILINGS = (24.0, 18.0, 12.0)`
- `RIVAL_MARGIN_FLOORS = (0.00, 0.02, 0.05)`
- `FAMILY_SUPPORT_FLOORS = (1, 2)`
- `BOUNDARY_STABILITY_COUNTS = (1, 2, 3)`

The current score-panel artifact targets are also expanded to a coarse 24-run
ladder:

- solved / near-perfect: `6`
- near-solved / high-quality: `6`
- mid-quality: `8`
- bad / false-friend: `4`

Do not add a global raw full-score floor in this pass.

## Minimum acceptance checks for the first implementation

- reads fresh `space_map_v1` artifacts and older fallback artifacts without
  crashing
- emits explicit row/run `data_gap_flags`
- replay-decrypts key-only rows when possible
- replay-scores at least one row with full/search/judge scorers
- replay-scores at least one row with the word-ngram report scorer when enabled
- computes fixture truth match where target plaintext exists
- distinguishes `would_dump` from `would_stop`
- reports family support and rival-family margin at trigger time

## Known limitations

- older artifacts predate `space_map_v1`
- `stage3_prep` mutation ancestry still includes fallback parent links in some
  runs
- row-complete word-ngram summaries are still not persisted in saved rows
- stage-level work-unit timing is patchier before newer Stage 3.5 artifacts

## Bottom line

`score_stop_shadow_v2` should answer a more realistic question than “is one row
very high-scoring?”.

It should answer:

- did the run enter a **stable, dominant, high-trust family region** that looks
  separable from false friends strongly enough to justify a dump or stop proxy?
