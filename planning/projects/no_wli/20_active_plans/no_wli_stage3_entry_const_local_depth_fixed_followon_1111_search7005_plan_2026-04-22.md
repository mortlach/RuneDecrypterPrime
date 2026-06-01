# Stage-3 Entry Constant-Local-Depth Fixed Follow-On Plan: 1111/search7005

Date: 2026-04-22

Status:

- closed non-launch
- replication gate removed

## Why this note exists

The most recent runtime canary was the bounded two-job compare on fixed
`1111/search7004`:

- `tune_v76_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_compare_2job`

If that compare finishes early enough, the remaining overnight budget until
`2026-04-22 07:00` America/Los_Angeles can still fit one more independently
complete same-family compare.

The right next cell is not another `search7002` retry and not a broader panel.

It is a second cheap `1111` Stage 3.5 cell that asks the same mechanism
question under the same bounded late stack.

That replication gate no longer exists in the current branch because the later
`1111/search7004` one-job probe was itself closed as an underpowered
non-signal.

## Closure update

Current branch read:

- the queue had already failed earlier because `v76` did not complete before
  cutoff
- later, the rescaled `1111/search7004` one-job probe also closed negative in
  the practical sense:
  - over budget
  - no completed artifact
  - no top-line lift
  - structurally too weak to test the suspicion strongly

So this `1111/search7005` follow-on is now closed as a non-launch.

Meaning:

- this is not a scientific negative on `1111/search7005`
- it is no longer an authorized replication from the closed `7004` branch

## Main question

On fixed `1111/search7005`, can constant-local-depth Stage-3 entry allocation
beat the bounded Stage 3.5 control on a second cheap conversion-failure lane?

## Mechanism layer

- allocation

## Why `1111/search7005`

- it stays inside the main `1111` conversion-failure family
- it is a retained fixed-panel Stage 3.5 case
- retained exact wallclock for `1111/search7005` is about `2.48h`
- two retained-anchor jobs project to about `4.96h`
- that is materially safer than any `611` or `1511` two-job compare for the
  remaining overnight window

Retained case read:

- status:
  - `unsolved`
- best stage:
  - `stage35_substitution_only`
- best match:
  - `0.372`
- baseline lane:
  - `phaseA_selected/challenger`
- mapped late-family read:
  - `f0`-dominant with a small `f1` tail

So this is a useful second `1111` read:

- cheaper than `1111/search7001`
- cleaner than reopening the heavy `1111/search7002` seed
- still a real Stage 3.5 conversion-failure shape rather than a solved control

## Pre-run block

Question:

- on fixed `1111/search7005`, does preserving the bounded Stage 3.5 baseline
  stack but widening Stage-3 entry with constant-local-depth beat the bounded
  control?

Suspicion:

- if entry-budget starvation is real on `1111`, the widened entry should not
  be only a `7004` one-off and should have a second chance to help on
  `1111/search7005`.

Main alternative:

- the `7004` result, whatever it is, does not generalize to the next cheap
  `1111` lane, and `7005` stays flat or worse under the widened entry.

If suspicion is true, expect:

- the candidate again widens executed entry counts versus control
- and the candidate beats control on run-level best match or late-route outcome

If alternative is true, expect:

- widened entry executes but the candidate stays flat or worse than control

Tomorrow's decision rule:

- promote only if the candidate beats control on `7005`, the widening really
  executes, and the runtime still fits the remaining overnight budget
- refine only if the result is slightly positive but still narrow
- close if the candidate is flat or worse on this second same-family cell

## What we expect to learn

This follow-on is not a broader sweep.

It exists to answer one replication question:

- if `1111/search7004` is positive or narrowly ambiguous, does the same
  entry-allocation idea repeat on a second cheap `1111` conversion-failure
  lane?

So the expected learning is:

- whether the mechanism is a same-family effect rather than a one-cell accident
- whether executed widening on `7004` carries to another `1111` lane
- whether the branch should move toward:
  - promote
  - refine
  - or close

## Why this is the right science-method step now

This is the current replication step in the method:

- first run the smallest honest live falsification on fixed `1111/search7004`
- only if that finishes inside budget and still looks scientifically readable,
  ask the same mechanism question on a second cheap `1111` lane
- do not widen to a broader panel until the same-family read exists

That keeps the branch disciplined:

- one mechanism layer
- one family
- one cheap replication cell

## Runtime budget proof

Runtime reference:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260421T152723Z__fixed_runtime_wallclock_reference_v1/fixed_runtime_wallclock_reference.md`

Exact retained anchor:

- `1111/search7005`:
  - `2.48h`

Two-job retained-anchor total:

- about `4.96h`

Overnight gate:

- this run is authorized only if the active `1111/search7004` compare finishes
  early enough to leave a realistic same-family window before
  `2026-04-22 07:00` America/Los_Angeles
- use `2026-04-22 01:15` America/Los_Angeles as the latest honest auto-launch
  cutoff
- if the active compare is not complete by then, do not auto-launch this run

Why that cutoff is honest:

- `01:15` to `07:00` leaves about `5.75h`
- the retained two-job anchor is about `4.96h`
- that preserves some margin while still using the remaining overnight budget

## Queue outcome

- the follow-on never launched
- queue log:
  - `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_queue_2026-04-22.log`
- final queue read:
  - `queue_aborted reason=cutoff_reached_before_current_completed`

Interpretation:

- this is not a scientific negative on `1111/search7005`
- it is only a launch-gate failure because the `1111/search7004` canary did not
  complete the first job before cutoff

## Runtime shape

Fixed panel:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_1111_search7005_v1.json`

Runtime family:

- bounded Stage 3.5 retained-style compare
- exact fixed cell only
- `text_offsets = [5]`

Presets:

- control:
  - `stage35_baseline_score_plus_novelty_live_bounded_p9`
- candidate:
  - bounded baseline carry-forward with:
    - `force_stage3_init_keys_cap = 288`
    - `force_stage3_entry_allocation_policy = "constant_local_depth"`
    - `force_stage3_entry_mutations_per_promoted = 1`

## Required outputs

This follow-on must produce:

- one machine-readable per-run comparison table
- one short markdown readout
- one explicit promote / refine / close recommendation
- handoff-level confirmation for:
  - `stage3_entry_allocation_policy`
  - `stage3_entry_target_before_cap`
  - `stage3_entry_cap`
  - `init3_n`
  - `stage3_init3_count`

## Operational rule

Do not launch this follow-on in parallel with the active `1111/search7004`
compare.

If launched, it should start only after the active compare is complete and only
before the cutoff above.
