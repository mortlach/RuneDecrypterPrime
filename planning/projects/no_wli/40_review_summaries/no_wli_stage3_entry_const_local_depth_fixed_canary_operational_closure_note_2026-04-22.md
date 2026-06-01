# Stage-3 Entry Constant-Local-Depth Fixed Canary Operational Closure Note

Date: 2026-04-22

Status:

- completed partial
- operational closure

## Scope

This note closes the specific two-job live canary shape:

- `tune_v76_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_compare_2job`

It does **not** close the broader entry-allocation hypothesis scientifically.

It closes the current runtime shape because the first control job already proved
too slow and too stall-prone to serve as an honest independently useful
two-job canary within the intended session budget.

## What happened

Planned shape:

- fixed `1111/search7004`
- control first
- candidate second only if the first completed job still fit the intended
  `~8h` session budget

Actual runtime read:

- matrix control files never advanced beyond:
  - `completed_jobs = 0 / 2`
  - one `job_started` event only
- actual child run directory:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T024910116301Z__bench_solve_pipeline_no_wli__ee62083/`
- final completion artifacts never appeared:
  - no `best/best_instance.json`
  - no completed `final_instances/*`
- watcher log progressed past the fifth completed start and into:
  - Phase C start `6 / 6`, step `73 / 96`
- the live process was later killed intentionally rather than left to run by
  inertia

## Rescued partial evidence

The rescued evidence is the live Phase-C checkpoint stream:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260422T024910116301Z__bench_solve_pipeline_no_wli__ee62083/phasec_start_checkpoints.jsonl`

Completed starts before kill:

- `5 / 6`

Last watcher-log line before kill:

- Phase C start `6 / 6`, step `73 / 96`

Best rescued control read:

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
- start `5`:
  - `0.364`

Last completed checkpoint timestamp:

- `2026-04-22T13:27:20.016968+00:00`

## Scientific read

The rescued partial control evidence is still useful:

- the control lane did not look badly drifted
- the best rescued control read matched the retained `1111/search7004` stable
  anchor family:
  - retained `max_mapped_family_by_final_match`:
    - `0.432`
  - rescued partial control best:
    - `0.432`

So the run did teach one real thing:

- the bounded control lane on `1111/search7004` looks faithful enough

But it did **not** teach the intended branch decision:

- the candidate never ran
- there is no control-versus-candidate comparison
- there is no completed first-job wallclock read from the matrix wrapper

## Operational read

This runtime shape is not acceptable as the next learning unit:

- the first control lane alone exceeded the intended session logic
- the run could sit in long late-stage work without producing completed-job
  artifacts
- the same-family queued follow-on did not launch because the canary never
  completed before cutoff

Queue outcome:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_queue_2026-04-22.log`
- final queue read:
  - `queue_aborted reason=cutoff_reached_before_current_completed`

## Decision

Decision on this **runtime shape**:

- `close`

Meaning:

- close the two-job live canary shape
- do not relaunch the same `v76` compare shape as another overnight unit
- do not interpret this as a candidate negative, because the candidate never ran

## Carry-forward lesson

Keep the mechanism question alive only in a smaller honest unit:

- one-job independently complete live probes
- or cheaper offline / saved-surface / shadow gates first

Do not spend another session on:

- a two-job same-cell live compare whose first control lane can already fail the
  budget and artifact-completion contract
