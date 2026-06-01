# No-WLI partial-state space-map data contract

## Purpose

Define what the pipeline should save so we can map the search space, classify
partial states, and support replay/resume science without immediately changing
solver policy.

The goal is not "more telemetry". The goal is enough state + relation +
provenance data to answer:

- what states existed at each compression boundary?
- which states were selected or rejected?
- which states belong to the same hill/family?
- which challengers opened genuinely different continuation paths?
- where does useful diversity collapse too early?

## Canonical record 1: partial-state row

Target use:

- one row per candidate state at a named stage boundary
- stable enough to compare rows across diagnostics, checkpoints, and replay
  artifacts

Proposed minimum fields:

- identity:
  - `run_id`
  - `tier_name`
  - `text_id`
  - `key_seed`
  - `stage_boundary`
  - `candidate_hash`
  - `parent_candidate_hash`
  - `source`
  - `lane`
  - `source_rank`
  - `stage_rank`
- reconstructability:
  - `init_key_idx`
  - `init_plaintext_idx`
  - `final_key_idx`
  - `final_plaintext_idx`
  - `replay_config_ref`
- score / truth:
  - `init_score`
  - `final_score`
  - `init_search_score`
  - `final_search_score`
  - `score_gain`
  - `init_match`
  - `final_match`
  - `match_gain`
- selection / continuation provenance:
  - `pool_member`
  - `eligible`
  - `selected`
  - `selection_policy`
  - `selection_rank`
  - `rejected`
  - `reject_reason`
  - `admitted_by_next_stage`
  - `next_stage_accept_reason`
  - `continued_best_candidate_hash`
  - `continued_best_score`
  - `continued_best_match`
- structural / family:
  - `start_hash`
  - `end_hash`
  - `family_view_id`
  - `family_id`
  - `within_family_rank`
  - `distance_to_anchor`
  - `nearest_selected_distance`
  - `nearest_better_truth_distance`
- lexical / shape:
  - `preview_text`
  - `word_ngram_summary`
  - `lexical_request_count`
  - `lexical_threshold_skip_count`
  - `lexical_tie_count`

## Canonical record 2: pool-summary row

Target use:

- one row per decision pool at a stage boundary
- enough to reason about "how many hills were present and how much compression
  happened?"

Proposed minimum fields:

- pool identity:
  - `run_id`
  - `tier_name`
  - `text_id`
  - `key_seed`
  - `stage_boundary`
  - `pool_id`
  - `pool_status`
  - `selection_policy`
  - `family_view_id`
- pool shape:
  - `row_count`
  - `eligible_row_count`
  - `selected_row_count`
  - `unique_candidate_hash_count`
  - `unique_start_hash_count`
  - `unique_end_hash_count`
  - `source_counts`
  - `lane_counts`
- family / distance summary:
  - `family_count`
  - `selected_family_count`
  - `top_band_family_count`
  - `largest_family_share`
  - `anchor_candidate_hash`
  - `mean_distance_to_anchor`
  - `min_distance_to_anchor`
  - `max_distance_to_anchor`
  - `selected_pairwise_distance_min`
  - `selected_pairwise_distance_mean`
- continuation summary:
  - `next_stage_started_count`
  - `next_stage_admitted_count`
  - `next_stage_rejected_count`
  - `best_continued_candidate_hash`
  - `best_continued_score`
  - `best_continued_match`

## Current artifact coverage map

### Already mostly covered

- run index / outcome:
  - `run_config.json`
  - `run_manifest.json`
  - `final_instances/*.json`
  - `best/best_instance.json`
- Phase C starts:
  - `stage3_diagnostics.phaseC_start_summaries`
  - `phasec_start_checkpoints.jsonl`
- Stage 3.5 seeds / archive / partial progress:
  - `stage3_diagnostics.stage35_seed_rows`
  - `stage3_diagnostics.stage35_archive_rows`
  - `stage35_partial_state.json`
  - `stage35_progress.jsonl`

### Missing or incomplete now

- no single canonical partial-state row schema shared across:
  - Phase C start summaries
  - Stage 3.5 seed rows
  - Stage 3.5 archive rows
- Stage 2 promoted pool and Stage 3 prep/init pool are not persisted as
  reviewer-facing **available-vs-selected** candidate pools with stable
  identity/provenance fields
