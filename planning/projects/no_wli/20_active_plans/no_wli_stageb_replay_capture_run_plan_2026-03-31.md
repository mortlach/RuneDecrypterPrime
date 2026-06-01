# No-WLI Stage B replay-capture run plan

## Purpose

Queue one fresh post-hardening `411` late-stage run whose primary purpose is to
produce a replay-ready frontier, not to change the science question again.

This run exists to close the gap left by the historical `v45` artifact:

- the disagreement frontier is already scientifically useful
- but it predates the new Phase-C replay-capture fields

So the goal here is:

- same known disagreement shape
- fresh artifact
- full `final_key_idx` / `final_plaintext_idx` capture on explored starts

## Run definition

Use the same two-job compare that produced the strongest late-stage disagreement
signal:

- control:
  - `stage3_phaseb_width_probe_p9`
- candidate:
  - `stage3_phasec_novel_challenger_p9`

Keep fixed:

- `seed = 411`
- `p9 / c3`
- the widened-late compare semantics

Do not mutate:

- Phase-B ranking
- Phase-C candidate-pool construction
- rescue semantics
- scorer semantics

## Current control identity

Active experiment id:

- `tune_v46_p9c3_seed411_novel_start_replay_capture_2job`

Derived control files:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v46_p9c3_seed411_novel_start_replay_capture_2job.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v46_p9c3_seed411_novel_start_replay_capture_2job.jsonl`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_tune_v46_p9c3_seed411_novel_start_replay_capture_2job.json`

## Success condition

At least one finished run in this compare should export a late frontier with:

- `frontier_key_material_complete = 1`
- candidate rows carrying:
  - `init_key_idx`
  - `init_plaintext_idx`
  - `final_key_idx`
  - `final_plaintext_idx`

That run then becomes the first replay-ready late-stage frontier for Stage B.

## Immediate follow-up after the run

1. export the fresh frontier with:
   - `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_frontier_fixture.py`
2. confirm replay completeness
3. use that frontier for:
   - trial-key / replay experiments
   - legacy-vs-revised selector replay validation

## Readiness checklist reference

Use:

- `planning_old/working/no_wli_stageb_first_replay_ready_frontier_checklist_2026-03-31.md`

as the first-pass inspection checklist when `v46` finishes.

## Baseline-to-beat for Stage B

Freeze the conservative pre-`v46` Stage A baseline as:

- `score + novelty`

Do not automatically promote the source-penalty variant to baseline yet.

Reason:

- it improves the last unrecovered Stage A pattern
- but it does so by selecting `7391...`, not the oracle-best `e45...`
- so it should enter Stage B as an optional comparison candidate, not as the
  locked baseline-to-beat

## `v46` completion result

The replay-capture compare finished cleanly:

- `completed_jobs = 2`
- `remaining_jobs = 0`
- `stopped_early = 0`
- no `job_error`

Replay-ready status:

- both finished runs wrote run-level `phasec_start_checkpoints.jsonl`
- both checkpoint frontiers contain `6` rows
- all `6 / 6` rows in both runs carry complete:
  - `init_key_idx`
  - `init_plaintext_idx`
  - `final_key_idx`
  - `final_plaintext_idx`

Important nuance:

- the replay-complete frontier is available in both places:
  - `stage3_diagnostics.phaseC_start_summaries`
  - run-level `phasec_start_checkpoints.jsonl`
- the shared frontier loader now keeps Stage B robust to either storage shape

Resulting handoff:

- Stage B may now begin
- required replay capture is present
- the frozen pre-`v46` baseline remains:
  - `score + novelty`
- the safe source-penalty variant remains:
  - optional comparison candidate only

## Stage B first concrete output

Fresh frontier exports:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v46_seed411_control_replay_frontier.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v46_seed411_candidate_replay_frontier.json`

First Stage B comparison bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/summary.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/selected_trial_material_rows.json`

Current Stage B reading:

- both replay-ready frontiers confirm the same legacy-vs-challenger disagreement
- both `score + novelty` and the optional source-penalty variant choose
  `9002ee09917e5a0d`
- so the next discriminator is no longer ranking-only
- the next discriminator is a direct replay / continuation comparison using the
  saved selected-trial material rows

## Stage B first continuation result

Reference:

- `planning_old/working/no_wli_stageb_first_continuation_note_2026-03-31.md`

Generated continuation bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46_continuation/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46_continuation/summary.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46_continuation/continuation_results.json`

Current maintained reading:

- legacy selection does not survive the real Stage 3.5 acceptance rule:
  - selected `73eee2bf84b7c07f`
  - selected truth `0.039`
  - Stage 3.5 selected `0`
  - accept reason `search_score_drop_guard_failed`
  - best continued truth `0.038`
- locked Stage B baseline `score + novelty` does survive the real continuation:
  - selected `9002ee09917e5a0d`
  - selected truth `0.418`
  - Stage 3.5 selected `1`
  - accept reason `accepted`
  - best continued candidate `d9430723f54e973e`
  - best continued truth `0.496`
  - truth gain vs selected challenger `+0.078`
- the optional source-penalty variant selects the same challenger on this case
  and therefore adds no extra continuation lift

Practical consequence:

- Stage B has now crossed from replay-ready export into real continuation
  validation
- the late-stage selector/reranker path now has one replay-validated positive
  case

