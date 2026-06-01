# Phase-B challenger supply retake plan

Date: 2026-04-20

Status:

- completed branch point
- retake
- microbatch runtime study

## Why this note exists

`phaseb_challenger_supply_matrix_v1` is now closed as an operational failure of
batch sizing, not as a scientific closure of the upstream supply question.

The original `18`-job serial matrix was not an honest overnight batch on this
machine. The first completed job took about `18h57m`, and the matrix stopped
after `1/18` jobs.

The rescued completed canary remains valid and should be kept:

- `611/search7002`
- `phaseb_supply_selected24_saved16_stage3only_v1`
- true spare non-selected retained `phaseB_topk` challengers:
  - `0`

## Main question

The scientific question is unchanged:

- can wider upstream Phase-B saved challenger supply create real spare
  non-selected retained `phaseB_topk` challengers for downstream Phase-C use?

The operational method is now different.

## Retake rules

This retake must obey all of these:

- no monolithic multi-job serial matrix without runtime proof
- each session must end with one independently complete microbatch
- every completed microbatch must be extracted immediately
- every incomplete batch must still produce a partial coverage readout
- path resolution must use repo root, not current working directory

## Mechanism layer

- supply

## Required pre-run block

Before each microbatch, write:

- Question
- Suspicion
- Main alternative
- If suspicion is true, expect
- If alternative is true, expect
- Tomorrow's decision rule

## Runtime budget rule

Use runtime more carefully than in `v1`.

So for this retake:

- one microbatch means one job
- do not queue the next job automatically
- review the completed output before launching the next one
- if one job already makes the line look operationally unreasonable or
  scientifically weak, stop
- every microbatch must declare an intended wallclock budget before launch
- if the cheapest canary that can answer the question already looks too slow,
  do not launch a deeper or wider cell first

Original intended session budget:

- target budget:
  - `12h`
- hard stop cap:
  - `12h`
- selection rule:
  - prefer the smallest one-job canary that can still falsify the supply
    suspicion

## Retake shape

This retake uses independently complete one-job microbatches.

Each microbatch is:

- one fixed case
- one retained search seed
- one explicit upstream supply preset
- one independent experiment id

That means every session ends with a complete artifact bundle rather than an
interrupted fraction of a large matrix.

## Priority order

The current rescued canary already covers:

- `611/search7002`
- `phaseb_supply_selected24_saved16_stage3only_v1`

The next high-information microbatch should be:

1. `1111/search7002`
2. preset:
   - `phaseb_supply_selected24_saved64_stage3only_v1`

Why this is first:

- `1111` is the clearest conversion-failure case
- the rescued canary already showed that even a smaller supply cell can take
  almost `19h`, so the next retake must start with a cheaper falsification
  attempt rather than the deepest cell
- `selected24_saved64` is the next honest canary because it increases saved
  Phase-B supply without jumping immediately to the most expensive setting
- it is better to test one high-information cell fully inside budget than to
  relaunch another oversized runtime cell

Hold the deeper retry for later only if this cheaper canary creates real spare
challenger supply or otherwise clearly justifies spending more time:

- `phaseb_supply_selected48_saved96_stage3only_v1`

## Microbatch 1 result

Completed microbatch:

- `1111/search7002`
- preset:
  - `phaseb_supply_selected24_saved64_stage3only_v1`
- runtime bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260420T163353521403Z__bench_solve_pipeline_no_wli__ee62083`
- extracted readout:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260421T145900Z__phaseb_challenger_supply_retake_microbatch_v1/`

Result:

- elapsed about `18.82h`
- retained best-match delta:
  - `-0.004`
- true spare non-selected retained `phaseB_topk` challengers:
  - `14`
- duplicate non-selected retained `phaseB_topk` challengers:
  - `0`
- downstream replacement engageable:
  - `1`
- downstream quota engageable:
  - `0`

Interpretation:

- the upstream supply suspicion is validated on this richer pool
- the added supply did not improve the top-line result on this cell
- the next honest move is downstream richer-pool replacement reopen, not a
  deeper supply retry
- the original `12h` target budget was missed badly enough that this retake
  should not remain the active plan

## Decision rule after microbatch 1

### Continue the supply retake only if

- real spare non-selected retained `phaseB_topk` challengers appear
- and the result is not just duplicate archive growth

### Stop the supply retake early if

- true spare challenger count is still `0`
- and the runtime cost remains very high

If that stop condition is hit, the likely next branch is:

- `stage3_entry_const_local_depth_p9`

Actual branch after microbatch 1:

- the supply retake is no longer the active line
- the branch moved first to a richer-pool downstream replacement reopen because
  real spare challengers appeared
- `stage3_entry_const_local_depth_p9` remains the held next branch candidate if
  the richer-pool reopen closes cleanly

## Required outputs per microbatch

Each microbatch must end with:

- one completed run bundle
- one short extraction readout
- one explicit note on:
  - spare challenger count
  - duplicate-versus-true-spare split
  - winner source and lane
  - runtime cost
  - continue / stop recommendation

## Not allowed

Do not do any of these in the retake:

- relaunch the old `18`-job serial matrix unchanged
- treat partial progress as if it were a full-study answer
- queue multiple new jobs just because the machine is idle
- broaden the case basis before the microbatch method proves useful