- Phase C candidate-pool summaries are still mostly aggregate counts; they do
  not persist enough row-level relational fields at the decision boundary:
  - `family_id`
  - `distance_to_anchor`
  - `nearest_selected_distance`
  - explicit `selected` / `eligible` flags for every available row
- Stage 3.5 archive rows do not yet persist enough transition structure to map
  continuation edges directly:
  - `parent_candidate_hash`
  - `rejected` / `reject_reason` for non-admitted archive rows
  - `continued_best_candidate_hash` links for seed rows
- no canonical pool-summary rows with fixed family/diversity metrics that can
  be compared across stage boundaries

## Recommended implementation order

1. Define a small shared serializer for the two canonical record types above.
   Do not change solver decisions.
2. Adapt one late boundary first:
   - Phase C actual starts
   - Stage 3.5 seed rows
   - Stage 3.5 archive snapshots
3. Add missing parent/selection/family fields there.
4. Emit one reviewer-facing pool-summary JSON per adapted boundary.
5. Only after that, backfill earlier boundaries:
   - Stage 2 promoted pool
   - Stage 3 init / prep pool

## Classification labels to support later

Initial manual or rule-based labels should be auditable from the saved fields:

- `dead_path`
- `false_friend`
- `weak_family_survivor`
- `promising_outsider`
- `undervalued_good_family`
- `good_family_not_exploited`
- `repair_candidate`

These labels are not a live policy yet. They are a science/reporting layer for
space mapping first.

## Bottom line

The next data-contract task should make Phase C and Stage 3.5 candidate pools
look like one comparable graph of partial states, not disconnected ad hoc
diagnostics dumps.

## 2026-04-02 implementation status

Landed:

- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - emits `space_map_v1.partial_state_rows`
  - emits `space_map_v1.pool_summaries`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - stores that payload under:
    - `stage3_diagnostics.space_map_v1`
- `tools/benchmarks/periodic_sub_trans/no_wli/audit_space_map_v1_summary.py`
  - scans saved final artifacts and writes reviewer-facing
    `pool_summaries.csv`

First hardcoded p5 one-job lane prepared:

- `STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p5"`
- grid:
  - `p5/c1`
  - `seed411`
- preset:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- experiment id:
  - `tune_v53_p5c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`

Focused proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_audit_space_map_v1_summary.py -q`
- result:
  - `23 passed`

## 2026-04-03 hardening status

Landed:

- `tools/benchmarks/periodic_sub_trans/no_wli/run_pipeline_execution.py`
  - threads `run_id = run_dir.name` into runner state before iteration
    finalization
- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - adds `pool_status`
  - marks empty `phaseC_start` pools as `not_run` when `phaseC_ran != 1`
  - marks other empty pools as `empty`
- `tools/benchmarks/periodic_sub_trans/no_wli/audit_space_map_v1_summary.py`
  - exposes `pool_status` in `pool_summaries.csv`

Current one-job control setup:

- `STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p5"`
- grid:
  - `p5/c1`
  - `seed511`
- experiment id:
  - `tune_v54_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_single_1job`

## 2026-04-03 classifier / atlas slice

Added a first-pass classifier spec and a hardcoded offline atlas extractor:

- `planning_old/working/no_wli_space_map_v1_classifier_spec_2026-04-03.md`
- `tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
- `tests/tools/test_no_wli_extract_space_map_v1_atlas.py`

Atlas output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/<timestamp>__space_map_v1_atlas/row_atlas.csv`
- `.../pool_atlas.csv`
- `.../transition_atlas.csv`
- `.../run_atlas.csv`
- `.../summary.json`

Design rule:

- these row/pool/run labels are deterministic science annotations only
- they do not affect live search
- when current `space_map_v1` is insufficient, the extractor emits explicit
  data-gap flags such as `phasec_pool_not_row_complete` or
  `missing_parent_candidate_hash`

First atlas run:

- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260403T143429Z__space_map_v1_atlas/summary.json`
- scanned artifacts:
  - `361`
- extracted rows:
  - `row_atlas_rows = 81`
  - `pool_atlas_rows = 15`
  - `transition_atlas_rows = 53`
- run labels:
  - `solved_control = 47`
  - `stage35_guard_reject = 5`
  - `stage35_live_win = 3`
  - `unclassified_run = 306`
- strongest current data-gap flags:
  - `missing_space_map_v1 = 356`
  - `missing_space_map_run_id = 50`
  - `missing_distance_to_anchor = 71`
  - `missing_parent_candidate_hash = 28`
  - `missing_continued_best_links = 4`
  - `phasec_pool_not_row_complete = 2`

Immediate interpretation:

- the extractor contract works
- current `space_map_v1` coverage is still concentrated in recent runs only
- row labels remain mostly `unclassified_row` because many rows lack distance,
  parent-link, or richer family fields
- this is useful evidence for the next data-contract slice:
  - add stronger parent/family/distance fields where cheap
  - backfill historical artifacts only if needed for a broader atlas

## 2026-04-03 saved-row boundary hardening slice

Landed:

- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - derives `parent_candidate_hash` for non-root Phase C starts from the Phase C
    anchor hash
  - derives `parent_candidate_hash` for non-root Stage 3.5 seed/archive rows
    from the baseline candidate hash when a direct parent is missing
  - computes `distance_to_anchor` from the run's family view when row keys are
    available
  - assigns cluster-based `family_id` values using the same
    `phaseC_novel_view_id` geometry
  - populates baseline seed-row continuation links:
    - `continued_best_candidate_hash`
    - `continued_best_score`
    - `continued_best_match`
    - `next_stage_accept_reason`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - passes `columns` into the space-map serializer
- `tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
  - no longer flags Phase C anchors and Stage 3.5 baseline seed rows as
    missing-parent gaps just because they are root rows
- `tests/tools/test_no_wli_partial_state_space_map.py`
  - guards parent links, family IDs, anchor distance, and continuation links

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_extract_space_map_v1_atlas.py tests/tools/test_no_wli_audit_space_map_v1_summary.py -q`
- result:
  - `7 passed`

Atlas smoke test:

- `C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260403T144434Z__space_map_v1_atlas`

Caveat:

- existing `v55` / `v57` artifacts were written before this serializer patch,
  so their saved `space_map_v1` rows do not yet contain the new derived
  parent/distance/family fields
- the improved fields will appear in the next fresh one-job artifacts

## 2026-04-03 Stage 2 / Stage 3 prep pool extension

Landed:

- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - adds `stage2_promoted` partial-state rows and pool summaries
  - adds `stage3_prep` partial-state rows and pool summaries from
    `stage3_prep_live.init3`
  - adds row-complete `phaseC_pool` partial-state rows and pool summaries from
    `stage3_diagnostics.phaseC_candidate_pool_rows`
  - keeps Stage 3 prep scores/truth blank when those fields are not available
    in the prep handoff state, rather than inventing synthetic values
  - uses `stage3_entry_allocation_policy` as the Stage 3 prep selection policy
  - marks missing Stage 3 prep pools as `not_run` when no prep handoff exists
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - returns Phase C candidate-pool rows with explicit
    `eligible_novel_challenger`, `novelty_distance_to_anchor`, and
    `selected_by_phasec_start` annotations
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  - threads Phase C candidate-pool rows into finalize state
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
  - persists Phase C candidate-pool rows into `stage3_diagnostics`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - passes `stage2_promoted` and `stage3_prep_live` into the space-map
    serializer
  - forwards Phase C candidate-pool rows into Stage 3 diagnostics
- `tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
  - treats `stage2_promoted` rows as root rows for parent-link gap detection
  - treats the Stage 3 prep anchor row as a root row
  - checks Phase C row completeness against `phaseC_pool` when available
- `tests/tools/test_no_wli_partial_state_space_map.py`
  - now guards `stage2_promoted`, `stage3_prep`, `phaseC_pool`,
    `phaseC_start`, and Stage 3.5 row/pool serialization

Validation:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_partial_state_space_map.py tests/tools/test_no_wli_extract_space_map_v1_atlas.py tests/tools/test_no_wli_audit_space_map_v1_summary.py -q`
- result:
  - `7 passed`

Remaining gap:

- Stage 3 prep mutated-row parentage is still a fallback star link to the prep
  anchor when exact mutation origin metadata is absent from `stage3_prep_live`.
  That preserves schema consistency without changing solver logic, but it is
  not yet an exact ancestry graph.

Recommended next check:

- run one fresh short p5/p7 smoke artifact under the new serializer
- inspect `space_map_v1` and the atlas output on that fresh run
- only then collect more comparison runs

## 2026-04-03 fresh p5 smoke setup

Prepared:

- `STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p5"`
- grid:
  - `p5/c1`
  - `seed511`
