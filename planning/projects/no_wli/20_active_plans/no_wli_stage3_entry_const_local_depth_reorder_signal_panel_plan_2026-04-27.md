# no-WLI Stage-3 Entry Constant-Local-Depth Reorder-Signal Panel Plan

Date: 2026-04-27

Status:

- completed capped run
- direct-run Python file only
- intended for one 10-hour capped runtime block; capped after one completed job
- uses existing fixed-panel / mainflow machinery
- not a saved-surface replay
- not a live-runtime promotion

## Why this exists

The Phase-C multi-thread long harvest completed cleanly:

- 19 cases
- 27 policies
- 3 passes
- 1539 / 1539 policy units
- repeated exact replays were stable
- depth / quota / replacement saved-surface variants did not beat the existing reorder controls

Main conclusion from that run:

- more saved-surface reshuffling is not the next best lever
- the useful remaining mechanism is likely downstream of the best reorder controls
- the next mechanism to test is local search / rescue / Stage-3 entry allocation

## Question

On the 1111 reorder-signal lanes, can the constant-local-depth Stage-3 entry preset beat the bounded Stage-3.5 control within one honest 10-hour capped panel run?

## Suspicion

The saved-surface atlas showed that the existing reorder controls sometimes move score or route, but the extra surface reshuffling policies do not add value.

That suggests the next bottleneck may not be “which extra surface reshuffle?”, but whether the solver gives the promising Stage-3 entry enough local search / rescue budget after the route is selected.

The constant-local-depth entry preset may help by widening executed Stage-3 entry search in a controlled way.

## Main alternative

The current bounded Stage-3.5 control already captures the useful late route. Constant-local-depth entry will either stay flat, become worse, or cost too much wallclock for too little gain.

## Mechanism layer

- local search / rescue
- Stage-3 entry allocation
- not Stage2 checkpointing
- not saved-surface reshuffling
- not live-runtime promotion

## Target panel

This run uses one generated fixed-panel spec:

`planning/projects/no_wli/30_analysis_specs/generated_panels/p9_c3_solver_panel_1111_reorder_signal_stage3_entry_const_local_depth_v1.json`

The panel contains:

- fixture: `fixture_001__p9_c3_l1000__text0__seed1111`
- search seeds:
  - `7002`
  - `7004`
  - `7005`

Why these:

- `1111/search7002` had positive reorder-control signal in the atlas.
- `1111/search7004` is the main hard conversion-failure / route-signal lane.
- `1111/search7005` is a useful adjacent 1111 context lane already supported by existing fixed-panel history.

## Presets

Control preset:

`stage35_baseline_score_plus_novelty_live_bounded_p9`

Candidate preset:

`stage35_baseline_score_plus_novelty_live_bounded_entry_const_local_depth_v1`

Candidate preset changes relative to control:

- `force_stage3_init_keys_cap = 288`
- `force_stage3_entry_allocation_policy = constant_local_depth`
- `force_stage3_entry_mutations_per_promoted = 1`

## Jobs

Expected jobs:

- 3 search seeds
- 2 presets
- 1 text offset
- total expected jobs: 6

## Runtime budget

Hard cap:

- 10 hours

This is a cap, not a success criterion.

If the run finishes early:

- do not immediately start a different branch without review
- first inspect completed jobs and matrix state

If the run caps:

- partial output is useful
- review completed jobs only
- do not treat cap as a science failure unless no interpretable jobs completed

## Output locations

Matrix/control outputs use the usual no-WLI matrix output root:

`output/tools/benchmarks/periodic_sub_trans/no_wli/`

Experiment run id:

`tune_v79_fixed_p9c3_1111_reorder_signal_stage35_entry_const_local_depth_panel_6job`

Expected control files and run state will be under that experiment id.

The generated fixed-panel spec is written under:

`planning/projects/no_wli/30_analysis_specs/generated_panels/`

The normal output catalogue is refreshed at the end of the run.

## What to inspect after run

First inspect:

- matrix run state
- completed job count
- failed job count
- per-job best match ratio
- best stage
- elapsed time
- Stage-3 entry diagnostics
- Stage-3 entry target before cap
- Stage-3 entry cap
- Stage-3 entry cap applied
- Stage-3 init3 count
- promoted key count
- whether constant-local-depth actually widened execution

## Decision rule

Advance only if:

- candidate beats control on at least one target lane by a meaningful score movement
- the candidate actually widens executed Stage-3 entry / local search
- output is complete enough to compare against control
- runtime is acceptable under the 10-hour capped session

Hold if:

- candidate is near-flat but diagnostics show real entry widening
- not enough jobs complete to judge all lanes
- runtime/cap behaviour makes the result ambiguous

Close if:

- candidate is flat or worse on all completed lanes
- candidate does not materially widen executed entry
- candidate costs more wallclock without score or route benefit

## Non-goals

Do not use this run to:

- tune the Stage2 checkpoint
- reopen live runtime
- add new saved-surface policies
- rerun the Phase-C width/quota/replacement atlas
- claim a production policy
- run multiprocessing
- edit core solver code

## First launch check

After the run starts, confirm the console prints a JSON study summary with:

- run label
- experiment run id
- fixed panel path
- search seeds `[7002, 7004, 7005]`
- preset ids
- job count `6`
- max wallclock `10h`

Then let it run.

## After completion

Do not start the next branch until this run is reviewed.

The intended close-out question is:

Did constant-local-depth Stage-3 entry allocation convert any 1111 reorder-signal lane into a better result than the bounded Stage-3.5 control?





Yes — this is enough to analyse meaningfully.

## Immediate verdict

This run produced **one completed job**, not a completed panel.

```text id="zqyf3s"
planned jobs:      6
completed jobs:    1
completed seed:    1111/search7002
job elapsed:       13h32m47s
matrix cap:        10h
panel status:      capped after first job
best match:        0.754
best stage:        stage35_substitution_only
status:            unsolved
```

So the main finding is:

```text id="1ll7de"
The first control-style job ran far beyond the intended 10h panel budget and
blocked the rest of the comparison.
```

That is not useless — it is a useful single-job result — but it does **not** answer the intended candidate-vs-control question yet.

---

# 1. What actually ran

The matrix started correctly:

```text id="e0ix5y"
fixture:
  fixture_001__p9_c3_l1000__text0__seed1111

search seed:
  7002

p/c:
  p9 / c3

profile:
  c_min_late

planned comparison:
  control bounded Stage-3.5 preset
  vs constant-local-depth entry preset
```

But only the first job completed before the matrix cap was checked:

```text id="nxks2p"
[no_wli_fixture_matrix] completed 1/6
[no_wli_fixture_matrix] wallclock cap reached
elapsed = 48767.4s
cap = 36000.0s
completed_jobs = 1
```

The cap was checked **between jobs**, not inside the job. So a single job can exceed the cap.

That matters for planning.

---

# 2. Which preset probably completed?

The completed job appears to be the **control-style legacy entry job**, not the constant-local-depth candidate.

Evidence from `run_config.json`:

```text id="y18ghm"
entry.allocation_policy:
  legacy_fixed_budget

entry.mutations_per_promoted:
  1

period_scaling.init_keys_cap:
  192
```

The candidate preset we intended had:

```text id="6ax4zp"
force_stage3_init_keys_cap = 288
force_stage3_entry_allocation_policy = constant_local_depth
force_stage3_entry_mutations_per_promoted = 1
```

So the completed job does **not** look like the candidate constant-local-depth job. It looks like the bounded control job.

Therefore:

```text id="j3pygj"
We do not yet have a candidate-vs-control comparison.
```

---

# 3. Score result

The completed job result:

```text id="q4qywt"
best_match_ratio: 0.754
best_stage:       stage35_substitution_only
status:           unsolved
```

Stage progression:

```text id="u44o9u"
Stage 2 exact:
  match = 0.091

Stage 3 Phase A best:
  max match = 0.329
  max score = 0.142965

Stage 3 Phase B:
  match = 0.734
  score = 0.284349

Stage 3 Phase C:
  match = 0.750
  score = 0.302229

Stage 3.5:
  accepted
  final/best match = 0.754
```

