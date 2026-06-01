# no-WLI Stage35 Resume From Handoff Focus-Family Rescue Plan

Date: 2026-04-29

Status:

- active planning; static inventory, selected-row runner design, and smoke
  preflight complete; first real `7005` selected-row run complete
- first real runtime launched and completed:
  - `1111/search7005`
- late-stage-only handoff/archive branch
- full-pipeline rerun is explicitly out of scope

## Guardrails

- Do not launch an hour-plus run without asking first.
- Do not launch an overnight or multi-hour run without:
  - written wallclock budget
  - stop condition
  - retained timing reference or completed same-family canary
  - repo-relative output/log paths checked before launch
- Do not run another six-job full-pipeline Stage-3 entry panel as-is.
- Do not use CLI arguments for repo automation/helper scripts.
- Keep runner configuration as hardcoded constants in the source file.

## Why this exists

The Phase-C multi-thread long harvest completed cleanly:

- `19` candidate3 saved-surface cases
- `27` policies
- `3` passes
- `1539 / 1539` policy units
- `19:21:02` elapsed
- `513 / 513` repeated case-policy rows stable for score, delta, winner, and
  surface class

It closed the broad saved-surface reshuffling direction:

- frontload-depth did not beat reorder-only controls
- quota did not beat reorder-only controls
- replacement did not beat reorder-only controls

The Stage-3 entry constant-local-depth reorder-signal panel then launched
correctly but capped after one completed full-pipeline control job:

- completed lane:
  - `1111/search7002`
- completed preset:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- completed config:
  - `stage3.entry.allocation_policy = legacy_fixed_budget`
  - `stage3.period_scaling.init_keys_cap = 192`
- elapsed:
  - about `13:32:47`
- best match:
  - `0.754`
- best stage:
  - `stage35_substitution_only`

So the constant-local-depth candidate comparison remains unanswered, and the
full-pipeline panel is too expensive as configured.

## Main question

Starting from retained handoff/archive artefacts, can a late-stage-only selector
or rescue variant improve beyond the retained route without recomputing the full
pipeline?

## Suspicion

The useful mechanism is now downstream of saved-surface ordering:

- choose or rescue better within retained Stage 3.5 / late-family material
- spend compute only after a retained handoff/archive point
- avoid recomputing Stage 1, Stage 2, Stage 3 Phase A, Phase B, and Phase C

## Main alternative

The retained archive already captures the available local rescue value, or the
existing handoff artefacts are not sufficient to run a clean late-stage-only
comparison without rebuilding too much upstream work.

## Mechanism layer

- local search / rescue
- late-stage selector / archive replay
- not upstream supply
- not Stage2 checkpointing
- not broad saved-surface reshuffling
- not a full-pipeline Stage-3 entry allocation panel

## Target order

### Primary target: `1111/search7005`

Reason:

- retained best match:
  - `0.372`
- focus-family max final match from review summary:
  - `0.416`
- stage35 family counts:
  - `f0:5`
  - `f1:1`
- final best flips away from the dominant / focus family
- Phase-C atlas had a drifted/context clue:
  - `frontload_all 0.391`
  - versus source `0.366`

Handoff root:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260412T053512632846Z__bench_solve_pipeline_no_wli__9557c0f/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7005/`

### Secondary target: `1111/search7004`

Reason:

- retained best match:
  - `0.423`
- focus-family max final match from review summary:
  - `0.432`
- stage35 family counts:
  - `f0:1`
  - `f1:1`
  - `f2:3`
- fragmentation target
- Phase-C atlas usable clue:
  - `frontload_all 0.440`
  - versus source `0.432`

Handoff root:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260412T031328680128Z__bench_solve_pipeline_no_wli__9557c0f/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7004/`

### Control target: `1111/search7002`

Reason:

- fresh v79 full-pipeline control reached:
  - `0.754`
- stage35 family counts:
  - `f0:6`
- clean aligned control case
- useful proof-of-runner case, but lower expected upside

Handoff root:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260428T035424021944Z__bench_solve_pipeline_no_wli__ee62083/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7002/`

## Required input files

Each target handoff root must contain:

- `manifest.json`
- `stage2_resume.json`
- `stage3_prep.json`
- `stage35_seed_archive.json`

Repo-local check already found all four files for `7002`, `7004`, and `7005`.

Static inventory bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T043455Z__stage35_resume_from_handoff_focus_family_rescue_v1/`

Inventory result:

- target rows:
  - `3`
- late-stage feasible rows:
  - `3`
- runtime launched:
  - `0`
- recommendation:
  - `advance_to_static_archive_design`
- static design read:
  - `1111/search7005`
    - retained:
      - `0.372`
    - best checkpoint:
      - `0.398`
    - delta:
      - `+0.026`
    - recommended variant:
      - `focus_or_dominant_challenger_rescue_first`
  - `1111/search7004`
    - retained:
      - `0.423`
    - best checkpoint:
      - `0.413`
    - delta:
      - `-0.010`
    - recommended variant:
      - `fragmentation_static_audit_before_runtime`
  - `1111/search7002`
    - retained:
      - `0.754`
    - best checkpoint:
      - `0.752`
    - delta:
      - `-0.002`
    - recommended variant:
      - `control_archive_replay_only`

Selected-row runner design read:

- late-stage entry point:
  - `artifact_resume.run_stage35_from_selected_trial_row`
- upstream recompute required:
  - `0`
- partial outputs supported:
  - `1`
- runtime launched:
  - `0`
- selected material completeness:
  - `17 / 17` archive seed rows have runnable key/plaintext material