- experiment id:
  - `tune_v58_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_space_map_v1_smoke_single_1job`

Post-run checks:

- `space_map_v1.pool_summaries` should include:
  - `stage2_promoted`
  - `stage3_prep`
  - `phaseC_pool`
  - `phaseC_start`
  - `stage35_seed`
  - `stage35_archive`
- p5 solved-control behavior should remain no-harm
- then run `tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
  and inspect the new artifact in the generated atlas tables

## 2026-04-03 one-shot v58 smoke watcher and v59 fresh-seed ladder

Prepared:

- `planning_old/working/no_wli_v58_watch_and_launch_v59_2026-04-03.ps1`
- `planning_old/working/no_wli_v59_launch_ladder_small_2026-04-03.ps1`

Smoke-pass contract:

- `best_match_ratio = 1.0`
- non-empty `space_map_v1.run_id`
- `space_map_v1.pool_summaries` contains all six mapped boundaries with
  non-empty `pool_status`
- non-empty `space_map_v1.partial_state_rows`

If the smoke artifact passes, the watcher runs the atlas extractor, switches
`STAGE35_BASELINE_SELECTOR_COMPARE_MODE` to `candidate_ladder_small`, and
launches one bounded ladder run with fresh seeds `611` and `711`.

No automatic chaining is allowed beyond `v59`.

## 2026-04-03 v58 smoke readout

Fresh artifact:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260403T151917509031Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p5_c1_l1000__text0__seed511.json`

Serializer check:

- `space_map_v1.run_id` is populated
- `space_map_v1.partial_state_rows` is non-empty
- `space_map_v1.pool_summaries` includes all six mapped boundaries:
  - `stage2_promoted`
  - `stage3_prep`
  - `phaseC_pool`
  - `phaseC_start`
  - `stage35_seed`
  - `stage35_archive`
- p5 no-Phase-C control statuses are explicit:
  - `phaseC_pool.pool_status = "not_run"`
  - `phaseC_start.pool_status = "not_run"`

Atlas check:

- `tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260403T155429Z__space_map_v1_atlas`

Interpretation:

- the current serializer coverage is good enough to start collecting fresh
  comparison runs
- old atlas warnings are still dominated by pre-`space_map_v1` artifacts, which
  is expected

Next:

- run the fresh-seed `v59` ladder:
  - `seed611`
  - `seed711`

## 2026-04-03 seed-category objective for fresh-space-map runs

The next fresh-seed runs are not just extra samples. The goal is to test
whether the saved hill/family geometry starts to form repeatable seed
categories.

Working rule:

- keep `seed411` as the anchor case for continuity with the known hard-case
  `9002...` mechanism
- use `seed611` and `seed711` to ask whether new seeds fall into:
  - a repeated solved-control family,
  - a repeated `411`-like hard continuation family,
  - or a genuinely different hard family

Warning condition:

- if every seed appears unique under `space_map_v1`, do not immediately assume
  that the solver problem is intrinsically unstructured
- first check whether `family_id`, `distance_to_anchor`, and
  `parent_candidate_hash` are still too weak or too fallback-heavy to expose
  repeated hill structure

Required post-run atlas comparisons:

- per-seed `run_type`
- per-boundary pool concentration:
  - `family_count`
  - `largest_family_share`
  - selected-vs-available family coverage
- repeated lineage signatures:
  - does the same family survive from `stage2_promoted` to `stage35_archive`?
  - do accepted Stage 3.5 rows share family IDs or parent-path motifs across
    seeds?

Decision rule:

- pick the next seeds deliberately to fill taxonomy gaps, not at random
- prefer one candidate seed that looks like a same-family repeat and one that
  looks like a new hard family

## 2026-04-03 score-stop shadow v2 analysis spec

