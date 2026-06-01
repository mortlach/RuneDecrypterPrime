# Stage 3.5 speed-first focus proposal

Date: `2026-04-02`

## Why the focus is changing

The current full-budget candidate run already tells us something important even
before completion:

- the selector does choose a different Stage 3.5 baseline row
- but the candidate Stage 3.5 path is operationally much more expensive than
  the completed legacy long lane

So the immediate bottleneck is no longer:

- can we select a different row?

It is now:

- can Stage 3.5 evaluate that row fast enough and clearly enough to be a
  practical solve path?

## What the current `v50` run has already shown

From the live candidate log:

- `stage35-start`
  - `selector = score_plus_novelty`
  - `baseline_hash = 9002ee09917e5a0d`
  - `baseline_source = phaseA_selected`
  - `baseline_lane = challenger`
  - `baseline_source_rank = 2`
  - `baseline_score = 0.172845`

This already answers the first live question:

- yes, the candidate lane chose a different Stage 3.5 baseline row

But the same live log also shows the runtime problem:

- `seed_rows_scored` at `elapsed = 2.148s`
- `round_progress round=1/3 mini=1/18 ... elapsed = 1763.575s`
- `round_progress round=1/3 mini=8/18 ... elapsed = 12245.814s`
- `round_progress round=1/3 mini=16/18 ... elapsed = 24495.704s`

Compare that to the completed `v48` legacy long lane:

- full legacy Stage 3.5 runtime:
  - `27080.954s`
- and that legacy runtime covered all `3` rounds

So the candidate path has already spent almost the full legacy Stage 3.5 budget
without even finishing round `1 / 3`.

## Working diagnosis

The late-stage selector logic is not the immediate blocker now.

The immediate blocker is Stage 3.5 runtime shape on the stronger candidate
path:

- heavier local mini-search work
- long silent blocks between useful decisions
- no persisted partial Stage 3.5 archive during the run

That makes the current candidate lane hard to finish and hard to inspect.

## Why Stage 3.5 can now be worked on directly

We already have enough persisted data to isolate it.

Reliable inputs now available:

- `run_config.json`
- `final_instances/*.json`
- `stage3_diagnostics.phaseC_start_summaries`
- `phasec_start_checkpoints.jsonl`
- replay-ready candidate key/plaintext material for the replayable `411` case

Existing isolation/replay entry points:

- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - `run_stage35_resume_from_artifact(...)`
  - `run_stage35_from_selected_trial_row(...)`
- `tools/benchmarks/periodic_sub_trans/no_wli/replay_stage35_substitution_solver.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/phasec_frontier_rows.py`

So Stage 3.5 speed work does not need to wait on full live solves.

## Proposed work order

### 1. Speed and observability first

Before more solve-quality interpretation, make Stage 3.5 cheap and visible
enough to iterate on.

Priority items:

- add wall-clock timestamps to Stage 3.5 logs
- add `mini_search_start` progress events
- add periodic persisted partial Stage 3.5 state dumps
- add explicit per-lane caps and an `unfinished/capped` persisted outcome

Status update:

- wall-clock timestamps are now in Stage 3.5 log lines
- `mini_search_start` events are now emitted
- periodic partial Stage 3.5 persistence is now implemented in the live
  followup wrapper:
  - `stage35_partial_state.json`
  - `stage35_progress.jsonl`
- explicit Stage 3.5 outcome persistence is now threaded through the live
  result surface:
  - `outcome_status`
  - `outcome_reason`
  - `completed`
  - `capped`
  - partial dump / progress filenames and write counts
- focused proof after the persistence slice:
  - `tests/tools/test_no_wli_artifact_resume.py`
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - `tests/tools/test_no_wli_stage35_replay_profile.py`
  - `tests/tools/test_no_wli_stage35_substitution_solver.py`
  - result: `55 passed`

### 2. Replay Stage 3.5 in isolation

Use replayable artifact cases first, not full pipeline runs.