- selected-row deltas versus retained:
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
    - delta:
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
    - delta:
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
    - delta:
      - `-0.002`
    - recommended next unit:
      - `control_replay_or_hold`

Interpretation update:

- the checkpoint-only archive read understated the available runnable frontier
  material for `1111/search7005` and `1111/search7004`
- `1111/search7005` remains the first target because its selected-row headroom
  is larger
- `1111/search7004` is no longer just a fragmentation static-audit target; it
  also has a small selected-row headroom row
- `1111/search7002` remains useful as control/proof-of-runner, not as an
  expected improvement target

Smoke preflight bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T044610Z__stage35_resume_from_handoff_focus_family_rescue_v1__smoke_preflight/`

Smoke preflight configuration:

- target:
  - `1111/search7005`
- selected row:
  - `c9e69b90b779e318`
- selected source:
  - `stage3_best_phaseB`
- selected lane:
  - `anchor`
- Stage 3.5 override:
  - `rounds = 0`
  - `seed_keep = 2`
  - `beam_width = 2`
  - `archive_keep = 4`
  - `max_runtime_seconds = 30`

Smoke result:

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

Smoke interpretation:

- selected-row loading works
- Stage 3.5 scorer construction works
- partial/progress artefact writeback works
- this is not a science result because local-rescue rounds were disabled
- the real micro-canary is still pending an explicit launch decision

First real selected-row run bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T060445Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_v1__real_selected_best_frontier_one_round/`

First real selected-row run configuration:

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

First real selected-row run result:

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

First real selected-row run interpretation:

- the late-stage selected-row path completed cleanly and extractably
- it preserved the selected-row improvement over retained best
- the accepted resume result did not improve beyond the selected row because
  the score-ranked rank-1 local proposal was rejected by the existing
  search-score-drop guard
- posthoc archive analysis changes the read from "local-rescue flat" to
  "acceptance-selector missed a guard-passing alternate":
  - rank 1 `f095bf4c31b02daf`:
    - truth match `0.416`
    - score delta versus baseline `+0.003019`
    - search-score delta versus baseline `-0.093198`
    - rejected by search-score guard
  - rank 2 `7068135ec036da03`:
    - truth match `0.422`
    - truth delta versus selected start `+0.006`
    - score delta versus baseline `+0.002984`
    - search-score delta versus baseline `+0.016851`
    - satisfies the current nonnegative score and search-score guards
- the current run used `accept_guard_passing_selector_mode = off`, so it did
  not fall through to rank 2
- this result weakens the case for deepening the same broad `7005` rescue
  shape, but strengthens the case for a narrow guard-passing-selector
  follow-up on the same target before spending on `7004`

## Timing references

Current timing references:

- broad runtime history:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T011225Z__no_wli_runtime_history_reference_v1/`
- fixed runtime wallclock reference:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T011225Z__fixed_runtime_wallclock_reference_v1/`

Relevant current fixed-runtime read:

- retained `1111/search7002` full-pipeline rows:
  - min:
    - `2.32h`
  - mean:
    - `11.56h`
  - max:
    - `18.81h`
- v79 control/full-pipeline job:
  - about `13.54h`
- retained `search7002` remains the heaviest search-seed family:
  - mean about `9.83h`
  - max about `18.96h`

This is why the next unit must be late-stage-only rather than full-pipeline.

Specific retained Stage 3.5 timing anchor:

- retained `1111/search7005` Stage 3.5 follow-up:
  - `1996.242s`
  - about `33m16s`
  - `1` completed round
  - `9` mini-searches
  - `3740` evals
  - progress events written:
    - `16`
  - partial dumps written:
    - `4`

Pre-launch projected real micro-canary budget:

- first real cell:
  - `1111/search7005`
- selected row:
  - `c9e69b90b779e318`
- proposed cap:
  - `3600s`
- proposed stop condition:
  - stop after one bounded Stage 3.5 round or `3600s`, whichever comes first
- expectation:
  - likely under one hour based on the retained same-lane Stage 3.5 anchor
- guard:
  - because the margin is close to the user threshold, require an explicit
    launch decision before starting the real micro-canary

Observed first real selected-row runtime:

- `2.991s`
- interpretation:
  - selected-row rescue on this chosen `7005` row is much cheaper than the
    retained baseline Stage 3.5 anchor because it completed the bounded round
    with only `1470` evals
  - this is now the same-family timing anchor for this exact selected-row
    runner shape

Observed guard-selector follow-up runtime:

- `6.361s`
- interpretation:
  - same selected-row one-round shape remains safely short on `7005`
  - the extra wallclock relative to `2.991s` is still far below the retained
    same-lane Stage 3.5 anchor and below the user's hour-plus approval guard

Observed `7004` guard-selector confirmation runtime:

- `10.620s`
- interpretation:
  - the secondary selected-row one-round shape also stayed safely short
  - this was not a full-pipeline `7004` rerun and should not be budgeted from
    the historical `2.36h` full-pipeline anchor

## First work unit

Build a static handoff/archive inventory and feasibility readout.

The inventory should answer:

- can each target load `stage35_seed_archive.json` cleanly?
- how many archive rows / seed rows are available?
- what candidate hashes and family-related fields are available?
- what retained baseline match should each target compare against?
- what late-stage-only entry point can be called without recomputing upstream
  stages?
- what output files would be written if a late-stage-only runner caps?

Expected runtime:

- minutes, not hours
- safe to run in the interactive terminal

Status:

- complete
- latest bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T043455Z__stage35_resume_from_handoff_focus_family_rescue_v1/`
- runtime launched:
  - `0`

## Second work unit

Build and run a smoke-only selected-row Stage 3.5 preflight.

Status:

- complete
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_v1.py`
- latest bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T044610Z__stage35_resume_from_handoff_focus_family_rescue_v1__smoke_preflight/`
- real science runtime launched:
  - `0`
- recommended next:
  - make an explicit launch decision for the real `1111/search7005`
    selected-best-frontier micro-canary with a `3600s` cap

## Third work unit

Run the first real `1111/search7005` selected-best-frontier micro-canary.

Status:

- complete
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_real_7005_v1.py`
- launch wrapper:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_resume_from_handoff_focus_family_rescue_real_7005_launch_2026-04-29.ps1`
- terminal opener:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_resume_from_handoff_focus_family_rescue_real_7005_open_terminal_2026-04-29.ps1`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_resume_from_handoff_focus_family_rescue_real_7005_2026-04-29.log`
- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T060445Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_v1__real_selected_best_frontier_one_round/`

Recommendation after completion:

- do not deepen the same broad `7005` selected-row rescue shape immediately
- first run a narrow same-target selector follow-up with:
  - `accept_guard_passing_selector_mode = top_score_then_search`
  - same selected row `c9e69b90b779e318`
  - same one-round bounded Stage 3.5 shape
- success condition:
  - the accepted result chooses the guard-passing alternate and exposes the
    posthoc `0.422` truth-positive archive row, or explains why live selector
    behavior differs from the archive read
- only after this selector check decide whether `1111/search7004` deserves a
  secondary confirmation

## Fourth work unit

Run the same `1111/search7005` selected-best-frontier micro-canary with
guard-passing selector fallback enabled.

Status:

- complete
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1.py`
- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T145906Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/`

Configuration delta from third work unit:

- `accept_guard_passing_selector_mode = top_score_then_search`

Result:

- status:
  - `completed`
- retained best:
  - `0.372`
- selected row start:
  - `0.416`
- accepted resume best:
  - `0.422`
- delta versus retained:
  - `+0.050`
- delta versus selected row:
  - `+0.006`
- accept reason:
  - `accepted_via_guard_passing_selector`
- selected archive rank:
  - `2`
- selected candidate:
  - `7068135ec036da03`
- rounds completed:
  - `1`
- evals:
  - `1470`
- elapsed:
  - `6.361s`
- progress events:
  - `16`
- partial dumps:
  - `4`

Interpretation:

- the posthoc archive read was actionable
- `7005` is now a real accepted local-rescue improvement, not just a
  route-choice improvement:
  - `+0.006` beyond selected-row start
  - `+0.050` beyond retained route
- do not deepen `7005` immediately
- next useful question is whether the same guard-selector mechanism repeats
  on the smaller-headroom `1111/search7004` lane before closing or widening
  the branch

## Fifth work unit

Run the same guard-selector shape on the secondary `1111/search7004`
selected-row target.

Status:

- complete
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1.py`
- completed bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T150415Z__stage35_resume_from_handoff_focus_family_rescue_real_7004_guard_selector_v1__real_selected_best_frontier_one_round_guard_selector/`

Configuration:

- target:
  - `1111/search7004`
- selected row:
  - `6858f26bdc4c4d1f`
- selected source:
  - `stage3_best_phaseA`
- guard selector:
  - `accept_guard_passing_selector_mode = top_score_then_search`
- Stage 3.5 shape:
  - same one-round selected-row shape as the `7005` guard-selector follow-up

Result:

- status:
  - `completed`
- retained best:
  - `0.423`
- selected row start:
  - `0.432`
- reported local top resume:
  - `0.425`
- delta versus retained:
  - `+0.002`
- delta versus selected row:
  - `-0.007`
- accept reason:
  - `search_score_drop_guard_failed`
- selected:
  - `0`
- selected archive rank:
  - `1`
- evals:
  - `2643`
- elapsed:
  - `10.620s`

Posthoc archive read:

- no non-no-op archive row passed both nonnegative score and search-score
  guards
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
- baseline/no-op rank 12 `0e53773898ecab02`:
  - truth match `0.432`
  - score and search-score deltas `0`

Interpretation:

- strict guard-selector fallback does not repeat as an accepted improvement on
  `7004`
- `7004` should be carried as selected-row route-choice positive (`0.432`
  versus retained `0.423`) but strict local-rescue negative
- the truth-positive rank-6 row means any next `7004` work should be an
  offline guard-relaxation/policy audit, not more blind runtime
- branch status is mixed:
  - `7005`: strict guard-selector accepted positive
  - `7004`: strict guard-selector rejected all non-no-op local rows

Recommended closeout:

- stop running this exact strict guard-selector shape for now
- summarize it as a useful but non-uniform mechanism:
  - accepted on strongest `7005`
  - blocked by search-score guard on smaller-headroom `7004`
- next useful branch, if pursued, should be an offline guard-relaxation audit
  over saved archives before any more runtime

## Sixth work unit

Run a small offline guard-selector archive policy audit over the two completed
selected-row guard-selector archives.

Status:

