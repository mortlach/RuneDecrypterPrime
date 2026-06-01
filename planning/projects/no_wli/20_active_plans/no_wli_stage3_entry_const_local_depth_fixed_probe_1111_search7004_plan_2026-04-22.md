# Stage-3 Entry Constant-Local-Depth Fixed Probe Plan: 1111/search7004

Date: 2026-04-22

Status:

- closed
- over-budget partial plus structural closure

## Why this note exists

The paired fixed `1111/search7004` canary is now closed as an operational
runtime shape:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_fixed_canary_operational_closure_note_2026-04-22.md`

That closure did not invalidate the allocation hypothesis scientifically.

It only showed that another two-job same-cell compare is not the honest next
unit on this machine.

So the branch rescaled to the smallest independently complete live probe:

- one completed candidate job
- one stable fixed cell
- one explicit session budget
- one explicit manual stop rule

That probe has now been run and closed in the current form.

## Closed run result

Closed experiment:

- `tune_v78_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_probe_1job`

Child run dir:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T154043010456Z__bench_solve_pipeline_no_wli__ee62083/`

Outcome:

- process stopped manually after the written `~8h` stop rule had been exceeded
- no normal completion artifacts were written
- completed Phase-C starts before stop:
  - `4 / 6`

Best completed start:

- start `1`
- source:
  - `stage3_best_phaseA`
- final match:
  - `0.432`
- final score:
  - `0.17955717672334726`

Other completed starts:

- start `2`:
  - `0.413`
- start `3`:
  - `0.399`
- start `4`:
  - `0.411`

Retained comparison:

- retained run-level best match:
  - `0.423`
- retained mapped-family max final match:
  - `0.432`
- retained focus-family max final score:
  - `0.17955717672334737`

Read:

- the probe reproduced the retained anchor-family best
- it did not improve top-line outcome
- the partial bundle was already low-information before completion

Structural read:

- Stage-3 base entry budget:
  - `64`
- Stage-3 Phase-B top-n:
  - `32`
- mutations per promoted:
  - `1`
- maximum promoted-key count here:
  - `33`
- maximum target:
  - `66`

So this exact config could widen Stage-3 entry by at most:

- `+2` keys over legacy

That means the configured cap `288` never mattered on this shape.

## Closure decision

Decision:

- `close`

Meaning:

- close this exact `constant_local_depth` probe shape
- do not rerun this exact fixed-cell candidate runtime
- do not launch the contingent `1111/search7005` replication from this branch
- require a written structural-activation proof before any future allocation
  runtime

## Main question

On fixed `1111/search7004`, can the bounded constant-local-depth Stage-3 entry
candidate beat the retained bounded control reference inside an honest `~8h`
single-job session?

## Mechanism layer

- allocation

## Pre-run block

Question:

- on fixed `1111/search7004`, does the bounded constant-local-depth Stage-3
  entry candidate clear the retained bounded control reference when given one
  completed job to itself?

Suspicion:

- `1111/search7004` still looks entry-budget-starved before the bounded late
  stack gets its chance, and the candidate can show that if we stop paying for
  paired-control overhead in the same session.

Main alternative:

- the candidate is still flat or worse than retained control on this lane, or
  the new-family job still does not complete honestly enough to justify another
  overnight session.

If suspicion is true, expect:

- the candidate completes within the intended session budget
- the candidate widens executed Stage-3 entry counts versus the legacy default
- the candidate beats the retained fixed `1111/search7004` control reference:
  - retained run-level best match:
    - `0.423`

If alternative is true, expect:

- the candidate completes but stays at or below the retained reference
- or the job still fails to produce completed artifacts before the session stop

Tomorrow's decision rule:

- advance only if the candidate completes inside the `~8h` session, shows real
  executed widening, and beats the retained fixed reference cleanly
- refine only if the candidate is a narrow near-miss or a budget-fragile
  positive
- close if the candidate is flat, worse, or operationally incomplete

## What we expect to learn

This probe is meant to answer three things with one completed runtime unit:

- whether the allocation candidate has any real top-line lift at all on the
  cleanest `1111` lane
- whether the candidate really widens executed entry counts rather than only
  changing configured intent
- what the first completed wallclock anchor is for this new-family runtime

So even if the result is negative, it is still useful:

- it gives a real completed timing anchor
- it tells us whether the candidate deserves one more same-family attempt

## Why this is the right science-method step now

This is the current method correction:

- downstream replacement is already closed
- the paired entry-allocation canary is already closed operationally
- the next unit must therefore be:
  - smaller
  - independently complete
  - and still scientifically interpretable at one mechanism layer

This probe keeps the branch honest because it does not pretend a paired compare
fits the machine when it currently does not.

## Why this cell

Use exactly:

- fixture seed:
  - `1111`
- search seed:
  - `7004`

Why `1111/search7004`:

- it is still the cheapest clean `1111` exact cell:
  - retained control anchor about `2.36h`
- it is the main conversion-failure family
- the killed control canary already rescued a useful fidelity read on the same
  lane:
  - best rescued control read:
    - `0.432`
  - retained mapped-family max final match:
    - `0.432`

So this is the strongest place to spend one completed new-family candidate job.

Why not `1111/search7005` first:

- `7005` is still a good same-family replication cell
- but the first completed new-family anchor should come from the lane that
  already showed control fidelity cleanly

## Runtime budget proof

Planning references:

- `planning/projects/no_wli/20_active_plans/no_wli_runtime_budgeting_reference_note_2026-04-20.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260421T152723Z__fixed_runtime_wallclock_reference_v1/fixed_runtime_wallclock_reference.md`

Relevant retained timing:

- exact retained fixed cell `1111/search7004`:
  - `2.36h`

Budget rule for this probe:

- intended wallclock budget:
  - `8.0h`
- rationale:
  - one completed new-family candidate job only
  - more than `3x` the exact retained control anchor
  - no same-session paired control overhead

Stop condition:

- this probe does not count as "overnight until it finishes"
- if normal completion artifacts are still missing at launch `+ 8h`, kill the
  run manually and record the session as operationally incomplete
- do not leave the job running past the written stop by inertia

## Runtime shape

Fixed panel:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_1111_search7004_v1.json`

Runtime family:

- bounded Stage 3.5 retained-style candidate probe
- exact fixed cell only
- one completed job only
- `text_offsets = [5]`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1.py`

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1.py`

Launchers:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_launch_2026-04-22.ps1`
- `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_open_terminal_2026-04-22.ps1`

## Active preset

Candidate:

- derived from:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- preserve Stage 3.5
- preserve the current bounded Phase A / Phase B / Phase C stack
- change only:
  - `force_stage3_init_keys_cap = 288`
  - `force_stage3_entry_allocation_policy = "constant_local_depth"`
  - `force_stage3_entry_mutations_per_promoted = 1`

## Required outputs

This probe must produce:

- one machine-readable probe row
- one short markdown readout
- one explicit advance / refine / close recommendation
- handoff-level confirmation for:
  - `stage3_entry_allocation_policy`
  - `stage3_entry_target_before_cap`
  - `stage3_entry_cap`
  - `init3_n`
  - `stage3_init3_count`

## Decision rules

### Advance only if

- the candidate completes inside the intended `~8h` session
- the candidate beats the retained fixed reference cleanly
- real executed widening is present in the saved handoff diagnostics

### Refine only if

- the candidate is a narrow near-miss against retained control
- or a positive that looks real but still too budget-fragile to replicate yet

### Close if

- the candidate is flat or worse than retained control
- the candidate does not show real executed widening
- or the run is still incomplete at the written session stop
