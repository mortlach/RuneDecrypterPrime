# No-WLI runtime budgeting reference note

Date: 2026-05-01

Status:

- active
- general planning reference

## Why this note exists

This note is the general place to look before estimating how long a no-WLI run
or batch might take.

Do not treat "one overnight run" as a generic unit.

Look here first, then size the run from retained evidence.

## Primary references

Use these generated references:

- broad runtime history ledger:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T234300Z__no_wli_runtime_history_reference_v1/`
- fixed-panel wallclock reference:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T234300Z__fixed_runtime_wallclock_reference_v1/`

Key files:

- broad row-level ledger:
  - `runtime_history_rows.csv`
- broad shape summary:
  - `runtime_shape_summary.csv`
- fixed-panel completed rows:
  - `fixed_runtime_completed_rows.csv`
- fixed-panel cell summary:
  - `fixed_runtime_cell_summary.csv`
- fixed-panel fixture summary:
  - `fixed_runtime_fixture_seed_summary.csv`
- fixed-panel search summary:
  - `fixed_runtime_search_seed_summary.csv`
- fixed-panel planning note:
  - `fixed_runtime_wallclock_reference.md`

## How to use this note

Before launching any new multi-hour no-WLI runtime job or matrix:

1. look for the exact retained cell first
2. if no exact cell exists, look for the closest retained shape
3. budget from the conservative side:
   - exact-cell max if available
   - otherwise the worse of:
     - fixture-family max
     - search-seed max
4. do not call a batch "overnight" unless the serial total fits with margin
5. if the first canary already overshoots the intended session budget, stop and
   rescope

## Current high-signal fixed-panel read

Retained fixed `p9 / c3 / l1000` timings currently show:

- `611/search7002` is the main wallclock trap:
  - mean about `12.89h`
  - max about `18.96h`
- `1111/search7002` is no longer safe to treat as a cheap default cell:
  - retained runs now span about `2.32h` to `18.81h`
  - the new v79 control/full-pipeline panel job took about `13.54h`
  - materially different mechanism families have different timing classes
- retained `1111` cells are not uniformly cheap once the config family changes:
  - current family mean about `6.50h`
  - current family max about `18.81h`
- retained `611` cells are the riskiest fixed-panel family:
  - mean about `6.62h`
  - max about `18.96h`
- retained `search7002` remains the heaviest search-seed family:
  - mean about `9.83h`
  - max about `18.96h`

So for fixed-panel planning:

- do not assume one `611` canary is a normal overnight unit
- do not budget richer-supply or other altered runtime families from legacy
  control timings alone
- treat `search7002` as a heavy seed unless same-family retained evidence says
  otherwise
- if you need a real `~8h` target, do not choose `1111/search7002` as the first
  confirmation cell by default
- do not rerun a six-job full-pipeline panel whose first completed job already
  took `13.54h` under a `10h` intended panel cap

## Housekeeping check

Checked current through:

- `2026-05-01` America/Los_Angeles

Current state of the timing reference:

- the latest materially important completed multi-hour runtime captured in the
  active history ledger is:
  - run id:
    - `20260428T035424021944Z__bench_solve_pipeline_no_wli__ee62083`
  - fixed cell:
    - `1111/search7002`
  - elapsed:
    - `13.5424h`
  - preset:
    - `stage35_baseline_score_plus_novelty_live_bounded_p9`
  - interpretation:
    - v79 completed the control / legacy-entry job, not the
      constant-local-depth candidate
