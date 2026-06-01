# Phase-B challenger supply matrix v1 operational closure note

Date: 2026-04-20

Status:

- closed
- operational failure
- rescued partial data retained

## Question

Can wider upstream Phase-B saved challenger supply create real spare
non-selected retained `phaseB_topk` challengers for downstream Phase-C use?

## What happened

The intended runtime batch was:

- `18` jobs
- primary trio:
  - `611`
  - `1111`
  - `1511`
- retained search seeds:
  - `7002`
  - `7004`
- three upstream supply presets

That batch was launched as one serial matrix with a `14`-hour wallclock cap.

This was a sizing mistake.

The first completed job alone took about `18h57m`, so the matrix stopped after
`1/18` jobs with the wallclock already exceeded.

The batch therefore did not fail scientifically first. It failed operationally
as a wrongly scoped serial run for this machine and budget.

## Rescued valid data

One child run completed cleanly and remains valid:

- run bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260419T153752267602Z__bench_solve_pipeline_no_wli__ee62083/`
- case:
  - `611/search7002`
- preset:
  - `phaseb_supply_selected24_saved16_stage3only_v1`

Key rescued read:

- elapsed:
  - about `18h57m`
- best match ratio:
  - `0.424`
- winner stayed:
  - `stage3_best_phaseA / anchor`
- retained `phaseB_topk` saved count:
  - `1`
- true spare non-selected retained `phaseB_topk` challengers:
  - `0`

This is one valid canary datapoint.

It is not a full-study answer.

## What this closure does and does not mean

This closure does mean:

- the original `18`-job matrix shape should not be continued by inertia
- the batch sizing was not justified honestly enough before launch
- the current line needs a retake format that preserves completed data and uses
  time more carefully

This closure does not mean:

- the upstream supply mechanism question is answered fully
- the upstream supply line is scientifically closed
- the rescued canary should be discarded

## Carry-forward lessons

- long serial runtime matrices need explicit wallclock proof before launch
- first completed jobs must be treated as a sizing gate, not just progress
- incomplete matrices must still be extractable so rescued completed jobs are
  not lost
- helper and catalog code must resolve repo root, not current working
  directory, for end-of-run writeback

## Immediate next plan

The next active line is a retake, not a resume-by-inertia.

That retake should:

- keep the rescued canary
- use independently complete microbatches
- review after each microbatch
- stop early if the line is already operationally or scientifically closed

Held next-branch candidate if the supply retake closes cleanly:

- `stage3_entry_const_local_depth_p9`