- complete
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_guard_selector_archive_policy_audit_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T151026Z__stage35_guard_selector_archive_policy_audit_v1/`

Scope:

- `accepted_positive_7005`
- `blocked_secondary_7004`
- archive rows:
  - `24`

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
    - rank `2`, `7068135ec036da03`, `0.422`
- `7004`:
  - accepted:
    - `0`
  - accepted delta versus selected:
    - `-0.007` reported local top; carried route remains selected start
      `0.432` because Stage 3.5 selected `0`
  - guard-passing non-noop rows:
    - `0`
  - truth-positive rows:
    - `1`
  - blocked truth-positive rows:
    - `1`
  - best truth row:
    - rank `6`, `3b5b0ca607c51fbe`, `0.438`

Interpretation:

- strict guard-selector fallback is useful but not sufficient as a uniform
  policy
- the search-score guard separates the useful `7005` rank-2 row from the
  `7004` rank-6 row only by rejecting the latter, even though rank 6 is
  truth-positive
- do not run more strict guard-selector runtime until a broader offline policy
  audit can decide whether any non-truth features separate useful
  search-score-failing rows from regressions

## Seventh work unit

Launch a broader archive-policy data-taking run for the guard-relaxation
question.

Status:

- completed
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_relaxation_archive_policy_long_audit_v1.py`
- launch wrapper:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_relaxation_archive_policy_long_audit_launch_2026-04-29.ps1`
- terminal opener:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_relaxation_archive_policy_long_audit_open_terminal_2026-04-29.ps1`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_relaxation_archive_policy_long_audit_2026-04-29.log`

Question:

- across retained Stage 3.5 archive surfaces, does relaxing the search-score
  guard recover truth-positive rows, and how often does it admit truth-negative
  rows?

Written runtime budget:

- intended wallclock budget:
  - `8h`
- hardcoded script budget:
  - `28800s`
- stop condition:
  - stop when all discovered `stage35_summary.json` / `best_instance.json`
    Stage 3.5 archive sources are processed, or when `28800s` is reached
- progress requirement:
  - emit completed-versus-total source counts, elapsed time, and ETA to
    stdout/log every `5` sources
- partial writeback:
  - write partial CSV/JSON/readout outputs every `5` sources

Timing basis:

- full retained fixed cells are much heavier:
  - `1111/search7004` retained full cell about `2.36h`
  - `1111/search7005` retained full cell about `2.48h`
  - worst retained `search7002` examples exceed `18h`
- this run is not a full solver matrix; it is archive data-taking over saved
  Stage 3.5 surfaces
- the previous same-family archive audit processed `2` cases / `24` rows in
  under a second, so the risk is filesystem/JSON volume, not solver runtime

Expected output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/*__stage35_guard_relaxation_archive_policy_long_audit_v1/`

Outcome:

- completed quickly rather than consuming the full budget
- completed sources:
  - `264 / 264`
- usable case summaries:
  - `80`
- archive rows:
  - `931`
- elapsed:
  - `8.084s`
- key policy result:
  - strict search-score guard remains the best default in this audit
  - relaxing the search-score floor did not increase truth-positive selections
    and increased truth-negative selections

## Eighth work unit

Launch a broader selected-frontier runtime harvest to use the remaining
session for actual bounded Stage 3.5 data-taking.

Status:

- completed
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_selector_frontier_runtime_harvest_v1.py`
- launch wrapper:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_selector_frontier_runtime_harvest_launch_2026-04-29.ps1`
- terminal opener:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_selector_frontier_runtime_harvest_open_terminal_2026-04-29.ps1`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_selector_frontier_runtime_harvest_2026-04-29.log`

Question:

- across retained fixed-panel artefacts and multiple saved frontier rows per
  artefact, where does one bounded strict guard-selector Stage 3.5 rescue
  actually accept useful local improvements?

Written runtime budget:

- intended wallclock budget:
  - `8h`
- hardcoded script budget:
  - `28800s`
- per-cell cap:
  - `900s`
- selected rows per retained artifact:
  - up to `12`
- stop conditions:
  - queue exhausted
  - wallclock budget reached
  - after first cell, stop if projected serial runtime exceeds the `28800s`
    budget
- progress:
  - emit completed-versus-total cells, elapsed time, per-cell time, and ETA
    after every cell
- partial writeback:
  - write result/error CSV and summary/readout after every cell

Timing basis:

- recent selected-row one-round cells:
  - `7005` guard-selector: `6.361s`
  - `7004` guard-selector: `10.620s`
- retained full fixed cells remain multi-hour, but this harvest is late-stage
  only and independently extractable after every cell

## Candidate implementation shape

Likely runner / extractor names:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_resume_from_handoff_focus_family_rescue_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_resume_from_handoff_focus_family_rescue_v1.py`

Use hardcoded constants for:

- target handoff roots
- output bundle name
- enabled variants
- per-variant caps
- target order

Do not add CLI arguments.

## Initial variants to consider

The static inventory should decide the final variant list. Plausible candidates:

- retained archive control replay
- focus-family preferred selector
- dominant-family preferred selector
- wider local rescue from the focus-family archive rows

Keep the first executable comparison narrow. Do not build a broad variant atlas.

## Tomorrow's decision rule

Advance to a late-stage-only runtime only if:

- handoff/archive loading is clean for at least one priority target
- the late-stage entry point avoids full upstream recompute
- expected runtime is under one hour or explicit approval is obtained
- output is extractable if capped
- comparison against retained anchors is unambiguous

Hold if:

- the archive is loadable but the late-stage entry point is unclear
- the first implementation would require invasive solver refactoring
- expected runtime cannot be estimated from retained evidence

Close or rescope if:

- the required handoff/archive files are insufficient for late-stage-only work
- the only viable route recomputes the full pipeline
- the first proposed run would silently run for hours without incremental
  progress and partial artefacts

## Current non-claims

- This branch does not promote constant-local-depth.
- This branch does not reopen live runtime generally.
- This branch does not claim a production policy.
- This branch does not invalidate the Stage2 checkpoint review-ready result.
- This branch does not reopen broad Phase-C saved-surface reshuffling.

## Ninth work unit

Launch a focused Stage 3.5 deepening harvest on the strongest shallow-positive
selected-frontier cells.

Status:

- completed
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_selector_frontier_deepening_harvest_v1.py`
- launch wrapper:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_selector_frontier_deepening_harvest_launch_2026-04-29.ps1`
- terminal opener:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_guard_selector_frontier_deepening_harvest_open_terminal_2026-04-29.ps1`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_selector_frontier_deepening_harvest_2026-04-29.log`

Preceding shallow harvest outcome:

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/`
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
  - `19 / 22` positives
  - `0 / 22` negatives
  - mean delta versus start `+0.164`
  - best delta versus start `+0.458`

