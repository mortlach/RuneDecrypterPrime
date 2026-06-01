# Stage-3 Entry Constant-Local-Depth Fixed Probe Closure Note: 1111/search7004

Date: 2026-04-22

Status:

- closed
- over-budget partial plus structural negative

## Scope

This note closes the specific one-job live probe shape:

- `tune_v78_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_probe_1job`

It also closes the exact fixed-probe configuration used here:

- fixed `1111/search7004`
- bounded Stage 3.5 preserved
- `force_stage3_init_keys_cap = 288`
- `force_stage3_entry_allocation_policy = "constant_local_depth"`
- `force_stage3_entry_mutations_per_promoted = 1`

It does **not** prove that every possible entry-allocation idea is false.

It closes this probe because it was both:

- over budget without producing normal completion artifacts
- structurally too weak to count as an honest test of the stated
  entry-budget-starvation suspicion

## What happened

Planned shape:

- one fixed-cell candidate-only probe
- intended wallclock budget:
  - `~8h`
- manual stop rule:
  - kill if normal completion artifacts are still missing at launch `+ 8h`

Actual runtime read:

- child run directory:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T154043010456Z__bench_solve_pipeline_no_wli__ee62083/`
- process start in matrix control state:
  - `2026-04-22T15:40:42.946501+00:00`
- process was later stopped manually
- normal completion artifacts never appeared:
  - no `best/best_instance.json`
  - no completed `final_instances/*`
- run manifest stayed at:
  - `run_status = "running"`

## Rescued partial evidence

The rescued evidence is the live Phase-C checkpoint stream:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T154043010456Z__bench_solve_pipeline_no_wli__ee62083/phasec_start_checkpoints.jsonl`

Completed starts before stop:

- `4 / 6`

Completed start reads:

- start `1`:
  - source:
    - `stage3_best_phaseA`
  - final match:
    - `0.432`
  - final score:
    - `0.17955717672334726`
  - became global best:
    - `1`
- start `2`:
  - source:
    - `phaseB_topk`
  - final match:
    - `0.413`
  - final score:
    - `0.1716928019549998`
- start `3`:
  - source:
    - `phaseB_topk`
  - final match:
    - `0.399`
  - final score:
    - `0.16823409738024098`
- start `4`:
  - source:
    - `phaseB_topk`
  - final match:
    - `0.411`
  - final score:
    - `0.16719620333317853`

## Scientific read

The partial evidence is already enough to answer the main practical question.

Best partial read versus retained `1111/search7004` reference:

- retained run-level best match:
  - `0.423`
- retained mapped-family max final match:
  - `0.432`
- retained focus-family max final score:
  - `0.17955717672334737`
- probe best completed start:
  - final match `0.432`
  - final score `0.17955717672334726`

Interpretation:

- the probe reproduced the retained anchor-family best
- it did **not** show a new top-line lift
- the completed non-anchor starts were all weaker

Partial stop-signal read:

- completed starts with `shadow_stop_v1.plateau_would_stop = 1`:
  - `3 / 4`
- those starts were:
  - start `1`
  - start `2`
  - start `4`

So the run had already become low-information before completion.

## Structural activation read

This is the more important closure reason.

The probe was meant to test whether entry allocation was materially widening
Stage-3 entry on this lane.

But the actual config math made that nearly impossible:

- Stage-3 base entry budget:
  - `64`
- Stage-3 Phase-B top-n:
  - `32`
- entry policy:
  - `constant_local_depth`
- mutations per promoted:
  - `1`

The seeding rule is:

- `entry_target_before_cap = max(base_budget, len(promoted_keys) * (1 + mutations_per_promoted))`

And the promoted-key builder can produce at most:

- one `best_key`
- plus up to `32` promoted keys
- so at most `33` keys

Therefore the absolute best-case target here is:

- `max(64, 33 * 2) = 66`

Meaning:

- the theoretical widening over legacy is only:
  - `+2` keys
- the configured cap `288` is irrelevant on this shape

So this probe was not an honest live falsification of a strong
entry-budget-starvation hypothesis.

It was structurally too weak.

## Decision

Decision on this probe:

- `close`

Meaning:

- close the exact `1111/search7004` one-job probe shape
- do not rerun this exact `constant_local_depth` fixed probe
- do not launch the contingent `1111/search7005` replication from this branch

## Carry-forward lesson

Future allocation studies need a written pre-launch structural-activation
proof.

Minimum requirement before any new live allocation runtime:

- show the maximum theoretical widening over legacy for the actual config
- show that the widening is materially larger than trivial noise
- show that the budget still fits an honest session

If that proof cannot be made cheaply, the next branch should move upstream
from entry allocation rather than spending more runtime on this exact line.