New review spec:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/SPEC.md`

Why it belongs next to `space_map_v1`:

- the goal is to test whether high-scoring near-solved rows occupy a region of
  score/report space that is separable from false friends
- that requires row-level state, family/anchor metadata, replay-decryptability,
  and explicit missing-data flags rather than only final-run summaries

Current data-contract implications:

- `space_map_v1` is now rich enough to define the candidate-row universe across
  Stage 2 promoted, Stage 3 prep, Phase C, and Stage 3.5 boundaries
- it is not yet row-complete for word-ngram reports, so the first
  `score_stop_shadow_v2` extractor should replay-score rows from plaintext/key
  where possible and label missing scorer/runtime dependencies explicitly
- `stage3_prep` and `stage2_promoted` rows may require decrypt-then-score
  replay because current fresh artifacts often save key material but not
  plaintext or search/judge scores at those boundaries

Maintained rule:

- do not promote a raw high-score cutoff from this analysis directly
- use `would_dump` and `would_stop` shadow labels first, then evaluate
  false-stop risk on fixture truth

Current score-panel narrowing:

- `score_stop_shadow_v2` is now in a bounded `score_panel_v1` mode for the first
  score-only pass
- old artifacts without `space_map_v1` are allowed in this mode because they
  are still useful for old `0.7-ish` / mid-quality score calibration
- only late boundaries are replay-scored:
  - `stage2_topk`
  - `stage3_topk`
  - `phaseC_start`
  - `stage35_seed`
  - `stage35_archive`
- family-stability `would_stop` is disabled for this pass
- this means current outputs should be read as **score-panel dump calibration**,
  not family-graph or stop-policy evidence

Current family-panel narrowing:

- `score_stop_shadow_v2` now also has a tiny `family_panel_v1` mode
- it is restricted to five fresh modern artifacts:
  - solved control `seed511`
  - selector-sensitive hard win `seed411`
  - selector-neutral hard win `seed1011`
  - selector-sensitive reject `seed811`
  - selector-neutral reject `seed911`
- only late mapped boundaries are replay-scored:
  - `phaseC_pool`
  - `phaseC_start`
  - `stage35_seed`
  - `stage35_archive`
- this mode should be read as **family-aware dump calibration**, not as a live
  stop benchmark

Legacy fallback expansion:

- for old artifacts without `space_map_v1`, `score_stop_shadow_v2` now also
  imports `stage2_topk` and `stage3_topk` rows when those rows contain saved
  key/plaintext state
- this is intentionally a score-panel fallback only, not a family-map claim
- `stage3_topk.end_hash` is reused as `candidate_hash` where available, and
  otherwise a stable key hash is derived from `key_idx`
- if a legacy `phaseC_start` summary row omits key/plaintext state, the
  extractor now backfills that state from a same-hash `stage3_topk` fallback
  row in the same artifact when available

Residual fallback limits:

- some legacy `phaseC_start` hashes do not match `stage3_topk` hashes or
  `resume_handoffs/.../stage3_prep.json` keys under `stable_key_hash`, so those
  rows still remain key/plaintext-missing and are explicitly flagged
- some legacy runs do not expose a usable word-ngram report runtime; the
  extractor should keep surfacing `word_ngram_unavailable_for_run` instead of
  guessing a modern scorer config

## 2026-04-04 fresh family-mapping overnight panel

Next data-collection run:

- `candidate_family_overnight`

Grid:

- `p7/c1 seed411`
- `p7/c1 seed611`
- `p9/c3 seed411`
- `p9/c3 seed611`

Reason:

- use `411` as the anchor seed and `611` as a fresh comparator
- collect current-serializer `space_map_v1` artifacts for one easier family
  control class and one hard family class
- keep the panel small enough that the next-day atlas readout is still
  interpretable

Do not claim global hill identity from this run:

- `family_id` remains run-local
- the goal is first to check whether family-collapse and parent-link patterns
  look qualitatively repeatable across these seeds, not to promote a new global
  family taxonomy

## 2026-04-04 first fresh `v61` map readout

Artifacts used:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260404T074732265025Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p7_c1_l1000__text0__seed411.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260404T114639913723Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p7_c1_l1000__text0__seed611.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260404T154911594408Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed411.json`

Processed atlas/audit outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260404T212752Z__space_map_v1_atlas`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260404T212751Z__space_map_v1_audit`

Observed late-space patterns:

- `p7/c1 seed411` and `p7/c1 seed611`
  - both solved at `stage35_substitution_only` with `best_match_ratio = 1.000`
  - both had `phaseC_start.family_count = 2`
  - both had `phaseC_start.largest_family_share = 0.833`
  - both had `stage35_seed.family_count = 1`
  - both had `stage35_archive.family_count = 1`
  - interpretation:
    - the easy-control late stage currently collapses to one dominant family in
      a repeatable way across these two seeds
- `p9/c3 seed411`
  - reproduced the accepted `9002...` branch:
    - `stage35_baseline_candidate_hash = 9002ee09917e5a0d`
    - `stage35_best_candidate_hash = 1fdc6d7d88e80a2b`
    - `best_match_ratio = 0.487`
  - `phaseC_start.family_count = 6`
  - `phaseC_start.largest_family_share = 0.167`
  - `stage35_seed.family_count = 2`
  - `stage35_archive.family_count = 1`
  - interpretation:
    - unlike the easy p7 controls, the hard anchor keeps a much broader
      multi-family `phaseC_start` frontier before Stage 3.5 narrows to the
      accepted `9002...` family

Remaining map question:

- `p9/c3 seed611` did not run before the 12h fixture-matrix cap, so the first
  fresh hard-seed family-repeatability test is still missing
- this reinforces the need for a benchmark-only solved-stop gate on already
  solved controls before collecting another hard-seed family panel

Implementation semantics now fixed in
`tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/extract_score_stop_shadow_v2.py`:

- newest-first artifact scan before `MAX_ARTIFACTS`
- explicit dump-vs-stop split at run-summary level
- strongest matching family-stability support threshold wins
- repo-relative path emission is robust for temp/test artifacts

First extractor-pass data contract lesson:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260404T015035Z__score_stop_shadow_v2`
  analyzed `936` row records but emitted no active rule rows
- all rows had `replay_word_ngram_available = false`
- all rows had blank `family_id_kind`

Interpretation:

- the extractor logic is running, but the current saved artifacts are still too
  stale and/or too sparse in word-ngram replay metadata to support a meaningful
  first threshold study
- before any stop-rule tuning, collect one fresh artifact under the latest
  `space_map_v1` serializer and rerun `score_stop_shadow_v2`

## 2026-04-03 reviewer-facing map semantics hardening

Review response implemented:

- pool summaries now distinguish whole-pool family structure from selected-set
  family structure more honestly:
  - `family_count` remains the whole-pool family count
  - `selected_family_count` now counts families in the selected subset
  - `selected_pairwise_distance_min` / `selected_pairwise_distance_mean` are now
    selected-subset distances
  - `top_band_family_count` is computed from the top selected-band rows instead
    of being a blind alias for `family_count`
- partial-state rows now carry explicit provenance for inferred graph/family
  metadata:
  - `parent_link_kind = "root" | "observed" | "fallback_anchor"`
  - `family_id_kind = "run_local_cluster" | "hash_fallback" | "saved_row"`
- atlas gap detection now avoids two over-flags:
  - baseline/root `stage35_archive` rows are valid root rows
  - missing Stage 3.5 progress-path flags are only raised when Stage 3.5 is
    actually relevant to the artifact

Interpretation discipline:

- `family_id` should be treated as a **run-local** family cluster label, not a
  stable global hill identifier across seeds/runs
- `parent_link_kind = "fallback_anchor"` edges preserve map connectivity for
  diagnostics, but they are not exact ancestry claims
- `stage2_promoted` and `stage3_prep` remain selected/init-level views, not yet
  full upstream available-vs-selected compression maps

## 2026-04-05 reviewer-facing late-pool count semantics

Additional reviewer-facing pool-summary fields now exist:

- `review_primary_row_count`
- `review_primary_row_count_kind`
- `review_primary_relation`

Meaning:

- for most boundaries:
  - `review_primary_row_count_kind = selected_row_count`
  - `review_primary_relation = selected_vs_available`
- for `stage35_seed`:
  - `review_primary_row_count_kind = next_stage_started_count`
  - `review_primary_relation = started_vs_available`

Reading rule:

- keep `selected_row_count` as the strict serialized selected-set count
- when summarizing `stage35_seed`, use the reviewer-facing primary-count fields
  rather than raw `selected_row_count`

