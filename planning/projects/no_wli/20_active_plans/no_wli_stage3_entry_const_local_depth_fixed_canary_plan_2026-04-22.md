# Stage-3 Entry Constant-Local-Depth Fixed Canary Plan

Date: 2026-04-22

Status:

- completed partial
- operational closure

## Why this note exists

The richer-pool downstream replacement reopen is now closed:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260422T015033Z__phasec_richer_pool_phaseb_replacement_reopen_v1/`

That closure matters because it removed the last active downstream follow-up on
the richer `1111/search7002` pool:

- reorder-only `phaseb_topk_frontload_all_v1` stayed the only exact-lane lift
- active replacement widths changed membership and order but stayed flat
- the spare richer-pool challengers were real, but the narrow downstream
  replacement lever was still not solver-usable

So the held next branch now becomes the active one, but with one important
carry-forward constraint:

- preserve the current bounded Stage 3.5 baseline stack
- change only the Stage-3 entry allocation mechanism

Do not reopen the old stage3-only entry compare as if it were still the right
baseline.

The retained `1111` fixed-panel runs all finish at `stage35_substitution_only`,
so a stage3-only compare would now answer the wrong question.

## Main question

On the bounded Stage 3.5 baseline stack for fixed `1111/search7004`, can a
constant-local-depth Stage-3 entry allocation widen the useful lane enough to
beat the current bounded control within an honest `~8h` two-job budget?

## Mechanism layer

- allocation

## Pre-run block

Question:

- on fixed `1111/search7004`, does preserving the current bounded Stage 3.5
  stack but widening Stage-3 entry with constant-local-depth beat the bounded
  control?

Suspicion:

- `1111/search7004` is a fragmented conversion-failure case where the bounded
  Stage 3.5 stack is already useful, but the legacy fixed-budget Stage-3 entry
  may still be too narrow before the late stack gets its chance.

Main alternative:

- the current bounded stack is already capturing what this cell can use, so a
  wider constant-local-depth entry just burns extra entry work and stays flat
  or worse.

If suspicion is true, expect:

- the candidate run shows a larger Stage-3 entry target and initialization
  count than control
- and the candidate beats the bounded control on run-level best match or lands
  a meaningfully better late-route outcome

If alternative is true, expect:

- the candidate widens entry counts but stays flat or worse than control
- or the widened entry does not materially change the actual Stage-3 start lane

Tomorrow's decision rule:

- promote only if the candidate beats control with a meaningful run-level gain,
  the entry widening really executes, and the two-job session stays inside the
  intended budget
- refine only if the gain is real but still too small or noisy to generalize
- close if the candidate stays flat or worse even after the wider entry really
  executes

## What we expect to learn

This run is meant to answer three things at once, but only at one mechanism
layer:

- whether the main `1111` conversion-failure family still looks
  entry-budget-starved after preserving the current bounded late stack
- whether wider Stage-3 entry produces a better late-route outcome on a stable
  fixed lane
- whether the candidate really widens executed entry counts rather than only
  changing configured intent

If this canary is flat or harmful even with real executed widening, the current
entry-allocation idea is much weaker than the earlier downstream suspicions and
should not be extended by inertia.

## Why this is the right science-method step now

This branch follows the current method discipline:

- close the previous downstream line before opening a new one
- preserve the currently trusted bounded Stage 3.5 baseline
- change only one mechanism layer:
  - `allocation`
- start on the cheapest independently complete same-family cell that can falsify
  the suspicion honestly

So this is not "try another tweak."

It is the next controlled falsification step after:

- richer-pool downstream replacement closed
- downstream ordering remained the only small positive
- the real unresolved question moved upstream from `ordering` to `allocation`

## Why this is the right next move

This is the smallest honest runtime canary after the richer-pool reopen closed:

- it tests a different mechanism layer
- it avoids the now-heavy `1111/search7002` timing class
- it preserves the currently trusted bounded Stage 3.5 stack
- it asks the next branch question on the main `1111` conversion-failure family

## Chosen cell

Use exactly:

- fixture seed:
  - `1111`
- search seed:
  - `7004`

Why `1111/search7004`:

- it is still a primary `1111` conversion-failure case
- it is a retained fixed-panel cell with a clean exact wallclock reference
- retained fixed `1111/search7004` control runtime is about `2.36h`
- it is materially cheaper than the now-heavy `1111/search7002` family

Do not use `1111/search7002` as the first runtime confirmation cell here:

- the retained wallclock reference now shows `1111/search7002` spanning about
  `2.32h` to `18.81h`
- the richer-supply family changed that seed into a heavy timing class
- this plan is explicitly sized for an intended `~8h` session, not for a new
  open-ended timing-class discovery on `search7002`

## Runtime budget proof

Planning reference:

- `planning/projects/no_wli/20_active_plans/no_wli_runtime_budgeting_reference_note_2026-04-20.md`
- retained fixed wallclock note:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260421T152723Z__fixed_runtime_wallclock_reference_v1/fixed_runtime_wallclock_reference.md`