Question:

- among the best shallow accepted rescue cells, does a deeper bounded Stage 3.5
  continuation improve beyond the one-round result?

Written runtime budget:

- intended wallclock budget:
  - `8h`
- hardcoded script budget:
  - `28800s`
- per-cell cap:
  - `1800s`
- max cells:
  - `36`
- queue filter:
  - shallow selected cells with `resume_minus_selected >= 0.05`, sorted by
    shallow delta descending
- stop conditions:
  - queue exhausted
  - wallclock budget reached
  - after first cell, stop if projected serial runtime exceeds the `28800s`
    budget
- progress:
  - emit completed-versus-total cells, elapsed time, per-cell time, and ETA
    after every cell
- partial writeback:
  - write result/error CSV and summary/readout after every cell

Timing basis:

- immediately preceding same-entry shallow harvest completed `136` cells in
  `721.112s`
- the deepening run is a materially new timing class:
  - `rounds=3`
  - `seed_keep=4`
  - `beam_width=2`
  - `archive_keep=24`
  - `mini_search_steps=2`
- therefore the first completed cell must become the real timing anchor; if
  its projection exceeds the budget, the script stops and preserves the single
  completed cell

Recommended next:

- if deepening improves multiple cells without new regression patterns, design
  a narrower rank/slice-aware local-rescue policy
- do not promote unfiltered guard-selector from the shallow harvest because it
  admitted accepted regressions outside the best slice

Outcome:

- completed
- output bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/`
- closeout:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/stage35_guard_selector_frontier_deepening_closeout.md`
- completed cells:
  - `15 / 15`
- errors:
  - `0`
- elapsed:
  - `1919.390s`
- first-cell timing:
  - elapsed `164.446s`
  - projected serial runtime `2466.693s`, safely under the `28800s` budget
- selected cells:
  - `15 / 15`
- better than shallow:
  - `12 / 15`
- worse than shallow:
  - `3 / 15`
- mean delta versus shallow:
  - `+0.007533`
- best delta versus shallow:
  - `+0.019`
- worst delta versus shallow:
  - `-0.007`
- mean delta versus selected-row start:
  - `+0.254600`
- mean delta versus retained anchor:
  - `+0.004533`
- rank-6 read:
  - `13` rows
  - `11` better than shallow
  - `2` worse than shallow
  - mean delta versus shallow `+0.008154`

Carried interpretation:

- deepening is a real but modest positive follow-up on the shallow local-rescue
  signal
- the result supports a rank/slice-aware local-rescue branch, especially around
  rank-6-heavy cells
- it does not justify promoting broad unfiltered guard-selector selection:
  the shallow harvest admitted accepted regressions, and deepening still had
  `3` cells worse than shallow

Updated recommended next:

- do not rerun the same broad deepening shape immediately
- build a narrower offline extractor that joins shallow and deepening rows,
  removes duplicate retained artefact rows, and characterizes which rank-6
  cells are safe
- only after that, consider a small policy canary for rank/slice-aware
  local-rescue selection

Runtime-reference refresh:

- refreshed runtime-history output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T001224Z__no_wli_runtime_history_reference_v1/`
- refreshed fixed wallclock-reference output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T001224Z__fixed_runtime_wallclock_reference_v1/`

## Tenth work unit

Run the offline shallow-plus-deepening join/dedup extractor.

Status:

- completed
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_guard_selector_frontier_deepening_join_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/`

Question:

- after deduplicating the shallow and deepening rows, which slices look safe
  enough to justify a narrower local-rescue policy design?

Coverage:

- shallow rows:
  - `136`
- deep rows:
  - `15`
- deduplicated joined rows:
  - `14`
- duplicate keys:
  - `1`
  - duplicate key: `1111/search7002 rank 6 74dfe3cb559629f7`

Result:

- better than shallow:
  - `11 / 14`
- worse than shallow:
  - `3 / 14`
- mean deep minus shallow:
  - `+0.007000`
- best deep minus shallow:
  - `+0.019000`
- worst deep minus shallow:
  - `-0.007000`
- mean deep minus retained:
  - `+0.004714`

Rank read:

- rank `6`:
  - `12` rows
  - `10` better than shallow
  - `2` worse than shallow
  - mean deep minus shallow `+0.007583`
- rank `1`:
  - `1` row
  - `1` better than shallow
- rank `5`:
  - `1` row
  - `1` worse than shallow

Posthoc candidate gate sketch:

- `rank6_selected_start_ge_0p437`:
  - rows `6`
  - better `6`
  - worse `0`
  - mean deep minus shallow `+0.009333`
- this is a hypothesis only:
  - it was found after seeing the deepening data
  - it is not a promoted rule
  - it needs an explicit no-regression gate before any runtime canary

Updated recommendation:

- do not launch more runtime from the broad rank-6/deepening shape
- next step should be an offline safety-rule design note or extractor focused
  on whether `selected_start_match_ratio` can serve as a robust rank-6 gate
- if that offline rule remains coherent, the next runtime should be a small
  independently complete policy canary, not another broad batch

## Eleventh work unit

Run the rank-6 selected-start gate safety extractor.

Status:

- completed
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_rank6_selected_start_gate_safety_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T014439Z__stage35_rank6_selected_start_gate_safety_v1/`