Main loop:

- load replayable `411` artifact
- run Stage 3.5 from:
  - the legacy row
  - the selected candidate row
- vary Stage 3.5-only settings
- measure:
  - runtime
  - evals
  - archive size
  - acceptance result
  - best downstream truth/score

New replay benchmark harness:

- `tools/benchmarks/periodic_sub_trans/no_wli/profile_stage35_replay_hotspots.py`

It profiles saved Stage B rows from:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/selected_trial_material_rows.json`

and writes repo-relative outputs under:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/`

First reduced replay-profile run:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260402T151731Z__profile_stage35_replay_hotspots_v1/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260402T151731Z__profile_stage35_replay_hotspots_v1/case_timings.csv`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260402T151731Z__profile_stage35_replay_hotspots_v1/profiles/candidate__score_plus_novelty/cprofile_top_cumulative.txt`

Reduced Stage 3.5 sample config used:

- `rounds = 1`
- `seed_keep = 2`
- `beam_width = 2`
- `archive_keep = 8`
- `mini_search_steps = 1`
- `mini_search_beam_width = 2`
- `mini_search_final_keep = 1`

Observed replay timing split:

- legacy rows:
  - `6.095s` to `8.341s`
  - `2479` evals
  - `accept_reason = search_score_drop_guard_failed`
- `score_plus_novelty` rows:
  - `16.324s` to `16.807s`
  - `8704` evals
  - `accept_reason = accepted`

So even under a reduced 1-round replay, the stronger candidate path is already
roughly `2x` to `3x` heavier than legacy while also being the path that flips
from guard failure to acceptance.

The first cumulative hotspots are:

- `run_slice_local_mini_search`
- Stage 3.5 row/key scoring:
  - `_score_key_rows`
  - `_score_rows_for_keys`
- scorer batch execution:
  - `score_plaintexts_chunked`
  - `torch_rune_scorer.batch_score`
  - `_lookup_logp_linear_probe`
- nontrivial Python-side archive/ordering overhead:
  - `stable_key_hash`
  - selector ranking / sorting

The solver itself now also emits internal telemetry buckets, not just outer
`cProfile` totals. New persisted Stage 3.5 telemetry includes:

- row scoring wallclock
- decrypt time
- scorer batch-score time
- candidate-hash time during scoring
- mini-search generation / scoring / ranking time
- proposal materialization time
- archive update time
- archive ranking time
- beam ranking time
- average scorer batch size
- average proposals / rows scored / rows kept per mini-search
- per-mini summaries including proposal counts and unpruned archive-candidate
  pool growth

This makes the next config sweep much more actionable because it can now answer
whether cost is growing mainly through:

- more proposals per mini-search
- more scorer work per proposal set
- or Python-side archive/ranking churn

### 3. Optimize runtime before quality

The current best next engineering question is:

- how do we get a practically bounded Stage 3.5 pass on the better candidate
  row?

Only after that should the main question become:

- does that bounded pass still improve continuation quality?

### 3a. First one-knob replay sweep result

The first Stage 3.5-only sweep has now been run on the stable saved `v46`
Stage B rows using:

- `tools/benchmarks/periodic_sub_trans/no_wli/sweep_stage35_replay_configs.py`

Output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_sweep/20260402T154929Z__sweep_stage35_replay_configs_v1/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_sweep/20260402T154929Z__sweep_stage35_replay_configs_v1/variant_summary.csv`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_sweep/20260402T154929Z__sweep_stage35_replay_configs_v1/case_rows.csv`

The sweep kept everything else fixed and varied one knob family at a time in
the planned order:

- `mini_search_top_symbols`
- `beam_width`
- `mini_search_final_keep`
- `archive_keep`

Main result:

- `beam_width_1` is the first clearly useful boundedness lever
- it preserves the important replay split:
  - legacy rows still fail `search_score_drop_guard_failed`
  - `score_plus_novelty` rows still end `accepted`