So the job did produce a strong result for this lane:

```text id="y05upx"
1111/search7002 reached 0.754
```

That is consistent with the earlier Phase-C atlas signal where `1111/search7002` could reach around `0.754` under the useful reorder controls.

Plain English:

```text id="6h5rb8"
The full pipeline already recovers the useful 7002 route to about the same level
as the reorder-control atlas. It does not solve the case, but it does reach the
known useful region.
```

---

# 4. Stage breakdown

The internal stage timing columns only account for part of the total wallclock, because Phase C does not report its full wallclock into the simple `seconds` column.

Visible stage timing:

```text id="0531jw"
Stage 1:
  487 s
  ~8.1 min

Stage 3 Phase A:
  64 restarts
  3354 s
  ~55.9 min
  4,553,024 evals

Stage 3 Phase B:
  1278 s
  ~21.3 min
  1,942,146 evals

Stage 3.5:
  890 s
  ~14.8 min
  1,189 evals
```

The overall job time was:

```text id="6jn60k"
48,752 s
~13h32m
```

So most of the wallclock is not exposed as `seconds` in the main stage rows. The obvious suspect is Phase C / replay scoring overhead, because the total job went from early morning to late afternoon, and Stage 3.5 only starts near the end.

This is an important instrumentation gap:

```text id="tghtfs"
The completed job is interpretable for score and stage outcome, but not cleanly
interpretable for wallclock attribution.
```

---

# 5. Stage 3 Phase A

Phase A did 64 restarts.

Best Phase A match:

```text id="kk1bb8"
restart 20:
  match = 0.329
  score = 0.081173
```

Best Phase A score:

```text id="gdf8uu"
restart 11:
  match = 0.289
  score = 0.142965
```

That distinction matters:

```text id="zswngf"
best match and best score are not the same Phase-A restart.
```

The Stage-B gate used score, not truth match, so the route that ultimately feeds the later stages is not necessarily the highest-match Phase-A row.

That is expected under non-oracle scoring, but it is useful context.

---

# 6. Stage 3 Phase B and C

Phase B:

```text id="zybtkw"
phaseB_top_n = 32
phaseB_top_n_used = 32
phaseB_selected_unique_end_hash = 32
phaseB_topk_saved_count = 5
match = 0.734
```

This is good. It means the Phase-B selection layer did produce a strong route.

Phase C:

```text id="cxbcds"
phaseC_start_keys_used = 6
phaseC_start_policy = source_order
phaseC_steps = 96
phaseC_evals = 9216
phaseC_improved_best = 1
match = 0.750
```

So Phase C improved the Phase-B route:

```text id="br5wzx"
0.734 -> 0.750
```

That is useful but small.

Then Stage 3.5 lifted final best to:

```text id="n8rgc6"
0.754
```

Again small, but real.

---

# 7. Stage 3.5 details

Stage 3.5 completed normally:

```text id="j62slj"
stage35_requested_cfg = 1
stage35_enabled = 1
stage35_ran = 1
stage35_completed = 1
stage35_capped = 0
stage35_accept_reason = accepted
stage35_evals = 1189
stage35_runtime_seconds = 890.15
stage35_archive_count = 12
stage35_seed_count = 6
```

Stage 3.5 selected:

```text id="uuxdg5"
selected candidate hash:
  4814cb61f95af7e0

baseline candidate hash:
  36e2e7cb81dbf1bd

baseline candidate source:
  phaseB_topk

baseline selector:
  score_plus_novelty
```

So Stage 3.5 did select a different archive candidate from the baseline.

But its score is lower than Phase C’s scoring row:

```text id="cpl0ys"
Phase C score:
  0.302229

Stage 3.5 best score:
  0.295596
```

Yet final best stage is reported as `stage35_substitution_only` and final match is `0.754`.

So the important thing here is:

```text id="kesxdp"
Stage 3.5 improved truth match slightly, but not search score.
```

That is a familiar non-oracle tension: the accepted result may be better by truth match but not obviously better by scoring surface.