Question:

- can the posthoc `rank6_selected_start_ge_0p437` hypothesis be converted into
  a safe predeclared local-rescue gate?

Prediction ledger for later comparison:

- these predictions are for calibration/comparison, not blame assignment
- `real_late_local_rescue_phenomenon`:
  - `75-85%`
- `narrow_rank_or_slice_policy_can_improve_selected_cases`:
  - `50-65%`
- `general_production_policy_from_current_signal`:
  - `25-40%`
- `exact_selected_start_threshold_0p437_survives_as_is`:
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
- rejected deep rows:
  - `6`
- rejected better/worse versus shallow:
  - `4 / 2`
- observed rank-6 deepening regressions:
  - `2`
- kept regressions:
  - `0`
- all observed rank-6 deepening regressions removed:
  - `yes`
- rejected deepening positives:
  - `4`
  - includes `1111/search7002 rank 6 74dfe3cb559629f7`, deep-shallow
    `+0.015`, deep-selected `+0.465`

Shallow cross-check:

- deduplicated selected shallow rank-6 rows:
  - `20`
- shallow gate-kept rows:
  - `8`
- shallow kept positives/negatives:
  - `8 / 0`
- shallow rejected positives/negatives:
  - `9 / 1`

Interpretation:

- the selected-start gate is directionally useful as a safety separator
- it removes observed rank-6 deepening regressions
- it is too conservative to promote or canary as-is because it rejects several
  real positives
- the exact `0.437` threshold remains posthoc and should be expected to move or
  be replaced by a broader feature

Updated recommendation:

- do not launch runtime from this gate as-is
- next step should be a predeclared policy sketch that softens the
  selected-start gate or combines it with a second non-seed feature
- only after that sketch has an explicit no-regression decision rule should a
  tiny independently complete runtime canary be considered

## Twelfth work unit

Write the offline rank-6 local-rescue policy sketch.

Status:

- completed
- note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_local_rescue_policy_sketch_2026-04-30.md`

Softened candidate rule:

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

- the softened rule keeps the observed safety behavior while recovering the
  largest rejected positive, `1111/search7002 rank 6`
- it is still posthoc and should not be launched directly

Next required step:

- write a no-runtime canary design note with exact cells, budget, stop
  conditions, and success/failure rules
- only after that should runtime be considered

## Thirteenth work unit

Write the no-runtime rank-6 local-rescue canary design.

Status:

- completed
- note:
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
- partial writeback:
  - after every cell

Current decision:

- runtime is not launched
- next implementation step, if approved, is a hardcoded four-cell canary runner
  that writes a policy-decision row for every cell

## Fourteenth work unit

Launch the approved four-cell rank-6 local-rescue canary.

Status:

- completed
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_local_rescue_canary_v1.py`
- launch wrapper:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_rank6_local_rescue_canary_launch_2026-04-30.ps1`
- terminal opener:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_rank6_local_rescue_canary_open_terminal_2026-04-30.ps1`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_canary_2026-04-30.log`

Question:

- does the softened rank-6 local-rescue policy execute the two expected keep
  cells safely while rejecting the known regression and recording
  rejected-positive opportunity cost?

Policy:

- rank `6`
- and either:
  - `selected_start_match_ratio >= 0.437`
  - or `shallow_resume_minus_selected >= 0.400`

Cells:

- hard-gate keep:
  - `1511/search7004 rank 6 51b7dab086e94186`
- shallow-delta keep:
  - `1111/search7002 rank 6 74dfe3cb559629f7`
- observed-regression reject:
  - `1111/search7004 rank 6 511a29668b8c44d1`
- rejected-positive audit/control:
  - `1411/search7005 rank 6 b47e22bc63e7c189`

Written runtime budget:

- intended wallclock:
  - `45m`
- hardcoded cap:
  - `2700s`
- per-cell rescue cap:
  - `600s`
- stop conditions:
  - all four cells processed
  - wallclock cap reached
  - first executed rescue cell projection exceeds `2700s`
- progress:
  - completed-versus-total, elapsed, per-cell elapsed, and ETA after every cell
- partial writeback:
  - after every cell

Success criteria:

- policy decision labels match expected keep/reject labels
- executed keep cells are nonnegative versus shallow
- reject cells are explicit policy skips, not missing rows
- output distinguishes policy skips from runtime failures

Outcome:

- completed
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T015732Z__stage35_rank6_local_rescue_canary_v1/`
- closeout:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T015732Z__stage35_rank6_local_rescue_canary_v1/stage35_rank6_local_rescue_canary_closeout.md`
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
  - `168.396s` versus `2700s` budget
- policy decision mismatches:
  - `0`
- executed cells nonnegative versus shallow:
  - `2 / 2`
- executed cells regressed versus shallow:
  - `0 / 2`

Executed keep cells:

- `1511/search7004 rank 6 51b7dab086e94186`:
  - canary resume `0.578`
  - canary minus shallow `+0.010`
  - canary minus prior deep `0.000`
- `1111/search7002 rank 6 74dfe3cb559629f7`:
  - canary resume `0.756`
  - canary minus shallow `+0.015`
  - canary minus prior deep `0.000`

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

- implementation and no-regression pass for the softened rank-6 policy
- not a production promotion
- opportunity cost remains real because the policy still intentionally rejects
  a known positive row

Updated recommendation:

- do not broaden directly to a large runtime batch
- next run, if any, should be a small same-rule recall/audit microbatch that
  tests the rejected-positive boundary without changing the rule mid-run

## Fifteenth work unit

Launch the same-rule rank-6 local-rescue recall/audit microbatch.

Status:

- launching
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_local_rescue_recall_audit_v1.py`
- launch wrapper:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_rank6_local_rescue_recall_audit_launch_2026-04-30.ps1`
- terminal opener:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage35_rank6_local_rescue_recall_audit_open_terminal_2026-04-30.ps1`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_recall_audit_2026-04-30.log`

Question:

- among rows rejected by the softened rank-6 policy, how much reproducible
  local-rescue opportunity cost remains, and how many rejected rows are
  necessary safety rejects?

Policy remains fixed:

- rank `6`
- and either:
  - `selected_start_match_ratio >= 0.437`
  - or `shallow_resume_minus_selected >= 0.400`

Audit cells:

- rejected positive high:
  - `1411/search7005 rank 6 b47e22bc63e7c189`
- rejected positive mid:
  - `611/search7003 rank 6 826e5c871f444486`
- rejected positive low:
  - `1411/search7004 rank 6 2632e79517bf1c7c`
- rejected regression mild:
  - `1411/search7001 rank 6 c7d123cf849533ee`
- rejected regression strong:
  - `1111/search7004 rank 6 511a29668b8c44d1`

Written runtime budget:

- intended wallclock:
  - `45m`
- hardcoded cap:
  - `2700s`
- per-cell rescue cap:
  - `600s`
- prior same-shape timing:
  - selected audit cells previously ran between about `89s` and `159s`
  - expected serial time is about `526s` plus load/write overhead
- stop conditions:
  - all five cells processed
  - wallclock cap reached
  - first cell projection exceeds `2700s`
- progress:
  - completed-versus-total, elapsed, per-cell elapsed, and ETA after every cell
- partial writeback:
  - after every cell

Success criteria:

- policy decision remains `reject` for every cell
- audit rows are marked as policy-reject audit, not policy success
- positive and regression boundary rows are both reproducibly measured
- output remains extractable if stopped early

Outcome:

- completed
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T021919Z__stage35_rank6_local_rescue_recall_audit_v1/`
- closeout:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T021919Z__stage35_rank6_local_rescue_recall_audit_v1/stage35_rank6_local_rescue_recall_audit_closeout.md`
- completed cells:
  - `5 / 5`
- errors:
  - `0`
- elapsed:
  - `354.964s`
- first-cell projection:
  - `316.850s` versus `2700s` budget
- policy decision mismatches:
  - `0`
- audit positives versus shallow:
  - `3`
- audit regressions versus shallow:
  - `2`
- rows reproducing prior deepening exactly:
  - `5 / 5`

Interpretation:

- the softened policy is safe on the observed boundary but too conservative for
  recall
- the rejected-positive boundary is reproducible, not noise
- the rejected regressions are also reproducible, so simply widening the rule
  would reintroduce harm

Prediction comparison:

- real late local-rescue phenomenon:
  - supported
- narrow rank/slice policy improves selected cases:
  - partially supported; safe in the canary, but too conservative
- general production policy from current signal:
  - not supported
- exact `0.437` threshold survives as-is:
  - not supported; too conservative

Updated recommendation:

- do not launch more runtime yet
- next useful work is an offline boundary-feature extractor comparing the
  three rejected positives against the two rejected regressions to find a
  second separator beyond selected-start and shallow-delta

## Sixteenth work unit

Run the offline rank-6 boundary-feature audit and write the rule-revision note.

Status:

- completed
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_rank6_boundary_feature_audit_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T032952Z__stage35_rank6_boundary_feature_audit_v1/`
- revision note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_boundary_rule_revision_note_2026-04-30.md`

Question:

- what boundary features separate the three rejected positives from the two
  rejected regressions without simply widening the policy?

Result:

- boundary rows:
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

Best zero-false-positive sketches:

- `audit_minus_retained >= 0.0045`:
  - true positives `2`, false positives `0`, false negatives `1`
- `retained_best_match_ratio <= 0.4225`:
  - true positives `2`, false positives `0`, false negatives `1`
- `selected_start_match_ratio <= 0.294`:
  - true positives `2`, false positives `0`, false negatives `1`
- `shallow_resume_best_match_ratio <= 0.4225`:
  - true positives `2`, false positives `0`, false negatives `1`

Interpretation:

- no clean simple numeric separator exists in the current feature set
- the softened rank-6 policy remains safe but too conservative
- simply widening the rule would reintroduce known regressions

Updated recommendation:

- do not launch more runtime on this branch now
- do not promote the softened rule
- next useful work is offline feature expansion using a different feature
  family, likely route composition or family/lineage context

## Seventeenth work unit

Run the offline rank-6 route-lineage boundary audit and prepare the result for
external review.

Status:

- completed
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_rank6_route_lineage_boundary_audit_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T033637Z__stage35_rank6_route_lineage_boundary_audit_v1/`
- review note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_boundary_review_note_2026-04-30.md`

Question:

- can pre-runtime route-composition or lineage features separate the three
  rejected rank-6 positives from the two rejected rank-6 regressions?

Result:

- boundary rows:
  - `5`
- positives:
  - `3`
- regressions:
  - `2`
- route-lineage numeric features:
  - `27`
- route-lineage categorical features:
  - `5`
- single-feature perfect separators:
  - `0`
- two-feature perfect separators:
  - `141`

Most interpretable separator family:

- candidate source rank is `1`
- and candidate is far from the existing route:
  - `candidate_novelty_distance_to_anchor >= 173.5`
  - equivalent sketches appeared using distance to Phase-C anchor, Stage-3
    top-k, or final-best key

Preferred read:

- this is a coherent posthoc hypothesis, not a promotion-ready policy
- the prior simple boundary audit failed because it lacked route context
- the mild regression is close to the existing route
- the strong regression is distant but not source-rank `1`

Current decision:

- wait for external review
- do not launch additional runtime from this branch now
- do not promote either the softened rule or the route-lineage separator

Recommended next:

- if external review accepts the lineage fields as stable and mechanistically
  meaningful, write a tiny confirmation design on held-out/disagreement rank-6
  rows before any runtime
- if no honest held-out confirmation surface exists, close rank-6 local rescue
  as a mechanism insight rather than a policy candidate

## Eighteenth work unit

Action the final dev review by moving the review draft and running the strict
offline confirmation-prep scan requested by review.

Status:

- completed
- moved review draft:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_final_dev_review_draft_2026-04-30.md`
- action note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_review_action_note_2026-04-30.md`
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_rank6_route_lineage_confirmation_prep_v1.py`
- tests:
  - `tests/tools/test_no_wli_stage35_rank6_route_lineage_confirmation_prep_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T151237Z__stage35_rank6_route_lineage_confirmation_prep_v1/`