- and it cuts candidate cost materially relative to the baseline replay config

Cross-checked evidence from `variant_summary.csv`:

- baseline candidate:
  - wallclock `15.017s`
  - proposals generated `8704`
  - row scoring `12.305s`
- `beam_width_1` candidate:
  - wallclock `8.152s`
  - proposals generated `4352`
  - row scoring `6.220s`
- ratios versus baseline:
  - runtime `0.543`
  - proposals `0.500`
  - row scoring `0.505`

Negative / less useful findings from the same sweep:

- reducing `mini_search_top_symbols` to `8` or `6` preserved the acceptance
  split but made runtime worse, not better
- `beam_width_2` was effectively neutral
- `mini_search_final_keep = 1` gave only a marginal gain
- `archive_keep = 8` gave only a marginal gain

Working interpretation:

- the first meaningful speed lever is reducing Stage 3.5 beam width, not
  reducing top-symbol branching first
- proposal explosion and scorer work are still the dominant cost centres
- archive pressure remains a secondary concern for runtime at this stage

### 3b. First bounded replay baseline run

The first artifact-producing bounded replay run has now been completed using:

- `tools/benchmarks/periodic_sub_trans/no_wli/run_stage35_bounded_replay_baseline.py`

Output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T163527Z__stage35_bounded_replay_baseline_v1/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T163527Z__stage35_bounded_replay_baseline_v1/case_summary.csv`
- per-case Stage 3.5 artifacts under:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T163527Z__stage35_bounded_replay_baseline_v1/cases/`

Bounded config used:

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

Observed result:

- all `4 / 4` replay cases completed without capping
- acceptance split preserved for both fixtures:
  - legacy rows still failed `search_score_drop_guard_failed`
  - `score_plus_novelty` rows still ended `accepted`
- runtime stayed comfortably bounded:
  - legacy:
    - `2.001s`
    - `2.275s`
  - `score_plus_novelty`:
    - `6.328s`
    - `7.288s`
- per-case Stage 3.5 artifacts were written:
  - `stage35_partial_state.json`
  - `stage35_progress.jsonl`
- per-case persistence counts:
  - `progress_events_written = 16`
  - `partial_dump_write_count = 4`

Interpretation:

- `beam_width_1` is now more than just the best row in the sweep table
- it is a usable bounded replay baseline that:
  - preserves the key replay accept/reject split
  - stays well inside the explicit runtime cap
  - writes readable partial/progress artifacts for inspection

### 4. Return to live runs after Stage 3.5 is bounded

Once Stage 3.5 runtime is under control on replayable cases:

- rerun the 1-job live candidate lane
- then read:
  1. baseline row changed?
  2. admission changed?
  3. downstream continuation beat the locked legacy long lane?

## Concrete proposal for the next run

The next run should ideally be:

- a Stage 3.5-focused replay/resume run
- not another full end-to-end solve first

Concrete boundedness direction now supported by evidence:

- adopt `beam_width_1` as the first bounded replay candidate baseline
- use the new partial-dump / capped-outcome contract inside the replay loop
  while keeping `beam_width_1` as the active bounded baseline
- then rerun one fresh live candidate confirmation job only after the bounded
  Stage 3.5 config itself is locked

That gives the fastest path to:

- speed improvements
- clear instrumentation
- and only then solve-quality comparison

## Bottom line

The best next task is:

- optimize and instrument Stage 3.5 in isolation first

Not because solve quality stopped mattering, but because the current live
candidate result already shows that Stage 3.5 runtime is the limiting factor.

## 2026-04-02 bounded replay rerun and bounded live promotion