- that row is present in:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T011225Z__no_wli_runtime_history_reference_v1/runtime_history_rows.csv`
- the current fixed-wallclock reference now counts `24` retained completed
  fixed `p9/c3/l1000` rows
- the current fixed-wallclock reference includes `3` retained
  `1111/search7002` rows with:
  - min:
    - `2.32h`
  - mean:
    - `11.56h`
  - max:
    - `18.81h`
- the earlier standalone exact replay:
  - `20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1`
  finished in:
  - `01:07:53`
- that older replay is no longer the best local planning anchor for the newer
  patched live-read family
- the newer patched exact replay canary:
  - `20260424T061020Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1`
  finished in:
  - `00:23:56`
- the completed follow-on family read:
  - `20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1`
  finished:
  - `5` jobs in `02:03:21`
  - observed per-job range:
    - `00:23:41`
    - to `00:26:43`
- that completed family run is now the best local serial timing anchor for
  this patched exact-replay live-read family
- it does not automatically justify refreshing the broad runtime-history or
  fixed-wallclock generated references, because it is an analysis exact replay
  family rather than a new completed fixture-matrix runtime class
- it also should not be confused with the heavier fixture-matrix runtime
  families captured in the broad history ledger
- the Phase-C multi-thread long harvest:
  - `20260427T020956Z__phasec_multi_thread_long_harvest_v1`
  completed in:
  - `19:21:02`
  but it is a saved-surface analysis harvest, not a fixture-matrix runtime row
- the v79 Stage-3 entry reorder-signal panel confirms that a six-job
  full-pipeline comparison is not viable as launched:
  - first completed job:
    - `13.54h`
  - planned panel cap:
    - `10h`
  - completed jobs:
    - `1 / 6`
  - next planning anchor:
    - use saved handoff/archive artefacts for a late-stage-only comparison
- the next constant-local-depth runtime is deliberately one handoff cell, not
  a full-pipeline panel:
  - target:
    - `1111/search7005`
  - retained same-cell legacy full-pipeline anchor:
    - `2.479h`
  - activation check:
    - legacy init3 `64`
    - candidate init3 `288`
    - widening factor `4.5x`
  - written watchdog cap:
    - `16h`
  - plan:
    - `planning/projects/no_wli/20_active_plans/no_wli_stage3_entry_const_local_depth_handoff_resume_plan_2026-05-01.md`
- the first constant-local-depth handoff runtime completed:
  - target:
    - `1111/search7005`
  - elapsed:
    - `7139.745s`
    - `1.983h`
  - result:
    - retained `0.372`
    - candidate `0.374`
    - delta `+0.002`
  - this is now the first same-family timing anchor for the handoff-resume
    configuration
- the second constant-local-depth handoff runtime completed:
  - target:
    - `1111/search7004`
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/`
  - elapsed:
    - `7755.439s`
    - `2.154h`
  - result:
    - retained `0.423`
    - candidate `0.406`
    - delta `-0.017`
  - timing read:
    - same-family handoff-resume cells now sit near `2h` for `7005` and
      `7004`
    - this does not make `7002` safe, because `7002` remains a materially
      different heavy lane in retained evidence
- the Stage 3.5 frontier-space robustness harvest completed:
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T161846Z__stage35_frontier_space_robustness_harvest_v1/`
  - elapsed:
    - `12602.918s`
    - `3.501h`
  - first-cell projection:
    - `21305.002s` against an `8h` cap
  - result:
    - `48 / 48` cells completed
    - `0` errors
  - timing read:
    - this is a new deeper local-rescue analysis timing shape
    - it supports stratified local-rescue harvests of this size inside an
      `8h` budget when the first-cell projection is below cap
- the PhaseB Runeberg NOSE Stage 3 PCB calibration continuation completed:
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb/`
  - launch/review note:
    - `planning/working/stage3_fwd_full_len5_14_pcb_launch_20260512.md`
  - review pack:
    - `planning/projects/no_wli/40_review_summaries/stage3_fwd_full_len5_14_pcb_review_pack_2026-05-13.zip`
  - elapsed:
    - `85298.1381107s`
    - `23.69h`
  - scale:
    - `10000` clean chunks
    - `370000` samples
    - `36260000` feature rows
  - observed throughput:
    - `4.337726569363257` samples/s
    - `425.09720379759915` feature rows/s
  - timing read:
    - this is a PhaseB calibration-analysis timing class, not a fixed-panel
      fixture-matrix runtime class
    - it is the current PCB anchor for future same-family FWD/full/no-WLI
      len5-14 calibration continuations
    - the fixed runtime-history and fixed-wallclock generated references are
      not superseded by this calibration run, because those ledgers track
      fixed-instance solver/runtime bundles

## Update rule

This note must be refreshed when new completed no-WLI runtime runs add material
timing evidence.

At minimum, refresh after:

- any completed multi-hour fixed-panel runtime microbatch
- any completed runtime canary in a new mechanism family
- any completed run that materially changes the slowest exact-cell or
  shape-level wallclock read

Refresh by rerunning:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_no_wli_runtime_history_reference_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_fixed_runtime_wallclock_reference_v1.py`

Then update this note's referenced output directories if newer completed
bundles supersede the current ones.

## Current planning rule

If a run estimate depends mostly on intuition rather than one of the references
above, the run is not ready to launch.