Review verdict carried:

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

Strict action-safe route-lineage rule:

- `candidate_source == "phaseA_selected"`
- `candidate_source_rank == 1`
- `candidate_novelty_distance_to_anchor >= 173.5`

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

Interpretation:

- the review-requested strict offline scan found an honest disagreement surface
- missing lineage is now invalid, not reject
- the route-lineage action rule does not use `candidate_distance_to_final_best`
  or other posthoc fields
- no runtime was launched or authorized

Verification:

- extractor `py_compile` passed
- dedicated test file passed:
  - `9 passed`

Updated recommendation:

- inspect group A and B against existing shallow/deep evidence
- if still coherent, write a fixed-rule tiny confirmation design with named
  rows, budget, and stop condition
- do not launch runtime until that design is written and approved

## Nineteenth work unit

Launch the route-lineage additive confirmation microbatch.

Status:

- completed
- design note:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_additive_confirmation_design_2026-04-30.md`
- closeout:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_rank6_route_lineage_additive_confirmation_closeout_2026-04-30.md`
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_route_lineage_additive_confirmation_v1.py`
- console log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_route_lineage_additive_confirmation_2026-04-30.log`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153119Z__stage35_rank6_route_lineage_additive_confirmation_v1/`

Question:

- can route-lineage be used as an additive rescue rule for old-rejected rank-6
  rows without adding a confirmed regression?

Important pre-launch interpretation:

- strict route-lineage is not a replacement for the old softened rule
- group B includes old-keep / route-reject rows with existing positive
  evidence, so route-lineage replacement would be too lossy
- the test here is additive:
  - keep the old softened rule
  - additionally rescue group-A rows admitted by source-rank plus route-novelty

Cells:

- `611/search7003 rank 6 826e5c871f444486`
  - prior deepening positive; reproduction/control
- `1111/search7001 rank 6 d94845511e181f7c`
  - key safety check; shallow was negative and there is no prior deepening row
- `1411/search7004 rank 6 2632e79517bf1c7c`
  - prior deepening positive; boundary reproduction/control
- `1411/search7005 rank 6 b47e22bc63e7c189`
  - prior deepening positive; boundary reproduction/control

Runtime budget:

- intended wallclock:
  - `45m`
- hardcoded cap:
  - `2700s`
- per-cell rescue cap:
  - `600s`
- prior same-shape comparable cells:
  - about `75s` to `179s`
- stop conditions:
  - all four cells processed
  - wallclock cap reached
  - first-cell projection exceeds `2700s`
- partial writeback:
  - after every cell

Success criteria:

- `0` runtime errors
- all four route-additive keep cells run
- no executed cell regresses versus shallow
- `1111/search7001` is nonnegative versus shallow

Outcome:

- completed cells:
  - `4 / 4`
- runtime errors:
  - `0`
- elapsed:
  - `287.159s`
- first-cell projection:
  - `306.208s` versus `2700s`
- nonnegative versus shallow:
  - `3 / 4`
- regressed versus shallow:
  - `1 / 4`
- key safety cell:
  - `1111/search7001 rank 6 d94845511e181f7c`
  - shallow:
    - `0.038`
  - confirmation:
    - `0.037`
  - delta versus shallow:
    - `-0.001`
- prior-positive reproduction cells:
  - `611/search7003`: `0.475`, `+0.011` versus shallow
  - `1411/search7004`: `0.404`, `+0.005` versus shallow
  - `1411/search7005`: `0.425`, `+0.013` versus shallow
  - all three matched prior deepening exactly

Catalog / timing refresh:

- output catalog refreshed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli_catalog`
- runtime history reference refreshed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153651Z__no_wli_runtime_history_reference_v1/`
- fixed runtime wallclock reference refreshed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153651Z__fixed_runtime_wallclock_reference_v1/`

Interpretation:

- route-lineage is useful mechanism evidence but failed the additive policy
  safety check
- strict route-lineage is still not viable as a replacement because group B
  contains old-keep / route-reject rows with existing positive evidence
- this closes the current source-rank plus route-novelty rule as a policy
  candidate

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
- close the current rank-6 route-lineage policy line as policy-negative
- carry the mechanism lesson forward only as analysis context
- move back to offline mechanism analysis or a different candidate branch