The bounded replay baseline was rerun again before promoting it into a fresh
live candidate lane:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T171133Z__stage35_bounded_replay_baseline_v1/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260402T171133Z__stage35_bounded_replay_baseline_v1/case_summary.csv`

The rerun preserved the same split:

- legacy rows:
  - `accept_reason = search_score_drop_guard_failed`
- `score_plus_novelty` rows:
  - `accept_reason = accepted`
- all `4 / 4` cases:
  - `completed = 1`
  - `capped = 0`

And it remained comfortably bounded:

- legacy:
  - `0.977s`
  - `1.031s`
- `score_plus_novelty`:
  - `3.043s`
  - `4.094s`

Live follow-up is now set to a fresh bounded 1-job candidate preset in:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

with:

- preset:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- experiment id:
  - `tune_v51_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`

That live preset keeps the same upstream `seed411` candidate lane but promotes
the bounded Stage 3.5 shape:

- `beam_width = 1`
- `seed_keep = 2`
- `archive_keep = 12`
- `rounds = 1`
- `mini_search_steps = 1`
- `mini_search_beam_width = 2`
- `mini_search_top_symbols = 10`
- `mini_search_final_keep = 2`
- `mini_search_keep_all_rows = 0`
- `max_runtime_seconds = 14400.0`

## 2026-04-02 bounded live candidate confirmation

The fresh bounded 1-job candidate lane completed cleanly:

- experiment id:
  - `tune_v51_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`
- run artifact:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260402T171534470152Z__bench_solve_pipeline_no_wli__048e35c/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed411.json`
- run console:
  - `planning_old/working/no_wli_stage35_v51_live_console_2026-04-02.log`

Result against the locked `v48` legacy long lane:

- baseline row differed:
  - `v48` legacy:
    - `stage35_baseline_candidate_hash = 73eee2bf84b7c07f`
    - `stage35_baseline_candidate_source = stage3_best_phaseB`
    - `stage35_baseline_candidate_lane = anchor`
  - `v51` bounded candidate:
    - `stage35_baseline_selector = score_plus_novelty`
    - `stage35_baseline_candidate_hash = 9002ee09917e5a0d`
    - `stage35_baseline_candidate_source = phaseA_selected`
    - `stage35_baseline_candidate_lane = challenger`
    - `stage35_baseline_differs_from_phasec_score_winner = 1`
- Stage 3.5 admission changed:
  - `v48` legacy:
    - `stage35_accept_passed = 0`
    - `stage35_accept_reason = search_score_drop_guard_failed`
  - `v51` bounded candidate:
    - `stage35_accept_passed = 1`
    - `stage35_accept_reason = accepted`
- downstream continuation beat the locked legacy lane:
  - `v48` legacy:
    - `best_stage = stage2_search`
    - `best_match_ratio = 0.041`
    - `stage35_best_match = 0.038`
  - `v51` bounded candidate:
    - `best_stage = stage35_substitution_only`
    - `best_match_ratio = 0.487`
    - `stage35_best_match = 0.487`
    - `stage35_best_candidate_hash = 1fdc6d7d88e80a2b`
    - `stage35_truth_gain_vs_selected_row = 0.069`
    - `stage35_truth_gain_vs_phasec_score_winner = 0.448`

Runtime / boundedness read:

- full job wallclock:
  - `11948.520s`
- Stage 3.5 runtime:
  - `3286.700s`
- Stage 3.5 search budget actually used:
  - `rounds_completed = 1`
  - `evals = 4352`
  - `outcome_status = completed`
  - `completed = 1`
  - `capped = 0`

The new live Stage 3.5 persistence contract also worked:

- `stage35_partial_state.json`
- `stage35_progress.jsonl`
- `stage35_progress_event_count = 16`
- `stage35_partial_dump_write_count = 4`

Interpretation:

- the replay-proven mechanism transferred into the real live job under the
  bounded Stage 3.5 configuration
- the selector changed the baseline row, Stage 3.5 admitted that row, and the
  bounded continuation produced a materially better downstream result than the
  locked legacy long lane
- the final winner was not the original `9002...` row itself:
  - `9002...` was the admitted baseline row
  - the best continued row was `1fdc6d7d88e80a2b` from the `phaseB_topk` side
  - that is still the intended mechanism: the better baseline row unlocks a
    better continuation path