Relevant retained timing:

- exact retained fixed cell `1111/search7004`:
  - `2.36h`

Initial canary shape:

- `2` jobs total
- same fixed cell for both jobs
- control first
- candidate second only if the first job still projects inside the intended
  session budget

Initial conservative sizing:

- control anchor:
  - `2.36h`
- doubled exact-cell anchor:
  - `4.72h`
- generous margin for a new entry-allocation family:
  - still below `8h`

Stop condition:

- after the first completed job, compare actual elapsed time against the
  intended `~8h` two-job session budget
- if the projection already overruns budget materially, stop and do not keep
  the second job running by inertia
- otherwise stop after both jobs complete

## Outcome

Experiment:

- `tune_v76_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_compare_2job`

Outcome:

- the live process was later killed intentionally
- no active multi-hour no-WLI runtime is currently confirmed from repo state
- the matrix wrapper never advanced beyond `job_started`
- `completed_jobs` stayed at `0 / 2`
- no completed-job artifacts were written
- the candidate never ran

Rescued partial control evidence:

- child run dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T024910116301Z__bench_solve_pipeline_no_wli__ee62083/`
- completed Phase-C starts before kill:
  - `5 / 6`
- watcher-log last line before kill:
  - Phase C start `6 / 6`, step `73 / 96`
- best rescued control read:
  - source:
    - `stage3_best_phaseA`
  - final match:
    - `0.432`
  - final score:
    - `0.17955717672334726`

Interpretation:

- the bounded control lane looked faithful enough
- this specific two-job live canary shape did not
- this plan is therefore closed operationally as a runtime shape, not as a
  scientific negative on the allocation hypothesis

## Runtime shape

Fixed panel:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_1111_search7004_v1.json`

Runtime family:

- bounded Stage 3.5 retained-style compare
- exact fixed cell only
- `text_offsets = [5]`

## Presets

Control:

- `stage35_baseline_score_plus_novelty_live_bounded_p9`

Candidate:

- derived from the same bounded baseline preset
- preserve Stage 3.5
- preserve the current bounded Phase A / Phase B / Phase C stack
- change only:
  - `force_stage3_init_keys_cap = 288`
  - `force_stage3_entry_allocation_policy = "constant_local_depth"`
  - `force_stage3_entry_mutations_per_promoted = 1`

## Required outputs

This canary must produce:

- one machine-readable per-run comparison table
- one short markdown readout
- one explicit promote / refine / close recommendation
- handoff-level confirmation for:
  - `stage3_entry_allocation_policy`
  - `stage3_entry_target_before_cap`
  - `stage3_entry_cap`
  - `init3_n`
  - `stage3_init3_count`

## Decision rules

### Promote only if

- candidate best match clearly beats control
- the control lane is not badly drifted from the retained fixed reference
- the widened entry actually executes in the saved handoff diagnostics
- the two-job session fits the intended budget

### Refine only if

- candidate beats control slightly
- but the gain is still too small, noisy, or budget-fragile to generalize

### Close if

- candidate is flat or worse than control
- or the widened entry never really changes the executed handoff counts
- or the first completed job already proves the family is over budget for this
  session shape