---

# 8. Comparison to the intended experiment

The intended question was:

```text id="p0lv91"
Does constant-local-depth Stage-3 entry allocation beat bounded Stage-3.5
control on the 1111 reorder-signal lanes?
```

This run does **not** answer that yet, because:

```text id="40wqfd"
only 1/6 jobs completed
the completed job appears to be the control preset
no candidate constant-local-depth job completed
no paired seed comparison exists
```

So the correct conclusion is:

```text id="l5ai6q"
The panel design was scientifically reasonable, but the job runtime made the
panel execution impractical as configured.
```

---

# 9. What this teaches

This run teaches three useful things.

## A. `1111/search7002` is expensive in full pipeline mode

The job took:

```text id="ap82tv"
13h32m
```

That is too long for a six-job 10h panel.

So future panel jobs need either:

```text id="jj93io"
per-job caps
```

or:

```text id="nuhgx3"
replay/resume from saved handoff points
```

rather than full pipeline from scratch.

## B. The control route is already strong

The control full-pipeline result reached:

```text id="s4pmkd"
0.754
```

This is near the best known reorder-control region for `1111/search7002`.

So this lane may not be the best first local-depth comparison unless we can start from a saved handoff and isolate Stage 3.5/local-depth.

## C. We are not making good enough use of saved replay/handoff data yet

This run produced handoffs:

```text id="isijqp"
resume_handoffs/.../stage2_resume.json
resume_handoffs/.../stage3_prep.json
resume_handoffs/.../stage35_seed_archive.json
```

Those are exactly the artefacts we should use next.

The next run should not recompute Stage 1, Phase A, Phase B, and Phase C from scratch for every preset.

---

# 10. Recommended next step

Do **not** rerun the same six-job panel.

Instead, design a resume/handoff-based comparison.

## New branch

```text id="nnbm9h"
stage35_resume_from_handoff_const_local_depth_v1
```

## Question

```text id="5k1tqq"
Starting from the saved 7002 handoff/archive, can a constant-local-depth or
wider Stage-3.5/local-rescue variant improve beyond the accepted 0.754 result
without recomputing the full 13.5h pipeline?
```

## Use these existing artefacts

From this completed job:

```text id="x15i91"
resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7002/
  stage2_resume.json
  stage3_prep.json
  stage35_seed_archive.json
  manifest.json
```

## Compare variants only on the late stage

For example:

```text id="vmtcy2"
control stage35 archive replay
constant-local-depth Stage 3.5 / local rescue variant
possibly one wider local search variant
```

Use shorter per-variant caps.

Target:

```text id="8v8bvi"
30-90 minutes per late-stage variant
```

not 13.5 hours per full job.

This would make much better use of compute.

---

# 11. Should we continue current matrix?

No.

It has already stopped after one completed job due cap. I would not restart it as-is.

Reason:

```text id="n9tt2t"
At ~13.5h per full job, the 6-job panel could take days, and the first job was
only the control.
```

The correct move is to extract value from the completed handoff and switch to a late-stage-only comparison.

---

# 12. Close-out for this job

I would write:

```text id="abq8jc"
The Stage-3 entry constant-local-depth panel launched correctly but capped after
one completed job. The completed job was 1111/search7002 and appears to be the
control/legacy-entry preset, not the constant-local-depth candidate.

The job reached best_match_ratio = 0.754, with best_stage =
stage35_substitution_only. Stage progression was Stage B 0.734, Phase C 0.750,
Stage 3.5 0.754. Stage 3.5 completed and was accepted, but the overall job took
13h32m, exceeding the 10h panel cap before any paired candidate comparison could
run.

Conclusion:
The full-pipeline panel is too expensive as configured. Do not rerun this
six-job panel from scratch. Use the saved resume handoff and stage35 archive to
build a late-stage-only comparison instead.
```

## Bottom line

```text id="e37l8f"
Useful data: yes.
Answered intended comparison: no.
Main result: full-pipeline panel is too expensive; completed control reached 0.754.
Next best move: use saved handoff/archive for late-stage-only rescue comparison.
```