Maintained next step:

- do not reopen a broad live compare yet
- first inspect the persisted `stage35_progress.jsonl` and
  `stage35_partial_state.json` from the `v51` run to understand where the
  one-round bounded search still spends its ~55 minutes
- then decide whether the next Stage 3.5 improvement should be:
  - a second small bounded replay optimization pass
  - or a guarded promotion path for the bounded selector-plus-Stage-3.5 lane

## 2026-04-02 `v51` Stage 3.5 progress/partial-state inspection

The first inspection pass on the persisted `v51` Stage 3.5 artifacts says the
remaining one-round runtime is overwhelmingly row-scoring time, not archive
maintenance:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260402T171534470152Z__bench_solve_pipeline_no_wli__048e35c/stage35_progress.jsonl`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260402T171534470152Z__bench_solve_pipeline_no_wli__048e35c/stage35_partial_state.json`

Timing read from `stage35_progress.jsonl`:

- one accepted round ran `9` serial mini-searches
- all mini-search starts came from the same parent row:
  - `parent_candidate_hash = 82bc15ae884d34f6`
- per-mini wallclock ranged from `286.708s` to `417.389s`
- mean mini-search wallclock was `364.997s`
- total mini-search span was `3284.976s`, essentially all of the
  `3286.700s` Stage 3.5 runtime

Telemetry read from the persisted `finish` row:

- `row_scoring_seconds = 3286.330567400204`
- `archive_update_seconds = 0.00017620017752051353`
- `mini_search_count = 9`

Partial-state read:

- accepted baseline row:
  - `9002ee09917e5a0d`
- best final Stage 3.5 row:
  - `1fdc6d7d88e80a2b`
  - `seed_source = stage3_topk_phaseb`
  - `stage3_source = phaseB_topk`
  - `target_slice = 2`

Interpretation:

- `beam_width_1` solved archive growth enough for this one-round pass
- the remaining runtime problem is the repeated slice-local row scoring itself
- the next replay-speed pass should target the row-scoring path under
  `run_slice_local_mini_search`, not archive update / ranking first

Small implementation follow-up:

- `stage3_diagnostics` now persists `stage35_telemetry_summary` directly,
  instead of forcing consumers to recover that timing summary from
  `stage35_progress.jsonl`
- focused proof:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_stage35_substitution_solver.py -q`
  - result: `41 passed`

## 2026-04-02 replay-only duplicate rescoring audit

Question:

- are we wasting Stage 3.5 mini-search time by repeatedly scoring duplicate keys
  or proposals that collapse to the same normalized key after frozen-tail
  application?

Implementation slice:

- added mini-search telemetry for exact duplicate proposals skipped by the
  pre-scoring `seen` set
- added scoring-callback telemetry for normalized input count, normalized
  unique-key count, and normalized duplicate-key count
- added safe post-normalization dedupe in the scoring callback while preserving
  one returned row per original proposal in original order

Replay harness:

- `tools/benchmarks/periodic_sub_trans/no_wli/profile_stage35_replay_hotspots.py`
- stable input rows remain the `v46` Stage B selected-trial material

Result bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260403T001129Z__profile_stage35_replay_hotspots_v1/`

Result:

- exact duplicate proposal skips before scoring:
  - `candidate__legacy = 0`
  - `candidate__score_plus_novelty = 0`
  - `control__legacy = 0`
  - `control__score_plus_novelty = 0`
- duplicate normalized keys after frozen-tail application:
  - `candidate__legacy = 0 / 2479`
  - `candidate__score_plus_novelty = 0 / 8704`
  - `control__legacy = 0 / 2479`
  - `control__score_plus_novelty = 0 / 8704`
- acceptance split remained unchanged:
  - legacy rows still `search_score_drop_guard_failed`
  - `score_plus_novelty` rows still `accepted`

Interpretation:

- exact duplicate rescoring is not the current bottleneck on these replay rows
- the candidate path is slower because it generates and scores many more
  genuinely unique slice-local proposals
- the next replay-only speed pass should therefore target reducing the cost of
  scoring large volumes of unique local 2-swap proposals, not one-seed dedupe
  heuristics

Focused proof:

- `37 passed` for:
  - `tests/tools/test_no_wli_stage35_substitution_solver.py`
  - `tests/tools/test_no_wli_stage35_replay_profile.py`
  - `tests/tools/test_no_wli_artifact_resume.py`

## 2026-04-02 replay batch-chunk sweep under `beam_width_1`

Question:

- can larger scorer/decrypt batches make the same unique-proposal workload
  cheaper, without changing Stage 3.5 accept/reject behavior?

Implementation slice:

- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - added function-level `batch_eval_chunk_size` overrides for Stage 3.5
    replay entry points
- `tools/benchmarks/periodic_sub_trans/no_wli/profile_stage35_replay_hotspots.py`
  - switched the replay profile config to the current bounded
    `beam_width_1` shape
  - runs a hardcoded chunk sweep over `256`, `512`, and `1024`
  - emits chunk-qualified case ids and per-row chunk telemetry
- `tools/benchmarks/periodic_sub_trans/no_wli/run_stage35_bounded_replay_baseline.py`
  - uses `BATCH_EVAL_CHUNK_SIZE = 1024` for replay-only bounded baseline runs

Result bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_profile/20260403T002414Z__profile_stage35_replay_hotspots_v1/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/stage35_replay_bounded_baseline/20260403T002224Z__stage35_bounded_replay_baseline_v1/`

Result:

- acceptance split stayed unchanged for all tested chunk sizes:
  - legacy rows still `search_score_drop_guard_failed`
  - `score_plus_novelty` rows still `accepted`
- candidate fixture, `score_plus_novelty` selector:
  - chunk `256`: `solver_runtime_seconds = 8.438587199896574`
  - chunk `512`: `solver_runtime_seconds = 7.348186699906364`
  - chunk `1024`: `solver_runtime_seconds = 6.539424399845302`
- control fixture, `score_plus_novelty` selector:
  - chunk `256`: `solver_runtime_seconds = 7.665857300162315`
  - chunk `512`: `solver_runtime_seconds = 6.691823699977249`
  - chunk `1024`: `solver_runtime_seconds = 6.550577500136569`
- legacy rows were roughly neutral across chunk sizes:
  - `candidate__legacy` best observed at chunk `512`
  - `control__legacy` differences were small

Interpretation:

- larger replay batch chunks are a generic speed lever for the heavier accepted
  candidate path under the bounded `beam_width_1` shape
- this improves scorer throughput without relying on duplicate-key removal or
  seed/hash-specific behavior
- current maintained replay baseline:
  - `beam_width_1`
  - `BATCH_EVAL_CHUNK_SIZE = 1024`

Caution:

- this is still a replay-only batch-shape result, not a live default change
- the next live confirmation should happen only after one more replay sanity
  pass if needed

## 2026-04-02 frozen-ladder gate setup: replay is not enough for easy/medium controls

Artifact scan result:

- current saved outputs do contain replay-ready hard `p9/c3` Phase-C rows for
  `seed211`, `seed411`, and `seed511`
- but there are no replay-ready `phaseC_start_summaries` for the sampled
  easy/medium controls:
  - `fixture_fixture_001_p5_c1_l1000`
  - `fixture_fixture_001_p9_c1_l1000`
- therefore the generality gate cannot be answered purely from replay with the
  currently available artifact pool

Maintained interpretation:

- the `v51` bounded candidate lane is still a real live success on the known
  `seed411` hard case
- but that remains one-case mechanism proof, not a broad promotion
- the next guard should therefore be a **fresh small live candidate ladder
  run** that includes:
  - a known hard `411` case
  - easy/medium controls
  - one harder non-`9002...` family case

Config slice prepared:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  - active mode:
    - `STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_ladder_small"`
  - job grid:
    - `PERIODS_OVERRIDE = (5, 9)`
    - `COLUMNS_OVERRIDE_BY_PERIOD = {5: (1,), 9: (1, 3)}`
    - `RUN_SEEDS = (411, 511)`
  - preset:
    - `stage35_baseline_score_plus_novelty_live_bounded_p9`
  - planned truncation:
    - `MAX_JOBS = 6`
  - experiment id:
    - `tune_v52_ladder_small_stage35_baseline_selector_candidate_live_bounded_6job`

Operational constraint:

- do **not** leave the 6-job ladder mode as the active default
- if a long run is approved, that approval applies to that specific run only
- after that run attempt, reset the active hardcoded matrix mode to a shorter
  one-job lane unless a fresh explicit approval is given

Current config reset:

- `STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p5"`
- the ladder mode remains available in the config for a future explicitly
  approved run, but it is not the active default

Replay-data direction:

- next replay work should add richer saved state/category descriptors so we can
  stratify late-stage states and potentially use those categories to guide
  solver decisions later
- that should happen in replay artifacts first, before changing live decision
  logic

## 2026-04-02 first space-map data-contract slice landed

Implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/partial_state_space_map.py`
  - canonical `partial_state_rows`
  - canonical `pool_summaries`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - persists the combined payload under:
    - `stage3_diagnostics.space_map_v1`

Boundaries covered now:

- `phaseC_start`
- `stage35_seed`
- `stage35_archive`

What this gives immediately:

- one consistent row schema for late-stage states
- explicit selected/rejected/admitted flags where current diagnostics expose
  enough provenance
- basic pool-level counts, source/lane counts, exact-family counts, and
  selected-row pairwise key-distance summaries

Still missing:

- Stage 2 promoted pool and Stage 3 prep/init pool in the same canonical layer
- full Phase C available-vs-selected candidate-pool rows
- stronger fixed family labels beyond candidate-hash fallback

Focused proof:

- `43 passed` for:
  - `tests/tools/test_no_wli_partial_state_space_map.py`
  - `tests/tools/test_no_wli_truth_diagnostics.py`
  - `tests/tools/test_no_wli_stage35_substitution_solver.py`
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`

Readout contract:

- do not claim broad promotion from this ladder slice alone
- ask only:
  - does the bounded candidate lane remain helpful on the known `p9/c3 seed411`
    case?
  - does it avoid damaging the easier control cases?
  - does it behave reasonably on at least one hard case outside the dominant
    `9002...` disagreement family?

Focused proof:

- `39 passed` for:
  - `tests/tools/test_no_wli_stage35_bounded_replay_baseline.py`
  - `tests/tools/test_no_wli_stage35_replay_profile.py`
  - `tests/tools/test_no_wli_artifact_resume.py`
  - `tests/tools/test_no_wli_stage35_substitution_solver.py`

## 2026-04-03 p5 control pass and current one-job setup

`v53` rerun result:

- `p5/c1 seed411` solved cleanly at `stage3_full_refine`
- `best_match_ratio = 1.0`
- Stage 3.5 no-op reject:
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - `stage35_accept_reason = "top_candidate_matches_baseline"`

Interpretation:

- this is the expected easy-control pass, not a new mechanism result
- the bounded candidate lane does not appear to harm this p5/c1 control

Hardening landed from the `v53` artifact:

- `space_map_v1` now receives `run_id` from `run_dir.name`
- `pool_summaries` now expose `pool_status`
- empty no-Phase-C pools are explicitly marked `not_run`

Current one-job setup:

- `candidate_single_p5`
- `p5/c1`
- `seed511`
- experiment id:
  - `tune_v54_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_single_1job`

Prepared next one-job mode:

- `candidate_single_p7`
- `p7/c1`
- `seed411`
- experiment id:
  - `tune_v55_p7c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`

Decision rule:

- only flip to `candidate_single_p7` after `v54` passes and the new
  `space_map_v1` hardening fields are confirmed in the artifact

`v54` first result:

- solver quality passed:
  - `p5/c1 seed511`
  - `best_match_ratio = 1.0`
  - `stage35_accept_reason = "top_candidate_matches_baseline"`
- data-contract hardening was only partially correct:
  - `phaseC_start.pool_status = "not_run"` worked
  - `space_map_v1.run_id` was still blank

Root-cause fix:

- `run_pipeline_execution.py` setting `runner_state["run_id"]` was not enough
  because `iteration_matrix_flow.py` rebuilds per-iteration state dicts
- `run_id` is now explicitly passed into `run_iteration_matrix(...)` and stored
  in both Stage 3 and finalize-state builders

Rerun rule:

- rerun the same `p5/c1 seed511` lane under fresh experiment id `v56` before
  switching to `v55`
- this is a one-run data-contract verification, not a new long-run ladder

`v56` result:

- easy `p5/c1 seed511` control passed again:
  - `best_stage = "stage3_full_refine"`
  - `best_match_ratio = 1.0`
  - `stage35_accept_reason = "top_candidate_matches_baseline"`
- data-contract status:
  - row/pool `run_id` fields are populated
  - `phaseC_start.pool_status = "not_run"`
  - top-level `space_map_v1.run_id` has been patched for the next artifact

Current next run:

- `STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p7"`
- `p7/c1 seed411`
- `tune_v55_p7c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job`

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

### 2026-04-03 `v55` / `v57` readout and next speed slice

`v55` p7/c1 seed411:

- clean control pass:
  - `best_match_ratio = 1.0`
  - `best_stage = "stage35_substitution_only"`
  - `stage35_accept_reason = "accepted"`
- space-map contract pass:
  - `space_map_v1.run_id` is populated
  - `phaseC_start.pool_status = "available"`
- but runtime is still too high for an easy solved control:
  - matrix elapsed `12137.381100654602s`
  - Phase C ran `9216` evals even though the anchor start already had
    `init_match = 1.0`
  - Stage 3.5 then ran one accepted round with `575` evals and
    `483.7016396999825s`

`v57` p9/c3 seed411:

- hard-case result is a stable reproduction of `v51`:
  - baseline hash `9002ee09917e5a0d`
  - baseline source `phaseA_selected`
  - baseline lane `challenger`
  - baseline differs from the Phase C score winner
  - Stage 3.5 accepts
  - `best_match_ratio = 0.487`
- boundedness remains practical on the hard case:
  - matrix elapsed `11870.78020787239s`
  - Stage 3.5 runtime `3295.0344342000317s`
  - `rounds_completed = 1`
  - `evals = 4352`
- space-map contract pass:
  - `space_map_v1.run_id = "20260403T080049428735Z__bench_solve_pipeline_no_wli__048e35c"`
  - Phase C / Stage 3.5 pools are populated

Maintained reading:

- the bounded `score_plus_novelty + beam_width_1` lane is now confirmed on
  one p7 control and reproducibly wins on the p9/c3 seed411 hard case
- this is still not a broad solver promotion because the repeated hard-case
  confirmation is the same 411 family
- the next speed slice should not be another long run by default

Next implementation target:

- implement a truth-based hard stop for benchmark runs at the Phase C /
  Stage 3.5 handoff and inside Phase C:
  - if `continue_after_solve = 0`
  - truth is available
  - and the current best row is already solved
  - skip remaining Phase C / Stage 3.5 work
- this should turn solved p5/p7 controls from multi-hour validation runs into
  short no-harm checks without changing selection semantics on unsolved cases

Secondary tooling follow-up:

- add explicit repo-relative diagnostic path fields for Stage 3.5 progress and
  partial-state dumps if reviewer-facing tooling should open those files
  directly
- keep the existing file-name fields too

